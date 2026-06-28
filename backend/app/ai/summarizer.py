"""
Lightweight NLP utilities for summarizing request clusters.
"""

from __future__ import annotations

import re
from collections import Counter

STOP_WORDS = {
    "about",
    "after",
    "again",
    "because",
    "before",
    "can",
    "could",
    "final",
    "for",
    "from",
    "have",
    "help",
    "how",
    "need",
    "please",
    "question",
    "should",
    "that",
    "the",
    "this",
    "what",
    "when",
    "where",
    "with",
    "would",
}


def summarize_request_cluster(texts: list[str], *, max_keywords: int = 4) -> dict[str, object]:
    keywords = extract_keywords(texts, max_keywords=max_keywords)
    title = build_cluster_title(keywords)

    return {
        "title": title,
        "keywords": keywords,
        "request_count": len(texts),
    }


def extract_keywords(texts: list[str], *, max_keywords: int = 4) -> list[str]:
    cleaned_texts = [text.strip() for text in texts if text.strip()]
    if not cleaned_texts:
        return []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=24,
        )
        matrix = vectorizer.fit_transform(cleaned_texts)
        scores = matrix.sum(axis=0).A1
        features = vectorizer.get_feature_names_out()
        ranked = sorted(zip(features, scores), key=lambda item: item[1], reverse=True)
        return [keyword for keyword, _ in ranked[:max_keywords]]
    except Exception:
        return _fallback_keywords(cleaned_texts, max_keywords=max_keywords)


def build_cluster_title(keywords: list[str]) -> str:
    if not keywords:
        return "Student support follow-up"

    return " / ".join(keyword.title() for keyword in keywords[:3])


def _fallback_keywords(texts: list[str], *, max_keywords: int) -> list[str]:
    tokens = re.findall(r"[a-z][a-z0-9-]{2,}", " ".join(texts).lower())
    counts = Counter(token for token in tokens if token not in STOP_WORDS)
    return [token for token, _ in counts.most_common(max_keywords)]
