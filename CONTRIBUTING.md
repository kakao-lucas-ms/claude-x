# Contributing to Claude-X

Claude-X에 기여해주셔서 감사합니다! 이 문서는 개발 환경 설정과 기여 가이드라인을 제공합니다.

## 🛠️ 개발 환경 설정

### 필수 요구사항

- **Python 3.13+**
- **uv** (Python package manager)
- **Claude Code** (데이터 소스)
- **Git**

### 초기 설정

```bash
# 1. 저장소 클론
git clone <repository-url> claude-x
cd claude-x

# 2. 가상환경 생성 및 의존성 설치
uv venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 3. 개발 모드로 설치
uv pip install -e .

# 4. 개발 의존성 설치 (향후)
uv pip install -e ".[dev]"
```

### 프로젝트 구조 이해

```
claude-x/
├── src/claude_x/              # 소스 코드
│   ├── cli.py                 # CLI 진입점
│   ├── models.py              # 데이터 모델
│   ├── storage.py             # 데이터베이스
│   ├── analytics.py           # 분석 엔진
│   └── ...
├── tests/                     # 테스트 (계획)
├── docs/                      # 추가 문서 (계획)
└── pyproject.toml             # 프로젝트 설정
```

자세한 내용은 `PROJECT_STRUCTURE.md`를 참고하세요.

## 🧪 테스트

### 수동 테스트

```bash
# 데이터베이스 초기화
cx init

# 테스트 데이터 import
cx import --project "test-project"

# 기능 테스트
cx stats
cx search "test" --lang python
cx list --limit 5
cx show <session-id>
cx prompts --best-only
cx templates
```

### 자동화된 테스트 (향후)

```bash
# Unit tests
pytest tests/

# Coverage
pytest --cov=claude_x tests/
```

## 📝 코드 작성 가이드라인

### 코드 스타일

- **PEP 8** 준수
- **Type hints** 사용 (`from typing import ...`)
- **Pydantic** 모델로 데이터 검증
- **Docstrings** 작성 (Google 스타일 권장)

```python
def example_function(param: str) -> dict:
    """
    Function description.

    Args:
        param: Parameter description.

    Returns:
        Return value description.
    """
    pass
```

### 모듈별 책임

| 모듈 | 책임 |
|------|------|
| `models.py` | Pydantic 데이터 모델만 |
| `indexer.py` | sessions-index.json 파싱만 |
| `session_parser.py` | JSONL 파일 파싱만 |
| `extractor.py` | 코드 블록 추출만 |
| `security.py` | 민감 정보 검출만 |
| `storage.py` | 데이터베이스 작업만 |
| `analytics.py` | 분석 및 통계만 |
| `prompt_templates.py` | 템플릿 정의만 |
| `cli.py` | CLI 인터페이스만 |

**원칙**: 한 모듈은 한 가지 책임만 가집니다.

## 🔧 새 기능 추가하기

### CLI 명령어 추가

1. **storage.py에 데이터 메서드 추가**

```python
def get_new_data(self) -> List[dict]:
    """새 데이터를 가져옵니다."""
    cursor = self.conn.execute("""
        SELECT * FROM table_name
    """)
    return [dict(row) for row in cursor]
```

2. **cli.py에 명령어 추가**

```python
@app.command()
def new_command(
    option: Optional[str] = typer.Option(None, help="옵션 설명")
):
    """새 명령어 설명"""
    db = DatabaseStorage()
    data = db.get_new_data()

    # Rich로 출력
    table = Table(title="결과")
    table.add_column("컬럼1")
    console.print(table)
```

3. **README.md 업데이트**

`### cx new-command` 섹션 추가

### 분석 지표 추가

1. **analytics.py에 분석 메서드 추가**

```python
def get_new_metric(self, project_name: str) -> dict:
    """새 분석 지표를 계산합니다."""
    cursor = self.conn.execute("""
        SELECT ... FROM sessions
        WHERE project_name LIKE ?
    """, (f"%{project_name}%",))
    return cursor.fetchone()
```

2. **report 명령어에 통합**

### 템플릿 추가

`prompt_templates.py`의 `TEMPLATES` 리스트에 추가:

```python
PromptTemplate(
    name="new_template",
    category="category",
    description="설명",
    template="템플릿 내용 {{variable}}",
    variables=["variable"],
    example="예시",
    success_metrics="성공 지표",
    tags=["tag1", "tag2"]
)
```

## 🗄️ 데이터베이스 스키마 변경

### 1. 새 테이블 추가

`storage.py`의 `_init_db()` 메서드 수정:

```python
def _init_db(self):
    # 기존 테이블...

    # 새 테이블
    self.conn.execute("""
        CREATE TABLE IF NOT EXISTS new_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field1 TEXT NOT NULL,
            field2 INTEGER,
            FOREIGN KEY (field2) REFERENCES other_table(id)
        )
    """)
```

### 2. 인덱스 추가

```python
self.conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_new_table_field1
    ON new_table(field1)
""")
```

### 3. FTS5 테이블 추가

```python
# 가상 테이블
self.conn.execute("""
    CREATE VIRTUAL TABLE new_fts USING fts5(
        content,
        content=new_table,
        content_rowid=id
    )
""")

# 트리거 추가
self.conn.execute("""
    CREATE TRIGGER new_fts_insert AFTER INSERT ON new_table BEGIN
        INSERT INTO new_fts(rowid, content)
        VALUES (new.id, new.content);
    END
""")
```

## 🐛 버그 수정

### 버그 리포트

이슈 제출 시 포함할 정보:

1. **재현 단계**
2. **예상 동작**
3. **실제 동작**
4. **환경 정보** (OS, Python 버전, uv 버전)
5. **에러 로그**

### 디버깅 팁

```python
# 로깅 활성화 (향후)
import logging
logging.basicConfig(level=logging.DEBUG)

# SQL 쿼리 확인
cursor.execute("SELECT * FROM sessions")
print(cursor.fetchall())

# Rich console로 디버깅
from rich.console import Console
console = Console()
console.print(data, style="bold red")
```

## 📊 성능 최적화

### SQL 최적화

1. **인덱스 사용 확인**

```sql
EXPLAIN QUERY PLAN
SELECT * FROM sessions WHERE project_name = 'test';
```

2. **배치 처리**

```python
# 나쁜 예
for item in items:
    db.insert_one(item)

# 좋은 예
db.insert_many(items)
```

3. **트랜잭션 활용**

```python
with self.conn:  # 자동 커밋
    self.conn.execute(...)
    self.conn.execute(...)
```

## 📚 문서화

### 문서 업데이트가 필요한 경우

- 새 명령어 추가 → `README.md`, `EXAMPLES.md`
- 새 모듈 추가 → `ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`
- 기능 변경 → `CHANGELOG.md`
- 설치/설정 변경 → `QUICKSTART.md`

### 문서 작성 원칙

- **한글** 사용 (주 사용자가 한국어 사용자)
- **코드 예시** 포함
- **실제 출력** 보여주기
- **사용 시나리오** 기반 설명

## 🔄 릴리즈 프로세스

### 버전 번호 규칙

**Semantic Versioning**: `Major.Minor.Patch`

- **Major**: 호환성 없는 변경
- **Minor**: 하위 호환 기능 추가
- **Patch**: 하위 호환 버그 수정

### 릴리즈 체크리스트

- [ ] 모든 테스트 통과
- [ ] `CHANGELOG.md` 업데이트
- [ ] `pyproject.toml` 버전 업데이트
- [ ] 문서 업데이트
- [ ] Git 태그 생성

```bash
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

## 🤝 Pull Request 가이드라인

### PR 제출 전

1. ✅ 최신 main 브랜치와 동기화
2. ✅ 코드 스타일 확인
3. ✅ 테스트 실행
4. ✅ 문서 업데이트
5. ✅ CHANGELOG.md 업데이트

### PR 템플릿

```markdown
## 변경 내용
- 무엇을 변경했는지 간단히 설명

## 변경 이유
- 왜 이 변경이 필요한지

## 테스트
- 어떻게 테스트했는지

## 체크리스트
- [ ] 테스트 추가/업데이트
- [ ] 문서 업데이트
- [ ] CHANGELOG.md 업데이트
```

## 🎯 개발 로드맵

현재 계획 중인 기능:

- [ ] **테스트 Suite** (pytest 기반)
- [ ] **CI/CD** (GitHub Actions)
- [ ] **웹 UI** (대시보드)
- [ ] **실시간 모니터링**
- [ ] **AI 기반 프롬프트 개선 제안**
- [ ] **팀 공유 기능**
- [ ] **플러그인 시스템**

기여하고 싶은 기능이 있다면 이슈로 제안해주세요!

## 📞 도움이 필요하신가요?

- **이슈**: 버그 리포트 및 기능 제안
- **토론**: 아이디어 공유 및 질문
- **문서**: `docs/` 디렉토리 참고

## 📄 라이선스

이 프로젝트에 기여하면 프로젝트 라이선스 조건에 동의하는 것으로 간주됩니다.

---

**Happy Coding!** 🚀
