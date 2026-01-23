"""SQLite storage backend with FTS5 search."""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Any, Dict
from contextlib import contextmanager

from .models import Project, Session, Message, CodeSnippet


class Storage:
    """SQLite storage backend for Claude-X."""

    def __init__(self, db_path: Path):
        """Initialize storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.executescript("""
                -- Projects table
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    encoded_path TEXT NOT NULL,
                    name TEXT,
                    session_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                -- Sessions table
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    project_id INTEGER NOT NULL,
                    full_path TEXT NOT NULL,
                    first_prompt TEXT,
                    message_count INTEGER,
                    git_branch TEXT,
                    is_sidechain BOOLEAN DEFAULT FALSE,
                    session_type TEXT DEFAULT 'main',
                    file_mtime INTEGER,
                    last_read_offset INTEGER DEFAULT 0,
                    created_at DATETIME,
                    modified_at DATETIME,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                );

                -- Messages table
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    has_code BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );

                -- Code snippets table
                CREATE TABLE IF NOT EXISTS code_snippets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    session_id TEXT NOT NULL,
                    language TEXT NOT NULL,
                    code TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    line_count INTEGER,
                    has_sensitive BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES messages(id),
                    UNIQUE (session_id, hash)
                );

                -- Fulltext search table
                CREATE VIRTUAL TABLE IF NOT EXISTS code_fts USING fts5(
                    code,
                    language,
                    content=code_snippets,
                    content_rowid=id
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_branch ON sessions(git_branch);
                CREATE INDEX IF NOT EXISTS idx_snippets_language ON code_snippets(language);
                CREATE INDEX IF NOT EXISTS idx_snippets_session ON code_snippets(session_id);

                -- FTS triggers
                CREATE TRIGGER IF NOT EXISTS code_fts_insert AFTER INSERT ON code_snippets BEGIN
                    INSERT INTO code_fts(rowid, code, language) VALUES (new.id, new.code, new.language);
                END;

                CREATE TRIGGER IF NOT EXISTS code_fts_delete AFTER DELETE ON code_snippets BEGIN
                    DELETE FROM code_fts WHERE rowid = old.id;
                END;

                CREATE TRIGGER IF NOT EXISTS code_fts_update AFTER UPDATE ON code_snippets BEGIN
                    UPDATE code_fts SET code = new.code, language = new.language WHERE rowid = new.id;
                END;
            """)
            conn.commit()

            # Try to create unique index for messages deduplication
            # May fail if duplicate data exists - that's OK, we handle duplicates in insert
            try:
                conn.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_unique
                    ON messages(session_id, timestamp, type, content)
                """)
                conn.commit()
            except sqlite3.IntegrityError:
                # Duplicate data exists, skip index creation
                pass

    def insert_project(self, project: Project) -> int:
        """Insert or get existing project.

        Args:
            project: Project model

        Returns:
            Project ID
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO projects (path, encoded_path, name, session_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    session_count = session_count + 1
                RETURNING id
                """,
                (project.path, project.encoded_path, project.name, project.session_count)
            )
            project_id = cursor.fetchone()[0]
            conn.commit()
            return project_id

    def insert_session(self, session: Session) -> int:
        """Insert or update session.

        Args:
            session: Session model

        Returns:
            Session database ID
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions (
                    session_id, project_id, full_path, first_prompt, message_count,
                    git_branch, is_sidechain, session_type, file_mtime, last_read_offset,
                    created_at, modified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    message_count = excluded.message_count,
                    file_mtime = excluded.file_mtime,
                    last_read_offset = excluded.last_read_offset,
                    modified_at = excluded.modified_at
                RETURNING id
                """,
                (
                    session.session_id, session.project_id, session.full_path,
                    session.first_prompt, session.message_count, session.git_branch,
                    session.is_sidechain, session.session_type, session.file_mtime,
                    session.last_read_offset, session.created_at, session.modified_at
                )
            )
            session_id = cursor.fetchone()[0]
            conn.commit()
            return session_id

    def insert_message(self, message: Message) -> int:
        """Insert message.

        Args:
            message: Message model

        Returns:
            Message database ID
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO messages (session_id, type, content, timestamp, has_code)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message.session_id, message.type, message.content, message.timestamp, message.has_code)
            )
            message_id = cursor.lastrowid
            if not message_id:
                cursor = conn.execute(
                    """
                    SELECT id FROM messages
                    WHERE session_id = ? AND type = ? AND content = ? AND timestamp = ?
                    LIMIT 1
                    """,
                    (message.session_id, message.type, message.content, message.timestamp)
                )
                row = cursor.fetchone()
                message_id = row[0] if row else 0
            message_id = int(message_id or 0)
            conn.commit()
            return message_id

    def insert_code_snippet(self, snippet: CodeSnippet) -> Optional[int]:
        """Insert code snippet (ignoring duplicates within session).

        Args:
            snippet: CodeSnippet model

        Returns:
            Snippet ID or None if duplicate
        """
        with self._get_connection() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO code_snippets (
                        message_id, session_id, language, code, hash, line_count, has_sensitive
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snippet.message_id, snippet.session_id, snippet.language,
                        snippet.code, snippet.hash, snippet.line_count, snippet.has_sensitive
                    )
                )
                snippet_id = cursor.lastrowid
                conn.commit()
                return snippet_id
            except sqlite3.IntegrityError:
                # Duplicate within session - skip
                return None

    def search_code(self, query: str, language: Optional[str] = None, limit: int = 20) -> List[dict]:
        """Search code using FTS5.

        Args:
            query: Search query
            language: Optional language filter
            limit: Max results

        Returns:
            List of search results
        """
        with self._get_connection() as conn:
            sql = """
                SELECT
                    cs.id,
                    cs.language,
                    cs.code,
                    cs.line_count,
                    cs.has_sensitive,
                    cs.session_id,
                    COALESCE(
                        (SELECT content
                         FROM messages
                         WHERE session_id = s.session_id
                           AND type = 'user'
                         ORDER BY timestamp ASC
                         LIMIT 1),
                        s.first_prompt
                    ) as first_prompt,
                    s.git_branch,
                    p.name as project_name,
                    bm25(code_fts) as rank
                FROM code_fts
                JOIN code_snippets cs ON code_fts.rowid = cs.id
                JOIN sessions s ON cs.session_id = s.session_id
                JOIN projects p ON s.project_id = p.id
                WHERE code_fts MATCH ?
            """

            params: list[object] = [query]

            if language:
                sql += " AND cs.language = ?"
                params.append(language)

            sql += " ORDER BY rank LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_session_offsets(self, session_id: str) -> Optional[Dict[str, int]]:
        """Get last read offset and file mtime for a session.

        Args:
            session_id: Session ID

        Returns:
            Dict with last_read_offset and file_mtime, or None
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT last_read_offset, file_mtime
                FROM sessions
                WHERE session_id = ?
                LIMIT 1
                """,
                (session_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "last_read_offset": row[0] or 0,
                "file_mtime": row[1] or 0,
            }

    def get_session_stats(self, project_name: Optional[str] = None) -> dict:
        """Get statistics.

        Args:
            project_name: Optional project filter

        Returns:
            Statistics dictionary
        """
        with self._get_connection() as conn:
            where_clause = ""
            params = []

            if project_name:
                where_clause = "WHERE p.name = ?"
                params = [project_name]

            cursor = conn.execute(
                f"""
                SELECT
                    COUNT(DISTINCT s.id) as session_count,
                    COUNT(DISTINCT p.id) as project_count,
                    COUNT(m.id) as message_count,
                    COUNT(cs.id) as code_snippet_count
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                LEFT JOIN messages m ON s.session_id = m.session_id
                LEFT JOIN code_snippets cs ON m.id = cs.message_id
                {where_clause}
                """,
                params
            )
            return dict(cursor.fetchone())

    def get_stats(self, project_name: Optional[str] = None) -> dict:
        """Backward-compatible stats accessor."""
        return self.get_session_stats(project_name=project_name)

    def list_sessions(
        self,
        project_name: Optional[str] = None,
        branch: Optional[str] = None,
        limit: int = 50
    ) -> List[dict]:
        """List sessions with filters.

        Args:
            project_name: Filter by project
            branch: Filter by git branch
            limit: Max results

        Returns:
            List of session dictionaries
        """
        with self._get_connection() as conn:
            sql = """
                SELECT
                    s.session_id,
                    s.first_prompt,
                    s.message_count,
                    s.git_branch,
                    s.created_at,
                    s.modified_at,
                    p.name as project_name
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                WHERE 1=1
            """
            params = []

            if project_name:
                sql += " AND p.name LIKE ?"
                params.append(f"%{project_name}%")

            if branch:
                sql += " AND s.git_branch = ?"
                params.append(branch)

            sql += " ORDER BY s.modified_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_session_detail(self, session_id: str) -> Optional[dict]:
        """Get session details by ID.

        Args:
            session_id: Full or partial session ID

        Returns:
            Session dictionary or None
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    s.session_id,
                    s.first_prompt,
                    s.message_count,
                    s.git_branch,
                    s.created_at,
                    s.modified_at,
                    s.full_path,
                    p.name as project_name
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                WHERE s.session_id LIKE ?
                LIMIT 1
                """,
                (f"{session_id}%",)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_session_code_snippets(self, session_id: str) -> List[dict]:
        """Get all code snippets for a session.

        Args:
            session_id: Full or partial session ID

        Returns:
            List of code snippet dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    cs.id,
                    cs.language,
                    cs.code,
                    cs.line_count,
                    cs.has_sensitive,
                    m.type as message_type,
                    m.timestamp
                FROM code_snippets cs
                JOIN messages m ON cs.message_id = m.id
                WHERE cs.session_id LIKE ?
                ORDER BY m.timestamp ASC
                """,
                (f"{session_id}%",)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_session_messages(self, session_id: str) -> List[dict]:
        """Get all messages for a session.

        Args:
            session_id: Full or partial session ID

        Returns:
            List of message dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    id,
                    type,
                    content,
                    timestamp,
                    has_code
                FROM messages
                WHERE session_id LIKE ?
                ORDER BY timestamp ASC
                """,
                (f"{session_id}%",)
            )
            return [dict(row) for row in cursor.fetchall()]
