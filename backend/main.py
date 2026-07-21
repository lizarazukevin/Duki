from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.config import Settings, get_settings
from backend.constants import API_TITLE, LOGGER_NAME
from backend.errors import DukiError
from backend.routers.health import router as health_router

logger = logging.getLogger(LOGGER_NAME)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    docs_url = "/docs" if resolved_settings.is_local else None
    app = FastAPI(
        title=API_TITLE,
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=None,
    )
    app.state.settings = resolved_settings
    app.include_router(health_router)

    @app.exception_handler(DukiError)
    async def handle_domain_error(request: Request, error: DukiError) -> JSONResponse:
        logger.warning("domain_error code=%s path=%s", error.code, request.url.path)
        return JSONResponse(
            status_code=400,
            content={"error": str(error), "code": error.code},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        logger.info("validation_error path=%s", request.url.path)
        return JSONResponse(
            status_code=422,
            content={"error": "Request validation failed", "code": "validation_error"},
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
            content={"error": "An unexpected error occurred", "code": "internal_error"},
        )

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
