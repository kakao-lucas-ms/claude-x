"""Data models for Claude-X."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Project(BaseModel):
    """Represents a project directory."""

    id: Optional[int] = None
    path: str
    encoded_path: str
    name: str
    session_count: int = 0
    created_at: Optional[datetime] = None


class Session(BaseModel):
    """Represents a Claude session."""

    id: Optional[int] = None
    session_id: str
    project_id: int
    full_path: str
    first_prompt: Optional[str] = None
    message_count: Optional[int] = None
    git_branch: Optional[str] = None
    is_sidechain: bool = False
    session_type: str = "main"  # 'main' or 'agent'
    file_mtime: Optional[int] = None
    last_read_offset: int = 0
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None


class Message(BaseModel):
    """Represents a message in a session."""

    id: Optional[int] = None
    session_id: str
    type: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    has_code: bool = False


class CodeSnippet(BaseModel):
    """Represents a code snippet extracted from a message."""

    id: Optional[int] = None
    message_id: int
    session_id: str
    language: str
    code: str
    hash: str
    line_count: int
    has_sensitive: bool = False
    created_at: Optional[datetime] = None


class SessionIndexEntry(BaseModel):
    """Represents an entry in sessions-index.json."""

    session_id: str = Field(alias="sessionId")
    full_path: str = Field(alias="fullPath")
    file_mtime: int = Field(alias="fileMtime")
    first_prompt: Optional[str] = Field(alias="firstPrompt", default=None)
    message_count: Optional[int] = Field(alias="messageCount", default=None)
    created: str
    modified: str
    git_branch: Optional[str] = Field(alias="gitBranch", default=None)
    project_path: Optional[str] = Field(alias="projectPath", default=None)
    is_sidechain: bool = Field(alias="isSidechain", default=False)

    class Config:
        populate_by_name = True


class SessionIndex(BaseModel):
    """Represents the sessions-index.json file structure."""

    version: int
    entries: List[SessionIndexEntry]
