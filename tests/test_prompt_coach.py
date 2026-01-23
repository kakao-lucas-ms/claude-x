"""Tests for prompt coaching logic."""

from claude_x.prompt_coach import PromptCoach


class FakeAnalytics:
    def get_best_prompts(self, limit=5, strict_mode=True):
        return [
            {"first_prompt": "LoginForm.tsx에 validation 추가해줘"},
            {"first_prompt": "현재 상황이 이런데 해결책을 찾아줘"},
        ]


def test_identify_problems():
    coach = PromptCoach(FakeAnalytics())
    prompt = "응 진행해줘"
    problems = coach.identify_problems(prompt, {"structure": 0.0, "context": 0.0}, "ko")

    issues = {p["issue"] for p in problems}
    assert "no_target" in issues
    assert "conversational" in issues


def test_generate_suggestions():
    coach = PromptCoach(FakeAnalytics())
    suggestions = coach.generate_suggestions(
        prompt="이 버그 수정해줘",
        problems=[],
        user_best=coach._get_user_best_prompts(),
        lang="ko",
    )

    assert len(suggestions) > 0
    assert suggestions[0]["type"] in ["user_pattern", "generic"]
    assert "template" in suggestions[0]


def test_calculate_expected_impact():
    coach = PromptCoach(FakeAnalytics())
    impact = coach.calculate_expected_impact({"structure": 1.0, "context": 1.0})

    assert "messages" in impact
    assert "code_generation" in impact
    assert "success_rate" in impact


def test_generate_user_insights():
    coach = PromptCoach(FakeAnalytics())
    insights = coach.generate_user_insights(coach._get_user_best_prompts(), "ko")

    assert len(insights) > 0
