"""
Prediction endpoints.

- POST /predict        → classify a single ticket
- POST /predict/batch  → classify up to N tickets in one call
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_predictor
from app.api.schemas import (
    BatchPredictionItem,
    BatchPredictionResponse,
    BatchTicketInput,
    CategoryScore,
    PredictionResponse,
    TicketInput,
    UserInfo,
)
from app.config import settings
from app.core.logging import get_logger
from app.ml.predict import TicketPredictor

router = APIRouter()
logger = get_logger(__name__)


def _join(t: TicketInput) -> str:
    return f"{t.subject}. {t.body}"


@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Classify a single support ticket",
)
async def predict(
    ticket: TicketInput,
    predictor: Annotated[TicketPredictor, Depends(get_predictor)],
    user: Annotated[UserInfo, Depends(get_current_user)],
) -> PredictionResponse:
    start = time.perf_counter()
    text = _join(ticket)
    result = predictor.predict_one(text)

    top_3 = [CategoryScore(category=c, score=s) for c, s in result["top_3"]]
    confidence = result["confidence"]
    category = result["predicted_category"]
    routed = settings.routing_map.get(category) if confidence >= settings.high_confidence_threshold else None

    latency_ms = int((time.perf_counter() - start) * 1000)
    ticket_id = str(uuid.uuid4())

    logger.info(
        "prediction.served",
        ticket_id=ticket_id,
        category=category,
        confidence=round(confidence, 4),
        latency_ms=latency_ms,
        user=user.username,
    )

    return PredictionResponse(
        ticket_id=ticket_id,
        predicted_category=category,
        confidence=confidence,
        top_3=top_3,
        routed_to_queue=routed,
        needs_review=confidence < settings.high_confidence_threshold,
        model_version=predictor.version,
        latency_ms=latency_ms,
        timestamp=datetime.now(timezone.utc),
    )


@router.post(
    "/predict/batch",
    response_model=BatchPredictionResponse,
    summary="Classify a batch of tickets",
)
async def predict_batch(
    payload: BatchTicketInput,
    predictor: Annotated[TicketPredictor, Depends(get_predictor)],
    user: Annotated[UserInfo, Depends(get_current_user)],
) -> BatchPredictionResponse:
    if len(payload.tickets) > settings.batch_predict_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size exceeds limit of {settings.batch_predict_max}",
        )

    start = time.perf_counter()
    texts = [_join(t) for t in payload.tickets]
    results = predictor.predict_many(texts)

    items = [
        BatchPredictionItem(
            predicted_category=r["predicted_category"],
            confidence=r["confidence"],
            needs_review=r["confidence"] < settings.high_confidence_threshold,
        )
        for r in results
    ]
    latency_ms = int((time.perf_counter() - start) * 1000)

    logger.info(
        "prediction.batch_served",
        count=len(items),
        latency_ms=latency_ms,
        user=user.username,
    )

    return BatchPredictionResponse(
        results=items,
        count=len(items),
        model_version=predictor.version,
        latency_ms=latency_ms,
    )
