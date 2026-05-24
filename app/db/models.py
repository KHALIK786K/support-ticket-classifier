"""
ORM models.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="agent")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(64), index=True, nullable=True)
    subject = Column(String(512), nullable=False)
    body = Column(Text, nullable=False)
    submitted_by = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    predictions = relationship("Prediction", back_populates="ticket", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="ticket", cascade="all, delete-orphan")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=False)
    predicted_category = Column(String(64), index=True, nullable=False)
    confidence = Column(Float, nullable=False)
    model_version = Column(String(32), nullable=False)
    routed_to = Column(String(64), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    ticket = relationship("Ticket", back_populates="predictions")


class Feedback(Base):
    """Agent-provided correction for a prediction — fuel for retraining."""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=False)
    correct_category = Column(String(64), index=True, nullable=False)
    agent_username = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ticket = relationship("Ticket", back_populates="feedback")
