"""Code block extraction from message content."""

import re
import hashlib
from typing import Iterator
from .models import CodeSnippet


class CodeExtractor:
    """Extracts code blocks from message content."""

    # Regex pattern for markdown code blocks
    CODE_BLOCK_PATTERN = re.compile(
        r"```([\w+-]+)?\n(.*?)```",
        re.DOTALL | re.MULTILINE
    )

    def __init__(self):
        """Initialize code extractor."""
        pass

    def extract_code_blocks(
        self,
        message_id: int,
        session_id: str,
        content: str
    ) -> Iterator[CodeSnippet]:
        """Extract all code blocks from message content.

        Args:
            message_id: Database ID of the message
            session_id: Session ID
            content: Message content

        Yields:
            CodeSnippet objects
        """
        matches = self.CODE_BLOCK_PATTERN.finditer(content)

        for match in matches:
            language = self.normalize_language(match.group(1) or "text")
            code = match.group(2).strip()

            if not code:
                continue

            # Calculate hash for deduplication
            code_hash = self._calculate_hash(code)

            # Count lines
            line_count = code.count("\n") + 1

            yield CodeSnippet(
                message_id=message_id,
                session_id=session_id,
                language=language.lower(),
                code=code,
                hash=code_hash,
                line_count=line_count,
                has_sensitive=False  # Will be set by security module
            )

    def _calculate_hash(self, code: str) -> str:
        """Calculate SHA-256 hash of code.

        Args:
            code: Code content

        Returns:
            Hex digest of hash
        """
        return hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]

    def normalize_language(self, language: str) -> str:
        """Normalize language identifier.

        Args:
            language: Raw language identifier

        Returns:
            Normalized language name
        """
        # Map common variations to standard names
        lang_map = {
            "js": "javascript",
            "ts": "typescript",
            "py": "python",
            "sh": "bash",
            "shell": "bash",
            "yml": "yaml",
            "jsx": "javascript",
            "tsx": "typescript",
        }

        normalized = language.lower()
        return lang_map.get(normalized, normalized)
