"""
Unit tests for configuration management.

Tests Config class and related functionality in src.bot.core.config module.
"""

import os
import pytest
import tempfile
import time
from pathlib import Path
from pydantic import ValidationError

from src.bot.core.config import Config, BotConfig, OpenRouterConfig, LoggingConfig


class TestConfigModels:
    """Test Pydantic configuration models."""
    
    def test_valid_bot_config(self):
        """Test creating valid BotConfig."""
        config = BotConfig(
            bot={
                "name": "TestBot",
                "username": "@TestBot",
                "target_bot_username": "@TargetBot",
                "version": "1.0.0"
            }
        )
        
        assert config.bot.name == "TestBot"
        assert config.bot.username == "@TestBot"
        assert config.bot.target_bot_username == "@TargetBot"
        assert config.bot.version == "1.0.0"
    
    def test_openrouter_config_defaults(self):
        """Test OpenRouterConfig default values."""
        config = OpenRouterConfig()
        
        assert config.model == "nex-agi/deepseek-v3.1-nex-n1:free"
        assert config.temperature == 0.7
        assert config.max_tokens == 500
        assert config.timeout == 30
        assert config.enable_caching is True
    
    def test_logging_config_validation(self):
        """Test LoggingConfig level validation."""
        with pytest.raises(ValidationError):
            LoggingConfig(level="INVALID")
    
    def test_config_extra_fields_allowed(self):
        """Test that extra fields are allowed in config."""
        config = BotConfig(
            bot={
                "name": "TestBot",
                "username": "@TestBot",
                "target_bot_username": "@TargetBot",
                "version": "1.0.0"
            },
            extra_field="value"  # Should be allowed
        )
        
        # Extra field should be in dict representation
        config_dict = config.model_dump()
        assert "extra_field" in config_dict


class TestConfigSingleton:
    """Test Config singleton pattern."""
    
    def test_singleton_pattern(self):
        """Test that Config is a singleton."""
        config1 = Config()
        config2 = Config()
        
        assert config1 is config2
    
    def test_singleton_thread_safety(self):
        """Test singleton pattern is thread-safe."""
        import threading
        
        instances = []
        
        def create_instance():
            instances.append(Config())
        
        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # All instances should be the same object
        assert all(inst is instances[0] for inst in instances)


class TestConfigLoading:
    """Test configuration loading from files."""
    
    def test_load_valid_yaml_config(self):
        """Test loading valid YAML configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("""
bot:
  name: "TestBot"
  username: "@TestBot"
  target_bot_username: "@TargetBot"
  version: "1.0.0"

telegram:
  group_chat_ids: []
  admin_user_ids: []

openrouter:
  model: "test-model"
  temperature: 0.5
  max_tokens: 300
""")
            
            ai_file = Path(tmpdir) / "ai_instruction.md"
            ai_file.write_text("# AI Instructions\nTest instructions")
            
            # Temporarily modify global config paths
            original_paths = (Config._instance.config_path, Config._instance.ai_instruction_path)
            Config._instance.config_path = config_file
            Config._instance.ai_instruction_path = ai_file
            
            try:
                Config._instance.load()
                
                assert Config._instance.bot.name == "TestBot"
                assert Config._instance.bot.username == "@TestBot"
                assert Config._instance.openrouter.model == "test-model"
                assert Config._instance.openrouter.temperature == 0.5
                assert Config._instance.openrouter.max_tokens == 300
            finally:
                # Restore original paths
                Config._instance.config_path, Config._instance.ai_instruction_path = original_paths
    
    def test_load_missing_config_file(self):
        """Test error when config file is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "nonexistent.yaml"
            ai_file = Path(tmpdir) / "ai_instruction.md"
            ai_file.write_text("# AI Instructions")
            
            Config._instance.config_path = config_file
            Config._instance.ai_instruction_path = ai_file
            
            with pytest.raises(FileNotFoundError, match="Configuration file not found"):
                Config._instance.load()
    
    def test_load_missing_ai_instruction_file(self):
        """Test error when AI instruction file is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("""
bot:
  name: "TestBot"
  username: "@TestBot"
  target_bot_username: "@TargetBot"
  version: "1.0.0"
""")
            
            ai_file = Path(tmpdir) / "nonexistent.md"
            
            Config._instance.config_path = config_file
            Config._instance.ai_instruction_path = ai_file
            
            with pytest.raises(FileNotFoundError, match="AI instruction file not found"):
                Config._instance.load()
    
    def test_load_ai_instruction_content(self):
        """Test loading AI instruction content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("""
bot:
  name: "TestBot"
  username: "@TestBot"
  target_bot_username: "@TargetBot"
  version: "1.0.0"
""")
            
            ai_file = Path(tmpdir) / "ai_instruction.md"
            instruction_content = "# AI Instructions\n\nThis is a test instruction file."
            ai_file.write_text(instruction_content)
            
            Config._instance.config_path = config_file
            Config._instance.ai_instruction_path = ai_file
            
            Config._instance.load()
            
            assert Config._instance.ai_instruction == instruction_content


class TestEnvironmentVariables:
    """Test environment variable integration."""
    
    def test_env_variables_override_yaml(self):
        """Test that environment variables override YAML values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("""
bot:
  name: "TestBot"
  username: "@TestBot"
  target_bot_username: "@TargetBot"
  version: "1.0.0"

openrouter:
  model: "yaml-model"
  temperature: 0.5
""")
            
            ai_file = Path(tmpdir) / "ai_instruction.md"
            ai_file.write_text("# AI Instructions")
            
            Config._instance.config_path = config_file
            Config._instance.ai_instruction_path = ai_file
            
            # Set environment variables
            os.environ['OPENROUTER_MODEL'] = 'env-model'
            os.environ['OPENROUTER_TIMEOUT'] = '60'
            
            try:
                Config._instance.load()
                
                # Environment variables should override YAML
                assert Config._instance.openrouter.model == "env-model"
                assert Config._instance.openrouter.timeout == 60
                # YAML value should still be used for temperature
                assert Config._instance.openrouter.temperature == 0.5
            finally:
                # Clean up environment variables
                os.environ.pop('OPENROUTER_MODEL', None)
                os.environ.pop('OPENROUTER_TIMEOUT', None)
    
    def test_env_variable_types(self):
        """Test environment variable type conversion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("""
bot:
  name: "TestBot"
  username: "@TestBot"
  target_bot_username: "@TargetBot"
  version: "1.0.0"
""")
            
            ai_file = Path(tmpdir) / "ai_instruction.md"
            ai_file.write_text("# AI Instructions")
            
            Config._instance.config_path = config_file
            Config._instance.ai_instruction_path = ai_file
            
            # Set environment variables with different types
            os.environ['OPENROUTER_TIMEOUT'] = '45'  # int
            os.environ['AI_TEMPERATURE'] = '0.8'  # float
            os.environ['DEBUG'] = 'true'  # bool
            
            try:
                Config._instance.load()
                
                assert Config._instance.openrouter.timeout == 45
                assert Config._instance.openrouter.temperature == 0.8
                assert Config._instance.development.debug is True
            finally:
                # Clean up
                for key in ['OPENROUTER_TIMEOUT', 'AI_TEMPERATURE', 'DEBUG']:
                    os.environ.pop(key, None)


class TestConfigProperties:
    """Test Config class properties."""
    
    def test_config_properties(self):
        """Test accessing configuration properties."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("""
bot:
  name: "TestBot"
  username: "@TestBot"
  target_bot_username: "@TargetBot"
  version: "1.0.0"

telegram:
  group_chat_ids: [-1001234567890]

openrouter:
  model: "test-model"
""")
            
            ai_file = Path(tmpdir) / "ai_instruction.md"
            ai_file.write_text("# AI Instructions")
            
            Config._instance.config_path = config_file
            Config._instance.ai_instruction_path = ai_file
            Config._instance.load()
            
            # Test property access
            assert Config._instance.bot.name == "TestBot"
            assert Config._instance.telegram.group_chat_ids == [-1001234567890]
            assert Config._instance.openrouter.model == "test-model"
            assert Config._instance.ai_instruction == "# AI Instructions"
    
    def test_get_method_dot_notation(self):
        """Test get method with dot notation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("""
bot:
  name: "TestBot"
  username: "@TestBot"
  target_bot_username: "@TargetBot"
  version: "1.0.0"

openrouter:
  model: "test-model"
  temperature: 0.7
""")
            
            ai_file = Path(tmpdir) / "ai_instruction.md"
            ai_file.write_text("# AI Instructions")
            
            Config._instance.config_path = config_file
            Config._instance.ai_instruction_path = ai_file
            Config._instance.load()
            
            # Test dot notation access
            assert Config._instance.get('bot.name') == "TestBot"
            assert Config._instance.get('openrouter.model') == "test-model"
            assert Config._instance.get('openrouter.temperature') == 0.7
            assert Config._instance.get('nonexistent.key', 'default') == 'default'
    
    def test_to_dict_method(self):
        """Test to_dict method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("""
bot:
  name: "TestBot"
  username: "@TestBot"
  target_bot_username: "@TargetBot"
  version: "1.0.0"
""")
            
            ai_file = Path(tmpdir) / "ai_instruction.md"
            ai_file.write_text("# AI Instructions")
            
            Config._instance.config_path = config_file
            Config._instance.ai_instruction_path = ai_file
            Config._instance.load()
            
            config_dict = Config._instance.to_dict()
            
            assert isinstance(config_dict, dict)
            assert config_dict['bot']['name'] == "TestBot"
            assert 'telegram' in config_dict
            assert 'openrouter' in config_dict


# Hot reload functionality removed - configuration is loaded only at startup


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_invalid_bot_info(self):
        """Test validation of invalid bot information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("""
bot:
  name: ""
  username: "InvalidUsername"
  target_bot_username: "@TargetBot"
  version: "invalid"
""")
            
            ai_file = Path(tmpdir) / "ai_instruction.md"
            ai_file.write_text("# AI Instructions")
            
            Config._instance.config_path = config_file
            Config._instance.ai_instruction_path = ai_file
            
            with pytest.raises(ValueError, match="Configuration validation failed"):
                Config._instance.load()
    
    def test_missing_required_fields(self):
        """Test validation of missing required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("""
bot:
  name: "TestBot"
  # Missing required fields
""")
            
            ai_file = Path(tmpdir) / "ai_instruction.md"
            ai_file.write_text("# AI Instructions")
            
            Config._instance.config_path = config_file
            Config._instance.ai_instruction_path = ai_file
            
            with pytest.raises(ValueError, match="Configuration validation failed"):
                Config._instance.load()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])