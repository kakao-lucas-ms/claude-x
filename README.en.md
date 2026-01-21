# Claude-X (cx)

> **Second Brain and Command Center for Claude Code**
>
> Transform your Claude Code conversation history into a searchable database and turn your prompt patterns into reusable knowledge assets.

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**[🇰🇷 한국어](README.md) | [🇺🇸 English](README.en.md)**

## Features

### 💾 Session Data Collection & Storage
- Automatically collects all Claude Code sessions from `~/.claude/projects/`
- SQLite + FTS5 full-text search for blazing-fast queries
- Automatic code snippet extraction with language detection
- Sensitive information detection (API keys, tokens, credentials - 14 patterns)

### 🔍 Powerful Search
- Full-text search across all code snippets
- Filter by project, branch, and programming language
- Detailed session and message browsing

### 📊 Prompt Analysis & Knowledge Building
- Automatic best/worst prompt analysis (4 metrics)
- Curated collection of successful prompts
- Reusable prompt template library

### 📈 Usage Reports
- Statistics by category, branch, and language
- Time-based activity analysis
- Productivity metrics

## Quick Start

### Installation

```bash
# Using pip
pip install claude-x

# Using pipx (recommended for CLI tools)
pipx install claude-x

# From source
git clone https://github.com/kakao/claude-x.git
cd claude-x
pip install -e .
```

### First Use

```bash
# Auto-initializes on first run
cx stats

# Search your code
cx search "useState" --lang typescript

# View recent sessions
cx list --limit 10

# Analyze your prompts
cx prompts --best-only

# Browse templates
cx templates
```

### Health Check

```bash
cx doctor
```

## Core Commands

| Command | Description |
|---------|-------------|
| `cx init` | Initialize database (auto-runs on first use) |
| `cx import` | Import Claude Code sessions |
| `cx list` | List recent sessions |
| `cx search <query>` | Search code snippets |
| `cx stats` | View usage statistics |
| `cx show <session-id>` | Show session details |
| `cx prompts` | Analyze prompt patterns |
| `cx templates` | Browse prompt templates |
| `cx doctor` | Diagnose issues |

## Requirements

- **Python 3.10+** (3.13 recommended)
- **Claude Code CLI** - must be installed and used at least once
- Dependencies: `rich`, `typer`, `pydantic`, `watchdog`

## Architecture

```
~/.claude/projects/          Claude-X Processing        ~/.claude-x/
├── project1/               ─────────────────>          ├── data/
│   ├── sessions-index.json    1. Parse index           │   └── claude_x.db
│   └── sessions/              2. Parse JSONL           ├── prompt-library/
│       └── abc123.jsonl       3. Extract code          │   └── *-prompts.md
├── project2/                  4. Detect secrets        └── prompt-templates.md
│   └── ...                    5. Store in DB
```

### Database Schema

**Four Main Tables:**
- `projects` - Project directories
- `sessions` - Claude Code sessions
- `messages` - Individual messages
- `code_snippets` - Extracted code with FTS5 index

### Tech Stack

- **Python 3.10+** - Modern Python features
- **SQLite + FTS5** - Lightning-fast full-text search
- **Pydantic** - Type-safe data validation
- **Typer + Rich** - Beautiful CLI interface
- **uv** (optional) - Fast package management

## Generated Files

### Database
```
~/.claude-x/data/claude_x.db
```
All session, message, and code data with FTS5 search index.

### Analysis Reports
```
~/.claude-x/prompt-library/{project}-prompts.md
```
- Top 15 best prompts (detailed analysis)
- Bottom 10 worst prompts (improvement tips)
- Categorized by type
- Prompt writing tips

### Template Library
```
~/.claude-x/prompt-templates.md
```
8 reusable templates with variables, examples, and success metrics.

## Use Cases

### 1. Knowledge Mining
Extract insights from your Claude Code history:
```bash
# Find all React hooks usage
cx search "useState|useEffect" --lang typescript

# Analyze successful patterns
cx prompts --best-only --export
```

### 2. Prompt Engineering
Learn from your successful prompts:
```bash
# Browse templates
cx templates

# Study specific pattern
cx templates --show jira_ticket_creation

# Export your best prompts as templates
cx prompts --project frontend --export
```

### 3. Productivity Analysis
Understand your coding patterns:
```bash
# Overall stats
cx stats

# Project-specific analysis
cx stats --project backend

# Generate detailed report
cx report --project frontend --output report.json
```

## Performance

### Optimized for Speed
- **FTS5 Index**: Sub-second search across millions of lines
- **WAL Mode**: Concurrent read/write operations
- **Efficient Pagination**: Handle large datasets smoothly

### Scalability
Tested with:
- 1,000+ sessions
- 10,000+ messages
- 50,000+ code snippets

## Troubleshooting

### Database is Empty
```bash
rm -rf ~/.claude-x/data/claude_x.db
cx init
cx import
```

### Sessions Not Importing
**Check:**
- Claude Code is installed: `which claude`
- Sessions directory exists: `ls ~/.claude/projects/`
- Sessions have been created

```bash
# Import specific project
cx import --project "myproject"
```

### No Search Results
```bash
# Rebuild index
rm ~/.claude-x/data/claude_x.db
cx init
cx import
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/kakao/claude-x.git
cd claude-x

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Test
cx init
cx import --project "test-project"
```

### Project Structure

```
claude-x/
├── src/claude_x/
│   ├── cli.py              # CLI interface
│   ├── models.py           # Pydantic models
│   ├── indexer.py          # sessions-index.json parser
│   ├── session_parser.py   # JSONL session parser
│   ├── extractor.py        # Code extraction
│   ├── security.py         # Secret detection
│   ├── storage.py          # SQLite backend
│   ├── analytics.py        # Prompt analysis
│   └── prompt_templates.py # Template library
├── pyproject.toml
└── README.md
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Areas for Contribution
- Additional prompt templates
- Enhanced analytics metrics
- UI/visualization tools
- Integration with other tools
- Documentation improvements

## Roadmap

- [ ] Web UI for session browsing
- [ ] Real-time session monitoring (`cx watch`)
- [ ] Export to various formats (CSV, JSON)
- [ ] Integration with note-taking apps
- [ ] Prompt A/B testing framework

## License

MIT License - see [LICENSE](LICENSE) file.

## Credits

- **Claude Code** - Excellent AI coding assistant CLI
- **SQLite FTS5** - Powerful full-text search
- **Typer + Rich** - Beautiful CLI framework

## Contact

Issues and suggestions: https://github.com/kakao/claude-x/issues

---

**Made with ❤️ by lucas.ms**

**For Claude Code Users**
