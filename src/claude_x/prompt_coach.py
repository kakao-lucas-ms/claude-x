"""Prompt coaching engine for analysis and improvement suggestions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol
import re

from .extensions import detect_installed_extensions, suggest_extension_command
from .i18n import detect_language, t
from .patterns import analyze_prompt_for_pattern
from .scoring import calculate_structure_score, calculate_context_score
from .context import get_project_context, find_matching_files, summarize_task


# Helper functions for info checking (defined first for use in REQUIRED_INFO_BY_INTENT)
def _has_file_path(prompt: str) -> bool:
    """Check if prompt contains a file path."""
    if not prompt:
        return False
    return bool(re.search(r"[\w./-]+\.(tsx?|jsx?|py|go|rs|java|vue|svelte|css|scss)", prompt))


def _has_error_message(prompt: str) -> bool:
    """Check if prompt contains an error message."""
    if not prompt:
        return False
    return bool(re.search(r"(TypeError|ReferenceError|SyntaxError|Exception|Traceback|stack\s*trace|에러|오류):", prompt))


def _has_error_keywords(prompt: str) -> bool:
    """Check if prompt contains error-related keywords."""
    if not prompt:
        return False
    return bool(re.search(r"error|exception|traceback|stack\s*trace|에러|오류|버그|실패|bug", prompt, re.IGNORECASE))


def _is_conversational(prompt: str) -> bool:
    """Check if prompt is conversational (too short/vague)."""
    if not prompt:
        return False
    patterns = [
        r"^(응|그래|알겠|좋아|ok|okay|ㅇㅇ|ㄱㄱ)",
        r"그거|이거|저거|아까|방금",
    ]
    return any(re.search(p, prompt.strip(), re.IGNORECASE) for p in patterns)


# Intent detection patterns
INTENT_PATTERNS: dict[str, list[str]] = {
    "find": [
        r"찾아|검색|어디|위치|확인|보여|알려|뭐|무엇|어떤",
        r"find|search|where|show|list|what|which|check|look",
    ],
    "fix": [
        r"수정|고쳐|버그|에러|오류|해결|디버그|안[돼되]|실패",
        r"fix|bug|error|debug|broken|fail|issue|problem|resolve",
    ],
    "create": [
        r"만들어|생성|추가|새로|작성|구현",
        r"create|add|new|implement|build|make|write|generate",
    ],
    "explain": [
        r"설명|뭐야|왜|이유|어떻게|분석",
        r"explain|why|how|what is|analyze|understand|describe",
    ],
    "refactor": [
        r"리팩토링|개선|최적화|정리|변경|바꿔",
        r"refactor|improve|optimize|clean|change|update|modify",
    ],
    "test": [
        r"테스트|검증|확인해",
        r"test|verify|validate|check if",
    ],
}

# File pattern suggestions by intent
FILE_PATTERNS_BY_INTENT: dict[str, list[str]] = {
    "find": ["**/*.md", "docs/**/*", "**/*"],
    "fix": ["src/**/*.{ts,tsx,py,js}", "**/*.{ts,tsx,py,js}"],
    "create": ["src/**/*", "**/*"],
    "explain": ["**/*"],
    "refactor": ["src/**/*.{ts,tsx,py,js}"],
    "test": ["**/*.test.{ts,tsx,js}", "tests/**/*.py", "**/*_test.py"],
}


def detect_intent(prompt: str) -> str:
    """Detect the intent of a prompt."""
    prompt_lower = prompt.lower()

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, prompt_lower):
                return intent

    return "unknown"


def extract_keywords(prompt: str) -> list[str]:
    """Extract meaningful keywords from prompt for file search."""
    # Remove common words
    stopwords = {
        "해줘", "해", "줘", "좀", "이거", "저거", "그거", "뭐", "please", "the", "a", "an",
        "is", "are", "was", "were", "be", "been", "to", "of", "and", "in", "that", "it",
        "for", "on", "with", "as", "at", "by", "from", "지금", "다음", "이", "그", "저",
        "뭔지", "어디", "어떤", "확인", "보여", "알려", "확인해줘", "찾아줘", "해결해줘",
        "수정해줘", "만들어줘", "추가해줘", "설명해줘", "분석해줘",
    }

    # Korean particle patterns to strip
    korean_particles = r"(이|가|을|를|은|는|에|에서|의|와|과|로|으로|도|만|부터|까지|처럼|같이)$"

    # Extract words
    words = re.findall(r"[a-zA-Z가-힣]{2,}", prompt)

    # Clean keywords
    cleaned = []
    for w in words:
        # Skip stopwords
        if w.lower() in stopwords:
            continue
        # Remove Korean particles
        clean_word = re.sub(korean_particles, "", w)
        if len(clean_word) >= 2 and clean_word.lower() not in stopwords:
            cleaned.append(clean_word)

    return cleaned[:5]  # Top 5 keywords


def generate_improved_prompt(prompt: str, intent: str, lang: str) -> str:
    """Generate an improved version of the prompt."""
    keywords = extract_keywords(prompt)

    if intent == "find":
        if lang == "ko":
            if keywords:
                return f"@docs/ 또는 관련 폴더에서 '{' '.join(keywords)}' 관련 파일을 찾아서 내용을 확인해줘"
            return f"{prompt} - 관련 파일 경로를 명시해주세요"
        else:
            if keywords:
                return f"Search for files related to '{' '.join(keywords)}' in docs/ or relevant folders and show the content"
            return f"{prompt} - please specify the file path"

    elif intent == "fix":
        if lang == "ko":
            return f"{prompt}\n\n[에러 메시지를 여기에 붙여넣기]\n[관련 파일: src/...]"
        else:
            return f"{prompt}\n\n[Paste error message here]\n[Related file: src/...]"

    elif intent == "create":
        if lang == "ko":
            return f"{prompt}\n\n[생성 위치: src/...]\n[참고할 기존 파일: @...]"
        else:
            return f"{prompt}\n\n[Create at: src/...]\n[Reference file: @...]"

    elif intent == "explain":
        if lang == "ko":
            return f"@[파일경로] 여기서 {prompt}"
        else:
            return f"@[filepath] {prompt}"

    elif intent == "refactor":
        if lang == "ko":
            return f"@[파일경로] 에서 {prompt}\n\n[현재 문제점: ...]\n[원하는 결과: ...]"
        else:
            return f"@[filepath] {prompt}\n\n[Current issue: ...]\n[Expected result: ...]"

    elif intent == "test":
        if lang == "ko":
            return f"{prompt}\n\n[테스트 대상 파일: src/...]\n[테스트 파일 위치: tests/...]"
        else:
            return f"{prompt}\n\n[Target file: src/...]\n[Test file location: tests/...]"

    # Unknown intent - generic improvement
    if lang == "ko":
        return f"{prompt}\n\n[관련 파일: @...]\n[추가 컨텍스트: ...]"
    else:
        return f"{prompt}\n\n[Related file: @...]\n[Additional context: ...]"


def generate_recommended_actions(prompt: str, intent: str) -> list[PromptDict]:
    """Generate recommended tool actions based on intent."""
    keywords = extract_keywords(prompt)
    actions: list[PromptDict] = []

    if intent == "find":
        # Suggest Glob for file search
        patterns = FILE_PATTERNS_BY_INTENT.get(intent, ["**/*"])
        for keyword in keywords[:2]:
            actions.append({
                "tool": "Glob",
                "params": {"pattern": f"**/*{keyword}*"},
                "reason": f"'{keyword}' 관련 파일 검색",
            })

        # Suggest Grep for content search
        if keywords:
            actions.append({
                "tool": "Grep",
                "params": {"pattern": keywords[0], "path": "."},
                "reason": f"'{keywords[0]}' 키워드 검색",
            })

    elif intent == "fix":
        # Suggest reading error-related files
        actions.append({
            "tool": "Grep",
            "params": {"pattern": "error|Error|ERROR", "path": "src/"},
            "reason": "에러 관련 코드 검색",
        })
        if keywords:
            actions.append({
                "tool": "Glob",
                "params": {"pattern": f"**/*{keywords[0]}*"},
                "reason": f"'{keywords[0]}' 관련 파일 찾기",
            })

    elif intent == "create":
        # Suggest exploring existing structure
        actions.append({
            "tool": "Glob",
            "params": {"pattern": "src/**/*"},
            "reason": "기존 코드 구조 파악",
        })

    elif intent == "explain":
        if keywords:
            actions.append({
                "tool": "Grep",
                "params": {"pattern": keywords[0]},
                "reason": f"'{keywords[0]}' 정의 찾기",
            })

    elif intent == "refactor":
        if keywords:
            actions.append({
                "tool": "Grep",
                "params": {"pattern": keywords[0]},
                "reason": f"'{keywords[0]}' 사용처 찾기",
            })

    elif intent == "test":
        actions.append({
            "tool": "Glob",
            "params": {"pattern": "**/*.test.{ts,tsx,js,py}"},
            "reason": "기존 테스트 파일 확인",
        })

    # Generic: always suggest reading relevant files
    if not actions:
        actions.append({
            "tool": "Glob",
            "params": {"pattern": "**/*.md"},
            "reason": "문서 파일 확인",
        })

    return actions[:3]  # Max 3 actions


# v0.5.0: Required info by intent
REQUIRED_INFO_BY_INTENT: dict[str, list[dict[str, Any]]] = {
    "fix": [
        {
            "type": "error_message",
            "check": _has_error_message,
            "question_ko": "어떤 에러가 발생했나요?",
            "question_en": "What error are you seeing?",
            "example": "TypeError: Cannot read property 'x' of undefined",
            "required": True,
        },
        {
            "type": "file_path",
            "check": _has_file_path,
            "question_ko": "어떤 파일에서 발생했나요?",
            "question_en": "Which file is this happening in?",
            "example": "src/components/Button.tsx",
            "required": False,
        },
    ],
    "create": [
        {
            "type": "location",
            "check": lambda p: bool(re.search(r"(src/|app/|lib/|components/)", p)),
            "question_ko": "어디에 생성할까요?",
            "question_en": "Where should I create it?",
            "example": "src/components/",
            "required": False,
        },
    ],
    "refactor": [
        {
            "type": "file_path",
            "check": _has_file_path,
            "question_ko": "어떤 파일을 리팩토링할까요?",
            "question_en": "Which file should I refactor?",
            "example": "src/utils/helpers.ts",
            "required": True,
        },
    ],
    "explain": [
        {
            "type": "file_path",
            "check": _has_file_path,
            "question_ko": "어떤 파일에 대해 설명할까요?",
            "question_en": "Which file should I explain?",
            "example": "src/api/auth.ts",
            "required": False,
        },
    ],
}


def detect_missing_info(prompt: str, intent: str, lang: str) -> list[PromptDict]:
    """Detect missing required information based on intent.

    Args:
        prompt: User's prompt.
        intent: Detected intent.
        lang: Language code.

    Returns:
        List of missing info items with questions.
    """
    missing: list[PromptDict] = []
    required_items = REQUIRED_INFO_BY_INTENT.get(intent, [])

    for item in required_items:
        check_fn = item.get("check")
        if check_fn and not check_fn(prompt):
            question_key = f"question_{lang}" if lang in ("ko", "en") else "question_en"
            missing.append({
                "type": item["type"],
                "question": item.get(question_key, item.get("question_en", "")),
                "example": item.get("example", ""),
                "required": item.get("required", False),
            })

    return missing


def generate_auto_execute_hint(
    prompt: str,
    intent: str,
    actions: list[PromptDict],
    lang: str,
) -> PromptDict | None:
    """Generate auto-execute hint for Claude to act on.

    Args:
        prompt: User's prompt.
        intent: Detected intent.
        actions: Recommended actions.
        lang: Language code.

    Returns:
        Auto-execute hint dictionary or None.
    """
    if not actions:
        return None

    # Determine if auto-execute is appropriate
    # Safe intents that can auto-execute: find, explain
    safe_intents = {"find", "explain"}
    should_auto = intent in safe_intents

    if lang == "ko":
        reason = {
            "find": "사용자가 정보 조회를 요청했고, 파일 검색으로 해결 가능합니다",
            "explain": "설명을 위해 관련 코드를 먼저 확인해야 합니다",
            "fix": "버그 수정을 위해 관련 파일을 찾아야 합니다",
            "create": "생성 전 기존 구조를 파악해야 합니다",
            "refactor": "리팩토링 전 현재 코드를 확인해야 합니다",
            "test": "테스트 전 기존 테스트 파일을 확인해야 합니다",
        }.get(intent, "요청을 처리하기 위해 파일을 확인해야 합니다")
        fallback = "파일을 찾지 못하면 사용자에게 경로를 물어보세요"
    else:
        reason = {
            "find": "User requested information lookup, can be resolved with file search",
            "explain": "Need to check relevant code first to explain",
            "fix": "Need to find related files to fix the bug",
            "create": "Need to understand existing structure before creating",
            "refactor": "Need to check current code before refactoring",
            "test": "Need to check existing test files before testing",
        }.get(intent, "Need to check files to process the request")
        fallback = "If no files found, ask the user for the file path"

    # Build prioritized action list
    prioritized_actions = []
    for i, action in enumerate(actions):
        prioritized_actions.append({
            **action,
            "priority": i + 1,
            "description": action.get("reason", f"Action {i + 1}"),
        })

    return {
        "enabled": should_auto,
        "reason": reason,
        "actions": prioritized_actions,
        "fallback": fallback,
    }


def smart_rewrite(prompt: str, intent: str, lang: str) -> str:
    """Rewrite prompt using actual project file paths.

    Args:
        prompt: Original user prompt.
        intent: Detected intent.
        lang: Language code.

    Returns:
        Rewritten prompt with actual file paths or original improved prompt.
    """
    keywords = extract_keywords(prompt)

    # Get project context
    try:
        context = get_project_context()
        matching_files = find_matching_files(keywords, context)
    except Exception:
        # Fallback if context collection fails
        return generate_improved_prompt(prompt, intent, lang)

    if not matching_files:
        return generate_improved_prompt(prompt, intent, lang)

    # Use the best matching file
    best_file = matching_files[0]
    task = summarize_task(prompt)

    if lang == "ko":
        return f"@{best_file} 여기서 {task}"
    else:
        return f"@{best_file} - {task}"


@dataclass
class CoachingResult:
    """Prompt coaching result."""

    language: str
    original_prompt: str
    scores: "ScoreMap"
    problems: list["PromptDict"]
    suggestions: list["PromptDict"]
    extension_suggestion: "PromptDict | None"
    expected_impact: "ImpactDict"
    user_insights: list["PromptDict"]
    # v0.4.1: New fields for actionable coaching
    intent: str = "unknown"
    improved_prompt: str = ""
    recommended_actions: list["PromptDict"] | None = None
    # v0.5.0: Auto-execute hints, missing info, smart rewrite
    auto_execute: "PromptDict | None" = None
    missing_info: list["PromptDict"] = field(default_factory=list)
    smart_prompt: str = ""  # Project-context-aware rewrite


PromptDict = dict[str, Any]
ScoreMap = dict[str, float]
ImpactDict = dict[str, dict[str, float | int | str]]


class AnalyticsProtocol(Protocol):
    def get_best_prompts(self, *args: Any, **kwargs: Any) -> list[PromptDict]:
        ...


class PromptCoach:
    """Prompt coaching engine."""

    def __init__(self, analytics: AnalyticsProtocol):
        self.analytics = analytics

    def analyze(
        self,
        prompt: str,
        detect_extensions: bool = True,
        include_history: bool = True,
    ) -> CoachingResult:
        """Analyze a prompt and return coaching result."""
        lang = detect_language(prompt)

        scores = {
            "structure": calculate_structure_score(prompt),
            "context": calculate_context_score(prompt),
        }

        problems = self.identify_problems(prompt, scores, lang)

        user_best = self._get_user_best_prompts() if include_history else []
        suggestions = self.generate_suggestions(prompt, problems, user_best, lang)

        extension_suggestion = None
        if detect_extensions:
            installed = detect_installed_extensions()
            extension_suggestion = suggest_extension_command(prompt, installed)

        expected_impact = self.calculate_expected_impact(scores)
        user_insights = self.generate_user_insights(user_best, lang)

        # v0.4.1: Intent detection and actionable suggestions
        intent = detect_intent(prompt)
        improved_prompt = generate_improved_prompt(prompt, intent, lang)
        recommended_actions = generate_recommended_actions(prompt, intent)

        # v0.5.0: Enhanced coaching with auto-execute, missing info, smart rewrite
        auto_execute = generate_auto_execute_hint(prompt, intent, recommended_actions, lang)
        missing_info = detect_missing_info(prompt, intent, lang)
        smart_prompt = smart_rewrite(prompt, intent, lang)

        return CoachingResult(
            language=lang,
            original_prompt=prompt,
            scores=scores,
            problems=problems,
            suggestions=suggestions,
            extension_suggestion=extension_suggestion,
            expected_impact=expected_impact,
            user_insights=user_insights,
            intent=intent,
            improved_prompt=improved_prompt,
            recommended_actions=recommended_actions,
            auto_execute=auto_execute,
            missing_info=missing_info,
            smart_prompt=smart_prompt,
        )

    def identify_problems(self, prompt: str, scores: ScoreMap, lang: str) -> list[PromptDict]:
        """Identify prompt problems based on heuristics and scores."""
        problems: list[PromptDict] = []
        structure = scores.get("structure", 0)
        context = scores.get("context", 0)

        if structure < 2.0:
            problems.append(self._problem("no_target", "high", lang))

        if context < 2.0:
            problems.append(self._problem("no_context", "high", lang))

        if _is_conversational(prompt):
            problems.append(self._problem("conversational", "medium", lang))

        if not _has_file_path(prompt):
            problems.append(self._problem("no_file", "medium", lang))

        if _has_error_keywords(prompt) and not _has_error_message(prompt):
            problems.append(self._problem("no_error", "medium", lang))

        return problems

    def generate_suggestions(
        self,
        prompt: str,
        problems: list[PromptDict],
        user_best: list[PromptDict],
        lang: str,
    ) -> list[PromptDict]:
        """Generate improvement suggestions."""
        suggestions: list[PromptDict] = []

        for best in user_best[:2]:
            prompt_text = best.get("first_prompt", "")
            analysis = analyze_prompt_for_pattern(prompt_text)
            template = analysis.get("template")
            if not template:
                continue

            title = t(
                "suggestions.user_pattern",
                lang,
                pattern=analysis.get("pattern_description", "pattern"),
            )

            suggestions.append(
                {
                    "type": "user_pattern",
                    "title": title,
                    "template": template,
                    "example": prompt_text,
                    "why_successful": "",
                    "confidence": analysis.get("quality_score", 0.7),
                }
            )

        for issue in problems:
            if len(suggestions) >= 3:
                break
            issue_key = issue.get("issue")
            suggestion = self._suggestion_from_issue(issue_key, lang)
            if suggestion:
                suggestions.append(suggestion)

        if not suggestions:
            suggestions.append(
                {
                    "type": "generic",
                    "title": t("suggestions.generic", lang),
                    "template": prompt,
                    "example": prompt,
                    "confidence": 0.5,
                }
            )

        return suggestions[:3]

    def calculate_expected_impact(self, current_scores: ScoreMap) -> ImpactDict:
        """Estimate expected impact from improvements."""
        structure = current_scores.get("structure", 0.0)
        context = current_scores.get("context", 0.0)

        target_structure = min(10.0, max(7.0, structure + 3.0))
        target_context = min(10.0, max(7.0, context + 3.0))

        improvement_ratio = min(0.7, max(0.1, (target_structure + target_context - structure - context) / 20))

        current_messages = 9
        expected_messages = max(3, round(current_messages * (1 - improvement_ratio)))

        current_code = 2
        expected_code = max(1, round(current_code * (1 + improvement_ratio * 2)))

        current_success = 0.35
        expected_success = min(0.95, current_success + improvement_ratio * 0.6)

        return {
            "messages": {
                "current": current_messages,
                "expected": expected_messages,
                "improvement": _percent_change(current_messages, expected_messages, lower_is_better=True),
            },
            "code_generation": {
                "current": current_code,
                "expected": expected_code,
                "improvement": _percent_change(current_code, expected_code),
            },
            "success_rate": {
                "current": round(current_success, 2),
                "expected": round(expected_success, 2),
                "improvement": _percent_change(current_success, expected_success),
            },
        }

    def generate_user_insights(self, user_best: list[PromptDict], lang: str) -> list[PromptDict]:
        """Generate user-specific insights based on best prompts."""
        if not user_best:
            return []

        file_ratio = _ratio(user_best, _has_file_path)
        error_ratio = _ratio(user_best, _has_error_message)

        insights: list[PromptDict] = []
        if file_ratio >= 0.6:
            insights.append(
                {
                    "type": "strength",
                    "message": t("insights.file_strength", lang, value=int(file_ratio * 100)),
                    "recommendation": t("insights.keep", lang),
                }
            )
        else:
            insights.append(
                {
                    "type": "weakness",
                    "message": t("insights.file_weakness", lang),
                    "recommendation": t("insights.improve", lang),
                }
            )

        if error_ratio >= 0.4:
            insights.append(
                {
                    "type": "strength",
                    "message": t("insights.error_strength", lang, value=int(error_ratio * 100)),
                    "recommendation": t("insights.keep", lang),
                }
            )
        else:
            insights.append(
                {
                    "type": "weakness",
                    "message": t("insights.error_weakness", lang),
                    "recommendation": t("insights.improve", lang),
                }
            )

        return insights

    def _get_user_best_prompts(self) -> list[PromptDict]:
        try:
            return self.analytics.get_best_prompts(limit=5, strict_mode=True)
        except Exception:
            return []

    def _problem(self, key: str, severity: str, lang: str) -> PromptDict:
        return {
            "issue": key,
            "severity": severity,
            "description": t(f"problems.{key}", lang),
            "impact": t(f"problems.{key}.impact", lang),
            "how_to_fix": t(f"problems.{key}.fix", lang),
        }

    def _suggestion_from_issue(self, issue_key: str | None, lang: str) -> PromptDict | None:
        if issue_key == "no_file":
            return {
                "type": "generic",
                "title": t("suggestions.add_file", lang),
                "template": "[FILE]에서 [TASK]를 처리해줘",
                "example": "src/app.py에서 로그인 버그를 수정해줘",
                "confidence": 0.7,
            }
        if issue_key == "no_context":
            return {
                "type": "generic",
                "title": t("suggestions.add_context", lang),
                "template": "현재 상황: [CONTEXT]\n요청: [TASK]",
                "example": "현재 결제 버튼이 동작하지 않아. 원인을 찾아줘",
                "confidence": 0.6,
            }
        if issue_key == "no_error":
            return {
                "type": "generic",
                "title": t("suggestions.add_error", lang),
                "template": "에러 메시지: [ERROR]\n기대 동작: [EXPECTED]",
                "example": "TypeError: ... / 기대 동작: 버튼 클릭 시 결제",
                "confidence": 0.6,
            }
        return None


def _ratio(prompts: list[PromptDict], predicate: Callable[[str], bool]) -> float:
    if not prompts:
        return 0.0
    matches = 0
    for item in prompts:
        text = item.get("first_prompt", "")
        if predicate(text):
            matches += 1
    return matches / len(prompts)


def _percent_change(current: float, expected: float, lower_is_better: bool = False) -> str:
    if current == 0:
        return "N/A"

    change = (expected - current) / current
    if lower_is_better:
        change = -change

    sign = "+" if change >= 0 else ""
    return f"{sign}{int(change * 100)}%"
