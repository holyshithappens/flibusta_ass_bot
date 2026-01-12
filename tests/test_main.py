"""
Tests for main bot entry point.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from src.bot.main import FlibustaUserAssistBot

@pytest.fixture
def bot_app():
    """Create bot application instance."""
    return FlibustaUserAssistBot()

def test_bot_initialization(bot_app):
    """Test bot initialization."""
    assert bot_app.config is not None
    assert bot_app.logger is not None
    assert bot_app.bot is None  # Not initialized yet
    assert bot_app.dispatcher is None  # Not initialized yet
    assert bot_app.is_running == False

@pytest.mark.asyncio
async def test_setup_logging(bot_app):
    """Test logging setup."""
    # Mock setup_global_logger
    with patch('src.bot.main.setup_global_logger') as mock_setup:
        bot_app._setup_logging()

        # Should call setup_global_logger with config
        mock_setup.assert_called_once()

@pytest.mark.asyncio
async def test_initialize_aiogram(bot_app):
    """Test aiogram initialization."""
    # Mock environment to have Telegram token
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        await bot_app._initialize_aiogram()

        # Should initialize bot and dispatcher
        assert bot_app.bot is not None
        assert bot_app.dispatcher is not None

@pytest.mark.asyncio
async def test_initialize_aiogram_no_token(bot_app):
    """Test aiogram initialization without token."""
    # Remove Telegram token
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN not configured"):
            await bot_app._initialize_aiogram()

@pytest.mark.asyncio
async def test_initialize_services(bot_app):
    """Test services initialization."""
    # Mock environment to have API keys
    with patch.dict('os.environ', {
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'OPENROUTER_API_KEY': 'test_api_key'
    }):
        await bot_app._initialize_aiogram()
        await bot_app._initialize_services()

        # Should initialize all services
        assert bot_app.openrouter_client is not None
        assert bot_app.ai_assistant is not None
        assert bot_app.message_analyzer is not None
        assert bot_app.button_generator is not None

@pytest.mark.asyncio
async def test_initialize_services_no_api_key(bot_app):
    """Test services initialization without API key."""
    # Mock environment without OpenRouter API key
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        await bot_app._initialize_aiogram()

        with pytest.raises(ValueError, match="OPENROUTER_API_KEY not configured"):
            await bot_app._initialize_services()

@pytest.mark.asyncio
async def test_initialize_middleware(bot_app):
    """Test middleware initialization."""
    # Initialize aiogram first
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        await bot_app._initialize_aiogram()
        bot_app._initialize_middleware()

        # Should initialize middleware
        assert bot_app.logging_middleware is not None
        assert bot_app.error_middleware is not None

@pytest.mark.asyncio
async def test_initialize_middleware_no_dispatcher(bot_app):
    """Test middleware initialization without dispatcher."""
    with pytest.raises(RuntimeError, match="Dispatcher not initialized"):
        bot_app._initialize_middleware()

@pytest.mark.asyncio
async def test_initialize_handlers(bot_app):
    """Test handlers initialization."""
    # Initialize aiogram and services first
    with patch.dict('os.environ', {
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'OPENROUTER_API_KEY': 'test_api_key'
    }):
        await bot_app._initialize_aiogram()
        await bot_app._initialize_services()
        bot_app._initialize_middleware()
        bot_app._initialize_handlers()

        # Should initialize handlers
        assert bot_app.group_handler is not None
        assert bot_app.channel_handler is not None

@pytest.mark.asyncio
async def test_initialize_handlers_no_dispatcher(bot_app):
    """Test handlers initialization without dispatcher."""
    with pytest.raises(RuntimeError, match="Dispatcher not initialized"):
        bot_app._initialize_handlers()

@pytest.mark.asyncio
async def test_get_allowed_updates(bot_app):
    """Test allowed updates configuration."""
    # Test with default features
    allowed = bot_app._get_allowed_updates()
    assert 'message' in allowed
    assert 'inline_query' not in allowed
    assert 'callback_query' not in allowed

    # Test with inline queries enabled
    with patch.object(bot_app.config.features, 'inline_queries', True):
        allowed = bot_app._get_allowed_updates()
        assert 'inline_query' in allowed

@pytest.mark.asyncio
async def test_is_running(bot_app):
    """Test is_running property."""
    # Test when not running
    assert bot_app.is_running == False

    # Test when running
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        await bot_app._initialize_aiogram()
        assert bot_app.is_running == True

@pytest.mark.asyncio
async def test_shutdown(bot_app):
    """Test graceful shutdown."""
    # Initialize services first
    with patch.dict('os.environ', {
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'OPENROUTER_API_KEY': 'test_api_key'
    }):
        await bot_app._initialize_aiogram()
        await bot_app._initialize_services()

        # Mock close methods
        with patch.object(bot_app.openrouter_client, 'close', new_callable=AsyncMock):
            with patch.object(bot_app.dispatcher, 'stop', new_callable=AsyncMock):
                with patch.object(bot_app.bot.session, 'close', new_callable=AsyncMock):
                    await bot_app._shutdown()

                    # Should call all close methods
                    bot_app.openrouter_client.close.assert_called_once()
                    bot_app.dispatcher.stop.assert_called_once()
                    bot_app.bot.session.close.assert_called_once()

@pytest.mark.asyncio
async def test_shutdown_no_services(bot_app):
    """Test shutdown when services not initialized."""
    # Should not raise error
    await bot_app._shutdown()

@pytest.mark.asyncio
async def test_main_function():
    """Test main function."""
    # Mock FlibustaUserAssistBot
    with patch('src.bot.main.FlibustaUserAssistBot') as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot

        # Mock asyncio.run to avoid actual execution
        with patch('asyncio.run') as mock_run:
            # Import and call main
            from src.bot.main import main
            await main()

            # Should create bot instance
            mock_bot_class.assert_called_once()

            # Should call start
            mock_bot.start.assert_called_once()