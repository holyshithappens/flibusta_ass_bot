"""
Unit tests for core type definitions.

Tests all Pydantic models and type aliases in src.bot.core.types module.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.bot.core.types import (
    ChatContext,
    AIResponse,
    ButtonCommand,
    OpenRouterRequest,
    OpenRouterResponse,
    BotInfo,
    MAX_SUGGESTIONS,
    MAX_BUTTONS,
)


class TestChatContext:
    """Test ChatContext model."""
    
    def test_valid_chat_context(self):
        """Test creating valid ChatContext."""
        context = ChatContext(
            chat_id=-1001234567890,
            user_id=123456789,
            message_id=42,
            message_text="Test message",
            chat_type="group"
        )
        
        assert context.chat_id == -1001234567890
        assert context.user_id == 123456789
        assert context.message_id == 42
        assert context.message_text == "Test message"
        assert context.chat_type == "group"
        assert isinstance(context.timestamp, datetime)
    
    def test_invalid_chat_type(self):
        """Test invalid chat type raises ValidationError."""
        with pytest.raises(ValidationError):
            ChatContext(
                chat_id=-1001234567890,
                user_id=123456789,
                message_id=42,
                message_text="Test message",
                chat_type="invalid_type"
            )
    
    def test_default_values(self):
        """Test default values are set correctly."""
        context = ChatContext(
            chat_id=-1001234567890,
            user_id=123456789,
            message_id=42,
            message_text="Test message"
        )
        
        assert context.chat_type == "group"
        assert context.message_history == []
        assert isinstance(context.timestamp, datetime)


class TestAIResponse:
    """Test AIResponse model."""
    
    def test_valid_ai_response(self):
        """Test creating valid AIResponse."""
        response = AIResponse(
            text="Test response",
            suggestions=["Suggestion 1", "Suggestion 2"],
            commands=["/command1", "/command2"],
            confidence=0.95,
            model_used="deepseek-v3.1"
        )
        
        assert response.text == "Test response"
        assert len(response.suggestions) == 2
        assert len(response.commands) == 2
        assert response.confidence == 0.95
        assert response.model_used == "deepseek-v3.1"
    
    def test_suggestions_limit(self):
        """Test suggestions limit validation."""
        with pytest.raises(ValidationError):
            AIResponse(
                text="Test",
                suggestions=[f"Suggestion {i}" for i in range(MAX_SUGGESTIONS + 1)]
            )
    
    def test_commands_limit(self):
        """Test commands limit validation."""
        with pytest.raises(ValidationError):
            AIResponse(
                text="Test",
                commands=[f"/command{i}" for i in range(MAX_BUTTONS + 1)]
            )
    
    def test_confidence_bounds(self):
        """Test confidence value bounds."""
        with pytest.raises(ValidationError):
            AIResponse(text="Test", confidence=1.5)
        
        with pytest.raises(ValidationError):
            AIResponse(text="Test", confidence=-0.1)
    
    def test_default_values(self):
        """Test default values are set correctly."""
        response = AIResponse(text="Test response")
        
        assert response.suggestions == []
        assert response.commands == []
        assert response.confidence == 1.0
        assert response.model_used == "unknown"


class TestButtonCommand:
    """Test ButtonCommand model."""
    
    def test_valid_button_command(self):
        """Test creating valid ButtonCommand."""
        button = ButtonCommand(
            text="Click me",
            command="/test@bot",
            type="command",
            priority=3
        )
        
        assert button.text == "Click me"
        assert button.command == "/test@bot"
        assert button.type == "command"
        assert button.priority == 3
    
    def test_button_text_length(self):
        """Test button text length validation."""
        with pytest.raises(ValidationError):
            ButtonCommand(
                text="A" * 21,  # Too long
                command="/test"
            )
    
    def test_command_validation(self):
        """Test command validation."""
        with pytest.raises(ValidationError):
            ButtonCommand(
                text="Test",
                command=""  # Empty command
            )
    
    def test_priority_bounds(self):
        """Test priority value bounds."""
        with pytest.raises(ValidationError):
            ButtonCommand(text="Test", command="/test", priority=0)
        
        with pytest.raises(ValidationError):
            ButtonCommand(text="Test", command="/test", priority=11)
    
    def test_invalid_type(self):
        """Test invalid button type."""
        with pytest.raises(ValidationError):
            ButtonCommand(
                text="Test",
                command="/test",
                type="invalid_type"
            )
    
    def test_default_values(self):
        """Test default values are set correctly."""
        button = ButtonCommand(text="Test", command="/test")
        
        assert button.type == "command"
        assert button.priority == 1


class TestOpenRouterRequest:
    """Test OpenRouterRequest model."""
    
    def test_valid_request(self):
        """Test creating valid OpenRouterRequest."""
        request = OpenRouterRequest(
            model="nex-agi/deepseek-v3.1-nex-n1:free",
            messages=[
                {"role": "system", "content": "You are a bot"},
                {"role": "user", "content": "Hello"}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        assert request.model == "nex-agi/deepseek-v3.1-nex-n1:free"
        assert len(request.messages) == 2
        assert request.temperature == 0.7
        assert request.max_tokens == 500
    
    def test_temperature_bounds(self):
        """Test temperature value bounds."""
        with pytest.raises(ValidationError):
            OpenRouterRequest(
                model="test",
                messages=[],
                temperature=2.5
            )
    
    def test_max_tokens_bounds(self):
        """Test max_tokens value bounds."""
        with pytest.raises(ValidationError):
            OpenRouterRequest(
                model="test",
                messages=[],
                max_tokens=5000
            )
    
    def test_default_values(self):
        """Test default values are set correctly."""
        request = OpenRouterRequest(
            model="test",
            messages=[]
        )
        
        assert request.temperature == 0.7
        assert request.max_tokens == 500


class TestOpenRouterResponse:
    """Test OpenRouterResponse model."""
    
    def test_valid_response(self):
        """Test creating valid OpenRouterResponse."""
        response = OpenRouterResponse(
            choices=[
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello!"
                    }
                }
            ],
            model="deepseek-v3.1",
            usage={
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "total_tokens": 30
            }
        )
        
        assert len(response.choices) == 1
        assert response.model == "deepseek-v3.1"
        assert response.usage["total_tokens"] == 30
    
    def test_first_choice_text_property(self):
        """Test first_choice_text property."""
        response = OpenRouterResponse(
            choices=[
                {
                    "message": {
                        "role": "assistant",
                        "content": "Test response"
                    }
                }
            ],
            model="test"
        )
        
        assert response.first_choice_text == "Test response"
    
    def test_first_choice_text_empty(self):
        """Test first_choice_text with no choices."""
        response = OpenRouterResponse(
            choices=[],
            model="test"
        )
        
        assert response.first_choice_text is None


class TestBotInfo:
    """Test BotInfo model."""
    
    def test_valid_bot_info(self):
        """Test creating valid BotInfo."""
        bot_info = BotInfo(
            name="TestBot",
            username="@TestBot",
            target_bot_username="@TargetBot",
            version="1.0.0"
        )
        
        assert bot_info.name == "TestBot"
        assert bot_info.username == "@TestBot"
        assert bot_info.target_bot_username == "@TargetBot"
        assert bot_info.version == "1.0.0"
    
    def test_username_format_validation(self):
        """Test username format validation."""
        with pytest.raises(ValidationError):
            BotInfo(
                name="TestBot",
                username="TestBot",  # Missing @
                target_bot_username="@TargetBot",
                version="1.0.0"
            )
    
    def test_version_format_validation(self):
        """Test version format validation."""
        with pytest.raises(ValidationError):
            BotInfo(
                name="TestBot",
                username="@TestBot",
                target_bot_username="@TargetBot",
                version="invalid"  # Invalid format
            )
    
    def test_name_length_validation(self):
        """Test name length validation."""
        with pytest.raises(ValidationError):
            BotInfo(
                name="A" * 101,  # Too long
                username="@TestBot",
                target_bot_username="@TargetBot",
                version="1.0.0"
            )


class TestTypeAliases:
    """Test type aliases and constants."""
    
    def test_constants(self):
        """Test constant values."""
        assert MAX_SUGGESTIONS == 6
        assert MAX_BUTTONS == 6
        assert isinstance(MAX_SUGGESTIONS, int)
        assert isinstance(MAX_BUTTONS, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])