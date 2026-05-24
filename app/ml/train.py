"""
Training entry point.

Used both by:
- the scripts/train_model.py CLI for offline training
- the /train HTTP endpoint via run_training_job()
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split

from app.config import settings
from app.core.exceptions import TrainingError
from app.core.logging import get_logger
from app.ml.pipeline import build_pipeline
from app.ml.preprocessing import preprocess_many

logger = get_logger(__name__)


def train_model(
    data_path: str | Path,
    *,
    model_type: str = "logreg",
    test_size: float = 0.10,
    val_size: float = 0.10,
    random_state: int = 42,
    output_path: Optional[str | Path] = None,
) -> dict:
    """
    Train the classification pipeline.

    Returns a dict containing metrics and the path of the saved artifact.
    """
    data_path = Path(data_path)
    if not data_path.exists():
        raise TrainingError(f"Training data not found at {data_path}")

    logger.info("training.start", data=str(data_path), model_type=model_type)
    df = pd.read_csv(data_path)
    if {"text", "category"} - set(df.columns):
        raise TrainingError(f"Dataset must contain columns 'text' and 'category'; got {list(df.columns)}")

    df = df.dropna(subset=["text", "category"]).drop_duplicates(subset=["text"])
    logger.info("training.data_loaded", rows=len(df), classes=df["category"].nunique())

    # Preprocess up-front (the vectorizer will get cleaned text)
    df["text_clean"] = preprocess_many(df["text"].astype(str).tolist())
    df = df[df["text_clean"].str.len() > 0]

    X = df["text_clean"]
    y = df["category"]

    # 80 / 10 / 10 stratified split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train,
        test_size=val_size / (1 - test_size),
        random_state=random_state, stratify=y_train,
    )

    pipe = build_pipeline(model_type=model_type)

    start = time.perf_counter()
    pipe.fit(X_train, y_train)
    fit_seconds = time.perf_counter() - start

    val_preds = pipe.predict(X_val)
    test_preds = pipe.predict(X_test)
    val_f1 = f1_score(y_val, val_preds, average="macro")
    test_f1 = f1_score(y_test, test_preds, average="macro")

    report = classification_report(y_test, test_preds, output_dict=True, zero_division=0)

    output_path = Path(output_path or settings.model_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Attach metadata directly to the pipeline object — survives pickling.
    pipe._metadata = {  # type: ignore[attr-defined]
        "version": settings.app_version,
        "model_type": model_type,
        "fit_seconds": round(fit_seconds, 2),
        "val_f1_macro": round(val_f1, 4),
        "test_f1_macro": round(test_f1, 4),
        "n_train": len(X_train),
        "n_val": len(X_val),
        "n_test": len(X_test),
    }
    joblib.dump(pipe, output_path)

    # Write a side-by-side metrics file for auditability.
    (output_path.parent / "metrics.json").write_text(
        json.dumps(
            {**pipe._metadata, "classification_report": report},  # type: ignore[attr-defined]
            indent=2, default=str,
        )
    )

    logger.info(
        "training.done",
        val_f1=round(val_f1, 4),
        test_f1=round(test_f1, 4),
        fit_seconds=round(fit_seconds, 2),
        output=str(output_path),
    )

    return {
        "val_f1_macro": val_f1,
        "test_f1_macro": test_f1,
        "fit_seconds": fit_seconds,
        "output_path": str(output_path),
        "classification_report": report,
    }


def run_training_job(
    *,
    job_id: str,
    data_source: str,
    min_samples: int,
    promote_if_better: bool,
) -> None:
    """Background-task wrapper around train_model()."""
    logger.info("training.job_started", job_id=job_id, data_source=data_source)
    try:
        # In a real deployment we'd export from MySQL here.
        data_path = Path("data/raw/tickets.csv")
        result = train_model(data_path)
        logger.info(
            "training.job_completed",
            job_id=job_id,
            test_f1=round(result["test_f1_macro"], 4),
            promoted=promote_if_better,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("training.job_failed", job_id=job_id, error=str(exc))
