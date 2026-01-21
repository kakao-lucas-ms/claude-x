"""
System message filtering for prompt analysis.

This module provides functions to identify and filter out system/meta messages
that should not be included in prompt quality analysis.
"""

import re
from typing import List, Dict, Any, Optional


# Pattern-based filters for known system message types
SYSTEM_MESSAGE_PATTERNS = [
    # Claude Code internal tags
    r'<task-notification>',
    r'<context-summary>',
    r'<system-reminder>',
    r'<session-restore>',
    r'<local-command-',
    r'<command-name>',
    r'<command-message>',
    r'<command-args>\s*</command-args>',  # Empty command args

    # Skill/document loading
    r'\[PLANNING MODE ACTIVATED\]',
    r'\[ULTRAWORK MODE',
    r'\[PENDING TASKS DETECTED\]',
    r'Available skills:',
    r'Available subagents:',
    r'## Planning Session with Prometheus',
    r'### Current Phase: Interview Mode',

    # Interrupts/errors
    r'Request interrupted by user',
    r'\[Request interrupted\]',
    r'^No prompt$',

    # Empty/meaningless messages
    r'^/$',
    r'^/\w+$',  # Simple slash commands like /clear, /help
    r'^\s*$',

    # System context messages
    r'UserPromptSubmit hook success',
    r'SessionStart:clear hook success',
    r'gitStatus: This is the git status',
    r'Current branch:.*\n.*Main branch:',
    r'Platform: darwin',
    r'Working directory:',
    r"Today's date:",
    r'You are Claude Code',
    r'Contents of /Users/.*\.claude/',
    r'# claudeMd\s*\n',
    r'Codebase and user instructions are shown below',
    r'IMPORTANT: this context may or may not be relevant',

    # Sisyphus system messages
    r'# Sisyphus Multi-Agent System',
    r'## INTELLIGENT SKILL ACTIVATION',
    r'The boulder does not stop until it reaches the summit',
    r'\| Agent \| Model \| Purpose \| When to Use \|',
]

# Compiled patterns for performance
_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in SYSTEM_MESSAGE_PATTERNS]


def is_system_message(text: Optional[str]) -> bool:
    """
    Determine if a message is a system/meta message using pattern matching.

    Args:
        text: The message text to check

    Returns:
        True if the message matches system message patterns, False otherwise
    """
    if not text:
        return True

    text = text.strip()
    if not text:
        return True

    for pattern in _COMPILED_PATTERNS:
        if pattern.search(text):
            return True

    return False


def is_likely_system_message(text: Optional[str]) -> bool:
    """
    Use heuristics to determine if a message is likely a system message.

    This catches system messages that don't match specific patterns.

    Args:
        text: The message text to check

    Returns:
        True if the message is likely a system message, False otherwise
    """
    if not text:
        return True

    text = text.strip()
    if not text:
        return True

    # 1. Too short to be meaningful (less than 5 chars)
    if len(text) < 5:
        return True

    # 2. High XML tag ratio (>40% of words are tags)
    words = text.split()
    if words:
        xml_tags = len(re.findall(r'<[^>]+>', text))
        xml_ratio = xml_tags / len(words)
        if xml_ratio > 0.4:
            return True

    # 3. Mostly markdown structure with little content
    stripped = text
    # Remove headers
    stripped = re.sub(r'^#+\s+.*$', '', stripped, flags=re.MULTILINE)
    # Remove list items markers
    stripped = re.sub(r'^\s*[-*]\s+', '', stripped, flags=re.MULTILINE)
    # Remove table rows
    stripped = re.sub(r'^\|.*\|$', '', stripped, flags=re.MULTILINE)
    # Remove horizontal rules
    stripped = re.sub(r'^[-=]{3,}$', '', stripped, flags=re.MULTILINE)

    stripped = stripped.strip()
    if len(stripped) < 10 and len(text) > 50:
        return True

    # 4. Contains mostly code blocks (>80% of content)
    code_block_content = re.findall(r'```[\s\S]*?```', text)
    if code_block_content:
        code_length = sum(len(block) for block in code_block_content)
        if code_length / len(text) > 0.8:
            return True

    return False


def filter_prompts(
    prompts: List[Dict[str, Any]],
    include_system: bool = False,
    prompt_key: str = 'first_prompt'
) -> List[Dict[str, Any]]:
    """
    Filter out system/meta messages from a list of prompts.

    Args:
        prompts: List of prompt dictionaries
        include_system: If True, include system messages (no filtering)
        prompt_key: The key in the dictionary containing the prompt text

    Returns:
        Filtered list of prompts
    """
    if include_system:
        return prompts

    filtered = []
    for p in prompts:
        prompt_text = p.get(prompt_key, '')

        # Skip if matches system message patterns
        if is_system_message(prompt_text):
            continue

        # Skip if heuristics suggest it's a system message
        if is_likely_system_message(prompt_text):
            continue

        filtered.append(p)

    return filtered


def extract_real_prompt(text: Optional[str]) -> Optional[str]:
    """
    Extract the actual user prompt from a message that may contain command wrappers.

    Args:
        text: The raw message text

    Returns:
        The extracted prompt, or None if no real prompt content found
    """
    if not text:
        return None

    # Try to extract from <command-args>
    match = re.search(r'<command-args>"?(.*?)"?</command-args>', text, re.DOTALL)
    if match:
        extracted = match.group(1).strip()
        if extracted and len(extracted) > 3:
            return extracted

    # Try to extract from after command tags
    # Remove command-related tags and see what's left
    cleaned = text
    cleaned = re.sub(r'<command-name>.*?</command-name>', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<command-message>.*?</command-message>', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<command-args>.*?</command-args>', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<local-command-.*?>.*?</local-command-.*?>', '', cleaned, flags=re.DOTALL)

    cleaned = cleaned.strip()
    if cleaned and len(cleaned) > 10:
        return cleaned

    return None


def get_filter_stats(prompts: List[Dict[str, Any]], prompt_key: str = 'first_prompt') -> Dict[str, int]:
    """
    Get statistics about how many prompts would be filtered.

    Args:
        prompts: List of prompt dictionaries
        prompt_key: The key containing the prompt text

    Returns:
        Dictionary with filter statistics
    """
    total = len(prompts)
    pattern_filtered = 0
    heuristic_filtered = 0
    kept = 0

    for p in prompts:
        prompt_text = p.get(prompt_key, '')

        if is_system_message(prompt_text):
            pattern_filtered += 1
        elif is_likely_system_message(prompt_text):
            heuristic_filtered += 1
        else:
            kept += 1

    return {
        'total': total,
        'pattern_filtered': pattern_filtered,
        'heuristic_filtered': heuristic_filtered,
        'total_filtered': pattern_filtered + heuristic_filtered,
        'kept': kept,
        'filter_rate': (pattern_filtered + heuristic_filtered) / total if total > 0 else 0,
    }
