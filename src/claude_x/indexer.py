"""Session index parser for sessions-index.json files."""

import json
from pathlib import Path
from typing import Iterator, List, Tuple
from .models import SessionIndex, SessionIndexEntry


class SessionIndexer:
    """Parses sessions-index.json files from Claude projects."""

    def __init__(self, claude_dir: Path = Path.home() / ".claude"):
        """Initialize indexer with Claude directory.

        Args:
            claude_dir: Root Claude configuration directory
        """
        self.claude_dir = claude_dir
        self.projects_dir = claude_dir / "projects"

    def find_all_project_dirs(self) -> List[Path]:
        """Find all project directories containing sessions-index.json.

        Returns:
            List of project directory paths
        """
        if not self.projects_dir.exists():
            return []

        project_dirs = []
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                index_file = project_dir / "sessions-index.json"
                if index_file.exists():
                    project_dirs.append(project_dir)

        return project_dirs

    def parse_index_file(self, index_path: Path) -> SessionIndex:
        """Parse a sessions-index.json file.

        Args:
            index_path: Path to sessions-index.json

        Returns:
            Parsed SessionIndex object
        """
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return SessionIndex(**data)

    def iter_all_sessions(self) -> Iterator[Tuple[Path, SessionIndexEntry]]:
        """Iterate over all sessions across all projects.

        Yields:
            Tuple of (project_dir, session_entry)
        """
        for project_dir in self.find_all_project_dirs():
            index_file = project_dir / "sessions-index.json"
            try:
                index = self.parse_index_file(index_file)
                for entry in index.entries:
                    yield project_dir, entry
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to parse {index_file}: {e}")
                continue

    def get_project_sessions(self, project_dir: Path) -> List[SessionIndexEntry]:
        """Get all sessions for a specific project.

        Args:
            project_dir: Path to project directory

        Returns:
            List of session entries
        """
        index_file = project_dir / "sessions-index.json"
        if not index_file.exists():
            return []

        try:
            index = self.parse_index_file(index_file)
            return index.entries
        except (json.JSONDecodeError, KeyError):
            return []

    def decode_project_path(self, encoded_path: str) -> str:
        """Decode project path from directory name.

        Args:
            encoded_path: Encoded path (e.g., '-Users-kakao-workspace-brunch-front')

        Returns:
            Decoded path (e.g., '/Users/kakao/workspace/brunch-front')
        """
        # Remove leading dash and replace remaining dashes with slashes
        if encoded_path.startswith("-"):
            encoded_path = encoded_path[1:]

        return "/" + encoded_path.replace("-", "/")

    def extract_project_name(self, project_path: str) -> str:
        """Extract project name from path.

        Args:
            project_path: Full project path

        Returns:
            Project name (last component of path)
        """
        return Path(project_path).name
