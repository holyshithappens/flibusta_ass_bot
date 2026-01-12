"""
Tests for group message handler.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat, ReplyKeyboardMarkup
from datetime import datetime

from src.bot.core.config import Config
from src.bot.core.types import ChatContext
from src.bot.handlers.group_messages import GroupMessageHandler

@pytest.fixture
def config():
    """Create test configuration."""
    return Config()

@pytest.fixture
def group_handler(config):
    """Create group message handler instance."""
    return GroupMessageHandler(config)

@pytest.fixture
def mock_message():
    """Create mock Telegram message."""
    message = MagicMock(spec=Message)
    message.message_id = 67890
    message.chat = MagicMock(spec=Chat)
    message.chat.id = -1001234567890  # Group chat ID
    message.chat.type = "group"
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 123456789
    message.from_user.username = "testuser"
    message.text = "Hello @FlibustaAssBot"
    message.date = datetime.now()
    return message

@pytest.mark.asyncio
async def test_group_handler_initialization(config):
    """Test handler initialization."""
    handler = GroupMessageHandler(config)
    assert handler.config == config
    assert handler.target_bot_username == config.bot.target_bot_username
    assert handler.bot_username == config.bot.username

@pytest.mark.asyncio
async def test_is_group_message(group_handler, mock_message):
    """Test group message detection."""
    # Test group message
    assert group_handler._is_group_message(mock_message) == True

    # Test private message
    private_message = MagicMock(spec=Message)
    private_message.chat = MagicMock(spec=Chat)
    private_message.chat.id = 123456789  # Positive ID = private
    assert group_handler._is_group_message(private_message) == False

@pytest.mark.asyncio
async def test_is_bot_mention(group_handler, mock_message):
    """Test bot mention detection."""
    # Test with bot mention
    assert group_handler._is_bot_mention(mock_message) == True

    # Test without bot mention
    no_mention_message = MagicMock(spec=Message)
    no_mention_message.text = "Hello world"
    no_mention_message.chat = mock_message.chat
    assert group_handler._is_bot_mention(no_mention_message) == False

@pytest.mark.asyncio
async def test_is_from_target_bot(group_handler, mock_message):
    """Test target bot message detection."""
    # Test message from target bot
    target_bot_message = MagicMock(spec=Message)
    target_bot_message.from_user = MagicMock(spec=User)
    target_bot_message.from_user.username = "FlibustaRuBot"
    assert group_handler._is_from_target_bot(target_bot_message) == True

    # Test message not from target bot
    assert group_handler._is_from_target_bot(mock_message) == False

@pytest.mark.asyncio
async def test_handle_group_message_no_mention(group_handler, mock_message):
    """Test handler when no bot mention."""
    # Remove bot mention
    mock_message.text = "Hello world"

    # Should return None
    result = await group_handler.handle_group_message(mock_message)
    assert result is None

@pytest.mark.asyncio
async def test_handle_group_message_from_target_bot(group_handler, mock_message):
    """Test handler when message from target bot."""
    # Make message from target bot
    mock_message.from_user.username = "FlibustaRuBot"

    # Should return None
    result = await group_handler.handle_group_message(mock_message)
    assert result is None

@pytest.mark.asyncio
async def test_handle_group_message_success(group_handler, mock_message):
    """Test successful group message handling."""
    # Mock AI assistant
    mock_ai_assistant = MagicMock()
    mock_ai_response = MagicMock()
    mock_ai_response.text = "Here's what I found"
    mock_ai_response.commands = ["/search@FlibustaRuBot test"]
    mock_ai_assistant.get_ai_response.return_value = mock_ai_response

    group_handler.ai_assistant = mock_ai_assistant

    # Mock button generator
    mock_keyboard = MagicMock(spec=ReplyKeyboardMarkup)
    group_handler.button_generator.generate_reply_buttons.return_value = mock_keyboard

    # Mock message.answer
    with patch.object(mock_message, 'answer', new_callable=AsyncMock) as mock_answer:
        mock_answer.return_value = mock_message

        # Handle message
        result = await group_handler.handle_group_message(mock_message)

        # Should return the sent message
        assert result == mock_message

        # Should call AI assistant
        mock_ai_assistant.get_ai_response.assert_called_once()

        # Should call button generator
        group_handler.button_generator.generate_reply_buttons.assert_called_once()

        # Should send message
        mock_answer.assert_called_once()

@pytest.mark.asyncio
async def test_handle_start_command(group_handler, mock_message):
    """Test start command handling."""
    # Mock message.answer
    with patch.object(mock_message, 'answer', new_callable=AsyncMock) as mock_answer:
        mock_answer.return_value = mock_message

        # Handle start command
        result = await group_handler.handle_start_command(mock_message)

        # Should return the sent message
        assert result == mock_message

        # Should send welcome message
        mock_answer.assert_called_once()
        assert "Привет" in mock_answer.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_help_command(group_handler, mock_message):
    """Test help command handling."""
    # Mock message.answer
    with patch.object(mock_message, 'answer', new_callable=AsyncMock) as mock_answer:
        mock_answer.return_value = mock_message

        # Handle help command
        result = await group_handler.handle_help_command(mock_message)

        # Should return the sent message
        assert result == mock_message

        # Should send help message
        mock_answer.assert_called_once()
        assert "Как использовать" in mock_answer.call_args[0][0]

@pytest.mark.asyncio
async def test_extract_context(group_handler, mock_message):
    """Test context extraction."""
    # Mock message analyzer
    mock_context = MagicMock(spec=ChatContext)
    group_handler.message_analyzer.extract_context.return_value = mock_context

    # Extract context
    context = await group_handler._extract_context(mock_message)

    # Should return context from analyzer
    assert context == mock_context

    # Should call analyzer with correct parameters
    group_handler.message_analyzer.extract_context.assert_called_once_with(
        chat_id=mock_message.chat.id,
        user_id=mock_message.from_user.id,
        message_text=mock_message.text,
        message_history=[]
    )

@pytest.mark.asyncio
async def test_get_message_history(group_handler, mock_message):
    """Test message history retrieval."""
    # Get message history
    history = await group_handler._get_message_history(mock_message)

    # Should return empty list (simplified implementation)
    assert history == []

@pytest.mark.asyncio
async def test_generate_ai_response(group_handler):
    """Test AI response generation."""
    # Mock AI assistant
    mock_ai_assistant = MagicMock()
    mock_ai_response = MagicMock()
    mock_ai_assistant.get_ai_response.return_value = mock_ai_response

    group_handler.ai_assistant = mock_ai_assistant

    # Mock context
    mock_context = MagicMock(spec=ChatContext)

    # Generate AI response
    result = await group_handler._generate_ai_response(mock_context)

    # Should return AI response
    assert result == mock_ai_response

    # Should call AI assistant
    mock_ai_assistant.get_ai_response.assert_called_once_with(mock_context)

@pytest.mark.asyncio
async def test_generate_reply_buttons(group_handler):
    """Test reply button generation."""
    # Mock AI response
    mock_ai_response = MagicMock()
    mock_ai_response.commands = ["/search@FlibustaRuBot test"]

    # Mock button generator
    mock_keyboard = MagicMock(spec=ReplyKeyboardMarkup)
    group_handler.button_generator.generate_reply_buttons.return_value = mock_keyboard

    # Generate buttons
    result = group_handler._generate_reply_buttons(mock_ai_response)

    # Should return keyboard
    assert result == mock_keyboard

    # Should call button generator
    group_handler.button_generator.generate_reply_buttons.assert_called_once_with(mock_ai_response)

@pytest.mark.asyncio
async def test_send_response(group_handler, mock_message):
    """Test response sending."""
    # Mock AI response
    mock_ai_response = MagicMock()
    mock_ai_response.text = "Test response"

    # Mock keyboard
    mock_keyboard = MagicMock(spec=ReplyKeyboardMarkup)

    # Mock message.answer
    with patch.object(mock_message, 'answer', new_callable=AsyncMock) as mock_answer:
        mock_answer.return_value = mock_message

        # Send response
        result = await group_handler._send_response(mock_message, mock_ai_response, mock_keyboard)

        # Should return sent message
        assert result == mock_message

        # Should call message.answer with correct parameters
        mock_answer.assert_called_once_with(
            text="Test response",
            reply_markup=mock_keyboard,
            parse_mode=None,
            disable_web_page_preview=True
        )