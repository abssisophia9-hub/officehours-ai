"""
Clustering logic for grouping similar requests.

The default backend uses sentence-transformers embeddings and cosine
similarity. Tests can switch to a deterministic lexical backend with
``OFFICEHOURS_CLUSTERING_BACKEND=lexical`` to avoid downloading a model.
"""

from __future__ import annotations

import math
import os
import re
from functools import lru_cache
from typing import Protocol

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_SIMILARITY_THRESHOLD = 0.72


class ExistingRequest(Protocol):
    id: int
    text: str
    cluster_id: int | None


def assign_cluster_id(
    text: str,
    existing_requests: list[ExistingRequest],
    *,
    similarity_threshold: float | None = None,
) -> int:
    """
    Assign a cluster ID by comparing the new request to existing requests.

    If no existing request is similar enough, this starts the next cluster.
    """
    threshold = similarity_threshold or _similarity_threshold()
    existing_requests = [request for request in existing_requests if request.text.strip()]

    if not existing_requests:
        return 1

    new_embedding = embed_text(text)
    best_request = None
    best_similarity = -1.0

    for request in existing_requests:
        similarity = cosine_similarity(new_embedding, embed_text(request.text))
        if similarity > best_similarity:
            best_similarity = similarity
            best_request = request

    if best_request is not None and best_similarity >= threshold:
        return best_request.cluster_id or _next_cluster_id(existing_requests)

    return _next_cluster_id(existing_requests)


def embed_text(text: str) -> list[float]:
    backend = os.getenv("OFFICEHOURS_CLUSTERING_BACKEND", "sentence-transformers")

    if backend == "lexical":
        return _lexical_embedding(text)

    return _sentence_transformer_embedding(text)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))

    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0

    return dot_product / (left_norm * right_norm)


@lru_cache(maxsize=1)
def _sentence_transformer_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(os.getenv("OFFICEHOURS_EMBEDDING_MODEL", DEFAULT_MODEL_NAME))


def _sentence_transformer_embedding(text: str) -> list[float]:
    embedding = _sentence_transformer_model().encode(text, normalize_embeddings=True)
    return [float(value) for value in embedding]


def _lexical_embedding(text: str) -> list[float]:
    tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    vocabulary = (
        "recursion",
        "binary",
        "search",
        "graph",
        "dijkstra",
        "exam",
        "final",
        "project",
        "grade",
        "stress",
        "panic",
        "office",
        "hours",
        "accommodation",
        "retake",
        "makeup",
    )
    return [1.0 if token in tokens else 0.0 for token in vocabulary]


def _next_cluster_id(existing_requests: list[ExistingRequest]) -> int:
    existing_cluster_ids = [
        request.cluster_id
        for request in existing_requests
        if request.cluster_id is not None
    ]
    return (max(existing_cluster_ids) if existing_cluster_ids else 0) + 1


def _similarity_threshold() -> float:
    return float(
        os.getenv(
            "OFFICEHOURS_CLUSTER_SIMILARITY_THRESHOLD",
            str(DEFAULT_SIMILARITY_THRESHOLD),
        )
    )
