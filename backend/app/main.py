"""
Verity API - Production-grade RAG Research Platform
Main application entry point.
"""

import time
import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.api.documents import router as documents_router
from app.api.research import router as research_router
from app.api.evaluation import router as evaluation_router
from app.api.system import router as system_router

logger = logging.getLogger("verity")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler – initialise DB on startup."""
    logger.info("Starting Verity API …")
    await init_db()
    logger.info("Database initialised.")
    yield
    logger.info("Shutting down Verity API …")


app = FastAPI(
    title="Verity API",
    description=(
        "Verity is a production-grade RAG research platform that provides "
        "document ingestion, semantic retrieval, answer generation, and "
        "evaluation capabilities."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Attach X-Process-Time header to every response."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{elapsed:.4f}"
    return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning("ValueError: %s | path=%s", exc, request.url.path)
    return JSONResponse(
        status_code=422,
        content={
            "error": str(exc),
            "status_code": 422,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
        },
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(documents_router)
app.include_router(research_router)
app.include_router(evaluation_router)
app.include_router(system_router)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/", tags=["Root"])
async def root():
    """Return basic API information."""
    return {
        "name": "Verity API",
        "version": "0.1.0",
        "description": "Production-grade RAG Research Platform",
        "docs": "/docs",
        "health": "/api/system/health",
    }
