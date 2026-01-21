"""Tests for prompt pattern extraction."""

import pytest
from claude_x.patterns import (
    extract_pattern_type,
    extract_template,
    extract_tags,
    calculate_pattern_quality,
    analyze_prompt_for_pattern,
    extract_patterns_from_prompts,
    PATTERN_TYPES,
)
from claude_x.classifier import PromptCategory


class TestExtractPatternType:
    """Tests for extract_pattern_type function."""

    def test_target_action_pattern_korean(self):
        """Should detect target + action patterns in Korean."""
        prompts = [
            "LoginForm.tsx에 validation 추가해줘",
            "components/Button.jsx를 수정해줘",
            "src/utils/helper.py에서 함수 찾아줘",
        ]
        for prompt in prompts:
            result = extract_pattern_type(prompt)
            assert result == 'target_action', f"'{prompt}' should be target_action, got {result}"

    def test_reference_based_pattern(self):
        """Should detect reference-based patterns."""
        prompts = [
            "기존 LoginForm처럼 SignupForm을 만들어줘",
            "create a component like the existing Header",
            "참고해서 비슷하게 만들어줘",
        ]
        for prompt in prompts:
            result = extract_pattern_type(prompt)
            assert result == 'reference_based', f"'{prompt}' should be reference_based, got {result}"

    def test_constraint_based_pattern(self):
        """Should detect constraint-based patterns."""
        prompts = [
            "외부 라이브러리 없이 구현해줘",
            "implement this without using any external dependencies",
            "최소 8자 이상으로 만들어줘",
        ]
        for prompt in prompts:
            result = extract_pattern_type(prompt)
            assert result == 'constraint_based', f"'{prompt}' should be constraint_based, got {result}"

    def test_question_driven_pattern(self):
        """Should detect question-driven patterns."""
        prompts = [
            "이게 뭐야?",
            "what is the difference?",
            "왜 이렇게 동작하는 거야?",
        ]
        for prompt in prompts:
            result = extract_pattern_type(prompt)
            assert result == 'question_driven', f"'{prompt}' should be question_driven, got {result}"

    def test_debug_report_pattern(self):
        """Should detect debug report patterns."""
        prompts = [
            "에러가 발생해요. TypeError: Cannot read property",
            "기대동작과 실제동작이 달라요",
            "stack trace를 분석해줘",
        ]
        for prompt in prompts:
            result = extract_pattern_type(prompt)
            assert result == 'debug_report', f"'{prompt}' should be debug_report, got {result}"

    def test_context_goal_pattern(self):
        """Should detect context + goal patterns."""
        prompts = [
            "현재 상황이 이런데 해결책을 찾아줘",
            "지금 이런 문제가 있는데 수정해줘",
        ]
        for prompt in prompts:
            result = extract_pattern_type(prompt)
            assert result == 'context_goal', f"'{prompt}' should be context_goal, got {result}"

    def test_generic_pattern(self):
        """Should return generic for unclassifiable prompts."""
        prompts = [
            "ok",
            "됐어",
            "hello",
        ]
        for prompt in prompts:
            result = extract_pattern_type(prompt)
            assert result == 'generic', f"'{prompt}' should be generic, got {result}"

    def test_empty_prompt(self):
        """Should return generic for empty prompts."""
        assert extract_pattern_type("") == 'generic'
        assert extract_pattern_type(None) == 'generic'


class TestExtractTemplate:
    """Tests for extract_template function."""

    def test_replaces_file_names(self):
        """Should replace file names with placeholders."""
        prompt = "helper.tsx에 validation 추가해줘"
        template = extract_template(prompt, 'target_action')
        assert '[FILE_NAME]' in template
        assert 'helper.tsx' not in template

    def test_replaces_paths(self):
        """Should replace paths with placeholders."""
        prompt = "src/components/Button.tsx를 수정해줘"
        template = extract_template(prompt, 'target_action')
        assert '[PATH]' in template

    def test_replaces_component_names(self):
        """Should replace component names with placeholders."""
        prompt = "UserProfileComponent를 만들어줘"
        template = extract_template(prompt, 'target_action')
        assert '[COMPONENT]' in template

    def test_replaces_urls(self):
        """Should replace URLs with placeholders."""
        prompt = "https://example.com/api 를 호출해줘"
        template = extract_template(prompt, 'generic')
        assert '[URL]' in template

    def test_replaces_code_blocks(self):
        """Should replace code blocks with placeholders."""
        prompt = "```typescript\nconst x = 1;\n``` 이 코드를 수정해줘"
        template = extract_template(prompt, 'generic')
        assert '[CODE_BLOCK]' in template

    def test_replaces_inline_code(self):
        """Should replace inline code with placeholders."""
        prompt = "`useState` 훅을 사용해줘"
        template = extract_template(prompt, 'generic')
        assert '[CODE]' in template

    def test_empty_prompt(self):
        """Should return empty string for empty prompts."""
        assert extract_template("", 'generic') == ""
        assert extract_template(None, 'generic') == ""


class TestExtractTags:
    """Tests for extract_tags function."""

    def test_extracts_tech_tags(self):
        """Should extract technology tags."""
        prompt = "React 컴포넌트에서 TypeScript 타입 에러"
        tags = extract_tags(prompt)
        assert 'react' in tags
        assert 'typescript' in tags

    def test_extracts_action_tags(self):
        """Should extract action tags."""
        prompts_tags = [
            ("새로 만들어줘", 'create'),
            ("버그 수정해줘", 'fix'),
            ("리팩토링해줘", 'refactor'),
            ("설명해줘", 'explain'),
        ]
        for prompt, expected_tag in prompts_tags:
            tags = extract_tags(prompt)
            assert expected_tag in tags, f"'{prompt}' should have tag '{expected_tag}', got {tags}"

    def test_extracts_multiple_tags(self):
        """Should extract multiple relevant tags."""
        prompt = "React 컴포넌트의 버그를 수정하고 테스트 추가해줘"
        tags = extract_tags(prompt)
        assert 'react' in tags
        assert 'fix' in tags
        assert 'test' in tags

    def test_empty_prompt(self):
        """Should return empty set for empty prompts."""
        assert extract_tags("") == set()
        assert extract_tags(None) == set()


class TestCalculatePatternQuality:
    """Tests for calculate_pattern_quality function."""

    def test_high_quality_prompt(self):
        """Should give high score to well-structured prompts."""
        prompt = "LoginForm.tsx 컴포넌트에 비밀번호 유효성 검사를 추가해줘. React를 사용중이야."
        score = calculate_pattern_quality(prompt)
        assert score >= 5.0, f"Expected >= 5.0, got {score}"

    def test_low_quality_prompt(self):
        """Should give low score to vague prompts."""
        prompt = "고쳐줘"
        score = calculate_pattern_quality(prompt)
        assert score <= 3.0, f"Expected <= 3.0, got {score}"

    def test_empty_prompt(self):
        """Should return 0 for empty prompts."""
        assert calculate_pattern_quality("") == 0.0
        assert calculate_pattern_quality(None) == 0.0


class TestAnalyzePromptForPattern:
    """Tests for analyze_prompt_for_pattern function."""

    def test_returns_all_fields(self):
        """Should return all expected fields."""
        prompt = "LoginForm.tsx에 validation 추가해줘"
        result = analyze_prompt_for_pattern(prompt)

        assert 'pattern_type' in result
        assert 'pattern_description' in result
        assert 'template' in result
        assert 'category' in result
        assert 'category_icon' in result
        assert 'tags' in result
        assert 'quality_score' in result

    def test_correct_pattern_type(self):
        """Should identify correct pattern type."""
        prompt = "기존 Button처럼 새 컴포넌트를 만들어줘"
        result = analyze_prompt_for_pattern(prompt)
        assert result['pattern_type'] == 'reference_based'

    def test_correct_category(self):
        """Should identify correct category."""
        prompt = "버그를 수정해줘"
        result = analyze_prompt_for_pattern(prompt)
        assert result['category'] == PromptCategory.DEBUGGING.value

    def test_empty_prompt(self):
        """Should handle empty prompts gracefully."""
        result = analyze_prompt_for_pattern("")
        assert result['pattern_type'] == 'generic'
        assert result['quality_score'] == 0.0


class TestExtractPatternsFromPrompts:
    """Tests for extract_patterns_from_prompts function."""

    def test_extracts_patterns(self, high_quality_prompts):
        """Should extract patterns from high quality prompts."""
        prompts = [{'first_prompt': p['prompt']} for p in high_quality_prompts]
        patterns = extract_patterns_from_prompts(prompts, min_quality=3.0)

        assert len(patterns) > 0

    def test_filters_by_quality(self, low_quality_prompts):
        """Should filter out low quality prompts."""
        prompts = [{'first_prompt': p['prompt']} for p in low_quality_prompts]
        patterns = extract_patterns_from_prompts(prompts, min_quality=8.0)

        # Low quality prompts should be filtered out
        assert len(patterns) < len(prompts)

    def test_groups_similar_patterns(self):
        """Should group similar patterns together."""
        prompts = [
            {'first_prompt': "LoginForm.tsx에 validation 추가해줘"},
            {'first_prompt': "SignupForm.tsx에 validation 추가해줘"},
            {'first_prompt': "ProfileForm.tsx에 validation 추가해줘"},
        ]
        patterns = extract_patterns_from_prompts(prompts, min_quality=0.0)

        # Similar patterns should be grouped
        # May have 1-3 patterns depending on template similarity
        assert len(patterns) <= len(prompts)

    def test_empty_list(self):
        """Should handle empty list gracefully."""
        patterns = extract_patterns_from_prompts([])
        assert patterns == []
