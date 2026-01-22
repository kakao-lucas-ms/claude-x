"""MCP Server for Claude-X - Exposes analytics tools to Claude Code."""

from pathlib import Path
from typing import Optional
from mcp.server.fastmcp import FastMCP

from .analytics import PromptAnalytics
from .storage import Storage
from .scoring import (
    calculate_structure_score,
    calculate_context_score,
    calculate_composite_score_v2,
)


def get_storage() -> Storage:
    """Get storage instance."""
    data_dir = Path.home() / ".claude-x" / "data"
    db_path = data_dir / "claude_x.db"
    return Storage(db_path)


def get_analytics() -> PromptAnalytics:
    """Get analytics instance."""
    return PromptAnalytics(get_storage())

# Create MCP server
mcp = FastMCP("claude-x")


@mcp.tool()
def get_best_prompts(
    project: Optional[str] = None,
    limit: int = 10,
    strict: bool = False,
    min_quality: Optional[float] = None,
) -> dict:
    """Get best quality prompts from Claude Code sessions.

    Args:
        project: Project name to analyze (default: None = all projects)
        limit: Maximum number of prompts to return (default: 10)
        strict: Use strict filtering (structure>=3.0, context>=2.0)
        min_quality: Minimum combined structure+context score

    Returns:
        Dictionary containing best prompts with scores and metadata
    """
    analytics = get_analytics()
    prompts = analytics.get_best_prompts(
        project_name=project,
        limit=limit,
        strict_mode=strict,
        min_quality=min_quality,
    )

    result = {
        "count": len(prompts),
        "prompts": prompts,
    }

    # Add helpful message if no data
    if len(prompts) == 0:
        result["message"] = (
            "No session data found. To collect data:\n"
            "1. Run 'cx watch' in background, or\n"
            "2. Just use Claude Code normally - sessions are auto-saved to ~/.claude/projects/\n"
            "3. Make sure you've used Claude Code at least once since installing claude-x"
        )

    return result


@mcp.tool()
def get_worst_prompts(
    project: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Get prompts that need improvement from Claude Code sessions.

    Args:
        project: Project name to analyze (default: None = all projects)
        limit: Maximum number of prompts to return (default: 10)

    Returns:
        Dictionary containing worst prompts with scores and improvement suggestions
    """
    analytics = get_analytics()
    prompts = analytics.get_worst_prompts(
        project_name=project,
        limit=limit,
    )

    result = {
        "count": len(prompts),
        "prompts": prompts,
    }

    # Add helpful message if no data
    if len(prompts) == 0:
        result["message"] = (
            "No session data found. To collect data:\n"
            "1. Run 'cx watch' in background, or\n"
            "2. Just use Claude Code normally - sessions are auto-saved to ~/.claude/projects/\n"
            "3. Make sure you've used Claude Code at least once since installing claude-x"
        )

    return result


@mcp.tool()
def analyze_sessions(
    project: Optional[str] = None,
) -> dict:
    """Analyze Claude Code session statistics for a project.

    Args:
        project: Project name to analyze (default: None = all projects)

    Returns:
        Dictionary containing session statistics including:
        - Time-based analysis
        - Language distribution
        - Category stats
        - Branch productivity
    """
    analytics = get_analytics()
    storage = get_storage()

    # Check if we have any sessions
    sessions = list(storage.list_sessions(project_name=project))

    result = {
        "time_analysis": analytics.get_time_based_analysis(project_name=project),
        "language_distribution": analytics.get_language_distribution(project_name=project),
        "category_stats": analytics.get_category_stats(project_name=project),
        "branch_productivity": analytics.get_branch_productivity(project_name=project),
    }

    # Add helpful message if no data
    if len(sessions) == 0:
        result["message"] = (
            f"No session data found for project '{project}'. To collect data:\n"
            "1. Run 'cx watch' in background, or\n"
            "2. Just use Claude Code normally - sessions are auto-saved to ~/.claude/projects/\n"
            "3. Make sure you've used Claude Code at least once since installing claude-x"
        )

    return result


@mcp.tool()
def score_prompt(prompt: str) -> dict:
    """Score a single prompt for quality.

    Args:
        prompt: The prompt text to analyze

    Returns:
        Dictionary containing:
        - structure_score: How well-structured the prompt is (0-10)
        - context_score: How much context is provided (0-10)
        - composite_score: Overall quality score
        - suggestions: List of improvement suggestions
    """
    structure = calculate_structure_score(prompt)
    context = calculate_context_score(prompt)

    # Generate suggestions based on scores
    suggestions = []
    if structure < 4.0:
        suggestions.append("Add a clear goal or action verb (e.g., '추가해줘', 'fix', 'implement')")
    if structure < 6.0:
        suggestions.append("Be more specific about what you want to achieve")
    if context < 2.0:
        suggestions.append("Add file paths or component names")
    if context < 4.0:
        suggestions.append("Mention the technology stack (React, TypeScript, etc.)")
    if len(prompt) < 20:
        suggestions.append("Provide more details about the task")

    return {
        "structure_score": structure,
        "context_score": context,
        "combined_score": structure + context,
        "suggestions": suggestions if suggestions else ["Good prompt! No major improvements needed."],
    }


@mcp.tool()
def get_prompt_patterns(
    project: Optional[str] = None,
    limit: int = 5,
) -> dict:
    """Get common successful prompt patterns from your sessions.

    Args:
        project: Project name to analyze (default: None = all projects)
        limit: Maximum number of patterns to return (default: 5)

    Returns:
        Dictionary containing common patterns found in high-quality prompts
    """
    analytics = get_analytics()
    best_prompts = analytics.get_best_prompts(
        project_name=project,
        limit=20,
        strict_mode=True,
    )

    # Extract patterns from best prompts
    patterns = {
        "file_references": 0,
        "technology_mentions": 0,
        "clear_goals": 0,
        "code_blocks": 0,
        "questions": 0,
    }

    examples = []
    for p in best_prompts[:limit]:
        prompt_text = p.get("prompt", "")
        if "/" in prompt_text or "." in prompt_text:
            patterns["file_references"] += 1
        if any(tech in prompt_text.lower() for tech in ["react", "typescript", "python", "javascript"]):
            patterns["technology_mentions"] += 1
        if any(goal in prompt_text for goal in ["해줘", "fix", "add", "implement", "create"]):
            patterns["clear_goals"] += 1
        if "```" in prompt_text:
            patterns["code_blocks"] += 1
        if "?" in prompt_text:
            patterns["questions"] += 1

        examples.append({
            "prompt": prompt_text[:100] + "..." if len(prompt_text) > 100 else prompt_text,
            "score": p.get("composite_score", 0),
            "category": p.get("category", "unknown"),
        })

    result = {
        "patterns": patterns,
        "top_examples": examples,
        "recommendation": "Include file paths, technology names, and clear action verbs for best results.",
    }

    # Add helpful message if no data
    if len(best_prompts) == 0:
        result["message"] = (
            "No session data found to analyze patterns. To collect data:\n"
            "1. Run 'cx watch' in background, or\n"
            "2. Just use Claude Code normally - sessions are auto-saved to ~/.claude/projects/\n"
            "3. Make sure you've used Claude Code at least once since installing claude-x"
        )

    return result


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
