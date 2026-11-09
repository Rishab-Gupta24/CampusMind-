from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import catalog, health
from app.config import get_settings
from app.db import NotConfiguredError

settings = get_settings()

app = FastAPI(title="CampusMind API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


@app.exception_handler(NotConfiguredError)
async def not_configured(_: Request, exc: NotConfiguredError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"error": str(exc)})


@app.exception_handler(Exception)
async def unexpected_error(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": "Something went wrong. Please try again."})


app.include_router(health.router)
app.include_router(catalog.router)
