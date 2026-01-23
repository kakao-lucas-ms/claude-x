"""Tests for MCP prompt coaching tool."""

import claude_x.mcp_server as mcp_server
import claude_x.prompt_coach as prompt_coach


class FakeAnalytics:
    def get_best_prompts(self, limit=5, strict_mode=True):
        return [{"first_prompt": "LoginForm.tsx에 validation 추가해줘"}]


def test_analyze_prompt_korean(monkeypatch):
    monkeypatch.setattr(mcp_server, "get_analytics", lambda: FakeAnalytics())
    monkeypatch.setattr(prompt_coach, "detect_installed_extensions", lambda: [])

    result = mcp_server.analyze_and_improve_prompt("응 진행해줘", detect_extensions=False)

    assert result["language"] == "ko"
    assert "scores" in result
    assert len(result["problems"]) > 0
    assert "llm_summary" in result


def test_analyze_with_extensions(monkeypatch):
    monkeypatch.setattr(mcp_server, "get_analytics", lambda: FakeAnalytics())
    monkeypatch.setattr(prompt_coach, "detect_installed_extensions", lambda: ["oh-my-opencode"])
    monkeypatch.setattr(
        prompt_coach,
        "suggest_extension_command",
        lambda prompt, installed: {
            "extension": "Oh-My-OpenCode",
            "command": "/sisyphus",
            "reason": "멀티 에이전트 오케스트레이션",
            "confidence": 0.9,
            "usage_example": "/sisyphus ...",
        },
    )

    result = mcp_server.analyze_and_improve_prompt(
        "이 기능 복잡해서 여러 단계로 구현해야 해",
        detect_extensions=True,
    )

    assert result["extension_suggestion"] is not None
    assert result["extension_suggestion"]["command"].startswith("/")
