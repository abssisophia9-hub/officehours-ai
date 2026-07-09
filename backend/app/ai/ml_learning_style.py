"""
Trainable learning-style classifier.

Uses cue-count + character n-gram features (not the clustering embedding
vocabulary) so training works under OFFICEHOURS_CLUSTERING_BACKEND=lexical.
"""

from __future__ import annotations

import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer, LabelEncoder, StandardScaler

from app.ai.learning_style import LEARNING_STYLES, STYLE_CUES

DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parents[2] / "models" / "learning_style_classifier.joblib"
)


def classify_learning_style_ml(text: str) -> dict[str, object]:
    model_path = Path(
        os.getenv("OFFICEHOURS_LEARNING_STYLE_MODEL", str(DEFAULT_MODEL_PATH))
    )
    if not model_path.exists():
        from app.ai.learning_style import infer_learning_style_rules

        payload = infer_learning_style_rules(text)
        payload["learning_style_backend"] = "ml_fallback_rules"
        return payload

    artifact = joblib.load(model_path)
    pipeline: Pipeline = artifact["pipeline"]
    label_encoder: LabelEncoder = artifact["label_encoder"]
    predicted = pipeline.predict([text])[0]
    probabilities = pipeline.predict_proba([text])[0]
    style = str(label_encoder.inverse_transform([predicted])[0])
    confidence = float(max(probabilities))
    return {
        "learning_style": style if style in LEARNING_STYLES else "unknown",
        "learning_style_confidence": round(confidence, 4),
        "learning_style_cues": [],
        "learning_style_backend": "ml",
    }


def train_learning_style_classifier(
    texts: list[str],
    labels: list[str],
    *,
    model_path: Path | None = None,
) -> dict[str, object]:
    if len(texts) < 8:
        raise ValueError("Need at least 8 labeled examples to train.")

    label_encoder = LabelEncoder()
    encoded = label_encoder.fit_transform(labels)

    pipeline = Pipeline(
        steps=[
            (
                "features",
                FeatureUnion(
                    [
                        (
                            "cues",
                            Pipeline(
                                [
                                    (
                                        "extract",
                                        FunctionTransformer(
                                            _cue_feature_matrix,
                                            validate=False,
                                        ),
                                    ),
                                    ("scale", StandardScaler()),
                                ]
                            ),
                        ),
                        (
                            "tfidf",
                            TfidfVectorizer(
                                analyzer="char_wb",
                                ngram_range=(3, 5),
                                min_df=1,
                                max_features=2000,
                            ),
                        ),
                    ]
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                ),
            ),
        ]
    )

    n_splits = min(5, int(min(np.bincount(encoded))))
    if n_splits < 2:
        pipeline.fit(texts, encoded)
        cv_scores = np.array([pipeline.score(texts, encoded)])
    else:
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        cv_scores = cross_val_score(pipeline, texts, encoded, cv=cv)
        pipeline.fit(texts, encoded)

    destination = model_path or DEFAULT_MODEL_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipeline, "label_encoder": label_encoder}, destination)

    return {
        "model_path": str(destination),
        "n_examples": len(texts),
        "labels": sorted(set(labels)),
        "cv_accuracy_mean": float(np.mean(cv_scores)),
        "cv_accuracy_std": float(np.std(cv_scores)),
    }


def _cue_feature_matrix(texts) -> np.ndarray:
    rows = []
    for text in texts:
        normalized = " ".join(str(text).lower().split())
        rows.append(
            [float(sum(1 for cue in cues if cue in normalized)) for cues in STYLE_CUES.values()]
        )
    return np.asarray(rows, dtype=float)
