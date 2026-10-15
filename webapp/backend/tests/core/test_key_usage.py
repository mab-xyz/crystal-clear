import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from src.api.core import key_usage, rate_limit
from src.api.core.config import settings
from src.api.core.database import get_session
from src.api.core.key_usage import UsageStore
from src.api.core.rate_limit import RateLimiter, rate_limit_middleware
from src.api.crud.api_key import create_api_key
from src.api.models.api_key import ApiKeyCreate
from src.api.routers import keys


class Clock:
    def __init__(self, t=1_760_000_000.0):  # 2025-10-09
        self.t = t

    def __call__(self):
        return self.t


@pytest.mark.asyncio
async def test_store_counts_by_day_and_status_class():
    clock = Clock()
    u = UsageStore(clock=clock)
    await u.record("AAAAAAAA", scan=True, status=200)
    await u.record("AAAAAAAA", scan=True, status=422)
    await u.record("BBBBBBBB", scan=False, status=500)
    clock.t += 86400
    await u.record("AAAAAAAA", scan=False, status=200)
    r = await u.read(7)
    a = r["AAAAAAAA"]
    assert (a["total"], a["scan"], a["2xx"], a["4xx"]) == (3, 2, 2, 1)
    assert sorted(a["by_day"].values()) == [1, 2]
    assert r["BBBBBBBB"]["5xx"] == 1 and r["BBBBBBBB"]["scan"] == 0
    assert (await u.read(1))["AAAAAAAA"]["total"] == 1  # only "today"
    assert list(await u.read(7, prefix="BBBBBBBB")) == ["BBBBBBBB"]


class FakePipe:
    def __init__(self, store):
        self.s, self.ops = store, []

    def hincrby(self, k, f, n):
        self.ops.append(("h", k, f, n))

    def expire(self, k, ttl):
        self.ops.append(("e", k, ttl))

    async def execute(self):
        for op in self.ops:
            if op[0] == "h":
                self.s.setdefault(op[1], {})
                self.s[op[1]][op[2]] = self.s[op[1]].get(op[2], 0) + op[3]
        self.s["_pipelines"] = self.s.get("_pipelines", 0) + 1


class FakeRedis:
    def __init__(self):
        self.data = {}

    def pipeline(self):
        return FakePipe(self.data)

    async def hgetall(self, k):
        return {f.encode(): str(v).encode() for f, v in self.data.get(k, {}).items()}


@pytest.mark.asyncio
async def test_redis_path_uses_one_pipeline_per_request():
    redis = FakeRedis()
    u = UsageStore(redis, clock=Clock())
    await u.record("CCCCCCCC", scan=True, status=200)
    assert redis.data["_pipelines"] == 1  # one round trip per request
    assert (await u.read(1))["CCCCCCCC"]["total"] == 1


@pytest.fixture
def env(monkeypatch, tmp_path):
    db = create_engine(f"sqlite:///{tmp_path}/k.db", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(db)
    clock = Clock()
    limiter = RateLimiter(clock=clock)
    monkeypatch.setattr(rate_limit, "_limiter", limiter)
    monkeypatch.setattr(rate_limit, "_usage", UsageStore(clock=clock))
    for k, v in dict(rate_limit_enabled=True, rate_limit_scan_per_min=1000,
                     rate_limit_default_per_min=1000, rate_limit_anon_per_min=1000,
                     rate_limit_authfail_per_min=3, root_api_key="rootkey-rootkey",
                     api_key_auth_enabled=True).items():
        monkeypatch.setattr(settings, k, v)
    app = FastAPI()
    app.middleware("http")(rate_limit_middleware)
    app.include_router(keys.router)

    @app.post("/ethereum/scan/tx")
    async def scan():
        return {"ok": True}

    @app.get("/fail")
    async def fail():
        return JSONResponse({"x": 1}, status_code=500)

    @app.get("/r/{rid}")
    async def report(rid: str):
        return {}

    @app.get("/private")
    async def private():
        return JSONResponse({"detail": "Invalid or revoked API key"}, status_code=403)

    def _session():
        with Session(db) as s:
            yield s

    app.dependency_overrides[get_session] = _session
    with Session(db) as s:
        a = create_api_key(s, ApiKeyCreate(name="ledger-staging"))
        b = create_api_key(s, ApiKeyCreate(name="ledger-production"))
    return TestClient(app), a, b


def test_usage_endpoints_report_per_key_counts(env):
    c, a, b = env
    ha, hb = {"X-API-Key": a.key}, {"X-API-Key": b.key}
    for _ in range(3):
        c.post("/ethereum/scan/tx", headers=ha)
    c.get("/fail", headers=ha)
    c.post("/ethereum/scan/tx", headers=hb)
    c.get("/r/abc")  # unauthenticated report hit is never attributed to a key
    admin = c.get("/keys/usage", headers={"X-API-Key": "rootkey-rootkey"}).json()
    rows = {r["name"]: r for r in admin["keys"]}
    assert rows["ledger-staging"]["total"] == 4 and rows["ledger-staging"]["scan"] == 3
    assert rows["ledger-staging"]["server_error_5xx"] == 1 and rows["ledger-staging"]["ok_2xx"] == 3
    assert rows["ledger-production"]["total"] == 1
    assert admin["keys"][0]["name"] == "ledger-staging"  # sorted by usage
    me = c.get("/keys/usage/me", headers=hb).json()
    assert me["name"] == "ledger-production" and me["total"] == 1
    assert c.get("/keys/usage/me", headers=hb).json()["total"] == 2  # the previous /me call
    assert sum(me["by_day"].values()) == me["total"]


def test_usage_admin_only_and_me_needs_key(env):
    c, a, _ = env
    assert c.get("/keys/usage", headers={"X-API-Key": a.key}).status_code == 403
    assert c.get("/keys/usage").status_code == 401
    assert c.get("/keys/usage/me").status_code == 401


def test_forbidden_requests_are_not_usage_and_lock_out_the_ip(env):
    c, a, _ = env
    codes = [c.get("/private", headers={"X-API-Key": f"fake{i}-fake{i}"}).status_code for i in range(5)]
    assert codes == [403, 403, 403, 429, 429]  # invalid keys (403) count as auth failures
    assert c.get("/keys/usage", headers={"X-API-Key": "rootkey-rootkey"}).status_code == 429
    assert key_usage is not None
