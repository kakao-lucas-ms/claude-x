"""Tests for system message filtering."""

import pytest
from claude_x.filters import (
    is_system_message,
    is_likely_system_message,
    filter_prompts,
    extract_real_prompt,
    get_filter_stats,
)


class TestIsSystemMessage:
    """Tests for is_system_message function."""

    def test_filters_task_notification(self):
        """Should filter task notification tags."""
        assert is_system_message("<task-notification>Task completed</task-notification>")

    def test_filters_system_reminder(self):
        """Should filter system reminder tags."""
        assert is_system_message("<system-reminder>Remember something</system-reminder>")

    def test_filters_context_summary(self):
        """Should filter context summary tags."""
        assert is_system_message("<context-summary>Previous context</context-summary>")

    def test_filters_session_restore(self):
        """Should filter session restore tags."""
        assert is_system_message("<session-restore>Restoring session</session-restore>")

    def test_filters_planning_mode(self):
        """Should filter planning mode activation."""
        assert is_system_message("[PLANNING MODE ACTIVATED]")

    def test_filters_ultrawork_mode(self):
        """Should filter ultrawork mode messages."""
        assert is_system_message("[ULTRAWORK MODE RESTORED]")

    def test_filters_request_interrupted(self):
        """Should filter interrupted requests."""
        assert is_system_message("Request interrupted by user")

    def test_filters_no_prompt(self):
        """Should filter 'No prompt' messages."""
        assert is_system_message("No prompt")

    def test_filters_slash_commands(self):
        """Should filter simple slash commands."""
        assert is_system_message("/")
        assert is_system_message("/clear")
        assert is_system_message("/help")

    def test_filters_empty_messages(self):
        """Should filter empty messages."""
        assert is_system_message("")
        assert is_system_message("   ")
        assert is_system_message(None)

    def test_filters_hook_success(self):
        """Should filter hook success messages."""
        assert is_system_message("UserPromptSubmit hook success: Success")

    def test_filters_available_skills(self):
        """Should filter available skills listing."""
        assert is_system_message("Available skills:\n- sisyphus\n- orchestrator")

    def test_keeps_real_prompts(self):
        """Should keep real user prompts."""
        assert not is_system_message("이 함수를 리팩토링해줘")
        assert not is_system_message("버그를 수정해줘")
        assert not is_system_message("새로운 컴포넌트를 만들어줘")

    def test_keeps_detailed_prompts(self):
        """Should keep detailed implementation prompts."""
        assert not is_system_message(
            "LoginForm.tsx 컴포넌트에 비밀번호 유효성 검사 추가해줘"
        )
        assert not is_system_message(
            "현재 React 프로젝트의 src/components/Login.tsx에서 에러가 발생해"
        )

    def test_keeps_question_prompts(self):
        """Should keep question/learning prompts."""
        assert not is_system_message("이 코드가 어떻게 동작하는지 설명해줘")
        assert not is_system_message("React Server Components가 뭐야")


class TestIsLikelySystemMessage:
    """Tests for is_likely_system_message function."""

    def test_filters_very_short_messages(self):
        """Should filter very short messages."""
        assert is_likely_system_message("hi")
        assert is_likely_system_message("ok")
        assert is_likely_system_message("?")

    def test_filters_empty_messages(self):
        """Should filter empty messages."""
        assert is_likely_system_message("")
        assert is_likely_system_message(None)

    def test_filters_high_xml_ratio(self):
        """Should filter messages with high XML tag ratio."""
        msg = "<tag1>x</tag1> <tag2>y</tag2> <tag3>z</tag3>"
        assert is_likely_system_message(msg)

    def test_keeps_normal_prompts(self):
        """Should keep normal user prompts."""
        assert not is_likely_system_message("이 함수를 리팩토링해줘")
        assert not is_likely_system_message("버그를 수정해줘")

    def test_keeps_longer_prompts(self):
        """Should keep longer detailed prompts."""
        prompt = "LoginForm.tsx 컴포넌트에 비밀번호 유효성 검사를 추가해줘. 최소 8자 이상으로."
        assert not is_likely_system_message(prompt)


class TestFilterPrompts:
    """Tests for filter_prompts function."""

    def test_filters_system_messages(self):
        """Should filter out system messages from list."""
        prompts = [
            {"first_prompt": "버그를 수정해줘"},
            {"first_prompt": "<system-reminder>test</system-reminder>"},
            {"first_prompt": "새 기능 추가해줘"},
            {"first_prompt": "Request interrupted by user"},
        ]

        filtered = filter_prompts(prompts)

        assert len(filtered) == 2
        assert filtered[0]["first_prompt"] == "버그를 수정해줘"
        assert filtered[1]["first_prompt"] == "새 기능 추가해줘"

    def test_include_system_option(self):
        """Should include system messages when include_system=True."""
        prompts = [
            {"first_prompt": "버그를 수정해줘"},
            {"first_prompt": "<system-reminder>test</system-reminder>"},
        ]

        filtered = filter_prompts(prompts, include_system=True)

        assert len(filtered) == 2

    def test_custom_prompt_key(self):
        """Should work with custom prompt key."""
        prompts = [
            {"prompt_text": "버그를 수정해줘"},
            {"prompt_text": "No prompt"},
        ]

        filtered = filter_prompts(prompts, prompt_key="prompt_text")

        assert len(filtered) == 1
        assert filtered[0]["prompt_text"] == "버그를 수정해줘"


class TestExtractRealPrompt:
    """Tests for extract_real_prompt function."""

    def test_extracts_from_command_args(self):
        """Should extract prompt from command-args tags."""
        text = '<command-args>"실제 프롬프트 내용"</command-args>'
        assert extract_real_prompt(text) == "실제 프롬프트 내용"

    def test_extracts_without_quotes(self):
        """Should extract prompt without quotes."""
        text = '<command-args>실제 프롬프트 내용</command-args>'
        assert extract_real_prompt(text) == "실제 프롬프트 내용"

    def test_returns_none_for_empty(self):
        """Should return None for empty input."""
        assert extract_real_prompt("") is None
        assert extract_real_prompt(None) is None

    def test_returns_none_for_empty_args(self):
        """Should return None for empty command args."""
        text = '<command-args></command-args>'
        assert extract_real_prompt(text) is None


class TestGetFilterStats:
    """Tests for get_filter_stats function."""

    def test_returns_correct_stats(self):
        """Should return correct filter statistics."""
        prompts = [
            {"first_prompt": "버그를 수정해줘"},
            {"first_prompt": "<system-reminder>test</system-reminder>"},
            {"first_prompt": "새 기능 추가해줘"},
            {"first_prompt": "hi"},  # Too short - heuristic
        ]

        stats = get_filter_stats(prompts)

        assert stats["total"] == 4
        assert stats["pattern_filtered"] == 1  # system-reminder
        assert stats["heuristic_filtered"] == 1  # "hi"
        assert stats["kept"] == 2
        assert stats["filter_rate"] == 0.5


class TestFilterAccuracy:
    """Integration tests for filter accuracy."""

    def test_system_message_filter_accuracy(self, system_messages):
        """Should filter at least 95% of system messages."""
        filtered_count = sum(1 for msg in system_messages if is_system_message(msg))
        accuracy = filtered_count / len(system_messages)

        assert accuracy >= 0.95, f"System message filter accuracy: {accuracy:.2%}"

    def test_real_prompt_preservation(self, real_prompts):
        """Should preserve at least 95% of real prompts."""
        kept_count = sum(1 for prompt in real_prompts if not is_system_message(prompt))
        preservation_rate = kept_count / len(real_prompts)

        assert preservation_rate >= 0.95, f"Real prompt preservation rate: {preservation_rate:.2%}"

    def test_combined_filter_accuracy(self, system_messages, real_prompts):
        """Should have good combined accuracy."""
        # System messages filtered
        sys_filtered = sum(
            1 for msg in system_messages
            if is_system_message(msg) or is_likely_system_message(msg)
        )
        sys_accuracy = sys_filtered / len(system_messages)

        # Real prompts kept
        real_kept = sum(
            1 for prompt in real_prompts
            if not is_system_message(prompt) and not is_likely_system_message(prompt)
        )
        real_preservation = real_kept / len(real_prompts)

        assert sys_accuracy >= 0.90, f"System message filter accuracy: {sys_accuracy:.2%}"
        assert real_preservation >= 0.90, f"Real prompt preservation: {real_preservation:.2%}"
