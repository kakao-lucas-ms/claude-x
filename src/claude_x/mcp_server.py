"""MCP Server for Claude-X - Exposes analytics tools to Claude Code."""

from pathlib import Path
from typing import Optional
import re
from mcp.server.fastmcp import FastMCP

from .analytics import PromptAnalytics
from .storage import Storage
from .scoring import (
    calculate_structure_score,
    calculate_context_score,
    calculate_composite_score_v2,
)
from .patterns import (
    analyze_prompt_for_pattern,
    extract_patterns_from_prompts,
    get_pattern_recommendations,
)
from .prompt_coach import PromptCoach


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

    reuse_ready = []
    for prompt in prompts:
        prompt_text = prompt.get("first_prompt", "")
        analysis = analyze_prompt_for_pattern(prompt_text)
        placeholders = []
        if analysis.get("template"):
            placeholders = list(set(re.findall(r"\[([A-Z_]+)\]", analysis["template"])))

        template = analysis.get("template", "")
        template_preview = template
        if template:
            template_preview = re.sub(r"\[([A-Z_]+)\]", r"<\1>", template)

        fill_guide = {
            "fill_order": placeholders,
            "example": template_preview,
            "tip": "Replace <PLACEHOLDER> with your concrete target/context before sending.",
        }

        reuse_ready.append({
            "prompt": prompt_text,
            "template": analysis.get("template", ""),
            "pattern_type": analysis.get("pattern_type"),
            "pattern_description": analysis.get("pattern_description"),
            "category": analysis.get("category"),
            "tags": analysis.get("tags", []),
            "quality_score": analysis.get("quality_score", 0.0),
            "placeholders": placeholders,
            "template_preview": template_preview,
            "fill_guide": fill_guide,
            "reuse_checklist": [
                "target/file/path", "action verb", "constraints", "expected outcome", "tech stack"
            ],
        })

    result = {
        "count": len(prompts),
        "prompts": prompts,
        "reuse_ready": reuse_ready,
        "reuse_guidance": {
            "goal": "Make prompts reusable in your next session",
            "how": "Use the template, fill placeholders, and keep a clear action + context",
        },
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

    time_analysis = analytics.get_time_based_analysis(project_name=project)
    language_distribution = analytics.get_language_distribution(project_name=project)
    category_stats = analytics.get_category_stats(project_name=project)
    branch_productivity = analytics.get_branch_productivity(project_name=project)

    result = {
        "time_analysis": time_analysis,
        "language_distribution": language_distribution,
        "category_stats": category_stats,
        "branch_productivity": branch_productivity,
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

    top_language = language_distribution[0]["language"] if language_distribution else "N/A"
    top_category = category_stats[0]["category"] if category_stats else "N/A"
    peak_hour = time_analysis.get("hour_distribution", [])
    peak_hour = peak_hour[0]["hour"] if peak_hour else "N/A"

    result["llm_summary"] = {
        "top_language": top_language,
        "top_category": top_category,
        "peak_hour": peak_hour,
        "note": "Use these signals to craft reusable prompts for your dominant work patterns.",
    }
    result["next_actions"] = [
        "Use get_best_prompts to extract reusable templates",
        "Use get_prompt_patterns to build a personal prompt library",
        "Write prompts with clear target + action + constraints",
    ]

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
def analyze_and_improve_prompt(
    prompt: str,
    detect_extensions: bool = True,
    include_history: bool = True,
) -> dict:
    """
    Analyze a prompt and provide improvement suggestions.

    Args:
        prompt: Prompt text to analyze
        detect_extensions: Whether to detect extensions
        include_history: Whether to use user history

    Returns:
        Coaching result with LLM-friendly summary
    """
    analytics = get_analytics()
    coach = PromptCoach(analytics)

    result = coach.analyze(
        prompt=prompt,
        detect_extensions=detect_extensions,
        include_history=include_history,
    )

    llm_summary = generate_llm_summary(result)

    return {
        **result.__dict__,
        "llm_summary": llm_summary,
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

    extracted_patterns = extract_patterns_from_prompts(best_prompts, min_quality=5.0)
    reusable_templates = [p.to_dict() for p in extracted_patterns[:limit]]
    top_reusable = []
    for pattern in extracted_patterns[:3]:
        top_reusable.append({
            "template": pattern.template,
            "pattern_type": pattern.pattern_type,
            "avg_score": pattern.avg_score,
            "usage_count": pattern.usage_count,
            "example": pattern.examples[0] if pattern.examples else "",
        })
    recommendations = get_pattern_recommendations(limit=limit)

    result = {
        "reusable_templates": reusable_templates,
        "top_reusable": top_reusable,
        "recommendations": recommendations,
        "recommendation": "Use reusable templates with placeholders, then fill target/action/context.",
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


def generate_llm_summary(result) -> str:
    """Generate a human-readable summary for LLM consumption."""
    lang = result.language

    if lang == "ko":
        summary = f"""
프롬프트 "{result.original_prompt}"를 분석했습니다.

📊 현재 점수:
- 구조: {result.scores['structure']}/10
- 맥락: {result.scores['context']}/10

❌ 주요 문제:
{_format_problems(result.problems, lang)}

💡 개선 제안:
{_format_suggestions(result.suggestions, lang)}

📈 예상 효과:
{_format_impact(result.expected_impact, lang)}
"""
    else:
        summary = f"""
Analyzed prompt "{result.original_prompt}".

📊 Current scores:
- Structure: {result.scores['structure']}/10
- Context: {result.scores['context']}/10

❌ Issues:
{_format_problems(result.problems, lang)}

💡 Suggestions:
{_format_suggestions(result.suggestions, lang)}

📈 Expected impact:
{_format_impact(result.expected_impact, lang)}
"""

    # v0.4.1: Add improved prompt and recommended actions
    if hasattr(result, 'intent') and result.intent != "unknown":
        if lang == "ko":
            summary += f"""

🎯 감지된 의도: {result.intent}

✨ 개선된 프롬프트:
{result.improved_prompt}
"""
        else:
            summary += f"""

🎯 Detected intent: {result.intent}

✨ Improved prompt:
{result.improved_prompt}
"""

    if hasattr(result, 'recommended_actions') and result.recommended_actions:
        if lang == "ko":
            summary += "\n🔧 권장 액션:\n"
            for action in result.recommended_actions:
                summary += f"- {action['tool']}: {action['reason']}\n"
        else:
            summary += "\n🔧 Recommended actions:\n"
            for action in result.recommended_actions:
                summary += f"- {action['tool']}: {action['reason']}\n"

    # v0.5.0: Add auto-execute hints and smart prompt
    if hasattr(result, 'smart_prompt') and result.smart_prompt:
        if lang == "ko":
            summary += f"""
🚀 스마트 프롬프트 (실제 파일 경로 포함):
{result.smart_prompt}
"""
        else:
            summary += f"""
🚀 Smart prompt (with actual file paths):
{result.smart_prompt}
"""

    if hasattr(result, 'auto_execute') and result.auto_execute:
        auto = result.auto_execute
        if auto.get("enabled"):
            if lang == "ko":
                summary += f"""
🤖 자동 실행 권장:
{auto.get('reason', '')}

권장 순서:
"""
                for action in auto.get("actions", []):
                    summary += f"{action['priority']}. {action['tool']}: {action.get('description', '')}\n"
                summary += f"\n⚠️ 실패 시: {auto.get('fallback', '')}\n"
            else:
                summary += f"""
🤖 Auto-execute recommended:
{auto.get('reason', '')}

Recommended order:
"""
                for action in auto.get("actions", []):
                    summary += f"{action['priority']}. {action['tool']}: {action.get('description', '')}\n"
                summary += f"\n⚠️ Fallback: {auto.get('fallback', '')}\n"

    if hasattr(result, 'missing_info') and result.missing_info:
        if lang == "ko":
            summary += "\n❓ 추가 정보 필요:\n"
            for info in result.missing_info:
                required = " (필수)" if info.get("required") else ""
                summary += f"- {info['question']}{required}\n"
                if info.get("example"):
                    summary += f"  예: {info['example']}\n"
        else:
            summary += "\n❓ Additional information needed:\n"
            for info in result.missing_info:
                required = " (required)" if info.get("required") else ""
                summary += f"- {info['question']}{required}\n"
                if info.get("example"):
                    summary += f"  Example: {info['example']}\n"

    if result.extension_suggestion:
        ext = result.extension_suggestion
        if lang == "ko":
            summary += f"""

✨ {ext['extension']} 제안:
`{ext['command']}` 명령어를 사용하면 더 효율적입니다.
이유: {ext['reason']}

예시: {ext['usage_example']}
"""
        else:
            summary += f"""

✨ {ext['extension']} suggestion:
Consider using `{ext['command']}`.
Reason: {ext['reason']}

Example: {ext['usage_example']}
"""

    return summary.strip()


def _format_problems(problems, lang: str) -> str:
    if not problems:
        return "- 없음" if lang == "ko" else "- None"

    lines = []
    for problem in problems:
        description = problem.get("description", "")
        impact = problem.get("impact", "")
        if lang == "ko":
            lines.append(f"- {description} (영향: {impact})")
        else:
            lines.append(f"- {description} (impact: {impact})")
    return "\n".join(lines)


def _format_suggestions(suggestions, lang: str) -> str:
    if not suggestions:
        return "- 없음" if lang == "ko" else "- None"

    lines = []
    for idx, suggestion in enumerate(suggestions, 1):
        title = suggestion.get("title", "")
        template = suggestion.get("template", "")
        if lang == "ko":
            lines.append(f"{idx}. {title}: {template}")
        else:
            lines.append(f"{idx}. {title}: {template}")
    return "\n".join(lines)


def _format_impact(impact, lang: str) -> str:
    if not impact:
        return "- 없음" if lang == "ko" else "- None"

    messages = impact.get("messages", {})
    code_generation = impact.get("code_generation", {})
    success_rate = impact.get("success_rate", {})

    if lang == "ko":
        return (
            f"- 메시지 수: {messages.get('improvement', 'N/A')}\n"
            f"- 코드 생성: {code_generation.get('improvement', 'N/A')}\n"
            f"- 성공률: {success_rate.get('improvement', 'N/A')}"
        )

    return (
        f"- Messages: {messages.get('improvement', 'N/A')}\n"
        f"- Code generation: {code_generation.get('improvement', 'N/A')}\n"
        f"- Success rate: {success_rate.get('improvement', 'N/A')}"
    )


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
