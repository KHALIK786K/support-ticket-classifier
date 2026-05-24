"""
Train + predict tests on a tiny in-memory dataset.
"""
from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from app.ml.pipeline import build_pipeline
from app.ml.predict import TicketPredictor


def _toy_df() -> pd.DataFrame:
    rows = [
        ("refund not received for order", "Billing"),
        ("payment failed but money deducted", "Billing"),
        ("unable to login getting 500 error", "Technical"),
        ("api endpoint returning 503", "Technical"),
        ("salary slip missing on hr portal", "HR"),
        ("provident fund balance not updated", "HR"),
        ("share gst invoice for order", "Finance"),
        ("financial statement for q3", "Finance"),
        ("forgot password reset email not arriving", "Account"),
        ("delete my account permanently", "Account"),
    ] * 20  # repeat to give the model enough samples
    return pd.DataFrame(rows, columns=["text", "category"])


def test_build_pipeline_returns_fittable_object() -> None:
    pipe = build_pipeline()
    df = _toy_df()
    pipe.fit(df["text"], df["category"])
    preds = pipe.predict(df["text"])
    assert len(preds) == len(df)


def test_predictor_round_trip(tmp_path: Path) -> None:
    pipe = build_pipeline()
    df = _toy_df()
    pipe.fit(df["text"], df["category"])
    pipe._metadata = {"version": "test-1.0.0"}  # type: ignore[attr-defined]

    path = tmp_path / "pipeline.pkl"
    joblib.dump(pipe, path)

    predictor = TicketPredictor.from_disk(path)
    out = predictor.predict_one("refund not received for last order")
    assert out["predicted_category"] in {"Billing", "Finance", "Account", "HR", "Technical"}
    assert 0.0 <= out["confidence"] <= 1.0
    assert len(out["top_3"]) == 3
    assert predictor.version == "test-1.0.0"


def test_predict_many_matches_predict_one(tmp_path: Path) -> None:
    pipe = build_pipeline()
    df = _toy_df()
    pipe.fit(df["text"], df["category"])
    pipe._metadata = {"version": "test-1.0.0"}  # type: ignore[attr-defined]
    path = tmp_path / "pipeline.pkl"
    joblib.dump(pipe, path)

    predictor = TicketPredictor.from_disk(path)
    texts = ["refund not received", "unable to login error", "salary slip missing"]
    single = [predictor.predict_one(t)["predicted_category"] for t in texts]
    batch = [r["predicted_category"] for r in predictor.predict_many(texts)]
    assert single == batch
