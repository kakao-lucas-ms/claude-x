# Architecture Documentation

Claude-X의 아키텍처 설계 문서입니다.

## 📐 시스템 개요

Claude-X는 Claude Code의 세션 데이터를 수집, 저장, 분석하는 CLI 도구입니다.

### 핵심 설계 원칙

1. **단순성**: 복잡한 설정 없이 바로 사용 가능
2. **성능**: SQLite FTS5를 활용한 빠른 검색
3. **확장성**: 모듈형 구조로 새 기능 추가 용이
4. **안정성**: Pydantic으로 타입 안전성 보장

---

## 🏗️ 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Interface (Typer)                   │
│  ┌────────┬────────┬────────┬────────┬─────────┬──────────┐│
│  │ import │ search │  list  │  show  │  report │ prompts  ││
│  └────────┴────────┴────────┴────────┴─────────┴──────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │   Indexer    │  │   Analytics  │  │  TemplateLibrary │ │
│  │  (sessions-  │  │  (분석 엔진)  │  │  (템플릿 관리)    │ │
│  │  index.json) │  │              │  │                  │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │SessionParser │  │  Extractor   │  │    Security      │ │
│  │  (JSONL)     │  │  (코드 추출)  │  │  (민감정보 검출)  │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data Access Layer                          │
│                     Storage (SQLite)                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Projects  │  Sessions  │  Messages  │  Code Snippets  ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │              FTS5 Full-Text Search Index                ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Sources                            │
│        ~/.claude/projects/{project}/sessions/*.jsonl         │
│        ~/.claude/projects/{project}/sessions-index.json      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 모듈 설명

### 1. CLI Interface (cli.py)

**역할:** 사용자 명령어 처리 및 출력

**의존성:**
- Typer: 명령어 라우팅
- Rich: 예쁜 터미널 출력

**주요 함수:**
```python
@app.command()
def import_sessions(project: Optional[str] = None):
    """세션 데이터 가져오기"""

@app.command()
def search(query: str, lang: Optional[str] = None):
    """코드 검색"""

@app.command()
def prompts(best_only: bool = False):
    """프롬프트 분석"""
```

---

### 2. Indexer (indexer.py)

**역할:** `sessions-index.json` 파일 파싱

**핵심 로직:**
```python
def find_all_project_dirs() -> List[Path]:
    """모든 프로젝트 디렉토리 검색"""
    base_dir = Path.home() / ".claude" / "projects"
    return [d for d in base_dir.iterdir() if d.is_dir()]

def parse_index_file(index_path: Path) -> SessionIndex:
    """sessions-index.json 파싱"""
    with open(index_path) as f:
        data = json.load(f)
    return SessionIndex(**data)

def decode_project_path(encoded: str) -> str:
    """URL 인코딩된 경로 디코딩"""
    return urllib.parse.unquote(encoded)
```

**데이터 모델:**
```python
class SessionIndexEntry(BaseModel):
    session_id: str
    full_path: str
    file_mtime: int
    first_prompt: Optional[str]
    message_count: Optional[int]
    created: str
    modified: str
    git_branch: Optional[str]
    is_sidechain: bool
```

---

### 3. SessionParser (session_parser.py)

**역할:** JSONL 세션 파일 파싱

**핵심 로직:**
```python
def parse_messages(self, session_id: str) -> Iterator[Message]:
    """JSONL 파일의 메시지 파싱"""
    with open(self.session_path, 'r') as f:
        for line in f:
            data = json.loads(line)

            # SessionStart 이벤트
            if data.get("name") == "SessionStart":
                yield from self._parse_session_start(data)

            # MessageEvent
            elif data.get("type") == "MessageEvent":
                yield from self._parse_message_event(data)
```

**타임스탬프 자동 감지:**
```python
def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
    """Unix milliseconds 또는 ISO 8601 형식 자동 감지"""
    # ISO 8601 시도
    if isinstance(timestamp_str, str) and "T" in timestamp_str:
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

    # Unix milliseconds 시도
    try:
        return datetime.fromtimestamp(int(timestamp_str) / 1000.0)
    except:
        return None
```

---

### 4. Extractor (extractor.py)

**역할:** 마크다운 코드 블록 추출

**정규식 패턴:**
```python
CODE_BLOCK_PATTERN = re.compile(
    r"```(\w+)?\n(.*?)```",
    re.DOTALL | re.MULTILINE
)
```

**중복 제거:**
```python
def _calculate_hash(self, code: str) -> str:
    """SHA-256 해시 계산 (세션 내 중복 방지)"""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]
```

**추출 로직:**
```python
def extract_code_blocks(
    self,
    message_id: int,
    session_id: str,
    content: str
) -> Iterator[CodeSnippet]:
    """코드 블록 추출"""
    for match in self.pattern.finditer(content):
        language = match.group(1) or "text"
        code = match.group(2).strip()

        yield CodeSnippet(
            message_id=message_id,
            session_id=session_id,
            language=language,
            code=code,
            hash=self._calculate_hash(code),
            line_count=len(code.splitlines())
        )
```

---

### 5. Security (security.py)

**역할:** 민감 정보 패턴 검출

**검출 패턴 (14개):**
```python
SENSITIVE_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[\w-]+', "API Key"),
    (r'sk-[a-zA-Z0-9]{48}', "OpenAI API Key"),
    (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token"),
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
    (r'mongodb(\+srv)?://[^:]+:[^@]+@', "MongoDB Connection String"),
    # ... 9 more patterns
]
```

**검출 로직:**
```python
def has_sensitive_data(self, code: str) -> bool:
    """민감 정보 포함 여부 확인"""
    return len(self.scan_code(code)) > 0
```

---

### 6. Storage (storage.py)

**역할:** SQLite 데이터베이스 관리

**최적화 설정:**
```python
@contextmanager
def _get_connection(self):
    conn = sqlite3.connect(str(self.db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")    # 동시성 향상
    conn.execute("PRAGMA foreign_keys=ON")     # 참조 무결성
```

**FTS5 트리거:**
```python
CREATE TRIGGER code_fts_insert AFTER INSERT ON code_snippets
BEGIN
    INSERT INTO code_fts(rowid, code, language)
    VALUES (new.id, new.code, new.language);
END;
```

**검색 최적화:**
```python
def search_code(self, query: str, language: Optional[str] = None):
    """FTS5 full-text search"""
    sql = """
        SELECT cs.*, s.first_prompt, p.name
        FROM code_fts
        JOIN code_snippets cs ON code_fts.rowid = cs.id
        JOIN sessions s ON cs.session_id = s.session_id
        JOIN projects p ON s.project_id = p.id
        WHERE code_fts MATCH ?
        ORDER BY rank
    """
```

---

### 7. Analytics (analytics.py)

**역할:** 프롬프트 품질 분석

**점수 계산:**
```python
def analyze_prompt_quality(self, project_name: str):
    """4가지 지표로 프롬프트 품질 평가"""

    # 1. 효율성: 코드 생성량 / 프롬프트 수
    efficiency_score = code_count / user_prompt_count

    # 2. 명확성: 100 / 메시지 수
    clarity_score = 100.0 / message_count

    # 3. 생산성: 총 라인 수 (정규화)
    productivity_score = total_lines

    # 4. 품질: 민감정보 없음 + 언어 다양성
    quality_score = calculate_quality(sensitive_count, language_diversity)

    # 종합 점수 (가중 평균)
    composite_score = (
        efficiency_score * 0.4 +
        clarity_score * 0.3 +
        normalized_productivity * 0.2 +
        quality_score * 0.1
    )
```

---

### 8. PromptTemplates (prompt_templates.py)

**역할:** 재사용 가능한 템플릿 관리

**템플릿 구조:**
```python
@dataclass
class PromptTemplate:
    name: str                    # 템플릿 이름
    category: str                # 카테고리
    description: str             # 설명
    template: str                # {{변수}} 포함 템플릿
    variables: List[str]         # 필요한 변수 목록
    example: str                 # 실제 사용 예시
    success_metrics: str         # 성공 지표
    tags: List[str]              # 검색용 태그
```

---

## 🔄 데이터 흐름

### Import 프로세스

```
1. Indexer.find_all_project_dirs()
   ↓ ~/.claude/projects/ 스캔

2. Indexer.parse_index_file()
   ↓ sessions-index.json 파싱

3. Storage.insert_project()
   ↓ 프로젝트 저장

4. SessionParser.parse_messages()
   ↓ JSONL 파일 파싱

5. Storage.insert_session()
   Storage.insert_message()
   ↓ 세션, 메시지 저장

6. Extractor.extract_code_blocks()
   ↓ 코드 블록 추출

7. Security.has_sensitive_data()
   ↓ 민감 정보 검출

8. Storage.insert_code_snippet()
   ↓ 코드 저장 + FTS5 인덱싱
```

### Search 프로세스

```
1. CLI.search(query, lang)
   ↓

2. Storage.search_code(query, lang)
   ↓

3. SQLite FTS5 MATCH query
   ↓

4. JOIN projects, sessions, code_snippets
   ↓

5. ORDER BY rank
   ↓

6. Rich.print() 결과 출력
```

---

## 💾 데이터베이스 설계

### ERD

```
┌──────────────┐
│   projects   │
├──────────────┤
│ id (PK)      │
│ path         │◄──┐
│ name         │   │
│ session_count│   │
└──────────────┘   │
                   │
       ┌───────────┘
       │
┌──────────────┐
│   sessions   │
├──────────────┤
│ id (PK)      │
│ session_id   │◄──┐
│ project_id(FK)│  │
│ first_prompt │   │
│ git_branch   │   │
│ message_count│   │
└──────────────┘   │
                   │
       ┌───────────┤
       │           │
┌──────────────┐   │
│   messages   │   │
├──────────────┤   │
│ id (PK)      │   │
│ session_id(FK)│  │
│ type         │   │
│ content      │   │
│ has_code     │   │
└──────────────┘   │
       │           │
       └───────────┘
       │
┌──────────────────┐
│  code_snippets   │
├──────────────────┤
│ id (PK)          │
│ message_id (FK)  │
│ session_id (FK)  │
│ language         │
│ code             │
│ hash             │
│ has_sensitive    │
└──────────────────┘
       │
       ↓
┌──────────────────┐
│    code_fts      │
│  (FTS5 Virtual)  │
├──────────────────┤
│ code             │
│ language         │
└──────────────────┘
```

### 인덱스 전략

```sql
-- 프로젝트 검색
CREATE INDEX idx_sessions_project ON sessions(project_id);

-- 브랜치 필터링
CREATE INDEX idx_sessions_branch ON sessions(git_branch);

-- 언어 필터링
CREATE INDEX idx_snippets_language ON code_snippets(language);

-- 세션별 코드 조회
CREATE INDEX idx_snippets_session ON code_snippets(session_id);

-- FTS5 full-text search
CREATE VIRTUAL TABLE code_fts USING fts5(...);
```

---

## 🔐 보안 고려사항

### 1. 민감 정보 보호

- 코드 저장 시 자동 검출
- `has_sensitive` 플래그로 표시
- 분석 리포트에 경고 포함

### 2. 데이터 격리

- 사용자별 `~/.claude-x/` 디렉토리
- 프로젝트별 독립적 분석

### 3. SQL Injection 방지

- Parameterized queries 사용
- ORM 없이 raw SQL이지만 모든 입력 바인딩

---

## 🚀 성능 최적화

### 1. Database

- **WAL 모드**: 동시 읽기/쓰기 가능
- **FTS5**: 빠른 full-text search
- **인덱스**: 자주 사용하는 쿼리 최적화

### 2. Import

- **스트리밍 파싱**: 메모리 효율적
- **배치 커밋**: 트랜잭션 최소화
- **중복 제거**: 해시 기반 (세션 내)

### 3. Search

- **FTS5 rank**: 관련도 순 정렬
- **LIMIT**: 결과 수 제한
- **인덱스 활용**: JOIN 최적화

---

## 🔧 확장 가능성

### 새 명령어 추가

```python
# cli.py
@app.command()
def new_command(param: str):
    """새 명령어"""
    storage = get_storage()
    # 구현
```

### 새 분석 기능

```python
# analytics.py
def new_analysis(self, project: str):
    """새 분석 기능"""
    with self.storage._get_connection() as conn:
        # SQL 쿼리
        return results
```

### 새 템플릿

```python
# prompt_templates.py
PromptTemplate(
    name="new_template",
    category="카테고리",
    template="{{variable}} content",
    # ...
)
```

---

## 📈 향후 개선 방향

1. **웹 UI**: 브라우저에서 시각화
2. **AI 분석**: LLM으로 프롬프트 개선 제안
3. **실시간 모니터링**: 세션 진행 중 분석
4. **팀 공유**: 중앙 서버로 데이터 공유
5. **플러그인 시스템**: 커스텀 분석 추가

---

**Last Updated:** 2026-01-20
