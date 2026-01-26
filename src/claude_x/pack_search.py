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
        """Extract meaningful keywords from text."""
        # Extract all significant words (3+ chars, not stopwords)
        stopwords = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
            'had', 'her', 'was', 'one', 'our', 'out', 'has', 'have', 'been',
            'would', 'could', 'should', 'will', 'with', 'this', 'that', 'from',
            'they', 'what', 'when', 'where', 'which', 'who', 'how', 'why',
            'each', 'she', 'use', 'used', 'using', 'like', 'make', 'made',
            'just', 'into', 'than', 'then', 'them', 'some', 'such', 'only',
            'also', 'more', 'most', 'other', 'your', 'about', 'these', 'those',
        }

        text_lower = text.lower()
        words = re.findall(r'\b[a-z]{3,}\b', text_lower)
        keywords = [w for w in words if w not in stopwords]

        return keywords

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

        # Minimum score threshold for relevance
        MIN_SCORE = 2.0

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

                # Only include results above threshold
                if score >= MIN_SCORE:
                    # Extract relevant snippet around query terms
                    snippet = self._extract_relevant_snippet(
                        doc['content'], query_lower, query_words
                    )
                    results.append(SearchResult(
                        pack_id=pack_id,
                        pack_name=index.pack_name,
                        file_name=doc['file'],
                        title=doc['title'],
                        content=snippet,
                        score=score,
                        source_url=index.source_url,
                    ))

        # Sort by score and return top results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def _extract_relevant_snippet(
        self,
        content: str,
        query_lower: str,
        query_words: set,
        max_length: int = 600,
    ) -> str:
        """Extract a snippet that shows the relevant context around query terms.

        Returns longer snippets (600 chars) for better context.
        Minimizes use of "..." to avoid messy output.
        """
        content_lower = content.lower()

        # Short content: return as-is
        if len(content) <= max_length:
            return content.strip()

        # Try to find exact phrase first
        if query_lower in content_lower:
            idx = content_lower.find(query_lower)
            # Get more context around the match
            start = max(0, idx - 100)
            end = min(len(content), idx + len(query_lower) + 400)

            # Align to word boundaries
            if start > 0:
                space_idx = content.find(' ', start)
                if space_idx != -1 and space_idx < start + 20:
                    start = space_idx + 1

            snippet = content[start:end].strip()
            return snippet

        # Find the best position where query words cluster
        best_pos = 0
        best_score = 0

        for i in range(0, len(content_lower), 50):
            window = content_lower[i:i+max_length]
            score = sum(1 for w in query_words if w in window)
            if score > best_score:
                best_score = score
                best_pos = i

        if best_score > 0:
            end = min(len(content), best_pos + max_length)
            snippet = content[best_pos:end].strip()
            return snippet

        # Fallback to beginning
        return content[:max_length].strip()

    def _calculate_score(
        self,
        query_lower: str,
        query_keywords: List[str],
        query_words: set,
        doc: Dict[str, Any],
    ) -> float:
        """Calculate relevance score for a document.

        Scoring criteria (v0.6.5 - stricter matching):
        - ALL query words must be present for high scores
        - Partial matches get severely penalized
        - Exact phrase match: bonus points
        - Missing words: heavy penalty

        Score thresholds:
        - 10+: Excellent match (all words + exact phrase)
        - 6-10: Good match (all words present)
        - 2-6: Partial match (some words missing)
        - <2: Filtered out
        """
        score = 0.0

        content_lower = doc['content'].lower()
        title_lower = doc['title'].lower()
        combined_text = title_lower + " " + content_lower

        if not query_words:
            return 0.0

        # Count how many query words are present
        words_in_title = sum(1 for w in query_words if w in title_lower)
        words_in_content = sum(1 for w in query_words if w in content_lower)
        words_in_combined = sum(1 for w in query_words if w in combined_text)

        total_words = len(query_words)
        match_ratio = words_in_combined / total_words

        # CRITICAL: If not all words are present, apply heavy penalty
        if match_ratio < 1.0:
            # Partial match - severely reduced score
            # Missing even 1 word out of 3 = only 33% of potential score
            penalty_factor = match_ratio ** 2  # Quadratic penalty
            base_score = words_in_combined * 1.5
            score = base_score * penalty_factor
            # Cap partial matches at low score
            return min(score, 3.0)

        # ALL words are present - calculate full score
        score = 5.0  # Base score for having all words

        # Exact phrase match (highest priority)
        if len(query_lower) > 3:
            if query_lower in title_lower:
                score += 8.0  # Exact phrase in title
            elif query_lower in content_lower:
                score += 4.0  # Exact phrase in content

        # All words in title = extra bonus
        if words_in_title == total_words:
            score += 3.0

        # Density bonus: how concentrated are the matches?
        if len(content_lower) > 0:
            total_occurrences = sum(content_lower.count(w) for w in query_words)
            density = total_occurrences / (len(content_lower) / 100)
            score += min(density * 0.3, 1.5)

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
