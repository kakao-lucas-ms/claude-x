"""Custom exceptions with helpful error messages."""


class ClaudeXError(Exception):
    """Base exception for Claude-X."""
    pass


class ClaudeCodeNotFoundError(ClaudeXError):
    """Raised when Claude Code installation is not found."""

    def __init__(self):
        message = """
❌ Claude Code sessions directory not found

Claude-X requires Claude Code to be installed and used at least once.

Please:
  1. Install Claude Code: https://claude.ai/code
  2. Run at least one Claude Code session
  3. Try again: cx import

Need help? Run 'cx doctor' to diagnose the issue.
"""
        super().__init__(message)


class SessionDirectoryNotFoundError(ClaudeXError):
    """Raised when sessions directory doesn't exist."""

    def __init__(self, path):
        message = f"""
❌ Sessions directory not found: {path}

Please ensure:
  1. Claude Code has been run at least once
  2. At least one conversation exists
  3. The directory path is correct

Need help? Run 'cx doctor' for diagnostics.
"""
        super().__init__(message)


class DatabaseCorruptedError(ClaudeXError):
    """Raised when database is corrupted."""

    def __init__(self, db_path):
        message = f"""
❌ Database appears to be corrupted: {db_path}

To fix:
  1. Backup existing database: cp {db_path} {db_path}.backup
  2. Remove corrupted database: rm {db_path}
  3. Reinitialize: cx init
  4. Import sessions: cx import

Your original sessions are safe in ~/.claude/projects/
"""
        super().__init__(message)


class SessionFileNotFoundError(ClaudeXError):
    """Raised when a session file is missing."""

    def __init__(self, session_path, session_id):
        message = f"""
❌ Session file not found

Session ID: {session_id}
Expected at: {session_path}

This can happen if:
  1. The session was deleted
  2. Claude Code cleaned up old sessions
  3. The file was moved

Try: cx import (to re-index available sessions)
"""
        super().__init__(message)


class MalformedJSONError(ClaudeXError):
    """Raised when JSON data is malformed."""

    def __init__(self, file_path, line_number=None, error_detail=None):
        if line_number:
            location = f"Line {line_number}"
        else:
            location = "Unknown line"

        message = f"""
❌ Malformed JSON data

File: {file_path}
Location: {location}
{f'Error: {error_detail}' if error_detail else ''}

This session file may be corrupted. It will be skipped during import.
"""
        super().__init__(message)
