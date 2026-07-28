#!/usr/bin/env python3
"""Train the custom Synthesizer style-ranker (no external LLM).

Teaching bank: data/synthesizer_teaching_bank.csv
  columns: entry_id, category, learning_style, topic, student_hint,
           teaching_approach, source

Usage (from backend/):
  venv/bin/python scripts/train_synthesizer.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ai.synthesizer_model import (  # noqa: E402
    DEFAULT_MODEL_PATH,
    load_synthesizer,
    load_teaching_bank,
    save_synthesizer,
    train_synthesizer_ranker,
)
from app.ai.ml_classifier import _load_embedder  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Train OfficeHours Synthesizer model")
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="Optional single bank CSV (default: base + CSC supplement)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_MODEL_PATH)
    args = parser.parse_args()

    rows = load_teaching_bank(args.data)
    if len(rows) < 8:
        raise SystemExit(f"Need at least 8 teaching-bank entries, found {len(rows)}")

    # Train style ranker on topic + category + approach text as proxy questions.
    texts = [
        f"{row.get('topic', '')} {row.get('category', '')} {row.get('teaching_approach', '')}"
        for row in rows
    ]
    styles = [row["learning_style"].strip() for row in rows]
    bundle = train_synthesizer_ranker(texts, styles)
    path = save_synthesizer(bundle, args.out)
    load_synthesizer.cache_clear()
    _load_embedder.cache_clear()

    print(
        json.dumps(
            {
                "model_path": str(path),
                "bank_n": len(rows),
                "styles": sorted(set(styles)),
                "categories": sorted({row.get("category", "").strip() for row in rows}),
                "topics_sample": sorted({row.get("topic", "").strip() for row in rows})[:12],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
