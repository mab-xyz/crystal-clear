import asyncio
from contextlib import asynccontextmanager

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

# Setup logging
setup_logging()


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
app.include_router(
    analysis.router,
)
app.include_router(info.router, include_in_schema=False)
app.include_router(audit.router, include_in_schema=False)
app.include_router(contract.router, include_in_schema=False)
app.include_router(repository.router, include_in_schema=False)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Crystal-Clear API!",
        "docs": "/docs",
        "redoc": "/redoc",
    }
