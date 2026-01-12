"""
Channel comment handler for FlibustaUserAssistBot.

This module provides handlers for processing comments on channel posts,
providing context-aware suggestions, and generating reply buttons.
"""

from typing import Any, Dict, List, Optional
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup

from ..core.config import Config
from ..core.logger import BotLogger
from ..core.types import ChatContext, TelegramMessage
from ..services.message_analyzer import MessageAnalyzer, get_message_analyzer
from ..services.ai_assistant import AIAssistantService, get_ai_assistant
from ..services.button_generator import ButtonGenerator, get_button_generator

# Create router for channel comments
channel_router = Router()
channel_router.name = "Channel Comments Router"


class ChannelCommentHandler:
    """
    Handler for processing channel post comments and generating AI responses.

    Features:
    - Detects comments on channel posts
    - Extracts context from channel post and comment
    - Generates context-aware AI suggestions
    - Creates reply buttons for target bot
    - Handles channel-specific logic
    """

    def __init__(self, config: Config):
        """
        Initialize channel comment handler.

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
            f"ChannelCommentHandler initialized - target_bot: {self.target_bot_username}, "
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

    async def handle_channel_comment(self, message: Message) -> Optional[Message]:
        """
        Handle channel comment and generate response if appropriate.

        Args:
            message: Telegram Message object (channel comment)

        Returns:
            Response message or None if no response needed
        """
        try:
            # Check if this is a channel comment
            if not self._is_channel_comment(message):
                self.logger.debug(f"Not a channel comment - chat_id: {message.chat.id}")
                return None

            # Check if bot is mentioned or message is a reply to bot
            if not self._is_bot_mention(message):
                self.logger.debug(f"No bot mention - chat_id: {message.chat.id}")
                return None

            # Check if message is from target bot (avoid loops)
            if self._is_from_target_bot(message):
                self.logger.debug(f"Message from target bot - chat_id: {message.chat.id}")
                return None

            # Extract context from message (including channel post)
            context = await self._extract_context(message)

            # Generate AI response
            ai_response = await self._generate_ai_response(context)

            # Generate reply buttons
            keyboard = self._generate_reply_buttons(ai_response)

            # Send response with buttons
            return await self._send_response(message, ai_response, keyboard)

        except Exception as e:
            self.logger.error(
                f"Error handling channel comment - chat_id: {message.chat.id}, " f"error: {str(e)}"
            )
            return None

    def _is_channel_comment(self, message: Message) -> bool:
        """
        Check if message is a comment on a channel post.

        Args:
            message: Telegram Message object

        Returns:
            True if message is channel comment, False otherwise
        """
        if not message.chat:
            return False

        # Channel comments have IDs starting with -100
        chat_id_str = str(message.chat.id)
        return chat_id_str.startswith("-100") and message.reply_to_message

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
        Extract conversation context from channel comment.

        Args:
            message: Telegram Message object (comment)

        Returns:
            ChatContext object
        """
        # Get message history including the channel post being commented on
        message_history = await self._get_channel_context(message)

        # Use message analyzer to extract context
        context = await self.message_analyzer.extract_context(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            message_text=message.text or "",
            message_history=message_history,
        )

        self.logger.debug(
            f"Channel context extracted - chat_id: {message.chat.id}, "
            f"user_id: {message.from_user.id}, "
            f"history_count: {len(context.message_history)}"
        )

        return context

    async def _get_channel_context(self, message: Message) -> List[TelegramMessage]:
        """
        Get channel context including the post being commented on.

        Args:
            message: Comment message

        Returns:
            List of TelegramMessage objects
        """
        context_messages = []

        # Add the channel post being commented on
        if message.reply_to_message:
            post_message = {
                "message_id": message.reply_to_message.message_id,
                "chat_id": message.chat.id,
                "user_id": (
                    message.reply_to_message.from_user.id
                    if message.reply_to_message.from_user
                    else 0
                ),
                "text": message.reply_to_message.text,
                "date": message.reply_to_message.date,
                "chat_type": "channel",
                "reply_to_message_id": None,
                "from_user": {
                    "id": (
                        message.reply_to_message.from_user.id
                        if message.reply_to_message.from_user
                        else 0
                    ),
                    "username": (
                        message.reply_to_message.from_user.username
                        if message.reply_to_message.from_user
                        else None
                    ),
                    "first_name": (
                        message.reply_to_message.from_user.first_name
                        if message.reply_to_message.from_user
                        else None
                    ),
                    "last_name": (
                        message.reply_to_message.from_user.last_name
                        if message.reply_to_message.from_user
                        else None
                    ),
                    "is_bot": (
                        message.reply_to_message.from_user.is_bot
                        if message.reply_to_message.from_user
                        else False
                    ),
                },
            }
            context_messages.append(post_message)

        return context_messages

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
        # Prepare response text with channel context
        response_text = f"📌 В ответ на сообщение:\n{ai_response.text}"

        # Send message with keyboard
        sent_message = await message.answer(
            text=response_text,
            reply_markup=keyboard,
            parse_mode=None,  # No markdown to avoid formatting issues
            disable_web_page_preview=True,
        )

        self.logger.info(
            f"Channel response sent - chat_id: {message.chat.id}, "
            f"message_id: {sent_message.message_id}, "
            f"has_buttons: {keyboard is not None}"
        )

        return sent_message


# Register handlers
def register_channel_handlers(router: Router, handler: ChannelCommentHandler) -> None:
    """
    Register channel comment handlers.

    Args:
        router: Aiogram Router
        handler: ChannelCommentHandler instance
    """
    # Register message handler for channel comments with bot mentions
    router.message.register(
        handler.handle_channel_comment,
        F.chat.type == "channel",
        lambda message: handler._is_bot_mention(message),
    )


# Global instance for convenience
channel_handler: ChannelCommentHandler | None = None


def get_channel_handler() -> ChannelCommentHandler:
    """
    Get global channel handler instance.

    Returns:
        ChannelCommentHandler instance

    Raises:
        RuntimeError: If handler is not initialized
    """
    global channel_handler
    if channel_handler is None:
        raise RuntimeError("ChannelCommentHandler not initialized")
    return channel_handler


__all__ = [
    "ChannelCommentHandler",
    "channel_router",
    "register_channel_handlers",
    "get_channel_handler",
    "channel_handler",
]
