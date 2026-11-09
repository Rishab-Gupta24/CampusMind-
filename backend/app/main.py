import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import catalog, documents, health, lectures
from app.config import get_settings
from app.db import NotConfiguredError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("campusmind")

settings = get_settings()

app = FastAPI(title="CampusMind API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
