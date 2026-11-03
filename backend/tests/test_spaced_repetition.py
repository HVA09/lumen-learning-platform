"""
اختبارات خوارزمية SM-2+ (وحدة منطقية بحتة) + مسارات /srs
"""
from datetime import datetime, timezone

from app.models.review_card import CardState, ReviewCard
from app.services.spaced_repetition import (
    LAPSE_EASE_PENALTY,
    LEECH_THRESHOLD,
    MAX_EASE_FACTOR,
    MAX_INTERVAL_DAYS,
    review_card,
)
from tests.quiz_helpers import auth, make_student, topic_id_by_slug


def _fresh_card() -> ReviewCard:
    return ReviewCard(
        user_id=1, front_text="س", back_text="ج",
        state=CardState.new, ease_factor=2.5, interval_days=0, repetitions=0, lapses=0,
    )


def test_first_good_review_moves_to_learning_with_short_interval():
    card = _fresh_card()
    result = review_card(card, "good")
    assert result is card
    assert card.state == CardState.learning
    assert card.interval_days == 1
    assert card.repetitions == 1


def test_card_graduates_to_review_after_enough_good_reviews():
    card = _fresh_card()
    review_card(card, "good")  # 1: learning, 1 يوم
    review_card(card, "good")  # 2: learning، 3 أيام
    review_card(card, "good")  # 3: يتخرّج لـ review
    assert card.state == CardState.review
    assert card.repetitions == 3


def test_again_resets_repetitions_and_shortens_interval():
    card = _fresh_card()
    review_card(card, "good")
    review_card(card, "good")
    review_card(card, "good")  # صار review
    assert card.state == CardState.review

    review_card(card, "again")
    assert card.state == CardState.relearning
    assert card.repetitions == 0
    assert card.interval_days == 1
    assert card.lapses == 1


def test_ease_factor_never_drops_below_1_3():
    card = _fresh_card()
    card.ease_factor = 1.3
    for _ in range(20):
        review_card(card, "good")
    assert card.ease_factor >= 1.3


def test_easy_grows_ease_factor_more_than_good():
    card_good = _fresh_card()
    card_easy = _fresh_card()
    for _ in range(3):  # تخرّج الاثنتين لـ review أول
        review_card(card_good, "good")
        review_card(card_easy, "good")

    review_card(card_good, "good")
    review_card(card_easy, "easy")
    assert card_easy.ease_factor > card_good.ease_factor


def test_leech_flagged_after_threshold_lapses():
    card = _fresh_card()
    for _ in range(LEECH_THRESHOLD):
        review_card(card, "again")
    assert card.is_leech is True
    assert card.lapses == LEECH_THRESHOLD


def test_due_at_is_set_in_the_future_relative_to_now():
    card = _fresh_card()
    now = datetime.now(timezone.utc)
    review_card(card, "good", now=now)
    assert card.due_at > now


def _register_and_login(client, email="srsuser@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    return login_response.cookies.get("lumen_access")


def test_create_and_list_cards(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/srs/cards", json={"front_text": "ما ناتج 2+2؟", "back_text": "4"}, headers=headers
    )
    assert response.status_code == 201
    assert response.json()["state"] == "new"

    listed = client.get("/srs/cards", headers=headers)
    assert len(listed.json()) == 1


def test_new_card_is_immediately_due(client):
    token = _register_and_login(client, "duenow@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/srs/cards", json={"front_text": "س", "back_text": "ج"}, headers=headers)

    due = client.get("/srs/due", headers=headers)
    assert len(due.json()) == 1


def test_review_endpoint_updates_card_state(client):
    token = _register_and_login(client, "reviewer@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    card = client.post(
        "/srs/cards", json={"front_text": "س", "back_text": "ج"}, headers=headers
    ).json()

    response = client.post(f"/srs/cards/{card['id']}/review", json={"grade": "good"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["state"] == "learning"
    assert response.json()["repetitions"] == 1


def test_cannot_review_other_users_card(client):
    token_a = _register_and_login(client, "cardowner@example.com")
    card = client.post(
        "/srs/cards", json={"front_text": "س", "back_text": "ج"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()

    token_b = _register_and_login(client, "cardintruder@example.com")
    response = client.post(
        f"/srs/cards/{card['id']}/review", json={"grade": "good"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_export_then_import_csv_roundtrip(client):
    token = _register_and_login(client, "csvcards@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/srs/cards", json={"front_text": "سؤال أول", "back_text": "جواب أول"}, headers=headers)

    exported = client.get("/srs/export.csv", headers=headers)
    assert exported.status_code == 200
    assert "front_text" in exported.text

    token2 = _register_and_login(client, "csvimporter@example.com")
    headers2 = {"Authorization": f"Bearer {token2}"}
    files = {"file": ("cards.csv", exported.text, "text/csv")}
    imported = client.post("/srs/import.csv", files=files, headers=headers2)
    assert imported.status_code == 200
    assert len(imported.json()) == 1
    assert imported.json()[0]["front_text"] == "سؤال أول"


def test_import_csv_rejects_missing_columns(client):
    token = _register_and_login(client, "badcsv@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("bad.csv", "wrong_column\nvalue", "text/csv")}
    response = client.post("/srs/import.csv", files=files, headers=headers)
    assert response.status_code == 422


def test_srs_requires_authentication(client):
    assert client.get("/srs/cards").status_code == 401
    assert client.get("/srs/due").status_code == 401


# ---------- تحسينات الخوارزمية ----------

def _review_card_after_graduation() -> ReviewCard:
    card = _fresh_card()
    for _ in range(3):
        review_card(card, "good")
    return card


def test_again_lowers_ease_factor():
    card = _review_card_after_graduation()
    before = card.ease_factor
    review_card(card, "again")
    assert card.ease_factor == before - LAPSE_EASE_PENALTY


def test_easy_multiplies_interval_more_than_good():
    good_card = _review_card_after_graduation()
    easy_card = _review_card_after_graduation()
    review_card(good_card, "good")
    review_card(easy_card, "easy")
    assert easy_card.interval_days > good_card.interval_days


def test_interval_always_grows_even_with_minimum_ease_factor():
    card = _review_card_after_graduation()
    card.ease_factor = 1.3
    card.interval_days = 2
    review_card(card, "good")
    assert card.interval_days == 3  # التقريب لوحده كان يخليه 3 أصلًا، لكن الشرط يضمن +1 دائمًا
    card.interval_days = 1
    review_card(card, "good")
    assert card.interval_days == 2  # بدون الشرط: round(1 * 1.3) = 1 (يعلق)


def test_interval_and_ease_factor_are_capped():
    card = _review_card_after_graduation()
    for _ in range(60):
        review_card(card, "easy")
    assert card.interval_days == MAX_INTERVAL_DAYS
    assert card.ease_factor <= MAX_EASE_FACTOR


# ---------- مجموعات البطاقات الجاهزة ----------

def test_decks_require_authentication(client):
    assert client.get("/srs/decks").status_code == 401
    assert client.post("/srs/decks/1/add").status_code == 401


def test_decks_list_seeded_starter_cards(client):
    token = make_student(client, "deckreader@example.com")
    response = client.get("/srs/decks", headers=auth(token))
    assert response.status_code == 200
    decks = response.json()
    assert len(decks) >= 5
    assert all(d["total_cards"] == 6 for d in decks)
    assert all(d["added_cards"] == 0 for d in decks)
    assert any(d["topic_name_ar"] == "المعادلات الخطية" for d in decks)


def test_adding_a_deck_copies_cards_once(client):
    token = make_student(client, "deckadder@example.com")
    headers = auth(token)
    topic_id = topic_id_by_slug(client, "linear-equations")

    first = client.post(f"/srs/decks/{topic_id}/add", headers=headers)
    assert first.status_code == 200
    assert first.json() == {"added": 6, "total": 6}

    second = client.post(f"/srs/decks/{topic_id}/add", headers=headers)
    assert second.json() == {"added": 0, "total": 6}  # ما تتكرر البطاقات

    cards = client.get("/srs/cards", headers=headers).json()
    assert len(cards) == 6
    assert all(c["topic_id"] == topic_id for c in cards)

    decks = client.get("/srs/decks", headers=headers).json()
    linear = next(d for d in decks if d["topic_id"] == topic_id)
    assert linear["added_cards"] == 6
    other = next(d for d in decks if d["topic_id"] != topic_id)
    assert other["added_cards"] == 0

    due = client.get("/srs/due", headers=headers).json()
    assert len(due) == 6  # تدخل جدول المراجعة مباشرة


def test_adding_deck_for_unknown_topic_404(client):
    token = make_student(client, "deck404@example.com")
    assert client.post("/srs/decks/999999/add", headers=auth(token)).status_code == 404


def test_reviewing_a_card_records_study_day(client):
    token = make_student(client, "studyday@example.com")
    headers = auth(token)
    card = client.post("/srs/cards", json={"front_text": "س", "back_text": "ج"}, headers=headers).json()
    assert client.get("/gamification/my-stats", headers=headers).json()["studied_today"] is False

    client.post(f"/srs/cards/{card['id']}/review", json={"grade": "good"}, headers=headers)
    stats = client.get("/gamification/my-stats", headers=headers).json()
    assert stats["studied_today"] is True
    assert stats["streak_days"] == 1
