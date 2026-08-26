from contextlib import asynccontextmanager

from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from app.api.graphql.context import get_graphql_context
from app.api.graphql.schema import schema
from app.api.rest.admin import router as admin_router
from app.api.rest.auth import router as auth_router
from app.cache.client import redis_client
from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.database.session import engine
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware

settings = get_settings()
configure_logging(debug=settings.debug)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

register_exception_handlers(app)

# Order matters: Starlette runs middleware outer-to-inner as listed here,
# so request context (needed by logging/audit) is established before the
# rate limiter runs, and the rate limiter rejects abusive traffic before
# it reaches any route handler.
app.add_middleware(
    RateLimitMiddleware,
    redis=redis_client,
    limit=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
app.add_middleware(RequestContextMiddleware)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(
    GraphQLRouter(schema, context_getter=get_graphql_context), prefix="/graphql"
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
