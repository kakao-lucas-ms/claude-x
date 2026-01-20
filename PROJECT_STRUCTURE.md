# Project Structure

Claude-X 프로젝트의 전체 구조입니다.

## 📁 디렉토리 구조

```
claude-x/
├── src/claude_x/              # 소스 코드
│   ├── __init__.py            # 패키지 초기화
│   ├── cli.py                 # CLI 인터페이스 (Typer + Rich)
│   ├── models.py              # Pydantic 데이터 모델
│   ├── indexer.py             # sessions-index.json 파서
│   ├── session_parser.py      # JSONL 세션 파일 파서
│   ├── extractor.py           # 코드 블록 추출 (정규식)
│   ├── security.py            # 민감 정보 검출 (14개 패턴)
│   ├── storage.py             # SQLite + FTS5 backend
│   ├── analytics.py           # 프롬프트 분석 엔진
│   └── prompt_templates.py    # 템플릿 라이브러리
│
├── docs/                      # 문서 (계획)
│
├── tests/                     # 테스트 (계획)
│
├── pyproject.toml             # 프로젝트 설정
├── README.md                  # 메인 문서 (450+ 줄)
├── QUICKSTART.md              # 빠른 시작 가이드
├── EXAMPLES.md                # 사용 예시 시나리오별
├── ARCHITECTURE.md            # 아키텍처 설계 문서
├── CHANGELOG.md               # 변경 이력
└── PROJECT_STRUCTURE.md       # 이 파일
```

## 📦 모듈별 파일 설명

### `src/claude_x/cli.py` (550+ 줄)

**역할:** CLI 명령어 인터페이스

**주요 함수:**
- `init()` - DB 초기화
- `import_sessions()` - 세션 데이터 가져오기
- `list()` - 세션 목록
- `search()` - 코드 검색
- `stats()` - 통계
- `show()` - 세션 상세
- `report()` - 사용 현황 리포트
- `prompts()` - 프롬프트 분석
- `templates()` - 템플릿 라이브러리

**의존성:**
- Typer (CLI 프레임워크)
- Rich (터미널 UI)

---

### `src/claude_x/models.py` (100+ 줄)

**역할:** Pydantic 데이터 모델

**주요 모델:**
```python
class SessionIndex(BaseModel):
    """sessions-index.json 전체"""
    entries: List[SessionIndexEntry]

class SessionIndexEntry(BaseModel):
    """개별 세션 메타데이터"""
    session_id: str
    full_path: str
    first_prompt: Optional[str]
    # ...

class Project(BaseModel):
    """프로젝트 모델"""
    path: str
    name: str

class Session(BaseModel):
    """세션 모델"""
    session_id: str
    project_id: int
    # ...

class Message(BaseModel):
    """메시지 모델"""
    session_id: str
    type: str  # 'user' or 'assistant'
    content: str

class CodeSnippet(BaseModel):
    """코드 스니펫 모델"""
    message_id: int
    language: str
    code: str
    hash: str
```

---

### `src/claude_x/indexer.py` (150+ 줄)

**역할:** sessions-index.json 파서

**주요 기능:**
- 모든 프로젝트 디렉토리 검색
- sessions-index.json 파싱
- URL 디코딩 (프로젝트 경로)
- 프로젝트명 추출

**파일 경로:**
- 입력: `~/.claude/projects/{project}/sessions-index.json`
- 출력: `SessionIndex` 모델

---

### `src/claude_x/session_parser.py` (200+ 줄)

**역할:** JSONL 세션 파일 파서

**주요 기능:**
- JSONL 라인별 파싱
- 타임스탬프 자동 감지
  - Unix milliseconds
  - ISO 8601
- 이벤트 타입별 처리
  - SessionStart
  - MessageEvent

**파일 경로:**
- 입력: `~/.claude/projects/{project}/sessions/{session-id}.jsonl`
- 출력: `Message` 모델 스트림

---

### `src/claude_x/extractor.py` (80+ 줄)

**역할:** 마크다운 코드 블록 추출

**정규식:**
```python
r"```(\w+)?\n(.*?)```"
```

**주요 기능:**
- 코드 블록 감지 (언어 태그 포함)
- SHA-256 해시 계산 (중복 제거)
- 라인 수 계산

**처리 흐름:**
```
메시지 내용 → 정규식 매칭 → 코드 추출 → 해시 계산 → CodeSnippet
```

---

### `src/claude_x/security.py` (90+ 줄)

**역할:** 민감 정보 패턴 검출

**검출 패턴 (14개):**
1. API 키
2. OpenAI API 키
3. GitHub PAT
4. AWS Access Key
5. MongoDB 연결 문자열
6. PostgreSQL 연결 문자열
7. MySQL 연결 문자열
8. Private 키
9. Secret/Password
10. Auth Token
11. Bearer Token
12. GitHub OAuth Token
13. GitLab PAT
14. AWS Secret Key

**알고리즘:**
```
코드 → 14개 정규식 매칭 → 발견 시 True
```

---

### `src/claude_x/storage.py` (440+ 줄)

**역할:** SQLite 데이터베이스 관리

**테이블 (4개):**
- `projects` - 프로젝트 목록
- `sessions` - 세션 메타데이터
- `messages` - 메시지 내용
- `code_snippets` - 코드 스니펫

**가상 테이블:**
- `code_fts` - FTS5 full-text search

**최적화:**
- WAL 모드 (동시성)
- Foreign keys (참조 무결성)
- 인덱스 4개
- FTS5 자동 트리거 3개

**주요 메서드:**
- `insert_*()` - 데이터 삽입
- `search_code()` - FTS5 검색
- `list_sessions()` - 세션 목록
- `get_session_*()` - 세션 조회

---

### `src/claude_x/analytics.py` (350+ 줄)

**역할:** 프롬프트 품질 분석

**분석 지표:**
1. **효율성 (40%)**: 코드 생성량 / 프롬프트 수
2. **명확성 (30%)**: 100 / 메시지 수
3. **생산성 (20%)**: 총 코드 라인 수
4. **품질 (10%)**: 민감정보 + 언어 다양성

**주요 메서드:**
- `analyze_prompt_quality()` - 점수 계산
- `get_best_prompts()` - Top N
- `get_worst_prompts()` - Bottom N
- `get_category_stats()` - 카테고리별
- `get_branch_productivity()` - 브랜치별
- `get_language_distribution()` - 언어별
- `get_time_based_analysis()` - 시간대별
- `export_prompt_library()` - MD 생성

---

### `src/claude_x/prompt_templates.py` (400+ 줄)

**역할:** 재사용 가능한 템플릿 라이브러리

**템플릿 (8개):**
1. `jira_ticket_creation` - JIRA 티켓
2. `technical_research` - 기술 조사
3. `environment_setup_review` - 환경 검토
4. `bug_fix` - 버그 수정
5. `feature_implementation` - 기능 구현
6. `code_review` - 코드 리뷰
7. `refactoring` - 리팩토링
8. `test_creation` - 테스트 작성

**구조:**
```python
@dataclass
class PromptTemplate:
    name: str
    category: str
    description: str
    template: str        # {{변수}} 포함
    variables: List[str]
    example: str
    success_metrics: str
    tags: List[str]
```

---

## 🗄️ 데이터 파일

### 사용자 데이터

```
~/.claude-x/
├── data/
│   └── claude_x.db                # SQLite DB (메인)
│
├── prompt-library/
│   ├── front-prompts.md           # 프로젝트별 분석
│   ├── another-prompts.md
│   └── ...
│
├── prompt-templates.md            # 템플릿 라이브러리
└── my-best-prompts.md             # 개인 베스트 모음
```

### 입력 데이터 (Claude Code)

```
~/.claude/projects/
├── {project1}/
│   ├── sessions-index.json        # 세션 메타데이터
│   └── sessions/
│       ├── abc123.jsonl           # 세션 내용
│       ├── def456.jsonl
│       └── ...
│
├── {project2}/
│   └── ...
```

---

## 📄 문서 파일

### `README.md` (450+ 줄)
- 프로젝트 소개
- 설치 방법
- 모든 명령어 상세 설명
- 아키텍처 개요
- 문제 해결

### `QUICKSTART.md` (100+ 줄)
- 5분 빠른 시작
- 필수 명령어만
- 간단한 예시

### `EXAMPLES.md` (300+ 줄)
- 시나리오별 사용 예시
- 워크플로우
- 고급 활용법

### `ARCHITECTURE.md` (400+ 줄)
- 시스템 아키텍처
- 모듈별 상세 설명
- 데이터베이스 설계
- 성능 최적화

### `CHANGELOG.md` (200+ 줄)
- 버전별 변경 이력
- 릴리즈 노트

### `PROJECT_STRUCTURE.md` (이 파일)
- 파일 구조
- 모듈 설명

---

## 🔧 설정 파일

### `pyproject.toml`

```toml
[project]
name = "claude-x"
version = "0.1.0"
description = "Second Brain and Command Center for Claude Code"
requires-python = ">=3.13"
dependencies = [
    "rich>=14.2.0",
    "typer>=0.21.1",
    "click>=8.1",
    "watchdog>=6.0.0",
    "pydantic>=2.12.5",
]

[project.scripts]
cx = "claude_x.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## 📊 코드 통계

- **총 라인 수**: ~2,500 줄
- **Python 파일**: 9개
- **문서 파일**: 6개
- **명령어**: 9개
- **템플릿**: 8개

### 모듈별 라인 수

| 모듈 | 라인 수 | 비고 |
|------|---------|------|
| cli.py | 550+ | CLI 인터페이스 |
| analytics.py | 350+ | 분석 엔진 |
| storage.py | 440+ | DB 관리 |
| prompt_templates.py | 400+ | 템플릿 |
| session_parser.py | 200+ | JSONL 파서 |
| indexer.py | 150+ | 인덱스 파서 |
| models.py | 100+ | 데이터 모델 |
| security.py | 90+ | 보안 검사 |
| extractor.py | 80+ | 코드 추출 |
| __init__.py | 10 | 패키지 초기화 |

---

## 🎯 핵심 파일

새 작업자가 먼저 봐야 할 파일:

1. **`README.md`** - 전체 개요
2. **`QUICKSTART.md`** - 빠른 시작
3. **`cli.py`** - 명령어 구조
4. **`storage.py`** - 데이터 처리
5. **`ARCHITECTURE.md`** - 아키텍처

---

**Last Updated:** 2026-01-20
