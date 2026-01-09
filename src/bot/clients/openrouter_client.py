"""
OpenRouter.ai API client for FlibustaUserAssistBot.

This module provides an async client for interacting with the OpenRouter API,
with support for error handling, retry logic, request deduplication, and response caching.
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

import aiohttp
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..core.logger import BotLogger
from ..core.types import OpenRouterRequest, OpenRouterResponse

# ============================================================================
# Constants
# ============================================================================

OPENROUTER_API_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2
CACHE_TTL = 3600  # 1 hour

# HTTP status codes that should trigger a retry
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

# ============================================================================
# Cache Entry Model
# ============================================================================


class CacheEntry(BaseModel):
    """Represents a cached response."""

    response: str
    timestamp: datetime
    model_used: str
    tokens_used: int

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# OpenRouter Client
# ============================================================================


class OpenRouterClient:
    """
    Async client for OpenRouter.ai API.

    Features:
    - Async HTTP requests using aiohttp
    - Automatic retry with exponential backoff
    - Request deduplication (prevents duplicate concurrent requests)
    - Response caching with TTL
    - Comprehensive error handling
    - Request timeout management
    """

    def __init__(
        self,
        api_key: str,
        model: str = "nex-agi/deepseek-v3.1-nex-n1:free",
        timeout: int = DEFAULT_TIMEOUT,
        enable_caching: bool = True,
        cache_ttl: int = CACHE_TTL,
        max_retries: int = MAX_RETRIES,
        retry_delay: int = RETRY_DELAY,
    ) -> None:
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key
            model: Model identifier to use
            timeout: Request timeout in seconds
            enable_caching: Whether to enable response caching
            cache_ttl: Cache TTL in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize logger
        self.logger = BotLogger(__name__)

        # Response cache
        self._cache: Dict[str, CacheEntry] = {}

        # Request deduplication - track in-flight requests
        self._in_flight: Dict[str, asyncio.Task] = {}

        # Session for HTTP requests
        self._session: Optional[aiohttp.ClientSession] = None

        # Cleanup task for expired cache entries
        self._cleanup_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------------
    # Lifecycle Methods
    # ------------------------------------------------------------------------

    async def start(self) -> None:
        """Start the client and initialize resources."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "FlibustaUserAssistBot/0.3.0",
                },
            )

        # Start cache cleanup task if caching is enabled
        if self.enable_caching and self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_cache_loop())

        self.logger.info(
            f"OpenRouter client started - model: {self.model}, timeout: {self.timeout}, caching: {self.enable_caching}"
        )

    async def close(self) -> None:
        """Close the client and cleanup resources."""
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # Cancel in-flight requests
        for task in self._in_flight.values():
            if not task.done():
                task.cancel()

        # Close session
        if self._session:
            await self._session.close()
            self._session = None

        self.logger.info("OpenRouter client closed")

    # ------------------------------------------------------------------------
    # Public API Methods
    # ------------------------------------------------------------------------

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
        use_cache: bool = True,
    ) -> str:
        """
        Get chat completion from OpenRouter API.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            use_cache: Whether to use cached responses if available

        Returns:
            Response text from AI model

        Raises:
            ValueError: If messages are invalid
            aiohttp.ClientError: If HTTP request fails
            Exception: For other API errors
        """
        # Validate inputs
        if not messages or not isinstance(messages, list):
            raise ValueError("Messages must be a non-empty list")

        for msg in messages:
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                raise ValueError("Each message must have 'role' and 'content' keys")

        # Create request
        request_data = OpenRouterRequest(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Check cache first
        cache_key = self._generate_cache_key(request_data)
        if use_cache and self.enable_caching:
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                self.logger.debug(f"Using cached response - cache_key: {cache_key[:16]}")
                return cached_response

        # Check for duplicate request (deduplication)
        if cache_key in self._in_flight:
            self.logger.debug(f"Waiting for duplicate request - cache_key: {cache_key[:16]}")
            try:
                result = await self._in_flight[cache_key]
                return str(result)  # Ensure type safety
            except asyncio.CancelledError:
                # If cancelled, remove from in-flight and proceed normally
                self._in_flight.pop(cache_key, None)

        # Create new request task
        task = asyncio.create_task(self._make_request_with_retry(request_data, cache_key))
        self._in_flight[cache_key] = task

        try:
            response = await task
            return response
        finally:
            # Remove from in-flight
            self._in_flight.pop(cache_key, None)

    # ------------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------------

    def _generate_cache_key(self, request: OpenRouterRequest) -> str:
        """
        Generate cache key from request data.

        Args:
            request: OpenRouterRequest object

        Returns:
            MD5 hash of request data
        """
        request_dict = request.model_dump()
        # Remove timestamp-dependent fields if any
        request_json = json.dumps(request_dict, sort_keys=True)
        return hashlib.md5(request_json.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """
        Get response from cache if not expired.

        Args:
            cache_key: Cache key to look up

        Returns:
            Cached response text or None if not found/expired
        """
        if cache_key not in self._cache:
            return None

        entry = self._cache[cache_key]
        age = (datetime.now() - entry.timestamp).total_seconds()

        if age > self.cache_ttl:
            # Expired
            del self._cache[cache_key]
            return None

        return entry.response

    def _add_to_cache(self, cache_key: str, response: str, model_used: str, tokens: int) -> None:
        """
        Add response to cache.

        Args:
            cache_key: Cache key
            response: Response text
            model_used: Model identifier
            tokens: Number of tokens used
        """
        entry = CacheEntry(
            response=response,
            timestamp=datetime.now(),
            model_used=model_used,
            tokens_used=tokens,
        )
        self._cache[cache_key] = entry
        self.logger.debug(f"Added to cache - cache_key: {cache_key[:16]}, tokens: {tokens}")

    async def _make_request_with_retry(self, request: OpenRouterRequest, cache_key: str) -> str:
        """
        Make HTTP request with retry logic.

        Args:
            request: OpenRouterRequest object
            cache_key: Cache key for this request

        Returns:
            Response text

        Raises:
            aiohttp.ClientError: If all retries fail
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                response_text = await self._make_single_request(request)

                # Cache successful response
                if self.enable_caching:
                    # Extract model and tokens from response if available
                    model_used = self.model
                    tokens = len(response_text.split())  # Rough estimate
                    self._add_to_cache(cache_key, response_text, model_used, tokens)

                return response_text

            except Exception as e:
                last_exception = e

                # Check if we should retry
                should_retry = self._should_retry(e, attempt)

                if should_retry:
                    delay = self.retry_delay * (2**attempt)  # Exponential backoff
                    self.logger.warning(
                        f"Request failed, retrying - attempt: {attempt + 1}/{self.max_retries}, delay: {delay}s, error: {str(e)}"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"Request failed, not retrying - error: {str(e)}")
                    raise

        # All retries exhausted
        self.logger.error(
            f"All retry attempts exhausted - max_retries: {self.max_retries}, error: {str(last_exception)}"
        )
        raise last_exception or Exception("Unknown error occurred")

    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if a request should be retried.

        Args:
            exception: Exception that occurred
            attempt: Current attempt number (0-indexed)

        Returns:
            True if request should be retried
        """
        # Don't retry if max attempts reached
        if attempt >= self.max_retries - 1:
            return False

        # Retry on network errors
        if isinstance(exception, (aiohttp.ClientError, asyncio.TimeoutError)):
            return True

        # Retry on specific HTTP status codes
        if isinstance(exception, aiohttp.ClientResponseError):
            return exception.status in RETRY_STATUS_CODES

        # Don't retry on validation errors
        if isinstance(exception, ValueError):
            return False

        # Default: retry
        return True

    async def _make_single_request(self, request: OpenRouterRequest) -> str:
        """
        Make a single HTTP request to OpenRouter API.

        Args:
            request: OpenRouterRequest object

        Returns:
            Response text

        Raises:
            aiohttp.ClientError: If HTTP request fails
            ValueError: If response is invalid
        """
        if self._session is None:
            raise RuntimeError("Client not started. Call start() first.")

        url = f"{OPENROUTER_API_BASE_URL}/chat/completions"

        self.logger.debug(
            f"Making API request - model: {request.model}, messages_count: {len(request.messages)}, temperature: {request.temperature}, max_tokens: {request.max_tokens}"
        )

        try:
            async with self._session.post(url, json=request.model_dump()) as response:
                # Check for HTTP errors
                if response.status != 200:
                    text = await response.text()
                    self.logger.error(
                        f"API returned error status - status: {response.status}, response: {text[:500]}"
                    )
                    response.raise_for_status()

                # Parse response
                response_json = await response.json()
                openrouter_response = OpenRouterResponse(**response_json)

                # Extract response text
                response_text = openrouter_response.first_choice_text

                if not response_text:
                    raise ValueError("No response text in API response")

                self.logger.debug(
                    f"API request successful - model: {openrouter_response.model}, response_length: {len(response_text)}"
                )

                return response_text

        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP request failed - error: {str(e)}")
            raise
        except ValidationError as e:
            self.logger.error(f"Response validation failed - error: {str(e)}")
            raise ValueError(f"Invalid API response: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during request - error: {str(e)}")
            raise

    async def _cleanup_cache_loop(self) -> None:
        """Periodically clean up expired cache entries."""
        while True:
            try:
                await asyncio.sleep(self.cache_ttl)
                self._cleanup_expired_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cache cleanup - error: {str(e)}")

    def _cleanup_expired_cache(self) -> None:
        """Remove expired cache entries."""
        now = datetime.now()
        expired_keys = []

        for cache_key, entry in self._cache.items():
            age = (now - entry.timestamp).total_seconds()
            if age > self.cache_ttl:
                expired_keys.append(cache_key)

        if expired_keys:
            for key in expired_keys:
                del self._cache[key]
            self.logger.debug(f"Cleaned up expired cache entries - count: {len(expired_keys)}")

    # ------------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------------

    @property
    def cache_size(self) -> int:
        """Get current cache size."""
        return len(self._cache)

    @property
    def in_flight_count(self) -> int:
        """Get number of in-flight requests."""
        return len(self._in_flight)

    @property
    def is_started(self) -> bool:
        """Check if client is started."""
        return self._session is not None


__all__ = ["OpenRouterClient"]
