import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import db
from app.api import ask, catalog, documents, events, feedback, flagged, health, insights, lectures, study
from app.config import get_settings
from app.db import NotConfiguredError
from app.llm.base import get_provider
from app.rag import reranker
from app.rag.embedder import embed_query

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("campusmind")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Load the reranker and warm the LLM in the background so the first question starts fast."""

    async def warm() -> None:
        try:
            # Background uploads die with the process: anything still "processing" was interrupted.
            stuck = await asyncio.to_thread(db.fail_interrupted)
            if stuck:
                log.warning("Marked %d interrupted upload(s) as failed", stuck)
        except Exception:
            log.exception("Could not check for interrupted uploads")
        try:
            await asyncio.to_thread(reranker.load)
            await asyncio.to_thread(embed_query, "warm up")  # loads the embedding model too
            provider = get_provider()
            if hasattr(provider, "warm_up"):
                await provider.warm_up()
            log.info("Models ready")
        except Exception:
            log.exception("Model warm-up failed")

    task = asyncio.create_task(warm())
    yield
    task.cancel()


app = FastAPI(title="CampusMind API", lifespan=lifespan)

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CLIENT_HEADER = "x-campusmind"


@app.middleware("http")
async def require_client_header(request: Request, call_next):
    """Block cross-site requests: a custom header forces the browser's CORS preflight, which only our app passes.

    Without it any website open in the same browser could POST a multipart upload to localhost:8000.
    """
    if request.method in UNSAFE_METHODS and request.headers.get(CLIENT_HEADER) != "1":
        return JSONResponse(status_code=403, content={"error": "Requests must come from the CampusMind app."})
    return await call_next(request)


# Middleware runs outermost-last: host check, then CORS (answers preflights), then the header check above.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Accept", "X-CampusMind"],
)
# Rejects DNS-rebinding: a hostile domain resolved to 127.0.0.1 still sends its own Host header.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"])


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields = sorted({str(err["loc"][-1]) for err in exc.errors() if err.get("loc")})
    message = f"Check these fields: {', '.join(fields)}." if fields else "Some fields are missing or invalid."
    return JSONResponse(status_code=422, content={"error": message})


@app.exception_handler(NotConfiguredError)
async def not_configured(_: Request, exc: NotConfiguredError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"error": str(exc)})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    log.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"error": "Something went wrong. Please try again."})


app.include_router(health.router)
app.include_router(catalog.router)
app.include_router(documents.router)
app.include_router(lectures.router)
app.include_router(ask.router)
app.include_router(feedback.router)
app.include_router(flagged.router)
app.include_router(insights.router)
app.include_router(study.router)
app.include_router(events.router)
