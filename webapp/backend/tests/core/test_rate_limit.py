import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from src.api.core import rate_limit
from src.api.core.config import settings
from src.api.core.rate_limit import RateLimiter, rate_limit_middleware


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.mark.asyncio
async def test_fixed_window_allows_limit_then_blocks_then_resets():
    clock = Clock(1_000_040)  # 20s into a window
    rl = RateLimiter(clock=clock)
    results = [await rl.hit("k", 3) for _ in range(4)]
    assert [r[0] for r in results] == [True, True, True, False]
    assert results[-1][1] == 40  # seconds until the window ends
    clock.t += 40
    assert (await rl.hit("k", 3))[0] is True


@pytest.mark.asyncio
async def test_keys_are_independent():
    rl = RateLimiter(clock=Clock())
    assert (await rl.hit("a", 1))[0] and not (await rl.hit("a", 1))[0]
    assert (await rl.hit("b", 1))[0]


class BrokenRedis:
    async def incr(self, *_):
        raise ConnectionError("down")

    async def get(self, *_):
        raise ConnectionError("down")


@pytest.mark.asyncio
async def test_redis_failure_falls_back_to_memory_not_error():
    rl = RateLimiter(BrokenRedis(), clock=Clock())
    assert (await rl.hit("k", 1))[0] is True
    assert (await rl.hit("k", 1))[0] is False
    assert await rl.count("k") == 2


@pytest.fixture
def app_client(monkeypatch):
    monkeypatch.setattr(rate_limit, "_limiter", RateLimiter(clock=Clock()))
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_scan_per_min", 2)
    monkeypatch.setattr(settings, "rate_limit_report_per_min", 2)
    monkeypatch.setattr(settings, "rate_limit_default_per_min", 5)
    monkeypatch.setattr(settings, "rate_limit_anon_per_min", 3)
    monkeypatch.setattr(settings, "rate_limit_authfail_per_min", 2)
    app = FastAPI()
    app.middleware("http")(rate_limit_middleware)

    @app.post("/ethereum/scan/tx")
    async def scan():
        key_ok = True
        return JSONResponse({"ok": key_ok})

    @app.get("/r/{rid}")
    async def report(rid: str):
        return {"id": rid}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/forbidden")
    async def forbidden():
        return JSONResponse({"detail": "Invalid or revoked API key"}, status_code=403)

    @app.get("/secure")
    async def secure():
        return JSONResponse({"detail": "API key required"}, status_code=401)

    @app.get("/other")
    async def other():
        return {"ok": True}

    return TestClient(app)


def test_scan_limited_per_api_key(app_client):
    h1, h2 = {"X-API-Key": "one"}, {"X-API-Key": "two"}
    assert [app_client.post("/ethereum/scan/tx", headers=h1).status_code for _ in range(3)] == [200, 200, 429]
    r = app_client.post("/ethereum/scan/tx", headers=h1)
    assert r.status_code == 429 and r.json()["code"] == 429
    assert int(r.headers["Retry-After"]) >= 1
    assert app_client.post("/ethereum/scan/tx", headers=h2).status_code == 200


def test_report_links_limited_per_ip_without_key(app_client):
    assert [app_client.get(f"/r/id{i}").status_code for i in range(3)] == [200, 200, 429]


def test_default_bucket_differs_for_keyed_and_anonymous(app_client):
    assert [app_client.get("/other").status_code for _ in range(4)] == [200, 200, 200, 429]
    h = {"X-API-Key": "k"}
    assert all(app_client.get("/other", headers=h).status_code == 200 for _ in range(5))
    assert app_client.get("/other", headers=h).status_code == 429


def test_health_is_exempt(app_client):
    assert all(app_client.get("/health").status_code == 200 for _ in range(50))


def test_rotating_fake_keys_get_locked_out_by_auth_failures(app_client):
    codes = [app_client.get("/secure", headers={"X-API-Key": f"fake{i}"}).status_code for i in range(4)]
    assert codes == [401, 401, 429, 429]
    # the lockout is per IP: a valid-looking request from it is refused too
    assert app_client.get("/other", headers={"X-API-Key": "good"}).status_code == 429


def test_disabled_flag_bypasses(app_client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    assert all(app_client.get(f"/r/{i}").status_code == 200 for i in range(10))


def test_invalid_keys_403_also_count_as_auth_failures(app_client):
    codes = [app_client.get("/forbidden", headers={"X-API-Key": f"bad{i}"}).status_code for i in range(4)]
    assert codes == [403, 403, 429, 429]
