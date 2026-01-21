"""Pytest configuration and fixtures."""

import json
from pathlib import Path
from typing import List, Dict, Any

import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def system_messages() -> List[str]:
    """Load system message samples for filter testing."""
    path = FIXTURES_DIR / "system_messages.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def real_prompts() -> List[str]:
    """Load real user prompt samples."""
    path = FIXTURES_DIR / "real_prompts.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def high_quality_prompts() -> List[Dict[str, Any]]:
    """Load high quality prompt samples with metadata."""
    path = FIXTURES_DIR / "high_quality_prompts.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def low_quality_prompts() -> List[Dict[str, Any]]:
    """Load low quality prompt samples with metadata."""
    path = FIXTURES_DIR / "low_quality_prompts.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_fixture(name: str) -> Any:
    """Helper function to load fixtures by name."""
    path = FIXTURES_DIR / f"{name}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
