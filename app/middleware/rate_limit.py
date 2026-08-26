"""Redis-backed rate limiting using a sliding-window counter.

A naive fixed-window counter (INCR a `requests:{minute}` key) lets a
client burst up to 2x the limit across a window boundary — max out the
last second of one window, then immediately max out the first second of
the next. The sliding-window counter approximates a true sliding log
without its O(n) memory cost: it blends the previous window's count into
the current one, weighted by how much of the current window has elapsed,
using two cheap INCR/GET calls instead of a sorted-set per request.
"""

import hashlib
import time

from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


class SlidingWindowRateLimiter:
    def __init__(self, redis: Redis, *, limit: int, window_seconds: int) -> None:
        self.redis = redis
        self.limit = limit
        self.window_seconds = window_seconds

    async def check(self, key: str) -> tuple[bool, int]:
        now = time.time()
        window = self.window_seconds
        current_bucket = int(now // window)
        previous_bucket = current_bucket - 1
        elapsed_fraction = (now - current_bucket * window) / window
        previous_weight = 1.0 - elapsed_fraction

        current_key = f"ratelimit:{key}:{current_bucket}"
        previous_key = f"ratelimit:{key}:{previous_bucket}"

        pipe = self.redis.pipeline(transaction=False)
        pipe.incr(current_key)
        pipe.expire(current_key, window * 2)
        pipe.get(previous_key)
        current_count, _, previous_raw = await pipe.execute()

        previous_count = int(previous_raw or 0)
        estimated = previous_count * previous_weight + current_count

        allowed = estimated <= self.limit
        remaining = max(0, self.limit - int(estimated))
        return allowed, remaining


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applied ahead of everything else in the stack (REST and GraphQL
    alike, since GraphQL is just a POST to one path) so an abusive caller
    is rejected before it can touch the database, the query-complexity
    analyzer, or any handler logic."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        redis: Redis,
        limit: int,
        window_seconds: int,
        exempt_paths: frozenset[str] = frozenset({"/health"}),
    ) -> None:
        super().__init__(app)
        self.limiter = SlidingWindowRateLimiter(redis, limit=limit, window_seconds=window_seconds)
        self.exempt_paths = exempt_paths

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        identity = self._resolve_identity(request)
        allowed, remaining = await self.limiter.check(identity)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests. Please slow down.",
                    }
                },
                headers={"Retry-After": str(self.limiter.window_seconds)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    @staticmethod
    def _resolve_identity(request: Request) -> str:
        """Rate limits are keyed off the bearer token itself when present
        (so one user can't dodge a limit by rotating IPs) and fall back to
        IP for unauthenticated traffic. Deliberately does not decode the
        JWT here — that would couple rate limiting to token validity, and
        a request with an *expired* token should still be throttled
        rather than skip the limiter entirely. The token is hashed with
        SHA-256 (not Python's `hash()`, which is randomized per-process
        and would split one client's traffic across different buckets on
        each worker process) so the identity is stable across every
        worker sharing this Redis instance.
        """
        authorization = request.headers.get("authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ").strip()
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
            return f"token:{digest}"
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
