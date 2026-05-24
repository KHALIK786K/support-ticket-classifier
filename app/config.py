"""
Centralized configuration loaded from environment variables.

All env-driven values for the app live here. We use pydantic-settings so
the values are validated and typed at startup.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # ---- General ----------------------------------------------------------
    app_version: str = Field(default="2.3.0")
    environment: str = Field(default="development")  # development|staging|production
    log_level: str = Field(default="INFO")

    # ---- API --------------------------------------------------------------
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    # ---- Auth -------------------------------------------------------------
    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60)

    # ---- Database ---------------------------------------------------------
    mysql_host: str = Field(default="localhost")
    mysql_port: int = Field(default=3306)
    mysql_user: str = Field(default="ticketml")
    mysql_password: str = Field(default="ticketml")
    mysql_db: str = Field(default="ticketml")

    # ---- Redis ------------------------------------------------------------
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_enabled: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=3600)

    # ---- ML ---------------------------------------------------------------
    model_path: str = Field(default="models/pipeline.pkl")
    high_confidence_threshold: float = Field(default=0.85)
    batch_predict_max: int = Field(default=500)

    # ---- Routing ----------------------------------------------------------
    routing_map: dict = Field(
        default_factory=lambda: {
            "Finance": "finance-l2",
            "Billing": "billing-l2",
            "Technical": "tech-l2",
            "HR": "hr-l2",
            "Account": "account-l2",
        }
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Module-level singleton — convenient and matches FastAPI's idioms.
settings = get_settings()
