"""
Group message handler for FlibustaUserAssistBot.

This module provides handlers for processing group messages, detecting bot mentions,
and generating AI-powered responses with reply buttons.
"""

import asyncio
from typing import Any, Dict, Optional
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup
from aiogram.filters import Command

from ..core.config import Config
from ..core.logger import BotLogger
from ..core.types import ChatContext, TelegramMessage
from ..services.message_analyzer import MessageAnalyzer, get_message_analyzer
from ..services.ai_assistant import AIAssistantService, get_ai_assistant
from ..services.button_generator import ButtonGenerator, get_button_generator

# Create router for group messages
group_router = Router()
group_router.name = "Group Messages Router"


class GroupMessageHandler:
    """
    Handler for processing group messages and generating AI responses.

    Features:
    - Detects bot mentions in group chats
    - Extracts conversation context
    - Generates AI responses
    - Creates reply buttons for target bot
    - Handles rate limiting and error cases
    """

    def __init__(self, config: Config):
        """
        Initialize group message handler.

        Args:
            config: Bot configuration
        """
        self.config = config
        self.logger = BotLogger(__name__).get_logger()

        # Initialize services
        self.message_analyzer = MessageAnalyzer(config)
        self.ai_assistant = None  # Will be set later
        self.button_generator = ButtonGenerator(config)

        # Target bot username
        self.target_bot_username = config.bot.target_bot_username
        self.bot_username = config.bot.username

        self.logger.info(
            f"GroupMessageHandler initialized - target_bot: {self.target_bot_username}, "
            f"bot_username: {self.bot_username}"
        )

    def setup(self, ai_assistant: AIAssistantService) -> None:
        """
        Set up AI assistant service.

        Args:
            ai_assistant: AI assistant service instance
        """
        self.ai_assistant = ai_assistant
        self.logger.info("AI assistant service configured")

    async def handle_group_message(self, message: Message) -> Optional[Message]:
        """
        Handle group message and generate response if appropriate.

        Args:
            message: Telegram Message object

        Returns:
            Response message or None if no response needed
        """
        try:
            # Check if this is a group message
            if not self._is_group_message(message):
                self.logger.debug(f"Not a group message - chat_id: {message.chat.id}")
                return None

            # Check if bot is mentioned or message is a reply to bot
            if not self._is_bot_mention(message):
                self.logger.debug(f"No bot mention - chat_id: {message.chat.id}")
                return None

            # Check if message is from target bot (avoid loops)
            if self._is_from_target_bot(message):
                self.logger.debug(f"Message from target bot - chat_id: {message.chat.id}")
                return None

            # Extract context from message
            context = await self._extract_context(message)

            # Generate AI response
            ai_response = await self._generate_ai_response(context)

            # Generate reply buttons
            keyboard = self._generate_reply_buttons(ai_response)

            # Send response with buttons
            return await self._send_response(message, ai_response, keyboard)

        except Exception as e:
            self.logger.error(
                f"Error handling group message - chat_id: {message.chat.id}, " f"error: {str(e)}"
            )
            return None

    def _is_group_message(self, message: Message) -> bool:
        """
        Check if message is from a group chat.

        Args:
            message: Telegram Message object

        Returns:
            True if message is from group, False otherwise
        """
        if not message.chat:
            return False

        # Group chats have negative IDs
        return message.chat.id < 0 and not str(message.chat.id).startswith("-100")

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

        text = message.text.lower()
        bot_username = self.bot_username.lower()

        # Check for direct mention
        if f"@{bot_username}" in text:
            return True

        # Check for reply to bot message
        if message.reply_to_message and message.reply_to_message.from_user:
            if message.reply_to_message.from_user.username == bot_username[1:]:
                return True

        return False

    def _is_from_target_bot(self, message: Message) -> bool:
        """
        Check if message is from target bot (to avoid loops).

        Args:
            message: Telegram Message object

        Returns:
            True if message is from target bot, False otherwise
        """
        if not message.from_user:
            return False

        target_username = self.target_bot_username.lower()
        sender_username = message.from_user.username

        return sender_username and sender_username.lower() == target_username[1:]

    async def _extract_context(self, message: Message) -> ChatContext:
        """
        Extract conversation context from message.

        Args:
            message: Telegram Message object

        Returns:
            ChatContext object
        """
        # Get message history (simplified for this implementation)
        message_history = await self._get_message_history(message)

        # Use message analyzer to extract context
        context = await self.message_analyzer.extract_context(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            message_text=message.text or "",
            message_history=message_history,
        )

        self.logger.debug(
            f"Context extracted - chat_id: {message.chat.id}, "
            f"user_id: {message.from_user.id}, "
            f"history_count: {len(context.message_history)}"
        )

        return context

    async def _get_message_history(self, message: Message) -> List[TelegramMessage]:
        """
        Get recent message history for context.

        Args:
            message: Current Telegram Message

        Returns:
            List of TelegramMessage objects
        """
        # In a real implementation, this would fetch from Telegram API
        # For now, return empty list (context window handled by message analyzer)
        return []

    async def _generate_ai_response(self, context: ChatContext) -> Any:
        """
        Generate AI response for given context.

        Args:
            context: ChatContext object

        Returns:
            AIResponse object
        """
        if not self.ai_assistant:
            raise RuntimeError("AI assistant service not configured")

        return await self.ai_assistant.get_ai_response(context)

    def _generate_reply_buttons(self, ai_response: Any) -> Optional[ReplyKeyboardMarkup]:
        """
        Generate reply buttons from AI response.

        Args:
            ai_response: AIResponse object

        Returns:
            ReplyKeyboardMarkup or None
        """
        return self.button_generator.generate_reply_buttons(ai_response)

    async def _send_response(
        self, message: Message, ai_response: Any, keyboard: Optional[ReplyKeyboardMarkup]
    ) -> Message:
        """
        Send response message with reply buttons.

        Args:
            message: Original Telegram Message
            ai_response: AIResponse object
            keyboard: ReplyKeyboardMarkup or None

        Returns:
            Sent Message object
        """
        # Prepare response text
        response_text = ai_response.text

        # Send message with keyboard
        sent_message = await message.answer(
            text=response_text,
            reply_markup=keyboard,
            parse_mode=None,  # No markdown to avoid formatting issues
            disable_web_page_preview=True,
        )

        self.logger.info(
            f"Response sent - chat_id: {message.chat.id}, "
            f"message_id: {sent_message.message_id}, "
            f"has_buttons: {keyboard is not None}"
        )

        return sent_message

    async def handle_start_command(self, message: Message) -> Message:
        """
        Handle /start command in groups.

        Args:
            message: Telegram Message object

        Returns:
            Response message
        """
        welcome_text = (
            f"👋 Привет! Я {self.bot_username} - помощник для работы с {self.target_bot_username}. "
            f"Упомяните меня в сообщении, и я помогу сформулировать запрос!"
        )

        return await message.answer(welcome_text)

    async def handle_help_command(self, message: Message) -> Message:
        """
        Handle /help command in groups.

        Args:
            message: Telegram Message object

        Returns:
            Response message
        """
        help_text = (
            f"💡 Как использовать {self.bot_username}:\n\n"
            f"1. Упомяните меня в сообщении: @{self.bot_username[1:]} найти книгу\n"
            f"2. Я проанализирую ваш запрос\n"
            f"3. Предложу варианты команд для {self.target_bot_username}\n"
            f"4. Выберите нужную команду из кнопок\n\n"
            f"Пример: '@{self.bot_username[1:]} посоветуй фантастику'"
        )

        return await message.answer(help_text)


# Register handlers
def register_group_handlers(router: Router, handler: GroupMessageHandler) -> None:
    """
    Register group message handlers.

    Args:
        router: Aiogram Router
        handler: GroupMessageHandler instance
    """
    # Register command handlers
    router.message.register(handler.handle_start_command, Command("start"))
    router.message.register(handler.handle_help_command, Command("help"))

    # Register message handler for bot mentions
    router.message.register(
        handler.handle_group_message,
        F.chat.type.in_({"group", "supergroup"}),
        lambda message: handler._is_bot_mention(message),
    )


# Global instance for convenience
group_handler: GroupMessageHandler | None = None


def get_group_handler() -> GroupMessageHandler:
    """
    Get global group handler instance.

    Returns:
        GroupMessageHandler instance

    Raises:
        RuntimeError: If handler is not initialized
    """
    global group_handler
    if group_handler is None:
        raise RuntimeError("GroupMessageHandler not initialized")
    return group_handler


__all__ = [
    "GroupMessageHandler",
    "group_router",
    "register_group_handlers",
    "get_group_handler",
    "group_handler",
]
