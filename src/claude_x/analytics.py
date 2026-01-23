"""Analytics module for prompt usage analysis."""

import json
import csv
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import sqlite3

from .storage import Storage
from .filters import filter_prompts, is_system_message, is_likely_system_message, extract_real_prompt
from .classifier import classify_prompt, classify_prompt_with_scores, get_category_icon, PromptCategory, legacy_to_new_category
from .scoring import calculate_composite_score_v2


class PromptAnalytics:
    """Analyze prompt usage patterns."""

    def __init__(self, storage: Storage):
        """Initialize analytics.

        Args:
            storage: Storage instance
        """
        self.storage = storage

    def _resolve_project_name(self, project_name: Optional[str]) -> Optional[str]:
        """Resolve project name if None by selecting most recent project.

        Args:
            project_name: Project name or None

        Returns:
            Resolved project name or None if no projects exist
        """
        if project_name is not None:
            return project_name

        # Get most recent project
        with self.storage._get_connection() as conn:
            cursor = conn.execute("""
                SELECT p.name
                FROM projects p
                JOIN sessions s ON p.id = s.project_id
                ORDER BY s.modified_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            return row[0] if row else None

    def get_category_stats(self, project_name: Optional[str] = None) -> List[Dict]:
        """Get statistics by prompt category.

        Args:
            project_name: Project name to analyze

        Returns:
            List of category statistics
        """
        # Resolve project name if None
        project_name = self._resolve_project_name(project_name)
        if not project_name:
            return []  # No projects exist

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

    def get_branch_productivity(self, project_name: Optional[str] = None) -> List[Dict]:
        """Get productivity metrics by branch type.

        Args:
            project_name: Project name to analyze

        Returns:
            List of branch productivity metrics
        """
        # Resolve project name if None
        project_name = self._resolve_project_name(project_name)
        if not project_name:
            return []  # No projects exist

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

    def get_language_distribution(self, project_name: Optional[str] = None) -> List[Dict]:
        """Get code language distribution.

        Args:
            project_name: Project name to analyze

        Returns:
            List of language statistics
        """
        # Resolve project name if None
        project_name = self._resolve_project_name(project_name)
        if not project_name:
            return []  # No projects exist

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

    def get_time_based_analysis(self, project_name: Optional[str] = None, days: int = 30) -> Dict:
        """Get time-based usage analysis.

        Args:
            project_name: Project name to analyze
            days: Number of days to analyze

        Returns:
            Time-based statistics
        """
        # Resolve project name if None
        project_name = self._resolve_project_name(project_name)
        if not project_name:
            return {"daily_activity": [], "hourly_distribution": []}  # No projects exist

        with self.storage._get_connection() as conn:
            # Daily activity (convert UTC to KST/UTC+9)
            cursor = conn.execute("""
                SELECT
                    DATE(datetime(s.created_at, '+9 hours')) as date,
                    COUNT(DISTINCT s.session_id) as sessions,
                    COUNT(DISTINCT m.id) as messages,
                    COUNT(DISTINCT cs.id) as code_snippets
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                LEFT JOIN messages m ON s.session_id = m.session_id
                LEFT JOIN code_snippets cs ON m.id = cs.message_id
                WHERE p.name = ?
                    AND datetime(s.created_at, '+9 hours') >= datetime('now', '+9 hours', '-' || ? || ' days')
                GROUP BY DATE(datetime(s.created_at, '+9 hours'))
                ORDER BY date DESC
            """, (project_name, days))
            daily_activity = [dict(row) for row in cursor.fetchall()]

            # Hour distribution (convert UTC to KST/UTC+9)
            cursor = conn.execute("""
                SELECT
                    CAST(strftime('%H', datetime(s.created_at, '+9 hours')) AS INTEGER) as hour,
                    COUNT(DISTINCT s.session_id) as sessions
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                WHERE p.name = ?
                GROUP BY hour
                ORDER BY sessions DESC
            """, (project_name,))
            hour_distribution = [dict(row) for row in cursor.fetchall()]

            # Most productive day (convert UTC to KST/UTC+9)
            cursor = conn.execute("""
                SELECT
                    DATE(datetime(s.created_at, '+9 hours')) as date,
                    COUNT(DISTINCT cs.id) as code_count
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                LEFT JOIN messages m ON s.session_id = m.session_id
                LEFT JOIN code_snippets cs ON m.id = cs.message_id
                WHERE p.name = ?
                GROUP BY DATE(datetime(s.created_at, '+9 hours'))
                ORDER BY code_count DESC
                LIMIT 1
            """, (project_name,))
            most_productive = cursor.fetchone()

            return {
                "daily_activity": daily_activity,
                "hour_distribution": hour_distribution,
                "most_productive_day": dict(most_productive) if most_productive else None
            }

    def get_top_sessions(self, project_name: Optional[str] = None, limit: int = 10) -> List[Dict]:
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

    def get_sensitive_data_report(self, project_name: Optional[str] = None) -> Dict:
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

    def analyze_prompt_quality(
        self,
        project_name: Optional[str] = None,
        include_nocode: bool = False,
        include_commands: bool = False,
        filter_system: bool = True
    ) -> List[Dict]:
        """Analyze prompt quality with scoring.

        Args:
            project_name: Project name to analyze
            include_nocode: Include prompts without code generation
            include_commands: Include command-only prompts
            filter_system: Filter out system/meta messages (default: True)

        Returns:
            List of prompts with quality scores
        """
        # Resolve project name if None
        project_name = self._resolve_project_name(project_name)
        if not project_name:
            return []  # No projects exist

        with self.storage._get_connection() as conn:
            query = """
                WITH user_prompts AS (
                    SELECT
                        m.id as message_id,
                        m.session_id,
                        m.content as prompt_text,
                        m.timestamp as prompt_ts,
                        s.git_branch,
                        s.created_at,
                        LEAD(m.timestamp) OVER (
                            PARTITION BY m.session_id
                            ORDER BY m.timestamp
                        ) as next_user_ts
                    FROM messages m
                    JOIN sessions s ON m.session_id = s.session_id
                    JOIN projects p ON s.project_id = p.id
                    WHERE p.name = ? AND m.type = 'user'
                ),
                turn_messages AS (
                    SELECT
                        up.message_id,
                        up.session_id,
                        up.prompt_text,
                        up.git_branch,
                        up.created_at,
                        m.id as msg_id,
                        m.type,
                        m.timestamp
                    FROM user_prompts up
                    JOIN messages m ON m.session_id = up.session_id
                    WHERE m.timestamp >= up.prompt_ts
                      AND (up.next_user_ts IS NULL OR m.timestamp < up.next_user_ts)
                ),
                turn_stats AS (
                    SELECT
                        tm.message_id as message_id,
                        tm.session_id,
                        tm.prompt_text,
                        tm.git_branch,
                        tm.created_at,
                        COUNT(DISTINCT msg_id) as message_count,
                        COUNT(DISTINCT CASE WHEN type = 'user' THEN msg_id END) as user_prompt_count,
                        COUNT(DISTINCT cs.id) as code_count,
                        SUM(cs.line_count) as total_lines,
                        COUNT(DISTINCT cs.language) as language_diversity,
                        COUNT(DISTINCT CASE WHEN cs.has_sensitive THEN cs.id END) as sensitive_count
                    FROM turn_messages tm
                    LEFT JOIN code_snippets cs ON cs.message_id = tm.msg_id
                    GROUP BY tm.message_id
                    {having_clause}
                ),
                prompt_metrics AS (
                    SELECT
                        ts.message_id,
                        ts.session_id,
                        ts.prompt_text,
                        ts.git_branch,
                        ts.created_at,
                        message_count,
                        user_prompt_count,
                        code_count,
                        total_lines,
                        language_diversity,
                        sensitive_count,
                        CASE
                            WHEN lower(prompt_text) LIKE '%리뷰%' OR lower(prompt_text) LIKE '%review%' THEN '코드 리뷰'
                            WHEN lower(prompt_text) LIKE '%테스트%' OR lower(prompt_text) LIKE '%test%' THEN '테스트'
                            WHEN lower(prompt_text) LIKE '%버그%' OR lower(prompt_text) LIKE '%bug%' OR lower(prompt_text) LIKE '%fix%' THEN '버그 수정'
                            WHEN lower(prompt_text) LIKE '%구현%' OR lower(prompt_text) LIKE '%implement%' OR lower(prompt_text) LIKE '%add%' THEN '기능 구현'
                            WHEN lower(prompt_text) LIKE '%리팩토링%' OR lower(prompt_text) LIKE '%refactor%' THEN '리팩토링'
                            ELSE '기타'
                        END as category
                    FROM turn_stats ts
                )
                SELECT
                    message_id,
                    session_id,
                    prompt_text as first_prompt,
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
                    -- Clarity: 짧은 대화일수록 명확한 프롬프트
                    ROUND(100.0 / NULLIF(message_count, 0), 2) as clarity_score,
                    -- Productivity: 총 생성 라인 수
                    total_lines as productivity_score,
                    -- Quality: 민감 정보 없고 언어 다양성 높으면 좋음
                    CASE
                        WHEN sensitive_count = 0 AND language_diversity >= 3 THEN 10
                        WHEN sensitive_count = 0 AND language_diversity >= 2 THEN 8
                        WHEN sensitive_count = 0 THEN 6
                        WHEN language_diversity >= 3 THEN 5
                        ELSE 3
                    END as quality_score
                FROM prompt_metrics
            """

            having_clause = "HAVING code_count > 0" if not include_nocode else ""
            query = query.format(having_clause=having_clause)

            cursor = conn.execute(query, (project_name,))

            results = [dict(row) for row in cursor.fetchall()]

            cleaned_results = []
            for r in results:
                prompt_text = r.get("first_prompt", "")

                # Try to extract real prompt from command args
                extracted_prompt = self._extract_command_args(prompt_text)
                if extracted_prompt:
                    r["first_prompt"] = extracted_prompt
                    prompt_text = extracted_prompt

                # Filter system/meta messages
                if filter_system:
                    if is_system_message(prompt_text):
                        continue
                    if is_likely_system_message(prompt_text):
                        continue

                # Filter command-only messages
                if not include_commands and self._is_command_only(r.get("first_prompt")):
                    continue

                # Skip empty prompts
                if not r.get("first_prompt"):
                    continue

                cleaned_results.append(r)

            if not cleaned_results:
                return []

            max_lines = max([x['total_lines'] or 0 for x in cleaned_results])

            # Calculate composite score and classification for each result
            for r in cleaned_results:
                prompt_text = r.get('first_prompt', '')

                # New category classification
                new_category = classify_prompt(prompt_text)
                r['category'] = new_category.value
                r['category_icon'] = get_category_icon(new_category)

                # New scoring model (v2)
                v2_scores = calculate_composite_score_v2(
                    prompt=prompt_text,
                    code_count=r.get('code_count', 0) or 0,
                    total_lines=r.get('total_lines', 0) or 0,
                    message_count=r.get('message_count', 0) or 0,
                    language_diversity=r.get('language_diversity', 0) or 0,
                    max_lines=max_lines,
                )
                r['structure_score'] = v2_scores['structure_score']
                r['context_score'] = v2_scores['context_score']
                r['efficiency_score_v2'] = v2_scores['efficiency_score']
                r['diversity_score'] = v2_scores['diversity_score']
                r['productivity_score_v2'] = v2_scores['productivity_score']
                r['composite_score_v2'] = v2_scores['composite_score']

                # Legacy scoring (for backwards compatibility)
                normalized_productivity = (r['productivity_score'] or 0) / max(max_lines, 1) * 10
                r['composite_score'] = round(
                    (r['efficiency_score'] or 0) * 0.4 +
                    (r['clarity_score'] or 0) * 0.3 +
                    normalized_productivity * 0.2 +
                    r['quality_score'] * 0.1,
                    2
                )

            return sorted(cleaned_results, key=lambda x: x['composite_score_v2'], reverse=True)

    def _extract_command_args(self, prompt_text: Optional[str]) -> Optional[str]:
        if not prompt_text:
            return None

        start = prompt_text.find("<command-args>")
        if start == -1:
            return None

        start += len("<command-args>")
        end = prompt_text.find("</command-args>", start)
        if end == -1:
            return None

        args = prompt_text[start:end].strip()
        if not args:
            return None

        if args.startswith('"') and args.endswith('"') and len(args) >= 2:
            args = args[1:-1].strip()

        return args or None

    def _is_command_only(self, prompt_text: Optional[str]) -> bool:
        if not prompt_text:
            return True

        if "<command-name>" not in prompt_text and "<command-message>" not in prompt_text:
            return False

        extracted = self._extract_command_args(prompt_text)
        return not extracted

    def get_best_prompts(
        self,
        project_name: Optional[str] = None,
        limit: int = 10,
        include_nocode: bool = False,
        include_commands: bool = False,
        filter_system: bool = True,
        min_structure: float = 2.0,
        min_context: float = 0.0,
        min_quality: Optional[float] = None,
        strict_mode: bool = False
    ) -> List[Dict]:
        """Get best performing prompts.

        Args:
            project_name: Project name to analyze
            limit: Number of top prompts
            include_nocode: Include prompts without code generation
            include_commands: Include command-only prompts
            filter_system: Filter out system/meta messages (default: True)
            min_structure: Minimum structure score (default: 2.0)
            min_context: Minimum context score (default: 0.0)
            min_quality: Minimum combined structure+context score (overrides individual mins)
            strict_mode: If True, use stricter thresholds (structure>=3.0, context>=2.0)

        Returns:
            List of best prompts with scores
        """
        all_prompts = self.analyze_prompt_quality(
            project_name,
            include_nocode=include_nocode,
            include_commands=include_commands,
            filter_system=filter_system
        )

        # Apply strict mode thresholds
        if strict_mode:
            min_structure = 3.0
            min_context = 2.0

        # Filter by quality thresholds
        filtered_prompts = []
        for p in all_prompts:
            structure = p.get('structure_score', 0)
            context = p.get('context_score', 0)

            # Check min_quality (combined threshold)
            if min_quality is not None:
                if structure + context < min_quality:
                    continue
            else:
                # Check individual thresholds
                if structure < min_structure:
                    continue
                if context < min_context:
                    continue

            filtered_prompts.append(p)

        return filtered_prompts[:limit]

    def get_worst_prompts(
        self,
        project_name: Optional[str] = None,
        limit: int = 10,
        include_nocode: bool = False,
        include_commands: bool = False,
        filter_system: bool = True
    ) -> List[Dict]:
        """Get worst performing prompts.

        Args:
            project_name: Project name to analyze
            limit: Number of bottom prompts
            include_nocode: Include prompts without code generation
            include_commands: Include command-only prompts
            filter_system: Filter out system/meta messages (default: True)

        Returns:
            List of worst prompts with scores
        """
        all_prompts = self.analyze_prompt_quality(
            project_name,
            include_nocode=include_nocode,
            include_commands=include_commands,
            filter_system=filter_system
        )
        return all_prompts[-limit:][::-1]  # Reverse to show worst first

    def export_prompt_library(self, project_name: Optional[str] = None, output_path: Optional[Path] = None):
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

    def generate_full_report(self, project_name: Optional[str] = None) -> Dict:
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
