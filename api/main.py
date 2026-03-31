"""Standalone FastAPI application for the BDD-SKU API.

Serves all 25+ endpoints (v1 + legacy) from
``az_scout_bdd_api.routes`` in its own Container App,
independently of the az-scout plugin host.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from az_scout_bdd_api.db import close_pool, ensure_pool, is_healthy
from az_scout_bdd_api.routes import API_VERSION, router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Open the DB pool on startup, close it on shutdown.

    If the database is temporarily unreachable the app still starts
    (degraded mode).  The pool will be created lazily on the first
    request that needs a connection.
    """
    try:
        await ensure_pool()
        logger.info("Database pool ready")
    except Exception:
        logger.warning(
            "Database pool could not be opened at startup — "
            "the API will start in degraded mode and retry on first request",
            exc_info=True,
        )
    yield
    await close_pool()
    logger.info("Database pool closed")


app = FastAPI(
    title="BDD-SKU API",
    description="Azure VM SKU pricing & spot eviction data",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Structured error handlers — every response is valid JSON
# ------------------------------------------------------------------

def _error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


@app.exception_handler(404)
async def not_found_handler(request: Request, _exc: Any) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=_error_body(
            "NOT_FOUND",
            f"No endpoint matches {request.method} {request.url.path}. "
            "See GET / for the list of available endpoints.",
        ),
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, _exc: Any) -> JSONResponse:
    return JSONResponse(
        status_code=405,
        content=_error_body(
            "METHOD_NOT_ALLOWED",
            f"{request.method} is not allowed on {request.url.path}. Use GET.",
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_error_body("VALIDATION_ERROR", "Invalid request parameters", exc.errors()),
    )


@app.exception_handler(500)
async def internal_error_handler(_request: Request, _exc: Any) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=_error_body("INTERNAL", "An unexpected error occurred"),
    )


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

app.include_router(router)


@app.get("/", tags=["infra"])
async def root() -> JSONResponse:
    """API information and available endpoint groups."""
    return JSONResponse(
        content={
            "name": "BDD-SKU API",
            "apiVersion": API_VERSION,
            "endpoints": {
                "health": "/health",
                "ready": "/ready",
                "legacy": ["/status", "/spot/eviction-rates", "/spot/price-history"],
                "v1": "/v1/...",
                "docs": "/docs",
            },
        },
    )


@app.get("/health", tags=["infra"])
async def health() -> JSONResponse:
    """Liveness probe — always responds immediately, never blocks on DB."""
    return JSONResponse(
        status_code=200,
        content={"status": "alive"},
    )


@app.get("/ready", tags=["infra"])
async def ready() -> JSONResponse:
    """Readiness probe — checks DB connectivity."""
    healthy = await is_healthy()
    status = 200 if healthy else 503
    return JSONResponse(
        status_code=status,
        content={"status": "ok" if healthy else "degraded"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
