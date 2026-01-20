"""Command-line interface for Claude-X."""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import datetime

from .indexer import SessionIndexer
from .session_parser import SessionParser
from .extractor import CodeExtractor
from .security import SecurityScanner
from .storage import Storage
from .models import Project, Session, Message
from .analytics import PromptAnalytics
from .prompt_templates import PromptTemplateLibrary

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


@app.command()
def init():
    """Initialize Claude-X database."""
    storage = get_storage()
    console.print("✅ Database initialized at:", storage.db_path)


@app.command("import")
def import_sessions(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project name")
):
    """Import session logs from ~/.claude directory."""
    storage = get_storage()
    indexer = SessionIndexer()
    extractor = CodeExtractor()
    scanner = SecurityScanner()

    total_sessions = 0
    total_messages = 0
    total_snippets = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Importing sessions...", total=None)

        for project_dir, session_entry in indexer.iter_all_sessions():
            # Filter by project if specified
            if project:
                project_name = indexer.extract_project_name(session_entry.project_path or "")
                if project.lower() not in project_name.lower():
                    continue

            # Insert project
            project_path = indexer.decode_project_path(project_dir.name)
            project_model = Project(
                path=project_path,
                encoded_path=project_dir.name,
                name=indexer.extract_project_name(project_path)
            )
            project_id = storage.insert_project(project_model)

            # Insert session
            session_model = Session(
                session_id=session_entry.session_id,
                project_id=project_id,
                full_path=session_entry.full_path,
                first_prompt=session_entry.first_prompt,
                message_count=session_entry.message_count,
                git_branch=session_entry.git_branch,
                is_sidechain=session_entry.is_sidechain,
                file_mtime=session_entry.file_mtime,
                created_at=datetime.fromisoformat(session_entry.created.replace("Z", "+00:00")),
                modified_at=datetime.fromisoformat(session_entry.modified.replace("Z", "+00:00"))
            )
            storage.insert_session(session_model)
            total_sessions += 1

            # Parse messages
            session_path = Path(session_entry.full_path)
            if not session_path.exists():
                continue

            parser = SessionParser(session_path)
            for message in parser.parse_messages(session_entry.session_id):
                message_id = storage.insert_message(message)
                total_messages += 1

                # Extract code blocks
                if message.has_code:
                    for snippet in extractor.extract_code_blocks(
                        message_id, session_entry.session_id, message.content
                    ):
                        # Scan for sensitive data
                        snippet.has_sensitive = scanner.has_sensitive_data(snippet.code)

                        # Insert snippet
                        if storage.insert_code_snippet(snippet):
                            total_snippets += 1

            progress.update(
                task,
                description=f"Imported {total_sessions} sessions, {total_messages} messages, {total_snippets} code snippets"
            )

    console.print(f"\n✅ Import complete!")
    console.print(f"  Sessions: {total_sessions}")
    console.print(f"  Messages: {total_messages}")
    console.print(f"  Code Snippets: {total_snippets}")


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
    limit: int = typer.Option(10, "--limit", help="Max results")
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
        console.print(f"  Lines: {result['line_count']}")
        console.print(f"  Prompt: [dim]{result['first_prompt'][:60]}...[/dim]")
        console.print(f"\n[dim]{result['code'][:200]}...[/dim]\n")


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
    code_only: bool = typer.Option(False, "--code", help="Show only code snippets")
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
            console.print(f"[dim]{snippet['code'][:300]}{'...' if len(snippet['code']) > 300 else ''}[/dim]\n")
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
    export: bool = typer.Option(False, "--export", "-e", help="Export to markdown file"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Custom output path for markdown")
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

        if not worst_only:
            best = analytics.get_best_prompts(project, limit)
        if not best_only:
            worst = analytics.get_worst_prompts(project, limit)

        progress.update(task, description="✅ Analysis complete")

    console.print(f"\n[bold cyan]🎯 Prompt Quality Analysis[/bold cyan]")
    console.print(f"Project: [green]{project}[/green]\n")

    if not worst_only:
        console.print("[bold green]🏆 베스트 프롬프트 (성공 패턴)[/bold green]\n")

        for i, p in enumerate(best, 1):
            console.print(f"[bold cyan]{i}. {p['category']}[/bold cyan] (종합 점수: [green]{p['composite_score']}[/green])")
            console.print(f"[dim]프롬프트:[/dim] {p['first_prompt'][:120]}{'...' if len(p['first_prompt']) > 120 else ''}")
            console.print(f"[dim]브랜치:[/dim] [yellow]{p['git_branch'] or 'N/A'}[/yellow]  "
                         f"[dim]세션:[/dim] {p['session_id'][:12]}...")

            # Score breakdown
            console.print(f"  📊 효율성: {p['efficiency_score']} | "
                         f"명확성: {p['clarity_score']} | "
                         f"생산성: {p['total_lines']}줄 | "
                         f"품질: {p['quality_score']}/10")

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
            console.print(f"[bold yellow]{i}. {p['category']}[/bold yellow] (종합 점수: [red]{p['composite_score']}[/red])")
            console.print(f"[dim]프롬프트:[/dim] {p['first_prompt'][:120]}{'...' if len(p['first_prompt']) > 120 else ''}")

            # Issues
            issues = []
            if p['efficiency_score'] < 1:
                issues.append("낮은 효율성")
            if p['message_count'] > 100:
                issues.append("긴 대화")
            if p['sensitive_count'] > 0:
                issues.append(f"민감정보 {p['sensitive_count']}건")
            if p['language_diversity'] < 2:
                issues.append("단일 언어")

            if issues:
                console.print(f"  [red]❌ 문제점:[/red] {', '.join(issues)}")

            console.print(f"  📊 효율성: {p['efficiency_score']} | "
                         f"명확성: {p['clarity_score']} | "
                         f"메시지: {p['message_count']}개")
            console.print()

    console.print("\n[bold]💡 프롬프트 작성 팁:[/bold]")
    console.print("  1. 명확한 목표와 구체적인 요구사항 명시")
    console.print("  2. 예상 결과물의 형태나 예시 제공")
    console.print("  3. 큰 작업은 작은 단위로 분리해서 진행")
    console.print("  4. 컨텍스트와 제약사항을 명확히 전달")

    console.print(f"\n[dim]💡 Tip: Use --export to save as markdown library[/dim]")


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


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
