# 사용 예시 가이드

실제 사용 시나리오별 예시를 제공합니다.

## 🎯 시나리오별 사용법

### 1. 새 프로젝트 시작 시

**상황:** Claude-X를 처음 설치하고 데이터를 수집하고 싶을 때

```bash
# 1. 초기화
cx init

# 2. 전체 데이터 import
cx import

# 3. 전체 통계 확인
cx stats
```

---

### 2. 특정 프로젝트만 분석

**상황:** brunch-front 프로젝트만 집중 분석하고 싶을 때

```bash
# 1. brunch 관련 세션만 import
cx import --project "brunch"

# 2. brunch 프로젝트 통계
cx stats --project "front"

# 3. brunch 프로젝트 세션 목록
cx list --project "brunch" --limit 20

# 4. brunch 프로젝트 리포트 생성
cx report --project front --output ~/reports/brunch-report.json
```

---

### 3. 코드 스니펫 검색

**상황:** 이전에 작성했던 useState 관련 코드를 찾고 싶을 때

```bash
# 1. TypeScript 파일에서 useState 검색
cx search "useState" --lang typescript

# 2. 특정 프로젝트에서만 검색
cx search "useState" --lang typescript --project "brunch"

# 3. API 관련 코드 찾기
cx search "fetch" --lang typescript --limit 20

# 4. SQL 쿼리 찾기
cx search "CREATE TABLE" --lang sql
```

---

### 4. 프롬프트 개선하기

**상황:** 프롬프트 작성 실력을 향상시키고 싶을 때

```bash
# 1. 내가 잘 쓴 프롬프트 분석
cx prompts --best-only --limit 10

# 2. 개선이 필요한 프롬프트 확인
cx prompts --worst-only --limit 5

# 3. 프롬프트 라이브러리 생성
cx prompts --export

# 4. 생성된 파일 확인
cat ~/.claude-x/prompt-library/front-prompts.md
```

---

### 5. 프롬프트 템플릿 활용

**상황:** 지라 티켓을 만들어야 하는데 어떻게 프롬프트를 작성할지 모를 때

```bash
# 1. 지라 관련 템플릿 검색
cx templates --search jira

# 2. 템플릿 상세 보기
cx templates --show jira_ticket_creation

# 3. 모든 템플릿 마크다운으로 저장
cx templates --export --output ~/team/prompt-guide.md
```

---

### 6. 세션 상세 조회

**상황:** 특정 세션에서 어떤 코드를 생성했는지 확인하고 싶을 때

```bash
# 1. 최근 세션 목록 확인
cx list --limit 5

# 2. 세션 전체 정보 보기
cx show a7472f17

# 3. 코드만 보기
cx show a7472f17 --code
```

---

### 7. 정기 리포트 생성

**상황:** 주간/월간 프롬프트 사용 리포트를 만들고 싶을 때

```bash
# 주간 리포트 생성
DATE=$(date +%Y%m%d)
REPORT_DIR=~/reports

# 1. JSON 리포트 생성
cx report --project front --output $REPORT_DIR/weekly-$DATE.json

# 2. 프롬프트 분석
cx prompts --project front --export --output $REPORT_DIR/prompts-$DATE.md

# 3. 통계 저장
cx stats --project front > $REPORT_DIR/stats-$DATE.txt
```

---

### 8. 팀 공유용 문서 생성

**상황:** 팀원들과 좋은 프롬프트 패턴을 공유하고 싶을 때

```bash
# 1. 템플릿 라이브러리 생성
cx templates --export --output ~/team-wiki/prompt-templates.md

# 2. 프로젝트별 베스트 프롬프트
cx prompts --project brunch-front --export

# 3. Wiki에 업로드
cp ~/.claude-x/prompt-library/brunch-front-prompts.md ~/team-wiki/
```

---

## 🔄 워크플로우 예시

### 새 기능 개발 시

```
1. 템플릿 확인 → cx templates --show feature_implementation
2. 템플릿 기반 프롬프트 작성 → Claude에 입력
3. 작업 완료 후 import → cx import
4. 생성된 코드 확인 → cx show <session-id> --code
5. 프롬프트 품질 확인 → cx prompts --best-only
```

### 월간 회고

```
1. 월간 통계 → cx stats --project "my-project"
2. 베스트 프롬프트 → cx prompts --best-only --export
3. 워스트 프롬프트 → cx prompts --worst-only
4. 리포트 생성 → cx report --output monthly-report.json
5. 팀과 공유 → 생성된 파일 공유
```

---

## 💡 고급 활용

### 데이터 백업

```bash
# 데이터베이스 백업
cp ~/.claude-x/data/claude_x.db ~/backups/claude_x-$(date +%Y%m%d).db

# 생성된 리포트 백업
cp -r ~/.claude-x/prompt-library ~/backups/reports-$(date +%Y%m%d)/
```

### JSON 데이터 활용

```bash
# JSON으로 저장
cx report --project front --output report.json

# jq로 파싱
cat report.json | jq '.category_stats'

# Python으로 처리
python -c "import json; print(json.load(open('report.json'))['top_sessions'])"
```

---

**다음 단계:** 실제로 사용해보고 자신만의 워크플로우를 만들어보세요!
