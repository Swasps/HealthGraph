from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.rest.admin import router as admin_router
from app.api.rest.auth import router as auth_router
from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.database.session import engine

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

app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
