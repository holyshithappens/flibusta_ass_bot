"""
Tests for channel comment handler.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat, ReplyKeyboardMarkup
from datetime import datetime

from src.bot.core.config import Config
from src.bot.core.types import ChatContext
from src.bot.handlers.channel_comments import ChannelCommentHandler

@pytest.fixture
def config():
    """Create test configuration."""
    return Config()

@pytest.fixture
def channel_handler(config):
    """Create channel comment handler instance."""
    return ChannelCommentHandler(config)

@pytest.fixture
def mock_channel_comment():
    """Create mock Telegram channel comment."""
    comment = MagicMock(spec=Message)
    comment.message_id = 67890
    comment.chat = MagicMock(spec=Chat)
    comment.chat.id = -1001234567890  # Channel ID
    comment.chat.type = "channel"
    comment.from_user = MagicMock(spec=User)
    comment.from_user.id = 123456789
    comment.from_user.username = "testuser"
    comment.text = "Hello @FlibustaAssBot"
    comment.date = datetime.now()

    # Mock reply to channel post
    post = MagicMock(spec=Message)
    post.message_id = 12345
    post.from_user = MagicMock(spec=User)
    post.from_user.id = 987654321
    post.from_user.username = "channel_owner"
    post.text = "Original channel post"
    post.date = datetime.now()

    comment.reply_to_message = post
    return comment

@pytest.mark.asyncio
async def test_channel_handler_initialization(config):
    """Test handler initialization."""
    handler = ChannelCommentHandler(config)
    assert handler.config == config
    assert handler.target_bot_username == config.bot.target_bot_username
    assert handler.bot_username == config.bot.username

@pytest.mark.asyncio
async def test_is_channel_comment(channel_handler, mock_channel_comment):
    """Test channel comment detection."""
    # Test channel comment
    assert channel_handler._is_channel_comment(mock_channel_comment) == True

    # Test non-channel message
    group_message = MagicMock(spec=Message)
    group_message.chat = MagicMock(spec=Chat)
    group_message.chat.id = -123456789  # Group ID (not -100*)
    group_message.reply_to_message = None
    assert channel_handler._is_channel_comment(group_message) == False

@pytest.mark.asyncio
async def test_is_bot_mention(channel_handler, mock_channel_comment):
    """Test bot mention detection."""
    # Test with bot mention
    assert channel_handler._is_bot_mention(mock_channel_comment) == True

    # Test without bot mention
    no_mention_comment = MagicMock(spec=Message)
    no_mention_comment.text = "Hello world"
    no_mention_comment.chat = mock_channel_comment.chat
    assert channel_handler._is_bot_mention(no_mention_comment) == False

@pytest.mark.asyncio
async def test_is_from_target_bot(channel_handler, mock_channel_comment):
    """Test target bot message detection."""
    # Test message from target bot
    target_bot_comment = MagicMock(spec=Message)
    target_bot_comment.from_user = MagicMock(spec=User)
    target_bot_comment.from_user.username = "FlibustaRuBot"
    assert channel_handler._is_from_target_bot(target_bot_comment) == True

    # Test message not from target bot
    assert channel_handler._is_from_target_bot(mock_channel_comment) == False

@pytest.mark.asyncio
async def test_handle_channel_comment_no_mention(channel_handler, mock_channel_comment):
    """Test handler when no bot mention."""
    # Remove bot mention
    mock_channel_comment.text = "Hello world"

    # Should return None
    result = await channel_handler.handle_channel_comment(mock_channel_comment)
    assert result is None

@pytest.mark.asyncio
async def test_handle_channel_comment_from_target_bot(channel_handler, mock_channel_comment):
    """Test handler when message from target bot."""
    # Make message from target bot
    mock_channel_comment.from_user.username = "FlibustaRuBot"

    # Should return None
    result = await channel_handler.handle_channel_comment(mock_channel_comment)
    assert result is None

@pytest.mark.asyncio
async def test_handle_channel_comment_success(channel_handler, mock_channel_comment):
    """Test successful channel comment handling."""
    # Mock AI assistant
    mock_ai_assistant = MagicMock()
    mock_ai_response = MagicMock()
    mock_ai_response.text = "Here's what I found"
    mock_ai_response.commands = ["/search@FlibustaRuBot test"]
    mock_ai_assistant.get_ai_response.return_value = mock_ai_response

    channel_handler.ai_assistant = mock_ai_assistant

    # Mock button generator
    mock_keyboard = MagicMock(spec=ReplyKeyboardMarkup)
    channel_handler.button_generator.generate_reply_buttons.return_value = mock_keyboard

    # Mock message.answer
    with patch.object(mock_channel_comment, 'answer', new_callable=AsyncMock) as mock_answer:
        mock_answer.return_value = mock_channel_comment

        # Handle comment
        result = await channel_handler.handle_channel_comment(mock_channel_comment)

        # Should return the sent message
        assert result == mock_channel_comment

        # Should call AI assistant
        mock_ai_assistant.get_ai_response.assert_called_once()

        # Should call button generator
        channel_handler.button_generator.generate_reply_buttons.assert_called_once()

        # Should send message
        mock_answer.assert_called_once()

@pytest.mark.asyncio
async def test_extract_context(channel_handler, mock_channel_comment):
    """Test context extraction."""
    # Mock message analyzer
    mock_context = MagicMock(spec=ChatContext)
    channel_handler.message_analyzer.extract_context.return_value = mock_context

    # Extract context
    context = await channel_handler._extract_context(mock_channel_comment)

    # Should return context from analyzer
    assert context == mock_context

    # Should call analyzer with correct parameters
    channel_handler.message_analyzer.extract_context.assert_called_once_with(
        chat_id=mock_channel_comment.chat.id,
        user_id=mock_channel_comment.from_user.id,
        message_text=mock_channel_comment.text,
        message_history=channel_handler._get_channel_context(mock_channel_comment)
    )

@pytest.mark.asyncio
async def test_get_channel_context(channel_handler, mock_channel_comment):
    """Test channel context retrieval."""
    # Get channel context
    context = await channel_handler._get_channel_context(mock_channel_comment)

    # Should return list with channel post
    assert len(context) == 1
    assert context[0]['message_id'] == mock_channel_comment.reply_to_message.message_id
    assert context[0]['text'] == "Original channel post"

@pytest.mark.asyncio
async def test_generate_ai_response(channel_handler):
    """Test AI response generation."""
    # Mock AI assistant
    mock_ai_assistant = MagicMock()
    mock_ai_response = MagicMock()
    mock_ai_assistant.get_ai_response.return_value = mock_ai_response

    channel_handler.ai_assistant = mock_ai_assistant

    # Mock context
    mock_context = MagicMock(spec=ChatContext)

    # Generate AI response
    result = await channel_handler._generate_ai_response(mock_context)

    # Should return AI response
    assert result == mock_ai_response

    # Should call AI assistant
    mock_ai_assistant.get_ai_response.assert_called_once_with(mock_context)

@pytest.mark.asyncio
async def test_generate_reply_buttons(channel_handler):
    """Test reply button generation."""
    # Mock AI response
    mock_ai_response = MagicMock()
    mock_ai_response.commands = ["/search@FlibustaRuBot test"]

    # Mock button generator
    mock_keyboard = MagicMock(spec=ReplyKeyboardMarkup)
    channel_handler.button_generator.generate_reply_buttons.return_value = mock_keyboard

    # Generate buttons
    result = channel_handler._generate_reply_buttons(mock_ai_response)

    # Should return keyboard
    assert result == mock_keyboard

    # Should call button generator
    channel_handler.button_generator.generate_reply_buttons.assert_called_once_with(mock_ai_response)

@pytest.mark.asyncio
async def test_send_response(channel_handler, mock_channel_comment):
    """Test response sending."""
    # Mock AI response
    mock_ai_response = MagicMock()
    mock_ai_response.text = "Test response"

    # Mock keyboard
    mock_keyboard = MagicMock(spec=ReplyKeyboardMarkup)

    # Mock message.answer
    with patch.object(mock_channel_comment, 'answer', new_callable=AsyncMock) as mock_answer:
        mock_answer.return_value = mock_channel_comment

        # Send response
        result = await channel_handler._send_response(mock_channel_comment, mock_ai_response, mock_keyboard)

        # Should return sent message
        assert result == mock_channel_comment

        # Should call message.answer with channel context
        mock_answer.assert_called_once()
        assert "📌 В ответ на сообщение" in mock_answer.call_args[0][0]
        assert "Test response" in mock_answer.call_args[0][0]