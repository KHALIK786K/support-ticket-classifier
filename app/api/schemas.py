"""
Pydantic schemas for API request and response payloads.

All schemas use Pydantic v2 syntax (model_config + Field).
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- Auth -------------------------------------------------------------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    username: str
    role: str  # admin|agent|system


# ---- Ticket prediction ------------------------------------------------------
class TicketInput(BaseModel):
    subject: str = Field(..., min_length=1, max_length=512)
    body: str = Field(..., min_length=1, max_length=8192)

    @field_validator("subject", "body")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "subject": "Refund not received",
                    "body": (
                        "Hi team, I cancelled my subscription on June 3rd "
                        "but the refund still hasn't hit my account. Order #A-2231."
                    ),
                }
            ]
        }
    )


class CategoryScore(BaseModel):
    category: str
    score: float = Field(..., ge=0.0, le=1.0)


class PredictionResponse(BaseModel):
    ticket_id: str
    predicted_category: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    top_3: List[CategoryScore]
    routed_to_queue: Optional[str] = None
    needs_review: bool = False
    model_version: str
    latency_ms: int
    timestamp: datetime


class BatchTicketInput(BaseModel):
    tickets: List[TicketInput] = Field(..., min_length=1, max_length=500)


class BatchPredictionItem(BaseModel):
    predicted_category: str
    confidence: float
    needs_review: bool = False


class BatchPredictionResponse(BaseModel):
    results: List[BatchPredictionItem]
    count: int
    model_version: str
    latency_ms: int


# ---- Training ---------------------------------------------------------------
class TrainRequest(BaseModel):
    data_source: str = Field(default="mysql", pattern="^(mysql|csv)$")
    min_samples_per_class: int = Field(default=100, ge=10)
    promote_if_better: bool = True


class TrainResponse(BaseModel):
    job_id: str
    status: str
    estimated_seconds: int


# ---- Feedback ---------------------------------------------------------------
class FeedbackInput(BaseModel):
    ticket_id: str
    correct_category: str
    agent_username: str


# ---- Health -----------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str = "ok"


class ReadinessResponse(BaseModel):
    status: str
    model_loaded: bool
    db: str
    redis: str
