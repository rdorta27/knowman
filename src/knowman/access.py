"""Authentication and request-rate limiting for the HTTP API. Kept separate from
api.py: the routes serve the product, this module defends the door — a token
check and a request counter, neither of which knows what search or ask do.

Both are opt-in and off by default: unset API_TOKEN leaves every route open
exactly as before this module existed, and RATE_LIMIT_PER_MINUTE=0 disables
the limiter entirely. Enabling either is a deliberate step for a deployment
reachable beyond localhost, not a default this codebase imposes on local use.
"""

import hmac
import time

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from knowman.config import Settings, get_settings

# auto_error=False: a missing header must fall through to the "no token
# configured" no-op below, not turn into a 403 before require_token runs.
# Declaring the scheme this way (rather than reading the header off Request
# by hand) is what makes Swagger UI show a lock icon and an "Authorize"
# dialog on every protected route, entering the token once per session.
bearer_scheme = HTTPBearer(auto_error=False)


def require_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> None:
    """FastAPI dependency: a no-op WHEN no token is configured, otherwise requires
    a matching bearer credential. hmac.compare_digest avoids leaking the token's
    length or contents through response-time differences."""
    if not settings.api_token:
        return
    if credentials is None or not hmac.compare_digest(credentials.credentials, settings.api_token):
        raise HTTPException(status_code=401, detail="missing or invalid token")


class RateLimiter:
    """A fixed-window counter per client IP: each IP gets `limit` requests per
    60-second window, then every further request in that window is refused.
    Per-process, in-memory — it doesn't coordinate across multiple workers,
    which this project doesn't run behind this API today. `limit` is passed
    per call, not stored, so the middleware can read Settings fresh on every
    request without mutating shared state."""

    _WINDOW_SECONDS = 60.0

    def __init__(self) -> None:
        self._windows: dict[str, tuple[float, int]] = {}

    def seconds_until_allowed(
        self, client_ip: str, limit: int, now: float | None = None
    ) -> float | None:
        """None WHEN the request is allowed (and it's counted); otherwise the
        seconds remaining until the window resets."""
        now = time.monotonic() if now is None else now
        window_start, count = self._windows.get(client_ip, (now, 0))
        elapsed = now - window_start
        if elapsed >= self._WINDOW_SECONDS:
            window_start, count = now, 0
            elapsed = 0.0
        if count >= limit:
            return self._WINDOW_SECONDS - elapsed
        self._windows[client_ip] = (window_start, count + 1)
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Reads rate_limit_per_minute fresh on every request, the same way every
    route already reads settings — a limiter built once at import time
    couldn't be turned on or off by the tests, or by an operator's .env."""

    _EXEMPT_PATHS = {"/health"}

    def __init__(self, app) -> None:
        super().__init__(app)
        self._limiter = RateLimiter()

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        limit = settings.rate_limit_per_minute
        if request.url.path in self._EXEMPT_PATHS or limit <= 0:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        retry_after = self._limiter.seconds_until_allowed(client_ip, limit)
        if retry_after is not None:
            return Response(
                content="rate limit exceeded",
                status_code=429,
                headers={"Retry-After": str(int(retry_after) + 1)},
            )
        return await call_next(request)
