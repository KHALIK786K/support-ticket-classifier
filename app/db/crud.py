"""
Thin CRUD layer used by API handlers.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Feedback, Prediction, Ticket, User


# --- Users -------------------------------------------------------------------
def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()


# --- Tickets -----------------------------------------------------------------
def create_ticket(db: Session, *, subject: str, body: str, external_id: str | None = None) -> Ticket:
    ticket = Ticket(subject=subject, body=body, external_id=external_id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket(db: Session, ticket_id: int) -> Optional[Ticket]:
    return db.get(Ticket, ticket_id)


# --- Predictions -------------------------------------------------------------
def create_prediction(
    db: Session,
    *,
    ticket_id: int,
    predicted_category: str,
    confidence: float,
    model_version: str,
    routed_to: str | None = None,
    latency_ms: int | None = None,
) -> Prediction:
    pred = Prediction(
        ticket_id=ticket_id,
        predicted_category=predicted_category,
        confidence=confidence,
        model_version=model_version,
        routed_to=routed_to,
        latency_ms=latency_ms,
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)
    return pred


# --- Feedback ----------------------------------------------------------------
def create_feedback(db: Session, *, ticket_id: int, correct_category: str, agent: str) -> Feedback:
    fb = Feedback(ticket_id=ticket_id, correct_category=correct_category, agent_username=agent)
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


def labelled_corpus(db: Session, *, min_per_class: int = 0) -> List[tuple[str, str]]:
    """
    Return [(text, category), ...] suitable for retraining — joins each
    feedback row to its ticket and uses the agent-confirmed label.
    """
    rows = db.execute(
        select(Ticket.subject, Ticket.body, Feedback.correct_category)
        .join(Feedback, Feedback.ticket_id == Ticket.id)
    ).all()
    return [(f"{s}. {b}", cat) for (s, b, cat) in rows]
