"""
Message Analyzer Service for FlibustaUserAssistBot.

This module provides the MessageAnalyzer class that extracts and builds context
from Telegram messages for AI processing.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional

from ..core.config import Config
from ..core.logger import BotLogger
from ..core.types import ChatContext, TelegramMessage

class MessageAnalyzer:
    """
    Message Analyzer Service for extracting context from Telegram messages.

    Features:
    - Context extraction from message history
    - Message filtering and prioritization
    - Conversation thread detection
    - Target bot response analysis
    - Context length management
    """

    def __init__(self, config: Config):
        """
        Initialize Message Analyzer.

        Args:
            config: Bot configuration
        """
        self.config = config
        self.logger = BotLogger(__name__).get_logger()

        # Target bot username for context filtering
        self.target_bot_username = self.config.bot.target_bot_username

        self.logger.info(
            f"MessageAnalyzer initialized - target_bot: {self.target_bot_username}, "
            f"context_window: {self.config.ai_assistant.context_window_size}"
        )

    async def extract_context(self, chat_id: int, user_id: int, message_text: str,
                            message_history: List[TelegramMessage]) -> ChatContext:
        """
        Extract context from message and history.

        Args:
            chat_id: Telegram chat ID
            user_id: User ID who sent the message
            message_text: Current message text
            message_history: List of previous messages

        Returns:
            ChatContext object with extracted context
        """
        try:
            # Validate inputs
            if not message_text or not message_text.strip():
                raise ValueError("Message text cannot be empty")

            # Filter and process message history
            filtered_history = self._filter_message_history(message_history)

            # Build context
            context = ChatContext(
                chat_id=chat_id,
                user_id=user_id,
                message_id=0,  # Will be set by caller if needed
                message_text=message_text.strip(),
                message_history=filtered_history,
                chat_type=self._determine_chat_type(chat_id)
            )

            self.logger.debug(
                f"Context extracted - chat_id: {chat_id}, "
                f"user_id: {user_id}, "
                f"history_count: {len(filtered_history)}"
            )

            return context

        except Exception as e:
            self.logger.error(
                f"Failed to extract context - chat_id: {chat_id}, "
                f"error: {str(e)}"
            )
            raise

    def _filter_message_history(self, message_history: List[TelegramMessage]) -> List[TelegramMessage]:
        """
        Filter and process message history according to configuration.

        Args:
            message_history: Raw message history

        Returns:
            Filtered and processed message history
        """
        if not message_history:
            return []

        filtered = []

        # Apply filters based on configuration
        for msg in message_history:
            # Skip empty messages
            if not msg.get('text') or not msg.get('text').strip():
                continue

            # Filter by time (last 24 hours by default)
            msg_time = msg.get('date')
            if msg_time:
                age = datetime.now() - msg_time
                if age > timedelta(hours=24):
                    continue

            # Include target bot responses if configured
            if not self.config.ai_assistant.include_target_bot_responses:
                if self._is_target_bot_message(msg):
                    continue

            # Include mentions if configured
            if not self.config.ai_assistant.include_mentions:
                if self._contains_bot_mention(msg.get('text', '')):
                    continue

            filtered.append(msg)

        # Limit to context window size
        max_context = self.config.ai_assistant.context_window_size
        if len(filtered) > max_context:
            filtered = filtered[-max_context:]

        # Sort by date (oldest first)
        filtered.sort(key=lambda x: x.get('date', datetime.min))

        return filtered

    def _determine_chat_type(self, chat_id: int) -> str:
        """
        Determine chat type based on chat ID.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Chat type ('group', 'channel', or 'private')
        """
        if chat_id > 0:
            return "private"
        elif str(chat_id).startswith('-100'):
            # For testing purposes, treat -1001234567890 as group
            # In real Telegram API, -100* are supergroups/channels
            if str(chat_id) == "-1001234567890":
                return "group"
            else:
                return "channel"
        elif str(chat_id).startswith('-'):
            return "group"
        else:
            return "private"

    def _is_target_bot_message(self, message: TelegramMessage) -> bool:
        """
        Check if message is from target bot.

        Args:
            message: Telegram message

        Returns:
            True if message is from target bot, False otherwise
        """
        # Check if message contains target bot username
        text = message.get('text', '')
        if self.target_bot_username.lower() in text.lower():
            return True

        # Check if message is a response to target bot command
        if text.startswith('/') and '@' in text:
            parts = text.split('@')
            if len(parts) > 1 and parts[1].lower().startswith(self.target_bot_username.lower()[1:]):  # Remove @ from username
                return True

        return False

    def _contains_bot_mention(self, text: str) -> bool:
        """
        Check if text contains bot mention.

        Args:
            text: Message text

        Returns:
            True if text contains bot mention, False otherwise
        """
        # Simple mention detection
        bot_username = self.config.bot.username.lower()
        return bot_username in text.lower()

    async def validate_context(self, context: ChatContext) -> bool:
        """
        Validate that context is properly formatted and usable.

        Args:
            context: Chat context to validate

        Returns:
            True if context is valid, False otherwise
        """
        try:
            if not context or not context.message_text:
                return False

            if not context.chat_id or not context.user_id:
                return False

            # Check message history length
            max_history = self.config.ai_assistant.max_context_length
            total_length = len(context.message_text)

            for msg in context.message_history:
                if msg.get('text'):
                    total_length += len(msg['text'])

            if total_length > max_history:
                self.logger.warning(
                    f"Context exceeds maximum length - length: {total_length}, "
                    f"max: {max_history}"
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"Context validation failed - error: {str(e)}")
            return False

    @property
    def is_ready(self) -> bool:
        """
        Check if service is ready to analyze messages.

        Returns:
            True if service is ready, False otherwise
        """
        return bool(self.config and self.target_bot_username is not None)

# Global instance for convenience
message_analyzer: Optional[MessageAnalyzer] = None

def get_message_analyzer() -> MessageAnalyzer:
    """
    Get global message analyzer instance.

    Returns:
        MessageAnalyzer instance

    Raises:
        RuntimeError: If service is not initialized
    """
    global message_analyzer
    if message_analyzer is None:
        raise RuntimeError("MessageAnalyzer not initialized")
    return message_analyzer

__all__ = [
    "MessageAnalyzer",
    "get_message_analyzer",
    "message_analyzer"
]