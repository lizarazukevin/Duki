from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.config import Settings, get_settings
from backend.constants import API_TITLE, API_V1_PREFIX, LOGGER_NAME
from backend.errors import DukiError
from backend.routers.auth import router as auth_router
from backend.routers.calendar_events import router as calendar_events_router
from backend.routers.health import router as health_router
from backend.routers.tasks import router as tasks_router

logger = logging.getLogger(LOGGER_NAME)


def _validation_details(error: RequestValidationError) -> dict[str, object]:
    fields = [
        {
            "field": ".".join(str(part) for part in issue.get("loc", ())),
            "message": str(issue.get("msg", "Invalid value")),
            "type": str(issue.get("type", "validation_error")),
        }
        for issue in error.errors()
    ]
    return {"fields": fields}


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        timeout = httpx.Timeout(10.0, connect=5.0)
        limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as http_client:
            app.state.http_client = http_client
            yield

    docs_url = "/docs" if resolved_settings.is_local else None
    app = FastAPI(
        title=API_TITLE,
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.include_router(health_router)
    app.include_router(auth_router, prefix=API_V1_PREFIX)
    app.include_router(calendar_events_router, prefix=API_V1_PREFIX)
    app.include_router(tasks_router, prefix=API_V1_PREFIX)

    @app.exception_handler(DukiError)
    async def handle_domain_error(request: Request, error: DukiError) -> JSONResponse:
        logger.warning("domain_error code=%s path=%s", error.code, request.url.path)
        return JSONResponse(
            status_code=error.status_code,
            content={"error": str(error), "code": error.code, "details": {}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        logger.info("validation_error path=%s", request.url.path)
        return JSONResponse(
            status_code=422,
            content={
                "error": "Request validation failed",
                "code": "validation_error",
                "details": _validation_details(error),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_error path=%s type=%s",
            request.url.path,
            type(error).__name__,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "An unexpected error occurred",
                "code": "internal_error",
                "details": {},
            },
        )

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
