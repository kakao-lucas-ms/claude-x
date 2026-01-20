# Quick Start Guide

5분 안에 Claude-X를 시작해보세요!

## ⚡ 빠른 설치

```bash
# 1. 저장소 클론
cd ~/workspace
git clone <repository-url> claude-x
cd claude-x

# 2. 패키지 설치
uv pip install -e .

# 3. 초기화
cx init
```

## 🚀 첫 번째 명령어

```bash
# 모든 세션 가져오기
cx import

# 통계 확인
cx stats
```

**출력 예시:**
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

## 📝 기본 사용법

### 1. 코드 검색

```bash
# TypeScript에서 useState 검색
cx search "useState" --lang typescript

# SQL 쿼리 찾기
cx search "CREATE TABLE" --lang sql

# 특정 프로젝트에서만 검색
cx search "api" --project "brunch"
```

### 2. 세션 조회

```bash
# 최근 세션 목록
cx list --limit 10

# 특정 세션 상세
cx show a7472f17

# 코드만 보기
cx show a7472f17 --code
```

### 3. 프롬프트 분석

```bash
# 베스트 프롬프트 확인
cx prompts --best-only --limit 5

# 워스트 프롬프트 (개선점 파악)
cx prompts --worst-only --limit 5

# 분석 리포트 생성
cx prompts --export
```

### 4. 템플릿 사용

```bash
# 템플릿 목록
cx templates

# JIRA 티켓 템플릿 보기
cx templates --show jira_ticket_creation

# 모든 템플릿 저장
cx templates --export
```

## 💡 유용한 팁

### 프로젝트별 작업

```bash
# 특정 프로젝트만 import
cx import --project "my-project"

# 프로젝트 통계
cx stats --project "my-project"

# 프로젝트 리포트
cx report --project "my-project"
```

### 정기 리포트

```bash
# 주간 리포트 생성
cx report --project front --output ~/reports/weekly.json

# 프롬프트 라이브러리 업데이트
cx prompts --export
```

### 팀 공유

```bash
# 템플릿 공유
cx templates --export --output ~/team/templates.md

# 베스트 프롬프트 공유
cx prompts --best-only --export --output ~/team/best-prompts.md
```

## 📂 생성되는 파일

```
~/.claude-x/
├── data/
│   └── claude_x.db                    # SQLite 데이터베이스
├── prompt-library/
│   └── front-prompts.md               # 프롬프트 분석
├── prompt-templates.md                # 템플릿 라이브러리
└── my-best-prompts.md                 # 나의 베스트 프롬프트
```

## 🎯 다음 단계

1. 전체 기능: `README.md` 참고
2. 사용 예시: `EXAMPLES.md` 참고
3. 아키텍처: `ARCHITECTURE.md` 참고

## ❓ 문제 해결

### 세션이 import 되지 않음

```bash
# Claude Code 설치 확인
ls ~/.claude/projects/

# 특정 프로젝트만 시도
cx import --project "프로젝트명"
```

### 검색 결과 없음

```bash
# DB 재초기화
rm ~/.claude-x/data/claude_x.db
cx init
cx import
```

## 📞 도움말

```bash
# 명령어 도움말
cx --help
cx import --help
cx search --help
```

---

**Ready to go?** 이제 `cx import`로 시작하세요!
