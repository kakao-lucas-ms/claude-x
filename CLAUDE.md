# Claude-X Development Guide

> **For Claude Code AI Assistant**
>
> This file contains important project context, development workflows, and guidelines for working on claude-x.

## 🎯 Project Overview

**claude-x** is a Second Brain and Command Center for Claude Code that:
- Collects and indexes all Claude Code session history
- Provides full-text search over code snippets
- Analyzes prompt quality and extracts reusable templates
- Offers MCP (Model Context Protocol) server for real-time data access

**Current Version:** 0.3.7

## 🏗️ Repository Structure

```
claude-x-standalone/
├── src/claude_x/           # Main package
│   ├── cli.py              # CLI commands (cx)
│   ├── mcp_server.py       # MCP server (claude-x)
│   ├── storage.py          # SQLite + FTS5
│   ├── analytics.py        # Prompt analysis
│   ├── indexer.py          # Session indexing
│   ├── session_parser.py   # JSONL parser
│   ├── extractor.py        # Code extraction
│   ├── security.py         # Sensitive data detection
│   ├── scoring.py          # Quality scoring
│   └── patterns.py         # Pattern analysis (v0.3.7)
├── .claude-plugin/         # Claude Code plugin config
├── workflows/              # GitHub Actions workflows
├── pyproject.toml          # Package metadata
└── CLAUDE.md               # This file
```

## 🔄 Development Workflow

### 1. Testing Changes

```bash
# Install in development mode
pip3 install -e .

# Test CLI commands
cx --version
cx stats

# Test MCP server functions directly
python3 -c "
from claude_x.mcp_server import analyze_sessions, get_best_prompts
print(analyze_sessions())
print(get_best_prompts(limit=2))
"
```

### 2. MCP Server Testing

**Restart Claude Code to reload MCP server:**
1. Quit Claude Code completely
2. Start Claude Code again
3. MCP server will reload with changes

**Test MCP tools in Claude Code:**
```
User: "Analyze my session statistics"
→ Triggers mcp__claude-x__analyze_sessions

User: "Show me my best prompts"
→ Triggers mcp__claude-x__get_best_prompts
```

### 3. Version Update Process

When releasing a new version:

```bash
# 1. Update version in 3 files:
# - pyproject.toml
# - .claude-plugin/plugin.json
# - src/claude_x/__init__.py

# 2. Update CHANGELOG.md with new features

# 3. Update README.md if needed

# 4. Commit version bump
git add pyproject.toml .claude-plugin/plugin.json src/claude_x/__init__.py CHANGELOG.md README.md
git commit -m "chore: bump version to X.Y.Z"

# 5. Push to GitHub
git push origin main

# 6. Create GitHub Release
# → GitHub Actions will automatically build and publish to PyPI
```

## 🚀 Release Process

### Automated PyPI Publishing

**PyPI releases are automated via GitHub Actions.**

When you create a GitHub release:
1. GitHub Actions workflow is triggered
2. Package is built automatically
3. Uploaded to PyPI with release credentials
4. No manual `twine upload` needed

**To release:**
```bash
# 1. Create and push a git tag
git tag v0.3.7
git push origin v0.3.7

# 2. Create GitHub Release via web UI or gh CLI
gh release create v0.3.7 --generate-notes

# 3. GitHub Actions handles the rest
```

**Note:** If you need to manually publish:
```bash
# Build package
python3 -m build

# Upload to PyPI (requires API token)
python3 -m twine upload dist/*
```

## 🔑 Git Multi-Account Setup

This project uses SSH with multiple GitHub accounts.

### SSH Configuration

```bash
# ~/.ssh/config
Host github-new
 HostName github.com
 User git
 AddKeysToAgent yes
 UseKeychain yes
 IdentityFile ~/.ssh/id_ed25519_newaccount

Host github_old
 HostName github.com
 User git
 AddKeysToAgent yes
 UseKeychain yes
 IdentityFile ~/.ssh/id_ed25519_old
```

### Current Setup

```bash
# Remote URL (using github-new account)
git remote set-url origin git@github-new:kakao-lucas-ms/claude-x.git

# Verify
git remote -v
```

## 📦 Key Features by Version

### v0.3.7 (2026-01-23)
- **Reusable Templates**: Auto-extract templates from best prompts
- **LLM-Friendly Summaries**: `llm_summary` and `next_actions` in MCP responses
- **Watch Mode**: `cx watch` for real-time session monitoring
- **Incremental Import**: Offset-based resume for large sessions

### v0.3.6
- Enhanced `cx doctor` with MCP diagnostics
- Auto-import sessions during `cx init`
- Auto-create settings.json for first-time users

### v0.1.0
- Initial release with core features
- Session indexing and search
- Prompt quality analysis
- Template library

## 🛠️ Common Tasks

### Add New MCP Tool

1. Edit `src/claude_x/mcp_server.py`:
```python
@mcp.tool()
def new_tool_name(param: str) -> dict:
    """Tool description for Claude Code."""
    # Implementation
    return {"result": "data"}
```

2. Test locally:
```python
from claude_x.mcp_server import new_tool_name
print(new_tool_name("test"))
```

3. Restart Claude Code to test in UI

### Add New CLI Command

1. Edit `src/claude_x/cli.py`:
```python
@app.command()
def new_command(
    option: str = typer.Option(None, "--option", "-o")
):
    """Command description."""
    # Implementation
```

2. Test:
```bash
cx new-command --option value
```

### Database Schema Changes

When modifying `storage.py`:

1. Test with fresh DB:
```bash
rm ~/.claude-x/data/claude_x.db
cx init
cx import
```

2. Test with existing DB (migration):
```bash
# Ensure backward compatibility
cx import  # Should not fail
```

## 🔍 Debugging Tips

### MCP Server Not Working

1. Check server registration:
```bash
cat ~/.claude/settings.json | grep -A10 claude-x
```

2. Check Python path:
```bash
which python3
python3 -m claude_x.mcp_server
```

3. Restart Claude Code

### Database Issues

```bash
# Check database
sqlite3 ~/.claude-x/data/claude_x.db "SELECT COUNT(*) FROM sessions;"

# Rebuild from scratch
rm ~/.claude-x/data/claude_x.db
cx init
cx import
```

### Import Failures

```bash
# Verbose import
cx import --project claude-x

# Check session files
ls -la ~/.claude/projects/*/sessions/
```

## 📊 Testing MCP Features (v0.3.7)

### Test `analyze_sessions`

```python
from claude_x.mcp_server import analyze_sessions
result = analyze_sessions()

# Check new fields
assert "llm_summary" in result
assert "next_actions" in result
print(result["llm_summary"])
```

### Test `get_best_prompts`

```python
from claude_x.mcp_server import get_best_prompts
result = get_best_prompts(limit=2)

# Check new fields
assert "reuse_ready" in result
assert "reuse_guidance" in result
print(result["reuse_ready"][0]["template_preview"])
```

### Test `cx watch`

```bash
# Terminal 1: Start watch mode
cx watch

# Terminal 2: Use Claude Code
# → New sessions auto-imported

# Check logs
cx stats
```

## 🎯 Design Principles

1. **MCP-First**: Prioritize MCP server features for Claude Code integration
2. **LLM-Friendly**: Return structured data optimized for LLM consumption
3. **Incremental**: Support resume/offset for large data processing
4. **Zero Config**: Auto-setup on first run
5. **Local First**: All data stays on local machine

## 📝 Code Style

- Use type hints for all functions
- Docstrings for public APIs
- Rich for CLI output
- Pydantic for data validation
- SQLite + FTS5 for storage

## 🔗 Important Links

- **Repository**: https://github.com/kakao-lucas-ms/claude-x
- **PyPI**: https://pypi.org/project/claude-x/
- **Issues**: https://github.com/kakao-lucas-ms/claude-x/issues
- **MCP Docs**: https://modelcontextprotocol.io/

## 🚨 Before Committing

- [ ] Update version in 3 files
- [ ] Update CHANGELOG.md
- [ ] Test MCP server (restart Claude Code)
- [ ] Test CLI commands
- [ ] Run `cx import` on test data
- [ ] Check `cx doctor` passes

## 📞 Maintenance

**Owner**: lucas.ms (kakao-lucas-ms@kakaocorp.com)

**Python Version**: 3.10+

**Dependencies**:
- rich (terminal UI)
- typer (CLI)
- watchdog (file monitoring)
- pydantic (validation)
- mcp (Model Context Protocol)

---

Last Updated: 2026-01-23 (v0.3.7)
