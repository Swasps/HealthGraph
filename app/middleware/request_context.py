"""Per-request context propagated via contextvars.

FastAPI dependencies can't easily reach code several layers down (a
repository, a logging call) without threading a parameter through every
function signature in between. A contextvar sidesteps that: the
middleware sets it once per request, and anything running within that
request — structured logging, the audit service — can read it back
without being handed it explicitly.
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
client_ip_var: ContextVar[str | None] = ContextVar("client_ip", default=None)


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        client_ip = request.client.host if request.client else None

        id_token = request_id_var.set(request_id)
        ip_token = client_ip_var.set(client_ip)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(id_token)
            client_ip_var.reset(ip_token)

        response.headers["X-Request-ID"] = request_id
        return response
