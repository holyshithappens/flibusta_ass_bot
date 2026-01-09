"""
Logging configuration for FlibustaUserAssistBot.

This module provides centralized logging configuration with support for
multiple outputs, rotation, and structured logging.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Literal, Optional

from .types import DEFAULT_LOG_LEVEL, DEFAULT_LOG_PATH, LOG_LEVELS


class BotLogger:
    """
    Centralized logger configuration for the bot.

    Supports:
    - Console output with colors
    - File output with rotation
    - Multiple log levels
    - Structured logging (optional)
    """

    def __init__(
        self,
        name: str = "FlibustaUserAssistBot",
        level: str = DEFAULT_LOG_LEVEL,
        file_path: Optional[Path] = None,
        max_size_mb: int = 10,
        backup_count: int = 5,
        console_output: bool = True,
        file_output: bool = True,
        structured: bool = False,
        log_format: Optional[str] = None,
    ) -> None:
        """
        Initialize the logger.

        Args:
            name: Logger name
            level: Logging level
            file_path: Path to log file
            max_size_mb: Maximum log file size in MB
            backup_count: Number of backup files to keep
            console_output: Enable console output
            file_output: Enable file output
            structured: Enable JSON structured logging
            log_format: Custom log format string
        """
        self.name = name
        self.level = level.upper()
        self.file_path = Path(file_path) if file_path else Path(DEFAULT_LOG_PATH)
        self.max_size_mb = max_size_mb
        self.backup_count = backup_count
        self.console_output = console_output
        self.file_output = file_output
        self.structured = structured

        # Validate log level
        if self.level not in LOG_LEVELS:
            raise ValueError(f"Invalid log level: {self.level}. Must be one of {LOG_LEVELS}")

        # Set log format
        if log_format is None:
            self.log_format = (
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                if not structured
                else '{"timestamp": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
            )
        else:
            self.log_format = log_format

        # Initialize logger
        self._logger: Optional[logging.Logger] = None
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Set up the logger with handlers."""
        # Create logger
        self._logger = logging.getLogger(self.name)
        self._logger.setLevel(getattr(logging, self.level))

        # Remove existing handlers
        self._logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(self.log_format, datefmt="%Y-%m-%d %H:%M:%S")

        # Console handler
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.level))
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)

        # File handler with rotation
        if self.file_output:
            # Ensure log directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                filename=self.file_path,
                maxBytes=self.max_size_mb * 1024 * 1024,  # Convert MB to bytes
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(getattr(logging, self.level))
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        """
        Get the configured logger instance.

        Returns:
            Configured logger
        """
        if self._logger is None:
            raise RuntimeError("Logger not initialized. Call setup() first.")
        return self._logger

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message."""
        if self._logger:
            self._logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        if self._logger:
            self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        if self._logger:
            self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log error message."""
        if self._logger:
            self._logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log critical message."""
        if self._logger:
            self._logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with traceback."""
        if self._logger:
            self._logger.exception(message, *args, **kwargs)

    def log(self, level: int, message: str, *args: Any, **kwargs: Any) -> None:
        """Log message at specified level."""
        if self._logger:
            self._logger.log(level, message, *args, **kwargs)


def get_logger(
    name: str = "FlibustaUserAssistBot",
    level: str = DEFAULT_LOG_LEVEL,
    file_path: Optional[Path] = None,
    max_size_mb: int = 10,
    backup_count: int = 5,
    console_output: bool = True,
    file_output: bool = True,
) -> logging.Logger:
    """
    Convenience function to get a configured logger.

    Args:
        name: Logger name
        level: Logging level
        file_path: Path to log file
        max_size_mb: Maximum log file size in MB
        backup_count: Number of backup files to keep
        console_output: Enable console output
        file_output: Enable file output

    Returns:
        Configured logger instance
    """
    bot_logger = BotLogger(
        name=name,
        level=level,
        file_path=file_path,
        max_size_mb=max_size_mb,
        backup_count=backup_count,
        console_output=console_output,
        file_output=file_output,
    )
    return bot_logger.get_logger()


# Global logger instance (initialized on first use)
_global_logger: Optional[BotLogger] = None


def setup_global_logger(
    level: str = DEFAULT_LOG_LEVEL,
    file_path: Optional[Path] = None,
    max_size_mb: int = 10,
    backup_count: int = 5,
    console_output: bool = True,
    file_output: bool = True,
) -> None:
    """
    Set up global logger instance.

    Args:
        level: Logging level
        file_path: Path to log file
        max_size_mb: Maximum log file size in MB
        backup_count: Number of backup files to keep
        console_output: Enable console output
        file_output: Enable file output
    """
    global _global_logger
    _global_logger = BotLogger(
        name="FlibustaUserAssistBot",
        level=level,
        file_path=file_path,
        max_size_mb=max_size_mb,
        backup_count=backup_count,
        console_output=console_output,
        file_output=file_output,
    )


def get_global_logger() -> BotLogger:
    """
    Get global logger instance.

    Returns:
        Global logger instance

    Raises:
        RuntimeError: If global logger not initialized
    """
    if _global_logger is None:
        raise RuntimeError("Global logger not initialized. Call setup_global_logger() first.")
    return _global_logger


__all__ = [
    "BotLogger",
    "get_logger",
    "setup_global_logger",
    "get_global_logger",
]
