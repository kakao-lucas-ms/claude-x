"""Prompt template library for reusable patterns."""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """Prompt template model."""
    
    name: str
    category: str
    description: str
    template: str
    variables: List[str]
    example: str
    success_metrics: str
    tags: List[str]


class PromptTemplateLibrary:
    """Library of reusable prompt templates."""

    @staticmethod
    def get_all_templates() -> List[PromptTemplate]:
        """Get all available prompt templates."""
        return [
            # JIRA 티켓 생성
            PromptTemplate(
                name="jira_ticket_creation",
                category="문서화",
                description="구조화된 지라 티켓을 생성하는 프롬프트. 배경, 목적, 상세 내용을 명확히 제공합니다.",
                template="""아래의 내용으로 지라 이슈 만들어줘

📋 JIRA 티켓 초안

제목: {{title}}

설명:
## 배경
{{background}}

## 목적
{{purpose}}

## 상세 내용
{{details}}

## 체크리스트
{{checklist}}

## 참고 자료
{{references}}""",
                variables=["title", "background", "purpose", "details", "checklist", "references"],
                example="""아래의 내용으로 지라 이슈 만들어줘

📋 JIRA 티켓 초안

제목: 프로필 페이지 API 병렬화 (Promise.all)

설명:
## 배경
- 현재 프로필 페이지에서 API 호출이 순차적으로 실행됨
- 총 로딩 시간이 2.3초로 느림

## 목적
- 독립적인 API 호출을 병렬화하여 로딩 시간 단축
- 목표: 38% 단축 (1.4초)

## 상세 내용
- getUserProfile()
- getUserPosts()  
- getUserStats()
위 3개 API를 Promise.all로 병렬 호출

## 체크리스트
- [ ] API 호출 병렬화 구현
- [ ] 에러 핸들링 추가
- [ ] 로딩 시간 측정 및 검증

## 참고 자료
- 현재 구현: src/pages/profile.tsx""",
                success_metrics="짧은 대화(5-10 메시지), 명확한 티켓 생성, 코드 3-5개",
                tags=["jira", "documentation", "ticket"]
            ),

            # 기술 조사
            PromptTemplate(
                name="technical_research",
                category="조사",
                description="새로운 기술이나 도구를 조사하는 프롬프트. 현재 문제와 해결 방향을 제시합니다.",
                template="""{{problem}}을/를 해결하려고 하는데, {{solution}}을/를 쓰면 된다는 이야기가 있어.

다음 내용을 조사해줘:
1. {{solution}}이 뭔지 (개념, 원리)
2. 우리 상황에 적용 가능한지
3. 장단점 분석
4. 실제 사용 예시 코드
5. 도입 시 주의사항

현재 환경:
{{current_environment}}""",
                variables=["problem", "solution", "current_environment"],
                example="""만단 작업을 효율적으로 처리하려고 하는데, claude squad라는걸 쓰면 된다는 이야기가 있어.

다음 내용을 조사해줘:
1. claude squad가 뭔지 (개념, 원리)
2. 우리 상황에 적용 가능한지
3. 장단점 분석
4. 실제 사용 예시 코드
5. 도입 시 주의사항

현재 환경:
- Claude Code CLI 사용 중
- 복잡한 멀티스텝 작업 빈번
- 여러 파일 동시 수정 필요""",
                success_metrics="명확한 조사 결과, 적용 가능성 판단, 예시 코드 제공",
                tags=["research", "investigation", "technical"]
            ),

            # 환경 구축 검토
            PromptTemplate(
                name="environment_setup_review",
                category="기능 구현",
                description="새로운 개발 환경이나 도구를 도입할 때 사용. 현재 상황과 목표를 명확히 합니다.",
                template="""지금 {{current_situation}}인 상황에서, {{solution}}을/를 써서 {{goal}}을/를 할 수 있는 환경 구축이 가능한지 리뷰 해줘.

목표:
{{detailed_goal}}

현재 제약사항:
{{constraints}}

기대 효과:
{{expected_benefits}}

확인해야 할 사항:
{{checklist}}""",
                variables=["current_situation", "solution", "goal", "detailed_goal", "constraints", "expected_benefits", "checklist"],
                example="""지금 여러 피처를 동시에 개발해야 하는 상황에서, git worktree를 써서 다수의 피처를 한번에 개발할 수 있는 환경 구축이 가능한지 리뷰 해줘.

목표:
- 브랜치 전환 없이 여러 피처 동시 개발
- 빌드 시간 절약

현재 제약사항:
- monorepo 구조 (Nx 사용)
- node_modules 크기 큼 (2GB)

기대 효과:
- 브랜치 전환 시간 제거
- 동시 테스트 가능

확인해야 할 사항:
- node_modules 공유 가능 여부
- IDE 설정 방법
- CI/CD 영향도""",
                success_metrics="실현 가능성 판단, 구체적 설정 방법, 주의사항 제시",
                tags=["environment", "setup", "devops"]
            ),

            # 버그 수정
            PromptTemplate(
                name="bug_fix",
                category="버그 수정",
                description="버그를 수정하는 프롬프트. 현상, 재현 방법, 예상 원인을 제공합니다.",
                template="""다음 버그를 수정해줘:

## 현상
{{symptom}}

## 재현 방법
{{reproduction_steps}}

## 예상 원인
{{expected_cause}}

## 관련 파일
{{related_files}}

## 에러 로그
{{error_logs}}

## 제약사항
{{constraints}}""",
                variables=["symptom", "reproduction_steps", "expected_cause", "related_files", "error_logs", "constraints"],
                example="""다음 버그를 수정해줘:

## 현상
센트리에서 chrome-extension 오류가 여전히 집계됨

## 재현 방법
1. 프로덕션 환경 접속
2. 센트리 대시보드 확인
3. "Cannot redefine property: station" 오류 확인

## 예상 원인
- ignoreErrors 설정이 적용되지 않음
- 소스 매핑 문제로 필터링 실패

## 관련 파일
- sentry.config.ts
- next.config.js

## 에러 로그
```
Error: Cannot redefine property: station
  at chrome-extension://...
```

## 제약사항
- 기존 에러 수집은 유지해야 함
- chrome-extension 관련만 필터링""",
                success_metrics="근본 원인 파악, 수정 코드 제공, 테스트 방법 제시",
                tags=["bug", "fix", "debugging"]
            ),

            # 기능 구현
            PromptTemplate(
                name="feature_implementation",
                category="기능 구현",
                description="새 기능을 구현하는 프롬프트. 요구사항, 예시, 제약사항을 명확히 합니다.",
                template="""{{feature_name}} 기능을 구현해줘.

## 요구사항
{{requirements}}

## 동작 방식
{{behavior}}

## UI/UX
{{ui_ux}}

## 기술 스펙
{{tech_spec}}

## 예시
{{example}}

## 제약사항
{{constraints}}

## 참고 구현
{{reference_implementation}}""",
                variables=["feature_name", "requirements", "behavior", "ui_ux", "tech_spec", "example", "constraints", "reference_implementation"],
                example="""프로필 페이지에 독서노트 탭 추가 기능을 구현해줘.

## 요구사항
- 프로필 페이지에 "독서노트" 탭 추가
- 사용자의 독서노트 목록 표시
- 페이지네이션 적용 (20개씩)

## 동작 방식
1. 탭 클릭 시 독서노트 목록 API 호출
2. 로딩 상태 표시
3. 목록 렌더링
4. 스크롤 시 다음 페이지 로드

## UI/UX
- 기존 탭 스타일과 동일
- 카드형 레이아웃
- 빈 상태 처리

## 기술 스펙
- React 18, TypeScript
- React Query for data fetching
- Tailwind CSS

## 예시
참고: src/domains/profile/components/article-tab.tsx

## 제약사항
- 기존 탭 구조 유지
- SEO 최적화 필요
- 모바일 반응형

## 참고 구현
- ArticleTab 컴포넌트의 구조 참고""",
                success_metrics="완전한 구현, 테스트 가능, 코딩 스타일 일관성",
                tags=["feature", "implementation", "development"]
            ),

            # 코드 리뷰
            PromptTemplate(
                name="code_review",
                category="코드 리뷰",
                description="코드 리뷰를 요청하는 프롬프트. 리뷰 포인트를 명확히 합니다.",
                template="""다음 코드를 리뷰해줘:

## 코드 위치
{{file_paths}}

## 변경 내용
{{changes}}

## 리뷰 포인트
{{review_points}}

## 체크사항
- [ ] 코드 품질 (가독성, 유지보수성)
- [ ] 성능 최적화
- [ ] 에러 핸들링
- [ ] 테스트 커버리지
- [ ] 보안 이슈
- [ ] 베스트 프랙티스

## 특히 확인할 부분
{{specific_concerns}}""",
                variables=["file_paths", "changes", "review_points", "specific_concerns"],
                example="""다음 코드를 리뷰해줘:

## 코드 위치
- src/api/profile.ts
- src/hooks/useProfile.ts

## 변경 내용
- API 호출 병렬화 (Promise.all 적용)
- 에러 핸들링 추가
- 타입 안정성 개선

## 리뷰 포인트
1. Promise.all 사용이 적절한지
2. 에러 핸들링 로직
3. 타입 정의 개선 여부

## 체크사항
- [x] 코드 품질 (가독성, 유지보수성)
- [x] 성능 최적화
- [x] 에러 핸들링
- [ ] 테스트 커버리지
- [ ] 보안 이슈
- [x] 베스트 프랙티스

## 특히 확인할 부분
- Promise.all에서 하나라도 실패하면 전체 실패하는데 괜찮은지
- 에러 타입이 명확한지""",
                success_metrics="구체적 개선사항, 보안/성능 이슈 지적, 대안 제시",
                tags=["review", "code-quality", "refactoring"]
            ),

            # 리팩토링
            PromptTemplate(
                name="refactoring",
                category="리팩토링",
                description="코드 리팩토링을 요청하는 프롬프트. 목적과 제약사항을 명확히 합니다.",
                template="""{{target}}을/를 리팩토링해줘.

## 현재 문제점
{{current_issues}}

## 리팩토링 목표
{{refactoring_goals}}

## 유지해야 할 것
{{keep_behavior}}

## 개선 방향
{{improvement_direction}}

## 제약사항
{{constraints}}

## 테스트
{{test_requirements}}""",
                variables=["target", "current_issues", "refactoring_goals", "keep_behavior", "improvement_direction", "constraints", "test_requirements"],
                example="""src/utils/date-formatter.ts를 리팩토링해줘.

## 현재 문제점
- 중복 코드가 많음 (5개 함수에서 동일 로직 반복)
- 테스트 불가능한 구조 (Date.now() 직접 호출)
- 타입 안정성 부족

## 리팩토링 목표
1. 중복 제거 (DRY 원칙)
2. 테스트 가능한 구조로 변경
3. 타입 안정성 개선
4. 성능 최적화 (불필요한 변환 제거)

## 유지해야 할 것
- 기존 API 시그니처 (하위 호환성)
- 출력 포맷

## 개선 방향
- 공통 로직을 헬퍼 함수로 추출
- 의존성 주입으로 테스트 가능하게
- Zod로 타입 검증 추가

## 제약사항
- 기존 사용처 수정 최소화
- 번들 사이즈 증가 금지

## 테스트
- 모든 엣지 케이스 테스트 추가
- 기존 동작 검증 테스트""",
                success_metrics="코드 품질 개선, 테스트 커버리지 증가, 성능 유지",
                tags=["refactoring", "code-quality", "improvement"]
            ),

            # 테스트 작성
            PromptTemplate(
                name="test_creation",
                category="테스트",
                description="테스트 코드를 작성하는 프롬프트. 테스트 범위와 시나리오를 명확히 합니다.",
                template="""{{target}}에 대한 테스트 코드를 작성해줘.

## 테스트 대상
{{test_target}}

## 테스트 범위
{{test_scope}}

## 테스트 시나리오
{{test_scenarios}}

## 테스트 프레임워크
{{test_framework}}

## 커버리지 목표
{{coverage_goal}}

## 엣지 케이스
{{edge_cases}}""",
                variables=["target", "test_target", "test_scope", "test_scenarios", "test_framework", "coverage_goal", "edge_cases"],
                example="""src/api/profile.ts의 getUserProfile 함수에 대한 테스트 코드를 작성해줘.

## 테스트 대상
- getUserProfile(userId: string): Promise<Profile>

## 테스트 범위
- 정상 케이스
- 에러 케이스
- 엣지 케이스

## 테스트 시나리오
1. 성공: 유효한 userId로 프로필 조회
2. 실패: 존재하지 않는 userId
3. 실패: 네트워크 에러
4. 실패: 타임아웃
5. 캐싱: 같은 userId 반복 호출

## 테스트 프레임워크
- Jest
- React Testing Library
- MSW (API 모킹)

## 커버리지 목표
- 라인 커버리지 90% 이상
- 브랜치 커버리지 85% 이상

## 엣지 케이스
- 빈 문자열 userId
- 특수문자 포함 userId
- 매우 긴 userId""",
                success_metrics="높은 커버리지, 명확한 테스트 케이스, 유지보수 용이",
                tags=["test", "testing", "qa"]
            ),
        ]

    @staticmethod
    def get_template_by_name(name: str) -> PromptTemplate:
        """Get template by name."""
        templates = PromptTemplateLibrary.get_all_templates()
        for template in templates:
            if template.name == name:
                return template
        raise ValueError(f"Template not found: {name}")

    @staticmethod
    def get_templates_by_category(category: str) -> List[PromptTemplate]:
        """Get templates by category."""
        templates = PromptTemplateLibrary.get_all_templates()
        return [t for t in templates if t.category == category]

    @staticmethod
    def get_all_categories() -> List[str]:
        """Get all available categories."""
        templates = PromptTemplateLibrary.get_all_templates()
        return list(set(t.category for t in templates))

    @staticmethod
    def search_templates(keyword: str) -> List[PromptTemplate]:
        """Search templates by keyword."""
        templates = PromptTemplateLibrary.get_all_templates()
        keyword_lower = keyword.lower()
        return [
            t for t in templates
            if keyword_lower in t.name.lower()
            or keyword_lower in t.description.lower()
            or any(keyword_lower in tag for tag in t.tags)
        ]
