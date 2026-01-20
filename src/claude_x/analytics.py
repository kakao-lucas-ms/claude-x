"""Analytics module for prompt usage analysis."""

import json
import csv
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import sqlite3

from .storage import Storage


class PromptAnalytics:
    """Analyze prompt usage patterns."""

    def __init__(self, storage: Storage):
        """Initialize analytics.
        
        Args:
            storage: Storage instance
        """
        self.storage = storage

    def get_category_stats(self, project_name: str = "front") -> List[Dict]:
        """Get statistics by prompt category.
        
        Args:
            project_name: Project name to analyze
            
        Returns:
            List of category statistics
        """
        with self.storage._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    CASE 
                        WHEN lower(s.first_prompt) LIKE '%리뷰%' OR lower(s.first_prompt) LIKE '%review%' THEN '코드 리뷰'
                        WHEN lower(s.first_prompt) LIKE '%테스트%' OR lower(s.first_prompt) LIKE '%test%' THEN '테스트'
                        WHEN lower(s.first_prompt) LIKE '%버그%' OR lower(s.first_prompt) LIKE '%bug%' OR lower(s.first_prompt) LIKE '%fix%' THEN '버그 수정'
                        WHEN lower(s.first_prompt) LIKE '%구현%' OR lower(s.first_prompt) LIKE '%implement%' OR lower(s.first_prompt) LIKE '%add%' THEN '기능 구현'
                        WHEN lower(s.first_prompt) LIKE '%리팩토링%' OR lower(s.first_prompt) LIKE '%refactor%' THEN '리팩토링'
                        WHEN lower(s.first_prompt) LIKE '%문서%' OR lower(s.first_prompt) LIKE '%doc%' THEN '문서화'
                        ELSE '기타'
                    END as category,
                    COUNT(DISTINCT s.session_id) as session_count,
                    COUNT(DISTINCT m.id) as total_messages,
                    COUNT(DISTINCT CASE WHEN m.type = 'user' THEN m.id END) as user_prompts,
                    COUNT(DISTINCT cs.id) as code_count,
                    ROUND(AVG(s.message_count), 1) as avg_messages_per_session,
                    ROUND(CAST(COUNT(DISTINCT cs.id) AS FLOAT) / NULLIF(COUNT(DISTINCT s.session_id), 0), 1) as avg_code_per_session
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                LEFT JOIN messages m ON s.session_id = m.session_id
                LEFT JOIN code_snippets cs ON m.id = cs.message_id
                WHERE p.name = ?
                GROUP BY category
                ORDER BY session_count DESC
            """, (project_name,))
            return [dict(row) for row in cursor.fetchall()]

    def get_branch_productivity(self, project_name: str = "front") -> List[Dict]:
        """Get productivity metrics by branch type.
        
        Args:
            project_name: Project name to analyze
            
        Returns:
            List of branch productivity metrics
        """
        with self.storage._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    CASE 
                        WHEN s.git_branch LIKE 'feature/%' THEN 'Feature'
                        WHEN s.git_branch LIKE 'hotfix/%' THEN 'Hotfix'
                        WHEN s.git_branch = 'dev' THEN 'Dev'
                        WHEN s.git_branch = 'main' OR s.git_branch = 'master' THEN 'Main'
                        ELSE 'Other'
                    END as branch_type,
                    COUNT(DISTINCT s.session_id) as session_count,
                    COUNT(DISTINCT m.id) as total_messages,
                    COUNT(DISTINCT cs.id) as code_count,
                    ROUND(CAST(COUNT(DISTINCT cs.id) AS FLOAT) / NULLIF(COUNT(DISTINCT m.id), 0), 2) as code_per_message_ratio,
                    ROUND(AVG(s.message_count), 1) as avg_messages_per_session
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                LEFT JOIN messages m ON s.session_id = m.session_id
                LEFT JOIN code_snippets cs ON m.id = cs.message_id
                WHERE p.name = ?
                GROUP BY branch_type
                ORDER BY session_count DESC
            """, (project_name,))
            return [dict(row) for row in cursor.fetchall()]

    def get_language_distribution(self, project_name: str = "front") -> List[Dict]:
        """Get code language distribution.
        
        Args:
            project_name: Project name to analyze
            
        Returns:
            List of language statistics
        """
        with self.storage._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    cs.language,
                    COUNT(*) as count,
                    ROUND(CAST(COUNT(*) AS FLOAT) * 100.0 / (
                        SELECT COUNT(*) 
                        FROM code_snippets cs2
                        JOIN sessions s2 ON cs2.session_id = s2.session_id
                        JOIN projects p2 ON s2.project_id = p2.id
                        WHERE p2.name = ?
                    ), 2) as percentage,
                    SUM(cs.line_count) as total_lines
                FROM code_snippets cs
                JOIN sessions s ON cs.session_id = s.session_id
                JOIN projects p ON s.project_id = p.id
                WHERE p.name = ?
                GROUP BY cs.language
                ORDER BY count DESC
                LIMIT 15
            """, (project_name, project_name))
            return [dict(row) for row in cursor.fetchall()]

    def get_time_based_analysis(self, project_name: str = "front", days: int = 30) -> Dict:
        """Get time-based usage analysis.
        
        Args:
            project_name: Project name to analyze
            days: Number of days to analyze
            
        Returns:
            Time-based statistics
        """
        with self.storage._get_connection() as conn:
            # Daily activity
            cursor = conn.execute("""
                SELECT 
                    DATE(s.created_at) as date,
                    COUNT(DISTINCT s.session_id) as sessions,
                    COUNT(DISTINCT m.id) as messages,
                    COUNT(DISTINCT cs.id) as code_snippets
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                LEFT JOIN messages m ON s.session_id = m.session_id
                LEFT JOIN code_snippets cs ON m.id = cs.message_id
                WHERE p.name = ? 
                    AND s.created_at >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(s.created_at)
                ORDER BY date DESC
            """, (project_name, days))
            daily_activity = [dict(row) for row in cursor.fetchall()]

            # Hour distribution
            cursor = conn.execute("""
                SELECT 
                    CAST(strftime('%H', s.created_at) AS INTEGER) as hour,
                    COUNT(DISTINCT s.session_id) as sessions
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                WHERE p.name = ?
                GROUP BY hour
                ORDER BY sessions DESC
            """, (project_name,))
            hour_distribution = [dict(row) for row in cursor.fetchall()]

            # Most productive day
            cursor = conn.execute("""
                SELECT 
                    DATE(s.created_at) as date,
                    COUNT(DISTINCT cs.id) as code_count
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                LEFT JOIN messages m ON s.session_id = m.session_id
                LEFT JOIN code_snippets cs ON m.id = cs.message_id
                WHERE p.name = ?
                GROUP BY DATE(s.created_at)
                ORDER BY code_count DESC
                LIMIT 1
            """, (project_name,))
            most_productive = cursor.fetchone()

            return {
                "daily_activity": daily_activity,
                "hour_distribution": hour_distribution,
                "most_productive_day": dict(most_productive) if most_productive else None
            }

    def get_top_sessions(self, project_name: str = "front", limit: int = 10) -> List[Dict]:
        """Get most active sessions.
        
        Args:
            project_name: Project name to analyze
            limit: Max results
            
        Returns:
            List of top sessions
        """
        with self.storage._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    s.session_id,
                    s.first_prompt,
                    s.git_branch,
                    s.created_at,
                    COUNT(DISTINCT m.id) as message_count,
                    COUNT(DISTINCT cs.id) as code_count,
                    GROUP_CONCAT(DISTINCT cs.language) as languages
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                LEFT JOIN messages m ON s.session_id = m.session_id
                LEFT JOIN code_snippets cs ON m.id = cs.message_id
                WHERE p.name = ?
                GROUP BY s.session_id
                ORDER BY message_count DESC
                LIMIT ?
            """, (project_name, limit))
            return [dict(row) for row in cursor.fetchall()]

    def get_sensitive_data_report(self, project_name: str = "front") -> Dict:
        """Get sensitive data detection report.
        
        Args:
            project_name: Project name to analyze
            
        Returns:
            Sensitive data statistics
        """
        with self.storage._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_snippets,
                    COUNT(CASE WHEN has_sensitive THEN 1 END) as sensitive_count,
                    ROUND(CAST(COUNT(CASE WHEN has_sensitive THEN 1 END) AS FLOAT) * 100.0 / COUNT(*), 2) as sensitive_percentage
                FROM code_snippets cs
                JOIN sessions s ON cs.session_id = s.session_id
                JOIN projects p ON s.project_id = p.id
                WHERE p.name = ?
            """, (project_name,))
            stats = dict(cursor.fetchone())

            # Get sessions with sensitive data
            cursor = conn.execute("""
                SELECT DISTINCT
                    s.session_id,
                    s.first_prompt,
                    s.git_branch,
                    COUNT(DISTINCT cs.id) as sensitive_snippet_count
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                JOIN messages m ON s.session_id = m.session_id
                JOIN code_snippets cs ON m.id = cs.message_id
                WHERE p.name = ? AND cs.has_sensitive = 1
                GROUP BY s.session_id
                ORDER BY sensitive_snippet_count DESC
            """, (project_name,))
            sensitive_sessions = [dict(row) for row in cursor.fetchall()]

            return {
                "statistics": stats,
                "affected_sessions": sensitive_sessions
            }

    def export_to_json(self, data: Dict, output_path: Path):
        """Export analytics data to JSON.
        
        Args:
            data: Data to export
            output_path: Output file path
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def export_to_csv(self, data: List[Dict], output_path: Path):
        """Export analytics data to CSV.
        
        Args:
            data: Data to export (list of dicts)
            output_path: Output file path
        """
        if not data:
            return

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

    def analyze_prompt_quality(self, project_name: str = "front") -> List[Dict]:
        """Analyze prompt quality with scoring.

        Args:
            project_name: Project name to analyze

        Returns:
            List of prompts with quality scores
        """
        with self.storage._get_connection() as conn:
            cursor = conn.execute("""
                WITH session_metrics AS (
                    SELECT
                        s.session_id,
                        s.first_prompt,
                        s.git_branch,
                        s.created_at,
                        COUNT(DISTINCT m.id) as message_count,
                        COUNT(DISTINCT CASE WHEN m.type = 'user' THEN m.id END) as user_prompt_count,
                        COUNT(DISTINCT cs.id) as code_count,
                        SUM(cs.line_count) as total_lines,
                        COUNT(DISTINCT cs.language) as language_diversity,
                        COUNT(DISTINCT CASE WHEN cs.has_sensitive THEN cs.id END) as sensitive_count,
                        CASE
                            WHEN lower(s.first_prompt) LIKE '%리뷰%' OR lower(s.first_prompt) LIKE '%review%' THEN '코드 리뷰'
                            WHEN lower(s.first_prompt) LIKE '%테스트%' OR lower(s.first_prompt) LIKE '%test%' THEN '테스트'
                            WHEN lower(s.first_prompt) LIKE '%버그%' OR lower(s.first_prompt) LIKE '%bug%' OR lower(s.first_prompt) LIKE '%fix%' THEN '버그 수정'
                            WHEN lower(s.first_prompt) LIKE '%구현%' OR lower(s.first_prompt) LIKE '%implement%' OR lower(s.first_prompt) LIKE '%add%' THEN '기능 구현'
                            WHEN lower(s.first_prompt) LIKE '%리팩토링%' OR lower(s.first_prompt) LIKE '%refactor%' THEN '리팩토링'
                            ELSE '기타'
                        END as category
                    FROM sessions s
                    JOIN projects p ON s.project_id = p.id
                    LEFT JOIN messages m ON s.session_id = m.session_id
                    LEFT JOIN code_snippets cs ON m.id = cs.message_id
                    WHERE p.name = ?
                    GROUP BY s.session_id
                    HAVING code_count > 0
                )
                SELECT
                    session_id,
                    first_prompt,
                    git_branch,
                    created_at,
                    category,
                    message_count,
                    user_prompt_count,
                    code_count,
                    total_lines,
                    language_diversity,
                    sensitive_count,
                    -- Efficiency: 코드 생성량 / 사용자 프롬프트 수
                    ROUND(CAST(code_count AS FLOAT) / NULLIF(user_prompt_count, 0), 2) as efficiency_score,
                    -- Clarity: 짧은 대화일수록 명확한 프롬프트 (정규화: 1 / log(messages))
                    ROUND(100.0 / NULLIF(message_count, 0), 2) as clarity_score,
                    -- Productivity: 총 생성 라인 수 (상위 20%면 높은 점수)
                    total_lines as productivity_score,
                    -- Quality: 민감 정보 없고 언어 다양성 높으면 좋음
                    CASE
                        WHEN sensitive_count = 0 AND language_diversity >= 3 THEN 10
                        WHEN sensitive_count = 0 AND language_diversity >= 2 THEN 8
                        WHEN sensitive_count = 0 THEN 6
                        WHEN language_diversity >= 3 THEN 5
                        ELSE 3
                    END as quality_score
                FROM session_metrics
            """, (project_name,))

            results = [dict(row) for row in cursor.fetchall()]

            # Calculate composite score (weighted average)
            for r in results:
                # Normalize productivity score (0-10 scale)
                max_lines = max([x['total_lines'] or 0 for x in results])
                normalized_productivity = (r['productivity_score'] or 0) / max(max_lines, 1) * 10

                # Composite score: efficiency 40%, clarity 30%, productivity 20%, quality 10%
                r['composite_score'] = round(
                    (r['efficiency_score'] or 0) * 0.4 +
                    (r['clarity_score'] or 0) * 0.3 +
                    normalized_productivity * 0.2 +
                    r['quality_score'] * 0.1,
                    2
                )

            return sorted(results, key=lambda x: x['composite_score'], reverse=True)

    def get_best_prompts(self, project_name: str = "front", limit: int = 10) -> List[Dict]:
        """Get best performing prompts.

        Args:
            project_name: Project name to analyze
            limit: Number of top prompts

        Returns:
            List of best prompts with scores
        """
        all_prompts = self.analyze_prompt_quality(project_name)
        return all_prompts[:limit]

    def get_worst_prompts(self, project_name: str = "front", limit: int = 10) -> List[Dict]:
        """Get worst performing prompts.

        Args:
            project_name: Project name to analyze
            limit: Number of bottom prompts

        Returns:
            List of worst prompts with scores
        """
        all_prompts = self.analyze_prompt_quality(project_name)
        return all_prompts[-limit:][::-1]  # Reverse to show worst first

    def export_prompt_library(self, project_name: str = "front", output_path: Path = None):
        """Export prompt library as markdown.

        Args:
            project_name: Project name to analyze
            output_path: Output file path
        """
        if output_path is None:
            output_path = Path.home() / ".claude-x" / "prompt-library" / f"{project_name}-prompts.md"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        best = self.get_best_prompts(project_name, 15)
        worst = self.get_worst_prompts(project_name, 10)

        # Group by category
        by_category = {}
        for prompt in best:
            cat = prompt['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(prompt)

        lines = [
            f"# 프롬프트 라이브러리: {project_name}",
            f"",
            f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"총 분석 프롬프트: {len(self.analyze_prompt_quality(project_name))}개",
            f"",
            "---",
            "",
            "## 📊 점수 계산 방식",
            "",
            "각 프롬프트는 다음 4가지 지표로 평가됩니다:",
            "",
            "- **효율성 (40%)**: 코드 생성량 / 프롬프트 수",
            "- **명확성 (30%)**: 짧은 대화로 목표 달성 (메시지 수의 역수)",
            "- **생산성 (20%)**: 총 생성 코드 라인 수",
            "- **품질 (10%)**: 민감 정보 없음 + 언어 다양성",
            "",
            "**종합 점수 = 효율성×0.4 + 명확성×0.3 + 생산성×0.2 + 품질×0.1**",
            "",
            "---",
            "",
            "## 🏆 베스트 프롬프트 (Top 15)",
            "",
            "성공적인 프롬프트 패턴을 학습하세요.",
            ""
        ]

        for i, prompt in enumerate(best, 1):
            lines.extend([
                f"### {i}. {prompt['category']} (점수: {prompt['composite_score']})",
                f"",
                f"**프롬프트:**",
                f"> {prompt['first_prompt'][:200]}{'...' if len(prompt['first_prompt']) > 200 else ''}",
                f"",
                f"**세션 정보:**",
                f"- 세션 ID: `{prompt['session_id'][:16]}...`",
                f"- 브랜치: `{prompt['git_branch'] or 'N/A'}`",
                f"- 날짜: {prompt['created_at'][:10] if prompt['created_at'] else 'N/A'}",
                f"",
                f"**성과 지표:**",
                f"- 총 메시지: {prompt['message_count']}개",
                f"- 사용자 프롬프트: {prompt['user_prompt_count']}개",
                f"- 생성 코드: {prompt['code_count']}개 ({prompt['total_lines']}줄)",
                f"- 사용 언어: {prompt['language_diversity']}종류",
                f"",
                f"**점수 분석:**",
                f"- 효율성: {prompt['efficiency_score']} (코드/프롬프트)",
                f"- 명확성: {prompt['clarity_score']}",
                f"- 생산성: {prompt['total_lines']}줄",
                f"- 품질: {prompt['quality_score']}/10",
                f"",
                "---",
                ""
            ])

        lines.extend([
            "",
            "## 📚 카테고리별 베스트 프롬프트",
            ""
        ])

        for category, prompts in sorted(by_category.items()):
            lines.extend([
                f"### {category}",
                ""
            ])
            for p in prompts[:3]:  # Top 3 per category
                lines.extend([
                    f"- **점수 {p['composite_score']}**: {p['first_prompt'][:100]}...",
                    f"  - 💻 코드 {p['code_count']}개, 📝 {p['total_lines']}줄, 💬 메시지 {p['message_count']}개",
                    ""
                ])
            lines.append("")

        lines.extend([
            "## ⚠️ 개선이 필요한 프롬프트 (Bottom 10)",
            "",
            "다음 패턴은 피하는 것이 좋습니다.",
            ""
        ])

        for i, prompt in enumerate(worst, 1):
            lines.extend([
                f"### {i}. {prompt['category']} (점수: {prompt['composite_score']})",
                f"",
                f"**프롬프트:**",
                f"> {prompt['first_prompt'][:200]}{'...' if len(prompt['first_prompt']) > 200 else ''}",
                f"",
                f"**문제점:**",
            ])

            issues = []
            if prompt['efficiency_score'] < 1:
                issues.append("- 낮은 효율성: 프롬프트당 생성된 코드가 적음")
            if prompt['message_count'] > 100:
                issues.append("- 긴 대화: 명확하지 않은 지시로 많은 대화 필요")
            if prompt['sensitive_count'] > 0:
                issues.append(f"- 보안 이슈: 민감 정보 {prompt['sensitive_count']}건 발견")
            if prompt['language_diversity'] < 2:
                issues.append("- 제한적인 산출물: 단일 언어만 사용")

            if not issues:
                issues.append("- 전반적으로 낮은 성과 지표")

            lines.extend(issues)
            lines.extend([
                f"",
                f"**개선 방향:**",
                f"- 더 구체적인 요구사항 명시",
                f"- 예상 결과물 형태 제시",
                f"- 단계별로 작업 분리",
                "",
                "---",
                ""
            ])

        lines.extend([
            "",
            "## 💡 프롬프트 작성 팁",
            "",
            "베스트 프롬프트 분석 결과를 바탕으로 한 권장사항:",
            "",
            "1. **명확한 목표 설정**: 무엇을 만들고 싶은지 구체적으로 명시",
            "2. **컨텍스트 제공**: 현재 상황과 배경 설명",
            "3. **예시 제공**: 원하는 결과물의 예시나 참고 자료",
            "4. **제약사항 명시**: 지켜야 할 규칙이나 제한사항",
            "5. **단계적 접근**: 큰 작업은 작은 단위로 분리",
            "",
            "---",
            "",
            f"📝 이 문서는 `cx prompts --project {project_name} --export` 명령으로 생성되었습니다.",
            ""
        ])

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return output_path

    def generate_full_report(self, project_name: str = "front") -> Dict:
        """Generate comprehensive analytics report.

        Args:
            project_name: Project name to analyze

        Returns:
            Complete analytics report
        """
        return {
            "project": project_name,
            "generated_at": datetime.now().isoformat(),
            "category_stats": self.get_category_stats(project_name),
            "branch_productivity": self.get_branch_productivity(project_name),
            "language_distribution": self.get_language_distribution(project_name),
            "time_analysis": self.get_time_based_analysis(project_name),
            "top_sessions": self.get_top_sessions(project_name),
            "sensitive_data": self.get_sensitive_data_report(project_name)
        }
