import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from tests.helpers import professor_auth

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _h():
    headers, _ = professor_auth(client)
    return headers


def test_list_office_hours_starts_empty():
    response = client.get("/office-hours/", headers=_h())

    assert response.status_code == 200
    assert response.json() == []


def test_create_and_list_office_hours_windows():
    headers = _h()
    first = client.post(
        "/office-hours/",
        headers=headers,
        json={
            "day": "Wednesday",
            "start": "14:00",
            "end": "15:30",
            "location": "Zoom",
        },
    )
    second = client.post(
        "/office-hours/",
        headers=headers,
        json={
            "day": "Monday",
            "start": "10:00",
            "end": "11:30",
            "location": "Room 204",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201

    listed = client.get("/office-hours/", headers=headers).json()
    assert [window["day"] for window in listed] == ["Monday", "Wednesday"]
    assert listed[0]["location"] == "Room 204"
    assert listed[1]["location"] == "Zoom"


def test_create_office_hours_defaults_location():
    response = client.post(
        "/office-hours/",
        headers=_h(),
        json={
            "day": "Friday",
            "start": "09:00",
            "end": "10:00",
            "location": "   ",
        },
    )

    assert response.status_code == 201
    assert response.json()["location"] == "TBD"


def test_delete_office_hours_window():
    headers = _h()
    created = client.post(
        "/office-hours/",
        headers=headers,
        json={
            "day": "Tuesday",
            "start": "13:00",
            "end": "14:00",
            "location": "Room 101",
        },
    ).json()

    delete_response = client.delete(f"/office-hours/{created['id']}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get("/office-hours/", headers=headers).json() == []


def test_delete_missing_office_hours_window_returns_404():
    response = client.delete("/office-hours/999", headers=_h())

    assert response.status_code == 404
