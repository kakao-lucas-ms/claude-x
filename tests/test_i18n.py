"""Tests for i18n helpers."""

from claude_x.i18n import detect_language, t


def test_detect_language_korean():
    assert detect_language("이 버그 수정해줘") == "ko"


def test_detect_language_english():
    assert detect_language("fix this bug") == "en"


def test_detect_language_mixed():
    assert detect_language("버그 fix") == "ko"


def test_translation_korean():
    assert t("analysis.title", "ko") == "🤖 프롬프트 분석 결과"


def test_translation_english():
    assert t("analysis.title", "en") == "🤖 Prompt Analysis"


def test_translation_formatting():
    text = t("scores.value", "en", label="Structure", score=7.5)
    assert text == "Structure: 7.5/10"
