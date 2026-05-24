"""
Evaluation helpers — confusion matrix, per-class report, drift detection.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix


def per_class_report(y_true: Iterable, y_pred: Iterable) -> pd.DataFrame:
    """Return a DataFrame with per-class precision / recall / F1 / support."""
    report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
    rows = {k: v for k, v in report.items() if isinstance(v, dict) and k not in {"accuracy"}}
    df = pd.DataFrame(rows).T.reset_index().rename(columns={"index": "class"})
    return df


def confusion_df(y_true: Iterable, y_pred: Iterable, labels: list[str] | None = None) -> pd.DataFrame:
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    return pd.DataFrame(cm, index=labels, columns=labels)


def drift_score(reference_tokens: list[str], current_tokens: list[str]) -> float:
    """
    Crude vocabulary-overlap drift score in [0, 1] where 0 = identical
    distributions and 1 = no overlap. For production use a KS test on
    embedding distances or PSI on individual features.
    """
    ref = set(reference_tokens)
    cur = set(current_tokens)
    if not ref or not cur:
        return 1.0
    overlap = len(ref & cur) / len(ref | cur)
    return float(1.0 - overlap)
