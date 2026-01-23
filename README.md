# Claude-X (cx)

> **Second Brain and Command Center for Claude Code**
>
> Claude Code의 모든 대화 히스토리를 검색 가능한 데이터베이스로 전환하고,
> 프롬프트 사용 패턴을 분석하여 개인 지식 자산으로 만드는 도구입니다.

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**[🇰🇷 한국어](README.md) | [🇺🇸 English](README.en.md) | [⚡ Quick Start (EN)](QUICKSTART.en.md)**

## 🎯 주요 기능

### 1. 💾 세션 데이터 수집 및 저장
- `~/.claude/projects/` 디렉토리의 모든 Claude Code 세션 자동 수집
- SQLite + FTS5 full-text search로 빠른 검색
- 코드 스니펫 자동 추출 및 언어별 분류
- 민감 정보 자동 검출 (API 키, 토큰 등 14개 패턴)

### 2. 🔍 강력한 검색 기능
- 전체 코드 스니펫 full-text search
- 프로젝트, 브랜치, 언어별 필터링
- 세션별 코드 및 메시지 상세 조회

### 3. 📊 프롬프트 분석 & 자산화
- 베스트/워스트 프롬프트 자동 분석 (4가지 지표)
- 실제 성공한 프롬프트 모음 생성
- 재사용 가능한 프롬프트 템플릿 라이브러리

### 4. 📈 사용 현황 리포트
- 카테고리별, 브랜치별, 언어별 통계
- 시간대별 활동 분석
- 생산성 지표 측정

### 5. 🤖 프롬프트 코칭
- 프롬프트 구조/맥락 점수 분석
- 개선 제안 및 예상 효과 계산
- 확장 시스템 명령어 추천

## 📦 설치

### 요구사항
- Python 3.13+
- Claude Code CLI (설치되어 있어야 함)

### 설치 방법

```bash
# 1. 저장소 클론
cd ~/workspace
git clone <repository-url> claude-x
cd claude-x

# 2. 패키지 설치 (uv 사용)
uv pip install -e .

# 3. 데이터베이스 초기화
cx init

# 4. 세션 데이터 가져오기
cx import
```

## 🚀 빠른 시작

```bash
# 1. 전체 세션 가져오기
cx import

# 2. 실시간 모니터링 (백그라운드)
cx watch &

# 3. 통계 확인
cx stats

# 4. 최근 세션 목록
cx list --limit 10

# 5. 코드 검색
cx search "useState" --lang typescript

# 6. 프롬프트 분석
cx prompts --best-only --limit 5

# 7. 프롬프트 코칭
cx coach "응 진행해줘"

# 8. 템플릿 라이브러리
cx templates
```

## 📖 상세 사용법

### cx init
데이터베이스 초기화

```bash
cx init
```

**생성 파일:**
- `~/.claude-x/data/claude_x.db` - SQLite 데이터베이스

---

### cx import
Claude Code 세션 데이터 가져오기

```bash
# 전체 프로젝트 가져오기
cx import

# 특정 프로젝트만 가져오기
cx import --project "brunch"
cx import -p "claude-help-me"
```

**처리 내용:**
- `~/.claude/projects/` 모든 디렉토리 스캔
- `sessions-index.json` 파싱
- JSONL 세션 파일 파싱
- 코드 스니펫 추출 (마크다운 코드 블록)
- 민감 정보 검출
- SQLite DB 저장

**출력 예시:**
```
⠙ Imported 248 sessions, 2020 messages, 3257 code snippets

✅ Import complete!
  Sessions: 248
  Messages: 2020
  Code Snippets: 3257
```

---

### cx list
세션 목록 조회

```bash
# 기본: 최근 20개 세션
cx list

# 개수 지정
cx list --limit 50

# 프로젝트 필터링
cx list --project "brunch-front"
cx list -p "claude-x"

# 브랜치 필터링
cx list --branch "main"
cx list -b "feature/BRUNCH-123"
```

**출력:**
```
Sessions (20 results)
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Session ID     ┃ Project      ┃ Branch ┃ Message ┃ First Prompt             ┃ Modified   ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ a7472f17-8c9... │ claude-x     │ main   │ 78      │ implement session parser │ 2026-01-20 │
└────────────────┴──────────────┴────────┴─────────┴──────────────────────────┴────────────┘
```

---

### cx search
코드 스니펫 full-text search

```bash
# 기본 검색
cx search "function"

# 언어 필터링
cx search "useState" --lang typescript
cx search "CREATE TABLE" --lang sql

# 프로젝트 필터링
cx search "git" --project "brunch"

# 개수 지정
cx search "api" --limit 20
```

**출력:**
```
🔍 Found 10 results for: useState

Result 1
  Project: brunch-front
  Branch: feature/BRUNCH-123
  Language: typescript
  Lines: 15
  Prompt: implement user profile component...

const [user, setUser] = useState<User | null>(null);
...
```

---

### cx stats
전체 통계 조회

```bash
# 전체 통계
cx stats

# 특정 프로젝트 통계
cx stats --project "brunch-front"
cx stats -p "claude-x"
```

**출력:**
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

---

### cx show
세션 상세 정보 조회

```bash
# 세션 전체 정보 (메시지 포함)
cx show a7472f17

# 코드 스니펫만 보기
cx show a7472f17 --code
```

**출력:**
```
Session Details
ID: a7472f17-8c91-4d23-9f8a-1234567890ab
Project: claude-x
Branch: main
Messages: 78
Created: 2026-01-20 15:30:00
Modified: 2026-01-20 18:45:00

First Prompt:
implement session parser for Claude Code JSONL files

Messages (10 total):
1. USER 💻
   implement session parser...

2. ASSISTANT
   I'll create a session parser...
```

---

### cx report
프롬프트 사용 현황 분석 리포트

```bash
# 터미널에 리포트 출력
cx report --project front

# JSON 파일로 내보내기
cx report --project front --output report.json
```

**출력:**
```
📊 Prompt Usage Analytics Report
Project: front
Generated: 2026-01-20T18:55:42

1. 카테고리별 통계
┏━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ 카테고리  ┃ 세션수 ┃ 프롬프트수 ┃ 코드수 ┃ 평균 메시지/세션 ┃
┡━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ 기타      │     24 │       2067 │    654 │             46.2 │
│ 문서화    │      2 │        112 │     33 │             19.5 │
│ 코드 리뷰 │      1 │         44 │     28 │             29.0 │
└───────────┴────────┴────────────┴────────┴──────────────────┘

2. 브랜치 타입별 생산성
3. 언어 분포
4. 시간대별 분석
5. 활동량 상위 세션
6. 민감 정보 검출 현황
```

---

### cx prompts
베스트/워스트 프롬프트 분석

```bash
# 베스트 + 워스트 모두 보기
cx prompts --project front

# 베스트만 보기
cx prompts --project front --best-only --limit 10

# 워스트만 보기
cx prompts --project front --worst-only --limit 5

# 마크다운으로 내보내기
cx prompts --project front --export
```

**점수 계산:**
- **효율성 (40%)**: 코드 생성량 / 프롬프트 수
- **명확성 (30%)**: 짧은 대화로 목표 달성
- **생산성 (20%)**: 총 생성 코드 라인 수
- **품질 (10%)**: 민감 정보 없음 + 언어 다양성

**출력:**
```
🏆 베스트 프롬프트 (성공 패턴)

1. 문서화 (종합 점수: 6.02)
프롬프트: 아래의 내용으로 지라 이슈 만들어줘...
브랜치: feature/BRUNCH-36518  세션: abce2dcc...
  📊 효율성: 6.8 | 명확성: 20.0 | 생산성: 294줄 | 품질: 8/10
  💻 코드 34개 (294줄) | 💬 메시지 5개 | 🌐 언어 2종류

⚠️  개선이 필요한 프롬프트

1. 기타 (종합 점수: 0.73)
프롬프트: commit this
  ❌ 문제점: 낮은 효율성, 긴 대화, 단일 언어
  📊 효율성: 0.02 | 명확성: 0.35 | 메시지: 285개
```

**생성 파일:**
- `~/.claude-x/prompt-library/front-prompts.md` (586줄)

---

### cx templates
재사용 가능한 프롬프트 템플릿

```bash
# 전체 템플릿 목록
cx templates

# 특정 템플릿 상세 보기
cx templates --show jira_ticket_creation

# 카테고리별 필터링
cx templates --category "기능 구현"

# 키워드 검색
cx templates --search jira

# 마크다운으로 내보내기
cx templates --export
```

**출력:**
```
📚 프롬프트 템플릿 라이브러리
총 8개 템플릿

문서화
  jira_ticket_creation
    구조화된 지라 티켓을 생성하는 프롬프트...
    변수: title, background, purpose...

기능 구현
  feature_implementation
    새 기능을 구현하는 프롬프트...
    변수: feature_name, requirements, behavior...
```

**템플릿 종류:**
1. `jira_ticket_creation` - 지라 티켓 생성
2. `technical_research` - 기술 조사
3. `environment_setup_review` - 환경 구축 검토
4. `bug_fix` - 버그 수정
5. `feature_implementation` - 기능 구현
6. `code_review` - 코드 리뷰
7. `refactoring` - 리팩토링
8. `test_creation` - 테스트 작성

**생성 파일:**
- `~/.claude-x/prompt-templates.md` (596줄)

---

### cx watch
실시간 세션 모니터링 및 자동 import

```bash
# 백그라운드에서 실행
cx watch &

# 프로젝트 필터링
cx watch --project my-project

# Debounce 시간 조정 (기본: 2초)
cx watch --debounce 5.0
```

**기능:**
- 새로운 세션 파일 자동 감지
- Incremental import (변경된 부분만 처리)
- 파일 mtime 기반 중복 방지
- Offset 추적으로 중단/재개 지원

**사용 시나리오:**
```bash
# 터미널 1: watch 실행
cx watch

# 터미널 2: Claude Code 작업
# → 새 세션이 자동으로 import됨

# 실시간 통계 확인
cx stats
```

---

## 🔌 MCP Server Integration

Claude-X는 MCP(Model Context Protocol) 서버를 제공하여 Claude Code에서 직접 데이터를 조회할 수 있습니다.

### 사용 가능한 MCP Tools

#### 1. `analyze_sessions`
세션 통계 및 LLM 친화적 요약

**새로운 기능 (v0.3.7):**
- `llm_summary`: 주요 언어, 카테고리, 피크 시간 요약
- `next_actions`: 프롬프트 개선을 위한 실행 가능한 제안

#### 2. `get_best_prompts`
고품질 프롬프트 추출 및 재사용 템플릿

**새로운 기능 (v0.3.7):**
- `reuse_ready`: 자동 추출된 재사용 가능한 템플릿
  - Placeholder 자동 감지 (`[URL]`, `[FILE_NAME]` 등)
  - 패턴 타입 분류 (reference_based, generic)
  - 채우기 가이드 및 체크리스트
- `reuse_guidance`: 템플릿 활용 가이드

#### 3. `get_prompt_patterns`
성공한 프롬프트 패턴 분석

**새로운 기능 (v0.3.7):**
- 실제 사용 기반 템플릿 자동 생성
- 품질 점수 기반 랭킹
- 재사용 가능한 템플릿 추천

**사용 예시:**
```
# Claude Code에서 직접 사용
User: "내 프롬프트 사용 패턴을 분석해줘"
→ analyze_sessions MCP tool 자동 호출

User: "좋은 프롬프트 예시 보여줘"
→ get_best_prompts MCP tool 자동 호출
```

#### 4. `analyze_and_improve_prompt`
프롬프트 분석 및 개선 제안

**새로운 기능 (v0.4.0):**
- 구조/맥락 점수 산출
- 개선안과 예상 효과 제공
- 확장 명령어 추천 (설치된 경우)

---

## 🏗️ 아키텍처

### 디렉토리 구조

```
claude-x/
├── src/claude_x/
│   ├── __init__.py
│   ├── cli.py              # CLI 인터페이스 (Typer + Rich)
│   ├── models.py           # Pydantic 데이터 모델
│   ├── indexer.py          # sessions-index.json 파서
│   ├── session_parser.py   # JSONL 세션 파일 파서
│   ├── extractor.py        # 코드 블록 추출 (정규식)
│   ├── security.py         # 민감 정보 검출 (14개 패턴)
│   ├── storage.py          # SQLite + FTS5 backend
│   ├── analytics.py        # 프롬프트 분석 엔진
│   └── prompt_templates.py # 템플릿 라이브러리
├── pyproject.toml
└── README.md
```

### 데이터 흐름

```
~/.claude/projects/          Claude-X 처리           ~/.claude-x/
├── project1/               ─────────────────>      ├── data/
│   ├── sessions-index.json    1. 인덱스 파싱       │   └── claude_x.db
│   └── sessions/              2. JSONL 파싱        ├── prompt-library/
│       └── abc123.jsonl       3. 코드 추출         │   └── front-prompts.md
├── project2/                  4. 민감정보 검출     ├── prompt-templates.md
│   └── ...                    5. DB 저장           └── my-best-prompts.md
```

### 데이터베이스 스키마

```sql
-- 프로젝트 테이블
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    encoded_path TEXT NOT NULL,
    name TEXT,
    session_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 세션 테이블
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    project_id INTEGER NOT NULL,
    full_path TEXT NOT NULL,
    first_prompt TEXT,
    message_count INTEGER,
    git_branch TEXT,
    is_sidechain BOOLEAN DEFAULT FALSE,
    file_mtime INTEGER,
    created_at DATETIME,
    modified_at DATETIME,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- 메시지 테이블
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    type TEXT NOT NULL,              -- 'user' or 'assistant'
    content TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    has_code BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- 코드 스니펫 테이블
CREATE TABLE code_snippets (
    id INTEGER PRIMARY KEY,
    message_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    language TEXT NOT NULL,
    code TEXT NOT NULL,
    hash TEXT NOT NULL,              -- SHA-256 (세션 내 중복 방지)
    line_count INTEGER,
    has_sensitive BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id),
    UNIQUE (session_id, hash)
);

-- FTS5 전문 검색 테이블
CREATE VIRTUAL TABLE code_fts USING fts5(
    code,
    language,
    content=code_snippets,
    content_rowid=id
);
```

### 주요 기술 스택

- **Python 3.13** - 최신 Python 기능 활용
- **SQLite + FTS5** - 빠른 full-text search
- **Pydantic** - 타입 안전 데이터 검증
- **Typer + Rich** - 아름다운 CLI 인터페이스
- **uv** - 빠른 패키지 관리

---

## 📊 생성되는 파일들

### 데이터베이스
```
~/.claude-x/data/claude_x.db
```
- 모든 세션, 메시지, 코드 데이터 저장
- FTS5 인덱스로 빠른 검색
- WAL 모드로 동시성 지원

### 분석 리포트
```
~/.claude-x/prompt-library/{project}-prompts.md
```
- 베스트 프롬프트 Top 15 (상세 분석)
- 워스트 프롬프트 Bottom 10 (개선 방향)
- 카테고리별 정리
- 프롬프트 작성 팁

### 템플릿 라이브러리
```
~/.claude-x/prompt-templates.md
```
- 8개 재사용 가능 템플릿
- 각 템플릿별 변수, 예시, 성공 지표
- 카테고리별 정리

### 개인 베스트 프롬프트
```
~/.claude-x/my-best-prompts.md
```
- 실제 사용한 좋은 프롬프트 모음
- 성과 지표 포함
- 패턴 분석

---

## 🛠️ 개발 가이드

### 개발 환경 설정

```bash
# 1. 저장소 클론
git clone <repo> claude-x
cd claude-x

# 2. 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 개발 모드로 설치
uv pip install -e .

# 4. 테스트
cx init
cx import --project "test-project"
```

### 새 기능 추가

**1. 새 CLI 명령어 추가:**

```python
# src/claude_x/cli.py
@app.command()
def my_command(
    param: str = typer.Option(..., "--param", "-p", help="Parameter description")
):
    """Command description."""
    storage = get_storage()
    # Implementation
    console.print("✅ Done!")
```

**2. 새 분석 기능 추가:**

```python
# src/claude_x/analytics.py
class PromptAnalytics:
    def my_analysis(self, project_name: str) -> List[Dict]:
        """New analysis method."""
        with self.storage._get_connection() as conn:
            cursor = conn.execute("SELECT ...")
            return [dict(row) for row in cursor.fetchall()]
```

**3. 새 템플릿 추가:**

```python
# src/claude_x/prompt_templates.py
PromptTemplate(
    name="my_template",
    category="카테고리",
    description="설명",
    template="{{variable}} 템플릿 내용",
    variables=["variable"],
    example="사용 예시",
    success_metrics="성공 지표",
    tags=["tag1", "tag2"]
)
```

---

## 🐛 문제 해결

### 1. 데이터베이스가 비어있음

```bash
# 데이터베이스 재초기화
rm -rf ~/.claude-x/data/claude_x.db
cx init
cx import
```

### 2. 세션이 import 되지 않음

**확인사항:**
- Claude Code가 설치되어 있는지
- `~/.claude/projects/` 디렉토리가 존재하는지
- 세션 파일이 있는지

```bash
# 디렉토리 확인
ls -la ~/.claude/projects/

# 특정 프로젝트만 가져오기
cx import --project "특정프로젝트명"
```

### 3. 검색 결과가 없음

```bash
# 인덱스 재구축
rm ~/.claude-x/data/claude_x.db
cx init
cx import
```

### 4. 프롬프트 분석이 비어있음

**원인:** 프로젝트에 충분한 세션이 없음

```bash
# 특정 프로젝트 확인
cx stats --project "프로젝트명"

# 세션 목록 확인
cx list --project "프로젝트명"
```

---

## 📈 성능 최적화

### 대용량 프로젝트 처리

```bash
# 단계별 import
cx import --project "project1"
cx import --project "project2"

# 통계만 보기 (빠름)
cx stats

# 검색 시 limit 사용
cx search "query" --limit 10
```

### 데이터베이스 최적화

```sql
-- SQLite 최적화 (자동 적용됨)
PRAGMA journal_mode=WAL;      -- 동시성 향상
PRAGMA foreign_keys=ON;       -- 참조 무결성
```

---

## 🤝 기여 가이드

### 버그 리포트
1. 재현 가능한 예시 제공
2. 환경 정보 (Python 버전, OS)
3. 에러 로그

### 기능 제안
1. 사용 사례 설명
2. 기대하는 동작
3. 가능하면 구현 아이디어

---

## 📝 라이선스

MIT License

---

## 🙏 감사의 말

- **Claude Code** - 훌륭한 CLI 도구
- **SQLite FTS5** - 빠른 전문 검색
- **Typer + Rich** - 아름다운 CLI

---

## 📞 문의

문제나 제안사항이 있으면 이슈를 열어주세요!

---

**Made with ❤️ by lucas.ms**
