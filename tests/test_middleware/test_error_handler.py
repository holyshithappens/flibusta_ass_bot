"""
Tests for error handler middleware.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Update, Message, User, Chat
from aiogram.exceptions import TelegramAPIError
from datetime import datetime

from src.bot.core.config import Config
from src.bot.middleware.error_handler import ErrorHandlerMiddleware

@pytest.fixture
def config():
    """Create test configuration."""
    return Config()

@pytest.fixture
def error_middleware(config):
    """Create error handler middleware instance."""
    return ErrorHandlerMiddleware(config)

@pytest.fixture
def mock_update():
    """Create mock Telegram update with message."""
    update = MagicMock(spec=Update)
    update.update_id = 12345

    # Mock message
    message = MagicMock(spec=Message)
    message.message_id = 67890
    message.chat = MagicMock(spec=Chat)
    message.chat.id = -1001234567890
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 123456789
    message.text = "Test message"

    update.message = message
    return update

@pytest.mark.asyncio
async def test_error_middleware_initialization(config):
    """Test middleware initialization."""
    middleware = ErrorHandlerMiddleware(config)
    assert middleware.config == config
    assert "default" in middleware.error_messages
    assert "api_error" in middleware.error_messages

@pytest.mark.asyncio
async def test_error_middleware_successful_handler(error_middleware, mock_update):
    """Test middleware with successful handler."""
    # Mock handler
    async def mock_handler(update, data):
        return "success"

    # Mock data
    data = {}

    # Call middleware
    result = await error_middleware(mock_handler, mock_update, data)

    assert result == "success"

@pytest.mark.asyncio
async def test_error_middleware_value_error(error_middleware, mock_update):
    """Test middleware with ValueError."""
    # Mock handler that raises ValueError
    async def mock_handler(update, data):
        raise ValueError("Validation error")

    # Mock data
    data = {}

    # Mock message.answer to avoid actual Telegram calls
    with patch.object(mock_update.message, 'answer', new_callable=AsyncMock) as mock_answer:
        # Call middleware
        result = await error_middleware(mock_handler, mock_update, data)

        # Should return None
        assert result is None

        # Should call message.answer with validation error message
        mock_answer.assert_called_once()
        assert "Некорректный запрос" in mock_answer.call_args[0][0]

@pytest.mark.asyncio
async def test_error_middleware_telegram_api_error(error_middleware, mock_update):
    """Test middleware with TelegramAPIError."""
    # Mock handler that raises TelegramAPIError
    async def mock_handler(update, data):
        raise TelegramAPIError("Telegram error")

    # Mock data
    data = {}

    # Mock message.answer to avoid actual Telegram calls
    with patch.object(mock_update.message, 'answer', new_callable=AsyncMock) as mock_answer:
        # Call middleware
        result = await error_middleware(mock_handler, mock_update, data)

        # Should return None
        assert result is None

        # Should call message.answer with API error message
        mock_answer.assert_called_once()
        assert "Ошибка связи с Telegram" in mock_answer.call_args[0][0]

@pytest.mark.asyncio
async def test_error_middleware_timeout_error(error_middleware, mock_update):
    """Test middleware with TimeoutError."""
    # Mock handler that raises TimeoutError
    async def mock_handler(update, data):
        raise TimeoutError("Request timeout")

    # Mock data
    data = {}

    # Mock message.answer to avoid actual Telegram calls
    with patch.object(mock_update.message, 'answer', new_callable=AsyncMock) as mock_answer:
        # Call middleware
        result = await error_middleware(mock_handler, mock_update, data)

        # Should return None
        assert result is None

        # Should call message.answer with timeout error message
        mock_answer.assert_called_once()
        assert "Превышено время ожидания" in mock_answer.call_args[0][0]

@pytest.mark.asyncio
async def test_error_middleware_no_message(error_middleware):
    """Test middleware when update has no message."""
    # Create update without message
    update = MagicMock(spec=Update)
    update.update_id = 12345
    update.message = None

    # Mock handler that raises exception
    async def mock_handler(update, data):
        raise ValueError("Test error")

    # Mock data
    data = {}

    # Call middleware
    result = await error_middleware(mock_handler, update, data)

    # Should return None without trying to send message
    assert result is None

@pytest.mark.asyncio
async def test_error_middleware_message_answer_failure(error_middleware, mock_update):
    """Test middleware when message.answer fails."""
    # Mock handler that raises exception
    async def mock_handler(update, data):
        raise ValueError("Test error")

    # Mock data
    data = {}

    # Mock message.answer to raise exception
    with patch.object(mock_update.message, 'answer', side_effect=TelegramAPIError("Cannot send")):
        # Call middleware
        result = await error_middleware(mock_handler, mock_update, data)

        # Should return None
        assert result is None

@pytest.mark.asyncio
async def test_get_error_message(error_middleware):
    """Test error message selection."""
    # Test ValueError
    error_msg = error_middleware._get_error_message(ValueError("test"))
    assert "Некорректный запрос" in error_msg

    # Test TimeoutError
    error_msg = error_middleware._get_error_message(TimeoutError("test"))
    assert "Превышено время ожидания" in error_msg

    # Test TelegramAPIError
    error_msg = error_middleware._get_error_message(TelegramAPIError("test"))
    assert "Ошибка связи с Telegram" in error_msg

    # Test generic error
    error_msg = error_middleware._get_error_message(RuntimeError("test"))
    assert "Ошибка обработки запроса" in error_msg

@pytest.mark.asyncio
async def test_add_custom_error_message(error_middleware):
    """Test adding custom error messages."""
    # Add custom error message
    error_middleware.add_custom_error_message("custom_error", "Custom error message")

    # Test that it's in the messages
    assert "custom_error" in error_middleware.error_messages
    assert error_middleware.error_messages["custom_error"] == "Custom error message"

@pytest.mark.asyncio
async def test_get_update_type(error_middleware, mock_update):
    """Test update type detection."""
    # Test message update
    assert error_middleware._get_update_type(mock_update) == "message"

    # Test callback update
    callback_update = MagicMock(spec=Update)
    callback_update.callback_query = MagicMock()
    assert error_middleware._get_update_type(callback_update) == "callback"

    # Test unknown update
    unknown_update = MagicMock(spec=Update)
    assert error_middleware._get_update_type(unknown_update) == "unknown"

@pytest.mark.asyncio
async def test_is_security_error(error_middleware):
    """Test security error detection."""
    # Test security-related error
    security_error = ValueError("Authentication failed")
    assert error_middleware._is_security_error(security_error) == True

    # Test non-security error
    normal_error = ValueError("Normal error")
    assert error_middleware._is_security_error(normal_error) == False