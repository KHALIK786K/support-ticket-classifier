"""
API integration tests using FastAPI's TestClient.

We train a quick toy model in a temp dir and point the predictor at it,
so these tests run without needing a real artifact on disk.
"""
from __future__ import annotations

import os
from pathlib import Path

import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.ml.pipeline import build_pipeline


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    # Train a tiny model and point MODEL_PATH at it before importing the app.
    tmp = tmp_path_factory.mktemp("models")
    model_path = tmp / "pipeline.pkl"

    df = pd.DataFrame(
        [
            ("refund not received for last order please help", "Billing"),
            ("unable to login server error keeps coming", "Technical"),
            ("salary slip missing from hr portal this month", "HR"),
            ("share gst invoice for the previous quarter", "Finance"),
            ("forgot account password reset email never received", "Account"),
        ] * 30,
        columns=["text", "category"],
    )
    pipe = build_pipeline()
    pipe.fit(df["text"], df["category"])
    pipe._metadata = {"version": "test-1.0.0"}  # type: ignore[attr-defined]
    joblib.dump(pipe, model_path)

    os.environ["MODEL_PATH"] = str(model_path)
    os.environ["JWT_SECRET"] = "test-secret"

    # Import AFTER env vars are set so settings picks them up.
    from app.main import app  # noqa: WPS433 — intentional late import

    with TestClient(app) as c:
        yield c


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready(client: TestClient) -> None:
    r = client.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["model_loaded"] is True


def test_predict_requires_auth(client: TestClient) -> None:
    r = client.post("/predict", json={"subject": "x", "body": "y"})
    assert r.status_code == 401


def _get_token(client: TestClient, user: str = "agent", password: str = "agent") -> str:
    r = client.post("/auth/login", data={"username": user, "password": password})
    # NB: passwords for seeded users won't actually verify here (hashes were
    # placeholders). In a real test we'd patch verify_password — skipping below.
    return r.json().get("access_token", "")


def test_predict_with_mocked_auth(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass JWT for this test by overriding the auth dependency."""
    from app.api import dependencies as deps
    from app.api.schemas import UserInfo
    from app.main import app

    def _fake_user() -> UserInfo:
        return UserInfo(username="tester", role="agent")

    app.dependency_overrides[deps.get_current_user] = _fake_user

    r = client.post(
        "/predict",
        json={
            "subject": "Refund not received",
            "body": "I have not received my refund for last week's order.",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["predicted_category"] in {"Finance", "Billing", "Technical", "HR", "Account"}
    assert 0.0 <= body["confidence"] <= 1.0
    assert len(body["top_3"]) == 3
    assert body["model_version"] == "test-1.0.0"

    app.dependency_overrides.clear()
