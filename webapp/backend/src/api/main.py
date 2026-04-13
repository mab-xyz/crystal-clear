import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from src.api.core.config import settings
from src.api.core.database import create_db_and_tables
from src.api.core.logging import setup_logging
from src.api.routers import analysis, audit, contract, health, info, repository
from src.api.routers import keys
from src.api.core.security import require_api_key
from src.api.services.request_logger import RequestRecord, build_request_logger

# Setup logging
setup_logging()

# Request logger – fan-out to local disk, GitHub, and Postgres (stub)
_request_logger = build_request_logger(
    log_dir=settings.request_log_dir,
    github_token=settings.github_token,
    github_repo=settings.github_database_repo,
)


def _sanitize_headers_for_logging(headers: list[tuple[str, str]]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    sensitive = {"authorization", "cookie", "set-cookie"}
    for key, value in headers:
        lower_key = key.lower()
        if lower_key in sensitive:
            continue
        if lower_key == "x-api-key":
            sanitized[key] = value[:8]
            continue
        sanitized[key] = value
    return sanitized


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    create_db_and_tables()
    redis = aioredis.from_url(settings.cache_url)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    yield
    # Shutdown: add cleanup here if needed


# Create FastAPI app
app = FastAPI(
    title="Crystal-Clear API",
    description="API for analyzing Ethereum smart contracts",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """Capture every request/response and persist it to all backends."""
    timestamp = datetime.now(tz=timezone.utc)
    start = time.monotonic()

    # Read and cache the body so the route handler can still read it.
    try:
        body = await request.body()
    except Exception:
        body = b""

    # Keep only a short API-key prefix while dropping other credentials.
    headers = _sanitize_headers_for_logging(list(request.headers.items()))

    response = await call_next(request)

    elapsed_ms = (time.monotonic() - start) * 1000.0
    record = RequestRecord(
        timestamp=timestamp,
        method=request.method,
        path=request.url.path,
        query_string=str(request.url.query),
        headers=headers,
        request_body=body,
        status_code=response.status_code,
        response_time_ms=elapsed_ms,
    )
    asyncio.create_task(_request_logger.log(record))
    return response


@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    try:
        return await asyncio.wait_for(
            call_next(request), timeout=settings.request_timeout
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504, detail="Request timed out"
        ) from None


# # Include routers
app.include_router(health.router, include_in_schema=False)
app.include_router(analysis.router, dependencies=[Depends(require_api_key)])
app.include_router(
    info.router,
    dependencies=[Depends(require_api_key)],
    include_in_schema=False,
)
app.include_router(
    audit.router,
    dependencies=[Depends(require_api_key)],
    include_in_schema=False,
)
app.include_router(
    contract.router,
    dependencies=[Depends(require_api_key)],
    include_in_schema=False,
)
app.include_router(
    repository.router,
    dependencies=[Depends(require_api_key)],
    include_in_schema=False,
)
app.include_router(
    keys.router,
    dependencies=[Depends(require_api_key)],
    include_in_schema=False,
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Crystal-Clear API!",
        "docs": "/docs",
        "redoc": "/redoc",
    }
