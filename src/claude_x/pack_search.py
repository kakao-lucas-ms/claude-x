"""External pack search module for RAG-style reference.

This module provides search functionality over installed external template packs.
It indexes markdown files and returns relevant snippets based on user queries.
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from collections import defaultdict


@dataclass
class SearchResult:
    """A search result from external packs."""
    pack_id: str
    pack_name: str
    file_name: str
    title: str
    content: str
    score: float
    source_url: Optional[str] = None


@dataclass
class PackIndex:
    """Index for a single pack's content."""
    pack_id: str
    pack_name: str
    source_url: str
    documents: List[Dict[str, Any]] = field(default_factory=list)


class PackSearchEngine:
    """Search engine for external template packs."""

    def __init__(self):
        self.packs_dir = Path.home() / ".claude-x" / "best_practices"
        self.indices: Dict[str, PackIndex] = {}
        self._load_indices()

    def _load_indices(self):
        """Load and index all installed packs."""
        if not self.packs_dir.exists():
            return

        # Load installed.json to get pack info
        installed_file = self.packs_dir / "installed.json"
        if not installed_file.exists():
            return

        import json
        with open(installed_file, 'r', encoding='utf-8') as f:
            installed = json.load(f)

        # Load registry for pack metadata
        from .template_registry import get_registry
        registry = get_registry()

        for pack_id, info in installed.items():
            pack = registry.get_pack(pack_id)
            if not pack:
                continue

            pack_path = Path(info["path"])
            if not pack_path.exists():
                continue

            index = PackIndex(
                pack_id=pack_id,
                pack_name=pack.name,
                source_url=pack.source,
            )

            # Index all markdown files
            for md_file in pack_path.glob("**/*.md"):
                docs = self._parse_markdown(md_file)
                index.documents.extend(docs)

            self.indices[pack_id] = index

    def _parse_markdown(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse a markdown file into searchable documents."""
        documents = []

        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return documents

        # Split by headers
        sections = re.split(r'^(#{1,3})\s+(.+)$', content, flags=re.MULTILINE)

        current_title = file_path.stem
        current_content = []

        i = 0
        while i < len(sections):
            section = sections[i]

            if section.startswith('#'):
                # Save previous section
                if current_content:
                    text = '\n'.join(current_content).strip()
                    if text and len(text) > 50:  # Skip very short sections
                        documents.append({
                            'file': file_path.name,
                            'title': current_title,
                            'content': text,
                            'keywords': self._extract_keywords(text),
                        })

                # Start new section
                if i + 1 < len(sections):
                    current_title = sections[i + 1]
                    i += 2
                    current_content = []
                else:
                    i += 1
            else:
                current_content.append(section)
                i += 1

        # Save last section
        if current_content:
            text = '\n'.join(current_content).strip()
            if text and len(text) > 50:
                documents.append({
                    'file': file_path.name,
                    'title': current_title,
                    'content': text,
                    'keywords': self._extract_keywords(text),
                })

        return documents

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for matching."""
        # Common programming terms and patterns
        keywords = []

        # Extract code-related terms
        code_patterns = [
            r'\b(api|endpoint|route|http|rest|graphql)\b',
            r'\b(bug|fix|error|exception|debug)\b',
            r'\b(test|testing|unit|integration)\b',
            r'\b(refactor|clean|optimize|performance)\b',
            r'\b(component|react|vue|angular)\b',
            r'\b(function|class|method|module)\b',
            r'\b(database|sql|query|migration)\b',
            r'\b(auth|login|session|token|jwt)\b',
            r'\b(deploy|ci|cd|docker|kubernetes)\b',
            r'\b(prompt|template|example|pattern)\b',
        ]

        text_lower = text.lower()
        for pattern in code_patterns:
            matches = re.findall(pattern, text_lower)
            keywords.extend(matches)

        return list(set(keywords))

    def search(
        self,
        query: str,
        limit: int = 3,
        pack_ids: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """Search for relevant content across installed packs.

        Args:
            query: Search query
            limit: Maximum number of results
            pack_ids: Optional list of pack IDs to search (None = all)

        Returns:
            List of SearchResult objects
        """
        results = []
        query_lower = query.lower()
        query_keywords = self._extract_keywords(query)

        # Also extract words from query
        query_words = set(re.findall(r'\b\w{3,}\b', query_lower))

        for pack_id, index in self.indices.items():
            if pack_ids and pack_id not in pack_ids:
                continue

            for doc in index.documents:
                score = self._calculate_score(
                    query_lower,
                    query_keywords,
                    query_words,
                    doc,
                )

                if score > 0:
                    results.append(SearchResult(
                        pack_id=pack_id,
                        pack_name=index.pack_name,
                        file_name=doc['file'],
                        title=doc['title'],
                        content=doc['content'][:500],  # Truncate
                        score=score,
                        source_url=index.source_url,
                    ))

        # Sort by score and return top results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def _calculate_score(
        self,
        query_lower: str,
        query_keywords: List[str],
        query_words: set,
        doc: Dict[str, Any],
    ) -> float:
        """Calculate relevance score for a document."""
        score = 0.0

        content_lower = doc['content'].lower()
        title_lower = doc['title'].lower()
        doc_keywords = set(doc.get('keywords', []))

        # Keyword match (highest weight)
        keyword_matches = len(set(query_keywords) & doc_keywords)
        score += keyword_matches * 3.0

        # Title match
        for word in query_words:
            if word in title_lower:
                score += 2.0

        # Content match
        for word in query_words:
            if word in content_lower:
                count = content_lower.count(word)
                score += min(count * 0.5, 2.0)  # Cap at 2.0

        # Exact phrase match (bonus)
        if len(query_lower) > 5 and query_lower in content_lower:
            score += 3.0

        return score

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about indexed content."""
        stats = {
            'packs_indexed': len(self.indices),
            'total_documents': 0,
            'packs': [],
        }

        for pack_id, index in self.indices.items():
            doc_count = len(index.documents)
            stats['total_documents'] += doc_count
            stats['packs'].append({
                'id': pack_id,
                'name': index.pack_name,
                'documents': doc_count,
            })

        return stats


# Singleton instance
_search_engine: Optional[PackSearchEngine] = None


def get_search_engine() -> PackSearchEngine:
    """Get or create the search engine instance."""
    global _search_engine
    if _search_engine is None:
        _search_engine = PackSearchEngine()
    return _search_engine


def refresh_search_engine():
    """Refresh the search engine (reload indices)."""
    global _search_engine
    _search_engine = PackSearchEngine()


def search_packs(
    query: str,
    limit: int = 3,
    pack_ids: Optional[List[str]] = None,
) -> List[SearchResult]:
    """Search installed packs for relevant content.

    Args:
        query: Search query
        limit: Maximum number of results
        pack_ids: Optional list of pack IDs to search

    Returns:
        List of SearchResult objects
    """
    engine = get_search_engine()
    return engine.search(query, limit, pack_ids)


def get_pack_search_stats() -> Dict[str, Any]:
    """Get statistics about indexed packs."""
    engine = get_search_engine()
    return engine.get_stats()
