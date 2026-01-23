"""Internationalization helpers for prompt coaching."""

from __future__ import annotations

import re
from typing import Any


DEFAULT_LANGUAGE = "en"


def detect_language(prompt: str | None) -> str:
    """
    Detect prompt language.

    Logic:
    - Korean character ratio > 30% -> "ko"
    - Otherwise -> "en"
    """
    if not prompt:
        return DEFAULT_LANGUAGE

    korean_chars = len(re.findall(r"[\uac00-\ud7a3]", prompt))
    letter_chars = len(re.findall(r"[A-Za-z\uac00-\ud7a3]", prompt))
    if letter_chars == 0:
        return DEFAULT_LANGUAGE

    ratio = korean_chars / letter_chars
    return "ko" if ratio > 0.3 else "en"


TRANSLATIONS: dict[str, dict[str, str]] = {
    "ko": {
        "analysis.title": "🤖 프롬프트 분석 결과",
        "analysis.structure": "구조",
        "analysis.context": "맥락",
        "analysis.scores": "점수",
        "analysis.problems": "문제점",
        "analysis.suggestions": "개선 제안",
        "analysis.expected_impact": "예상 효과",
        "analysis.extension_suggestion": "확장 기능 제안",
        "analysis.user_insights": "사용자 인사이트",
        "scores.value": "{label}: {score}/10",
        "problems.no_target": "구체적 대상 없음",
        "problems.no_context": "배경 정보 부족",
        "problems.conversational": "대화형 프롬프트",
        "problems.no_file": "파일 경로 없음",
        "problems.no_error": "에러 메시지 없음",
        "problems.no_target.impact": "코드 생성량 -60%",
        "problems.no_context.impact": "재작업 증가",
        "problems.conversational.impact": "대화 횟수 증가",
        "problems.no_file.impact": "수정 범위 불명확",
        "problems.no_error.impact": "디버깅 효율 저하",
        "problems.no_target.fix": "파일명이나 모듈명을 명시하세요",
        "problems.no_context.fix": "현재 상황과 배경을 설명하세요",
        "problems.conversational.fix": "독립적인 요청으로 작성하세요",
        "problems.no_file.fix": "관련 파일 경로를 추가하세요",
        "problems.no_error.fix": "에러 메시지/로그를 포함하세요",
        "suggestions.add_file": "파일 경로를 명시하세요",
        "suggestions.add_context": "배경 정보를 추가하세요",
        "suggestions.add_error": "에러 메시지를 포함하세요",
        "suggestions.user_pattern": "당신의 베스트 패턴: {pattern}",
        "suggestions.generic": "기본 개선안",
        "insights.file_strength": "파일 경로 포함 시 효율성 +{value}%",
        "insights.file_weakness": "파일 경로 포함 비율이 낮습니다",
        "insights.error_strength": "에러 메시지 포함 시 성공률 +{value}%",
        "insights.error_weakness": "에러 메시지 포함 비율이 낮습니다",
        "insights.keep": "계속 유지하세요!",
        "insights.improve": "다음부터 포함해 보세요",
        "extensions.recommend": "{extension} 제안",
        "extensions.reason": "이유: {reason}",
    },
    "en": {
        "analysis.title": "🤖 Prompt Analysis",
        "analysis.structure": "Structure",
        "analysis.context": "Context",
        "analysis.scores": "Scores",
        "analysis.problems": "Issues",
        "analysis.suggestions": "Suggestions",
        "analysis.expected_impact": "Expected Impact",
        "analysis.extension_suggestion": "Extension Suggestion",
        "analysis.user_insights": "User Insights",
        "scores.value": "{label}: {score}/10",
        "problems.no_target": "No specific target",
        "problems.no_context": "Lacking context",
        "problems.conversational": "Conversational prompt",
        "problems.no_file": "No file path",
        "problems.no_error": "No error message",
        "problems.no_target.impact": "Code generation -60%",
        "problems.no_context.impact": "Higher rework",
        "problems.conversational.impact": "More back-and-forth",
        "problems.no_file.impact": "Unclear scope",
        "problems.no_error.impact": "Lower debugging efficiency",
        "problems.no_target.fix": "Specify file or module name",
        "problems.no_context.fix": "Describe background and current state",
        "problems.conversational.fix": "Write a standalone request",
        "problems.no_file.fix": "Add relevant file paths",
        "problems.no_error.fix": "Include error messages/logs",
        "suggestions.add_file": "Specify the file path",
        "suggestions.add_context": "Add background details",
        "suggestions.add_error": "Include the error message",
        "suggestions.user_pattern": "Your best pattern: {pattern}",
        "suggestions.generic": "General improvement",
        "insights.file_strength": "Including file paths improves efficiency by {value}%",
        "insights.file_weakness": "Low rate of including file paths",
        "insights.error_strength": "Including error messages improves success by {value}%",
        "insights.error_weakness": "Low rate of including error messages",
        "insights.keep": "Keep it up!",
        "insights.improve": "Try adding it next time",
        "extensions.recommend": "{extension} suggestion",
        "extensions.reason": "Reason: {reason}",
    },
}


def t(key: str, lang: str | None = None, **kwargs: Any) -> str:
    """
    Translate a key to localized text.

    Args:
        key: Translation key like "analysis.title"
        lang: Language code ("ko" or "en"); if None, try detect_language
        **kwargs: Formatting variables
    """
    if lang is None:
        prompt = kwargs.get("prompt")
        prompt_text = prompt if isinstance(prompt, str) else None
        lang = detect_language(prompt_text) if prompt_text is not None else DEFAULT_LANGUAGE

    translations = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])
    template = translations.get(key, key)
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
