"""
Tests for logging middleware.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Update, Message, User, Chat
from datetime import datetime

from src.bot.core.config import Config
from src.bot.middleware.logging import LoggingMiddleware

@pytest.fixture
def config():
    """Create test configuration."""
    return Config()

@pytest.fixture
def logging_middleware(config):
    """Create logging middleware instance."""
    return LoggingMiddleware(config)

@pytest.fixture
def mock_update():
    """Create mock Telegram update."""
    update = MagicMock(spec=Update)
    update.update_id = 12345

    # Mock message
    message = MagicMock(spec=Message)
    message.message_id = 67890
    message.chat = MagicMock(spec=Chat)
    message.chat.id = -1001234567890
    message.chat.type = "group"
    message.chat.title = "Test Group"
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 123456789
    message.from_user.username = "testuser"
    message.from_user.first_name = "Test"
    message.from_user.last_name = "User"
    message.text = "Hello @FlibustaAssBot"
    message.date = datetime.now()

    update.message = message
    return update

@pytest.mark.asyncio
async def test_logging_middleware_initialization(config):
    """Test middleware initialization."""
    middleware = LoggingMiddleware(config)
    assert middleware.config == config
    assert middleware.metrics['total_updates'] == 0
    assert middleware.metrics['message_updates'] == 0

@pytest.mark.asyncio
async def test_logging_middleware_call(logging_middleware, mock_update):
    """Test middleware call with successful handler."""
    # Mock handler
    async def mock_handler(update, data):
        return "success"

    # Mock data
    data = {}

    # Call middleware
    result = await logging_middleware(mock_handler, mock_update, data)

    assert result == "success"
    assert logging_middleware.metrics['total_updates'] == 1
    assert logging_middleware.metrics['message_updates'] == 1

@pytest.mark.asyncio
async def test_logging_middleware_error_handling(logging_middleware, mock_update):
    """Test middleware error handling."""
    # Mock handler that raises exception
    async def mock_handler(update, data):
        raise ValueError("Test error")

    # Mock data
    data = {}

    # Call middleware and expect exception
    with pytest.raises(ValueError, match="Test error"):
        await logging_middleware(mock_handler, mock_update, data)

    # Metrics should still be updated
    assert logging_middleware.metrics['total_updates'] == 1

@pytest.mark.asyncio
async def test_get_update_type(logging_middleware, mock_update):
    """Test update type detection."""
    # Test message update
    assert logging_middleware._get_update_type(mock_update) == "message"

    # Test callback update
    callback_update = MagicMock(spec=Update)
    callback_update.callback_query = MagicMock()
    assert logging_middleware._get_update_type(callback_update) == "callback"

    # Test unknown update
    unknown_update = MagicMock(spec=Update)
    assert logging_middleware._get_update_type(unknown_update) == "unknown"

@pytest.mark.asyncio
async def test_extract_user_info(logging_middleware, mock_update):
    """Test user info extraction."""
    user_info = logging_middleware._extract_user_info(mock_update)

    assert user_info['id'] == 123456789
    assert user_info['username'] == "testuser"
    assert user_info['first_name'] == "Test"
    assert user_info['last_name'] == "User"

@pytest.mark.asyncio
async def test_extract_chat_info(logging_middleware, mock_update):
    """Test chat info extraction."""
    chat_info = logging_middleware._extract_chat_info(mock_update)

    assert chat_info['id'] == -1001234567890
    assert chat_info['type'] == "group"
    assert chat_info['title'] == "Test Group"

@pytest.mark.asyncio
async def test_is_bot_mention(logging_middleware, mock_update):
    """Test bot mention detection."""
    # Test with bot mention
    assert logging_middleware._is_bot_mention(mock_update.message) == True

    # Test without bot mention
    no_mention_message = MagicMock(spec=Message)
    no_mention_message.text = "Hello world"
    assert logging_middleware._is_bot_mention(no_mention_message) == False

@pytest.mark.asyncio
async def test_is_target_bot_command(logging_middleware, mock_update):
    """Test target bot command detection."""
    # Test with target bot command
    target_command_message = MagicMock(spec=Message)
    target_command_message.text = "/search@FlibustaRuBot programming"
    assert logging_middleware._is_target_bot_command(target_command_message) == True

    # Test without target bot command
    assert logging_middleware._is_target_bot_command(mock_update.message) == False

@pytest.mark.asyncio
async def test_get_metrics(logging_middleware):
    """Test metrics retrieval."""
    # Add some fake processing times
    logging_middleware.metrics['processing_times'] = [0.1, 0.2, 0.3]

    metrics = logging_middleware.get_metrics()

    assert metrics['avg_processing_time'] == 0.2
    assert metrics['total_updates'] == 0

@pytest.mark.asyncio
async def test_reset_metrics(logging_middleware):
    """Test metrics reset."""
    # Add some metrics
    logging_middleware.metrics['total_updates'] = 10
    logging_middleware.metrics['processing_times'] = [0.1, 0.2]

    # Reset metrics
    logging_middleware.reset_metrics()

    assert logging_middleware.metrics['total_updates'] == 0
    assert len(logging_middleware.metrics['processing_times']) == 0