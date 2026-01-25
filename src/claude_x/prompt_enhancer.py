"""Prompt enhancement engine using best practice templates.

This module provides functionality to:
1. Apply best practice templates to prompts
2. Extract and manage placeholders
3. Generate before/after comparisons
4. Create LLM-friendly enhancement results
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .best_practices import BestPracticeTemplate, get_template_by_id
from .template_matcher import (
    detect_enhancement_trigger,
    find_best_templates,
    get_quality_gap,
    MatchResult,
)
from .scoring import calculate_structure_score, calculate_context_score
from .pack_search import search_packs, SearchResult


@dataclass
class PlaceholderInfo:
    """Information about a placeholder in a template."""

    name: str
    description: str
    description_ko: Optional[str]
    required: bool
    example: str
    current_value: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "description_ko": self.description_ko,
            "required": self.required,
            "example": self.example,
            "current_value": self.current_value,
            "filled": self.current_value is not None,
        }


@dataclass
class ExternalReference:
    """A reference from external template packs."""

    pack_id: str
    pack_name: str
    title: str
    content: str
    source_url: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "pack_id": self.pack_id,
            "pack_name": self.pack_name,
            "title": self.title,
            "content": self.content,
            "source_url": self.source_url,
        }


@dataclass
class EnhancementResult:
    """Result of prompt enhancement."""

    original_prompt: str
    enhanced_prompt: str
    template_used: Optional[BestPracticeTemplate]
    match_score: float
    original_scores: Dict[str, float]
    expected_scores: Dict[str, float]
    placeholders_remaining: List[PlaceholderInfo]
    placeholders_filled: List[PlaceholderInfo]
    before_after_comparison: str
    llm_summary: str
    auto_execute_hint: bool = False  # If true, prompt can be executed as-is
    external_references: List[ExternalReference] = field(default_factory=list)  # RAG results

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "original_prompt": self.original_prompt,
            "enhanced_prompt": self.enhanced_prompt,
            "template_used": self.template_used.id if self.template_used else None,
            "template_name": self.template_used.name if self.template_used else None,
            "template_name_ko": (
                self.template_used.name_ko if self.template_used else None
            ),
            "match_score": round(self.match_score, 2),
            "original_scores": {
                k: round(v, 2) for k, v in self.original_scores.items()
            },
            "expected_scores": {
                k: round(v, 2) for k, v in self.expected_scores.items()
            },
            "improvement": {
                "structure": f"+{self.expected_scores['structure'] - self.original_scores['structure']:.1f}",
                "context": f"+{self.expected_scores['context'] - self.original_scores['context']:.1f}",
            },
            "placeholders_remaining": [p.to_dict() for p in self.placeholders_remaining],
            "placeholders_filled": [p.to_dict() for p in self.placeholders_filled],
            "before_after_comparison": self.before_after_comparison,
            "llm_summary": self.llm_summary,
            "auto_execute_hint": self.auto_execute_hint,
            "external_references": [ref.to_dict() for ref in self.external_references],
        }


class PromptEnhancer:
    """Enhances prompts using best practice templates."""

    # Language detection patterns
    KOREAN_PATTERN = re.compile(r'[\uac00-\ud7af]')

    def __init__(self):
        """Initialize the enhancer."""
        pass

    def _detect_language(self, text: str) -> str:
        """Detect primary language of text.

        Args:
            text: Text to analyze

        Returns:
            'ko' for Korean, 'en' for English
        """
        if self.KOREAN_PATTERN.search(text):
            return 'ko'
        return 'en'

    def _extract_context_from_prompt(self, prompt: str) -> Dict[str, Optional[str]]:
        """Extract context clues from the user's prompt.

        Args:
            prompt: User's original prompt

        Returns:
            Dictionary of placeholder names to extracted values
        """
        context = {}

        # Try to extract file paths (e.g., @file.py or /path/to/file)
        file_pattern = r'@?[\w./\-]+\.(py|ts|tsx|js|jsx|java|go|rs|cpp|c|h|yaml|yml|json|md)'
        file_matches = re.findall(file_pattern, prompt, re.IGNORECASE)
        if file_matches:
            # Get the full path from the original prompt
            full_match = re.search(
                r'@?([\w./\-]+\.(?:py|ts|tsx|js|jsx|java|go|rs|cpp|c|h|yaml|yml|json|md))',
                prompt,
                re.IGNORECASE
            )
            if full_match:
                context['FILE_PATH'] = full_match.group(1)

        # Try to extract error messages (text in backticks or after "에러" / "error")
        error_pattern = r'(?:에러|error|오류)[:\s]*[`\'"]?([^`\'"]+)[`\'"]?'
        error_match = re.search(error_pattern, prompt, re.IGNORECASE)
        if error_match:
            context['ERROR_MESSAGE'] = error_match.group(1).strip()

        # Try to extract function/component names
        name_pattern = r'(?:함수|function|컴포넌트|component|클래스|class)\s+[`\'"]?(\w+)[`\'"]?'
        name_match = re.search(name_pattern, prompt, re.IGNORECASE)
        if name_match:
            context['COMPONENT_NAME'] = name_match.group(1)
            context['FEATURE_NAME'] = name_match.group(1)

        return context

    def _apply_template(
        self,
        template: BestPracticeTemplate,
        original_prompt: str,
        language: str,
        extracted_context: Dict[str, Optional[str]],
    ) -> Tuple[str, List[PlaceholderInfo], List[PlaceholderInfo]]:
        """Apply a template to create an enhanced prompt.

        Args:
            template: Template to apply
            original_prompt: User's original prompt
            language: Target language ('ko' or 'en')
            extracted_context: Context extracted from original prompt

        Returns:
            Tuple of (enhanced_prompt, remaining_placeholders, filled_placeholders)
        """
        # Get template text in the appropriate language
        template_text = template.template.get(language, template.template.get('en', ''))

        remaining = []
        filled = []

        # Process each placeholder
        for placeholder in template.placeholders:
            placeholder_pattern = rf'\[{placeholder.name}\]'
            value = extracted_context.get(placeholder.name)

            info = PlaceholderInfo(
                name=placeholder.name,
                description=placeholder.description,
                description_ko=placeholder.description_ko,
                required=placeholder.required,
                example=placeholder.example,
                current_value=value,
            )

            if value:
                # Replace with extracted value
                template_text = re.sub(placeholder_pattern, value, template_text)
                filled.append(info)
            else:
                # Mark as remaining with example
                replacement = f"[{placeholder.name}: {placeholder.example}]"
                template_text = re.sub(placeholder_pattern, replacement, template_text)
                remaining.append(info)

        return template_text, remaining, filled

    def _generate_comparison(
        self,
        original: str,
        enhanced: str,
        original_scores: Dict[str, float],
        expected_scores: Dict[str, float],
        language: str,
    ) -> str:
        """Generate a before/after comparison text.

        Args:
            original: Original prompt
            enhanced: Enhanced prompt
            original_scores: Scores of original prompt
            expected_scores: Expected scores after enhancement
            language: Language for the comparison

        Returns:
            Formatted comparison text
        """
        if language == 'ko':
            return f"""## Before (원래 프롬프트)
```
{original}
```
- 구조 점수: {original_scores['structure']:.1f}/10
- 맥락 점수: {original_scores['context']:.1f}/10

## After (고도화된 프롬프트)
```
{enhanced[:500]}{'...' if len(enhanced) > 500 else ''}
```
- 예상 구조 점수: {expected_scores['structure']:.1f}/10 (+{expected_scores['structure'] - original_scores['structure']:.1f})
- 예상 맥락 점수: {expected_scores['context']:.1f}/10 (+{expected_scores['context'] - original_scores['context']:.1f})"""
        else:
            return f"""## Before (Original Prompt)
```
{original}
```
- Structure Score: {original_scores['structure']:.1f}/10
- Context Score: {original_scores['context']:.1f}/10

## After (Enhanced Prompt)
```
{enhanced[:500]}{'...' if len(enhanced) > 500 else ''}
```
- Expected Structure Score: {expected_scores['structure']:.1f}/10 (+{expected_scores['structure'] - original_scores['structure']:.1f})
- Expected Context Score: {expected_scores['context']:.1f}/10 (+{expected_scores['context'] - original_scores['context']:.1f})"""

    def _generate_llm_summary(
        self,
        template: BestPracticeTemplate,
        remaining_placeholders: List[PlaceholderInfo],
        filled_placeholders: List[PlaceholderInfo],
        improvement: Dict[str, float],
        language: str,
    ) -> str:
        """Generate an LLM-friendly summary.

        Args:
            template: Template that was applied
            remaining_placeholders: Placeholders that need to be filled
            filled_placeholders: Placeholders that were auto-filled
            improvement: Score improvements
            language: Language for the summary

        Returns:
            LLM-friendly summary text
        """
        template_name = template.name_ko if language == 'ko' else template.name

        if language == 'ko':
            summary_parts = [
                f"'{template_name}' 템플릿을 적용하여 프롬프트를 고도화했습니다.",
                f"예상 품질 향상: 구조 +{improvement['structure']:.1f}, 맥락 +{improvement['context']:.1f}",
            ]

            if filled_placeholders:
                filled_names = [p.name for p in filled_placeholders]
                summary_parts.append(
                    f"자동 추출된 정보: {', '.join(filled_names)}"
                )

            if remaining_placeholders:
                required = [p for p in remaining_placeholders if p.required]
                if required:
                    required_names = [p.name for p in required]
                    summary_parts.append(
                        f"채워야 할 필수 항목: {', '.join(required_names)}"
                    )
                    summary_parts.append(
                        "위 항목을 채우면 더 정확한 응답을 받을 수 있습니다."
                    )
            else:
                summary_parts.append(
                    "모든 필수 정보가 채워졌습니다. 바로 실행 가능합니다."
                )

            return "\n".join(summary_parts)
        else:
            summary_parts = [
                f"Applied '{template_name}' template to enhance the prompt.",
                f"Expected quality improvement: Structure +{improvement['structure']:.1f}, Context +{improvement['context']:.1f}",
            ]

            if filled_placeholders:
                filled_names = [p.name for p in filled_placeholders]
                summary_parts.append(
                    f"Auto-extracted information: {', '.join(filled_names)}"
                )

            if remaining_placeholders:
                required = [p for p in remaining_placeholders if p.required]
                if required:
                    required_names = [p.name for p in required]
                    summary_parts.append(
                        f"Required fields to fill: {', '.join(required_names)}"
                    )
                    summary_parts.append(
                        "Fill in the above for more accurate responses."
                    )
            else:
                summary_parts.append(
                    "All required information is filled. Ready to execute."
                )

            return "\n".join(summary_parts)

    def _generate_reference_summary(
        self,
        references: List[ExternalReference],
        language: str,
    ) -> str:
        """Generate a summary of external references.

        Args:
            references: List of external references found
            language: Language for the summary

        Returns:
            Summary text for LLM
        """
        if not references:
            return ""

        if language == 'ko':
            lines = ["📚 외부 팩에서 관련 자료를 찾았습니다:"]
            for ref in references[:3]:
                lines.append(f"  • [{ref.pack_name}] {ref.title}")
            lines.append("위 자료를 참고하면 더 좋은 결과를 얻을 수 있습니다.")
        else:
            lines = ["📚 Found related resources from external packs:"]
            for ref in references[:3]:
                lines.append(f"  • [{ref.pack_name}] {ref.title}")
            lines.append("Reference these resources for better results.")

        return "\n".join(lines)

    def enhance(
        self,
        prompt: str,
        template_id: Optional[str] = None,
        auto_detect_trigger: bool = True,
    ) -> EnhancementResult:
        """Enhance a prompt using best practice templates.

        Args:
            prompt: User's input prompt
            template_id: Optional specific template ID to use
            auto_detect_trigger: Whether to check for enhancement triggers

        Returns:
            EnhancementResult with enhanced prompt and metadata
        """
        # Check for enhancement trigger if enabled
        original_prompt = prompt
        if auto_detect_trigger:
            triggered, cleaned_prompt = detect_enhancement_trigger(prompt)
            if triggered:
                prompt = cleaned_prompt

        # Detect language
        language = self._detect_language(prompt)

        # Get original scores
        original_scores = {
            'structure': calculate_structure_score(prompt),
            'context': calculate_context_score(prompt),
        }

        # Find or get template
        template: Optional[BestPracticeTemplate] = None
        match_score = 0.0

        if template_id:
            template = get_template_by_id(template_id)
            match_score = 10.0  # Manual selection = perfect match
        else:
            matches = find_best_templates(prompt, limit=1)
            if matches:
                template = matches[0].template
                match_score = matches[0].score

        # If no template found, return minimal enhancement
        if not template:
            return EnhancementResult(
                original_prompt=original_prompt,
                enhanced_prompt=prompt,
                template_used=None,
                match_score=0.0,
                original_scores=original_scores,
                expected_scores=original_scores,
                placeholders_remaining=[],
                placeholders_filled=[],
                before_after_comparison="No matching template found.",
                llm_summary="No suitable template was found for this prompt.",
                auto_execute_hint=True,
            )

        # Extract context from original prompt
        extracted_context = self._extract_context_from_prompt(prompt)

        # Apply template
        enhanced_prompt, remaining, filled = self._apply_template(
            template, prompt, language, extracted_context
        )

        # Calculate expected scores
        quality_boost = template.quality_boost
        expected_scores = {
            'structure': min(10.0, original_scores['structure'] + quality_boost * 0.6),
            'context': min(10.0, original_scores['context'] + quality_boost * 0.4),
        }

        # Calculate improvement
        improvement = {
            'structure': expected_scores['structure'] - original_scores['structure'],
            'context': expected_scores['context'] - original_scores['context'],
        }

        # Generate comparison
        comparison = self._generate_comparison(
            original_prompt, enhanced_prompt, original_scores, expected_scores, language
        )

        # Generate LLM summary
        llm_summary = self._generate_llm_summary(
            template, remaining, filled, improvement, language
        )

        # Check if auto-executable (no required placeholders remaining)
        required_remaining = [p for p in remaining if p.required]
        auto_execute = len(required_remaining) == 0

        # Search external packs for related content (RAG)
        external_refs = []
        try:
            search_results = search_packs(prompt, limit=3)
            for result in search_results:
                external_refs.append(ExternalReference(
                    pack_id=result.pack_id,
                    pack_name=result.pack_name,
                    title=result.title,
                    content=result.content,
                    source_url=result.source_url,
                ))
        except Exception:
            pass  # Silently fail if pack search fails

        # Update LLM summary with external references
        if external_refs:
            ref_summary = self._generate_reference_summary(external_refs, language)
            llm_summary = f"{llm_summary}\n\n{ref_summary}"

        return EnhancementResult(
            original_prompt=original_prompt,
            enhanced_prompt=enhanced_prompt,
            template_used=template,
            match_score=match_score,
            original_scores=original_scores,
            expected_scores=expected_scores,
            placeholders_remaining=remaining,
            placeholders_filled=filled,
            before_after_comparison=comparison,
            llm_summary=llm_summary,
            auto_execute_hint=auto_execute,
            external_references=external_refs,
        )


# Singleton instance
_enhancer: Optional[PromptEnhancer] = None


def get_enhancer() -> PromptEnhancer:
    """Get the singleton PromptEnhancer instance."""
    global _enhancer
    if _enhancer is None:
        _enhancer = PromptEnhancer()
    return _enhancer


def enhance_prompt(
    prompt: str,
    template_id: Optional[str] = None,
    auto_detect_trigger: bool = True,
) -> EnhancementResult:
    """Enhance a prompt using best practice templates.

    Args:
        prompt: User's input prompt
        template_id: Optional specific template ID to use
        auto_detect_trigger: Whether to check for enhancement triggers

    Returns:
        EnhancementResult with enhanced prompt and metadata
    """
    return get_enhancer().enhance(prompt, template_id, auto_detect_trigger)
