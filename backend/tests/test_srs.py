"""Security and boundary tests for spaced-repetition endpoints."""

from app.models.topic import Topic
from app.routers.srs import MAX_SRS_CSV_IMPORT_BYTES


def _register_and_login(client, email="srs-security@example.com"):
    registered = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123"},
    )
    assert registered.status_code == 201
    login = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_due_cards_limit_is_bounded(client):
    headers = _register_and_login(client)

    assert client.get("/srs/due?limit=0", headers=headers).status_code == 422
    assert client.get("/srs/due?limit=101", headers=headers).status_code == 422
    assert client.get("/srs/due?limit=100", headers=headers).status_code == 200


def test_import_csv_rejects_file_over_byte_limit(client):
    headers = _register_and_login(client, "srs-large-file@example.com")
    payload = b"x" * (MAX_SRS_CSV_IMPORT_BYTES + 1)

    response = client.post(
        "/srs/import.csv",
        headers=headers,
        files={"file": ("large.csv", payload, "text/csv")},
    )

    assert response.status_code == 413


def test_import_csv_rejects_more_than_500_cards(client):
    headers = _register_and_login(client, "srs-large-rows@example.com")
    rows = ["front_text,back_text"]
    rows.extend(f"front-{index},back-{index}" for index in range(501))
    payload = "\n".join(rows).encode("utf-8")

    response = client.post(
        "/srs/import.csv",
        headers=headers,
        files={"file": ("many.csv", payload, "text/csv")},
    )

    assert response.status_code == 413
    assert client.get("/srs/cards", headers=headers).json() == []


def test_import_csv_rejects_overlong_card_fields(client):
    headers = _register_and_login(client, "srs-long-field@example.com")
    payload = ("front_text,back_text\n" + ("x" * 2001) + ",back").encode("utf-8")

    response = client.post(
        "/srs/import.csv",
        headers=headers,
        files={"file": ("long.csv", payload, "text/csv")},
    )

    assert response.status_code == 422
    assert client.get("/srs/cards", headers=headers).json() == []


def test_import_csv_rejects_unknown_topic_before_creating_cards(client):
    headers = _register_and_login(client, "srs-unknown-topic@example.com")
    payload = b"front_text,back_text,topic_id\nquestion,answer,999999999"

    response = client.post(
        "/srs/import.csv",
        headers=headers,
        files={"file": ("unknown-topic.csv", payload, "text/csv")},
    )

    assert response.status_code == 422
    assert client.get("/srs/cards", headers=headers).json() == []


def test_import_csv_accepts_valid_utf8_cards_and_existing_topic(client, db_session):
    headers = _register_and_login(client, "srs-valid-import@example.com")
    topic = db_session.query(Topic).first()
    assert topic is not None
    payload = (
        "front_text,back_text,topic_id\n"
        f"ما هو DNS؟,نظام أسماء النطاقات,{topic.id}"
    ).encode("utf-8")

    response = client.post(
        "/srs/import.csv",
        headers=headers,
        files={"file": ("cards.csv", payload, "text/csv")},
    )

    assert response.status_code == 200
    cards = response.json()
    assert len(cards) == 1
    assert cards[0]["front_text"] == "ما هو DNS؟"
    assert cards[0]["topic_id"] == topic.id
