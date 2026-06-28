import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"

from app.database.session import Base, SessionLocal, engine
from app.models.request import Request
from scripts.seed_demo_data import load_synthetic_rows, seed_demo_data


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_load_synthetic_rows_includes_labels():
    rows = load_synthetic_rows()

    assert len(rows) == 40
    assert rows[0]["request_id"] == "FS001"
    assert rows[0]["label_category"] == "conceptual_question"
    assert rows[0]["label_urgency"] == "medium"


def test_seed_demo_data_creates_requests_and_is_idempotent():
    first_count = seed_demo_data(reset=True, limit=3)
    second_count = seed_demo_data(reset=False, limit=3)

    db = SessionLocal()
    try:
        requests = db.query(Request).order_by(Request.id).all()
        assert first_count == 3
        assert second_count == 0
        assert len(requests) == 3
        assert requests[0].category
        assert requests[0].cluster_id is not None
    finally:
        db.close()
