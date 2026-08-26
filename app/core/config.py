from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration, sourced from environment variables.

    Kept as a single object (rather than scattered `os.getenv` calls) so
    every setting has a type, a default, and one place to look it up.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "HealthGraph"
    app_env: str = "development"
    debug: bool = False

    secret_key: str = "insecure-dev-key-change-me"

    database_url: str = "postgresql+asyncpg://healthgraph:healthgraph@localhost:5432/healthgraph"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_echo: bool = False

    redis_url: str = "redis://localhost:6379/0"
    cache_default_ttl_seconds: int = 60

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    graphql_max_query_depth: int = 10
    graphql_max_query_complexity: int = 1000

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Settings are cached for the process lifetime; tests override via
    dependency injection rather than mutating this singleton."""
    return Settings()
