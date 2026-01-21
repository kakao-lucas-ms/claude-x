# Changelog

All notable changes to Claude-X will be documented in this file.

## [0.1.1] - 2026-01-21

### Changed
- Use the first user message (with command-args when present) for prompt analysis.
- Filter command-only prompts (e.g. /clear, /model) from prompt rankings.
- Add configurable prompt preview length for `cx prompts`.

## [0.1.0] - 2026-01-20

### 🎉 Initial Release

Claude-X의 첫 번째 공식 릴리즈입니다!

### ✨ Added

#### 핵심 기능
- **세션 데이터 수집**: Claude Code 세션 자동 import
- **전문 검색**: SQLite FTS5 기반 코드 검색
- **프롬프트 분석**: 4가지 지표로 품질 평가
- **템플릿 라이브러리**: 재사용 가능한 8개 템플릿

#### CLI 명령어
- `cx init` - 데이터베이스 초기화
- `cx import` - 세션 데이터 가져오기
- `cx list` - 세션 목록 조회
- `cx search` - 코드 전문 검색
- `cx stats` - 통계 조회
- `cx show` - 세션 상세 정보
- `cx report` - 사용 현황 리포트
- `cx prompts` - 프롬프트 품질 분석
- `cx templates` - 템플릿 라이브러리

#### 데이터 수집
- `sessions-index.json` 파서
- JSONL 세션 파일 파서
- 타임스탬프 자동 감지 (Unix ms / ISO 8601)
- 마크다운 코드 블록 자동 추출
- 민감 정보 자동 검출 (14개 패턴)

#### 분석 기능
- 프롬프트 품질 점수 계산
  - 효율성 (40%): 코드/프롬프트 비율
  - 명확성 (30%): 대화 길이
  - 생산성 (20%): 코드 라인 수
  - 품질 (10%): 보안 + 다양성
- 카테고리별 통계 (7개 카테고리)
- 브랜치 타입별 생산성 분석
- 언어 분포 분석
- 시간대별 활동 분석
- 민감 정보 검출 리포트

#### 템플릿
- `jira_ticket_creation` - JIRA 티켓 생성
- `technical_research` - 기술 조사
- `environment_setup_review` - 환경 구축 검토
- `bug_fix` - 버그 수정
- `feature_implementation` - 기능 구현
- `code_review` - 코드 리뷰
- `refactoring` - 리팩토링
- `test_creation` - 테스트 작성

#### 출력 형식
- Rich 터미널 UI (테이블, 색상, 진행 바)
- JSON 내보내기
- Markdown 리포트 생성

### 🏗️ Technical

#### 아키텍처
- 모듈형 구조 (8개 주요 모듈)
- SQLite + FTS5 full-text search
- WAL 모드로 동시성 지원
- Pydantic 타입 검증

#### 데이터베이스
- 4개 테이블 (projects, sessions, messages, code_snippets)
- FTS5 가상 테이블 (전문 검색)
- 자동 트리거 (FTS 동기화)
- 인덱스 최적화

#### 성능
- 스트리밍 파서 (메모리 효율)
- SHA-256 해시 기반 중복 제거
- 배치 커밋 (트랜잭션 최소화)
- FTS5 rank 정렬

### 📚 Documentation

- `README.md` - 종합 가이드 (450+ 줄)
- `EXAMPLES.md` - 사용 예시 (시나리오별)
- `ARCHITECTURE.md` - 아키텍처 설계 문서
- `CHANGELOG.md` - 변경 이력 (이 파일)

### 🎯 Highlights

**최고 효율 프롬프트:**
- 5개 메시지로 34개 코드 생성 (JIRA 티켓)
- 효율성 점수 6.8/10

**검색 성능:**
- 3,000+ 코드 스니펫 즉시 검색
- FTS5 rank 정렬로 관련도 순

**분석 정확도:**
- 14개 민감 정보 패턴 검출
- 7개 카테고리 자동 분류
- 4개 브랜치 타입 구분

### 📊 Statistics (테스트 데이터)

- 프로젝트: 3개
- 세션: 248개
- 메시지: 4,997개
- 코드 스니펫: 3,257개
- 언어: 15개 (TypeScript, Python, Bash, etc.)

### 🔒 Security

- 민감 정보 자동 검출 및 플래그
- SQL Injection 방지 (parameterized queries)
- 로컬 데이터만 사용 (외부 전송 없음)

---

## [Unreleased]

향후 추가 예정 기능:

### 계획 중
- 웹 UI 대시보드
- AI 기반 프롬프트 개선 제안
- 실시간 세션 모니터링
- 팀 공유 기능
- 플러그인 시스템

---

## Version Format

`[Major].[Minor].[Patch]`

- **Major**: 호환성 없는 변경
- **Minor**: 하위 호환 기능 추가
- **Patch**: 하위 호환 버그 수정

## Categories

- `Added` - 새로운 기능
- `Changed` - 기존 기능 변경
- `Deprecated` - 곧 제거될 기능
- `Removed` - 제거된 기능
- `Fixed` - 버그 수정
- `Security` - 보안 관련 변경

---

**Keep a Changelog**: https://keepachangelog.com/ko/1.0.0/
**Semantic Versioning**: https://semver.org/lang/ko/
