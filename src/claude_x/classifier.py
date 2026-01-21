"""
Prompt category classification system.

This module provides rule-based classification of prompts into categories:
- Learning/Exploration (학습/탐색)
- Implementation (기능 구현)
- Debugging (디버깅)
- Architecture (아키텍처)
- Efficiency (효율적 요청)
"""

import re
from enum import Enum
from typing import Dict, List, Optional


class PromptCategory(Enum):
    """Prompt category enumeration."""
    LEARNING = "학습/탐색"
    IMPLEMENTATION = "기능 구현"
    DEBUGGING = "디버깅"
    ARCHITECTURE = "아키텍처"
    EFFICIENCY = "효율적 요청"


# Category classification rules
CATEGORY_RULES: Dict[PromptCategory, Dict] = {
    PromptCategory.LEARNING: {
        'keywords': [
            # Korean
            '설명', '뭐야', '알아봐', '이해', '분석', '찾아', '검색',
            '차이', '비교', '어떻게', '왜', '무엇', '뭔지', '알려',
            # English
            'explain', 'what is', 'understand', 'analyze', 'find', 'search',
            'difference', 'compare', 'how does', 'why', 'what', 'tell me',
            'learn', 'research', 'investigate', 'explore',
        ],
        'patterns': [
            r'어떻게.*동작', r'왜.*하는', r'차이.*뭐', r'뭔지.*알려',
            r'how.*work', r'what.*difference', r'why.*does',
            r'.*이\s*뭐야', r'.*가\s*뭐야', r'.*란\s*뭐',
        ],
        'weight': 1.0,
    },
    PromptCategory.IMPLEMENTATION: {
        'keywords': [
            # Korean
            '구현', '만들어', '추가', '작성', '생성', '개발', '작업',
            '붙여', '넣어', '새로', '기능',
            # English
            'implement', 'create', 'add', 'write', 'build', 'develop',
            'make', 'generate', 'new', 'feature', 'integrate',
        ],
        'patterns': [
            r'기능.*추가', r'컴포넌트.*만들', r'API.*작성',
            r'add.*feature', r'create.*component', r'build.*api',
            r'만들어.*줘', r'추가해.*줘', r'작성해.*줘', r'구현해.*줘',
        ],
        'weight': 1.0,
    },
    PromptCategory.DEBUGGING: {
        'keywords': [
            # Korean
            '버그', '수정', '고쳐', '에러', '오류', '안됨', '실패',
            '문제', '해결', '이상', '깨짐', '안돼', '작동',
            # English
            'bug', 'fix', 'error', 'issue', 'broken', 'fail', 'not working',
            'problem', 'solve', 'wrong', 'crash', 'debug',
        ],
        'patterns': [
            r'왜.*안', r'에러.*발생', r'작동.*않',
            r'why.*not', r'error.*when', r"doesn't.*work", r"won't.*work",
            r'.*안\s*됨', r'.*안\s*돼', r'.*이상해',
            r'버그.*수정', r'에러.*고쳐', r'오류.*수정',
            r'fix.*bug', r'debug.*issue', r'solve.*problem',
            r'수정해.*줘', r'고쳐.*줘', r'해결해.*줘',
            r'this.*work', r'not.*work', r'why.*this',
        ],
        'weight': 1.2,  # Slightly higher weight for debugging keywords
    },
    PromptCategory.ARCHITECTURE: {
        'keywords': [
            # Korean
            '설계', '구조', '아키텍처', '패턴', '리팩토링', '최적화',
            '성능', '개선', '정리', '분리', '모듈', '의존성',
            # English
            'design', 'structure', 'architecture', 'pattern', 'refactor', 'optimize',
            'performance', 'improve', 'organize', 'separate', 'module', 'dependency',
            'clean', 'migrate', 'upgrade',
        ],
        'patterns': [
            r'어떻게.*설계', r'구조.*개선', r'패턴.*적용',
            r'how.*design', r'improve.*structure', r'apply.*pattern',
            r'리팩토링.*해', r'최적화.*해',
            r'리팩토링해.*줘', r'최적화해.*줘', r'개선해.*줘', r'정리해.*줘',
            r'refactor.*code', r'optimize.*performance', r'clean.*up',
        ],
        'weight': 1.0,
    },
    PromptCategory.EFFICIENCY: {
        # This is the fallback category - no specific keywords
        'keywords': [],
        'patterns': [],
        'weight': 0.5,
    },
}


def classify_prompt(prompt: str) -> PromptCategory:
    """
    Classify a prompt into a category using rule-based matching.

    Args:
        prompt: The prompt text to classify

    Returns:
        The detected PromptCategory
    """
    if not prompt:
        return PromptCategory.EFFICIENCY

    prompt_lower = prompt.lower()
    scores: Dict[PromptCategory, float] = {cat: 0.0 for cat in PromptCategory}

    for category, rules in CATEGORY_RULES.items():
        weight = rules.get('weight', 1.0)

        # Keyword matching (+1 per keyword)
        for keyword in rules.get('keywords', []):
            if keyword in prompt_lower:
                scores[category] += 1.0 * weight

        # Pattern matching (+2 per pattern, patterns are more specific)
        for pattern in rules.get('patterns', []):
            if re.search(pattern, prompt_lower):
                scores[category] += 2.0 * weight

    # Get category with highest score
    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]

    # If score is too low, fall back to EFFICIENCY
    if best_score < 1.0:
        return PromptCategory.EFFICIENCY

    return best_category


def classify_prompt_with_scores(prompt: str) -> Dict:
    """
    Classify a prompt and return detailed scoring information.

    Args:
        prompt: The prompt text to classify

    Returns:
        Dictionary with category, confidence, and all scores
    """
    if not prompt:
        return {
            'category': PromptCategory.EFFICIENCY,
            'confidence': 0.0,
            'scores': {cat: 0.0 for cat in PromptCategory},
        }

    prompt_lower = prompt.lower()
    scores: Dict[PromptCategory, float] = {cat: 0.0 for cat in PromptCategory}

    for category, rules in CATEGORY_RULES.items():
        weight = rules.get('weight', 1.0)

        for keyword in rules.get('keywords', []):
            if keyword in prompt_lower:
                scores[category] += 1.0 * weight

        for pattern in rules.get('patterns', []):
            if re.search(pattern, prompt_lower):
                scores[category] += 2.0 * weight

    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]
    total_score = sum(scores.values())

    # Calculate confidence (0-1)
    if total_score > 0:
        confidence = best_score / total_score
    else:
        confidence = 0.0

    if best_score < 1.0:
        best_category = PromptCategory.EFFICIENCY
        confidence = 0.0

    return {
        'category': best_category,
        'confidence': round(confidence, 2),
        'scores': {cat.value: round(score, 2) for cat, score in scores.items()},
    }


def get_category_icon(category: PromptCategory) -> str:
    """Get emoji icon for a category."""
    icons = {
        PromptCategory.LEARNING: "📚",
        PromptCategory.IMPLEMENTATION: "🔧",
        PromptCategory.DEBUGGING: "🐛",
        PromptCategory.ARCHITECTURE: "🏗️",
        PromptCategory.EFFICIENCY: "⚡",
    }
    return icons.get(category, "📝")


def get_category_description(category: PromptCategory) -> str:
    """Get description for a category."""
    descriptions = {
        PromptCategory.LEARNING: "탐색, 리서치, 이해를 위한 프롬프트",
        PromptCategory.IMPLEMENTATION: "새 기능, 코드 작성을 위한 프롬프트",
        PromptCategory.DEBUGGING: "버그 수정, 문제 해결을 위한 프롬프트",
        PromptCategory.ARCHITECTURE: "설계, 구조, 패턴 관련 프롬프트",
        PromptCategory.EFFICIENCY: "짧고 효율적인 요청",
    }
    return descriptions.get(category, "")


# Legacy category mapping for backwards compatibility
LEGACY_CATEGORY_MAP = {
    '코드 리뷰': PromptCategory.ARCHITECTURE,
    '테스트': PromptCategory.IMPLEMENTATION,
    '버그 수정': PromptCategory.DEBUGGING,
    '기능 구현': PromptCategory.IMPLEMENTATION,
    '리팩토링': PromptCategory.ARCHITECTURE,
    '문서화': PromptCategory.LEARNING,
    '기타': PromptCategory.EFFICIENCY,
}


def legacy_to_new_category(legacy_category: str) -> PromptCategory:
    """Convert legacy category to new category."""
    return LEGACY_CATEGORY_MAP.get(legacy_category, PromptCategory.EFFICIENCY)
