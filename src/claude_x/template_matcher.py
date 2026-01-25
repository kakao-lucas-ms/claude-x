"""Template matching engine for prompt enhancement.

This module provides functionality to:
1. Detect enhancement triggers ("고도화해서", "enhance")
2. Match user prompts to best practice templates
3. Rank templates by relevance
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .best_practices import load_templates, BestPracticeTemplate
from .scoring import calculate_structure_score, calculate_context_score


# Enhancement triggers (opt-in keywords)
ENHANCEMENT_TRIGGERS_KO = [
    "고도화해서",
    "고도화",
    "개선해서",
    "더 좋게",
    "전문적으로",
    "베스트 프랙티스로",
    "잘 작성해서",
]

ENHANCEMENT_TRIGGERS_EN = [
    "enhance",
    "improve",
    "professional",
    "best practice",
    "better way",
    "properly",
]

# Intent detection patterns
INTENT_PATTERNS = {
    "fix": [
        r"수정|고치|fix|bug|error|에러|버그|오류|안[돼되]|doesn'?t work|broken",
    ],
    "create": [
        r"만들|생성|구현|추가|implement|create|add|build|new|작성",
    ],
    "explain": [
        r"설명|알려|뭐야|왜|explain|what|why|how|리뷰|review|검토",
    ],
    "refactor": [
        r"리팩토|정리|개선|clean|refactor|improve|optimize|성능",
    ],
    "find": [
        r"찾|검색|어디|find|search|where|locate",
    ],
    "test": [
        r"테스트|검증|test|verify|check|확인",
    ],
}


@dataclass
class MatchResult:
    """Result of template matching."""

    template: BestPracticeTemplate
    score: float
    match_reasons: List[str]
    detected_intent: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "template_id": self.template.id,
            "template_name": self.template.name,
            "template_name_ko": self.template.name_ko,
            "score": round(self.score, 2),
            "match_reasons": self.match_reasons,
            "detected_intent": self.detected_intent,
            "quality_boost": self.template.quality_boost,
            "tags": self.template.tags,
        }


class TemplateMatcher:
    """Matches user prompts to best practice templates."""

    def __init__(self):
        """Initialize the matcher."""
        self._templates: List[BestPracticeTemplate] = []
        self._loaded = False

    def _ensure_loaded(self):
        """Ensure templates are loaded."""
        if not self._loaded:
            self._templates = load_templates()
            self._loaded = True

    def detect_enhancement_trigger(self, prompt: str) -> Tuple[bool, str]:
        """Detect if user wants prompt enhancement.

        Args:
            prompt: User's input prompt

        Returns:
            Tuple of (trigger_detected, cleaned_prompt)
        """
        prompt_lower = prompt.lower()
        cleaned = prompt

        # Check Korean triggers
        for trigger in ENHANCEMENT_TRIGGERS_KO:
            if trigger in prompt_lower:
                # Remove the trigger from prompt
                cleaned = re.sub(
                    rf'\s*[>→]?\s*{re.escape(trigger)}',
                    '',
                    prompt,
                    flags=re.IGNORECASE
                ).strip()
                return True, cleaned

        # Check English triggers
        for trigger in ENHANCEMENT_TRIGGERS_EN:
            pattern = rf'\b{re.escape(trigger)}\b'
            if re.search(pattern, prompt_lower):
                cleaned = re.sub(
                    rf'\s*[>→]?\s*{pattern}',
                    '',
                    prompt,
                    flags=re.IGNORECASE
                ).strip()
                return True, cleaned

        return False, prompt

    def detect_intent(self, prompt: str) -> str:
        """Detect the intent of a prompt.

        Args:
            prompt: User's input prompt

        Returns:
            Detected intent (fix, create, explain, refactor, find, test)
        """
        prompt_lower = prompt.lower()

        intent_scores = {}
        for intent, patterns in INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, prompt_lower)
                score += len(matches)
            if score > 0:
                intent_scores[intent] = score

        if not intent_scores:
            return "explain"  # Default intent

        return max(intent_scores, key=intent_scores.get)

    def _calculate_match_score(
        self,
        template: BestPracticeTemplate,
        prompt: str,
        detected_intent: str,
    ) -> Tuple[float, List[str]]:
        """Calculate how well a template matches a prompt.

        Args:
            template: Template to evaluate
            prompt: User's prompt
            detected_intent: Detected intent from prompt

        Returns:
            Tuple of (score, match_reasons)
        """
        score = 0.0
        reasons = []
        prompt_lower = prompt.lower()

        # Intent match (high weight)
        if template.intent == detected_intent:
            score += 3.0
            reasons.append(f"Intent match: {detected_intent}")

        # Trigger keyword match
        trigger_matches = 0
        for trigger in template.triggers:
            if trigger.lower() in prompt_lower:
                trigger_matches += 1

        if trigger_matches > 0:
            score += min(trigger_matches * 1.5, 4.5)  # Max 4.5 points
            reasons.append(f"Keyword matches: {trigger_matches}")

        # Tag relevance
        tag_matches = 0
        for tag in template.tags:
            if tag.lower() in prompt_lower:
                tag_matches += 1

        if tag_matches > 0:
            score += min(tag_matches * 0.5, 1.5)  # Max 1.5 points
            reasons.append(f"Tag matches: {tag_matches}")

        # Quality boost consideration
        # Higher quality_boost templates get slight preference
        score += template.quality_boost * 0.1

        return score, reasons

    def find_best_templates(
        self,
        prompt: str,
        limit: int = 3,
        intent_filter: Optional[str] = None,
    ) -> List[MatchResult]:
        """Find the best matching templates for a prompt.

        Args:
            prompt: User's input prompt
            limit: Maximum number of templates to return
            intent_filter: Optional intent to filter by

        Returns:
            List of MatchResult sorted by score (descending)
        """
        self._ensure_loaded()

        # Detect intent from prompt
        detected_intent = intent_filter or self.detect_intent(prompt)

        results = []
        for template in self._templates:
            # Filter by intent if specified
            if intent_filter and template.intent != intent_filter:
                continue

            score, reasons = self._calculate_match_score(
                template, prompt, detected_intent
            )

            # Only include templates with some relevance
            if score > 1.0:
                results.append(MatchResult(
                    template=template,
                    score=score,
                    match_reasons=reasons,
                    detected_intent=detected_intent,
                ))

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:limit]

    def get_quality_gap(self, prompt: str) -> dict:
        """Analyze the quality gap between current prompt and best practices.

        Args:
            prompt: User's prompt

        Returns:
            Dictionary with current scores and potential improvement
        """
        # Score current prompt using scoring functions
        current_structure = calculate_structure_score(prompt)
        current_context = calculate_context_score(prompt)

        # Find best matching template
        matches = self.find_best_templates(prompt, limit=1)

        if not matches:
            return {
                "current_structure": current_structure,
                "current_context": current_context,
                "potential_boost": 0,
                "recommendation": "No matching template found",
            }

        best_match = matches[0]
        potential_boost = best_match.template.quality_boost

        return {
            "current_structure": current_structure,
            "current_context": current_context,
            "potential_structure": min(
                10.0,
                current_structure + potential_boost * 0.6
            ),
            "potential_context": min(
                10.0,
                current_context + potential_boost * 0.4
            ),
            "potential_boost": potential_boost,
            "best_template": best_match.template.id,
            "match_score": best_match.score,
        }


# Singleton instance
_matcher: Optional[TemplateMatcher] = None


def get_matcher() -> TemplateMatcher:
    """Get the singleton TemplateMatcher instance."""
    global _matcher
    if _matcher is None:
        _matcher = TemplateMatcher()
    return _matcher


def detect_enhancement_trigger(prompt: str) -> Tuple[bool, str]:
    """Detect if user wants prompt enhancement.

    Args:
        prompt: User's input prompt

    Returns:
        Tuple of (trigger_detected, cleaned_prompt)
    """
    return get_matcher().detect_enhancement_trigger(prompt)


def find_best_templates(
    prompt: str,
    limit: int = 3,
    intent_filter: Optional[str] = None,
) -> List[MatchResult]:
    """Find the best matching templates for a prompt.

    Args:
        prompt: User's input prompt
        limit: Maximum number of templates to return
        intent_filter: Optional intent to filter by

    Returns:
        List of MatchResult sorted by score (descending)
    """
    return get_matcher().find_best_templates(prompt, limit, intent_filter)


def get_quality_gap(prompt: str) -> dict:
    """Analyze the quality gap between current prompt and best practices.

    Args:
        prompt: User's prompt

    Returns:
        Dictionary with current scores and potential improvement
    """
    return get_matcher().get_quality_gap(prompt)
