"""
New scoring model for prompt quality analysis.

This module provides a redesigned scoring system that focuses on
measurable metrics and better reflects actual prompt quality.
"""

import re
from typing import Optional


def calculate_structure_score(prompt: str) -> float:
    """
    Calculate prompt structure score based on measurable elements.

    Evaluates:
    - Goal statement presence (+2)
    - Specific target mentioned (+2)
    - Constraints specified (+2)
    - Examples/references provided (+2)
    - Appropriate length (+2)

    Args:
        prompt: The prompt text to evaluate

    Returns:
        Structure score (0-10)
    """
    if not prompt:
        return 0.0

    score = 0.0

    # 1. Goal statement presence (+2)
    goal_patterns = [
        r'해줘|하고\s*싶|만들어|구현해|추가해|수정해|삭제해|변경해|개선해',
        r'please|want to|create|implement|add|fix|remove|update|improve',
        r'알려줘|설명해|찾아|분석해|검토해',
        r'explain|find|analyze|review|help',
    ]
    if any(re.search(p, prompt, re.IGNORECASE) for p in goal_patterns):
        score += 2.0

    # 2. Specific target mentioned (+2)
    target_patterns = [
        r'\w+\.(tsx?|jsx?|py|go|rs|java|vue|svelte|css|scss)',  # File names
        r'[A-Z][a-zA-Z]+(?:Component|Page|Form|Modal|Hook|Service|Controller|Store)',  # Components
        r'(?:함수|function|method|class|컴포넌트|component|모듈|module)',  # Type mentions
        r'src/|components/|pages/|api/|utils/|lib/',  # Path patterns
    ]
    if any(re.search(p, prompt, re.IGNORECASE) for p in target_patterns):
        score += 2.0

    # 3. Constraints specified (+2)
    constraint_patterns = [
        r'하지\s*말고|없이|대신|만\s|만으로|제외',
        r'without|instead|only|don\'t|except|but not|avoid',
        r'최소|최대|이상|이하|미만|초과',
        r'minimum|maximum|at least|at most|less than|more than',
    ]
    if any(re.search(p, prompt, re.IGNORECASE) for p in constraint_patterns):
        score += 2.0

    # 4. Examples/references provided (+2)
    example_patterns = [
        r'예를\s*들어|예시|처럼|같이|참고|비슷하게',
        r'like|example|similar|reference|such as|e\.g\.',
        r'기존|현재|이전|원래|기반으로',
        r'existing|current|previous|original|based on',
    ]
    if any(re.search(p, prompt, re.IGNORECASE) for p in example_patterns):
        score += 2.0

    # 5. Appropriate length (+2 for optimal, +1 for acceptable)
    length = len(prompt)
    if 20 <= length <= 500:
        score += 2.0
    elif 10 <= length <= 1000:
        score += 1.0

    return min(score, 10.0)


def calculate_context_score(prompt: str) -> float:
    """
    Calculate context score based on provided information.

    Evaluates:
    - File/path mentions (+2)
    - Technology stack mentions (+2)
    - Code blocks included (+2)
    - Error/log information (+2)
    - Background explanation (+2)

    Args:
        prompt: The prompt text to evaluate

    Returns:
        Context score (0-10)
    """
    if not prompt:
        return 0.0

    score = 0.0

    # 1. File/path mentions (+2)
    if re.search(r'[/\\][\w.-]+|[\w.-]+\.[a-z]{2,4}\b', prompt):
        score += 2.0

    # 2. Technology stack mentions (+2)
    tech_keywords = [
        'react', 'vue', 'angular', 'svelte', 'next', 'nuxt',
        'typescript', 'javascript', 'python', 'node', 'go', 'rust',
        'api', 'rest', 'graphql', 'grpc', 'websocket',
        'database', 'sql', 'mongodb', 'redis', 'postgres',
        'css', 'tailwind', 'scss', 'styled',
        'docker', 'kubernetes', 'aws', 'gcp', 'azure',
        'git', 'github', 'gitlab',
    ]
    if any(kw in prompt.lower() for kw in tech_keywords):
        score += 2.0

    # 3. Code blocks included (+2)
    if '```' in prompt or re.search(r'`[^`]+`', prompt):
        score += 2.0

    # 4. Error/log information (+2)
    error_patterns = [
        r'error|exception|traceback|stack\s*trace',
        r'에러|오류|실패|안\s*됨|작동.*않|문제',
        r'warning|failed|crash|bug|issue',
        r'\d{3}\s*(error|status)',  # HTTP status codes
    ]
    if any(re.search(p, prompt, re.IGNORECASE) for p in error_patterns):
        score += 2.0

    # 5. Background explanation (+2)
    context_patterns = [
        r'현재|지금|기존|이전|원래|상황',
        r'currently|now|existing|previous|original|situation',
        r'배경|이유|목적|왜냐하면',
        r'background|reason|purpose|because',
    ]
    if any(re.search(p, prompt, re.IGNORECASE) for p in context_patterns):
        score += 2.0

    return min(score, 10.0)


def calculate_efficiency_score(message_count: int) -> float:
    """
    Calculate efficiency score based on conversation length.

    Shorter conversations (fewer back-and-forth) indicate clearer prompts.

    Args:
        message_count: Total number of messages in the turn

    Returns:
        Efficiency score (0-10)
    """
    if message_count <= 5:
        return 10.0
    elif message_count <= 10:
        return 9.0
    elif message_count <= 20:
        return 8.0
    elif message_count <= 35:
        return 6.0
    elif message_count <= 50:
        return 5.0
    elif message_count <= 75:
        return 4.0
    elif message_count <= 100:
        return 3.0
    else:
        return 2.0


def calculate_diversity_score(language_diversity: int) -> float:
    """
    Calculate diversity score based on language diversity.

    More diverse outputs indicate richer results.

    Args:
        language_diversity: Number of different programming languages used

    Returns:
        Diversity score (0-10)
    """
    if language_diversity >= 4:
        return 10.0
    elif language_diversity >= 3:
        return 8.0
    elif language_diversity >= 2:
        return 6.0
    elif language_diversity >= 1:
        return 4.0
    else:
        return 0.0


def calculate_productivity_score(total_lines: int, max_lines: int = 1000) -> float:
    """
    Calculate productivity score based on code output.

    Args:
        total_lines: Total lines of code generated
        max_lines: Maximum lines for normalization

    Returns:
        Productivity score (0-10)
    """
    if max_lines <= 0:
        return 0.0

    normalized = (total_lines or 0) / max_lines * 10
    return min(normalized, 10.0)


def calculate_composite_score_v2(
    prompt: str,
    code_count: int,
    total_lines: int,
    message_count: int,
    language_diversity: int,
    max_lines: int = 1000,
) -> dict:
    """
    Calculate new composite score with detailed breakdown.

    Weights:
    - Structure score: 25%
    - Context score: 25%
    - Productivity: 20%
    - Efficiency: 15%
    - Diversity: 15%

    Args:
        prompt: The prompt text
        code_count: Number of code snippets generated
        total_lines: Total lines of code
        message_count: Number of messages in conversation
        language_diversity: Number of different languages
        max_lines: Maximum lines for normalization

    Returns:
        Dictionary with individual scores and composite score
    """
    # Calculate individual scores
    structure = calculate_structure_score(prompt)
    context = calculate_context_score(prompt)
    productivity = calculate_productivity_score(total_lines, max_lines)
    efficiency = calculate_efficiency_score(message_count)
    diversity = calculate_diversity_score(language_diversity)

    # Calculate composite score with weights
    composite = (
        structure * 0.25 +
        context * 0.25 +
        productivity * 0.20 +
        efficiency * 0.15 +
        diversity * 0.15
    )

    return {
        'structure_score': round(structure, 2),
        'context_score': round(context, 2),
        'productivity_score': round(productivity, 2),
        'efficiency_score': round(efficiency, 2),
        'diversity_score': round(diversity, 2),
        'composite_score': round(composite, 2),
    }


# Legacy scoring functions for backwards compatibility

def calculate_legacy_efficiency(code_count: int, user_prompt_count: int) -> float:
    """Legacy efficiency: code generated per prompt."""
    if user_prompt_count == 0:
        return 0.0
    return round(code_count / user_prompt_count, 2)


def calculate_legacy_clarity(message_count: int) -> float:
    """Legacy clarity: inverse of message count."""
    if message_count == 0:
        return 0.0
    return round(100.0 / message_count, 2)


def calculate_legacy_quality(sensitive_count: int, language_diversity: int) -> int:
    """Legacy quality: based on sensitive data and diversity."""
    if sensitive_count == 0 and language_diversity >= 3:
        return 10
    elif sensitive_count == 0 and language_diversity >= 2:
        return 8
    elif sensitive_count == 0:
        return 6
    elif language_diversity >= 3:
        return 5
    else:
        return 3


def calculate_legacy_composite(
    efficiency_score: float,
    clarity_score: float,
    productivity_score: float,
    quality_score: int,
    max_lines: int
) -> float:
    """
    Calculate legacy composite score.

    Weights: efficiency 40%, clarity 30%, productivity 20%, quality 10%
    """
    normalized_productivity = (productivity_score or 0) / max(max_lines, 1) * 10

    return round(
        (efficiency_score or 0) * 0.4 +
        (clarity_score or 0) * 0.3 +
        normalized_productivity * 0.2 +
        quality_score * 0.1,
        2
    )
