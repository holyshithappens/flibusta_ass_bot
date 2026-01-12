"""
Tests for MessageAnalyzer.
"""

import pytest
from unittest.mock import MagicMock
from src.bot.services.message_analyzer import MessageAnalyzer
from src.bot.core.types import ChatContext, TelegramMessage
from src.bot.core.config import Config
from datetime import datetime, timedelta

@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = MagicMock(spec=Config)
    config.bot.target_bot_username = "@FlibustaRuBot"
    config.bot.username = "@FlibustaAssBot"
    config.ai_assistant.context_window_size = 5
    config.ai_assistant.max_context_length = 3000
    config.ai_assistant.include_history = True
    config.ai_assistant.include_mentions = True
    config.ai_assistant.include_target_bot_responses = True
    return config

@pytest.fixture
def message_analyzer(mock_config):
    """Create MessageAnalyzer instance."""
    return MessageAnalyzer(mock_config)

@pytest.fixture
def sample_message_history():
    """Create sample message history."""
    now = datetime.now()
    return [
        TelegramMessage(
            message_id=40,
            chat_id=-1001234567890,
            user_id=111111111,
            text="What fantasy books do you recommend?",
            date=now - timedelta(minutes=30),
            chat_type="group",
            reply_to_message_id=None,
            from_user={"id": 111111111, "name": "User1"}
        ),
        TelegramMessage(
            message_id=41,
            chat_id=-1001234567890,
            user_id=222222222,
            text="@FlibustaAssBot recommend some books",
            date=now - timedelta(minutes=15),
            chat_type="group",
            reply_to_message_id=None,
            from_user={"id": 222222222, "name": "User2"}
        ),
        TelegramMessage(
            message_id=42,
            chat_id=-1001234567890,
            user_id=987654321,
            text="I love fantasy books!",
            date=now - timedelta(minutes=5),
            chat_type="group",
            reply_to_message_id=None,
            from_user={"id": 987654321, "name": "User3"}
        )
    ]

def test_message_analyzer_initialization(message_analyzer, mock_config):
    """Test MessageAnalyzer initialization."""
    assert message_analyzer.config == mock_config
    assert message_analyzer.target_bot_username == "@FlibustaRuBot"
    assert message_analyzer.is_ready is True

@pytest.mark.asyncio
async def test_extract_context_success(message_analyzer, sample_message_history):
    """Test successful context extraction."""
    context = await message_analyzer.extract_context(
        chat_id=-1001234567890,
        user_id=123456789,
        message_text="Recommend some fantasy books",
        message_history=sample_message_history
    )

    assert isinstance(context, ChatContext)
    assert context.chat_id == -1001234567890
    assert context.user_id == 123456789
    assert context.message_text == "Recommend some fantasy books"
    assert len(context.message_history) == 3
    assert context.chat_type == "group"

@pytest.mark.asyncio
async def test_extract_context_empty_message(message_analyzer):
    """Test context extraction with empty message."""
    with pytest.raises(ValueError):
        await message_analyzer.extract_context(
            chat_id=-1001234567890,
            user_id=123456789,
            message_text="",
            message_history=[]
        )

@pytest.mark.asyncio
async def test_extract_context_no_history(message_analyzer):
    """Test context extraction with no message history."""
    context = await message_analyzer.extract_context(
        chat_id=-1001234567890,
        user_id=123456789,
        message_text="Test message",
        message_history=[]
    )

    assert isinstance(context, ChatContext)
    assert context.chat_id == -1001234567890
    assert context.user_id == 123456789
    assert context.message_text == "Test message"
    assert len(context.message_history) == 0
    assert context.chat_type == "group"

def test_filter_message_history_normal(message_analyzer, sample_message_history):
    """Test normal message history filtering."""
    filtered = message_analyzer._filter_message_history(sample_message_history)
    assert len(filtered) == 3

def test_filter_message_history_empty(message_analyzer):
    """Test empty message history filtering."""
    filtered = message_analyzer._filter_message_history([])
    assert len(filtered) == 0

def test_filter_message_history_old_messages(message_analyzer):
    """Test filtering out old messages."""
    now = datetime.now()
    old_message = TelegramMessage(
        message_id=1,
        chat_id=-1001234567890,
        user_id=111111111,
        text="Old message",
        date=now - timedelta(days=2),
        chat_type="group",
        reply_to_message_id=None,
        from_user={"id": 111111111, "name": "User1"}
    )

    filtered = message_analyzer._filter_message_history([old_message])
    assert len(filtered) == 0

def test_filter_message_history_empty_messages(message_analyzer):
    """Test filtering out empty messages."""
    messages = [
        TelegramMessage(
            message_id=1,
            chat_id=-1001234567890,
            user_id=111111111,
            text="",
            date=datetime.now(),
            chat_type="group",
            reply_to_message_id=None,
            from_user={"id": 111111111, "name": "User1"}
        ),
        TelegramMessage(
            message_id=2,
            chat_id=-1001234567890,
            user_id=222222222,
            text="Valid message",
            date=datetime.now(),
            chat_type="group",
            reply_to_message_id=None,
            from_user={"id": 222222222, "name": "User2"}
        )
    ]

    filtered = message_analyzer._filter_message_history(messages)
    assert len(filtered) == 1
    assert filtered[0]['text'] == "Valid message"

def test_filter_message_history_context_window_limit(message_analyzer, mock_config):
    """Test context window size limit."""
    mock_config.ai_assistant.context_window_size = 2

    messages = []
    now = datetime.now()
    for i in range(5):
        messages.append(TelegramMessage(
            message_id=i,
            chat_id=-1001234567890,
            user_id=111111111,
            text=f"Message {i}",
            date=now - timedelta(minutes=5-i),
            chat_type="group",
            reply_to_message_id=None,
            from_user={"id": 111111111, "name": "User1"}
        ))

    filtered = message_analyzer._filter_message_history(messages)
    assert len(filtered) == 2  # Should be limited to context window size

def test_filter_message_history_exclude_target_bot(message_analyzer, mock_config, sample_message_history):
    """Test filtering out target bot messages when configured."""
    mock_config.ai_assistant.include_target_bot_responses = False

    # Add target bot message
    target_bot_message = TelegramMessage(
        message_id=43,
        chat_id=-1001234567890,
        user_id=999999999,
        text="@FlibustaRuBot processing your request...",
        date=datetime.now(),
        chat_type="group",
        reply_to_message_id=None,
        from_user={"id": 999999999, "name": "FlibustaRuBot"}
    )

    messages = sample_message_history + [target_bot_message]
    filtered = message_analyzer._filter_message_history(messages)
    assert len(filtered) == 3  # Should exclude target bot message

def test_filter_message_history_exclude_mentions(message_analyzer, mock_config, sample_message_history):
    """Test filtering out bot mentions when configured."""
    mock_config.ai_assistant.include_mentions = False

    filtered = message_analyzer._filter_message_history(sample_message_history)
    assert len(filtered) == 2  # Should exclude the mention message

def test_determine_chat_type(message_analyzer):
    """Test chat type determination."""
    assert message_analyzer._determine_chat_type(123456789) == "private"
    assert message_analyzer._determine_chat_type(-1001234567890) == "group"
    assert message_analyzer._determine_chat_type(-1000000000001) == "channel"

def test_is_target_bot_message(message_analyzer):
    """Test target bot message detection."""
    # Target bot message
    target_msg = TelegramMessage(
        message_id=1,
        chat_id=-1001234567890,
        user_id=999999999,
        text="@FlibustaRuBot processing your request...",
        date=datetime.now(),
        chat_type="group",
        reply_to_message_id=None,
        from_user={"id": 999999999, "name": "FlibustaRuBot"}
    )
    assert message_analyzer._is_target_bot_message(target_msg) is True

    # Command to target bot
    command_msg = TelegramMessage(
        message_id=2,
        chat_id=-1001234567890,
        user_id=111111111,
        text="/pop@FlibustaRuBot fantasy",
        date=datetime.now(),
        chat_type="group",
        reply_to_message_id=None,
        from_user={"id": 111111111, "name": "User1"}
    )
    assert message_analyzer._is_target_bot_message(command_msg) is True

    # Regular message
    regular_msg = TelegramMessage(
        message_id=3,
        chat_id=-1001234567890,
        user_id=111111111,
        text="Regular message",
        date=datetime.now(),
        chat_type="group",
        reply_to_message_id=None,
        from_user={"id": 111111111, "name": "User1"}
    )
    assert message_analyzer._is_target_bot_message(regular_msg) is False

def test_contains_bot_mention(message_analyzer):
    """Test bot mention detection."""
    assert message_analyzer._contains_bot_mention("@FlibustaAssBot help") is True
    assert message_analyzer._contains_bot_mention("Hey @FlibustaAssBot!") is True
    assert message_analyzer._contains_bot_mention("Regular message") is False
    assert message_analyzer._contains_bot_mention("@OtherBot help") is False

@pytest.mark.asyncio
async def test_validate_context_success(message_analyzer):
    """Test successful context validation."""
    context = ChatContext(
        chat_id=-1001234567890,
        user_id=123456789,
        message_id=42,
        message_text="Test message",
        message_history=[
            TelegramMessage(
                message_id=41,
                chat_id=-1001234567890,
                user_id=987654321,
                text="Short history",
                date=datetime.now(),
                chat_type="group",
                reply_to_message_id=None,
                from_user={"id": 987654321, "name": "User1"}
            )
        ],
        timestamp=datetime.now(),
        chat_type="group"
    )

    result = await message_analyzer.validate_context(context)
    assert result is True

@pytest.mark.asyncio
async def test_validate_context_empty(message_analyzer):
    """Test empty context validation."""
    context = ChatContext(
        chat_id=-1001234567890,
        user_id=123456789,
        message_id=42,
        message_text="",
        message_history=[],
        timestamp=datetime.now(),
        chat_type="group"
    )

    result = await message_analyzer.validate_context(context)
    assert result is False

@pytest.mark.asyncio
async def test_validate_context_too_long(message_analyzer, mock_config):
    """Test context length validation."""
    mock_config.ai_assistant.max_context_length = 50

    context = ChatContext(
        chat_id=-1001234567890,
        user_id=123456789,
        message_id=42,
        message_text="This is a very long message that exceeds the maximum allowed length",
        message_history=[
            TelegramMessage(
                message_id=41,
                chat_id=-1001234567890,
                user_id=987654321,
                text="This is also a very long message that makes the total context too long",
                date=datetime.now(),
                chat_type="group",
                reply_to_message_id=None,
                from_user={"id": 987654321, "name": "User1"}
            )
        ],
        timestamp=datetime.now(),
        chat_type="group"
    )

    result = await message_analyzer.validate_context(context)
    assert result is False

def test_is_ready(message_analyzer):
    """Test is_ready property."""
    assert message_analyzer.is_ready is True

def test_is_not_ready(message_analyzer, mock_config):
    """Test is_not_ready when config is invalid."""
    mock_config.bot.target_bot_username = None
    assert message_analyzer.is_ready is False