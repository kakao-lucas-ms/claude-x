"""
Prompt pattern extraction system.

This module extracts reusable patterns from high-quality prompts
to build a prompt pattern library for team assets and personal reuse.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime

from .classifier import PromptCategory, classify_prompt
from .scoring import calculate_structure_score, calculate_context_score


@dataclass
class PromptPattern:
    """Represents an extracted prompt pattern."""

    pattern_type: str
    template: str
    examples: List[str] = field(default_factory=list)
    category: Optional[PromptCategory] = None
    avg_score: float = 0.0
    usage_count: int = 0
    tags: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'pattern_type': self.pattern_type,
            'template': self.template,
            'examples': self.examples,
            'category': self.category.value if self.category else None,
            'avg_score': self.avg_score,
            'usage_count': self.usage_count,
            'tags': list(self.tags),
            'created_at': self.created_at.isoformat(),
        }


# Pattern types for classification
PATTERN_TYPES = {
    'target_action': 'Target + Action pattern (e.g., "LoginForm.tsx에 validation 추가해줘")',
    'context_goal': 'Context + Goal pattern (e.g., "현재 상황... 해결책을 찾아줘")',
    'reference_based': 'Reference-based pattern (e.g., "기존 X처럼 Y를 만들어줘")',
    'constraint_based': 'Constraint-based pattern (e.g., "A를 B 없이/만으로 해줘")',
    'step_by_step': 'Step-by-step pattern (e.g., "1. X 2. Y 3. Z 순서로 해줘")',
    'question_driven': 'Question-driven pattern (e.g., "X가 Y인 이유가 뭐야?")',
    'debug_report': 'Debug report pattern (e.g., "에러: X, 기대동작: Y, 실제동작: Z")',
}


def extract_pattern_type(prompt: str) -> str:
    """
    Identify the pattern type of a prompt.

    Args:
        prompt: The prompt text to analyze

    Returns:
        The pattern type identifier
    """
    if not prompt:
        return 'generic'

    prompt_lower = prompt.lower()

    # Target + Action pattern
    target_action_patterns = [
        r'\w+\.(tsx?|jsx?|py|go|rs|java|vue|svelte)\s*(에|에서|를|의)',
        r'[A-Z][a-zA-Z]+(?:Component|Page|Form|Modal)\s*(에|에서|를)',
        r'(src|components|pages|api)/[\w/]+\s*(에|에서)',
    ]
    if any(re.search(p, prompt) for p in target_action_patterns):
        return 'target_action'

    # Context + Goal pattern (check before reference_based since they share keywords)
    context_patterns = [
        r'현재|지금|상황|배경|이유',
        r'currently|now|situation|background|because',
    ]
    goal_patterns = [
        r'해줘|만들어|수정|구현|찾아|해결',
        r'please|create|fix|implement|find|solve',
    ]
    if any(re.search(p, prompt_lower) for p in context_patterns) and \
       any(re.search(p, prompt_lower) for p in goal_patterns):
        return 'context_goal'

    # Reference-based pattern
    reference_patterns = [
        r'처럼|같이|비슷하게|참고|기반으로',
        r'like|similar|based on|reference|same as',
        r'기존|이전|원래',  # Removed 현재 to avoid conflict with context_goal
    ]
    if any(re.search(p, prompt_lower) for p in reference_patterns):
        return 'reference_based'

    # Constraint-based pattern
    constraint_patterns = [
        r'없이|만으로|제외|하지\s*말고',
        r'without|only|except|don\'t|avoid',
        r'최소|최대|이상|이하',
    ]
    if any(re.search(p, prompt_lower) for p in constraint_patterns):
        return 'constraint_based'

    # Step-by-step pattern
    step_patterns = [
        r'[1-9]\.\s*\S+.*[2-9]\.\s*\S+',
        r'첫째|둘째|셋째|먼저|그다음|마지막',
        r'first|second|third|then|finally|step\s*\d',
    ]
    if any(re.search(p, prompt_lower) for p in step_patterns):
        return 'step_by_step'

    # Question-driven pattern
    question_patterns = [
        r'뭐야\??|무엇|왜\??|어떻게\??|언제\??|어디\??',
        r'what\s+(is|are|was|were)|why\s+|how\s+(do|does|to)|when\s+|where\s+|which\s+',
        r'what.*\?|why.*\?|how.*\?',
        r'이유|차이|비교|설명',
        r'difference|explain|reason',
    ]
    if any(re.search(p, prompt_lower) for p in question_patterns):
        return 'question_driven'

    # Debug report pattern
    debug_patterns = [
        r'에러.*발생|오류.*나|버그.*있',
        r'기대.*실제|expected.*actual|want.*but',
        r'스택\s*트레이스|traceback|stack\s*trace',
    ]
    if any(re.search(p, prompt_lower) for p in debug_patterns):
        return 'debug_report'

    return 'generic'


def extract_template(prompt: str, pattern_type: str) -> str:
    """
    Extract a reusable template from a prompt.

    Args:
        prompt: The prompt text
        pattern_type: The pattern type

    Returns:
        A template string with placeholders
    """
    if not prompt:
        return ""

    template = prompt

    # Replace specific file names with placeholders
    # Note: using (?=\s|$|[가-힣]) to handle Korean text following file names
    template = re.sub(
        r'[\w.-]+\.(tsx?|jsx?|py|go|rs|java|vue|svelte|css|scss)(?=\s|$|[가-힣]|[^\w])',
        '[FILE_NAME]',
        template
    )

    # Replace paths with placeholders
    template = re.sub(
        r'(?:src|components|pages|api|utils|lib)/[\w/.-]+',
        '[PATH]',
        template
    )

    # Replace component names
    template = re.sub(
        r'[A-Z][a-zA-Z]+(?:Component|Page|Form|Modal|Hook|Service|Controller|Store)',
        '[COMPONENT]',
        template
    )

    # Replace function/method names
    template = re.sub(
        r'(?:function|함수|method|메서드)\s+\w+',
        '[FUNCTION]',
        template,
        flags=re.IGNORECASE
    )

    # Replace URLs
    template = re.sub(
        r'https?://[^\s]+',
        '[URL]',
        template
    )

    # Replace error messages (common patterns)
    template = re.sub(
        r'(?:TypeError|ReferenceError|SyntaxError|Error):\s*[^\n]+',
        '[ERROR_MESSAGE]',
        template
    )

    # Replace code blocks
    template = re.sub(
        r'```[\w]*\n[\s\S]*?```',
        '[CODE_BLOCK]',
        template
    )

    # Replace inline code
    template = re.sub(
        r'`[^`]+`',
        '[CODE]',
        template
    )

    return template.strip()


def extract_tags(prompt: str) -> Set[str]:
    """
    Extract relevant tags from a prompt.

    Args:
        prompt: The prompt text

    Returns:
        Set of relevant tags
    """
    if not prompt:
        return set()

    tags = set()
    prompt_lower = prompt.lower()

    # Technology tags
    tech_tags = {
        'react': ['react', 'jsx', 'tsx', 'hook', 'useState', 'useEffect'],
        'vue': ['vue', 'vuex', 'nuxt', 'composition api'],
        'typescript': ['typescript', 'ts', 'type', 'interface'],
        'javascript': ['javascript', 'js', 'es6', 'node'],
        'python': ['python', 'py', 'django', 'flask', 'fastapi'],
        'css': ['css', 'scss', 'tailwind', 'styled', 'style'],
        'api': ['api', 'rest', 'graphql', 'endpoint', 'fetch'],
        'database': ['database', 'db', 'sql', 'mongodb', 'postgres'],
        'testing': ['test', 'jest', 'pytest', 'unittest', 'mock'],
        'git': ['git', 'commit', 'branch', 'merge', 'pr'],
    }

    for tag, keywords in tech_tags.items():
        if any(kw in prompt_lower for kw in keywords):
            tags.add(tag)

    # Action tags
    action_patterns = {
        'create': [r'만들어|생성|추가|create|add|new'],
        'fix': [r'수정|고쳐|fix|repair|correct'],
        'refactor': [r'리팩토링|리팩터|refactor|improve|clean'],
        'debug': [r'디버그|버그|debug|error|issue'],
        'explain': [r'설명|알려|explain|what|why|how'],
        'optimize': [r'최적화|성능|optimize|performance|speed'],
        'test': [r'테스트|test|spec|coverage'],
        'document': [r'문서|도큐|document|readme|comment'],
    }

    for tag, patterns in action_patterns.items():
        if any(re.search(p, prompt_lower) for p in patterns):
            tags.add(tag)

    return tags


def calculate_pattern_quality(prompt: str) -> float:
    """
    Calculate overall quality score for a prompt pattern.

    Args:
        prompt: The prompt text

    Returns:
        Quality score (0-10)
    """
    if not prompt:
        return 0.0

    structure_score = calculate_structure_score(prompt)
    context_score = calculate_context_score(prompt)

    # Average of structure and context scores
    return round((structure_score + context_score) / 2, 2)


def analyze_prompt_for_pattern(prompt: str) -> Dict:
    """
    Analyze a prompt and extract pattern information.

    Args:
        prompt: The prompt text

    Returns:
        Dictionary with pattern analysis results
    """
    if not prompt:
        return {
            'pattern_type': 'generic',
            'template': '',
            'category': None,
            'tags': [],
            'quality_score': 0.0,
        }

    pattern_type = extract_pattern_type(prompt)
    template = extract_template(prompt, pattern_type)
    category = classify_prompt(prompt)
    tags = extract_tags(prompt)
    quality_score = calculate_pattern_quality(prompt)

    return {
        'pattern_type': pattern_type,
        'pattern_description': PATTERN_TYPES.get(pattern_type, 'Generic pattern'),
        'template': template,
        'category': category.value,
        'category_icon': {
            PromptCategory.LEARNING: "📚",
            PromptCategory.IMPLEMENTATION: "🔧",
            PromptCategory.DEBUGGING: "🐛",
            PromptCategory.ARCHITECTURE: "🏗️",
            PromptCategory.EFFICIENCY: "⚡",
        }.get(category, "📝"),
        'tags': list(tags),
        'quality_score': quality_score,
    }


def extract_patterns_from_prompts(
    prompts: List[Dict],
    min_quality: float = 5.0,
    prompt_key: str = 'first_prompt'
) -> List[PromptPattern]:
    """
    Extract patterns from a list of prompts.

    Args:
        prompts: List of prompt dictionaries
        min_quality: Minimum quality score to include
        prompt_key: Key to access prompt text in dictionary

    Returns:
        List of extracted patterns
    """
    patterns_by_type: Dict[str, PromptPattern] = {}

    for p in prompts:
        prompt_text = p.get(prompt_key, '')
        if not prompt_text:
            continue

        analysis = analyze_prompt_for_pattern(prompt_text)

        if analysis['quality_score'] < min_quality:
            continue

        pattern_type = analysis['pattern_type']
        template = analysis['template']

        # Group by pattern type and template similarity
        pattern_key = f"{pattern_type}:{template[:50]}"

        if pattern_key in patterns_by_type:
            # Update existing pattern
            existing = patterns_by_type[pattern_key]
            existing.examples.append(prompt_text[:200])
            existing.usage_count += 1
            existing.avg_score = (
                (existing.avg_score * (existing.usage_count - 1) + analysis['quality_score'])
                / existing.usage_count
            )
            existing.tags.update(analysis['tags'])
        else:
            # Create new pattern
            category = classify_prompt(prompt_text)
            patterns_by_type[pattern_key] = PromptPattern(
                pattern_type=pattern_type,
                template=template,
                examples=[prompt_text[:200]],
                category=category,
                avg_score=analysis['quality_score'],
                usage_count=1,
                tags=set(analysis['tags']),
            )

    # Sort by average score and usage count
    patterns = list(patterns_by_type.values())
    patterns.sort(key=lambda x: (x.avg_score * x.usage_count), reverse=True)

    return patterns


def get_pattern_recommendations(
    category: Optional[PromptCategory] = None,
    tags: Optional[List[str]] = None,
    limit: int = 5
) -> List[Dict]:
    """
    Get pattern recommendations based on category and tags.

    This is a placeholder for pattern recommendation logic.
    In a full implementation, this would query a pattern database.

    Args:
        category: Filter by category
        tags: Filter by tags
        limit: Maximum number of recommendations

    Returns:
        List of recommended patterns
    """
    # Template recommendations based on category
    recommendations = {
        PromptCategory.LEARNING: [
            {
                'template': '[TOPIC]이 뭐야? 간단한 예시와 함께 설명해줘',
                'description': 'Basic explanation request',
            },
            {
                'template': '[A]와 [B]의 차이점이 뭐야?',
                'description': 'Comparison request',
            },
        ],
        PromptCategory.IMPLEMENTATION: [
            {
                'template': '[PATH]에 [FEATURE]를 구현해줘. [CONSTRAINT]',
                'description': 'Feature implementation with path and constraints',
            },
            {
                'template': '[EXISTING_CODE] 처럼 [NEW_FEATURE]를 만들어줘',
                'description': 'Reference-based implementation',
            },
        ],
        PromptCategory.DEBUGGING: [
            {
                'template': '[FILE]에서 [ERROR] 에러가 발생해. 기대동작: [EXPECTED], 실제동작: [ACTUAL]',
                'description': 'Structured bug report',
            },
            {
                'template': '[CODE]가 왜 [ISSUE]한지 분석해줘',
                'description': 'Debug analysis request',
            },
        ],
        PromptCategory.ARCHITECTURE: [
            {
                'template': '[CODE/MODULE]을 [PATTERN]으로 리팩토링해줘',
                'description': 'Refactoring with pattern',
            },
            {
                'template': '[CURRENT_STRUCTURE]의 구조를 개선해줘. 목표: [GOAL]',
                'description': 'Architecture improvement',
            },
        ],
        PromptCategory.EFFICIENCY: [
            {
                'template': '[ACTION]',
                'description': 'Simple action request',
            },
        ],
    }

    if category:
        results = recommendations.get(category, [])
    else:
        results = []
        for cat_recs in recommendations.values():
            results.extend(cat_recs)

    return results[:limit]
