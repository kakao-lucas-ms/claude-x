# claude-x v0.5.0 구현 로드맵

> **목표**: 시나리오 B 완성 - Claude가 분석 후 자동으로 개선된 행동 실행

**타겟 완료일**: 2026-02-15

---

## 📋 목차

1. [배경](#배경)
2. [핵심 목표](#핵심-목표)
3. [상세 기능](#상세-기능)
4. [구현 계획](#구현-계획)
5. [마일스톤](#마일스톤)

---

## 배경

### v0.4.x 현황

**v0.4.0 완료:**
- ✅ 프롬프트 분석 (점수, 문제점)
- ✅ 다국어 지원 (ko/en)
- ✅ 확장 시스템 탐지 (SuperClaude, oh-my-opencode)
- ✅ MCP 통합

**v0.4.1 완료:**
- ✅ Intent 감지 (find, fix, create, explain, refactor, test)
- ✅ improved_prompt 생성
- ✅ recommended_actions 생성

### 현재 한계 (시나리오 A)

```
User: "지금 다음 로드맵이 뭔지 확인해줘"

Claude: (MCP 호출 → 분석 결과)
        "점수가 낮네요. 개선된 프롬프트는..."
        (끝 - 실제 행동 없음)
```

### 목표 (시나리오 B)

```
User: "지금 다음 로드맵이 뭔지 확인해줘"

Claude: (MCP 호출 → 분석 + 액션 힌트)
        (recommended_actions 실행)
        → Glob: docs/**/ROADMAP*.md
        → Read: ROADMAP_v0.5.0.md

        "로드맵 확인했어요. 내용은..."
```

---

## 핵심 목표

### Goal 1: 자동 액션 실행 (Auto-Execute)

Claude가 `recommended_actions`를 보고 **스스로 실행**하도록 유도

**구현 방식:**
- MCP 응답에 `auto_execute_hint` 추가
- Claude가 해석하기 쉬운 구조화된 액션 제안
- `should_auto_execute` 플래그로 제어

### Goal 2: 대화형 정보 수집 (Interactive)

부족한 정보가 있으면 Claude가 **질문**하도록 유도

**예시:**
```
User: "이 버그 수정해줘"

Claude: (분석 결과: 에러 메시지 없음)
        "어떤 에러가 발생했나요? 에러 메시지를 알려주세요."
```

### Goal 3: 컨텍스트 기반 프롬프트 재작성 (Smart Rewrite)

현재 프로젝트 구조를 파악해서 **실제 파일명**으로 개선

**현재:**
```
improved_prompt: "@docs/ 또는 관련 폴더에서 '로드맵' 관련 파일을 찾아서..."
```

**개선:**
```
improved_prompt: "@docs/ROADMAP_v0.5.0.md 여기서 다음 버전 계획을 확인해줘"
```

### Goal 4: 프롬프트 공유 (Community)

베스트 프롬프트를 HTML/Gist로 내보내기

---

## 상세 기능

### Feature 1: Auto-Execute Hints

#### MCP 응답 확장

```python
{
    "intent": "find",
    "improved_prompt": "...",
    "recommended_actions": [...],

    # NEW in v0.5.0
    "auto_execute": {
        "enabled": True,
        "reason": "사용자가 정보 조회를 요청했고, 파일 검색으로 해결 가능",
        "actions": [
            {
                "tool": "Glob",
                "params": {"pattern": "docs/**/ROADMAP*.md"},
                "priority": 1,
                "description": "로드맵 파일 검색"
            },
            {
                "tool": "Read",
                "params": {"file": "$GLOB_RESULT[0]"},  # 이전 액션 결과 참조
                "priority": 2,
                "description": "파일 내용 읽기"
            }
        ],
        "fallback": "파일을 찾지 못하면 사용자에게 경로를 물어보세요"
    }
}
```

#### Claude 행동 유도

```
llm_summary에 추가:

🤖 권장 행동:
1. Glob으로 "docs/**/ROADMAP*.md" 검색
2. 결과 파일 읽기
3. 사용자에게 내용 요약 전달

이 작업을 자동으로 수행해도 될까요? (Y로 가정하고 진행)
```

---

### Feature 2: Interactive Mode

#### 부족 정보 감지

```python
def detect_missing_info(prompt: str, intent: str) -> list[dict]:
    """필수 정보 중 누락된 것 감지"""
    missing = []

    if intent == "fix":
        if not has_error_message(prompt):
            missing.append({
                "type": "error_message",
                "question_ko": "어떤 에러가 발생했나요?",
                "question_en": "What error are you seeing?",
                "example": "TypeError: Cannot read property 'x' of undefined"
            })
        if not has_file_path(prompt):
            missing.append({
                "type": "file_path",
                "question_ko": "어떤 파일에서 발생했나요?",
                "question_en": "Which file is this happening in?",
                "example": "src/components/Button.tsx"
            })

    elif intent == "create":
        if not has_location(prompt):
            missing.append({
                "type": "location",
                "question_ko": "어디에 생성할까요?",
                "question_en": "Where should I create it?",
                "example": "src/components/"
            })

    return missing
```

#### MCP 응답에 질문 포함

```python
{
    "missing_info": [
        {
            "type": "error_message",
            "question": "어떤 에러가 발생했나요?",
            "required": True,
            "example": "TypeError: ..."
        }
    ],
    "can_proceed_without": False,
    "llm_instruction": "위 정보가 없으면 먼저 사용자에게 물어보세요"
}
```

---

### Feature 3: Smart Rewrite

#### 프로젝트 컨텍스트 활용

```python
def smart_rewrite(prompt: str, intent: str, project_context: dict) -> str:
    """프로젝트 구조를 활용한 스마트 재작성"""
    keywords = extract_keywords(prompt)

    # 프로젝트에서 관련 파일 찾기
    matching_files = find_matching_files(keywords, project_context)

    if matching_files:
        # 실제 파일명으로 재작성
        file_path = matching_files[0]
        return f"@{file_path} 여기서 {summarize_task(prompt)}"

    return generate_improved_prompt(prompt, intent, lang)
```

#### 프로젝트 컨텍스트 수집

```python
def get_project_context() -> dict:
    """현재 프로젝트의 구조 파악"""
    return {
        "docs_files": glob("docs/**/*.md"),
        "src_files": glob("src/**/*.{py,ts,tsx,js}"),
        "test_files": glob("tests/**/*"),
        "config_files": ["pyproject.toml", "package.json", "tsconfig.json"],
        "readme": read_if_exists("README.md"),
    }
```

---

### Feature 4: Export & Share

#### HTML Export

```bash
cx export --format html --output best-prompts.html
```

**생성 파일:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>My Best Prompts - Claude-X</title>
    <style>/* 스타일링 */</style>
</head>
<body>
    <h1>🏆 My Best Prompts</h1>

    <div class="prompt-card">
        <div class="score">9.5/10</div>
        <div class="category">Bug Fix</div>
        <pre class="prompt">@src/api/auth.ts 에서 로그인 실패 시
TypeError: Cannot read property 'token' 에러 발생

현재 상황:
- 로그인 API 호출 후 응답 처리 과정
- user 객체가 undefined일 때 발생

기대 동작:
- 에러 핸들링 추가
- 사용자에게 친절한 에러 메시지</pre>
        <div class="stats">
            <span>메시지 3개</span>
            <span>코드 블록 5개</span>
        </div>
    </div>

    <!-- 더 많은 프롬프트들 -->
</body>
</html>
```

#### Gist Export

```bash
cx export --format gist --public
```

**결과:**
```
✅ Gist 생성 완료!
URL: https://gist.github.com/user/abc123

공유 가능한 링크:
https://gist.github.com/user/abc123
```

---

## 구현 계획

### Phase 1: Auto-Execute (Week 1-2)

**파일 변경:**
- `src/claude_x/prompt_coach.py` - auto_execute 로직
- `src/claude_x/mcp_server.py` - 응답 확장

**구현 항목:**
1. `generate_auto_execute_hint()` 함수
2. Intent별 액션 체인 정의
3. llm_summary 강화

### Phase 2: Interactive Mode (Week 3)

**파일 변경:**
- `src/claude_x/prompt_coach.py` - missing_info 감지
- `src/claude_x/mcp_server.py` - 질문 포함

**구현 항목:**
1. `detect_missing_info()` 함수
2. Intent별 필수 정보 정의
3. 질문 생성 로직

### Phase 3: Smart Rewrite (Week 4)

**파일 변경:**
- `src/claude_x/context.py` (NEW) - 프로젝트 컨텍스트
- `src/claude_x/prompt_coach.py` - smart_rewrite

**구현 항목:**
1. `get_project_context()` 함수
2. `find_matching_files()` 함수
3. `smart_rewrite()` 함수

### Phase 4: Export & Share (Week 5)

**파일 변경:**
- `src/claude_x/export.py` (NEW) - 내보내기
- `src/claude_x/cli.py` - export 명령어

**구현 항목:**
1. HTML 템플릿 및 생성
2. Gist API 연동
3. CLI 명령어

---

## 마일스톤

### Milestone 1: Auto-Execute MVP
- [ ] auto_execute 힌트 생성
- [ ] llm_summary에 행동 지침 추가
- [ ] 실제 테스트 (Claude가 액션 실행하는지)

**완료 조건:** Claude가 "로드맵 확인해줘"에 자동으로 파일 검색 → 읽기 수행

### Milestone 2: Interactive MVP
- [ ] missing_info 감지
- [ ] 질문 생성
- [ ] 테스트

**완료 조건:** "버그 수정해줘"에 Claude가 "어떤 에러인가요?" 질문

### Milestone 3: Smart Rewrite MVP
- [ ] 프로젝트 컨텍스트 수집
- [ ] 실제 파일명으로 재작성
- [ ] 테스트

**완료 조건:** improved_prompt에 실제 파일 경로 포함

### Milestone 4: Export MVP
- [ ] HTML export
- [ ] Gist export
- [ ] CLI 명령어

**완료 조건:** `cx export --format html` 작동

---

## 성공 지표

### 정량적
- [ ] Auto-execute 성공률 > 80%
- [ ] Interactive 질문 적절성 > 90%
- [ ] Smart rewrite 파일 매칭률 > 70%

### 정성적
- [ ] "시나리오 B" 자연스럽게 작동
- [ ] 사용자가 추가 입력 없이 원하는 결과
- [ ] Export 파일 품질 만족

---

## 리스크 및 완화

### 리스크 1: Claude가 auto_execute를 무시
**완화:** llm_summary 포맷 실험, 명시적 지시문 추가

### 리스크 2: 프로젝트 컨텍스트 수집 느림
**완화:** 캐싱, 점진적 로딩, 필수 파일만

### 리스크 3: Gist API 인증
**완화:** gh CLI 활용, 토큰 설정 가이드

---

## 다음 버전 (v0.6.0)

- 프롬프트 분석 대시보드 (웹 UI)
- 팀 공유 기능
- 프롬프트 A/B 테스트
- AI 기반 자동 개선 (선택적 API 키)

---

**작성일**: 2026-01-24
**담당자**: lucas.ms
**상태**: Draft
