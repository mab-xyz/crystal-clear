from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.logging import setup_logging
from core.database import create_db_and_tables
from routers import analysis, health, info

# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    create_db_and_tables()
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

# Include routers
app.include_router(health.router)
app.include_router(analysis.router)
app.include_router(info.router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Crystal-Clear API!",
        "docs": "/docs",
        "redoc": "/redoc",
    }
