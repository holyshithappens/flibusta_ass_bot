"""
Tests for AIAssistantService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.bot.services.ai_assistant import AIAssistantService
from src.bot.core.types import AIResponse, ChatContext, TelegramMessage
from src.bot.core.config import Config
from datetime import datetime

@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = MagicMock(spec=Config)
    config.bot.target_bot_username = "@FlibustaRuBot"
    config.openrouter.temperature = 0.7
    config.openrouter.max_tokens = 500
    config.openrouter.enable_caching = True
    config.ai_assistant.context_window_size = 5
    config.ai_assistant.max_context_length = 3000
    return config

@pytest.fixture
def mock_openrouter_client():
    """Create mock OpenRouter client."""
    client = MagicMock()
    client.is_started = True
    client.chat_completion = AsyncMock(return_value="Test AI response")
    return client

@pytest.fixture
def ai_assistant(mock_config, mock_openrouter_client):
    """Create AIAssistantService instance."""
    return AIAssistantService(mock_config, mock_openrouter_client)

@pytest.fixture
def sample_context():
    """Create sample chat context."""
    return ChatContext(
        chat_id=-1001234567890,
        user_id=123456789,
        message_id=42,
        message_text="Recommend some fantasy books",
        message_history=[
            TelegramMessage(
                message_id=41,
                chat_id=-1001234567890,
                user_id=987654321,
                text="I love fantasy books!",
                date=datetime.now(),
                chat_type="group",
                reply_to_message_id=None,
                from_user={"id": 987654321, "name": "User1"}
            )
        ],
        timestamp=datetime.now(),
        chat_type="group"
    )

def test_ai_assistant_initialization(ai_assistant, mock_config):
    """Test AIAssistantService initialization."""
    assert ai_assistant.config == mock_config
    assert ai_assistant.client == mock_config.openrouter_client
    assert ai_assistant.model == "mistralai/devstral-2512:free"
    assert ai_assistant.is_ready is True

def test_load_ai_instruction_success(ai_assistant, mock_config):
    """Test successful AI instruction loading."""
    mock_config.ai_instruction = "Test instruction content"
    instruction = ai_assistant._load_ai_instruction()
    assert instruction == "Test instruction content"

def test_load_ai_instruction_empty(ai_assistant, mock_config):
    """Test empty AI instruction handling."""
    mock_config.ai_instruction = ""
    with pytest.raises(ValueError):
        ai_assistant._load_ai_instruction()

def test_format_prompt_with_history(ai_assistant, sample_context):
    """Test prompt formatting with message history."""
    messages = ai_assistant._format_prompt(sample_context)
    assert len(messages) == 4  # system + context + history + user
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "Recommend some fantasy books"

def test_format_prompt_without_history(ai_assistant):
    """Test prompt formatting without message history."""
    context = ChatContext(
        chat_id=-1001234567890,
        user_id=123456789,
        message_id=42,
        message_text="Test message",
        message_history=[],
        timestamp=datetime.now(),
        chat_type="group"
    )
    messages = ai_assistant._format_prompt(context)
    assert len(messages) == 3  # system + context + user

@pytest.mark.asyncio
async def test_get_ai_response_success(ai_assistant, sample_context, mock_openrouter_client):
    """Test successful AI response generation."""
    mock_openrouter_client.chat_completion.return_value = "Great fantasy books: /pop@FlibustaRuBot"

    response = await ai_assistant.get_ai_response(sample_context)

    assert isinstance(response, AIResponse)
    assert response.text == "Great fantasy books:"
    assert len(response.commands) == 1
    assert "/pop@FlibustaRuBot" in response.commands
    assert response.model_used == "mistralai/devstral-2512:free"

    # Verify OpenRouter client was called
    mock_openrouter_client.chat_completion.assert_called_once()

@pytest.mark.asyncio
async def test_get_ai_response_with_commands_and_suggestions(ai_assistant, sample_context, mock_openrouter_client):
    """Test AI response with both commands and suggestions."""
    response_text = """Here are some options:
/pop@FlibustaRuBot fantasy
@FlibustaRuBot search best fantasy
Try these genres: epic, dark"""

    mock_openrouter_client.chat_completion.return_value = response_text

    response = await ai_assistant.get_ai_response(sample_context)

    assert isinstance(response, AIResponse)
    assert "Here are some options:" in response.text
    assert "Try these genres: epic, dark" in response.text
    assert len(response.commands) == 2
    assert "/pop@FlibustaRuBot fantasy" in response.commands
    assert "@FlibustaRuBot search best fantasy" in response.commands

@pytest.mark.asyncio
async def test_get_ai_response_empty_context(ai_assistant):
    """Test AI response with empty context."""
    empty_context = ChatContext(
        chat_id=-1001234567890,
        user_id=123456789,
        message_id=42,
        message_text="",
        message_history=[],
        timestamp=datetime.now(),
        chat_type="group"
    )

    with pytest.raises(ValueError):
        await ai_assistant.get_ai_response(empty_context)

@pytest.mark.asyncio
async def test_get_ai_response_api_failure(ai_assistant, sample_context, mock_openrouter_client):
    """Test AI response generation with API failure."""
    mock_openrouter_client.chat_completion.side_effect = Exception("API error")

    with pytest.raises(Exception):
        await ai_assistant.get_ai_response(sample_context)

def test_parse_ai_response_with_commands(ai_assistant, sample_context):
    """Test parsing AI response with commands."""
    response_text = """Here are some recommendations:
/pop@FlibustaRuBot fantasy
@FlibustaRuBot search best books
Enjoy reading!"""

    response = ai_assistant._parse_ai_response(response_text, sample_context)

    assert isinstance(response, AIResponse)
    assert response.text == "Here are some recommendations:\nEnjoy reading!"
    assert len(response.commands) == 2
    assert "/pop@FlibustaRuBot fantasy" in response.commands
    assert "@FlibustaRuBot search best books" in response.commands

def test_parse_ai_response_only_suggestions(ai_assistant, sample_context):
    """Test parsing AI response with only suggestions."""
    response_text = """Here are some suggestions:
Try fantasy genre
Explore best authors
Check recent releases"""

    response = ai_assistant._parse_ai_response(response_text, sample_context)

    assert isinstance(response, AIResponse)
    assert response.text == response_text
    assert len(response.commands) == 0

def test_parse_ai_response_empty(ai_assistant, sample_context):
    """Test parsing empty AI response."""
    with pytest.raises(ValueError):
        ai_assistant._parse_ai_response("", sample_context)

@pytest.mark.asyncio
async def test_validate_ai_instruction_success(ai_assistant, mock_config):
    """Test successful AI instruction validation."""
    mock_config.ai_instruction = "This is a valid instruction with sufficient length."
    result = await ai_assistant.validate_ai_instruction()
    assert result is True

@pytest.mark.asyncio
async def test_validate_ai_instruction_short(ai_assistant, mock_config):
    """Test short AI instruction validation."""
    mock_config.ai_instruction = "Short"
    result = await ai_assistant.validate_ai_instruction()
    assert result is False

@pytest.mark.asyncio
async def test_validate_ai_instruction_empty(ai_assistant, mock_config):
    """Test empty AI instruction validation."""
    mock_config.ai_instruction = ""
    result = await ai_assistant.validate_ai_instruction()
    assert result is False

def test_is_ready(ai_assistant):
    """Test is_ready property."""
    assert ai_assistant.is_ready is True

def test_is_not_ready(ai_assistant, mock_openrouter_client):
    """Test is_not_ready when client not started."""
    mock_openrouter_client.is_started = False
    assert ai_assistant.is_ready is False