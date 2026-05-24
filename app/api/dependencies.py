"""
Shared FastAPI dependencies.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from app.api.schemas import UserInfo
from app.core.security import decode_token
from app.ml.predict import TicketPredictor

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_predictor(request: Request) -> TicketPredictor:
    """Return the singleton predictor stored on app.state."""
    predictor: TicketPredictor | None = getattr(request.app.state, "predictor", None)
    if predictor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded",
        )
    return predictor


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserInfo:
    """Decode the JWT and return the authenticated user."""
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return UserInfo(username=payload["sub"], role=payload.get("role", "agent"))


def require_admin(user: Annotated[UserInfo, Depends(get_current_user)]) -> UserInfo:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user
