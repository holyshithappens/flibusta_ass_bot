"""
Error handler middleware for FlibustaUserAssistBot.

This module provides global exception handling middleware that catches
and processes errors, provides user-friendly error messages, and ensures
graceful degradation of bot functionality.
"""

import traceback
from typing import Any, Awaitable, Callable, Dict, Optional
from aiogram import BaseMiddleware
from aiogram.types import Update, Message
from aiogram.exceptions import TelegramAPIError

from ..core.logger import BotLogger
from ..core.config import Config


class ErrorHandlerMiddleware(BaseMiddleware):
    """
    Global exception handling middleware.

    Features:
    - Catches all unhandled exceptions
    - Provides user-friendly error messages
    - Logs detailed error information
    - Implements graceful degradation
    - Handles Telegram API errors specifically
    - Supports custom error messages per error type
    """

    def __init__(self, config: Config):
        """
        Initialize error handler middleware.

        Args:
            config: Bot configuration
        """
        self.config = config
        self.logger = BotLogger(__name__).get_logger()

        # Custom error messages
        self.error_messages = {
            "default": "❌ Ошибка обработки запроса. Пожалуйста, попробуйте позже.",
            "api_error": "❌ Ошибка связи с Telegram. Попробуйте позже.",
            "validation_error": "❌ Некорректный запрос. Проверьте формат команды.",
            "timeout_error": "❌ Превышено время ожидания. Сервер занят.",
            "rate_limit_error": "❌ Превышен лимит запросов. Подождите немного.",
            "ai_error": "❌ Ошибка ИИ. Попробуйте сформулировать запрос иначе.",
            "config_error": "❌ Ошибка конфигурации. Обратитесь к администратору.",
        }

        self.logger.info(
            f"ErrorHandlerMiddleware initialized - debug_mode: {self.config.development.debug}, "
            f"log_security_events: {self.config.security.log_security_events}"
        )

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: object,
        data: Dict[str, Any],
    ) -> Any:
        """
        Process update and handle any exceptions.

        Args:
            handler: Next handler in the chain
            event: Telegram Update object
            data: Additional data dictionary

        Returns:
            Result from handler or None if error occurred
        """
        try:
            return await handler(event, data)
        except Exception as e:
            return await self._handle_error(e, event, data)

    async def _handle_error(
        self, error: Exception, event: Update, data: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Handle error and provide appropriate response.

        Args:
            error: Exception that occurred
            event: Telegram Update object
            data: Additional data dictionary

        Returns:
            None (error response is sent directly)
        """
        # Log the error
        self._log_error(error, event)

        # Send user-friendly error message if possible
        await self._send_error_message(error, event)

        # Return None to stop further processing
        return None

    def _log_error(self, error: Exception, event: Update) -> None:
        """
        Log error with detailed information.

        Args:
            error: Exception that occurred
            event: Telegram Update object
        """
        update_id = getattr(event, "update_id", "unknown")
        update_type = self._get_update_type(event)

        # Log at ERROR level
        self.logger.error(
            f"Error processing update - update_id: {update_id}, "
            f"type: {update_type}, error: {str(error)}"
        )

        # Log full traceback in debug mode
        if self.config.development.debug:
            self.logger.error(f"Full traceback - {traceback.format_exc()}")

        # Log security events if configured
        if self.config.security.log_security_events and self._is_security_error(error):
            self.logger.warning(
                f"Security event detected - update_id: {update_id}, "
                f"error_type: {type(error).__name__}"
            )

    async def _send_error_message(self, error: Exception, event: Update) -> None:
        """
        Send user-friendly error message.

        Args:
            error: Exception that occurred
            event: Telegram Update object
        """
        # Only send error messages for message updates
        if not event.message:
            return

        message = event.message

        # Get appropriate error message
        error_msg = self._get_error_message(error)

        try:
            # Send error message to the same chat
            await message.answer(
                text=error_msg,
                parse_mode=None,  # No markdown to avoid formatting errors
                disable_web_page_preview=True,
            )

            self.logger.debug(
                f"Sent error message - chat_id: {message.chat.id}, "
                f"message_id: {message.message_id}"
            )

        except TelegramAPIError as e:
            # If we can't send error message, log it
            self.logger.error(
                f"Failed to send error message - chat_id: {message.chat.id}, " f"error: {str(e)}"
            )

    def _get_error_message(self, error: Exception) -> str:
        """
        Get appropriate error message based on error type.

        Args:
            error: Exception that occurred

        Returns:
            User-friendly error message
        """
        error_type = type(error).__name__

        # Map specific error types to messages
        if isinstance(error, TelegramAPIError):
            return self.error_messages["api_error"]
        elif isinstance(error, ValueError):
            return self.error_messages["validation_error"]
        elif isinstance(error, TimeoutError):
            return self.error_messages["timeout_error"]
        elif isinstance(error, RuntimeError) and "rate limit" in str(error).lower():
            return self.error_messages["rate_limit_error"]
        elif isinstance(error, RuntimeError) and "ai" in str(error).lower():
            return self.error_messages["ai_error"]
        elif isinstance(error, (FileNotFoundError, KeyError, AttributeError)):
            return self.error_messages["config_error"]
        else:
            return self.error_messages["default"]

    def _get_update_type(self, event: Update) -> str:
        """
        Determine the type of Telegram update.

        Args:
            event: Telegram Update object

        Returns:
            Update type string
        """
        if event.message:
            return "message"
        elif event.callback_query:
            return "callback"
        elif event.inline_query:
            return "inline_query"
        elif event.edited_message:
            return "edited_message"
        elif event.channel_post:
            return "channel_post"
        elif event.edited_channel_post:
            return "edited_channel_post"
        else:
            return "unknown"

    def _is_security_error(self, error: Exception) -> bool:
        """
        Check if error is security-related.

        Args:
            error: Exception that occurred

        Returns:
            True if error is security-related, False otherwise
        """
        error_str = str(error).lower()

        # Security-related error patterns
        security_patterns = [
            "authentication",
            "authorization",
            "permission",
            "access denied",
            "forbidden",
            "security",
            "token invalid",
            "unauthorized",
            "hacking",
            "intrusion",
            "malicious",
        ]

        return any(pattern in error_str for pattern in security_patterns)

    def add_custom_error_message(self, error_type: str, message: str) -> None:
        """
        Add custom error message for specific error type.

        Args:
            error_type: Error type key
            message: Custom error message
        """
        self.error_messages[error_type] = message
        self.logger.debug(f"Added custom error message - type: {error_type}")

    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error statistics (would need to be tracked in actual implementation).

        Returns:
            Dictionary with error statistics
        """
        # In a real implementation, this would track error counts by type
        return {"total_errors": 0, "by_type": {}, "last_error_time": 0.0}


# Global instance for convenience
error_handler_middleware: ErrorHandlerMiddleware | None = None


def get_error_handler_middleware() -> ErrorHandlerMiddleware:
    """
    Get global error handler middleware instance.

    Returns:
        ErrorHandlerMiddleware instance

    Raises:
        RuntimeError: If middleware is not initialized
    """
    global error_handler_middleware
    if error_handler_middleware is None:
        raise RuntimeError("ErrorHandlerMiddleware not initialized")
    return error_handler_middleware


__all__ = ["ErrorHandlerMiddleware", "get_error_handler_middleware", "error_handler_middleware"]
