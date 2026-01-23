"""Extension detection and command suggestion helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import re


KNOWN_EXTENSIONS: dict[str, dict[str, Any]] = {
    "superclaude": {
        "name": "SuperClaude",
        "detection": [
            "~/.claude/CLAUDE.md contains 'SuperClaude'",
            "~/.superclaude directory exists",
        ],
        "commands": {
            "/sc:implement": {
                "description": "구조화된 기능 구현",
                "triggers": ["기능 구현", "implement", "add feature"],
                "confidence_boost": 2.0,
                "usage_example": "/sc:implement 로그인 기능을 단계별로 구현해줘",
            },
            "/sc:brainstorm": {
                "description": "소크라틱 대화로 요구사항 탐색",
                "triggers": ["브레인스토밍", "brainstorm", "아이디어"],
                "confidence_boost": 2.0,
                "usage_example": "/sc:brainstorm 결제 UX 아이디어를 정리해줘",
            },
            "/sc:troubleshoot": {
                "description": "체계적 디버깅",
                "triggers": ["버그", "에러", "bug", "error"],
                "confidence_boost": 1.5,
                "usage_example": "/sc:troubleshoot 이 에러 원인을 단계별로 찾아줘",
            },
        },
    },
    "oh-my-opencode": {
        "name": "Oh-My-OpenCode",
        "detection": [
            ".oh-my-opencode directory exists",
            "~/.claude/CLAUDE.md contains 'oh-my-opencode'",
        ],
        "commands": {
            "/sisyphus": {
                "description": "멀티 에이전트 오케스트레이션",
                "triggers": ["복잡한", "여러 단계", "multi-step"],
                "confidence_boost": 1.8,
                "usage_example": "/sisyphus 이 기능을 끝까지 구현해줘",
            },
            "/ultrawork": {
                "description": "병렬 에이전트 실행",
                "triggers": ["빠르게", "병렬", "parallel"],
                "confidence_boost": 2.0,
                "usage_example": "/ultrawork 여러 파일을 병렬로 수정해줘",
            },
            "/deepsearch": {
                "description": "코드베이스 심층 검색",
                "triggers": ["찾아", "검색", "search", "find"],
                "confidence_boost": 1.5,
                "usage_example": "/deepsearch 해당 함수 정의를 찾아줘",
            },
        },
    },
}


def detect_installed_extensions() -> list[str]:
    """Detect installed extensions by rules."""
    installed: list[str] = []
    for ext_name in KNOWN_EXTENSIONS.keys():
        if is_extension_installed(ext_name):
            installed.append(ext_name)
    return installed


def is_extension_installed(ext_name: str) -> bool:
    """
    Determine whether a given extension is installed.

    Detection rules support:
    - "<path> contains '<text>'"
    - "<path> directory exists" or "<path> file exists"
    """
    ext = KNOWN_EXTENSIONS.get(ext_name)
    if not ext:
        return False

    for rule in ext.get("detection", []):
        if _match_contains_rule(rule):
            return True
        if _match_exists_rule(rule):
            return True

    return False


def suggest_extension_command(prompt: str, installed: list[str]) -> dict[str, Any] | None:
    """
    Suggest an extension command based on prompt and installed extensions.
    """
    if not prompt or not installed:
        return None

    best: dict[str, Any] | None = None
    for ext_key in installed:
        ext = KNOWN_EXTENSIONS.get(ext_key, {})
        commands = ext.get("commands", {})
        for command, info in commands.items():
            confidence = calculate_confidence(prompt, info.get("triggers", []), info.get("confidence_boost", 1.0))
            if confidence <= 0:
                continue
            if best is None or confidence > best["confidence"]:
                best = {
                    "extension": ext.get("name", ext_key),
                    "command": command,
                    "reason": info.get("description", ""),
                    "confidence": confidence,
                    "usage_example": info.get("usage_example", f"{command} ..."),
                }

    if not best:
        return None

    if best["confidence"] < 0.5:
        return None

    return best


def calculate_confidence(prompt: str, triggers: list[str], boost: float) -> float:
    """
    Calculate command matching confidence.

    - Base score = matched keyword count / total keywords
    - Final score = base score * boost (capped at 1.0)
    """
    if not prompt or not triggers:
        return 0.0

    prompt_lower = prompt.lower()
    matches = 0
    for trigger in triggers:
        if trigger.lower() in prompt_lower:
            matches += 1

    base = matches / len(triggers)
    return min(base * boost, 1.0)


def _match_contains_rule(rule: str) -> bool:
    match = re.match(r"(.+?)\s+contains\s+['\"](.+?)['\"]", rule)
    if not match:
        return False

    path_text, needle = match.groups()
    path = _expand_path(path_text.strip())
    if not path.exists() or not path.is_file():
        return False

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False

    return needle in content


def _match_exists_rule(rule: str) -> bool:
    if "exists" not in rule:
        return False

    path_text = rule.split("exists")[0].strip()
    path = _expand_path(path_text)
    return path.exists()


def _expand_path(path_text: str) -> Path:
    return Path(path_text).expanduser()
