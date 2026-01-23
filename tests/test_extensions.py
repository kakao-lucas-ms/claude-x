"""Tests for extension detection helpers."""

from pathlib import Path

import pytest

import claude_x.extensions as extensions


def test_detect_extensions_contains_rule(tmp_path, monkeypatch):
    claude_md = tmp_path / ".claude" / "CLAUDE.md"
    claude_md.parent.mkdir(parents=True)
    claude_md.write_text("SuperClaude Commands", encoding="utf-8")

    monkeypatch.setitem(
        extensions.KNOWN_EXTENSIONS,
        "superclaude",
        {
            "name": "SuperClaude",
            "detection": [f"{claude_md} contains 'SuperClaude'"],
            "commands": {},
        },
    )

    assert extensions.is_extension_installed("superclaude") is True


def test_detect_extensions_exists_rule(tmp_path, monkeypatch):
    ext_dir = tmp_path / ".oh-my-opencode"
    ext_dir.mkdir()

    monkeypatch.setitem(
        extensions.KNOWN_EXTENSIONS,
        "oh-my-opencode",
        {
            "name": "Oh-My-OpenCode",
            "detection": [f"{ext_dir} directory exists"],
            "commands": {},
        },
    )

    assert extensions.is_extension_installed("oh-my-opencode") is True


def test_calculate_confidence():
    prompt = "이 기능 복잡해서 여러 단계로 구현해야 해"
    confidence = extensions.calculate_confidence(prompt, ["여러 단계", "병렬"], 1.8)
    assert confidence > 0.5


def test_suggest_command():
    prompt = "이 기능 복잡해서 여러 단계로 구현해야 할 것 같아"
    installed = ["superclaude", "oh-my-opencode"]
    suggestion = extensions.suggest_extension_command(prompt, installed)

    assert suggestion is not None
    assert suggestion["command"].startswith("/")
    assert suggestion["confidence"] > 0.5
