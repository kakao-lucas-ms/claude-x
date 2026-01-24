"""Command-line interface for Claude-X."""

import json
import sys
import time
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .indexer import SessionIndexer
from .session_parser import SessionParser
from .extractor import CodeExtractor
from .security import SecurityScanner
from .storage import Storage
from .models import Project, Session, Message
from .analytics import PromptAnalytics
from .prompt_templates import PromptTemplateLibrary
from .export import export_to_html, export_to_gist, export_to_json

app = typer.Typer(
    name="cx",
    help="Claude-X: Second Brain and Command Center for Claude Code",
    add_completion=False
)
console = Console()


def get_storage() -> Storage:
    """Get storage instance."""
    data_dir = Path.home() / ".claude-x" / "data"
    db_path = data_dir / "claude_x.db"
    return Storage(db_path)


def db_exists() -> bool:
    """Check if database exists."""
    data_dir = Path.home() / ".claude-x" / "data"
    db_path = data_dir / "claude_x.db"
    return db_path.exists()


def claude_code_exists() -> bool:
    """Check if Claude Code is installed."""
    claude_dir = Path.home() / ".claude"
    projects_dir = claude_dir / "projects"
    return projects_dir.exists()


def _import_sessions(
    storage: Storage,
    indexer: SessionIndexer,
    extractor: CodeExtractor,
    scanner: SecurityScanner,
    project: Optional[str] = None,
    incremental: bool = True,
    progress=None,
    progress_task=None,
) -> dict:
    counts = {"sessions": 0, "messages": 0, "snippets": 0}

    for project_dir, session_entry in indexer.iter_all_sessions():
        # Filter by project if specified
        if project:
            project_name = indexer.extract_project_name(session_entry.project_path or "")
            if project.lower() not in project_name.lower():
                continue

        try:
            # Insert project
            project_path = indexer.decode_project_path(project_dir.name)
            project_model = Project(
                path=project_path,
                encoded_path=project_dir.name,
                name=indexer.extract_project_name(project_path)
            )
            project_id = storage.insert_project(project_model)

            # Determine incremental offsets
            existing = storage.get_session_offsets(session_entry.session_id)
            existing_offset = existing["last_read_offset"] if existing else 0
            existing_mtime = existing["file_mtime"] if existing else 0

            # Get actual file mtime for accurate incremental import
            session_file = Path(session_entry.full_path)
            actual_mtime = int(session_file.stat().st_mtime * 1000) if session_file.exists() else session_entry.file_mtime

            session_model = Session(
                session_id=session_entry.session_id,
                project_id=project_id,
                full_path=session_entry.full_path,
                first_prompt=session_entry.first_prompt,
                message_count=session_entry.message_count,
                git_branch=session_entry.git_branch,
                is_sidechain=session_entry.is_sidechain,
                file_mtime=actual_mtime,  # Use actual file mtime, not stale index mtime
                last_read_offset=existing_offset,
                created_at=datetime.fromisoformat(session_entry.created.replace("Z", "+00:00")),
                modified_at=datetime.fromisoformat(session_entry.modified.replace("Z", "+00:00"))
            )
            storage.insert_session(session_model)
            counts["sessions"] += 1

            # Parse messages - skip if file unchanged (using actual mtime, not stale index)
            if not session_file.exists():
                continue

            if incremental and existing and actual_mtime <= existing_mtime:
                continue

            start_offset = existing_offset if incremental else 0
            parser = SessionParser(session_file)
            for message in parser.parse_messages(session_entry.session_id, offset=start_offset):
                message_id = storage.insert_message(message)
                if not message_id:
                    continue
                counts["messages"] += 1

                if message.has_code:
                    for snippet in extractor.extract_code_blocks(
                        message_id, session_entry.session_id, message.content
                    ):
                        snippet.has_sensitive = scanner.has_sensitive_data(snippet.code)
                        if storage.insert_code_snippet(snippet):
                            counts["snippets"] += 1

            session_model.last_read_offset = parser.get_current_offset()
            storage.insert_session(session_model)

            if progress is not None and progress_task is not None:
                progress.update(
                    progress_task,
                    description=(
                        f"Imported {counts['sessions']} sessions, "
                        f"{counts['messages']} messages, {counts['snippets']} code snippets"
                    )
                )
        except Exception:
            continue

    return counts


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        try:
            from importlib.metadata import version
            __version__ = version("claude-x")
        except Exception:
            __version__ = "0.1.0"
        console.print(f"Claude-X version {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit"
    )
):
    """Auto-initialize on first run."""
    # Skip auto-init for init command itself or when no command
    if ctx.invoked_subcommand in ["init", None]:
        return

    # Check if DB exists
    if not db_exists():
        console.print("[yellow]First run detected. Initializing database...[/yellow]")
        storage = get_storage()
        console.print(f"✅ Database created at: {storage.db_path}")

        # Check if Claude Code exists
        if not claude_code_exists():
            console.print("\n[yellow]⚠️  Claude Code directory not found at ~/.claude/projects/[/yellow]")
            console.print("[dim]Make sure Claude Code is installed and you've run at least one session.[/dim]")
            console.print("[dim]Visit: https://claude.ai/code[/dim]\n")


@app.command()
def init(
    skip_import: bool = typer.Option(False, "--skip-import", help="Skip automatic session import")
):
    """Initialize Claude-X database and MCP server configuration."""
    # 1. Initialize database
    storage = get_storage()
    console.print("✅ Database initialized at:", storage.db_path)

    # 2. Setup MCP server configuration
    claude_settings = Path.home() / ".claude" / "settings.json"
    claude_dir = claude_settings.parent

    # Create .claude directory if it doesn't exist
    if not claude_dir.exists():
        console.print(f"📁 Creating Claude Code directory: {claude_dir}")
        claude_dir.mkdir(parents=True, exist_ok=True)

    # Read or create settings
    if not claude_settings.exists():
        console.print("📝 Creating new settings.json")
        settings = {}
    else:
        try:
            with open(claude_settings, 'r') as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            console.print("⚠️  Invalid settings.json, creating new one")
            settings = {}

    # Check if MCP server already configured
    if 'mcpServers' not in settings:
        settings['mcpServers'] = {}

    mcp_was_added = False
    if 'claude-x' in settings['mcpServers']:
        console.print("ℹ️  MCP server already configured")
        console.print(f"   Command: {settings['mcpServers']['claude-x'].get('command', 'N/A')}")
    else:
        # Add MCP server configuration
        python_path = sys.executable
        settings['mcpServers']['claude-x'] = {
            "command": "/usr/bin/arch",
            "args": [
                "-arm64",
                python_path,
                "-m",
                "claude_x.mcp_server"
            ]
        }

        # Write back to settings
        with open(claude_settings, 'w') as f:
            json.dump(settings, f, indent=2)

        console.print("✅ MCP server configured in Claude Code")
        console.print(f"   Location: {claude_settings}")
        mcp_was_added = True

    # Check if database has any data
    session_count = len(list(storage.list_sessions()))

    # Auto-import existing sessions if database is empty
    if session_count == 0 and not skip_import:
        claude_projects = Path.home() / ".claude" / "projects"
        if claude_projects.exists():
            console.print("\n[bold cyan]📥 Importing existing Claude Code sessions...[/bold cyan]")

            # Import sessions using the same logic as cx import
            indexer = SessionIndexer()
            extractor = CodeExtractor()
            scanner = SecurityScanner()

            import_count = 0
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Importing...", total=None)
                counts = _import_sessions(
                    storage=storage,
                    indexer=indexer,
                    extractor=extractor,
                    scanner=scanner,
                    project=None,
                    incremental=True,
                    progress=progress,
                    progress_task=task,
                )
                import_count = counts["sessions"]

            session_count = import_count
            if import_count > 0:
                console.print(f"[green]✅ Imported {import_count} sessions from Claude Code history[/green]")
        else:
            console.print("\n[yellow]📊 Database Status: Empty[/yellow]")
            console.print("[dim]No existing Claude Code sessions found to import.[/dim]")

    console.print("\n[bold green]Setup Complete![/bold green]")

    if session_count == 0:
        console.print("\n[yellow]📊 Database Status: Empty[/yellow]")
        console.print("[dim]Your database is initialized but has no data yet.[/dim]\n")
        console.print("[bold]To collect data, choose one:[/bold]")
        console.print("  Option 1: Run 'cx watch' in background to auto-collect sessions")
        console.print("  Option 2: Just use Claude Code normally - sessions are saved automatically")
        console.print("\n[dim]Note: MCP tools will return empty results until you have session data.[/dim]")
    else:
        console.print(f"\n[green]📊 Database Status: {session_count} sessions found[/green]")

    console.print("\n[bold]Next steps:[/bold]")
    if mcp_was_added:
        console.print("[red bold]⚠️  IMPORTANT: You MUST restart Claude Code for MCP server to work![/bold red]")
        console.print("1. [bold]Quit Claude Code completely (Cmd+Q)[/bold]")
        console.print("2. [bold]Reopen Claude Code[/bold]")
        console.print("3. Run '/mcp' to verify claude-x is listed")
        if session_count == 0:
            console.print("4. Use Claude Code to create some sessions")
            console.print("5. Then try: '내 베스트 프롬프트 보여줘'")
        else:
            console.print("4. Try: '내 베스트 프롬프트 보여줘'")
    else:
        console.print("1. Run '/mcp' in Claude Code to verify claude-x is listed")
        if session_count == 0:
            console.print("2. Use Claude Code to create some sessions")
            console.print("3. Then try: '내 베스트 프롬프트 보여줘'")
        else:
            console.print("2. Try: '내 베스트 프롬프트 보여줘'")


@app.command()
def doctor():
    """Diagnose installation and configuration issues."""
    import sys
    import shutil

    console.print("\n[bold]Claude-X System Diagnostics[/bold]")
    console.print("─" * 60)

    issues = []
    recommendations = []

    # 1. Python version check
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 10):
        console.print(f"✅ Python Version: {py_version} (compatible)")
    else:
        console.print(f"❌ Python Version: {py_version} (requires 3.10+)")
        issues.append("Python version too old")
        recommendations.append("Upgrade to Python 3.10 or later")

    # 2. Dependencies check
    try:
        import rich
        import typer
        import pydantic
        console.print("✅ Dependencies: All installed")
    except ImportError as e:
        console.print(f"❌ Dependencies: Missing {e.name}")
        issues.append(f"Missing dependency: {e.name}")
        recommendations.append("Run: pip install claude-x")

    # 3. Claude Code check
    claude_dir = Path.home() / ".claude"
    projects_dir = claude_dir / "projects"
    if projects_dir.exists():
        console.print(f"✅ Claude Code: Found at {claude_dir}")

        # Count sessions
        indexer = SessionIndexer()
        project_dirs = indexer.find_all_project_dirs()
        session_count = sum(1 for _ in indexer.iter_all_sessions())
        console.print(f"   {len(project_dirs)} projects, {session_count} sessions")
    else:
        console.print(f"❌ Claude Code: Not found at {claude_dir}")
        issues.append("Claude Code not installed or never used")
        recommendations.append("Install Claude Code from https://claude.ai/code")
        recommendations.append("Run at least one Claude Code session")

    # 4. Database check
    data_dir = Path.home() / ".claude-x" / "data"
    db_path = data_dir / "claude_x.db"
    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        console.print(f"✅ Database: Healthy ({size_mb:.1f} MB)")

        # Get stats
        try:
            storage = get_storage()
            stats = storage.get_stats()
            console.print(f"   {stats.get('sessions', 0)} sessions indexed")
        except Exception as e:
            console.print(f"[yellow]   Warning: Could not read stats: {e}[/yellow]")
    else:
        console.print(f"❌ Database: Not initialized")
        recommendations.append("Run: cx init")

    # 5. Disk space check
    if data_dir.exists():
        stat = shutil.disk_usage(data_dir)
        free_gb = stat.free / (1024 ** 3)
        if free_gb < 1:
            console.print(f"⚠️  Disk Space: Low ({free_gb:.1f} GB free)")
            recommendations.append("Free up disk space")
        else:
            console.print(f"✅ Disk Space: {free_gb:.1f} GB free")

    # 6. MCP Server Configuration Check
    claude_settings = Path.home() / ".claude" / "settings.json"
    if claude_settings.exists():
        try:
            with open(claude_settings, 'r') as f:
                settings = json.load(f)

            if 'mcpServers' in settings and 'claude-x' in settings['mcpServers']:
                console.print("✅ MCP Server: Configured in settings.json")
                mcp_config = settings['mcpServers']['claude-x']
                console.print(f"   Command: {mcp_config.get('command', 'N/A')}")
            else:
                console.print("❌ MCP Server: Not configured")
                issues.append("MCP server not in settings.json")
                recommendations.append("Run: cx init")
        except Exception as e:
            console.print(f"❌ MCP Server: Error reading settings.json - {e}")
            issues.append("Invalid settings.json")
            recommendations.append("Delete ~/.claude/settings.json and run: cx init")
    else:
        console.print("❌ MCP Server: settings.json not found")
        issues.append("No Claude Code settings file")
        recommendations.append("Run: cx init")

    # 7. MCP Command Check
    import subprocess
    cx_mcp_path = shutil.which("cx-mcp")
    if cx_mcp_path:
        console.print(f"✅ cx-mcp: Found at {cx_mcp_path}")

        # Test MCP server
        try:
            result = subprocess.run(
                [sys.executable, "-m", "claude_x.mcp_server"],
                input='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}\n',
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and "result" in result.stdout:
                console.print("✅ MCP Server: Test successful")
            else:
                console.print("⚠️  MCP Server: Test failed")
                console.print(f"   Error: {result.stderr[:100]}")
                issues.append("MCP server not responding correctly")
                recommendations.append("Reinstall: pip install --force-reinstall claude-x")
        except subprocess.TimeoutExpired:
            console.print("✅ MCP Server: Running (timeout expected)")
        except Exception as e:
            console.print(f"❌ MCP Server: Test error - {e}")
            issues.append("MCP server test failed")
    else:
        console.print("❌ cx-mcp: Command not found")
        issues.append("cx-mcp not in PATH")
        recommendations.append("Reinstall: pip install --force-reinstall claude-x")

    # 8. Claude Code Restart Reminder
    console.print("\n[bold cyan]MCP Troubleshooting:[/bold cyan]")
    console.print("If /mcp doesn't show claude-x after cx init:")
    console.print("1. [bold]Completely quit Claude Code (Cmd+Q)[/bold]")
    console.print("2. [bold]Reopen Claude Code[/bold]")
    console.print("3. Run '/mcp' command")
    console.print("4. Look for 'claude-x' in the list")

    # Summary
    console.print("\n" + "─" * 60)
    if issues:
        console.print(f"\n[bold red]Issues Found: {len(issues)}[/bold red]")
        for issue in issues:
            console.print(f"  • {issue}")

        console.print(f"\n[bold yellow]Recommendations:[/bold yellow]")
        for rec in recommendations:
            console.print(f"  → {rec}")

        console.print("\n[bold]Overall Status: Needs Attention ⚠️[/bold]")
    else:
        console.print("\n[bold green]Overall Status: Healthy ✓[/bold green]")

    console.print()


@app.command("import")
def import_sessions(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project name")
):
    """Import session logs from ~/.claude directory."""
    storage = get_storage()
    indexer = SessionIndexer()
    extractor = CodeExtractor()
    scanner = SecurityScanner()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Importing sessions...", total=None)
        counts = _import_sessions(
            storage=storage,
            indexer=indexer,
            extractor=extractor,
            scanner=scanner,
            project=project,
            incremental=True,
            progress=progress,
            progress_task=task,
        )

    console.print(f"\n✅ Import complete!")
    console.print(f"  Sessions: {counts['sessions']}")
    console.print(f"  Messages: {counts['messages']}")
    console.print(f"  Code Snippets: {counts['snippets']}")


@app.command()
def watch(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project name"),
    debounce: float = typer.Option(2.0, "--debounce", help="Debounce seconds for import"),
):
    """Watch Claude Code sessions and import incrementally."""
    storage = get_storage()
    indexer = SessionIndexer()
    extractor = CodeExtractor()
    scanner = SecurityScanner()

    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        console.print("[red]Claude Code projects directory not found: ~/.claude/projects[/red]")
        return

    import_in_progress = False

    def run_import():
        nonlocal import_in_progress
        if import_in_progress:
            return
        import_in_progress = True
        try:
            counts = _import_sessions(
                storage=storage,
                indexer=indexer,
                extractor=extractor,
                scanner=scanner,
                project=project,
                incremental=True,
            )
            if counts["messages"] or counts["snippets"]:
                from datetime import datetime
                now = datetime.now().strftime("%H:%M:%S")
                console.print(
                    f"[green]✅ [{now}][/green] "
                    f"Imported [bold]{counts['messages']}[/bold] messages, "
                    f"[bold]{counts['snippets']}[/bold] code snippets"
                )
        finally:
            import_in_progress = False

    class SessionWatchHandler(FileSystemEventHandler):
        def __init__(self, debounce_seconds: float):
            self.debounce_seconds = debounce_seconds
            self.last_run = 0.0

        def on_any_event(self, event):
            if event.is_directory:
                return
            path = str(event.src_path)
            if not (path.endswith(".jsonl") or path.endswith("sessions-index.json")):
                return
            now = time.time()
            if now - self.last_run < self.debounce_seconds:
                return  # Skip if within debounce window
            self.last_run = now
            run_import()

    handler = SessionWatchHandler(debounce)
    observer = Observer()
    observer.schedule(handler, str(projects_dir), recursive=True)
    observer.start()

    # Show initial status
    sessions = list(storage.list_sessions(limit=1))
    total_sessions = len(list(storage.list_sessions(limit=10000)))
    console.print()
    console.print("[bold cyan]╭─────────────────────────────────────╮[/bold cyan]")
    console.print("[bold cyan]│[/bold cyan]  👀 Claude-X Watch Mode            [bold cyan]│[/bold cyan]")
    console.print("[bold cyan]╰─────────────────────────────────────╯[/bold cyan]")
    console.print()
    console.print(f"📁 Monitoring: [dim]{projects_dir}[/dim]")
    console.print(f"📊 Sessions in DB: [green]{total_sessions}[/green]")
    if sessions:
        last = sessions[0]
        console.print(f"🕐 Last session: [dim]{last.get('created_at', 'N/A')}[/dim]")
    console.print()
    console.print("[dim]Waiting for Claude Code activity...[/dim]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()

    # Initial import
    run_import()

    try:
        poll_count = 0
        while True:
            time.sleep(1)
            poll_count += 1
            # Fallback: check every 60 seconds in case watchdog misses events
            if poll_count >= 60:
                poll_count = 0
                run_import()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Stopped watching.[/yellow]")
        observer.stop()
    observer.join()


@app.command("list")
def list_sessions(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Filter by git branch"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max results")
):
    """List sessions."""
    storage = get_storage()
    sessions = storage.list_sessions(project_name=project, branch=branch, limit=limit)

    if not sessions:
        console.print("No sessions found.")
        return

    table = Table(title=f"Sessions ({len(sessions)} results)")
    table.add_column("Session ID", style="cyan", no_wrap=True)
    table.add_column("Project", style="green")
    table.add_column("Branch", style="yellow")
    table.add_column("Messages", justify="right")
    table.add_column("First Prompt", style="dim")
    table.add_column("Modified", style="magenta")

    for session in sessions:
        table.add_row(
            session["session_id"][:12] + "...",
            session["project_name"],
            session["git_branch"] or "N/A",
            str(session["message_count"] or 0),
            (session["first_prompt"] or "")[:50] + "...",
            session["modified_at"][:10] if session["modified_at"] else "N/A"
        )

    console.print(table)


@app.command()
def search(
    query: str,
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Filter by language"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project"),
    limit: int = typer.Option(10, "--limit", help="Max results"),
    full: bool = typer.Option(False, "--full", "-f", help="Show full text without truncation"),
    show_sensitive: bool = typer.Option(False, "--show-sensitive", help="Show sensitive snippets")
):
    """Search code snippets using full-text search."""
    storage = get_storage()
    results = storage.search_code(query, language=lang, limit=limit)

    if not results:
        console.print(f"No results found for: {query}")
        return

    console.print(f"\n🔍 Found {len(results)} results for: [bold]{query}[/bold]\n")

    for i, result in enumerate(results, 1):
        # Filter by project if specified
        if project and project.lower() not in result["project_name"].lower():
            continue

        console.print(f"[bold cyan]Result {i}[/bold cyan]")
        console.print(f"  Project: [green]{result['project_name']}[/green]")
        console.print(f"  Branch: [yellow]{result['git_branch'] or 'N/A'}[/yellow]")
        console.print(f"  Language: [blue]{result['language']}[/blue]")
        sensitive_marker = " ⚠️" if result.get("has_sensitive") else ""
        console.print(f"  Lines: {result['line_count']}{sensitive_marker}")

        # Show prompt (always show full text - it's important context)
        prompt_text = result['first_prompt']
        console.print(f"  Prompt: [dim]{prompt_text}[/dim]")

        # Show code (truncate unless --full flag)
        code_text = result['code']
        if result.get("has_sensitive") and not show_sensitive:
            code_text = "[REDACTED]"
        if full or len(code_text) <= 500:
            console.print(f"\n[dim]{code_text}[/dim]\n")
        else:
            console.print(f"\n[dim]{code_text[:500]}...[/dim]\n")
            console.print(f"[dim]💡 Use --full to see complete code[/dim]\n")
        if result.get("has_sensitive") and not show_sensitive:
            console.print(f"[dim]💡 Use --show-sensitive to view redacted content[/dim]\n")


@app.command()
def stats(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project")
):
    """Show statistics."""
    storage = get_storage()
    stats_data = storage.get_session_stats(project_name=project)

    table = Table(title="Claude-X Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Projects", str(stats_data["project_count"]))
    table.add_row("Sessions", str(stats_data["session_count"]))
    table.add_row("Messages", str(stats_data["message_count"]))
    table.add_row("Code Snippets", str(stats_data["code_snippet_count"]))

    console.print(table)


@app.command()
def show(
    session_id: str,
    code_only: bool = typer.Option(False, "--code", help="Show only code snippets"),
    show_sensitive: bool = typer.Option(False, "--show-sensitive", help="Show sensitive snippets")
):
    """Show session details or code snippets."""
    storage = get_storage()

    # Get session details
    session = storage.get_session_detail(session_id)
    if not session:
        console.print(f"[red]Session not found:[/red] {session_id}")
        return

    if code_only:
        # Show only code snippets
        snippets = storage.get_session_code_snippets(session_id)

        if not snippets:
            console.print("[yellow]No code snippets found in this session.[/yellow]")
            return

        console.print(f"\n[bold cyan]Code Snippets ({len(snippets)} total)[/bold cyan]")
        console.print(f"Session: {session['session_id'][:16]}...")
        console.print(f"Project: [green]{session['project_name']}[/green]")
        console.print()

        for i, snippet in enumerate(snippets, 1):
            sensitive_marker = " ⚠️" if snippet.get("has_sensitive") else ""
            console.print(f"[bold]Snippet {i}[/bold] ([blue]{snippet['language']}[/blue], {snippet['line_count']} lines){sensitive_marker}")
            code_preview = snippet["code"]
            if snippet.get("has_sensitive") and not show_sensitive:
                code_preview = "[REDACTED]"
            preview_text = code_preview[:300] if code_preview else ""
            console.print(f"[dim]{preview_text}{'...' if len(code_preview) > 300 else ''}[/dim]\n")
            if snippet.get("has_sensitive") and not show_sensitive:
                console.print(f"[dim]💡 Use --show-sensitive to view redacted content[/dim]\n")
    else:
        # Show full session details
        console.print(f"\n[bold cyan]Session Details[/bold cyan]")
        console.print(f"ID: {session['session_id']}")
        console.print(f"Project: [green]{session['project_name']}[/green]")
        console.print(f"Branch: [yellow]{session['git_branch'] or 'N/A'}[/yellow]")
        console.print(f"Messages: {session['message_count'] or 0}")
        console.print(f"Created: {session['created_at'][:19] if session['created_at'] else 'N/A'}")
        console.print(f"Modified: {session['modified_at'][:19] if session['modified_at'] else 'N/A'}")
        console.print(f"\n[bold]First Prompt:[/bold]")
        console.print(f"[dim]{session['first_prompt'] or 'N/A'}[/dim]")

        # Show messages
        messages = storage.get_session_messages(session_id)
        console.print(f"\n[bold]Messages ({len(messages)} total):[/bold]\n")

        for i, msg in enumerate(messages[:10], 1):  # Show first 10 messages
            role_color = "green" if msg["type"] == "user" else "blue"
            code_marker = " 💻" if msg.get("has_code") else ""
            console.print(f"[{role_color}]{i}. {msg['type'].upper()}{code_marker}[/{role_color}]")
            console.print(f"[dim]{msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}[/dim]\n")

        if len(messages) > 10:
            console.print(f"[dim]... and {len(messages) - 10} more messages[/dim]")


@app.command()
def report(
    project: str = typer.Option("front", "--project", "-p", help="Project name to analyze"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Export to JSON file"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json, csv")
):
    """Generate analytics report for prompt usage."""
    storage = get_storage()
    analytics = PromptAnalytics(storage)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generating analytics report...", total=None)
        full_report = analytics.generate_full_report(project)
        progress.update(task, description="✅ Report generated")

    if output:
        # Export to file
        output_path = Path(output)
        if format == "json" or output.endswith(".json"):
            analytics.export_to_json(full_report, output_path)
            console.print(f"✅ Report exported to: {output_path}")
            return
        else:
            console.print("[red]CSV export requires specific data type (use --format json)[/red]")
            return

    # Display in terminal
    console.print(f"\n[bold cyan]📊 Prompt Usage Analytics Report[/bold cyan]")
    console.print(f"Project: [green]{project}[/green]")
    console.print(f"Generated: {full_report['generated_at'][:19]}\n")

    # Category Statistics
    console.print("[bold]1. 카테고리별 통계[/bold]")
    cat_table = Table()
    cat_table.add_column("카테고리", style="cyan")
    cat_table.add_column("세션수", justify="right")
    cat_table.add_column("프롬프트수", justify="right")
    cat_table.add_column("코드수", justify="right")
    cat_table.add_column("평균 메시지/세션", justify="right")
    cat_table.add_column("평균 코드/세션", justify="right")

    for cat in full_report["category_stats"]:
        cat_table.add_row(
            cat["category"],
            str(cat["session_count"]),
            str(cat["user_prompts"]),
            str(cat["code_count"]),
            str(cat["avg_messages_per_session"]),
            str(cat["avg_code_per_session"])
        )
    console.print(cat_table)
    console.print()

    # Branch Productivity
    console.print("[bold]2. 브랜치 타입별 생산성[/bold]")
    branch_table = Table()
    branch_table.add_column("브랜치", style="yellow")
    branch_table.add_column("세션수", justify="right")
    branch_table.add_column("총 메시지", justify="right")
    branch_table.add_column("코드 생성", justify="right")
    branch_table.add_column("코드/메시지 비율", justify="right")

    for branch in full_report["branch_productivity"]:
        branch_table.add_row(
            branch["branch_type"],
            str(branch["session_count"]),
            str(branch["total_messages"]),
            str(branch["code_count"]),
            str(branch["code_per_message_ratio"])
        )
    console.print(branch_table)
    console.print()

    # Language Distribution
    console.print("[bold]3. 언어 분포 (Top 10)[/bold]")
    lang_table = Table()
    lang_table.add_column("언어", style="blue")
    lang_table.add_column("개수", justify="right")
    lang_table.add_column("비율", justify="right")
    lang_table.add_column("총 라인수", justify="right")

    for lang in full_report["language_distribution"][:10]:
        lang_table.add_row(
            lang["language"],
            str(lang["count"]),
            f"{lang['percentage']}%",
            str(lang["total_lines"])
        )
    console.print(lang_table)
    console.print()

    # Time Analysis
    time_data = full_report["time_analysis"]
    console.print("[bold]4. 시간대별 분석[/bold]")

    if time_data["most_productive_day"]:
        console.print(f"가장 생산적인 날: [green]{time_data['most_productive_day']['date']}[/green] "
                     f"(코드 {time_data['most_productive_day']['code_count']}개 생성)")

    if time_data["hour_distribution"]:
        top_hours = sorted(time_data["hour_distribution"], key=lambda x: x["sessions"], reverse=True)[:3]
        console.print(f"활동 많은 시간대: ", end="")
        console.print(", ".join([f"{h['hour']}시 ({h['sessions']}회)" for h in top_hours]))
    console.print()

    # Top Sessions
    console.print("[bold]5. 활동량 상위 세션 (Top 5)[/bold]")
    top_table = Table()
    top_table.add_column("세션 ID", style="dim")
    top_table.add_column("브랜치", style="yellow")
    top_table.add_column("메시지", justify="right")
    top_table.add_column("코드", justify="right")
    top_table.add_column("첫 프롬프트", style="dim")

    for session in full_report["top_sessions"][:5]:
        top_table.add_row(
            session["session_id"][:12] + "...",
            session["git_branch"] or "N/A",
            str(session["message_count"]),
            str(session["code_count"]),
            (session["first_prompt"] or "")[:40] + "..."
        )
    console.print(top_table)
    console.print()

    # Sensitive Data Report
    sensitive = full_report["sensitive_data"]
    console.print("[bold]6. 민감 정보 검출 현황[/bold]")
    console.print(f"총 코드 스니펫: {sensitive['statistics']['total_snippets']}")
    console.print(f"민감 정보 포함: [yellow]{sensitive['statistics']['sensitive_count']}[/yellow] "
                 f"({sensitive['statistics']['sensitive_percentage']}%)")

    if sensitive["affected_sessions"]:
        console.print(f"영향받는 세션: {len(sensitive['affected_sessions'])}개")
    console.print()

    console.print("[dim]💡 Tip: Use --output report.json to export full data[/dim]")


@app.command()
def prompts(
    project: str = typer.Option("front", "--project", "-p", help="Project name to analyze"),
    best_only: bool = typer.Option(False, "--best-only", help="Show only best prompts"),
    worst_only: bool = typer.Option(False, "--worst-only", help="Show only worst prompts"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of prompts to show"),
    prompt_length: int = typer.Option(120, "--prompt-length", help="Max prompt preview length"),
    include_nocode: bool = typer.Option(False, "--include-nocode", help="Include sessions without code"),
    include_commands: bool = typer.Option(False, "--include-commands", help="Include command-only prompts"),
    export: bool = typer.Option(False, "--export", "-e", help="Export to markdown file"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Custom output path for markdown"),
    min_quality: Optional[float] = typer.Option(None, "--min-quality", help="Minimum combined structure+context score"),
    strict: bool = typer.Option(False, "--strict", help="Strict mode: require structure>=3.0, context>=2.0")
):
    """Analyze prompt quality and generate prompt library."""
    storage = get_storage()
    analytics = PromptAnalytics(storage)

    if export:
        # Export to markdown
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating prompt library...", total=None)

            if output:
                output_path = Path(output)
            else:
                output_path = None  # Use default

            result_path = analytics.export_prompt_library(project, output_path)
            progress.update(task, description="✅ Library generated")

        console.print(f"✅ Prompt library exported to: {result_path}")
        console.print(f"📖 Open the file to see best practices and patterns")
        return

    # Display in terminal
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Analyzing prompt quality...", total=None)
        best = []
        worst = []
        if not worst_only:
            best = analytics.get_best_prompts(
                project,
                limit,
                include_nocode=include_nocode,
                include_commands=include_commands,
                min_quality=min_quality,
                strict_mode=strict
            )
        if not best_only:
            worst = analytics.get_worst_prompts(
                project,
                limit,
                include_nocode=include_nocode,
                include_commands=include_commands
            )

        progress.update(task, description="✅ Analysis complete")

    console.print(f"\n[bold cyan]🎯 Prompt Quality Analysis[/bold cyan]")
    console.print(f"Project: [green]{project}[/green]\n")

    if not worst_only:
        console.print("[bold green]🏆 베스트 프롬프트 (성공 패턴)[/bold green]\n")

        for i, p in enumerate(best, 1):
            # Use new category icon and v2 composite score
            cat_icon = p.get('category_icon', '📝')
            composite_v2 = p.get('composite_score_v2', p.get('composite_score', 0))
            console.print(f"[bold cyan]{i}. {cat_icon} {p['category']}[/bold cyan] (종합 점수: [green]{composite_v2}/10[/green])")
            console.print(f"[dim]프롬프트:[/dim] {p['first_prompt'][:prompt_length]}{'...' if len(p['first_prompt']) > prompt_length else ''}")
            console.print(f"[dim]브랜치:[/dim] [yellow]{p['git_branch'] or 'N/A'}[/yellow]  "
                         f"[dim]세션:[/dim] {p['session_id'][:12]}...")

            # New v2 score breakdown
            structure = p.get('structure_score', 0)
            context = p.get('context_score', 0)
            efficiency_v2 = p.get('efficiency_score_v2', p.get('efficiency_score', 0))
            diversity = p.get('diversity_score', 0)
            console.print(f"  📊 구조: {structure}/10 | 컨텍스트: {context}/10 | "
                         f"효율: {efficiency_v2}/10 | 다양성: {diversity}/10")

            # Metrics
            console.print(f"  💻 코드 {p['code_count']}개 ({p['total_lines']}줄) | "
                         f"💬 메시지 {p['message_count']}개 | "
                         f"🌐 언어 {p['language_diversity']}종류")

            if p['sensitive_count'] > 0:
                console.print(f"  [yellow]⚠️  민감 정보 {p['sensitive_count']}건 발견[/yellow]")

            console.print()

    if not best_only and not worst_only:
        console.print("\n" + "─" * 80 + "\n")

    if not best_only:
        console.print("[bold red]⚠️  개선이 필요한 프롬프트[/bold red]\n")

        for i, p in enumerate(worst, 1):
            cat_icon = p.get('category_icon', '📝')
            composite_v2 = p.get('composite_score_v2', p.get('composite_score', 0))
            console.print(f"[bold yellow]{i}. {cat_icon} {p['category']}[/bold yellow] (종합 점수: [red]{composite_v2}/10[/red])")
            console.print(f"[dim]프롬프트:[/dim] {p['first_prompt'][:prompt_length]}{'...' if len(p['first_prompt']) > prompt_length else ''}")

            # Issues based on new v2 scores
            issues = []
            structure = p.get('structure_score', 0)
            context = p.get('context_score', 0)
            if structure < 3:
                issues.append("구조 부족")
            if context < 3:
                issues.append("컨텍스트 부족")
            if p['message_count'] > 100:
                issues.append("긴 대화")
            if p['sensitive_count'] > 0:
                issues.append(f"민감정보 {p['sensitive_count']}건")
            if p['language_diversity'] < 2:
                issues.append("단일 언어")

            if issues:
                console.print(f"  [red]❌ 문제점:[/red] {', '.join(issues)}")

            console.print(f"  📊 구조: {structure}/10 | 컨텍스트: {context}/10 | "
                         f"메시지: {p['message_count']}개")
            console.print()

    console.print("\n[bold]💡 프롬프트 작성 팁:[/bold]")
    console.print("  1. 명확한 목표와 구체적인 요구사항 명시")
    console.print("  2. 예상 결과물의 형태나 예시 제공")
    console.print("  3. 큰 작업은 작은 단위로 분리해서 진행")
    console.print("  4. 컨텍스트와 제약사항을 명확히 전달")

    console.print(f"\n[dim]💡 Tip: Use --export to save as markdown library[/dim]")


@app.command()
def coach(
    prompt: str = typer.Argument(..., help="Prompt to analyze"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    no_extensions: bool = typer.Option(False, "--no-ext", help="Disable extension detection"),
    no_history: bool = typer.Option(False, "--no-history", help="Disable user history"),
):
    """
    Analyze a prompt and receive improvement suggestions.

    Examples:
        cx coach "응 진행해줘"
        cx coach "fix this bug" --json
        cx coach "implement feature" --no-ext
    """
    from claude_x.mcp_server import analyze_and_improve_prompt
    from claude_x.i18n import t
    from rich.panel import Panel

    result = analyze_and_improve_prompt(
        prompt=prompt,
        detect_extensions=not no_extensions,
        include_history=not no_history,
    )

    if json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    lang = result["language"]

    title = t("analysis.title", lang)
    console.print(Panel(title, style="bold blue"))

    console.print("\n" + t("analysis.scores", lang))
    console.print(t("scores.value", lang, label=t("analysis.structure", lang), score=result["scores"]["structure"]))
    console.print(t("scores.value", lang, label=t("analysis.context", lang), score=result["scores"]["context"]))

    if result["problems"]:
        console.print("\n" + t("analysis.problems", lang))
        for idx, problem in enumerate(result["problems"], 1):
            console.print(f"{idx}. {problem['description']}")
            if problem.get("impact"):
                console.print(f"   {problem['impact']}", style="dim")

    if result["suggestions"]:
        console.print("\n" + t("analysis.suggestions", lang))
        for idx, suggestion in enumerate(result["suggestions"], 1):
            console.print(f"\n[bold]{idx}. {suggestion['title']}[/bold]")
            console.print(Panel(suggestion["template"], border_style="green"))
            if suggestion.get("why_successful"):
                console.print(f"   {suggestion['why_successful']}", style="dim")

    if result.get("extension_suggestion"):
        ext = result["extension_suggestion"]
        console.print("\n" + t("analysis.extension_suggestion", lang))
        console.print(f"[bold cyan]{ext['command']}[/bold cyan]")
        console.print(t("extensions.reason", lang, reason=ext["reason"]))

    if result.get("expected_impact"):
        impact = result["expected_impact"]
        console.print("\n" + t("analysis.expected_impact", lang))
        if lang == "ko":
            console.print(f"- 메시지 수: {impact['messages']['improvement']}")
            console.print(f"- 코드 생성: {impact['code_generation']['improvement']}")
            console.print(f"- 성공률: {impact['success_rate']['improvement']}")
        else:
            console.print(f"- Messages: {impact['messages']['improvement']}")
            console.print(f"- Code generation: {impact['code_generation']['improvement']}")
            console.print(f"- Success rate: {impact['success_rate']['improvement']}")


@app.command(hidden=True)
def cx(prompt: str = typer.Argument(...)):
    """Alias for 'coach' command."""
    coach(prompt)


@app.command()
def templates(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search templates"),
    show: Optional[str] = typer.Option(None, "--show", help="Show specific template by name"),
    export: bool = typer.Option(False, "--export", "-e", help="Export all templates to markdown"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Custom output path")
):
    """Browse and use prompt templates."""
    library = PromptTemplateLibrary()

    if export:
        # Export to markdown
        if output:
            output_path = Path(output)
        else:
            output_path = Path.home() / ".claude-x" / "prompt-templates.md"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        templates_list = library.get_all_templates()
        lines = [
            "# 프롬프트 템플릿 라이브러리",
            "",
            f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"총 템플릿: {len(templates_list)}개",
            "",
            "이 문서는 실제 프로젝트 데이터 분석을 통해 추출한 **베스트 프랙티스 프롬프트 패턴**을 템플릿화한 것입니다.",
            "각 템플릿은 실제로 높은 성과를 낸 프롬프트 구조를 기반으로 만들어졌습니다.",
            "",
            "---",
            "",
            "## 📚 사용 방법",
            "",
            "1. 카테고리에서 원하는 템플릿 선택",
            "2. 템플릿의 {{variables}} 부분을 실제 값으로 치환",
            "3. Claude에게 프롬프트 입력",
            "",
            "**CLI 사용:**",
            "```bash",
            "# 모든 템플릿 목록",
            "cx templates",
            "",
            "# 특정 템플릿 상세 보기",
            "cx templates --show jira_ticket_creation",
            "",
            "# 카테고리별 필터링",
            "cx templates --category 기능\\ 구현",
            "",
            "# 키워드 검색",
            "cx templates --search jira",
            "```",
            "",
            "---",
            ""
        ]

        # Group by category
        by_category = {}
        for template in templates_list:
            cat = template.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(template)

        # TOC
        lines.extend([
            "## 목차",
            ""
        ])
        for cat, tmpls in sorted(by_category.items()):
            lines.append(f"### {cat}")
            for t in tmpls:
                lines.append(f"- [{t.name}](#{t.name.replace('_', '-')}): {t.description[:60]}...")
            lines.append("")

        lines.append("---\n")

        # Detailed templates
        for cat, tmpls in sorted(by_category.items()):
            lines.extend([
                f"## {cat}",
                ""
            ])

            for t in tmpls:
                lines.extend([
                    f"### {t.name}",
                    "",
                    f"**설명:** {t.description}",
                    "",
                    f"**변수:** `{'`, `'.join(t.variables)}`",
                    "",
                    f"**태그:** {', '.join(t.tags)}",
                    "",
                    f"**성공 지표:** {t.success_metrics}",
                    "",
                    "#### 템플릿",
                    "```",
                    t.template,
                    "```",
                    "",
                    "#### 사용 예시",
                    "```",
                    t.example,
                    "```",
                    "",
                    "---",
                    ""
                ])

        lines.extend([
            "## 💡 템플릿 작성 팁",
            "",
            "좋은 프롬프트의 공통 요소:",
            "",
            "1. **명확한 액션**: \"만들어줘\", \"리뷰해줘\", \"조사해줘\" 등",
            "2. **충분한 컨텍스트**: 현재 상황, 배경 설명",
            "3. **구체적 요구사항**: 구조화된 포맷으로 제공",
            "4. **예시 제공**: 원하는 결과물의 형태 제시",
            "5. **제약사항 명시**: 지켜야 할 규칙 명확히",
            "",
            "---",
            "",
            f"📝 이 문서는 `cx templates --export` 명령으로 생성되었습니다.",
            ""
        ])

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        console.print(f"✅ Templates exported to: {output_path}")
        return

    if show:
        # Show specific template
        try:
            template = library.get_template_by_name(show)

            console.print(f"\n[bold cyan]📝 {template.name}[/bold cyan]")
            console.print(f"[dim]카테고리: {template.category}[/dim]\n")

            console.print(f"[bold]설명:[/bold]")
            console.print(f"{template.description}\n")

            console.print(f"[bold]변수:[/bold] [yellow]{', '.join(template.variables)}[/yellow]\n")

            console.print(f"[bold]태그:[/bold] {', '.join(template.tags)}\n")

            console.print(f"[bold]성공 지표:[/bold]")
            console.print(f"{template.success_metrics}\n")

            console.print("[bold green]템플릿:[/bold green]")
            console.print(f"[dim]{template.template}[/dim]\n")

            console.print("[bold blue]사용 예시:[/bold blue]")
            console.print(f"[dim]{template.example}[/dim]\n")

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print("\n사용 가능한 템플릿:")
            for t in library.get_all_templates():
                console.print(f"  - {t.name}")
        return

    # List templates
    if search:
        templates_list = library.search_templates(search)
        console.print(f"\n[bold cyan]🔍 검색 결과: \"{search}\"[/bold cyan]")
    elif category:
        templates_list = library.get_templates_by_category(category)
        console.print(f"\n[bold cyan]📂 카테고리: {category}[/bold cyan]")
    else:
        templates_list = library.get_all_templates()
        console.print(f"\n[bold cyan]📚 프롬프트 템플릿 라이브러리[/bold cyan]")

    console.print(f"총 {len(templates_list)}개 템플릿\n")

    if not templates_list:
        console.print("[yellow]검색 결과가 없습니다.[/yellow]")
        return

    # Group by category
    by_category = {}
    for template in templates_list:
        cat = template.category
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(template)

    for cat, tmpls in sorted(by_category.items()):
        console.print(f"[bold yellow]{cat}[/bold yellow]")
        for t in tmpls:
            console.print(f"  [cyan]{t.name}[/cyan]")
            console.print(f"    {t.description[:80]}...")
            console.print(f"    [dim]변수: {', '.join(t.variables[:3])}{'...' if len(t.variables) > 3 else ''}[/dim]")
            console.print()

    console.print(f"\n[dim]💡 Tip: Use --show <name> to see full template[/dim]")
    console.print(f"[dim]💡 Tip: Use --export to save all templates as markdown[/dim]")


@app.command("export")
def export_prompts(
    format: str = typer.Option("html", "--format", "-f", help="Output format: html, json, gist"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max prompts to export"),
    public: bool = typer.Option(False, "--public", help="Make gist public (gist format only)"),
    strict: bool = typer.Option(False, "--strict", help="Strict quality filtering"),
    min_quality: Optional[float] = typer.Option(None, "--min-quality", help="Minimum quality score"),
):
    """Export best prompts to HTML, JSON, or GitHub Gist.

    Examples:
        cx export --format html --output best-prompts.html
        cx export --format json --output prompts.json
        cx export --format gist --public
    """
    storage = get_storage()
    analytics = PromptAnalytics(storage)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Fetching best prompts...", total=None)

        prompts = analytics.get_best_prompts(
            project_name=project,
            limit=limit,
            strict_mode=strict,
            min_quality=min_quality,
        )

        progress.update(task, description=f"Found {len(prompts)} prompts")

    if not prompts:
        console.print("[yellow]No prompts found to export.[/yellow]")
        console.print("[dim]Try: cx import to import session data first.[/dim]")
        return

    if format == "html":
        if not output:
            output = str(Path.home() / ".claude-x" / "best-prompts.html")

        Path(output).parent.mkdir(parents=True, exist_ok=True)
        result = export_to_html(prompts, output)
        console.print(f"[green]✅ Exported to HTML: {result}[/green]")
        console.print(f"[dim]Open in browser: file://{result}[/dim]")

    elif format == "json":
        if not output:
            output = str(Path.home() / ".claude-x" / "best-prompts.json")

        Path(output).parent.mkdir(parents=True, exist_ok=True)
        result = export_to_json(prompts, output)
        console.print(f"[green]✅ Exported to JSON: {result}[/green]")

    elif format == "gist":
        console.print("[dim]Creating GitHub Gist...[/dim]")
        result = export_to_gist(prompts, public=public)

        if result.get("success"):
            console.print(f"[green]✅ Gist created successfully![/green]")
            console.print(f"[bold]URL: {result['url']}[/bold]")
            if public:
                console.print("[dim]This is a public gist - anyone with the link can view it.[/dim]")
            else:
                console.print("[dim]This is a secret gist - only you can find it.[/dim]")
        else:
            console.print(f"[red]❌ Failed to create gist: {result.get('error')}[/red]")
            console.print("[dim]Make sure gh CLI is installed and authenticated: gh auth login[/dim]")

    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        console.print("[dim]Supported formats: html, json, gist[/dim]")


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
