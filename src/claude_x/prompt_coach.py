"""Prompt coaching engine for analysis and improvement suggestions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import re

from .analytics import PromptAnalytics
from .extensions import detect_installed_extensions, suggest_extension_command
from .i18n import detect_language, t
from .patterns import analyze_prompt_for_pattern
from .scoring import calculate_structure_score, calculate_context_score


@dataclass
class CoachingResult:
    """Prompt coaching result."""

    language: str
    original_prompt: str
    scores: Dict
    problems: List[Dict]
    suggestions: List[Dict]
    extension_suggestion: Optional[Dict]
    expected_impact: Dict
    user_insights: List[Dict]


class PromptCoach:
    """Prompt coaching engine."""

    def __init__(self, analytics: PromptAnalytics):
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

        return CoachingResult(
            language=lang,
            original_prompt=prompt,
            scores=scores,
            problems=problems,
            suggestions=suggestions,
            extension_suggestion=extension_suggestion,
            expected_impact=expected_impact,
            user_insights=user_insights,
        )

    def identify_problems(self, prompt: str, scores: Dict, lang: str) -> List[Dict]:
        """Identify prompt problems based on heuristics and scores."""
        problems: List[Dict] = []
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
        problems: List[Dict],
        user_best: List[Dict],
        lang: str,
    ) -> List[Dict]:
        """Generate improvement suggestions."""
        suggestions: List[Dict] = []

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

    def calculate_expected_impact(self, current_scores: Dict) -> Dict:
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

    def generate_user_insights(self, user_best: List[Dict], lang: str) -> List[Dict]:
        """Generate user-specific insights based on best prompts."""
        if not user_best:
            return []

        file_ratio = _ratio(user_best, _has_file_path)
        error_ratio = _ratio(user_best, _has_error_message)

        insights: List[Dict] = []
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

    def _get_user_best_prompts(self) -> List[Dict]:
        try:
            return self.analytics.get_best_prompts(limit=5, strict_mode=True)
        except Exception:
            return []

    def _problem(self, key: str, severity: str, lang: str) -> Dict:
        return {
            "issue": key,
            "severity": severity,
            "description": t(f"problems.{key}", lang),
            "impact": t(f"problems.{key}.impact", lang),
            "how_to_fix": t(f"problems.{key}.fix", lang),
        }

    def _suggestion_from_issue(self, issue_key: Optional[str], lang: str) -> Optional[Dict]:
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


def _has_file_path(prompt: str) -> bool:
    if not prompt:
        return False
    return bool(re.search(r"[\w./-]+\.(tsx?|jsx?|py|go|rs|java|vue|svelte|css|scss)", prompt))


def _has_error_keywords(prompt: str) -> bool:
    if not prompt:
        return False
    return bool(re.search(r"error|exception|traceback|stack\s*trace|에러|오류|버그|실패|bug", prompt, re.IGNORECASE))


def _has_error_message(prompt: str) -> bool:
    if not prompt:
        return False
    return bool(re.search(r"(TypeError|ReferenceError|SyntaxError|Exception|Traceback|stack\s*trace|에러|오류):", prompt))


def _is_conversational(prompt: str) -> bool:
    if not prompt:
        return False
    patterns = [
        r"^(응|그래|알겠|좋아|ok|okay|ㅇㅇ|ㄱㄱ)",
        r"그거|이거|저거|아까|방금",
    ]
    return any(re.search(p, prompt.strip(), re.IGNORECASE) for p in patterns)


def _ratio(prompts: List[Dict], predicate) -> float:
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
