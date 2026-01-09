"""
Unit tests for logging configuration.

Tests BotLogger class and related functions in src.bot.core.logger module.
"""

import pytest
import logging
import tempfile
from pathlib import Path
from io import StringIO

from src.bot.core.logger import BotLogger, get_logger


class TestBotLogger:
    """Test BotLogger class."""
    
    def test_valid_logger_initialization(self):
        """Test creating valid logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = BotLogger(
                name="TestLogger",
                level="INFO",
                file_path=log_file,
                console_output=False,
                file_output=True
            )
            
            assert logger.name == "TestLogger"
            assert logger.level == "INFO"
            assert logger.file_path == log_file
            assert logger.console_output is False
            assert logger.file_output is True
    
    def test_invalid_log_level(self):
        """Test invalid log level raises ValueError."""
        with pytest.raises(ValueError, match="Invalid log level"):
            BotLogger(level="INVALID")
    
    def test_logger_has_handlers(self):
        """Test logger has correct handlers."""
        logger = BotLogger(console_output=True, file_output=False)
        assert len(logger.get_logger().handlers) == 1  # Only console handler
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = BotLogger(
                console_output=True,
                file_output=True,
                file_path=log_file
            )
            assert len(logger.get_logger().handlers) == 2  # Both handlers
    
    def test_log_messages(self):
        """Test logging messages at different levels."""
        logger = BotLogger(console_output=False, file_output=False)
        
        # These should not raise exceptions
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
    
    def test_log_file_creation(self):
        """Test log file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = BotLogger(
                file_path=log_file,
                console_output=False,
                file_output=True
            )
            
            # Log a message
            logger.info("Test message")
            
            # Check file exists and contains message
            assert log_file.exists()
            content = log_file.read_text()
            assert "Test message" in content
    
    def test_log_rotation(self):
        """Test log rotation configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = BotLogger(
                file_path=log_file,
                max_size_mb=1,
                backup_count=3,
                console_output=False,
                file_output=True
            )
            
            # Check handler has correct configuration
            handlers = logger.get_logger().handlers
            file_handlers = [h for h in handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
            
            assert len(file_handlers) == 1
            assert file_handlers[0].maxBytes == 1 * 1024 * 1024
            assert file_handlers[0].backupCount == 3
    
    def test_log_directory_creation(self):
        """Test log directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "nested" / "dir" / "test.log"
            logger = BotLogger(
                file_path=log_file,
                console_output=False,
                file_output=True
            )
            
            # Log a message
            logger.info("Test message")
            
            # Check directory and file exist
            assert log_file.parent.exists()
            assert log_file.exists()
    
    def test_logger_level_filtering(self):
        """Test logger filters messages by level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = BotLogger(
                level="WARNING",
                file_path=log_file,
                console_output=False,
                file_output=True
            )
            
            # Log messages at different levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            
            # Check only WARNING and above are logged
            content = log_file.read_text()
            assert "Debug message" not in content
            assert "Info message" not in content
            assert "Warning message" in content
            assert "Error message" in content
    
    def test_get_logger_returns_logging_logger(self):
        """Test get_logger returns standard logging.Logger."""
        logger = BotLogger()
        std_logger = logger.get_logger()
        
        assert isinstance(std_logger, logging.Logger)
        assert std_logger.name == "FlibustaUserAssistBot"


class TestGetLoggerFunction:
    """Test get_logger convenience function."""
    
    def test_get_logger_creates_logger(self):
        """Test get_logger creates configured logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = get_logger(
                name="TestLogger",
                level="DEBUG",
                file_path=log_file,
                console_output=False,
                file_output=True
            )
            
            assert isinstance(logger, logging.Logger)
            assert logger.name == "TestLogger"
            assert logger.level == logging.DEBUG
    
    def test_get_logger_default_values(self):
        """Test get_logger uses default values."""
        logger = get_logger(console_output=False, file_output=False)
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "FlibustaUserAssistBot"


class TestLoggingLevels:
    """Test different logging levels."""
    
    def test_debug_level(self):
        """Test DEBUG level."""
        logger = BotLogger(level="DEBUG")
        assert logger.level == "DEBUG"
    
    def test_info_level(self):
        """Test INFO level."""
        logger = BotLogger(level="INFO")
        assert logger.level == "INFO"
    
    def test_warning_level(self):
        """Test WARNING level."""
        logger = BotLogger(level="WARNING")
        assert logger.level == "WARNING"
    
    def test_error_level(self):
        """Test ERROR level."""
        logger = BotLogger(level="ERROR")
        assert logger.level == "ERROR"
    
    def test_critical_level(self):
        """Test CRITICAL level."""
        logger = BotLogger(level="CRITICAL")
        assert logger.level == "CRITICAL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])