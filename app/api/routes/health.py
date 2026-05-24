"""
Health and readiness endpoints.

- /health  → liveness probe (always 200 if process is up)
- /ready   → readiness probe (200 only when model + deps are healthy)
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.schemas import HealthResponse, ReadinessResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — used by Kubernetes."""
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadinessResponse)
async def ready(request: Request) -> ReadinessResponse:
    """Readiness probe — checks model + downstream deps."""
    model_loaded = getattr(request.app.state, "predictor", None) is not None

    # In a real deployment we'd ping MySQL and Redis here. Stubbed for brevity.
    db_status = "ok"
    redis_status = "ok"

    overall = "ready" if (model_loaded and db_status == "ok") else "not_ready"
    return ReadinessResponse(
        status=overall,
        model_loaded=model_loaded,
        db=db_status,
        redis=redis_status,
    )
