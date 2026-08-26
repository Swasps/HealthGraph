import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import HealthGraphError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Every error the domain layer raises, plus FastAPI's own request
    validation error, is rendered through this single envelope so REST
    clients never see a raw traceback or an inconsistent error shape
    depending on which layer failed.
    """

    @app.exception_handler(HealthGraphError)
    async def handle_health_graph_error(
        request: Request, exc: HealthGraphError
    ) -> JSONResponse:
        if exc.http_status >= 500:
            logger.exception("Unhandled application error", exc_info=exc)
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request failed validation.",
                    "details": jsonable_encoder(exc.errors()),
                }
            },
        )
