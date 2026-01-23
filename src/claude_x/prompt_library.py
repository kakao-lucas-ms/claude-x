"""
Prompt pattern library for storing and retrieving best patterns.

This module provides functionality to:
- Store high-quality prompt patterns
- Retrieve patterns by category, tags, or search
- Export patterns for team sharing
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

from .classifier import PromptCategory
from .patterns import (
    PromptPattern,
    PATTERN_TYPES,
    analyze_prompt_for_pattern,
    extract_patterns_from_prompts,
)


class PromptLibrary:
    """Manage a library of prompt patterns."""

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the prompt library.

        Args:
            storage_path: Path to store the library JSON file
        """
        self.storage_path = storage_path or Path.home() / ".claude-x" / "prompt_library.json"
        self.patterns: Dict[str, PromptPattern] = {}
        self._load()

    def _load(self) -> None:
        """Load patterns from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, pattern_data in data.get('patterns', {}).items():
                        category = None
                        if pattern_data.get('category'):
                            try:
                                category = PromptCategory(pattern_data['category'])
                            except ValueError:
                                pass

                        self.patterns[key] = PromptPattern(
                            pattern_type=pattern_data['pattern_type'],
                            template=pattern_data['template'],
                            examples=pattern_data.get('examples', []),
                            category=category,
                            avg_score=pattern_data.get('avg_score', 0.0),
                            usage_count=pattern_data.get('usage_count', 0),
                            tags=set(pattern_data.get('tags', [])),
                            created_at=datetime.fromisoformat(pattern_data.get('created_at', datetime.now().isoformat())),
                        )
            except (json.JSONDecodeError, KeyError):
                self.patterns = {}

    def _save(self) -> None:
        """Save patterns to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'version': '1.0',
            'updated_at': datetime.now().isoformat(),
            'patterns': {
                key: pattern.to_dict()
                for key, pattern in self.patterns.items()
            }
        }

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_pattern(self, pattern: PromptPattern) -> str:
        """
        Add a pattern to the library.

        Args:
            pattern: The pattern to add

        Returns:
            The key assigned to the pattern
        """
        key = f"{pattern.pattern_type}:{len(self.patterns)}"
        self.patterns[key] = pattern
        self._save()
        return key

    def add_from_prompt(self, prompt: str, min_quality: float = 5.0) -> Optional[str]:
        """
        Analyze a prompt and add it to the library if it meets quality threshold.

        Args:
            prompt: The prompt text
            min_quality: Minimum quality score required

        Returns:
            The key if added, None otherwise
        """
        analysis = analyze_prompt_for_pattern(prompt)

        if analysis['quality_score'] < min_quality:
            return None

        category = None
        if analysis['category']:
            try:
                category = PromptCategory(analysis['category'])
            except ValueError:
                pass

        pattern = PromptPattern(
            pattern_type=analysis['pattern_type'],
            template=analysis['template'],
            examples=[prompt[:200]],
            category=category,
            avg_score=analysis['quality_score'],
            usage_count=1,
            tags=set(analysis['tags']),
        )

        return self.add_pattern(pattern)

    def get_pattern(self, key: str) -> Optional[PromptPattern]:
        """
        Get a pattern by key.

        Args:
            key: The pattern key

        Returns:
            The pattern or None
        """
        return self.patterns.get(key)

    def search(
        self,
        category: Optional[PromptCategory] = None,
        tags: Optional[List[str]] = None,
        pattern_type: Optional[str] = None,
        min_score: float = 0.0,
        limit: int = 10,
    ) -> List[PromptPattern]:
        """
        Search patterns by criteria.

        Args:
            category: Filter by category
            tags: Filter by tags (any match)
            pattern_type: Filter by pattern type
            min_score: Minimum quality score
            limit: Maximum results

        Returns:
            List of matching patterns
        """
        results = []

        for pattern in self.patterns.values():
            # Filter by category
            if category and pattern.category != category:
                continue

            # Filter by tags
            if tags and not pattern.tags.intersection(set(tags)):
                continue

            # Filter by pattern type
            if pattern_type and pattern.pattern_type != pattern_type:
                continue

            # Filter by score
            if pattern.avg_score < min_score:
                continue

            results.append(pattern)

        # Sort by score and usage
        results.sort(key=lambda x: (x.avg_score, x.usage_count), reverse=True)

        return results[:limit]

    def get_by_category(self, category: PromptCategory, limit: int = 10) -> List[PromptPattern]:
        """Get patterns by category."""
        return self.search(category=category, limit=limit)

    def get_best_patterns(self, limit: int = 10) -> List[PromptPattern]:
        """Get the best patterns by score."""
        return self.search(min_score=5.0, limit=limit)

    def bulk_import(
        self,
        prompts: List[Dict],
        prompt_key: str = 'first_prompt',
        min_quality: float = 5.0
    ) -> int:
        """
        Bulk import patterns from a list of prompts.

        Args:
            prompts: List of prompt dictionaries
            prompt_key: Key to access prompt text
            min_quality: Minimum quality threshold

        Returns:
            Number of patterns imported
        """
        patterns = extract_patterns_from_prompts(
            prompts,
            min_quality=min_quality,
            prompt_key=prompt_key
        )

        for pattern in patterns:
            self.add_pattern(pattern)

        return len(patterns)

    def export_to_markdown(self, output_path: Optional[Path] = None) -> str:
        """
        Export patterns to markdown format.

        Args:
            output_path: Optional path to save the file

        Returns:
            Markdown content
        """
        lines = [
            "# Prompt Pattern Library",
            "",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
            f"Total patterns: {len(self.patterns)}",
            "",
        ]

        # Group by category
        by_category: Dict[PromptCategory, List[PromptPattern]] = {}
        for pattern in self.patterns.values():
            cat = pattern.category or PromptCategory.EFFICIENCY
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(pattern)

        category_icons = {
            PromptCategory.LEARNING: "📚",
            PromptCategory.IMPLEMENTATION: "🔧",
            PromptCategory.DEBUGGING: "🐛",
            PromptCategory.ARCHITECTURE: "🏗️",
            PromptCategory.EFFICIENCY: "⚡",
        }

        for category, patterns in sorted(by_category.items(), key=lambda x: x[0].value):
            icon = category_icons.get(category, "📝")
            lines.append(f"## {icon} {category.value}")
            lines.append("")

            for i, pattern in enumerate(sorted(patterns, key=lambda x: x.avg_score, reverse=True)[:5], 1):
                lines.append(f"### {i}. {pattern.pattern_type}")
                lines.append("")
                lines.append(f"**Template:**")
                lines.append(f"```")
                lines.append(pattern.template)
                lines.append(f"```")
                lines.append("")
                lines.append(f"**Score:** {pattern.avg_score:.1f}/10 | **Used:** {pattern.usage_count}x")
                if pattern.tags:
                    lines.append(f"**Tags:** {', '.join(sorted(pattern.tags))}")
                lines.append("")

                if pattern.examples:
                    lines.append("**Example:**")
                    lines.append(f"> {pattern.examples[0][:100]}...")
                    lines.append("")

            lines.append("---")
            lines.append("")

        content = '\n'.join(lines)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

        return content

    def export_to_json(self, output_path: Optional[Path] = None) -> Dict:
        """
        Export patterns to JSON format.

        Args:
            output_path: Optional path to save the file

        Returns:
            JSON data
        """
        data = {
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'total_patterns': len(self.patterns),
            'patterns': [p.to_dict() for p in self.patterns.values()],
        }

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        return data

    def get_stats(self) -> Dict:
        """Get library statistics."""
        if not self.patterns:
            return {
                'total_patterns': 0,
                'by_category': {},
                'by_pattern_type': {},
                'avg_score': 0.0,
                'total_usage': 0,
            }

        by_category: Dict[str, int] = {}
        by_pattern_type: Dict[str, int] = {}
        total_score = 0.0
        total_usage = 0

        for pattern in self.patterns.values():
            cat_name = pattern.category.value if pattern.category else '기타'
            by_category[cat_name] = by_category.get(cat_name, 0) + 1
            by_pattern_type[pattern.pattern_type] = by_pattern_type.get(pattern.pattern_type, 0) + 1
            total_score += pattern.avg_score
            total_usage += pattern.usage_count

        return {
            'total_patterns': len(self.patterns),
            'by_category': by_category,
            'by_pattern_type': by_pattern_type,
            'avg_score': round(total_score / len(self.patterns), 2),
            'total_usage': total_usage,
        }

    def clear(self) -> None:
        """Clear all patterns."""
        self.patterns = {}
        self._save()
