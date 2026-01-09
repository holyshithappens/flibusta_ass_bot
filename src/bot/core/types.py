"""
Core type definitions for FlibustaUserAssistBot.

This module defines all data models and type aliases used throughout the application.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================================================
# Telegram API Types
# ============================================================================


class TelegramMessage(TypedDict, total=False):
    """Typed dictionary for Telegram message structure."""

    message_id: int
    chat_id: int
    user_id: int
    text: Optional[str]
    date: datetime
    chat_type: str
    reply_to_message_id: Optional[int]
    from_user: Dict[str, Any]


# ============================================================================
# Chat Context Types
# ============================================================================


class ChatContext(BaseModel):
    """Represents the context of a conversation."""

    chat_id: int = Field(..., description="Telegram chat ID")
    user_id: int = Field(..., description="User ID who sent the message")
    message_id: int = Field(..., description="Message ID")
    message_text: str = Field(..., description="Message text content")
    message_history: List[TelegramMessage] = Field(
        default_factory=list, description="List of previous messages in the conversation"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the context was created"
    )
    chat_type: Literal["group", "channel", "private"] = Field(
        default="group", description="Type of chat"
    )

    @field_validator("chat_type")
    @classmethod
    def validate_chat_type(cls, v: str) -> str:
        """Validate chat type."""
        if v not in ["group", "channel", "private"]:
            raise ValueError(f"Invalid chat type: {v}")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "chat_id": -1001234567890,
                "user_id": 123456789,
                "message_id": 42,
                "message_text": "Посоветуйте книгу по программированию",
                "message_history": [],
                "timestamp": "2026-01-08T21:00:00Z",
                "chat_type": "group",
            }
        }
    )


# ============================================================================
# AI Response Types
# ============================================================================


class AIResponse(BaseModel):
    """Structured response from AI assistant."""

    text: str = Field(
        ..., min_length=1, max_length=4000, description="Main response text to show to user"
    )
    suggestions: List[str] = Field(
        default_factory=list, description="List of text suggestions (bullet points)"
    )
    commands: List[str] = Field(
        default_factory=list, description="List of commands for reply buttons"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score of the AI response"
    )
    model_used: str = Field(default="unknown", description="Name of the AI model used")

    @field_validator("suggestions")
    @classmethod
    def validate_suggestions(cls, v: List[str]) -> List[str]:
        """Limit number of suggestions."""
        if len(v) > 6:
            raise ValueError("Maximum 6 suggestions allowed")
        return v

    @field_validator("commands")
    @classmethod
    def validate_commands(cls, v: List[str]) -> List[str]:
        """Limit number of commands."""
        if len(v) > 6:
            raise ValueError("Maximum 6 commands allowed")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "Отличный выбор! Вот несколько вариантов:",
                "suggestions": ["Искать популярные книги", "Показать случайную книгу"],
                "commands": ["/search@FlibustaRuBot programming", "/random@FlibustaRuBot"],
                "confidence": 0.95,
                "model_used": "deepseek-v3.1",
            }
        }
    )


# ============================================================================
# Button Command Types
# ============================================================================


class ButtonCommand(BaseModel):
    """Represents a button command for Telegram reply keyboard."""

    text: str = Field(
        ..., min_length=1, max_length=20, description="Button text (displayed to user)"
    )
    command: str = Field(
        ..., min_length=1, max_length=100, description="Command to send when button is clicked"
    )
    type: Literal["command", "search", "navigation"] = Field(
        default="command", description="Type of button command"
    )
    priority: int = Field(
        default=1, ge=1, le=10, description="Button priority (higher = shown first)"
    )

    @field_validator("text")
    @classmethod
    def validate_button_text(cls, v: str) -> str:
        """Validate button text length."""
        if len(v) > 20:
            raise ValueError("Button text must be 20 characters or less")
        return v

    @field_validator("command")
    @classmethod
    def validate_command_format(cls, v: str) -> str:
        """Validate command format."""
        if not v.strip():
            raise ValueError("Command cannot be empty")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "🔍 Найти книги",
                "command": "/search@FlibustaRuBot programming",
                "type": "search",
                "priority": 3,
            }
        }
    )


# ============================================================================
# OpenRouter API Types
# ============================================================================


class OpenRouterRequest(BaseModel):
    """Request model for OpenRouter API."""

    model: str = Field(
        ..., description="Model identifier (e.g., nex-agi/deepseek-v3.1-nex-n1:free)"
    )
    messages: List[Dict[str, str]] = Field(
        ..., description="List of message objects with role and content"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=500, ge=1, le=4000, description="Maximum tokens in response")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model": "nex-agi/deepseek-v3.1-nex-n1:free",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello!"},
                ],
                "temperature": 0.7,
                "max_tokens": 500,
            }
        }
    )


class OpenRouterResponse(BaseModel):
    """Response model from OpenRouter API."""

    choices: List[Dict[str, Any]] = Field(..., description="List of response choices")
    model: str = Field(..., description="Model that generated the response")
    usage: Dict[str, int] = Field(default_factory=dict, description="Token usage statistics")

    @property
    def first_choice_text(self) -> Optional[str]:
        """Extract text from first choice."""
        if not self.choices:
            return None
        choice = self.choices[0]
        content = choice.get("message", {}).get("content")
        return str(content) if content is not None else None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "choices": [
                    {"message": {"role": "assistant", "content": "Hello! How can I help you?"}}
                ],
                "model": "deepseek-v3.1",
                "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            }
        }
    )


# ============================================================================
# Configuration Types
# ============================================================================


class BotInfo(BaseModel):
    """Basic bot information."""

    name: str = Field(..., min_length=1, max_length=100, description="Bot display name")
    username: str = Field(..., pattern=r"^@\w+$", description="Bot username (must start with @)")
    target_bot_username: str = Field(
        ..., pattern=r"^@\w+$", description="Target bot username (must start with @)"
    )
    version: str = Field(
        ..., pattern=r"^\d+\.\d+\.\d+$", description="Bot version (semantic versioning)"
    )

    @field_validator("username", "target_bot_username")
    @classmethod
    def validate_username_format(cls, v: str) -> str:
        """Validate username starts with @."""
        if not v.startswith("@"):
            raise ValueError("Username must start with @")
        return v


# ============================================================================
# Type Aliases
# ============================================================================

# Simple type aliases for clarity
ChatID = int
UserID = int
MessageID = int
CommandString = str

# Dictionary types for better type hints
MessageHistory = List[TelegramMessage]
ButtonGrid = List[List[ButtonCommand]]


# ============================================================================
# Constants
# ============================================================================

# Maximum values
MAX_SUGGESTIONS: int = 6
MAX_BUTTONS: int = 6
MAX_BUTTONS_PER_ROW: int = 3
MAX_CONTEXT_LENGTH: int = 3000
MAX_MESSAGE_HISTORY: int = 10

# Default values
DEFAULT_TEMPERATURE: float = 0.7
DEFAULT_MAX_TOKENS: int = 500
DEFAULT_TIMEOUT: int = 30
DEFAULT_LOG_LEVEL: str = "INFO"

# Logging
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# File paths
DEFAULT_CONFIG_PATH: str = "config/bot_config.yaml"
DEFAULT_AI_INSTRUCTION_PATH: str = "config/ai_instruction.md"
DEFAULT_LOG_PATH: str = "logs/bot.log"


__all__ = [
    # Types
    "TelegramMessage",
    "ChatContext",
    "AIResponse",
    "ButtonCommand",
    "OpenRouterRequest",
    "OpenRouterResponse",
    "BotInfo",
    # Type aliases
    "ChatID",
    "UserID",
    "MessageID",
    "CommandString",
    "MessageHistory",
    "ButtonGrid",
    # Constants
    "MAX_SUGGESTIONS",
    "MAX_BUTTONS",
    "MAX_BUTTONS_PER_ROW",
    "MAX_CONTEXT_LENGTH",
    "MAX_MESSAGE_HISTORY",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_TIMEOUT",
    "DEFAULT_LOG_LEVEL",
    "LOG_LEVELS",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_AI_INSTRUCTION_PATH",
    "DEFAULT_LOG_PATH",
]
