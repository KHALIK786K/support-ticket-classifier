"""
scikit-learn Pipeline factory.

We expose a `build_pipeline()` function that returns a fresh, untrained
sklearn Pipeline. Keeping this in one place means training, evaluation,
and tests all use exactly the same definition.
"""
from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def build_pipeline(
    model_type: str = "logreg",
    *,
    max_features: int = 20_000,
    ngram_range: tuple[int, int] = (1, 2),
    C: float = 4.0,
) -> Pipeline:
    """
    Build the classification pipeline.

    Parameters
    ----------
    model_type : str
        "logreg" or "random_forest".
    """
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=ngram_range,
        sublinear_tf=True,
        min_df=2,
        max_df=0.95,
    )

    if model_type == "logreg":
        clf = LogisticRegression(
            C=C,
            max_iter=1000,
            class_weight="balanced",
            n_jobs=-1,
            solver="liblinear",
        )
    elif model_type == "random_forest":
        from sklearn.ensemble import RandomForestClassifier

        clf = RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced",
            n_jobs=-1,
            random_state=42,
        )
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

    return Pipeline(
        steps=[
            ("tfidf", vectorizer),
            ("clf", clf),
        ]
    )
