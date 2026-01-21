"""Tests for prompt category classification."""

import pytest
from claude_x.classifier import (
    PromptCategory,
    classify_prompt,
    classify_prompt_with_scores,
    get_category_icon,
    get_category_description,
    legacy_to_new_category,
)


class TestClassifyPrompt:
    """Tests for classify_prompt function."""

    # Learning category tests
    def test_learning_korean_explain(self):
        """Should classify Korean explanation requests as LEARNING."""
        prompts = [
            "이 코드가 어떻게 동작하는지 설명해줘",
            "React Server Components가 뭐야",
            "useEffect와 useLayoutEffect의 차이점이 뭐야",
            "이 패턴이 뭔지 알려줘",
        ]
        for prompt in prompts:
            category = classify_prompt(prompt)
            assert category == PromptCategory.LEARNING, f"'{prompt}' should be LEARNING, got {category}"

    def test_learning_english_explain(self):
        """Should classify English explanation requests as LEARNING."""
        prompts = [
            "explain how this works",
            "what is the difference between X and Y",
            "tell me about this pattern",
            "how does authentication work",
        ]
        for prompt in prompts:
            category = classify_prompt(prompt)
            assert category == PromptCategory.LEARNING, f"'{prompt}' should be LEARNING, got {category}"

    # Implementation category tests
    def test_implementation_korean(self):
        """Should classify Korean implementation requests as IMPLEMENTATION."""
        prompts = [
            "새로운 컴포넌트를 만들어줘",
            "로그인 기능을 구현해줘",
            "API 엔드포인트를 추가해줘",
            "버튼 컴포넌트 작성해줘",
        ]
        for prompt in prompts:
            category = classify_prompt(prompt)
            assert category == PromptCategory.IMPLEMENTATION, f"'{prompt}' should be IMPLEMENTATION, got {category}"

    def test_implementation_english(self):
        """Should classify English implementation requests as IMPLEMENTATION."""
        prompts = [
            "create a new component",
            "implement login feature",
            "add a new API endpoint",
            "write a helper function",
        ]
        for prompt in prompts:
            category = classify_prompt(prompt)
            assert category == PromptCategory.IMPLEMENTATION, f"'{prompt}' should be IMPLEMENTATION, got {category}"

    # Debugging category tests
    def test_debugging_korean(self):
        """Should classify Korean debugging requests as DEBUGGING."""
        prompts = [
            "버그를 수정해줘",
            "에러가 발생하는데 고쳐줘",
            "이거 왜 안돼",
            "작동이 안됨",
            "문제를 해결해줘",
        ]
        for prompt in prompts:
            category = classify_prompt(prompt)
            assert category == PromptCategory.DEBUGGING, f"'{prompt}' should be DEBUGGING, got {category}"

    def test_debugging_english(self):
        """Should classify English debugging requests as DEBUGGING."""
        prompts = [
            "fix the bug",
            "there's an error when I click",
            "why doesn't this work",
            "debug this issue",
            "solve this problem",
        ]
        for prompt in prompts:
            category = classify_prompt(prompt)
            assert category == PromptCategory.DEBUGGING, f"'{prompt}' should be DEBUGGING, got {category}"

    # Architecture category tests
    def test_architecture_korean(self):
        """Should classify Korean architecture requests as ARCHITECTURE."""
        prompts = [
            "이 코드를 리팩토링해줘",
            "구조를 개선해줘",
            "설계 패턴을 적용해줘",
            "성능을 최적화해줘",
            "의존성을 정리해줘",
        ]
        for prompt in prompts:
            category = classify_prompt(prompt)
            assert category == PromptCategory.ARCHITECTURE, f"'{prompt}' should be ARCHITECTURE, got {category}"

    def test_architecture_english(self):
        """Should classify English architecture requests as ARCHITECTURE."""
        prompts = [
            "refactor this code",
            "improve the structure",
            "apply a design pattern",
            "optimize performance",
            "clean up dependencies",
        ]
        for prompt in prompts:
            category = classify_prompt(prompt)
            assert category == PromptCategory.ARCHITECTURE, f"'{prompt}' should be ARCHITECTURE, got {category}"

    # Efficiency category tests
    def test_efficiency_short_prompts(self):
        """Should classify very short/vague prompts as EFFICIENCY."""
        prompts = [
            "ok",
            "ㅇㅇ",
            "됐어",
            "계속",
        ]
        for prompt in prompts:
            category = classify_prompt(prompt)
            assert category == PromptCategory.EFFICIENCY, f"'{prompt}' should be EFFICIENCY, got {category}"

    def test_empty_prompt(self):
        """Should classify empty prompts as EFFICIENCY."""
        assert classify_prompt("") == PromptCategory.EFFICIENCY
        assert classify_prompt(None) == PromptCategory.EFFICIENCY


class TestClassifyPromptWithScores:
    """Tests for classify_prompt_with_scores function."""

    def test_returns_all_fields(self):
        """Should return category, confidence, and scores."""
        result = classify_prompt_with_scores("버그를 수정해줘")

        assert 'category' in result
        assert 'confidence' in result
        assert 'scores' in result
        assert isinstance(result['category'], PromptCategory)
        assert 0 <= result['confidence'] <= 1

    def test_confidence_high_for_clear_prompts(self):
        """Should have high confidence for clear prompts."""
        # Clear debugging prompt
        result = classify_prompt_with_scores("버그가 있어서 에러를 수정해줘")
        assert result['confidence'] > 0.5

    def test_scores_contain_all_categories(self):
        """Should contain scores for all categories."""
        result = classify_prompt_with_scores("테스트 프롬프트")

        for category in PromptCategory:
            assert category.value in result['scores']


class TestCategoryHelpers:
    """Tests for category helper functions."""

    def test_get_category_icon(self):
        """Should return correct icons for each category."""
        assert get_category_icon(PromptCategory.LEARNING) == "📚"
        assert get_category_icon(PromptCategory.IMPLEMENTATION) == "🔧"
        assert get_category_icon(PromptCategory.DEBUGGING) == "🐛"
        assert get_category_icon(PromptCategory.ARCHITECTURE) == "🏗️"
        assert get_category_icon(PromptCategory.EFFICIENCY) == "⚡"

    def test_get_category_description(self):
        """Should return descriptions for each category."""
        for category in PromptCategory:
            desc = get_category_description(category)
            assert desc, f"Category {category} should have a description"
            assert len(desc) > 0


class TestLegacyMapping:
    """Tests for legacy category mapping."""

    def test_legacy_to_new_category(self):
        """Should map legacy categories correctly."""
        assert legacy_to_new_category('코드 리뷰') == PromptCategory.ARCHITECTURE
        assert legacy_to_new_category('테스트') == PromptCategory.IMPLEMENTATION
        assert legacy_to_new_category('버그 수정') == PromptCategory.DEBUGGING
        assert legacy_to_new_category('기능 구현') == PromptCategory.IMPLEMENTATION
        assert legacy_to_new_category('리팩토링') == PromptCategory.ARCHITECTURE
        assert legacy_to_new_category('기타') == PromptCategory.EFFICIENCY

    def test_unknown_legacy_category(self):
        """Should return EFFICIENCY for unknown categories."""
        assert legacy_to_new_category('unknown') == PromptCategory.EFFICIENCY


class TestClassificationAccuracy:
    """Integration tests for classification accuracy."""

    def test_real_prompts_classification(self, real_prompts):
        """Should classify real prompts without errors."""
        for prompt in real_prompts:
            category = classify_prompt(prompt)
            assert isinstance(category, PromptCategory)

    def test_mixed_language_prompts(self):
        """Should handle mixed Korean/English prompts."""
        prompts = [
            "React 컴포넌트를 만들어줘",
            "TypeScript로 implement해줘",
            "이 bug를 fix해줘",
        ]
        for prompt in prompts:
            category = classify_prompt(prompt)
            assert isinstance(category, PromptCategory)
            # Should detect the intent despite mixed language
            assert category != PromptCategory.EFFICIENCY
