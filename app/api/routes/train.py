"""
Training endpoint.

For demo purposes the training "job" is launched synchronously in a background
task. In production this would be a Celery/Argo Workflow job that runs on a
GPU node-pool and writes the artifact to Azure Blob.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.dependencies import require_admin
from app.api.schemas import TrainRequest, TrainResponse, UserInfo
from app.core.logging import get_logger
from app.ml.train import run_training_job

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "",
    response_model=TrainResponse,
    summary="Trigger a model retraining job (admin only)",
)
async def trigger_training(
    request: TrainRequest,
    background_tasks: BackgroundTasks,
    admin: Annotated[UserInfo, Depends(require_admin)],
) -> TrainResponse:
    job_id = f"train-{datetime.utcnow().strftime('%Y%m%d-%H%M')}-{uuid.uuid4().hex[:6]}"
    logger.info("training.job_queued", job_id=job_id, admin=admin.username, **request.model_dump())

    background_tasks.add_task(
        run_training_job,
        job_id=job_id,
        data_source=request.data_source,
        min_samples=request.min_samples_per_class,
        promote_if_better=request.promote_if_better,
    )

    return TrainResponse(
        job_id=job_id,
        status="started",
        estimated_seconds=240,
    )
