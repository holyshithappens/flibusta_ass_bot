"""
Main entry point for FlibustaUserAssistBot.

This module initializes the aiogram bot and dispatcher, registers all middleware
and handlers, and starts the bot polling.
"""

import asyncio
import signal
import sys
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from .core.config import Config, config
from .core.logger import BotLogger, setup_global_logger
from .clients.openrouter_client import OpenRouterClient
from .services.ai_assistant import AIAssistantService
from .services.message_analyzer import MessageAnalyzer
from .services.button_generator import ButtonGenerator
from .middleware.logging import LoggingMiddleware
from .middleware.error_handler import ErrorHandlerMiddleware
from .handlers.group_messages import GroupMessageHandler, register_group_handlers
from .handlers.channel_comments import ChannelCommentHandler, register_channel_handlers


class FlibustaUserAssistBot:
    """
    Main bot application class.

    Responsibilities:
    - Initialize all bot components
    - Configure aiogram Bot and Dispatcher
    - Register middleware and handlers
    - Start and stop bot gracefully
    - Handle shutdown signals
    """

    def __init__(self):
        """
        Initialize the bot application.
        """
        self.config = config
        self.logger = BotLogger(__name__).get_logger()

        # Initialize components
        self.bot: Optional[Bot] = None
        self.dispatcher: Optional[Dispatcher] = None
        self.openrouter_client: Optional[OpenRouterClient] = None
        self.ai_assistant: Optional[AIAssistantService] = None
        self.message_analyzer: Optional[MessageAnalyzer] = None
        self.button_generator: Optional[ButtonGenerator] = None
        self.logging_middleware: Optional[LoggingMiddleware] = None
        self.error_middleware: Optional[ErrorHandlerMiddleware] = None
        self.group_handler: Optional[GroupMessageHandler] = None
        self.channel_handler: Optional[ChannelCommentHandler] = None

        self.logger.info("FlibustaUserAssistBot initialized")

    async def start(self) -> None:
        """
        Start the bot application.

        Initializes all components, registers handlers, and starts polling.
        """
        try:
            self.logger.info("Starting FlibustaUserAssistBot...")

            # Initialize global logger
            self._setup_logging()

            # Initialize aiogram components
            await self._initialize_aiogram()

            # Initialize services
            await self._initialize_services()

            # Initialize middleware
            self._initialize_middleware()

            # Initialize handlers
            self._initialize_handlers()

            # Register shutdown handler
            self._setup_shutdown_handler()

            # Start polling
            await self._start_polling()

        except Exception as e:
            self.logger.critical(f"Failed to start bot - error: {str(e)}")
            raise

    def _setup_logging(self) -> None:
        """
        Set up global logging configuration.
        """
        setup_global_logger(
            level=self.config.logging.level,
            file_path=self.config.logging.file_path,
            max_size_mb=self.config.logging.max_size_mb,
            backup_count=self.config.logging.backup_count,
            console_output=self.config.logging.console_output,
            file_output=self.config.logging.file_output,
        )

        self.logger.info(
            f"Logging configured - level: {self.config.logging.level}, "
            f"file: {self.config.logging.file_path}"
        )

    async def _initialize_aiogram(self) -> None:
        """
        Initialize aiogram Bot and Dispatcher.
        """
        # Get Telegram bot token from config (loaded from environment)
        telegram_token = self.config.telegram.bot_token
        if not telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured in environment variables")

        # Initialize bot
        self.bot = Bot(token=telegram_token, parse_mode=ParseMode.HTML)

        # Initialize dispatcher with memory storage
        self.dispatcher = Dispatcher(storage=MemoryStorage())

        self.logger.info(
            f"Aiogram initialized - bot: {self.bot.me.username if self.bot else 'unknown'}, "
            f"dispatcher: {type(self.dispatcher).__name__}"
        )

    async def _initialize_services(self) -> None:
        """
        Initialize all bot services.
        """
        # Initialize OpenRouter client
        # Get OpenRouter API key from config (loaded from environment)
        openrouter_api_key = self.config.openrouter.api_key
        if not openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY not configured in environment variables")

        self.openrouter_client = OpenRouterClient(
            api_key=openrouter_api_key,
            model=self.config.openrouter.model,
            timeout=self.config.openrouter.timeout,
            enable_caching=self.config.openrouter.enable_caching,
            cache_ttl=self.config.openrouter.cache_ttl,
        )
        await self.openrouter_client.start()

        # Initialize AI assistant
        self.ai_assistant = AIAssistantService(
            config=self.config, openrouter_client=self.openrouter_client
        )

        # Initialize message analyzer
        self.message_analyzer = MessageAnalyzer(self.config)

        # Initialize button generator
        self.button_generator = ButtonGenerator(self.config)

        self.logger.info("All services initialized")

    def _initialize_middleware(self) -> None:
        """
        Initialize and register middleware.
        """
        if not self.dispatcher:
            raise RuntimeError("Dispatcher not initialized")

        # Initialize logging middleware
        self.logging_middleware = LoggingMiddleware(self.config)
        self.dispatcher.message.middleware(self.logging_middleware)

        # Initialize error handler middleware
        self.error_middleware = ErrorHandlerMiddleware(self.config)
        self.dispatcher.message.middleware(self.error_middleware)

        self.logger.info("Middleware registered")

    def _initialize_handlers(self) -> None:
        """
        Initialize and register handlers.
        """
        if not self.dispatcher:
            raise RuntimeError("Dispatcher not initialized")

        # Initialize group handler
        self.group_handler = GroupMessageHandler(self.config)
        if self.ai_assistant:
            self.group_handler.setup(self.ai_assistant)

        # Initialize channel handler
        self.channel_handler = ChannelCommentHandler(self.config)
        if self.ai_assistant:
            self.channel_handler.setup(self.ai_assistant)

        # Register handlers
        register_group_handlers(self.dispatcher, self.group_handler)
        register_channel_handlers(self.dispatcher, self.channel_handler)

        self.logger.info("Handlers registered")

    def _setup_shutdown_handler(self) -> None:
        """
        Set up graceful shutdown handler.
        """

        def shutdown_handler(signame: str) -> None:
            self.logger.info(f"Received shutdown signal: {signame}")
            asyncio.create_task(self._shutdown())

        # Register signal handlers
        loop = asyncio.get_event_loop()
        for signame in ("SIGINT", "SIGTERM"):
            loop.add_signal_handler(getattr(signal, signame), lambda s=signame: shutdown_handler(s))

        self.logger.info("Shutdown handlers configured")

    async def _start_polling(self) -> None:
        """
        Start bot polling.
        """
        if not self.dispatcher or not self.bot:
            raise RuntimeError("Bot and dispatcher must be initialized")

        self.logger.info("Starting polling...")

        try:
            await self.dispatcher.start_polling(
                bot=self.bot, allowed_updates=self._get_allowed_updates(), skip_updates=True
            )
        except Exception as e:
            self.logger.critical(f"Polling failed - error: {str(e)}")
            raise

    def _get_allowed_updates(self) -> list[str]:
        """
        Get list of allowed update types.

        Returns:
            List of allowed update types
        """
        allowed = ["message"]

        # Check if inline queries are enabled in features
        if hasattr(self.config.features, "inline_queries") and self.config.features.inline_queries:
            allowed.append("inline_query")

        return allowed

    async def _shutdown(self) -> None:
        """
        Perform graceful shutdown.
        """
        self.logger.info("Starting graceful shutdown...")

        try:
            # Close OpenRouter client
            if self.openrouter_client:
                await self.openrouter_client.close()

            # Close dispatcher
            if self.dispatcher:
                await self.dispatcher.stop()

            # Close bot
            if self.bot:
                await self.bot.session.close()

            self.logger.info("Shutdown completed successfully")

        except Exception as e:
            self.logger.error(f"Error during shutdown - error: {str(e)}")

        finally:
            sys.exit(0)

    @property
    def is_running(self) -> bool:
        """
        Check if bot is running.

        Returns:
            True if bot is running, False otherwise
        """
        return self.bot is not None and self.dispatcher is not None


# Global bot instance
bot_app: Optional[FlibustaUserAssistBot] = None


def get_bot_app() -> FlibustaUserAssistBot:
    """
    Get global bot application instance.

    Returns:
        FlibustaUserAssistBot instance

    Raises:
        RuntimeError: If bot application is not initialized
    """
    global bot_app
    if bot_app is None:
        raise RuntimeError("FlibustaUserAssistBot not initialized")
    return bot_app


async def main() -> None:
    """
    Main entry point for the bot application.
    """
    global bot_app

    try:
        # Create bot application
        bot_app = FlibustaUserAssistBot()

        # Start the bot
        await bot_app.start()

    except Exception as e:
        if bot_app:
            bot_app.logger.critical(f"Bot startup failed - error: {str(e)}")
        else:
            print(f"Bot startup failed - error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())
