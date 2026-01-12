"""
Configuration management for FlibustaUserAssistBot.

This module provides a thread-safe configuration manager that loads settings
from environment variables, YAML files, and AI instruction files at startup.
"""

import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Type

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .types import (
    DEFAULT_AI_INSTRUCTION_PATH,
    DEFAULT_CONFIG_PATH,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT,
    LOG_LEVELS,
    BotInfo,
)

# ============================================================================
# Pydantic Configuration Models
# ============================================================================


class OpenRouterConfig(BaseModel):
    """OpenRouter AI API configuration."""

    api_key: str = Field(..., description="OpenRouter API key from environment")
    model: str = Field(
        default="nex-agi/deepseek-v3.1-nex-n1:free", description="AI model identifier"
    )
    temperature: float = Field(
        default=DEFAULT_TEMPERATURE, ge=0.0, le=2.0, description="Sampling temperature (0.0-2.0)"
    )
    max_tokens: int = Field(
        default=DEFAULT_MAX_TOKENS, ge=1, le=4000, description="Maximum tokens in response"
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT, ge=1, le=120, description="API timeout in seconds"
    )
    enable_caching: bool = Field(default=True, description="Enable response caching")
    cache_ttl: int = Field(default=3600, ge=60, description="Cache TTL in seconds")

    model_config = ConfigDict(extra="allow")


class TelegramConfig(BaseModel):
    """Telegram bot configuration."""

    bot_token: str = Field(..., description="Telegram bot token from environment")
    group_chat_ids: list = Field(
        default_factory=list, description="List of group chat IDs where bot should respond"
    )
    admin_user_ids: list = Field(default_factory=list, description="List of admin user IDs")
    allow_private_messages: bool = Field(
        default=False, description="Enable private message handling"
    )
    monitor_channel_comments: bool = Field(
        default=True, description="Enable channel comment monitoring"
    )

    model_config = ConfigDict(extra="allow")


class AIAssistantConfig(BaseModel):
    """AI assistant configuration."""

    context_window_size: int = Field(
        default=10, ge=1, le=50, description="Number of previous messages in context"
    )
    include_history: bool = Field(default=True, description="Include message history in context")
    include_mentions: bool = Field(default=True, description="Include user mentions in context")
    include_target_bot_responses: bool = Field(
        default=True, description="Include target bot responses in context"
    )
    max_context_length: int = Field(
        default=3000, ge=500, le=8000, description="Maximum context length in characters"
    )

    model_config = ConfigDict(extra="allow")


class ButtonsConfig(BaseModel):
    """Button generation configuration."""

    buttons_per_row: int = Field(default=2, ge=1, le=4, description="Maximum buttons per row")
    max_buttons: int = Field(default=6, ge=1, le=12, description="Maximum total buttons")
    enabled_types: list = Field(
        default_factory=lambda: ["command", "search", "navigation"],
        description="Enabled button types",
    )
    button_priority: Dict[str, int] = Field(
        default_factory=lambda: {"command": 3, "search": 2, "navigation": 1},
        description="Button type priorities",
    )

    model_config = ConfigDict(extra="allow")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default=DEFAULT_LOG_LEVEL, description="Logging level")
    file_path: str = Field(default="logs/bot.log", description="Log file path")
    max_size_mb: int = Field(default=10, ge=1, le=100, description="Maximum log file size in MB")
    backup_count: int = Field(default=5, ge=0, le=20, description="Number of backup log files")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    console_output: bool = Field(default=True, description="Enable console output")
    file_output: bool = Field(default=True, description="Enable file output")
    structured: bool = Field(default=False, description="Enable structured logging (JSON)")

    @field_validator("level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        if v not in LOG_LEVELS:
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()

    model_config = ConfigDict(extra="allow")


class PerformanceConfig(BaseModel):
    """Performance configuration."""

    rate_limiting_enabled: bool = Field(default=True, description="Enable rate limiting")
    max_requests_per_minute: int = Field(
        default=10, ge=1, le=100, description="Maximum requests per minute per user"
    )
    response_caching_enabled: bool = Field(default=True, description="Enable response caching")
    cache_ttl: int = Field(default=3600, ge=60, description="Cache TTL in seconds")
    connection_pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")

    model_config = ConfigDict(extra="allow")


class SecurityConfig(BaseModel):
    """Security configuration."""

    verify_webhook: bool = Field(default=True, description="Verify Telegram webhook data")
    user_rate_limit: int = Field(default=10, ge=1, le=100, description="Rate limit per user")
    chat_rate_limit: int = Field(default=30, ge=1, le=200, description="Rate limit per chat")
    block_suspicious: bool = Field(default=True, description="Block suspicious requests")
    log_security_events: bool = Field(default=True, description="Log security events")

    model_config = ConfigDict(extra="allow")


class DevelopmentConfig(BaseModel):
    """Development and debugging configuration."""

    debug: bool = Field(default=False, description="Enable debug mode")
    verbose: bool = Field(default=False, description="Enable verbose logging")
    mock_ai_responses: bool = Field(default=False, description="Mock AI responses for testing")
    log_all_updates: bool = Field(default=False, description="Log all incoming updates")
    test_mode: bool = Field(default=False, description="Enable test mode")

    model_config = ConfigDict(extra="allow")


class FeaturesConfig(BaseModel):
    """Feature flags."""

    group_messages: bool = Field(default=True, description="Enable group message handling")
    channel_comments: bool = Field(default=True, description="Enable channel comment handling")
    private_messages: bool = Field(default=False, description="Enable private message handling")
    inline_queries: bool = Field(default=False, description="Enable inline queries")
    admin_commands: bool = Field(default=True, description="Enable admin commands")
    statistics: bool = Field(default=False, description="Enable statistics collection")

    model_config = ConfigDict(extra="allow")


class BotConfig(BaseModel):
    """Complete bot configuration."""

    bot: BotInfo = Field(..., description="Basic bot information")
    telegram: TelegramConfig = Field(
        default_factory=TelegramConfig, description="Telegram configuration"
    )
    openrouter: OpenRouterConfig = Field(
        default_factory=OpenRouterConfig, description="OpenRouter API configuration"
    )
    ai_assistant: AIAssistantConfig = Field(
        default_factory=AIAssistantConfig, description="AI assistant configuration"
    )
    buttons: ButtonsConfig = Field(
        default_factory=ButtonsConfig, description="Button generation configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )
    performance: PerformanceConfig = Field(
        default_factory=PerformanceConfig, description="Performance configuration"
    )
    security: SecurityConfig = Field(
        default_factory=SecurityConfig, description="Security configuration"
    )
    development: DevelopmentConfig = Field(
        default_factory=DevelopmentConfig, description="Development configuration"
    )
    features: FeaturesConfig = Field(default_factory=FeaturesConfig, description="Feature flags")

    model_config = ConfigDict(extra="allow")


# ============================================================================
# Configuration Manager
# ============================================================================


class Config:
    """
    Thread-safe configuration manager.

    This class manages configuration from multiple sources:
    - Environment variables (via os.getenv)
    - YAML configuration file
    - AI instruction markdown file

    All configuration is loaded once at startup.
    """

    _instance: Optional["Config"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "Config":
        """Singleton pattern with thread safety."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        """Initialize configuration (only once)."""
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._yaml_data: Dict[str, Any] = {}
        self._ai_instruction: str = ""
        self._bot_config: Optional[BotConfig] = None

        # File paths
        self.config_path: Path = Path(DEFAULT_CONFIG_PATH)
        self.ai_instruction_path: Path = Path(DEFAULT_AI_INSTRUCTION_PATH)

        # Load configuration
        self.load()

    def load(self) -> None:
        """
        Load all configuration from files and environment.

        Raises:
            FileNotFoundError: If config files are missing
            ValueError: If configuration is invalid
        """
        # Load YAML configuration
        self._load_yaml_config()

        # Load AI instruction
        self._load_ai_instruction()

        # Merge with environment variables
        self._merge_env_variables()

        # Validate configuration
        self._validate_config()

    def _load_yaml_config(self) -> None:
        """Load YAML configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._yaml_data = yaml.safe_load(f) or {}

    def _load_ai_instruction(self) -> None:
        """Load AI instruction file."""
        if not self.ai_instruction_path.exists():
            raise FileNotFoundError(f"AI instruction file not found: {self.ai_instruction_path}")

        with open(self.ai_instruction_path, "r", encoding="utf-8") as f:
            self._ai_instruction = f.read()

    def _merge_env_variables(self) -> None:
        """Merge environment variables into configuration."""
        # Telegram configuration
        if "TELEGRAM_BOT_TOKEN" in os.environ:
            self._yaml_data.setdefault("telegram", {})
            self._yaml_data["telegram"]["bot_token"] = os.environ["TELEGRAM_BOT_TOKEN"]

        # OpenRouter configuration
        if "OPENROUTER_API_KEY" in os.environ:
            self._yaml_data.setdefault("openrouter", {})
            self._yaml_data["openrouter"]["api_key"] = os.environ["OPENROUTER_API_KEY"]

        if "OPENROUTER_MODEL" in os.environ:
            self._yaml_data.setdefault("openrouter", {})
            self._yaml_data["openrouter"]["model"] = os.environ["OPENROUTER_MODEL"]

        if "OPENROUTER_TIMEOUT" in os.environ:
            self._yaml_data.setdefault("openrouter", {})
            self._yaml_data["openrouter"]["timeout"] = int(os.environ["OPENROUTER_TIMEOUT"])

        # Bot configuration
        if "TARGET_BOT_USERNAME" in os.environ:
            self._yaml_data.setdefault("bot", {})
            self._yaml_data["bot"]["target_bot_username"] = os.environ["TARGET_BOT_USERNAME"]

        if "BOT_USERNAME" in os.environ:
            self._yaml_data.setdefault("bot", {})
            self._yaml_data["bot"]["username"] = os.environ["BOT_USERNAME"]

        # Logging configuration
        if "LOG_LEVEL" in os.environ:
            self._yaml_data.setdefault("logging", {})
            self._yaml_data["logging"]["level"] = os.environ["LOG_LEVEL"]

        if "LOG_FILE_PATH" in os.environ:
            self._yaml_data.setdefault("logging", {})
            self._yaml_data["logging"]["file_path"] = os.environ["LOG_FILE_PATH"]

        if "LOG_MAX_SIZE_MB" in os.environ:
            self._yaml_data.setdefault("logging", {})
            self._yaml_data["logging"]["max_size_mb"] = int(os.environ["LOG_MAX_SIZE_MB"])

        if "LOG_BACKUP_COUNT" in os.environ:
            self._yaml_data.setdefault("logging", {})
            self._yaml_data["logging"]["backup_count"] = int(os.environ["LOG_BACKUP_COUNT"])

        # AI configuration
        if "AI_TEMPERATURE" in os.environ:
            self._yaml_data.setdefault("openrouter", {})
            self._yaml_data["openrouter"]["temperature"] = float(os.environ["AI_TEMPERATURE"])

        if "AI_MAX_TOKENS" in os.environ:
            self._yaml_data.setdefault("openrouter", {})
            self._yaml_data["openrouter"]["max_tokens"] = int(os.environ["AI_MAX_TOKENS"])

        # Development configuration
        if "DEBUG" in os.environ:
            self._yaml_data.setdefault("development", {})
            self._yaml_data["development"]["debug"] = os.environ["DEBUG"].lower() == "true"

        if "VERBOSE" in os.environ:
            self._yaml_data.setdefault("development", {})
            self._yaml_data["development"]["verbose"] = os.environ["VERBOSE"].lower() == "true"

    def _validate_config(self) -> None:
        """Validate and create BotConfig object."""
        try:
            self._bot_config = BotConfig(**self._yaml_data)
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")

    @property
    def bot(self) -> BotInfo:
        """Get bot information."""
        if self._bot_config is None:
            raise RuntimeError("Configuration not loaded")
        return self._bot_config.bot

    @property
    def telegram(self) -> TelegramConfig:
        """Get Telegram configuration."""
        if self._bot_config is None:
            raise RuntimeError("Configuration not loaded")
        return self._bot_config.telegram

    @property
    def openrouter(self) -> OpenRouterConfig:
        """Get OpenRouter configuration."""
        if self._bot_config is None:
            raise RuntimeError("Configuration not loaded")
        return self._bot_config.openrouter

    @property
    def ai_assistant(self) -> AIAssistantConfig:
        """Get AI assistant configuration."""
        if self._bot_config is None:
            raise RuntimeError("Configuration not loaded")
        return self._bot_config.ai_assistant

    @property
    def buttons(self) -> ButtonsConfig:
        """Get button configuration."""
        if self._bot_config is None:
            raise RuntimeError("Configuration not loaded")
        return self._bot_config.buttons

    @property
    def logging(self) -> LoggingConfig:
        """Get logging configuration."""
        if self._bot_config is None:
            raise RuntimeError("Configuration not loaded")
        return self._bot_config.logging

    @property
    def performance(self) -> PerformanceConfig:
        """Get performance configuration."""
        if self._bot_config is None:
            raise RuntimeError("Configuration not loaded")
        return self._bot_config.performance

    @property
    def security(self) -> SecurityConfig:
        """Get security configuration."""
        if self._bot_config is None:
            raise RuntimeError("Configuration not loaded")
        return self._bot_config.security

    @property
    def development(self) -> DevelopmentConfig:
        """Get development configuration."""
        if self._bot_config is None:
            raise RuntimeError("Configuration not loaded")
        return self._bot_config.development

    @property
    def features(self) -> FeaturesConfig:
        """Get feature flags."""
        if self._bot_config is None:
            raise RuntimeError("Configuration not loaded")
        return self._bot_config.features

    @property
    def ai_instruction(self) -> str:
        """Get AI instruction text."""
        return self._ai_instruction

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (dot notation supported).

        Args:
            key: Configuration key (e.g., 'bot.name', 'telegram.group_chat_ids')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if self._bot_config is None:
            raise RuntimeError("Configuration not loaded")

        # Convert to Pydantic dict
        config_dict = self._bot_config.model_dump()

        # Navigate using dot notation
        keys = key.split(".")
        value = config_dict

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        if self._bot_config is None:
            raise RuntimeError("Configuration not loaded")
        return self._bot_config.model_dump()

    def __repr__(self) -> str:
        """String representation of Config."""
        return f"Config(bot={self.bot.name}, version={self.bot.version})"


# Global config instance
config: Config = Config()


__all__ = [
    # Configuration models
    "OpenRouterConfig",
    "TelegramConfig",
    "AIAssistantConfig",
    "ButtonsConfig",
    "LoggingConfig",
    "PerformanceConfig",
    "SecurityConfig",
    "DevelopmentConfig",
    "FeaturesConfig",
    "BotConfig",
    # Config manager
    "Config",
    "config",
]
