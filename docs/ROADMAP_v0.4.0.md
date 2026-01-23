# claude-x v0.4.0 구현 로드맵

> **목표**: 프롬프트 개선 코칭 기능 (cx 명령어 + MCP 통합)

**타겟 완료일**: 2026-01-30 (7일)

---

## 📋 목차

1. [개요](#개요)
2. [핵심 기능](#핵심-기능)
3. [파일 구조](#파일-구조)
4. [상세 구현 계획](#상세-구현-계획)
5. [데이터 흐름](#데이터-흐름)
6. [테스트 계획](#테스트-계획)
7. [마일스톤](#마일스톤)

---

## 개요

### 비전
```
사용자: "cx 이 버그 수정해줘"
  ↓
MCP 함수 호출
  ↓
로컬 데이터 분석 (베스트 프롬프트, 패턴, 확장)
  ↓
Claude가 자연스럽게 개선안 제시
```

### 핵심 가치
- ✅ **API 키 불필요** - Claude Code의 Claude 활용
- ✅ **로컬 데이터 기반** - 사용자의 실제 성공 패턴
- ✅ **다국어 지원** - 한국어/영어 자동 감지
- ✅ **확장 인식** - SuperClaude, oh-my-opencode 통합
- ✅ **즉시 실행** - 설정 없이 바로 작동

---

## 핵심 기능

### Feature 1: 프롬프트 분석
```bash
cx "응 진행해줘"
```
- 점수 계산 (structure, context)
- 문제점 식별
- 언어 자동 감지
- 사용자 히스토리 기반 분석

### Feature 2: 개선 제안
- 사용자 베스트 프롬프트 패턴 활용
- 구체적 개선안 생성
- 예상 효과 계산

### Feature 3: 확장 시스템 연동
- SuperClaude, oh-my-opencode 탐지
- 컨텍스트 기반 명령어 제안
- 멀티 확장 최적 워크플로우

### Feature 4: MCP 통합
- Claude Code에서 자동 호출
- LLM-친화적 응답 형식
- 자연스러운 대화형 UX

---

## 파일 구조

```
claude-x-standalone/
├── src/claude_x/
│   ├── i18n.py                    # NEW - 다국어 지원
│   ├── extensions.py              # NEW - 확장 시스템 탐지
│   ├── prompt_coach.py            # NEW - 코칭 로직
│   ├── mcp_server.py              # UPDATE - MCP 함수 추가
│   ├── cli.py                     # UPDATE - cx 명령어 추가
│   ├── scoring.py                 # 기존 - 점수 계산
│   ├── patterns.py                # 기존 - 패턴 분석
│   └── analytics.py               # 기존 - 사용자 히스토리
│
├── tests/
│   ├── test_i18n.py               # NEW
│   ├── test_extensions.py         # NEW
│   ├── test_prompt_coach.py       # NEW
│   └── test_mcp_coach.py          # NEW
│
└── docs/
    ├── ROADMAP_v0.4.0.md          # 이 파일
    └── PROMPT_COACHING.md         # NEW - 사용 가이드
```

---

## 상세 구현 계획

### Day 1: 다국어 지원 인프라 (i18n)

#### 파일: `src/claude_x/i18n.py`

**기능:**
1. 언어 자동 감지
2. 번역 딕셔너리 관리
3. 번역 헬퍼 함수

**상세 스펙:**

```python
# 1. 언어 감지
def detect_language(prompt: str) -> str:
    """
    프롬프트의 언어를 자동 감지

    로직:
    - 한글 비율 > 30% → "ko"
    - 그 외 → "en"

    Args:
        prompt: 분석할 프롬프트

    Returns:
        "ko" | "en"
    """
    pass

# 2. 번역 딕셔너리
TRANSLATIONS = {
    "ko": {
        "analysis.title": "🤖 프롬프트 분석 결과",
        "analysis.structure": "구조",
        "analysis.context": "맥락",
        "problems.no_target": "구체적 대상 없음",
        "problems.no_context": "배경 정보 부족",
        "suggestions.add_file": "파일 경로를 명시하세요",
        # ... 50+ 번역 키
    },
    "en": {
        "analysis.title": "🤖 Prompt Analysis",
        "analysis.structure": "Structure",
        "analysis.context": "Context",
        "problems.no_target": "No specific target",
        "problems.no_context": "Lacking context",
        "suggestions.add_file": "Specify the file path",
        # ... 50+ 번역 키
    }
}

# 3. 번역 헬퍼
def t(key: str, lang: str = None, **kwargs) -> str:
    """
    번역 키를 실제 텍스트로 변환

    Args:
        key: "analysis.title" 형식의 키
        lang: 언어 코드 (None이면 자동 감지)
        **kwargs: 포맷팅 변수

    Returns:
        번역된 텍스트

    Example:
        t("suggestions.add_file", "ko")
        t("scores.value", "en", score=7.5)
    """
    pass
```

**테스트 케이스:**
```python
def test_detect_language():
    assert detect_language("이 버그 수정해줘") == "ko"
    assert detect_language("fix this bug") == "en"
    assert detect_language("버그 fix") == "ko"  # 혼합

def test_translation():
    assert t("analysis.title", "ko") == "🤖 프롬프트 분석 결과"
    assert t("analysis.title", "en") == "🤖 Prompt Analysis"
```

**소요 시간:** 4시간

---

### Day 2: 확장 시스템 탐지

#### 파일: `src/claude_x/extensions.py`

**기능:**
1. 설치된 확장 탐지
2. 확장별 명령어 매핑
3. 프롬프트 기반 명령어 제안

**상세 스펙:**

```python
# 1. 확장 정의
KNOWN_EXTENSIONS = {
    "superclaude": {
        "name": "SuperClaude",
        "detection": [
            "~/.claude/CLAUDE.md contains 'SuperClaude'",
            ".superclaude directory exists"
        ],
        "commands": {
            "/sc:implement": {
                "description": "구조화된 기능 구현",
                "triggers": ["기능 구현", "implement", "add feature"],
                "confidence_boost": 2.0
            },
            "/sc:brainstorm": {
                "description": "소크라틱 대화로 요구사항 탐색",
                "triggers": ["브레인스토밍", "brainstorm", "아이디어"],
                "confidence_boost": 2.0
            },
            "/sc:troubleshoot": {
                "description": "체계적 디버깅",
                "triggers": ["버그", "에러", "bug", "error"],
                "confidence_boost": 1.5
            }
            # ... 10+ 명령어
        }
    },
    "oh-my-opencode": {
        "name": "Oh-My-OpenCode",
        "detection": [
            ".oh-my-opencode directory exists",
            "~/.claude/CLAUDE.md contains 'oh-my-opencode'"
        ],
        "commands": {
            "/sisyphus": {
                "description": "멀티 에이전트 오케스트레이션",
                "triggers": ["복잡한", "여러 단계", "multi-step"],
                "confidence_boost": 1.8
            },
            "/ultrawork": {
                "description": "병렬 에이전트 실행",
                "triggers": ["빠르게", "병렬", "parallel"],
                "confidence_boost": 2.0
            },
            "/deepsearch": {
                "description": "코드베이스 심층 검색",
                "triggers": ["찾아", "검색", "search", "find"],
                "confidence_boost": 1.5
            }
            # ... 10+ 명령어
        }
    }
}

# 2. 탐지 함수
def detect_installed_extensions() -> list[str]:
    """
    설치된 확장 탐지

    Returns:
        ["superclaude", "oh-my-opencode"]
    """
    pass

def is_extension_installed(ext_name: str) -> bool:
    """
    특정 확장 설치 여부

    로직:
    - detection 규칙 체크
    - "contains" → 파일 내용 확인
    - "exists" → 경로 존재 확인
    """
    pass

# 3. 명령어 제안
def suggest_extension_command(
    prompt: str,
    installed: list[str]
) -> dict | None:
    """
    프롬프트에 맞는 확장 명령어 제안

    Returns:
        {
            "extension": "superclaude",
            "command": "/sc:implement",
            "reason": "구조화된 기능 구현",
            "confidence": 0.85,
            "usage_example": "..."
        }
    """
    pass

def calculate_confidence(prompt: str, triggers: list[str], boost: float) -> float:
    """
    명령어 매칭 신뢰도 계산

    로직:
    - 기본 점수 = (매칭 키워드 수 / 전체 키워드 수)
    - 최종 점수 = 기본 점수 * boost
    """
    pass
```

**테스트 케이스:**
```python
def test_detect_extensions(tmp_path):
    # SuperClaude 설치 시뮬레이션
    claude_md = tmp_path / ".claude" / "CLAUDE.md"
    claude_md.parent.mkdir()
    claude_md.write_text("SuperClaude Commands")

    installed = detect_installed_extensions()
    assert "superclaude" in installed

def test_suggest_command():
    prompt = "이 기능 복잡해서 여러 단계로 구현해야 할 것 같아"
    suggestion = suggest_extension_command(prompt, ["superclaude", "oh-my-opencode"])

    assert suggestion["command"] == "/sc:implement"
    assert suggestion["confidence"] > 0.7
```

**소요 시간:** 6시간

---

### Day 3: 프롬프트 코칭 로직

#### 파일: `src/claude_x/prompt_coach.py`

**기능:**
1. 프롬프트 분석
2. 문제점 식별
3. 개선 제안 생성
4. 예상 효과 계산

**상세 스펙:**

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class CoachingResult:
    """코칭 결과"""
    language: str
    original_prompt: str
    scores: dict
    problems: list[dict]
    suggestions: list[dict]
    extension_suggestion: Optional[dict]
    expected_impact: dict
    user_insights: list[dict]


class PromptCoach:
    """프롬프트 코칭 엔진"""

    def __init__(self, analytics: Analytics):
        self.analytics = analytics

    def analyze(
        self,
        prompt: str,
        detect_extensions: bool = True
    ) -> CoachingResult:
        """
        프롬프트 종합 분석

        Flow:
        1. 언어 감지
        2. 점수 계산
        3. 문제점 식별
        4. 사용자 패턴 분석
        5. 개선 제안 생성
        6. 확장 명령어 제안
        7. 예상 효과 계산
        """
        pass

    def identify_problems(
        self,
        prompt: str,
        scores: dict,
        lang: str
    ) -> list[dict]:
        """
        문제점 식별

        체크 항목:
        - structure < 2.0 → 대상 없음
        - context < 2.0 → 배경 정보 부족
        - 대화형 패턴 (응, 그거, 이거)
        - 파일 경로 없음
        - 에러 메시지 없음 (버그 수정 시)

        Returns:
            [
                {
                    "issue": "no_target",
                    "severity": "high",
                    "description": "구체적 대상 없음",
                    "impact": "코드 생성량 -60%",
                    "how_to_fix": "파일명이나 모듈명 명시"
                }
            ]
        """
        pass

    def generate_suggestions(
        self,
        prompt: str,
        problems: list[dict],
        user_best: list[dict],
        lang: str
    ) -> list[dict]:
        """
        개선 제안 생성

        로직:
        1. 사용자 베스트 프롬프트에서 유사 패턴 찾기
        2. 해당 패턴의 템플릿 추출
        3. 현재 프롬프트를 템플릿에 맞춰 변환
        4. 여러 개선안 생성 (최대 3개)

        Returns:
            [
                {
                    "type": "user_pattern",
                    "title": "당신의 베스트 패턴: 버그 수정",
                    "template": "[FILE]에서 [ERROR] 발생...",
                    "example": "실제 예시...",
                    "why_successful": "평균 코드 4개 생성, 재작업 10%",
                    "confidence": 0.85
                }
            ]
        """
        pass

    def calculate_expected_impact(
        self,
        current_scores: dict,
        target_scores: dict,
        user_stats: dict
    ) -> dict:
        """
        개선 시 예상 효과 계산

        Returns:
            {
                "messages": {
                    "current": 9,
                    "expected": 3,
                    "improvement": "66% 감소"
                },
                "code_generation": {
                    "current": 2,
                    "expected": 4,
                    "improvement": "2배 증가"
                },
                "success_rate": {
                    "current": 0.35,
                    "expected": 0.85,
                    "improvement": "+143%"
                }
            }
        """
        pass

    def generate_user_insights(self) -> list[dict]:
        """
        사용자별 맞춤 인사이트

        분석 항목:
        - 파일 참조 효과
        - 에러 메시지 포함 효과
        - 대화형 프롬프트 비율
        - 카테고리별 성공률

        Returns:
            [
                {
                    "type": "strength",
                    "message": "파일 경로 포함 시 효율성 +40%",
                    "recommendation": "계속 유지하세요!"
                },
                {
                    "type": "weakness",
                    "message": "대화형 프롬프트 60% → 재작업 증가",
                    "recommendation": "독립적 프롬프트 작성"
                }
            ]
        """
        pass
```

**테스트 케이스:**
```python
def test_identify_problems():
    coach = PromptCoach(analytics)

    prompt = "응 진행해줘"
    scores = {"structure_score": 0.0, "context_score": 0.0}
    problems = coach.identify_problems(prompt, scores, "ko")

    assert len(problems) >= 2
    assert any(p["issue"] == "no_target" for p in problems)
    assert any(p["issue"] == "conversational" for p in problems)

def test_generate_suggestions():
    coach = PromptCoach(analytics)

    suggestions = coach.generate_suggestions(
        prompt="이 버그 수정해줘",
        problems=[...],
        user_best=[...],
        lang="ko"
    )

    assert len(suggestions) > 0
    assert suggestions[0]["type"] in ["user_pattern", "generic"]
    assert "template" in suggestions[0]
```

**소요 시간:** 8시간

---

### Day 4: MCP 함수 구현

#### 파일: `src/claude_x/mcp_server.py` (UPDATE)

**추가 함수:**

```python
@mcp.tool()
def analyze_and_improve_prompt(
    prompt: str,
    detect_extensions: bool = True,
    include_history: bool = True
) -> dict:
    """
    프롬프트를 분석하고 개선 제안 제공

    이 함수는 Claude Code에서 자동으로 호출됩니다.
    Claude가 결과를 자연스럽게 설명합니다.

    Args:
        prompt: 분석할 프롬프트
        detect_extensions: 확장 시스템 탐지 여부
        include_history: 사용자 히스토리 포함 여부

    Returns:
        {
            "language": "ko" | "en",
            "original_prompt": "...",
            "scores": {...},
            "problems": [...],
            "suggestions": [...],
            "extension_suggestion": {...} | null,
            "expected_impact": {...},
            "user_insights": [...],
            "llm_summary": "Claude가 읽기 좋은 요약"
        }
    """
    from claude_x.prompt_coach import PromptCoach
    from claude_x.i18n import detect_language
    from claude_x.extensions import detect_installed_extensions, suggest_extension_command

    # 1. 코칭 엔진 초기화
    coach = PromptCoach(analytics)

    # 2. 분석 실행
    result = coach.analyze(prompt, detect_extensions)

    # 3. LLM 친화적 요약 생성
    llm_summary = generate_llm_summary(result)

    return {
        **result.__dict__,
        "llm_summary": llm_summary
    }


def generate_llm_summary(result: CoachingResult) -> str:
    """
    Claude가 자연스럽게 설명할 수 있도록 요약

    포맷:
    - 간결한 문장
    - 핵심 포인트 강조
    - 구체적 예시 포함
    - 확장 제안 (있으면)
    """
    lang = result.language

    if lang == "ko":
        summary = f"""
프롬프트 "{result.original_prompt}"를 분석했습니다.

📊 현재 점수:
- 구조: {result.scores['structure']}/10
- 맥락: {result.scores['context']}/10

❌ 주요 문제:
{format_problems_ko(result.problems)}

💡 개선 제안:
{format_suggestions_ko(result.suggestions)}

📈 예상 효과:
{format_impact_ko(result.expected_impact)}
"""
    else:
        summary = f"""
Analyzed prompt "{result.original_prompt}".

📊 Current scores:
- Structure: {result.scores['structure']}/10
- Context: {result.scores['context']}/10

❌ Issues:
{format_problems_en(result.problems)}

💡 Suggestions:
{format_suggestions_en(result.suggestions)}

📈 Expected impact:
{format_impact_en(result.expected_impact)}
"""

    # 확장 제안 추가
    if result.extension_suggestion:
        ext = result.extension_suggestion
        if lang == "ko":
            summary += f"""

✨ {ext['extension']} 제안:
`{ext['command']}` 명령어를 사용하면 더 효율적입니다.
이유: {ext['reason']}

예시: {ext['usage_example']}
"""
        else:
            summary += f"""

✨ {ext['extension']} suggestion:
Consider using `{ext['command']}`.
Reason: {ext['reason']}

Example: {ext['usage_example']}
"""

    return summary
```

**테스트 케이스:**
```python
def test_mcp_analyze_prompt():
    result = analyze_and_improve_prompt("응 진행해줘")

    assert result["language"] == "ko"
    assert result["scores"]["structure"] == 0.0
    assert len(result["problems"]) > 0
    assert len(result["suggestions"]) > 0
    assert "llm_summary" in result

def test_mcp_with_extensions():
    result = analyze_and_improve_prompt(
        "이 기능 복잡해서 여러 단계로 구현해야 해",
        detect_extensions=True
    )

    assert result["extension_suggestion"] is not None
    assert result["extension_suggestion"]["command"].startswith("/")
```

**소요 시간:** 6시간

---

### Day 5: CLI 명령어 추가

#### 파일: `src/claude_x/cli.py` (UPDATE)

**추가 명령어:**

```python
@app.command()
def coach(
    prompt: str = typer.Argument(..., help="Prompt to analyze"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    no_extensions: bool = typer.Option(False, "--no-ext", help="Disable extension detection"),
    no_history: bool = typer.Option(False, "--no-history", help="Disable user history")
):
    """
    프롬프트를 분석하고 개선 제안을 받습니다.

    Examples:
        cx coach "응 진행해줘"
        cx coach "fix this bug" --json
        cx coach "implement feature" --no-ext
    """
    from claude_x.mcp_server import analyze_and_improve_prompt
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown

    console = Console()

    # MCP 함수 호출
    result = analyze_and_improve_prompt(
        prompt=prompt,
        detect_extensions=not no_extensions,
        include_history=not no_history
    )

    if json_output:
        # JSON 출력 (Claude가 읽기 좋게)
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Rich 포맷으로 출력
    lang = result["language"]

    # 제목
    title = "🤖 프롬프트 분석 결과" if lang == "ko" else "🤖 Prompt Analysis"
    console.print(Panel(title, style="bold blue"))

    # 점수
    console.print("\n📊 점수" if lang == "ko" else "\n📊 Scores")
    console.print(f"- 구조: {result['scores']['structure']}/10" if lang == "ko"
                  else f"- Structure: {result['scores']['structure']}/10")
    console.print(f"- 맥락: {result['scores']['context']}/10" if lang == "ko"
                  else f"- Context: {result['scores']['context']}/10")

    # 문제점
    if result["problems"]:
        console.print("\n❌ 문제점" if lang == "ko" else "\n❌ Issues")
        for i, problem in enumerate(result["problems"], 1):
            console.print(f"{i}. {problem['description']}")
            console.print(f"   영향: {problem['impact']}", style="dim")

    # 개선 제안
    if result["suggestions"]:
        console.print("\n💡 개선 제안" if lang == "ko" else "\n💡 Suggestions")
        for i, suggestion in enumerate(result["suggestions"], 1):
            console.print(f"\n[bold]{i}. {suggestion['title']}[/bold]")
            console.print(Panel(suggestion['template'], border_style="green"))
            if "why_successful" in suggestion:
                console.print(f"   성공 이유: {suggestion['why_successful']}", style="dim")

    # 확장 제안
    if result.get("extension_suggestion"):
        ext = result["extension_suggestion"]
        console.print("\n✨ 확장 기능 제안" if lang == "ko" else "\n✨ Extension Suggestion")
        console.print(f"[bold cyan]{ext['command']}[/bold cyan]")
        console.print(f"이유: {ext['reason']}" if lang == "ko" else f"Reason: {ext['reason']}")

    # 예상 효과
    if result.get("expected_impact"):
        impact = result["expected_impact"]
        console.print("\n📈 예상 효과" if lang == "ko" else "\n📈 Expected Impact")
        console.print(f"- 메시지 수: {impact['messages']['improvement']}")
        console.print(f"- 코드 생성: {impact['code_generation']['improvement']}")
        console.print(f"- 성공률: {impact['success_rate']['improvement']}")


# 별칭 명령어
@app.command(hidden=True)
def cx(prompt: str = typer.Argument(...)):
    """Alias for 'coach' command"""
    coach(prompt)
```

**테스트:**
```bash
# 기본 사용
cx coach "응 진행해줘"

# JSON 출력
cx coach "fix this bug" --json

# 확장 탐지 비활성화
cx coach "implement feature" --no-ext
```

**소요 시간:** 4시간

---

### Day 6-7: 테스트 및 문서화

#### 테스트 계획

**Unit Tests:**
```python
# tests/test_i18n.py
- test_detect_language_korean
- test_detect_language_english
- test_detect_language_mixed
- test_translation_ko
- test_translation_en
- test_translation_with_params

# tests/test_extensions.py
- test_detect_superclaude
- test_detect_oh_my_opencode
- test_suggest_command_implement
- test_suggest_command_brainstorm
- test_suggest_command_search
- test_calculate_confidence
- test_no_extensions_installed

# tests/test_prompt_coach.py
- test_identify_problems_no_target
- test_identify_problems_no_context
- test_identify_problems_conversational
- test_generate_suggestions_user_pattern
- test_generate_suggestions_generic
- test_calculate_expected_impact
- test_generate_user_insights

# tests/test_mcp_coach.py
- test_analyze_prompt_korean
- test_analyze_prompt_english
- test_analyze_with_extensions
- test_analyze_without_history
- test_llm_summary_format
```

**Integration Tests:**
```bash
# CLI 테스트
cx coach "응 진행해줘"
cx coach "fix this bug" --json
cx coach "implement X" --no-ext

# MCP 테스트 (Python으로)
python3 -c "
from claude_x.mcp_server import analyze_and_improve_prompt
result = analyze_and_improve_prompt('이 버그 수정해줘')
print(result['llm_summary'])
"
```

#### 문서 작성

**파일: `docs/PROMPT_COACHING.md`**

```markdown
# 프롬프트 코칭 가이드

## 사용법

### CLI에서 사용
\`\`\`bash
cx coach "내 프롬프트"
\`\`\`

### Claude Code에서 사용
\`\`\`
User: "cx 이 버그 수정해줘"
Claude: [자동으로 분석 및 개선안 제시]
\`\`\`

## 기능

### 1. 자동 언어 감지
- 한국어 프롬프트 → 한국어 응답
- 영어 프롬프트 → 영어 응답

### 2. 로컬 데이터 기반 분석
- 당신의 베스트 프롬프트 패턴 활용
- 실제 성공 데이터 기반 제안

### 3. 확장 시스템 연동
- SuperClaude 명령어 제안
- oh-my-opencode 워크플로우 추천

## 예시

[상세 예시 20개...]
```

**README.md 업데이트:**
```markdown
## 🆕 v0.4.0 - 프롬프트 코칭 기능

\`\`\`bash
# 프롬프트 개선 제안 받기
cx coach "응 진행해줘"

# Claude Code 내에서
User: "cx 이 버그 수정해줘"
→ 자동으로 분석 및 개선안 제시
\`\`\`

### 주요 기능
- ✅ 로컬 데이터 기반 개인화
- ✅ 다국어 지원 (한/영)
- ✅ 확장 시스템 인식
- ✅ API 키 불필요
```

**CHANGELOG.md 업데이트:**
```markdown
## [0.4.0] - 2026-01-30

### Added
- 프롬프트 코칭 기능 (`cx coach`)
- MCP 함수: `analyze_and_improve_prompt`
- 다국어 지원 (한국어, 영어)
- 확장 시스템 탐지 (SuperClaude, oh-my-opencode)
- 사용자 베스트 패턴 기반 개선 제안
- 예상 효과 계산
- 개인화된 인사이트

### Changed
- MCP 서버 응답 포맷 개선
- CLI 명령어 구조 확장
```

**소요 시간:** 2일 (16시간)

---

## 데이터 흐름

```
사용자 입력
  ↓
"cx 이 버그 수정해줘"
  ↓
CLI (cli.py)
  ↓
MCP 함수 (mcp_server.py)
  ↓
PromptCoach (prompt_coach.py)
  ├─→ i18n (언어 감지)
  ├─→ scoring (점수 계산)
  ├─→ analytics (사용자 히스토리)
  ├─→ patterns (패턴 분석)
  └─→ extensions (확장 탐지)
  ↓
CoachingResult
  ↓
LLM Summary 생성
  ↓
JSON 응답
  ↓
Claude Code
  ↓
자연스러운 설명
  ↓
사용자에게 표시
```

---

## 테스트 계획

### 자동화 테스트
```bash
# Unit tests
pytest tests/test_i18n.py
pytest tests/test_extensions.py
pytest tests/test_prompt_coach.py
pytest tests/test_mcp_coach.py

# Integration tests
pytest tests/integration/

# Coverage
pytest --cov=claude_x --cov-report=html
```

### 수동 테스트 체크리스트

**기능 테스트:**
- [ ] 한국어 프롬프트 분석
- [ ] 영어 프롬프트 분석
- [ ] 혼합 언어 프롬프트
- [ ] SuperClaude 탐지
- [ ] oh-my-opencode 탐지
- [ ] 확장 없을 때
- [ ] 사용자 히스토리 없을 때
- [ ] JSON 출력 형식
- [ ] Rich 출력 형식

**성능 테스트:**
- [ ] 분석 속도 < 500ms
- [ ] MCP 응답 < 1s
- [ ] 메모리 사용량 체크

**UX 테스트:**
- [ ] 에러 메시지 명확성
- [ ] 개선안 실용성
- [ ] 확장 제안 적절성

---

## 마일스톤

### Milestone 1: 기초 인프라 (Day 1-2)
- [x] TodoWrite로 작업 추적 시작
- [ ] i18n.py 구현
- [ ] extensions.py 구현
- [ ] 단위 테스트 작성

**완료 조건:**
- 언어 감지 정확도 > 95%
- 확장 탐지 작동
- 테스트 커버리지 > 80%

### Milestone 2: 코칭 로직 (Day 3-4)
- [ ] prompt_coach.py 구현
- [ ] MCP 함수 추가
- [ ] 통합 테스트

**완료 조건:**
- 문제점 식별 정확도 > 90%
- 개선 제안 품질 검증
- MCP 함수 작동 확인

### Milestone 3: CLI & 문서화 (Day 5-7)
- [ ] CLI 명령어 추가
- [ ] 테스트 완료
- [ ] 문서 작성
- [ ] v0.4.0 릴리즈

**완료 조건:**
- 모든 테스트 통과
- 문서 완성
- 실제 프롬프트로 검증

---

## 리스크 관리

### 리스크 1: 확장 탐지 실패
**완화 방안:**
- 여러 탐지 규칙 제공
- 수동 설정 옵션
- 우아한 fallback

### 리스크 2: 번역 품질
**완화 방안:**
- 네이티브 검토
- 커뮤니티 피드백
- 점진적 개선

### 리스크 3: 성능 이슈
**완화 방안:**
- 결과 캐싱
- 비동기 처리
- 프로파일링

---

## 배포 계획

### Pre-release (v0.4.0-rc1)
```bash
# 1. 버전 업데이트
# - pyproject.toml
# - plugin.json
# - __init__.py

# 2. 테스트 실행
pytest

# 3. Pre-release 생성
git tag v0.4.0-rc1
git push origin v0.4.0-rc1
gh release create v0.4.0-rc1 --prerelease

# 4. 피드백 수집 (3일)
```

### Release (v0.4.0)
```bash
# 1. 피드백 반영
# 2. 최종 테스트
# 3. 릴리즈 노트 작성
# 4. GitHub Release + PyPI 자동 배포
```

---

## 성공 지표

### 정량적 지표
- [ ] 테스트 커버리지 > 85%
- [ ] 분석 속도 < 500ms
- [ ] 확장 탐지 정확도 > 95%
- [ ] 언어 감지 정확도 > 95%

### 정성적 지표
- [ ] 개선안이 실제로 유용함
- [ ] 확장 제안이 적절함
- [ ] UX가 자연스러움
- [ ] 사용자 피드백 긍정적

---

## 다음 단계 (v0.5.0)

### 대화형 개선
- 부족한 정보 질문
- 인터랙티브 템플릿 채우기
- 실시간 피드백

### AI 강화 (선택적)
- `--ai` 플래그로 Claude API 활용
- 더 자연스러운 설명
- 컨텍스트 기반 고급 제안

### 커뮤니티 기능
- 익명화된 프롬프트 공유
- 베스트 프랙티스 라이브러리
- 투표 및 큐레이션

---

**작성일**: 2026-01-23
**담당자**: lucas.ms
**상태**: Draft → In Progress
