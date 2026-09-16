"""Auth and rate limiting are opt-in and off by default (see access.py's own
docstring). These tests exercise both the pure logic (RateLimiter's window
math, needing no clock or database) and the wiring through a real app."""

import time

import pytest
from conftest import requires_db
from fastapi.testclient import TestClient

import knowman.api as api_module
from knowman.access import RateLimiter


@pytest.fixture(autouse=True)
def _fresh_rate_limiter():
    """api_module.app is a module-level singleton shared by every test in this
    file, and Starlette builds its middleware stack once and caches it — so the
    RateLimitMiddleware's counters would otherwise leak between tests through
    the shared "testclient" IP TestClient always presents. Clearing the cache
    forces a new RateLimitMiddleware, and a fresh RateLimiter, before each test."""
    api_module.app.middleware_stack = None
    yield


# --- RateLimiter: pure, no server, no clock -----------------------------------


def test_allows_requests_up_to_the_limit():
    limiter = RateLimiter()
    for _ in range(3):
        assert limiter.seconds_until_allowed("1.2.3.4", limit=3) is None


def test_refuses_the_request_past_the_limit():
    limiter = RateLimiter()
    for _ in range(3):
        limiter.seconds_until_allowed("1.2.3.4", limit=3)

    retry_after = limiter.seconds_until_allowed("1.2.3.4", limit=3)

    assert retry_after is not None
    assert 0 < retry_after <= 60


def test_tracks_each_ip_in_its_own_window():
    limiter = RateLimiter()
    for _ in range(3):
        limiter.seconds_until_allowed("1.2.3.4", limit=3)

    assert limiter.seconds_until_allowed("5.6.7.8", limit=3) is None


def test_resets_once_the_window_elapses():
    limiter = RateLimiter()
    start = time.monotonic()
    for _ in range(3):
        limiter.seconds_until_allowed("1.2.3.4", limit=3, now=start)

    assert limiter.seconds_until_allowed("1.2.3.4", limit=3, now=start + 61) is None


# --- OpenAPI: what makes Swagger UI show the lock -----------------------------


def test_the_openapi_schema_declares_the_bearer_scheme():
    schema = api_module.app.openapi()

    assert schema["components"]["securitySchemes"]["HTTPBearer"] == {
        "type": "http",
        "scheme": "bearer",
    }


def test_a_protected_route_references_the_bearer_scheme_in_openapi():
    schema = api_module.app.openapi()

    assert schema["paths"]["/search"]["get"]["security"] == [{"HTTPBearer": []}]


def test_health_carries_no_security_requirement_in_openapi():
    schema = api_module.app.openapi()

    assert "security" not in schema["paths"]["/health"]["get"]


# --- Wired into the app --------------------------------------------------------


@requires_db
def test_every_route_stays_open_with_no_token_configured(monkeypatch):
    monkeypatch.delenv("API_TOKEN", raising=False)
    client = TestClient(api_module.app)

    response = client.get("/search", params={"q": "anything"})

    assert response.status_code == 200


@requires_db
def test_health_never_needs_a_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "secret")
    client = TestClient(api_module.app)

    response = client.get("/health")

    assert response.status_code == 200


@requires_db
def test_a_protected_route_refuses_no_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "secret")
    client = TestClient(api_module.app)

    response = client.get("/search", params={"q": "anything"})

    assert response.status_code == 401


@requires_db
def test_a_protected_route_refuses_the_wrong_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "secret")
    client = TestClient(api_module.app)

    response = client.get(
        "/search", params={"q": "anything"}, headers={"Authorization": "Bearer wrong"}
    )

    assert response.status_code == 401


@requires_db
def test_a_protected_route_accepts_the_right_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "secret")
    client = TestClient(api_module.app)

    response = client.get(
        "/search", params={"q": "anything"}, headers={"Authorization": "Bearer secret"}
    )

    assert response.status_code == 200


@requires_db
def test_rate_limit_at_zero_never_refuses(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_PER_MINUTE", raising=False)
    client = TestClient(api_module.app)

    for _ in range(20):
        response = client.get("/search", params={"q": "anything"})
        assert response.status_code == 200


@requires_db
def test_rate_limit_refuses_past_the_configured_count(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    client = TestClient(api_module.app)

    for _ in range(2):
        assert client.get("/search", params={"q": "anything"}).status_code == 200

    response = client.get("/search", params={"q": "anything"})

    assert response.status_code == 429
    assert "Retry-After" in response.headers


@requires_db
def test_health_is_exempt_from_the_rate_limit(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    client = TestClient(api_module.app)
    client.get("/search", params={"q": "anything"})

    for _ in range(5):
        assert client.get("/health").status_code == 200
