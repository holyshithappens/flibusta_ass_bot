"""
Tests for OpenRouterClient.

This module contains comprehensive tests for the OpenRouterClient class,
including unit tests, integration tests, and edge case handling.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

import pytest
from aiohttp import ClientResponseError, ClientError
from aioresponses import aioresponses

from src.bot.clients.openrouter_client import OpenRouterClient
from src.bot.core.types import OpenRouterRequest


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_api_key() -> str:
    """Mock API key for testing."""
    return "test-api-key-123"


@pytest.fixture
def mock_model() -> str:
    """Mock model identifier for testing."""
    return "test-model-v1"


@pytest.fixture
def mock_messages() -> list:
    """Mock messages for testing."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ]


@pytest.fixture
def mock_api_response() -> dict:
    """Mock successful API response."""
    return {
        "choices": [
            {"message": {"role": "assistant", "content": "Hello! How can I help you?"}}
        ],
        "model": "test-model-v1",
        "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
    }


@pytest.fixture
async def client(mock_api_key: str, mock_model: str) -> OpenRouterClient:
    """Create and start a test client."""
    client = OpenRouterClient(api_key=mock_api_key, model=mock_model, enable_caching=False)
    await client.start()
    yield client
    await client.close()


# ============================================================================
# Unit Tests - Client Initialization
# ============================================================================


class TestClientInitialization:
    """Tests for client initialization and configuration."""

    def test_init_with_default_values(self, mock_api_key: str):
        """Test client initialization with default values."""
        client = OpenRouterClient(api_key=mock_api_key)

        assert client.api_key == mock_api_key
        assert client.model == "nex-agi/deepseek-v3.1-nex-n1:free"
        assert client.timeout == 30
        assert client.enable_caching is True
        assert client.cache_ttl == 3600
        assert client.max_retries == 3
        assert client.retry_delay == 2
        assert client._session is None
        assert not client.is_started

    def test_init_with_custom_values(self, mock_api_key: str, mock_model: str):
        """Test client initialization with custom values."""
        client = OpenRouterClient(
            api_key=mock_api_key,
            model=mock_model,
            timeout=60,
            enable_caching=False,
            cache_ttl=1800,
            max_retries=5,
            retry_delay=1,
        )

        assert client.api_key == mock_api_key
        assert client.model == mock_model
        assert client.timeout == 60
        assert client.enable_caching is False
        assert client.cache_ttl == 1800
        assert client.max_retries == 5
        assert client.retry_delay == 1

    async def test_start_client(self, mock_api_key: str, mock_model: str):
        """Test starting the client."""
        client = OpenRouterClient(api_key=mock_api_key, model=mock_model)
        assert not client.is_started

        await client.start()
        assert client.is_started
        assert client._session is not None

        await client.close()

    async def test_close_client(self, mock_api_key: str, mock_model: str):
        """Test closing the client."""
        client = OpenRouterClient(api_key=mock_api_key, model=mock_model)
        await client.start()
        assert client.is_started

        await client.close()
        assert not client.is_started
        assert client._session is None


# ============================================================================
# Unit Tests - Cache Management
# ============================================================================


class TestCacheManagement:
    """Tests for response caching functionality."""

    async def test_cache_hit(self, mock_api_key: str, mock_model: str):
        """Test retrieving response from cache."""
        client = OpenRouterClient(api_key=mock_api_key, model=mock_model, enable_caching=True)
        await client.start()

        # Manually add to cache
        cache_key = "test-cache-key"
        test_response = "Cached response"
        client._add_to_cache(cache_key, test_response, mock_model, 100)

        # Retrieve from cache
        cached = client._get_from_cache(cache_key)
        assert cached == test_response

        await client.close()

    async def test_cache_miss(self, mock_api_key: str, mock_model: str):
        """Test cache miss scenario."""
        client = OpenRouterClient(api_key=mock_api_key, model=mock_model, enable_caching=True)
        await client.start()

        # Try to retrieve non-existent cache entry
        cached = client._get_from_cache("non-existent-key")
        assert cached is None

        await client.close()

    async def test_cache_expiration(self, mock_api_key: str, mock_model: str):
        """Test cache entry expiration."""
        client = OpenRouterClient(
            api_key=mock_api_key, model=mock_model, enable_caching=True, cache_ttl=1
        )
        await client.start()

        # Add to cache
        cache_key = "test-cache-key"
        test_response = "Cached response"
        client._add_to_cache(cache_key, test_response, mock_model, 100)

        # Should be in cache
        assert client._get_from_cache(cache_key) == test_response

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Should be expired
        assert client._get_from_cache(cache_key) is None

        await client.close()

    def test_generate_cache_key(self, mock_api_key: str, mock_model: str):
        """Test cache key generation."""
        client = OpenRouterClient(api_key=mock_api_key, model=mock_model)

        request = OpenRouterRequest(
            model=mock_model,
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.7,
            max_tokens=100,
        )

        key1 = client._generate_cache_key(request)
        key2 = client._generate_cache_key(request)

        # Same request should generate same key
        assert key1 == key2
        assert len(key1) == 32  # MD5 hash length

    def test_cache_size_property(self, mock_api_key: str, mock_model: str):
        """Test cache size property."""
        client = OpenRouterClient(api_key=mock_api_key, model=mock_model, enable_caching=True)

        assert client.cache_size == 0

        # Add entries
        client._add_to_cache("key1", "response1", mock_model, 100)
        client._add_to_cache("key2", "response2", mock_model, 100)

        assert client.cache_size == 2


# ============================================================================
# Unit Tests - Request Deduplication
# ============================================================================


class TestRequestDeduplication:
    """Tests for request deduplication functionality."""

    async def test_deduplication_same_request(
        self, mock_api_key: str, mock_model: str, mock_messages: list
    ):
        """Test that duplicate requests are deduplicated."""
        client = OpenRouterClient(api_key=mock_api_key, model=mock_model, enable_caching=False)
        await client.start()

        with aioresponses() as m:
            m.post(
                "https://openrouter.ai/api/v1/chat/completions",
                payload={
                    "choices": [{"message": {"content": "Response"}}],
                    "model": mock_model,
                },
            )

            # Start two identical requests concurrently
            task1 = asyncio.create_task(
                client.chat_completion(mock_messages, use_cache=False)
            )
            task2 = asyncio.create_task(
                client.chat_completion(mock_messages, use_cache=False)
            )

            # Both should return same result
            result1 = await task1
            result2 = await task2

            assert result1 == result2

        await client.close()

    async def test_in_flight_count_property(self, mock_api_key: str, mock_model: str):
        """Test in-flight request count."""
        client = OpenRouterClient(api_key=mock_api_key, model=mock_model)
        await client.start()

        assert client.in_flight_count == 0

        # Simulate in-flight request
        client._in_flight["test-key"] = asyncio.create_task(asyncio.sleep(10))

        assert client.in_flight_count == 1

        # Cleanup
        client._in_flight["test-key"].cancel()
        await client.close()


# ============================================================================
# Integration Tests - API Requests
# ============================================================================


class TestAPIRequests:
    """Tests for actual API requests."""

    async def test_successful_request(
        self,
        client: OpenRouterClient,
        mock_messages: list,
        mock_api_response: dict,
    ):
        """Test successful API request."""
        with aioresponses() as m:
            m.post(
                "https://openrouter.ai/api/v1/chat/completions",
                payload=mock_api_response,
            )

            response = await client.chat_completion(mock_messages, use_cache=False)

            assert response == "Hello! How can I help you?"

    async def test_request_with_custom_parameters(
        self, client: OpenRouterClient, mock_messages: list, mock_api_response: dict
    ):
        """Test request with custom temperature and max_tokens."""
        with aioresponses() as m:
            m.post(
                "https://openrouter.ai/api/v1/chat/completions",
                payload=mock_api_response,
            )

            response = await client.chat_completion(
                mock_messages, temperature=1.0, max_tokens=1000, use_cache=False
            )

            assert response == "Hello! How can I help you?"

    async def test_invalid_messages_empty_list(self, client: OpenRouterClient):
        """Test that empty messages list raises ValueError."""
        with pytest.raises(ValueError, match="non-empty list"):
            await client.chat_completion([])

    async def test_invalid_messages_format(self, client: OpenRouterClient):
        """Test that invalid message format raises ValueError."""
        with pytest.raises(ValueError, match="'role' and 'content'"):
            await client.chat_completion([{"invalid": "format"}])

    async def test_api_error_status_code(
        self, client: OpenRouterClient, mock_messages: list
    ):
        """Test handling of API error status codes."""
        with aioresponses() as m:
            # Mock all retry attempts to return 500 error
            for _ in range(3):  # 3 retry attempts
                m.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    status=500,
                    payload={"error": "Internal Server Error"},
                )

            with pytest.raises(ClientResponseError):
                await client.chat_completion(mock_messages, use_cache=False)

    async def test_network_error(self, client: OpenRouterClient, mock_messages: list):
        """Test handling of network errors."""
        with aioresponses() as m:
            m.post(
                "https://openrouter.ai/api/v1/chat/completions",
                exception=ClientError("Network error"),
            )

            with pytest.raises(ClientError):
                await client.chat_completion(mock_messages, use_cache=False)

    async def test_timeout_error(self, client: OpenRouterClient, mock_messages: list):
        """Test handling of timeout errors."""
        with patch.object(client._session, "post") as mock_post:
            mock_post.side_effect = asyncio.TimeoutError("Request timed out")

            with pytest.raises(asyncio.TimeoutError):
                await client.chat_completion(mock_messages, use_cache=False)


# ============================================================================
# Integration Tests - Retry Logic
# ============================================================================


class TestRetryLogic:
    """Tests for retry logic and error handling."""

    async def test_retry_on_500_error(
        self, mock_api_key: str, mock_model: str, mock_messages: list
    ):
        """Test retry on 500 status code."""
        client = OpenRouterClient(
            api_key=mock_api_key, model=mock_model, max_retries=3, retry_delay=0.1
        )
        await client.start()

        with aioresponses() as m:
            # First two requests fail with 500
            m.post("https://openrouter.ai/api/v1/chat/completions", status=500, payload={"error": "Internal Server Error"})
            m.post("https://openrouter.ai/api/v1/chat/completions", status=500, payload={"error": "Internal Server Error"})
            # Third request succeeds
            m.post(
                "https://openrouter.ai/api/v1/chat/completions",
                payload={"choices": [{"message": {"content": "Success"}}], "model": mock_model},
            )

            # Should eventually succeed
            response = await client.chat_completion(mock_messages, use_cache=False)
            assert response == "Success"

        await client.close()

    async def test_retry_on_429_rate_limit(
        self, mock_api_key: str, mock_model: str, mock_messages: list
    ):
        """Test retry on 429 rate limit error."""
        client = OpenRouterClient(
            api_key=mock_api_key, model=mock_model, max_retries=3, retry_delay=0.1
        )
        await client.start()

        with aioresponses() as m:
            # First request fails with 429
            m.post("https://openrouter.ai/api/v1/chat/completions", status=429)
            # Second request succeeds
            m.post(
                "https://openrouter.ai/api/v1/chat/completions",
                payload={"choices": [{"message": {"content": "Success"}}], "model": mock_model},
            )

            response = await client.chat_completion(mock_messages, use_cache=False)
            assert response == "Success"

        await client.close()

    async def test_max_retries_exhausted(
        self, mock_api_key: str, mock_model: str, mock_messages: list
    ):
        """Test that max retries are respected."""
        client = OpenRouterClient(
            api_key=mock_api_key, model=mock_model, max_retries=2, retry_delay=0.1
        )
        await client.start()

        with aioresponses() as m:
            # All requests fail
            m.post(
                "https://openrouter.ai/api/v1/chat/completions",
                status=500,
                repeat=True,
            )

            with pytest.raises(ClientResponseError):
                await client.chat_completion(mock_messages, use_cache=False)

        await client.close()

    async def test_no_retry_on_validation_error(self, client: OpenRouterClient):
        """Test that validation errors don't trigger retries."""
        # Invalid messages should not be retried
        with pytest.raises(ValueError):
            await client.chat_completion([])


# ============================================================================
# Integration Tests - Response Caching
# ============================================================================


class TestResponseCaching:
    """Tests for response caching in API requests."""

    async def test_cached_response_used(
        self, mock_api_key: str, mock_model: str, mock_messages: list
    ):
        """Test that cached responses are used on subsequent requests."""
        client = OpenRouterClient(
            api_key=mock_api_key, model=mock_model, enable_caching=True
        )
        await client.start()

        with aioresponses() as m:
            m.post(
                "https://openrouter.ai/api/v1/chat/completions",
                payload={"choices": [{"message": {"content": "First response"}}], "model": mock_model},
            )

            # First request - should hit API
            response1 = await client.chat_completion(mock_messages, use_cache=True)
            assert response1 == "First response"

        # Second request with same messages - should use cache
        response2 = await client.chat_completion(mock_messages, use_cache=True)
        assert response2 == "First response"

        await client.close()

    async def test_cache_bypass(self, client: OpenRouterClient, mock_messages: list):
        """Test that cache can be bypassed."""
        with aioresponses() as m:
            # Mock the same response for multiple calls
            m.post(
                "https://openrouter.ai/api/v1/chat/completions",
                payload={"choices": [{"message": {"content": "Response"}}], "model": "test"},
            )
            m.post(
                "https://openrouter.ai/api/v1/chat/completions",
                payload={"choices": [{"message": {"content": "Response"}}], "model": "test"},
            )

            # Both requests should hit API
            response1 = await client.chat_completion(mock_messages, use_cache=False)
            response2 = await client.chat_completion(mock_messages, use_cache=False)

            assert response1 == response2 == "Response"

    async def test_different_messages_different_cache(
        self, mock_api_key: str, mock_model: str
    ):
        """Test that different messages result in different cache entries."""
        client = OpenRouterClient(
            api_key=mock_api_key, model=mock_model, enable_caching=True
        )
        await client.start()

        messages1 = [{"role": "user", "content": "Hello"}]
        messages2 = [{"role": "user", "content": "Goodbye"}]

        with aioresponses() as m:
            m.post(
                "https://openrouter.ai/api/v1/chat/completions",
                payload={"choices": [{"message": {"content": "Response 1"}}], "model": mock_model},
            )
            m.post(
                "https://openrouter.ai/api/v1/chat/completions",
                payload={"choices": [{"message": {"content": "Response 2"}}], "model": mock_model},
            )

            response1 = await client.chat_completion(messages1, use_cache=True)
            response2 = await client.chat_completion(messages2, use_cache=True)

            assert response1 == "Response 1"
            assert response2 == "Response 2"

        await client.close()


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    async def test_client_not_started(self, mock_api_key: str, mock_model: str, mock_messages: list):
        """Test that using client before start raises error."""
        client = OpenRouterClient(api_key=mock_api_key, model=mock_model)

        with pytest.raises(RuntimeError, match="not started"):
            await client.chat_completion(mock_messages)

    async def test_empty_response(self, client: OpenRouterClient, mock_messages: list):
        """Test handling of empty API response."""
        with aioresponses() as m:
            m.post(
                "https://openrouter.ai/api/v1/chat/completions",
                payload={"choices": [{"message": {"content": None}}], "model": "test"},
            )

            with pytest.raises(ValueError, match="No response text"):
                await client.chat_completion(mock_messages, use_cache=False)

    async def test_malformed_response(self, client: OpenRouterClient, mock_messages: list):
        """Test handling of malformed API response."""
        with aioresponses() as m:
            m.post(
                "https://openrouter.ai/api/v1/chat/completions",
                payload={"invalid": "response"},
            )

            with pytest.raises(ValueError, match="Invalid API response"):
                await client.chat_completion(mock_messages, use_cache=False)

    async def test_concurrent_requests(
        self, mock_api_key: str, mock_model: str, mock_messages: list
    ):
        """Test handling multiple concurrent requests."""
        client = OpenRouterClient(api_key=mock_api_key, model=mock_model, enable_caching=False)
        await client.start()

        with aioresponses() as m:
            # Set up multiple different responses
            for i in range(5):
                m.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    payload={"choices": [{"message": {"content": f"Response {i}"}}], "model": mock_model},
                )

            # Start 5 concurrent requests
            tasks = [
                asyncio.create_task(
                    client.chat_completion(
                        [{"role": "user", "content": f"Message {i}"}], use_cache=False
                    )
                )
                for i in range(5)
            ]

            responses = await asyncio.gather(*tasks)

            # All should succeed
            assert len(responses) == 5
            for i, response in enumerate(responses):
                assert response == f"Response {i}"

        await client.close()


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Tests for performance and efficiency."""

    async def test_cache_cleanup(self, mock_api_key: str, mock_model: str):
        """Test that expired cache entries are cleaned up."""
        client = OpenRouterClient(
            api_key=mock_api_key, model=mock_model, enable_caching=True, cache_ttl=1
        )
        await client.start()

        # Add cache entries
        client._add_to_cache("key1", "response1", mock_model, 100)
        client._add_to_cache("key2", "response2", mock_model, 100)

        assert client.cache_size == 2

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Trigger cleanup
        client._cleanup_expired_cache()

        # Cache should be empty
        assert client.cache_size == 0

        await client.close()