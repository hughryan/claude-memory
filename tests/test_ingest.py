"""Tests for document ingestion hardening."""

import pytest
from unittest.mock import patch, MagicMock


class TestIngestDocHardening:
    """Test ingestion security and limits."""

    @pytest.mark.asyncio
    async def test_rejects_non_http_schemes(self):
        """Verify that file://, ftp://, etc. are rejected."""
        from daem0nmcp.server import ingest_doc

        # These should all be rejected
        bad_urls = [
            "file:///etc/passwd",
            "ftp://example.com/file.txt",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
        ]

        for url in bad_urls:
            result = await ingest_doc(
                url=url,
                topic="test",
                project_path="C:\\Users\\dasbl\\PycharmProjects\\Daem0n-MCP"
            )
            assert "error" in result, f"Should reject {url}"
            assert "scheme" in result["error"].lower() or "invalid" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_enforces_content_size_limit(self):
        """Verify large responses are truncated."""
        from daem0nmcp.server import _fetch_and_extract, MAX_CONTENT_SIZE

        # Mock a response that's too large
        with patch('httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.text = "x" * (MAX_CONTENT_SIZE + 1000)
            mock_response.raise_for_status = MagicMock()
            mock_response.headers.get = MagicMock(return_value=None)
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = _fetch_and_extract("https://example.com/large")

            # Should be truncated or return None
            assert result is None or len(result) <= MAX_CONTENT_SIZE

    @pytest.mark.asyncio
    async def test_enforces_chunk_limit(self):
        """Verify total chunks are limited."""
        from daem0nmcp.server import ingest_doc, MAX_CHUNKS

        with patch('daem0nmcp.server._fetch_and_extract') as mock_fetch:
            # Return content that would create many chunks
            mock_fetch.return_value = "word " * 100000  # Lots of words

            result = await ingest_doc(
                url="https://example.com/huge",
                topic="test",
                chunk_size=100,
                project_path="C:\\Users\\dasbl\\PycharmProjects\\Daem0n-MCP"
            )

            if "error" not in result:
                assert result["chunks_created"] <= MAX_CHUNKS

    @pytest.mark.asyncio
    async def test_rejects_ssrf_urls(self):
        """Verify SSRF protection blocks localhost and private IPs."""
        from daem0nmcp.server import ingest_doc

        ssrf_urls = [
            "http://localhost/admin",
            "http://127.0.0.1/",
            "http://localhost.localdomain/",
            "http://169.254.169.254/",  # AWS metadata endpoint
        ]

        for url in ssrf_urls:
            result = await ingest_doc(
                url=url,
                topic="test",
                project_path="C:\\Users\\dasbl\\PycharmProjects\\Daem0n-MCP"
            )
            assert "error" in result, f"Should reject {url}: {result}"
            error_msg = result["error"].lower()
            assert any(term in error_msg for term in [
                "localhost", "private", "internal", "metadata", "not allowed"
            ]), f"Error message should mention security issue: {result['error']}"

    @pytest.mark.asyncio
    async def test_validates_chunk_size(self):
        """Verify chunk_size is validated."""
        from daem0nmcp.server import ingest_doc

        # Test negative chunk_size
        result = await ingest_doc(
            url="https://example.com",
            topic="test",
            chunk_size=-1,
            project_path="C:\\Users\\dasbl\\PycharmProjects\\Daem0n-MCP"
        )
        assert "error" in result
        assert "positive" in result["error"].lower()

        # Test zero chunk_size
        result = await ingest_doc(
            url="https://example.com",
            topic="test",
            chunk_size=0,
            project_path="C:\\Users\\dasbl\\PycharmProjects\\Daem0n-MCP"
        )
        assert "error" in result
        assert "positive" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_validates_topic(self):
        """Verify topic is validated."""
        from daem0nmcp.server import ingest_doc

        # Test empty topic
        result = await ingest_doc(
            url="https://example.com",
            topic="",
            project_path="C:\\Users\\dasbl\\PycharmProjects\\Daem0n-MCP"
        )
        assert "error" in result
        assert "empty" in result["error"].lower()

        # Test whitespace-only topic
        result = await ingest_doc(
            url="https://example.com",
            topic="   ",
            project_path="C:\\Users\\dasbl\\PycharmProjects\\Daem0n-MCP"
        )
        assert "error" in result
        assert "empty" in result["error"].lower()
