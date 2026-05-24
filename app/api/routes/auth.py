"""
Authentication endpoints.

For demo purposes this uses an in-memory user dict. In production this would
hit MySQL via SQLAlchemy and verify hashed passwords with passlib's bcrypt.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.schemas import TokenResponse
from app.config import settings
from app.core.security import create_access_token, verify_password

router = APIRouter()


# Seeded users — replace with DB lookup in real deployments.
# Passwords are bcrypt hashes of the literal strings "admin" / "agent".
_USERS: dict[str, dict] = {
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$8mK4z9oCo0wYqxFhJZJ3T.4eDb1lDqQ/2cYg.eJxF5b.uVtH7Tk/G",
        "role": "admin",
    },
    "agent": {
        "username": "agent",
        "hashed_password": "$2b$12$D2.uZkXNkV2lO37lE/Y7e.b1rJ7P5Q8h.HnPq6V9C1eY7HuKtL3W.",
        "role": "agent",
    },
}


@router.post("/login", response_model=TokenResponse)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> TokenResponse:
    user = _USERS.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        subject=user["username"],
        role=user["role"],
        expires_minutes=settings.jwt_expire_minutes,
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
    )
