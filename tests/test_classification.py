"""
Tests for memory scope classification heuristics.

Tests the _classify_memory_scope() function that determines whether
memories should be stored globally or locally.
"""

import pytest
from claude_memory.memory import _classify_memory_scope


class TestMemoryClassification:
    """Test suite for memory scope classification."""

    def test_file_path_forces_local(self):
        """Memories with file paths should always be local."""
        scope = _classify_memory_scope(
            category="pattern",
            content="Always use async/await for I/O operations",
            rationale="Better performance",
            file_path="/project/src/api.py",  # Strong local signal
            tags=["best-practice"],
            project_path="/project"
        )
        assert scope == "local"

    def test_project_specific_language_local(self):
        """Project-specific language should classify as local."""
        # Test various project-specific patterns
        test_cases = [
            "In this repo, we use JWT for authentication",
            "Our codebase follows the MVC pattern",
            "This project uses src/ for source files",
            "For this application, configure the API key",
            "Our team decided to use PostgreSQL",
            "In our service, implement rate limiting",
        ]

        for content in test_cases:
            scope = _classify_memory_scope(
                category="pattern",
                content=content,
                rationale=None,
                file_path=None,
                tags=None,
                project_path="/project"
            )
            assert scope == "local", f"Failed for: {content}"

    def test_universal_patterns_global(self):
        """Universal best practices should classify as global."""
        test_cases = [
            {
                "content": "Always validate user input to prevent XSS attacks",
                "tags": ["security", "best-practice"]
            },
            {
                "content": "Never store passwords in plain text",
                "tags": ["security"]
            },
            {
                "content": "In Python, use context managers for file operations",
                "tags": ["best-practice"]
            },
            {
                "content": "Avoid premature optimization without profiling",
                "tags": ["performance", "best-practice"]
            },
        ]

        for case in test_cases:
            scope = _classify_memory_scope(
                category="pattern",
                content=case["content"],
                rationale=None,
                file_path=None,
                tags=case["tags"],
                project_path="/project"
            )
            assert scope == "global", f"Failed for: {case['content']}"

    def test_warnings_with_global_language(self):
        """Warnings with universal language should be global."""
        scope = _classify_memory_scope(
            category="warning",
            content="Avoid using == for floating point comparisons",
            rationale="Precision issues can cause bugs",
            file_path=None,
            tags=["general", "anti-pattern"],
            project_path="/project"
        )
        assert scope == "global"

    def test_decisions_default_local(self):
        """Decisions without clear global signals default to local."""
        scope = _classify_memory_scope(
            category="decision",
            content="Use Redis for caching",
            rationale="Fast in-memory storage",
            file_path=None,
            tags=None,
            project_path="/project"
        )
        assert scope == "local"

    def test_learning_default_local(self):
        """Learnings default to local unless clearly universal."""
        scope = _classify_memory_scope(
            category="learning",
            content="The API rate limit is 100 req/min",
            rationale=None,
            file_path=None,
            tags=None,
            project_path="/project"
        )
        assert scope == "local"

    def test_global_tags_influence_classification(self):
        """Global tags should influence classification."""
        scope = _classify_memory_scope(
            category="pattern",
            content="Use dependency injection for better testability",
            rationale=None,
            file_path=None,
            tags=["architecture", "design-pattern"],  # Global tags
            project_path="/project"
        )
        assert scope == "global"

    def test_mixed_signals_defaults_local(self):
        """When signals are mixed, default to local (safer)."""
        scope = _classify_memory_scope(
            category="pattern",
            content="Always use type hints",  # Global language
            rationale="Important for this codebase",  # Local language
            file_path=None,
            tags=None,
            project_path="/project"
        )
        # Rationale has project-specific language
        assert scope == "local"

    def test_language_specific_patterns_global(self):
        """Language-specific patterns should be global."""
        test_cases = [
            "In JavaScript, use const by default",
            "In Rust, prefer owned types over references when possible",
            "In Go, use defer for cleanup operations",
            "In TypeScript, leverage union types for better type safety",
        ]

        for content in test_cases:
            scope = _classify_memory_scope(
                category="pattern",
                content=content,
                rationale=None,
                file_path=None,
                tags=["best-practice"],
                project_path="/project"
            )
            assert scope == "global", f"Failed for: {content}"

    def test_empty_content_defaults_local(self):
        """Edge case: empty or minimal content defaults to local."""
        scope = _classify_memory_scope(
            category="pattern",
            content="",
            rationale=None,
            file_path=None,
            tags=None,
            project_path="/project"
        )
        assert scope == "local"

    def test_pr_ticket_references_local(self):
        """References to PRs, issues, tickets should be local."""
        test_cases = [
            "Fixed in PR #123",
            "See ticket #456 for details",
            "Resolved issue #789",
            "Bug report: bug #42",
        ]

        for content in test_cases:
            scope = _classify_memory_scope(
                category="decision",
                content=content,
                rationale=None,
                file_path=None,
                tags=None,
                project_path="/project"
            )
            assert scope == "local", f"Failed for: {content}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
