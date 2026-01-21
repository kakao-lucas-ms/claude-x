"""
New scoring model for prompt quality analysis.

This module provides a redesigned scoring system that focuses on
measurable metrics and better reflects actual prompt quality.
"""

import re
from typing import Optional, Tuple


def detect_console_log_ratio(prompt: str) -> Tuple[float, bool]:
    """
    Detect the ratio of console/debug log content in a prompt.

    Returns:
        Tuple of (log_ratio, has_question)
        - log_ratio: 0.0-1.0, proportion of prompt that looks like logs
        - has_question: whether there's a clear question/request with the logs
    """
    if not prompt:
        return 0.0, False

    # Patterns that indicate console/debug log output
    log_patterns = [
        r'\[[\w-]+\]\s+[\w:]+',  # [Profile] Page loaded:
        r'client-logger\.ts:\d+',  # client-logger.ts:24
        r'logger-console\.ts:\d+',  # logger-console.ts:19
        r'\[GET\]|\[POST\]|\[PUT\]|\[DELETE\]',  # HTTP methods
        r'\[GET\]\[\d{3}\]|\[POST\]\[\d{3}\]',  # [GET][200]
        r':\s*\{[^}]+\}',  # : {key: value}
        r'MutationObserver|IntersectionObserver',  # Browser APIs
        r'console\.(log|warn|error|info|debug)',  # console methods
        r'^\s*\w+:\s*[\'"]?[\w./-]+[\'"]?,?\s*$',  # key: value lines
        r'isLoading:\s*(true|false)',  # state properties
        r'pageCount:\s*\d+',  # common log properties
        r'hasNextPage:\s*(true|false)',
        r'\{[^}]*:\s*[^}]*,\s*[^}]*:\s*[^}]*\}',  # {a: b, c: d} objects
    ]

    # Count log-like lines
    lines = prompt.split('\n')
    log_line_count = 0
    for line in lines:
        if any(re.search(p, line, re.IGNORECASE) for p in log_patterns):
            log_line_count += 1

    # Also check for character-based ratio (log content often has special patterns)
    log_chars = 0
    total_chars = len(prompt)

    # Match common log output patterns
    for match in re.finditer(r'\[[^\]]+\]|\{[^}]+\}|:\s*\d+(?:px|%|ms)?', prompt):
        log_chars += len(match.group())

    char_ratio = log_chars / max(total_chars, 1)
    line_ratio = log_line_count / max(len(lines), 1)

    # Additional heuristic: count log file references (strong indicator of log dump)
    log_file_refs = len(re.findall(r'(?:client-logger|logger-console|\.ts:\d+|\.js:\d+)', prompt, re.IGNORECASE))

    # If many log file references, boost the ratio
    if log_file_refs >= 5:
        # Strong log dump indicator
        log_ratio = max(char_ratio, line_ratio, 0.6)
    elif log_file_refs >= 2:
        log_ratio = max(char_ratio, line_ratio, 0.4)
    else:
        log_ratio = max(char_ratio, line_ratio)

    # Also check for very long prompts with many lines - likely log dumps
    if len(prompt) > 5000 and len(lines) > 20 and line_ratio > 0.5:
        log_ratio = max(log_ratio, 0.7)

    # Check if there's a question or request accompanying the logs
    question_patterns = [
        r'\?\s*$',  # ends with ?
        r'왜.*[?]?|뭐야|뭘까|어떻게|어떨까|이유|원인',  # Korean questions
        r'why|what|how|explain|help|fix|solve|문제|에러|오류',  # Questions/issues
        r'해줘|해봐|알려|설명|분석|검토|확인',  # Korean requests
        r'이게 맞아|잘 된거야|정상이야',  # Verification questions
    ]

    has_question = any(re.search(p, prompt, re.IGNORECASE) for p in question_patterns)

    return log_ratio, has_question


def calculate_context_dependency_penalty(prompt: str) -> float:
    """
    Calculate penalty for prompts that are too context-dependent.

    Prompts that heavily rely on "위", "아까", "저거" etc. without
    providing actual context should be penalized.

    Returns:
        Penalty value (0.0-5.0) to subtract from scores
    """
    if not prompt:
        return 0.0

    # Patterns indicating context dependency
    context_dependent_patterns = [
        r'^(그|저|이)\s*(거|것|건)\s',  # 그거, 저것, 이건
        r'위(의|에서)?\s*(방법|코드|내용)',  # 위의 방법
        r'아까\s*(말한|언급|했던)',  # 아까 말한
        r'^(ㅇㅇ|ㅇㅋ|ㄱㄱ|ㄴㄴ)\s',  # 단축어 시작
        r'^(ok|okay|yes|no|응|어|넵)\s',  # 짧은 동의
        r'방금\s*(그|전)',  # 방금 그
        r'직전에?',  # 직전에
    ]

    penalty = 0.0

    for pattern in context_dependent_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            penalty += 1.0

    # Very short prompts with context dependency are worse
    if len(prompt) < 30:
        for pattern in context_dependent_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                penalty += 1.5

    # Check for prompts that are ONLY context references
    if len(prompt) < 50 and re.match(r'^(그|저|이|위|아까|방금|직전)', prompt):
        penalty += 2.0

    return min(penalty, 5.0)


def calculate_structure_score(prompt: str) -> float:
    """
    Calculate prompt structure score based on measurable elements.

    Evaluates:
    - Goal statement presence (+2)
    - Specific target mentioned (+2)
    - Constraints specified (+2)
    - Examples/references provided (+2)
    - Appropriate length (+2)
    - Penalties for console-log-only or context-dependent prompts

    Args:
        prompt: The prompt text to evaluate

    Returns:
        Structure score (0-10)
    """
    if not prompt:
        return 0.0

    score = 0.0

    # Check for console log content
    log_ratio, has_question = detect_console_log_ratio(prompt)

    # If prompt contains significant logs without a clear question, penalize structure
    if log_ratio > 0.3 and not has_question:
        # Just pasted logs without asking anything = bad structure
        return max(1.0, 3.0 - log_ratio * 4)

    # Even with question, heavy log content reduces structure score
    if log_ratio > 0.4:
        # Log-heavy prompts are not good templates for reuse
        return max(2.0, 4.0 - log_ratio * 3)

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

    # Apply context dependency penalty
    context_penalty = calculate_context_dependency_penalty(prompt)
    score = max(0.0, score - context_penalty)

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
    - Penalties for log-only or context-dependent prompts

    Args:
        prompt: The prompt text to evaluate

    Returns:
        Context score (0-10)
    """
    if not prompt:
        return 0.0

    score = 0.0

    # Check for console log content
    log_ratio, has_question = detect_console_log_ratio(prompt)

    # If prompt contains significant logs without a clear question, it lacks real context
    if log_ratio > 0.3 and not has_question:
        return max(1.0, 3.0 - log_ratio * 4)

    # Even with question, heavy log content reduces context score
    if log_ratio > 0.4:
        return max(2.0, 4.0 - log_ratio * 3)

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

    # 5. Background explanation (+2) - but not just context-dependent words
    context_patterns = [
        r'현재|지금|기존|이전|원래|상황',
        r'currently|now|existing|previous|original|situation',
        r'배경|이유|목적|왜냐하면',
        r'background|reason|purpose|because',
    ]
    if any(re.search(p, prompt, re.IGNORECASE) for p in context_patterns):
        score += 2.0

    # Apply context dependency penalty
    context_penalty = calculate_context_dependency_penalty(prompt)
    score = max(0.0, score - context_penalty)

    return min(score, 10.0)


def calculate_efficiency_score(message_count: int) -> float:
    """
    Calculate efficiency score based on conversation length.

    Shorter conversations (fewer back-and-forth) indicate clearer prompts.
    More stringent scoring - 10/10 is harder to achieve.

    Args:
        message_count: Total number of messages in the turn

    Returns:
        Efficiency score (0-10)
    """
    if message_count <= 2:
        return 10.0  # Single exchange = perfect efficiency
    elif message_count <= 4:
        return 9.0
    elif message_count <= 6:
        return 8.0
    elif message_count <= 10:
        return 7.0
    elif message_count <= 15:
        return 6.0
    elif message_count <= 25:
        return 5.0
    elif message_count <= 40:
        return 4.0
    elif message_count <= 60:
        return 3.0
    elif message_count <= 100:
        return 2.0
    else:
        return 1.0


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

    # Apply penalty for low quality prompts (Option B from plan)
    # If structure or context is too low, the prompt is not a good template
    quality_penalty = 1.0
    if structure < 2.0 or context < 1.0:
        quality_penalty = 0.8
    if structure < 1.0 and context < 1.0:
        quality_penalty = 0.6

    composite = composite * quality_penalty

    return {
        'structure_score': round(structure, 2),
        'context_score': round(context, 2),
        'productivity_score': round(productivity, 2),
        'efficiency_score': round(efficiency, 2),
        'diversity_score': round(diversity, 2),
        'composite_score': round(composite, 2),
        'quality_penalty': quality_penalty,
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
