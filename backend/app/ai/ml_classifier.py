"""
Embedding + logistic regression request classifier trained on labeled data.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression

from app.ai.classifier import _infer_urgency, _normalize

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
DEFAULT_MODEL_PATH = MODEL_DIR / "request_classifier.joblib"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def build_classifier() -> LogisticRegression:
    return LogisticRegression(max_iter=4000, class_weight="balanced", C=3.0)


def encode_texts(texts: list[str], model_name: str = DEFAULT_EMBEDDING_MODEL) -> np.ndarray:
    embedder = SentenceTransformer(model_name)
    return np.asarray(embedder.encode(texts, show_progress_bar=False))


def train_classifier(
    texts: list[str],
    categories: list[str],
    *,
    model_name: str | None = None,
) -> dict[str, object]:
    embedding_model = model_name or os.getenv("OFFICEHOURS_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    features = encode_texts(texts, embedding_model)
    classifier = build_classifier()
    classifier.fit(features, categories)
    return {
        "embedding_model": embedding_model,
        "classifier": classifier,
        "labels": sorted(set(categories)),
        "strategy": "embedding-logreg",
    }


def save_classifier(bundle: dict[str, object], path: Path = DEFAULT_MODEL_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)
    return path


@lru_cache(maxsize=1)
def load_classifier(path: str | None = None) -> dict[str, object]:
    model_path = Path(path or os.getenv("OFFICEHOURS_CLASSIFIER_MODEL", DEFAULT_MODEL_PATH))
    if not model_path.exists():
        raise FileNotFoundError(
            f"ML classifier model not found at {model_path}. "
            "Run backend/scripts/train_classifier.py first."
        )
    return joblib.load(model_path)


@lru_cache(maxsize=2)
def _load_embedder(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def classify_ml(text: str, *, model_path: str | None = None) -> dict[str, object]:
    bundle = load_classifier(model_path)
    normalized_text = _normalize(text)
    if not normalized_text:
        return {
            "category": "uncategorized",
            "urgency": "low",
            "confidence": 0.0,
            "matched_keywords": [],
            "classifier_backend": "ml",
        }

    embedder = _load_embedder(str(bundle["embedding_model"]))
    features = np.asarray(embedder.encode([text], show_progress_bar=False))
    classifier: LogisticRegression = bundle["classifier"]
    predicted_category = str(classifier.predict(features)[0])
    probabilities = classifier.predict_proba(features)[0]
    confidence = float(max(probabilities))

    return {
        "category": predicted_category,
        "urgency": _infer_urgency(predicted_category, normalized_text),
        "confidence": round(confidence, 2),
        "matched_keywords": [],
        "classifier_backend": "ml",
    }
