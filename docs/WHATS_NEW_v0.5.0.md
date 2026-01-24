# What's New in Claude-X v0.5.0

> v0.3.x에서 v0.5.0까지의 주요 개선 사항과 새로운 기능을 소개합니다.

## 목차

- [요약: v0.3.x vs v0.5.0](#요약-v03x-vs-v050)
- [v0.4.0: 프롬프트 코칭 엔진](#v040-프롬프트-코칭-엔진)
- [v0.5.0: 자동 실행 힌트 시스템](#v050-자동-실행-힌트-시스템)
- [사용 예시](#사용-예시)
- [업그레이드 방법](#업그레이드-방법)

---

## 요약: v0.3.x vs v0.5.0

| 기능 | v0.3.x | v0.5.0 |
|------|--------|--------|
| 프롬프트 점수 분석 | ✅ structure + context 점수 | ✅ + 인텐트별 세부 분석 |
| 개선 제안 | 일반적인 팁 | 🆕 구체적인 개선 템플릿 제공 |
| 인텐트 감지 | ❌ | ✅ fix, find, create, explain 등 6가지 |
| 누락 정보 감지 | ❌ | ✅ 필수/선택 정보 자동 질문 생성 |
| 자동 실행 힌트 | ❌ | ✅ 안전한 인텐트에서 자동 실행 권장 |
| 스마트 프롬프트 | ❌ | ✅ 실제 프로젝트 파일 경로 포함 |
| 내보내기 | ❌ | ✅ HTML, JSON, GitHub Gist |
| 확장 명령어 추천 | ❌ | ✅ SuperClaude, oh-my-opencode 감지 |

---

## v0.4.0: 프롬프트 코칭 엔진

### 인텐트(Intent) 감지

프롬프트에서 사용자의 의도를 자동으로 파악합니다.

| 인텐트 | 키워드 예시 | 설명 |
|--------|------------|------|
| `find` | 찾아, 확인해, 어디에 | 코드/파일 검색 |
| `fix` | 수정해, 고쳐, 에러 | 버그 수정 |
| `create` | 만들어, 생성해, 추가해 | 새 기능/파일 생성 |
| `explain` | 설명해, 뭐야, 알려줘 | 코드/개념 설명 |
| `refactor` | 리팩토링, 개선해, 정리해 | 코드 개선 |
| `test` | 테스트, 검증해 | 테스트 작성/실행 |

**예시:**

```
입력: "버그 수정해줘"

감지된 인텐트: fix
개선된 프롬프트: "[에러 메시지]가 발생하는 버그를 수정해줘.
                 관련 파일: [파일 경로]"
```

### 문제점 식별 및 개선 제안

프롬프트의 문제점을 구체적으로 식별하고, 개선 템플릿을 제공합니다.

**Before (v0.3.x):**
```
suggestions: ["Add file paths", "Be more specific"]
```

**After (v0.5.0):**
```json
{
  "problems": [
    {
      "type": "missing_target",
      "description": "작업 대상 파일/컴포넌트가 없음",
      "impact": "Claude가 전체 코드베이스를 검색해야 함"
    }
  ],
  "suggestions": [
    {
      "title": "파일 경로 추가",
      "template": "@파일경로에서 [작업내용]"
    }
  ]
}
```

---

## v0.5.0: 자동 실행 힌트 시스템

### Scenario B: Auto-Execute Hints

분석 결과를 바탕으로 Claude가 **자동으로 권장 액션을 실행**하도록 유도합니다.

**안전한 인텐트 (자동 실행 가능):**
- `find` - 파일/코드 검색
- `explain` - 설명 요청

**위험한 인텐트 (사용자 확인 필요):**
- `fix`, `create`, `refactor`, `test` - 코드 변경 가능

**예시:**

```
입력: "로드맵 확인해줘"

분석 결과:
{
  "intent": "find",
  "auto_execute": {
    "enabled": true,
    "reason": "검색 작업은 안전하므로 자동 실행합니다",
    "actions": [
      {"priority": 1, "tool": "Glob", "description": "**/ROADMAP*.md 검색"},
      {"priority": 2, "tool": "Read", "description": "발견된 파일 읽기"}
    ],
    "fallback": "파일을 찾지 못하면 사용자에게 경로 확인 요청"
  }
}
```

### Interactive Mode: 누락 정보 감지

프롬프트에서 필수 정보가 누락된 경우 자동으로 질문을 생성합니다.

**인텐트별 필수 정보:**

| 인텐트 | 필수 | 선택 |
|--------|------|------|
| `fix` | error_message | file_path, steps |
| `create` | - | location, specs |
| `refactor` | - | file_path, goal |

**예시:**

```
입력: "버그 수정해줘"

분석 결과:
{
  "missing_info": [
    {
      "type": "error_message",
      "question": "어떤 에러가 발생하나요?",
      "example": "TypeError: Cannot read property 'x' of undefined",
      "required": true
    },
    {
      "type": "file_path",
      "question": "어느 파일에서 발생하나요?",
      "example": "@src/components/Button.tsx",
      "required": false
    }
  ]
}
```

### Smart Rewrite: 프로젝트 컨텍스트 활용

실제 프로젝트의 파일 구조를 분석하여 구체적인 프롬프트를 생성합니다.

**예시:**

```
입력: "새 컴포넌트 만들어줘"

프로젝트 분석:
- src/components/ 디렉토리 발견
- React + TypeScript 스택 감지

스마트 프롬프트:
"@src/components/[ComponentName].tsx 새 컴포넌트를 만들어줘.
 기존 컴포넌트 스타일 참고: @src/components/Button.tsx"
```

### Export & Share: 베스트 프롬프트 내보내기

수집된 베스트 프롬프트를 다양한 형식으로 내보낼 수 있습니다.

**CLI 명령어:**

```bash
# JSON 형식으로 내보내기
cx export --format json --limit 20

# HTML 형식으로 내보내기 (브라우저에서 열기 가능)
cx export --format html --output my-prompts.html

# GitHub Gist로 공유 (gh CLI 필요)
cx export --format gist --public
```

**HTML Export 예시:**

![HTML Export](./images/html-export-preview.png)

---

## 사용 예시

### 예시 1: 모호한 버그 수정 요청

**입력:**
```
버그 수정해줘
```

**v0.3.x 응답:**
```
점수: structure 2.0, context 0.0
제안: "Be more specific about the bug"
```

**v0.5.0 응답:**
```
📊 현재 점수:
- 구조: 2.0/10
- 맥락: 0.0/10

🎯 감지된 의도: fix

❌ 주요 문제:
- 에러 메시지가 없음 (영향: Claude가 문제를 추측해야 함)
- 파일 경로가 없음 (영향: 전체 코드베이스 검색 필요)

❓ 추가 정보 필요:
- 어떤 에러가 발생하나요? (필수)
  예: TypeError: Cannot read property 'x' of undefined
- 어느 파일에서 발생하나요?
  예: @src/components/Button.tsx

✨ 개선된 프롬프트:
"[에러메시지]가 발생하는 버그를 수정해줘.
 관련 파일: @[파일경로]"
```

### 예시 2: 검색 요청 (자동 실행)

**입력:**
```
로드맵 확인해줘
```

**v0.5.0 응답:**
```
🎯 감지된 의도: find

🤖 자동 실행 권장:
검색 작업은 안전하므로 자동 실행합니다

권장 순서:
1. Glob: **/ROADMAP*.md 검색
2. Read: 발견된 파일 읽기

⚠️ 실패 시: 파일을 찾지 못하면 사용자에게 경로 확인 요청
```

→ Claude가 자동으로 Glob → Read 실행

### 예시 3: 잘 작성된 프롬프트

**입력:**
```
@src/api/users.ts 에서 "TypeError: user.name is undefined" 에러가
발생해. getUser 함수에서 null 체크가 빠진 것 같아. 수정해줘.
```

**v0.5.0 응답:**
```
📊 현재 점수:
- 구조: 6.0/10
- 맥락: 6.0/10

🎯 감지된 의도: fix

✅ 좋은 프롬프트입니다!
- 파일 경로 명시됨 ✓
- 에러 메시지 포함 ✓
- 원인 추측 포함 ✓

❓ 추가 정보 필요: 없음

🔧 권장 액션:
- Read: @src/api/users.ts 파일 읽기
- Edit: null 체크 로직 추가
```

---

## 업그레이드 방법

```bash
# PyPI에서 최신 버전 설치
pip3 install --upgrade claude-x

# 버전 확인
cx --version
# → claude-x, version 0.5.0

# Claude Code 재시작 (MCP 서버 리로드)
# 1. Claude Code 종료
# 2. Claude Code 재시작
```

---

## MCP Tool 사용법

Claude Code에서 자연스럽게 사용할 수 있습니다:

```
사용자: "내 프롬프트 분석해줘: 버그 수정해줘"
→ mcp__claude-x__analyze_and_improve_prompt 자동 호출

사용자: "내 베스트 프롬프트 보여줘"
→ mcp__claude-x__get_best_prompts 자동 호출

사용자: "세션 통계 보여줘"
→ mcp__claude-x__analyze_sessions 자동 호출
```

---

## 다음 단계

- **v0.6.0 예정**: 웹 UI 대시보드, 팀 공유 기능
- **피드백**: https://github.com/kakao-lucas-ms/claude-x/issues

---

Last Updated: 2026-01-24
