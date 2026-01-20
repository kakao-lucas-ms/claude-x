"""JSONL session file parser."""

import json
from pathlib import Path
from datetime import datetime
from typing import Iterator, Optional
from .models import Message


class SessionParser:
    """Parses individual session JSONL files."""

    def __init__(self, session_path: Path):
        """Initialize parser with session file path.

        Args:
            session_path: Path to session .jsonl file
        """
        self.session_path = session_path
        self.file_size = session_path.stat().st_size if session_path.exists() else 0

    def parse_messages(
        self,
        session_id: str,
        offset: int = 0,
        limit: Optional[int] = None
    ) -> Iterator[Message]:
        """Parse messages from the session file.

        Args:
            session_id: Session ID for this session
            offset: Byte offset to start reading from
            limit: Maximum number of messages to parse

        Yields:
            Parsed Message objects
        """
        if not self.session_path.exists():
            return

        count = 0
        with open(self.session_path, "r", encoding="utf-8") as f:
            # Seek to offset if specified
            if offset > 0:
                f.seek(offset)

            for line in f:
                # Stop if limit reached
                if limit is not None and count >= limit:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    message = self._parse_message_entry(session_id, data)
                    if message:
                        yield message
                        count += 1
                except (json.JSONDecodeError, KeyError) as e:
                    # Skip malformed lines
                    continue

    def _parse_message_entry(self, session_id: str, data: dict) -> Optional[Message]:
        """Parse a single message entry.

        Args:
            session_id: Session ID
            data: Raw JSONL entry

        Returns:
            Parsed Message or None if not a valid message
        """
        # Only process user and assistant messages
        msg_type = data.get("type")
        if msg_type not in ("user", "assistant"):
            return None

        # Extract message content
        message_data = data.get("message", {})

        # Handle different content formats
        content = ""
        if isinstance(message_data.get("content"), str):
            content = message_data["content"]
        elif isinstance(message_data.get("content"), list):
            # Extract text from content blocks
            content_parts = []
            for block in message_data["content"]:
                if isinstance(block, dict) and block.get("type") == "text":
                    content_parts.append(block.get("text", ""))
            content = "\n".join(content_parts)

        # Parse timestamp
        timestamp_str = data.get("timestamp")
        if not timestamp_str:
            return None

        timestamp = self._parse_timestamp(timestamp_str)
        if not timestamp:
            return None

        # Check if message contains code
        has_code = self._contains_code_blocks(content)

        return Message(
            session_id=session_id,
            type=msg_type,
            content=content,
            timestamp=timestamp,
            has_code=has_code
        )

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from various formats.

        Args:
            timestamp_str: Timestamp string (Unix ms or ISO 8601)

        Returns:
            Parsed datetime or None
        """
        # Try ISO 8601 format first
        if isinstance(timestamp_str, str) and "T" in timestamp_str:
            try:
                # Remove timezone suffix for parsing
                clean_ts = timestamp_str.replace("Z", "+00:00")
                return datetime.fromisoformat(clean_ts)
            except ValueError:
                pass

        # Try Unix timestamp (milliseconds)
        try:
            timestamp_int = int(timestamp_str)
            return datetime.fromtimestamp(timestamp_int / 1000.0)
        except (ValueError, TypeError):
            pass

        return None

    def _contains_code_blocks(self, content: str) -> bool:
        """Check if content contains code blocks.

        Args:
            content: Message content

        Returns:
            True if code blocks found
        """
        return "```" in content

    def get_current_offset(self) -> int:
        """Get the current file size (for incremental parsing).

        Returns:
            Current file size in bytes
        """
        return self.file_size
