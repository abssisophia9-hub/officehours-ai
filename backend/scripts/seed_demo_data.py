"""
Seed the local backend database with synthetic finals-week demo requests.

Run from `backend/`:
    python3 scripts/seed_demo_data.py --reset --limit 20
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite:///./officehours.db")
os.environ.setdefault("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")

from app.ai.clustering import assign_cluster_id
from app.database.session import Base, SessionLocal, engine
from app.models.action import RecommendationDecision
from app.models.knowledge import KnowledgeEntry
from app.models.request import Request
from app.services.classification_service import classify_and_recommend
from app.services.knowledge_service import create_pending_entry_from_request


def load_synthetic_rows(data_dir: Path = DATA_DIR) -> list[dict[str, str]]:
    synthetic_path = data_dir / "synthetic_requests.csv"
    labeled_path = data_dir / "labeled_requests.csv"

    labeled_by_id = {}
    with labeled_path.open(newline="") as labeled_file:
        for row in csv.DictReader(labeled_file):
            labeled_by_id[row["request_id"]] = row

    rows = []
    with synthetic_path.open(newline="") as synthetic_file:
        for row in csv.DictReader(synthetic_file):
            label = labeled_by_id.get(row["request_id"], {})
            rows.append({**row, **{f"label_{key}": value for key, value in label.items()}})

    return rows


def seed_demo_data(*, reset: bool = False, limit: int | None = None) -> int:
    Base.metadata.create_all(bind=engine)
    rows = load_synthetic_rows()
    if limit is not None:
        rows = rows[:limit]

    db = SessionLocal()
    try:
        if reset:
            db.query(RecommendationDecision).delete()
            db.query(KnowledgeEntry).delete()
            db.query(Request).delete()
            db.commit()

        created_count = 0
        for row in rows:
            if _request_exists(db, row["text"]):
                continue

            classification = classify_and_recommend(row["text"])
            existing_requests = db.query(Request).order_by(Request.id).all()
            cluster_id = assign_cluster_id(row["text"], existing_requests)
            anonymous = row["submission_type"] == "anonymous"

            request = Request(
                text=row["text"],
                anonymous=anonymous,
                student_id=None if anonymous else row["request_id"].replace("FS", "117"),
                category=str(classification["category"]),
                urgency=str(classification.get("urgency") or "medium"),
                cluster_id=cluster_id,
                recommended_action=str(classification["recommended_action"]),
            )
            db.add(request)
            db.commit()
            db.refresh(request)
            create_pending_entry_from_request(
                db,
                request,
                urgency=str(classification.get("urgency") or "medium"),
                matched_keywords=list(classification.get("matched_keywords") or []),
            )
            created_count += 1

        return created_count
    finally:
        db.close()


def _request_exists(db, text: str) -> bool:
    return db.query(Request).filter(Request.text == text).first() is not None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed OfficeHours AI demo data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing requests/action decisions before seeding.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Seed only the first N synthetic requests.",
    )
    parser.add_argument(
        "--clustering-backend",
        choices=["lexical", "sentence-transformers"],
        default=os.getenv("OFFICEHOURS_CLUSTERING_BACKEND", "lexical"),
        help="Use lexical for fast demos or sentence-transformers for semantic clustering.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = args.clustering_backend
    created_count = seed_demo_data(reset=args.reset, limit=args.limit)
    print(f"Seeded {created_count} demo requests.")
    print(f"Database URL: {os.getenv('DATABASE_URL')}")
    print(f"Clustering backend: {os.getenv('OFFICEHOURS_CLUSTERING_BACKEND')}")


if __name__ == "__main__":
    main()
