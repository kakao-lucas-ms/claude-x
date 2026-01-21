"""Tests for the new scoring model."""

import pytest
from claude_x.scoring import (
    calculate_structure_score,
    calculate_context_score,
    calculate_efficiency_score,
    calculate_diversity_score,
    calculate_productivity_score,
    calculate_composite_score_v2,
)


class TestStructureScore:
    """Tests for calculate_structure_score function."""

    def test_good_structure_prompt(self):
        """Should give high score to well-structured prompts."""
        prompt = "LoginForm.tsx 컴포넌트에 비밀번호 유효성 검사 추가해줘"
        score = calculate_structure_score(prompt)
        assert score >= 4.0, f"Expected >= 4.0, got {score}"

    def test_great_structure_prompt(self):
        """Should give very high score to excellent prompts."""
        prompt = (
            "현재 src/components/LoginForm.tsx에서 비밀번호 유효성 검사를 "
            "추가해줘. 최소 8자 이상, 특수문자 포함 조건으로 해줘. "
            "기존 이메일 검증 방식처럼 만들어줘."
        )
        score = calculate_structure_score(prompt)
        assert score >= 6.0, f"Expected >= 6.0, got {score}"

    def test_poor_structure_prompt(self):
        """Should give low score to vague prompts."""
        prompt = "fix it"
        score = calculate_structure_score(prompt)
        assert score <= 3.0, f"Expected <= 3.0, got {score}"

    def test_very_short_prompt(self):
        """Should penalize very short prompts."""
        prompt = "ok"
        score = calculate_structure_score(prompt)
        assert score <= 2.0, f"Expected <= 2.0, got {score}"

    def test_empty_prompt(self):
        """Should return 0 for empty prompt."""
        assert calculate_structure_score("") == 0.0
        assert calculate_structure_score(None) == 0.0

    def test_goal_patterns_korean(self):
        """Should detect Korean goal patterns."""
        prompts = ["버그를 수정해줘", "기능을 추가해줘", "코드를 리팩토링해줘"]
        for prompt in prompts:
            score = calculate_structure_score(prompt)
            assert score >= 2.0, f"Prompt '{prompt}' should have goal detected"

    def test_goal_patterns_english(self):
        """Should detect English goal patterns."""
        prompts = ["please fix the bug", "create a new component", "implement authentication"]
        for prompt in prompts:
            score = calculate_structure_score(prompt)
            assert score >= 2.0, f"Prompt '{prompt}' should have goal detected"


class TestContextScore:
    """Tests for calculate_context_score function."""

    def test_context_rich_prompt(self):
        """Should give high score to context-rich prompts."""
        prompt = (
            "현재 React 프로젝트의 src/components/Login.tsx에서 "
            "TypeError: Cannot read property 'name' of undefined 에러가 발생해"
        )
        score = calculate_context_score(prompt)
        assert score >= 6.0, f"Expected >= 6.0, got {score}"

    def test_context_poor_prompt(self):
        """Should give low score to context-poor prompts."""
        prompt = "수정해줘"
        score = calculate_context_score(prompt)
        assert score <= 2.0, f"Expected <= 2.0, got {score}"

    def test_empty_prompt(self):
        """Should return 0 for empty prompt."""
        assert calculate_context_score("") == 0.0

    def test_file_path_detection(self):
        """Should detect file paths."""
        prompts = [
            "src/components/Button.tsx",
            "components/Header.jsx",
            "utils/helper.py",
        ]
        for prompt in prompts:
            score = calculate_context_score(prompt)
            assert score >= 2.0, f"File path in '{prompt}' should be detected"

    def test_technology_detection(self):
        """Should detect technology mentions."""
        prompts = [
            "React 컴포넌트를 만들어줘",
            "TypeScript 타입을 추가해줘",
            "GraphQL 쿼리를 작성해줘",
        ]
        for prompt in prompts:
            score = calculate_context_score(prompt)
            assert score >= 2.0, f"Tech in '{prompt}' should be detected"

    def test_code_block_detection(self):
        """Should detect code blocks."""
        prompt = "```typescript\nconst x = 1;\n```"
        score = calculate_context_score(prompt)
        assert score >= 2.0

    def test_inline_code_detection(self):
        """Should detect inline code."""
        prompt = "`useState` 훅을 사용해줘"
        score = calculate_context_score(prompt)
        assert score >= 2.0


class TestEfficiencyScore:
    """Tests for calculate_efficiency_score function."""

    def test_short_conversation(self):
        """Should give high score for short conversations."""
        assert calculate_efficiency_score(5) == 10.0
        assert calculate_efficiency_score(3) == 10.0

    def test_medium_conversation(self):
        """Should give medium score for medium conversations."""
        assert calculate_efficiency_score(20) == 8.0
        assert calculate_efficiency_score(50) == 5.0

    def test_long_conversation(self):
        """Should give low score for long conversations."""
        assert calculate_efficiency_score(100) == 3.0
        assert calculate_efficiency_score(150) == 2.0


class TestDiversityScore:
    """Tests for calculate_diversity_score function."""

    def test_high_diversity(self):
        """Should give high score for many languages."""
        assert calculate_diversity_score(4) == 10.0
        assert calculate_diversity_score(5) == 10.0

    def test_medium_diversity(self):
        """Should give medium score for some languages."""
        assert calculate_diversity_score(3) == 8.0
        assert calculate_diversity_score(2) == 6.0

    def test_low_diversity(self):
        """Should give low score for single language."""
        assert calculate_diversity_score(1) == 4.0
        assert calculate_diversity_score(0) == 0.0


class TestProductivityScore:
    """Tests for calculate_productivity_score function."""

    def test_high_productivity(self):
        """Should give high score for many lines."""
        assert calculate_productivity_score(1000, 1000) == 10.0
        assert calculate_productivity_score(500, 1000) == 5.0

    def test_low_productivity(self):
        """Should give low score for few lines."""
        assert calculate_productivity_score(100, 1000) == 1.0
        assert calculate_productivity_score(0, 1000) == 0.0

    def test_cap_at_max(self):
        """Should cap score at 10."""
        assert calculate_productivity_score(2000, 1000) == 10.0


class TestCompositeScoreV2:
    """Tests for calculate_composite_score_v2 function."""

    def test_returns_all_scores(self):
        """Should return all individual scores and composite."""
        result = calculate_composite_score_v2(
            prompt="버그를 수정해줘",
            code_count=5,
            total_lines=100,
            message_count=10,
            language_diversity=2,
            max_lines=1000,
        )

        assert 'structure_score' in result
        assert 'context_score' in result
        assert 'productivity_score' in result
        assert 'efficiency_score' in result
        assert 'diversity_score' in result
        assert 'composite_score' in result

    def test_high_quality_prompt_scores_higher(self):
        """High quality prompts should score higher than low quality."""
        high_quality = calculate_composite_score_v2(
            prompt="LoginForm.tsx 컴포넌트에 비밀번호 유효성 검사를 추가해줘. React를 사용하고 있어.",
            code_count=5,
            total_lines=150,
            message_count=8,
            language_diversity=2,
            max_lines=1000,
        )

        low_quality = calculate_composite_score_v2(
            prompt="fix it",
            code_count=1,
            total_lines=10,
            message_count=50,
            language_diversity=1,
            max_lines=1000,
        )

        assert high_quality['composite_score'] > low_quality['composite_score']


class TestScoringAccuracy:
    """Integration tests for scoring accuracy with fixtures."""

    def test_high_quality_prompts_score_higher(self, high_quality_prompts, low_quality_prompts):
        """High quality prompts should score higher on average."""
        high_scores = []
        for p in high_quality_prompts:
            result = calculate_composite_score_v2(
                prompt=p['prompt'],
                code_count=p['code_count'],
                total_lines=p['total_lines'],
                message_count=p['message_count'],
                language_diversity=p['language_diversity'],
            )
            high_scores.append(result['composite_score'])

        low_scores = []
        for p in low_quality_prompts:
            result = calculate_composite_score_v2(
                prompt=p['prompt'],
                code_count=p['code_count'],
                total_lines=p['total_lines'],
                message_count=p['message_count'],
                language_diversity=p['language_diversity'],
            )
            low_scores.append(result['composite_score'])

        high_avg = sum(high_scores) / len(high_scores)
        low_avg = sum(low_scores) / len(low_scores)

        assert high_avg > low_avg, f"High quality avg ({high_avg:.2f}) should be > low quality avg ({low_avg:.2f})"

    def test_structure_score_differentiation(self, high_quality_prompts, low_quality_prompts):
        """Structure score should differentiate prompt quality."""
        high_structure_scores = [
            calculate_structure_score(p['prompt']) for p in high_quality_prompts
        ]
        low_structure_scores = [
            calculate_structure_score(p['prompt']) for p in low_quality_prompts
        ]

        high_avg = sum(high_structure_scores) / len(high_structure_scores)
        low_avg = sum(low_structure_scores) / len(low_structure_scores)

        assert high_avg > low_avg, f"High quality structure avg ({high_avg:.2f}) should be > low quality ({low_avg:.2f})"
