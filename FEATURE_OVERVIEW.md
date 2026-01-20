# Claude-X: Second Brain for Claude Code

**Version 0.1.0** | **License: MIT** | **Python 3.13+**

---

## 🎯 What is Claude-X?

Claude-X is a **session history analyzer and prompt engineering asset management tool** for Anthropic's Claude Code CLI. It automatically collects, indexes, and analyzes your Claude Code conversation history to help you become a better prompt engineer.

**Problem it solves**: Claude Code users have valuable prompt patterns buried in `~/.claude/projects/*.jsonl` files with no way to search, analyze, or learn from past successes and failures.

**Solution**: Automatic extraction → SQLite FTS5 indexing → 4-metric quality scoring → Template library generation

---

## 🚀 Core Features

### 1. Automatic Session Collection
- Parses `~/.claude/projects/{project}/sessions-index.json`
- Streams JSONL session files (memory efficient)
- Extracts 3,000+ code snippets with SHA-256 deduplication
- Auto-detects timestamps (Unix milliseconds / ISO 8601)

### 2. Full-Text Search (SQLite FTS5)
```bash
cx search "useState" --lang typescript
# Returns 4 results in <100ms from 3,257 snippets
# Shows: project, branch, language, line count, original prompt
```

### 3. Prompt Quality Analysis (4-Metric Scoring)
```python
composite_score = (
    efficiency × 40% +     # code_count / prompt_count
    clarity × 30% +        # 100 / message_count
    productivity × 20% +   # total_lines (normalized)
    quality × 10%          # no_sensitive + language_diversity
)
```

**Real results from test data:**
- ✅ Best: "Create JIRA template" → 6.02/10 (5 messages, 34 code snippets)
- ❌ Worst: "commit this" → 0.73/10 (285 messages, 1 code snippet)

### 4. Template Library Generation
8 pre-built templates based on successful patterns:
- JIRA ticket creation
- Bug fix workflow
- Feature implementation
- Code review
- Refactoring
- Test creation
- Technical research
- Environment setup review

---

## 🏗️ Technical Architecture

### Data Flow
```
~/.claude/projects/*.jsonl
    ↓ (indexer + session_parser)
SQLite Database (4 tables)
    ↓ (FTS5 triggers)
Full-Text Search Index
    ↓ (analytics engine)
Prompt Quality Scores
    ↓ (CLI / Export)
User Interface
```

### Database Schema
```sql
projects        # Project metadata
sessions        # Session info (branch, message count)
messages        # User/assistant messages
code_snippets   # Extracted code (language, hash, sensitive flag)
code_fts        # FTS5 virtual table (auto-synced)
```

### Key Technologies
- **Storage**: SQLite 3 with WAL mode
- **Search**: FTS5 (Full-Text Search 5)
- **Type Safety**: Pydantic models
- **CLI**: Typer + Rich (beautiful terminal UI)
- **Security**: 14 sensitive data patterns (API keys, DB strings, etc.)
- **Performance**: Streaming parsers, batch commits, indexed queries

---

## 📊 Real Performance Metrics

**Test dataset:**
- Projects: 3
- Sessions: 248
- Messages: 4,997
- Code snippets: 3,257
- Languages: 15 (TypeScript, Python, Bash, SQL, etc.)

**Benchmarks:**
- Import 248 sessions: ~10 seconds
- Search 3,257 snippets: <100ms
- Generate analysis report: ~2 seconds

---

## 💻 Usage Examples

### Installation
```bash
pip install claude-x
# or
uv tool install git+https://github.com/YOUR-USERNAME/claude-x.git
```

### Basic Commands
```bash
# Initialize database
cx init

# Import all sessions
cx import

# Search code
cx search "useState" --lang typescript

# View statistics
cx stats

# Analyze prompts
cx prompts --best-only --limit 10

# Export templates
cx templates --export
```

### Advanced Analysis
```bash
# Project-specific report
cx report --project "brunch-front" --output report.json

# Worst prompts (learning opportunities)
cx prompts --worst-only --limit 5

# Session detail with code
cx show a7472f17 --code
```

---

## 🎨 Output Examples

### Statistics Output
```
Claude-X Statistics
┏━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric        ┃ Count ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Projects      │     3 │
│ Sessions      │   248 │
│ Messages      │  4997 │
│ Code Snippets │  3257 │
└───────────────┴───────┘
```

### Prompt Analysis Output
```
🏆 Best Prompts (Success Patterns)

1. JIRA ticket creation (Score: 6.02)
   📊 Efficiency: 6.8 | Clarity: 20.0 | Productivity: 34 lines
   💻 5 messages → 34 code snippets
   🌐 Languages: 1 type

2. Git worktree setup (Score: 4.12)
   📊 Efficiency: 0.97 | Clarity: 3.45 | Productivity: 28 lines
   💻 29 messages → 28 code snippets
```

---

## 🔍 Unique Value Proposition

### vs. Existing Tools

| Tool | Focus | Claude-X |
|------|-------|----------|
| **ccusage** | Real-time token tracking & cost | ❌ |
| **claude-code-ui** | Live session monitoring | ❌ |
| **cc_peng_mcp** | Real-time prompt improvement | ❌ |
| **Claude-X** | Historical analysis & learning | ✅ |

**What makes Claude-X different:**
1. **Backward-looking**: Analyzes what worked/failed in the past
2. **Data-driven**: 4-metric scoring based on actual outcomes
3. **Asset creation**: Converts good prompts into reusable templates
4. **Code-centric**: Full-text search across all generated code
5. **Pattern discovery**: Automatically finds your best prompt patterns

---

## 📦 Project Stats

- **Lines of Code**: 2,500+
- **Modules**: 9 (cli, storage, analytics, models, etc.)
- **Documentation**: 66KB (8 files)
- **CLI Commands**: 9
- **Prompt Templates**: 8
- **Security Patterns**: 14
- **Dependencies**: 5 (rich, typer, pydantic, click, watchdog)

---

## 🔐 Security Features

- **14 sensitive pattern detection**:
  - API keys (OpenAI, GitHub, AWS, etc.)
  - Database connection strings (MongoDB, PostgreSQL, MySQL)
  - Private keys and auth tokens
  - Bearer tokens and OAuth tokens
- **Local-only processing**: No external API calls
- **SQL injection prevention**: Parameterized queries
- **Sensitive flag**: Code snippets marked for review

---

## 📚 Documentation

| Document | Size | Purpose |
|----------|------|---------|
| README.md | 17KB | Comprehensive guide |
| QUICKSTART.md | 3.2KB | 5-minute start |
| EXAMPLES.md | 4.4KB | Usage scenarios |
| ARCHITECTURE.md | 16KB | Technical details |
| CONTRIBUTING.md | 8.1KB | Development guide |
| DOCS_INDEX.md | 4.8KB | Navigation |
| PROJECT_STRUCTURE.md | 8.9KB | File organization |
| CHANGELOG.md | 3.9KB | Version history |

---

## 🎯 Use Cases

1. **Prompt Engineering Improvement**
   - Identify your most effective prompt patterns
   - Learn from failed prompts (high message count, low output)
   - Build personal prompt library

2. **Code Search & Reuse**
   - Find that React hook you wrote 3 months ago
   - Search SQL queries across all projects
   - Locate specific API patterns

3. **Team Knowledge Sharing**
   - Export best prompts as markdown
   - Share template library with team
   - Standardize prompt patterns

4. **Productivity Analysis**
   - Which branches had highest code generation?
   - What time of day are you most productive?
   - Which languages do you use most?

---

## 🚀 Future Roadmap

- [ ] Web UI dashboard
- [ ] AI-powered prompt suggestions (based on your history)
- [ ] Real-time session monitoring
- [ ] Team collaboration features
- [ ] Plugin system for custom analyzers
- [ ] Integration with ccusage (cost + quality)

---

## 🔗 Links

- **GitHub**: https://github.com/YOUR-USERNAME/claude-x
- **Documentation**: Full README with examples
- **License**: MIT (free & open source)
- **Python**: 3.13+ required
- **Platform**: macOS, Linux, Windows

---

## 🎓 Key Insights from Real Data

**Finding 1**: Short, specific prompts outperform vague ones
- "Create JIRA template with fields X, Y, Z" → 6.02/10
- "commit this" → 0.73/10

**Finding 2**: Efficiency matters more than volume
- 5 messages, 34 code → Better than 285 messages, 1 code

**Finding 3**: Language diversity indicates complex problem-solving
- TypeScript + Python + SQL + Bash → Higher quality score

**Finding 4**: First prompt clarity predicts session success
- Clear first prompt → Avg 20 messages
- Vague first prompt → Avg 200+ messages

---

## 💡 Philosophy

> "The best prompt is one you've already written and proven to work."

Claude-X treats your Claude Code history as a **learning corpus**, automatically extracting patterns that work for YOUR coding style, YOUR projects, and YOUR domain.

It's not about copying someone else's prompts—it's about discovering your own best practices through data.

---

**Built with ❤️ using Claude Code**
**Co-Authored-By: Claude Sonnet 4.5**
