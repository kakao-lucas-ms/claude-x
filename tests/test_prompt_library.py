"""Tests for prompt pattern library."""

import pytest
import tempfile
from pathlib import Path

from claude_x.prompt_library import PromptLibrary
from claude_x.patterns import PromptPattern
from claude_x.classifier import PromptCategory


class TestPromptLibrary:
    """Tests for PromptLibrary class."""

    @pytest.fixture
    def temp_library(self):
        """Create a temporary library for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            library_path = Path(tmpdir) / "test_library.json"
            library = PromptLibrary(storage_path=library_path)
            yield library

    def test_add_pattern(self, temp_library):
        """Should add pattern to library."""
        pattern = PromptPattern(
            pattern_type='target_action',
            template='[FILE_NAME]에 [FEATURE] 추가해줘',
            examples=['LoginForm.tsx에 validation 추가해줘'],
            category=PromptCategory.IMPLEMENTATION,
            avg_score=7.5,
            usage_count=1,
            tags={'react', 'create'},
        )

        key = temp_library.add_pattern(pattern)
        assert key is not None

        retrieved = temp_library.get_pattern(key)
        assert retrieved is not None
        assert retrieved.pattern_type == 'target_action'

    def test_add_from_prompt(self, temp_library):
        """Should analyze and add pattern from prompt."""
        prompt = "LoginForm.tsx 컴포넌트에 비밀번호 유효성 검사를 추가해줘. React를 사용중이야."
        key = temp_library.add_from_prompt(prompt, min_quality=0.0)

        assert key is not None
        pattern = temp_library.get_pattern(key)
        assert pattern is not None

    def test_add_from_prompt_quality_filter(self, temp_library):
        """Should not add low quality prompts."""
        prompt = "ok"
        key = temp_library.add_from_prompt(prompt, min_quality=5.0)

        assert key is None

    def test_search_by_category(self, temp_library):
        """Should search patterns by category."""
        # Add patterns with different categories
        for cat in [PromptCategory.IMPLEMENTATION, PromptCategory.DEBUGGING]:
            pattern = PromptPattern(
                pattern_type='generic',
                template='test template',
                category=cat,
                avg_score=5.0,
            )
            temp_library.add_pattern(pattern)

        results = temp_library.search(category=PromptCategory.IMPLEMENTATION)
        assert len(results) == 1
        assert results[0].category == PromptCategory.IMPLEMENTATION

    def test_search_by_tags(self, temp_library):
        """Should search patterns by tags."""
        pattern1 = PromptPattern(
            pattern_type='generic',
            template='test 1',
            tags={'react', 'typescript'},
            avg_score=5.0,
        )
        pattern2 = PromptPattern(
            pattern_type='generic',
            template='test 2',
            tags={'python', 'django'},
            avg_score=5.0,
        )

        temp_library.add_pattern(pattern1)
        temp_library.add_pattern(pattern2)

        results = temp_library.search(tags=['react'])
        assert len(results) == 1
        assert 'react' in results[0].tags

    def test_search_by_min_score(self, temp_library):
        """Should filter by minimum score."""
        for score in [3.0, 5.0, 8.0]:
            pattern = PromptPattern(
                pattern_type='generic',
                template=f'test {score}',
                avg_score=score,
            )
            temp_library.add_pattern(pattern)

        results = temp_library.search(min_score=6.0)
        assert len(results) == 1
        assert results[0].avg_score == 8.0

    def test_get_best_patterns(self, temp_library):
        """Should return best patterns by score."""
        for score in [3.0, 5.0, 8.0]:
            pattern = PromptPattern(
                pattern_type='generic',
                template=f'test {score}',
                avg_score=score,
            )
            temp_library.add_pattern(pattern)

        results = temp_library.get_best_patterns(limit=2)
        assert len(results) == 2  # Two have score >= 5.0 (5.0 and 8.0)
        assert all(p.avg_score >= 5.0 for p in results)

    def test_bulk_import(self, temp_library, high_quality_prompts):
        """Should bulk import patterns from prompts."""
        prompts = [{'first_prompt': p['prompt']} for p in high_quality_prompts[:5]]
        count = temp_library.bulk_import(prompts, min_quality=0.0)

        assert count > 0
        assert len(temp_library.patterns) > 0

    def test_export_to_markdown(self, temp_library):
        """Should export to markdown format."""
        pattern = PromptPattern(
            pattern_type='target_action',
            template='[FILE_NAME]에 [FEATURE] 추가해줘',
            examples=['example prompt'],
            category=PromptCategory.IMPLEMENTATION,
            avg_score=7.5,
            tags={'react'},
        )
        temp_library.add_pattern(pattern)

        md_content = temp_library.export_to_markdown()

        assert '# Prompt Pattern Library' in md_content
        assert 'target_action' in md_content
        assert '7.5' in md_content

    def test_export_to_json(self, temp_library):
        """Should export to JSON format."""
        pattern = PromptPattern(
            pattern_type='target_action',
            template='[FILE_NAME]에 [FEATURE] 추가해줘',
            avg_score=7.5,
        )
        temp_library.add_pattern(pattern)

        json_data = temp_library.export_to_json()

        assert 'version' in json_data
        assert 'patterns' in json_data
        assert len(json_data['patterns']) == 1

    def test_get_stats(self, temp_library):
        """Should return library statistics."""
        for cat in [PromptCategory.IMPLEMENTATION, PromptCategory.DEBUGGING]:
            pattern = PromptPattern(
                pattern_type='generic',
                template='test',
                category=cat,
                avg_score=5.0,
                usage_count=2,
            )
            temp_library.add_pattern(pattern)

        stats = temp_library.get_stats()

        assert stats['total_patterns'] == 2
        assert stats['avg_score'] == 5.0
        assert stats['total_usage'] == 4

    def test_persistence(self):
        """Should persist and reload patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            library_path = Path(tmpdir) / "persist_test.json"

            # Create and save
            library1 = PromptLibrary(storage_path=library_path)
            pattern = PromptPattern(
                pattern_type='target_action',
                template='test template',
                avg_score=7.5,
            )
            key = library1.add_pattern(pattern)

            # Load in new instance
            library2 = PromptLibrary(storage_path=library_path)
            retrieved = library2.get_pattern(key)

            assert retrieved is not None
            assert retrieved.avg_score == 7.5

    def test_clear(self, temp_library):
        """Should clear all patterns."""
        pattern = PromptPattern(
            pattern_type='generic',
            template='test',
            avg_score=5.0,
        )
        temp_library.add_pattern(pattern)
        assert len(temp_library.patterns) == 1

        temp_library.clear()
        assert len(temp_library.patterns) == 0
