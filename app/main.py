"""
Application entry point.

Creates the FastAPI app, wires routers, middleware, exception handlers,
and lifecycle hooks (startup loads the ML model into memory).
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, health, predict, train
from app.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.ml.predict import TicketPredictor

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan: load the model once at startup,
    release resources at shutdown.
    """
    configure_logging(settings.log_level)
    logger.info("application.starting", env=settings.environment, version=settings.app_version)

    # Load the model into a singleton accessible across requests.
    predictor = TicketPredictor.from_disk(settings.model_path)
    app.state.predictor = predictor
    logger.info("model.loaded", path=settings.model_path, classes=predictor.classes)

    yield  # ---- application is running ----

    logger.info("application.shutting_down")


app = FastAPI(
    title="Support Ticket Classification API",
    description=(
        "Enterprise NLP service that classifies support tickets into "
        "Finance, Billing, Technical, HR, or Account."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS — locked down to allowed origins in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_timing(request: Request, call_next):
    """Measure end-to-end latency and add X-Process-Time header."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time"] = f"{elapsed_ms:.2f}"
    logger.info(
        "request.completed",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=round(elapsed_ms, 2),
    )
    return response


@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    """Convert internal AppException into a JSON error body."""
    logger.warning("app.exception", code=exc.code, message=exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


# ---- Routers ----------------------------------------------------------------
app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(predict.router, tags=["predict"])
app.include_router(train.router, prefix="/train", tags=["train"])


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "name": "ticket-classifier",
        "version": settings.app_version,
        "docs": "/docs",
    }
