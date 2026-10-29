"""اختبارات توليد رموز دعوة الفصول (دوال بحتة)"""
import random

from app.services.invite_codes import (
    CODE_ALPHABET,
    CODE_LENGTH,
    generate_invite_code,
    normalize_invite_code,
)


def test_code_has_expected_length_and_alphabet():
    code = generate_invite_code(random.Random(1))
    assert len(code) == CODE_LENGTH
    assert set(code) <= set(CODE_ALPHABET)


def test_alphabet_excludes_visually_ambiguous_characters():
    for ambiguous in "01OIL":
        assert ambiguous not in CODE_ALPHABET


def test_codes_are_random_enough():
    rng = random.Random(42)
    codes = {generate_invite_code(rng) for _ in range(500)}
    assert len(codes) == 500  # 31^6 احتمال — تصادم بـ 500 توليد شبه مستحيل


def test_same_seed_gives_same_code():
    assert generate_invite_code(random.Random(7)) == generate_invite_code(random.Random(7))


def test_normalize_uppercases_and_strips_separators():
    assert normalize_invite_code("  abc-234 ") == "ABC234"
    assert normalize_invite_code("k7m 2pq") == "K7M2PQ"
    assert normalize_invite_code("ABC234") == "ABC234"
