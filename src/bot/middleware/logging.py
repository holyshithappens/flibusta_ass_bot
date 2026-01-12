"""
Logging middleware for FlibustaUserAssistBot.

This module provides middleware for logging all incoming Telegram events,
tracking response times, and collecting performance metrics.
"""

import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Update, User, Chat, Message

from ..core.logger import BotLogger
from ..core.config import Config


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware for logging all incoming Telegram updates and tracking performance.

    Features:
    - Logs all incoming updates with detailed information
    - Tracks request/response timing
    - Collects performance metrics
    - Handles different update types (messages, callbacks, etc.)
    - Configurable logging level
    """

    def __init__(self, config: Config):
        """
        Initialize logging middleware.

        Args:
            config: Bot configuration
        """
        self.config = config
        self.logger = BotLogger(__name__).get_logger()
        self.metrics = {
            "total_updates": 0,
            "message_updates": 0,
            "callback_updates": 0,
            "other_updates": 0,
            "processing_times": [],
            "last_update_time": 0.0,
        }

        self.logger.info(
            f"LoggingMiddleware initialized - log_level: {self.config.logging.level}, "
            f"metrics_enabled: {self.config.development.debug}"
        )

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: object,
        data: Dict[str, Any],
    ) -> Any:
        """
        Process incoming update and log details.

        Args:
            handler: Next handler in the chain
            event: Telegram Update object
            data: Additional data dictionary

        Returns:
            Result from handler
        """
        start_time = time.time()
        update_type = self._get_update_type(event)
        update_id = getattr(event, "update_id", "unknown")

        # Increment metrics
        self.metrics["total_updates"] = self.metrics.get("total_updates", 0) + 1
        self.metrics[f"{update_type}_updates"] = self.metrics.get(f"{update_type}_updates", 0) + 1

        # Extract user and chat information
        user_info = self._extract_user_info(event)
        chat_info = self._extract_chat_info(event)

        # Log update details
        self._log_update_details(event, update_type, user_info, chat_info)

        try:
            # Call next handler
            result = await handler(event, data)

            # Calculate processing time
            processing_time = time.time() - start_time
            self.metrics["processing_times"] = self.metrics.get("processing_times", []) + [
                processing_time
            ]
            self.metrics["last_update_time"] = start_time

            # Log successful processing
            self.logger.debug(
                f"Update processed successfully - update_id: {update_id}, "
                f"type: {update_type}, processing_time: {processing_time:.3f}s"
            )

            return result

        except Exception as e:
            # Log error
            self.logger.error(
                f"Error processing update - update_id: {update_id}, "
                f"type: {update_type}, error: {str(e)}"
            )
            raise

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
        elif event.chosen_inline_result:
            return "chosen_inline_result"
        elif event.edited_message:
            return "edited_message"
        elif event.channel_post:
            return "channel_post"
        elif event.edited_channel_post:
            return "edited_channel_post"
        elif event.shipping_query:
            return "shipping_query"
        elif event.pre_checkout_query:
            return "pre_checkout_query"
        elif event.poll:
            return "poll"
        elif event.poll_answer:
            return "poll_answer"
        elif event.my_chat_member:
            return "my_chat_member"
        elif event.chat_member:
            return "chat_member"
        elif event.chat_join_request:
            return "chat_join_request"
        else:
            return "unknown"

    def _extract_user_info(self, event: Update) -> Dict[str, Any]:
        """
        Extract user information from update.

        Args:
            event: Telegram Update object

        Returns:
            Dictionary with user information
        """
        user_info: Dict[str, Any] = {
            "id": None,
            "username": None,
            "first_name": None,
            "last_name": None,
        }

        # Try to get user from different sources
        user_sources = [
            getattr(event, "message", None) and getattr(event.message, "from_user", None),
            getattr(event, "callback_query", None)
            and getattr(event.callback_query, "from_user", None),
            getattr(event, "inline_query", None) and getattr(event.inline_query, "from_user", None),
            getattr(event, "chosen_inline_result", None)
            and getattr(event.chosen_inline_result, "from_user", None),
            getattr(event, "edited_message", None)
            and getattr(event.edited_message, "from_user", None),
            getattr(event, "channel_post", None) and getattr(event.channel_post, "from_user", None),
            getattr(event, "edited_channel_post", None)
            and getattr(event.edited_channel_post, "from_user", None),
            getattr(event, "shipping_query", None)
            and getattr(event.shipping_query, "from_user", None),
            getattr(event, "pre_checkout_query", None)
            and getattr(event.pre_checkout_query, "from_user", None),
            getattr(event, "poll_answer", None) and getattr(event.poll_answer, "user", None),
            getattr(event, "my_chat_member", None)
            and getattr(event.my_chat_member, "from_user", None),
            getattr(event, "chat_member", None) and getattr(event.chat_member, "from_user", None),
            getattr(event, "chat_join_request", None)
            and getattr(event.chat_join_request, "from_user", None),
        ]

        user = next((u for u in user_sources if u is not None), None)

        if user:
            user_info.update(
                {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_bot": user.is_bot,
                    "language_code": getattr(user, "language_code", None),
                }
            )

        return user_info

    def _extract_chat_info(self, event: Update) -> Dict[str, Any]:
        """
        Extract chat information from update.

        Args:
            event: Telegram Update object

        Returns:
            Dictionary with chat information
        """
        chat_info = {"id": None, "type": None, "title": None, "username": None}

        # Try to get chat from different sources
        chat_sources = [
            event.message.chat if event.message else None,
            (
                event.callback_query.message.chat
                if event.callback_query and event.callback_query.message
                else None
            ),
            event.edited_message.chat if event.edited_message else None,
            event.channel_post.chat if event.channel_post else None,
            event.edited_channel_post.chat if event.edited_channel_post else None,
            event.my_chat_member.chat if event.my_chat_member else None,
            event.chat_member.chat if event.chat_member else None,
            event.chat_join_request.chat if event.chat_join_request else None,
        ]

        chat = next((c for c in chat_sources if c is not None), None)

        if chat:
            chat_info.update(
                {
                    "id": chat.id,
                    "type": chat.type,
                    "title": chat.title,
                    "username": chat.username,
                    "is_forum": getattr(chat, "is_forum", False),
                }
            )

        return chat_info

    def _log_update_details(
        self, event: Update, update_type: str, user_info: Dict[str, Any], chat_info: Dict[str, Any]
    ) -> None:
        """
        Log detailed information about the incoming update.

        Args:
            event: Telegram Update object
            update_type: Type of update
            user_info: Extracted user information
            chat_info: Extracted chat information
        """
        update_id = getattr(event, "update_id", "unknown")

        # Basic update info
        log_data = {
            "update_id": update_id,
            "type": update_type,
            "user": user_info,
            "chat": chat_info,
        }

        # Add message-specific details
        if update_type == "message" and hasattr(event, "message"):
            message = event.message
            log_data.update(
                {
                    "message_id": getattr(message, "message_id", None),
                    "text": getattr(message, "text", None),
                    "entities": len(getattr(message, "entities", [])),
                    "is_bot_mention": self._is_bot_mention(message),
                    "is_target_bot_command": self._is_target_bot_command(message),
                    "reply_to_message_id": getattr(message, "reply_to_message", None)
                    and getattr(message.reply_to_message, "message_id", None),
                }
            )

        # Add callback-specific details
        elif update_type == "callback" and event.callback_query:
            callback = event.callback_query
            log_data.update(
                {
                    "callback_id": callback.id,
                    "callback_data": callback.data,
                    "message_id": callback.message.message_id if callback.message else None,
                }
            )

        # Log at appropriate level based on configuration
        if self.config.development.verbose:
            self.logger.info(f"Incoming update - {log_data}")
        else:
            self.logger.debug(f"Incoming update - update_id: {update_id}, type: {update_type}")

    def _is_bot_mention(self, message: Message) -> bool:
        """
        Check if message mentions our bot.

        Args:
            message: Telegram Message object

        Returns:
            True if message mentions our bot, False otherwise
        """
        if not message.text:
            return False

        bot_username = self.config.bot.username.lower()
        text = message.text.lower()

        # Check for direct mention
        if f"@{bot_username}" in text:
            return True

        # Check for reply to bot message
        if message.reply_to_message and message.reply_to_message.from_user:
            if message.reply_to_message.from_user.username == self.config.bot.username[1:]:
                return True

        return False

    def _is_target_bot_command(self, message: Message) -> bool:
        """
        Check if message is a command for target bot.

        Args:
            message: Telegram Message object

        Returns:
            True if message is target bot command, False otherwise
        """
        if not message.text:
            return False

        target_bot = self.config.bot.target_bot_username.lower()
        text = message.text.lower()

        # Check for command format: /command@target_bot
        if text.startswith("/") and f"@{target_bot}" in text:
            return True

        # Check for mention format: @target_bot command
        if text.startswith(f"@{target_bot}"):
            return True

        return False

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.

        Returns:
            Dictionary with performance metrics
        """
        metrics = self.metrics.copy()

        # Calculate averages
        processing_times = metrics.get("processing_times", [])
        if processing_times:
            avg_time = sum(processing_times) / len(processing_times)
            metrics["avg_processing_time"] = avg_time
        else:
            metrics["avg_processing_time"] = 0.0

        return metrics

    def reset_metrics(self) -> None:
        """
        Reset performance metrics.
        """
        self.metrics = {
            "total_updates": 0,
            "message_updates": 0,
            "callback_updates": 0,
            "other_updates": 0,
            "processing_times": [],
            "last_update_time": 0.0,
        }
        self.logger.debug("Performance metrics reset")


# Global instance for convenience
logging_middleware: LoggingMiddleware | None = None


def get_logging_middleware() -> LoggingMiddleware:
    """
    Get global logging middleware instance.

    Returns:
        LoggingMiddleware instance

    Raises:
        RuntimeError: If middleware is not initialized
    """
    global logging_middleware
    if logging_middleware is None:
        raise RuntimeError("LoggingMiddleware not initialized")
    return logging_middleware


__all__ = ["LoggingMiddleware", "get_logging_middleware", "logging_middleware"]
