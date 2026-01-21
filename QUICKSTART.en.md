# Claude-X Quick Start Guide (5 Minutes)

Get up and running with Claude-X in under 5 minutes.

## Prerequisites

- Python 3.10 or later
- [Claude Code CLI](https://claude.ai/code) installed and used at least once

## Installation

### Option 1: pip (Recommended)

```bash
pip install claude-x
```

### Option 2: pipx (Isolated Environment)

```bash
pipx install claude-x
```

### Option 3: From Source

```bash
git clone https://github.com/kakao/claude-x.git
cd claude-x
pip install -e .
```

## First Use

Claude-X automatically initializes on first run:

```bash
cx stats
```

That's it! The database is created automatically and you can start exploring your Claude Code sessions.

## Essential Commands

### 1. View Statistics

```bash
cx stats
```

Shows overview of your sessions, messages, and code snippets.

### 2. Search Code

```bash
cx search "useState"

# Filter by language
cx search "async/await" --lang typescript

# Filter by project
cx search "API" --project brunch
```

### 3. List Sessions

```bash
cx list

# Show more
cx list --limit 50

# Filter by project
cx list --project myapp
```

### 4. Analyze Prompts

```bash
# Best prompts only
cx prompts --best-only --limit 10

# Export to markdown
cx prompts --export
```

### 5. Browse Templates

```bash
# List all templates
cx templates

# Show specific template
cx templates --show bug_fix

# Search templates
cx templates --search jira
```

### 6. Health Check

```bash
cx doctor
```

Diagnoses installation issues and provides recommendations.

## Common Workflows

### Daily Session Review

```bash
# Check what you worked on today
cx list --limit 10

# Search for specific patterns
cx search "bug fix"

# Review best prompts
cx prompts --best-only
```

### Learning from Success

```bash
# Export successful prompts
cx prompts --export

# Browse prompt templates
cx templates

# Study specific template
cx templates --show feature_implementation
```

### Project Analysis

```bash
# Project-specific stats
cx stats --project frontend

# Project sessions
cx list --project frontend

# Project code search
cx search "useState" --project frontend
```

##  Troubleshooting

### "Claude Code not found"

Make sure Claude Code is installed:
1. Visit https://claude.ai/code
2. Install Claude Code CLI
3. Run at least one session
4. Try `cx doctor` to diagnose

### "No sessions found"

```bash
# Run import explicitly
cx import

# Or filter by specific project
cx import --project myproject
```

### Database Issues

```bash
# Reinitialize database
rm -rf ~/.claude-x/data/claude_x.db
cx init
cx import
```

## Next Steps

- Read the [full README](README.md) (Korean) or [README.en.md](README.en.md) (English)
- Explore [examples](EXAMPLES.md)
- Check [architecture docs](ARCHITECTURE.md)
- Review [feature overview](FEATURE_OVERVIEW.md)

## Need Help?

- Run `cx --help` for all commands
- Run `cx doctor` for diagnostics
- File issues at https://github.com/kakao/claude-x/issues

---

Made with ❤️ for Claude Code users
