"""
Inference singleton.

`TicketPredictor.from_disk(path)` loads the joblib artifact once and exposes
`predict_one` / `predict_many`. The predictor is held on `app.state` so all
worker requests reuse the same in-memory model — no per-request file IO.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import joblib
import numpy as np

from app.core.exceptions import ModelNotLoadedError
from app.core.logging import get_logger
from app.ml.preprocessing import preprocess, preprocess_many

logger = get_logger(__name__)


class TicketPredictor:
    """Thin wrapper around a fitted sklearn Pipeline."""

    def __init__(self, pipeline, classes: List[str], version: str = "unknown"):
        self._pipeline = pipeline
        self.classes = list(classes)
        self.version = version

    # ------------------------------------------------------------------ load
    @classmethod
    def from_disk(cls, path: str | Path) -> "TicketPredictor":
        path = Path(path)
        if not path.exists():
            raise ModelNotLoadedError(
                f"Model artifact not found at {path}. Run `python scripts/train_model.py` first."
            )

        pipeline = joblib.load(path)
        meta = getattr(pipeline, "_metadata", {}) or {}
        version = meta.get("version", "unknown")
        classes = list(pipeline.classes_)
        logger.info("predictor.loaded", path=str(path), version=version, classes=classes)
        return cls(pipeline=pipeline, classes=classes, version=version)

    # --------------------------------------------------------------- predict
    def predict_one(self, text: str) -> dict:
        cleaned = preprocess(text) or text
        proba = self._pipeline.predict_proba([cleaned])[0]
        return self._format_single(proba)

    def predict_many(self, texts: List[str]) -> List[dict]:
        cleaned = preprocess_many(texts)
        cleaned = [c or t for c, t in zip(cleaned, texts)]
        probas = self._pipeline.predict_proba(cleaned)
        return [self._format_single(p) for p in probas]

    # --------------------------------------------------------------- helpers
    def _format_single(self, proba: np.ndarray) -> dict:
        top_idx = int(np.argmax(proba))
        category = self.classes[top_idx]
        confidence = float(proba[top_idx])

        order = np.argsort(proba)[::-1][:3]
        top_3: List[Tuple[str, float]] = [
            (self.classes[int(i)], float(proba[int(i)])) for i in order
        ]
        return {
            "predicted_category": category,
            "confidence": confidence,
            "top_3": top_3,
        }
