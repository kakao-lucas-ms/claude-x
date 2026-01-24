"""Project context collection for smart prompt rewriting."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import glob as glob_module


ContextDict = dict[str, Any]


def get_project_context(base_path: str | None = None) -> ContextDict:
    """Collect current project structure for smart rewriting.

    Args:
        base_path: Base directory to scan. Defaults to current working directory.

    Returns:
        Dictionary containing project file lists and metadata.
    """
    base = Path(base_path) if base_path else Path.cwd()

    context: ContextDict = {
        "base_path": str(base),
        "docs_files": [],
        "src_files": [],
        "test_files": [],
        "config_files": [],
        "readme_exists": False,
    }

    # Collect docs files
    for pattern in ["docs/**/*.md", "**/*.md"]:
        for f in base.glob(pattern):
            if not _should_ignore(f):
                rel_path = str(f.relative_to(base))
                if rel_path not in context["docs_files"]:
                    context["docs_files"].append(rel_path)

    # Limit docs files
    context["docs_files"] = context["docs_files"][:50]

    # Collect src files
    for pattern in ["src/**/*.py", "src/**/*.ts", "src/**/*.tsx", "src/**/*.js", "src/**/*.jsx"]:
        for f in base.glob(pattern):
            if not _should_ignore(f):
                context["src_files"].append(str(f.relative_to(base)))

    context["src_files"] = context["src_files"][:100]

    # Collect test files
    for pattern in ["tests/**/*.py", "test/**/*.py", "**/*.test.ts", "**/*.test.tsx", "**/*.test.js"]:
        for f in base.glob(pattern):
            if not _should_ignore(f):
                context["test_files"].append(str(f.relative_to(base)))

    context["test_files"] = context["test_files"][:50]

    # Check config files
    config_candidates = [
        "pyproject.toml", "package.json", "tsconfig.json",
        "setup.py", "Cargo.toml", "go.mod", "pom.xml"
    ]
    for cfg in config_candidates:
        if (base / cfg).exists():
            context["config_files"].append(cfg)

    # Check README
    for readme in ["README.md", "readme.md", "README.rst", "README"]:
        if (base / readme).exists():
            context["readme_exists"] = True
            context["readme_path"] = readme
            break

    return context


def find_matching_files(keywords: list[str], context: ContextDict) -> list[str]:
    """Find files matching given keywords in project context.

    Args:
        keywords: Keywords to search for in file paths.
        context: Project context from get_project_context().

    Returns:
        List of matching file paths, sorted by relevance.
    """
    if not keywords:
        return []

    all_files = (
        context.get("docs_files", []) +
        context.get("src_files", []) +
        context.get("test_files", [])
    )

    scored: list[tuple[str, int]] = []

    for file_path in all_files:
        score = 0
        file_lower = file_path.lower()

        for keyword in keywords:
            kw_lower = keyword.lower()

            # Exact match in filename
            filename = os.path.basename(file_path).lower()
            if kw_lower in filename:
                score += 10
            # Match in path
            elif kw_lower in file_lower:
                score += 5
            # Partial match
            elif any(kw_lower in part for part in file_lower.split("/")):
                score += 2

        if score > 0:
            scored.append((file_path, score))

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    return [f for f, _ in scored[:10]]


def summarize_task(prompt: str) -> str:
    """Extract and summarize the main task from a prompt.

    Args:
        prompt: Original user prompt.

    Returns:
        Summarized task description.
    """
    # Remove common prefixes
    task = prompt.strip()

    prefixes_to_remove = [
        "지금", "다음", "이", "그", "저",
        "please", "can you", "could you",
    ]

    for prefix in prefixes_to_remove:
        if task.lower().startswith(prefix):
            task = task[len(prefix):].strip()

    # Limit length
    if len(task) > 100:
        task = task[:100] + "..."

    return task


def _should_ignore(path: Path) -> bool:
    """Check if a path should be ignored."""
    ignore_patterns = [
        "__pycache__", ".git", "node_modules", ".venv", "venv",
        ".egg-info", "dist", "build", ".pytest_cache", ".mypy_cache",
        ".tox", ".coverage", "htmlcov",
    ]

    path_str = str(path)
    return any(pattern in path_str for pattern in ignore_patterns)
