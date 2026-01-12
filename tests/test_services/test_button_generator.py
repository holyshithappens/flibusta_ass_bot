"""
Tests for ButtonGenerator.
"""

import pytest
from unittest.mock import MagicMock
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from src.bot.services.button_generator import ButtonGenerator
from src.bot.core.types import AIResponse
from src.bot.core.config import Config

@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = MagicMock(spec=Config)
    config.bot.target_bot_username = "@FlibustaRuBot"
    config.buttons.buttons_per_row = 2
    config.buttons.max_buttons = 6
    config.buttons.button_priority = {
        "command": 3,
        "search": 2,
        "navigation": 1
    }
    return config

@pytest.fixture
def button_generator(mock_config):
    """Create ButtonGenerator instance."""
    return ButtonGenerator(mock_config)

@pytest.fixture
def sample_ai_response():
    """Create sample AI response with commands."""
    return AIResponse(
        text="Here are some recommendations:",
        suggestions=["Try fantasy genre", "Explore best authors"],
        commands=[
            "/pop@FlibustaRuBot fantasy",
            "@FlibustaRuBot search best books",
            "/pop@FlibustaRuBot recent"
        ],
        confidence=0.95,
        model_used="mistralai/devstral-2512:free"
    )

def test_button_generator_initialization(button_generator, mock_config):
    """Test ButtonGenerator initialization."""
    assert button_generator.config == mock_config
    assert button_generator.target_bot_username == "@FlibustaRuBot"
    assert button_generator.is_ready is True

def test_generate_reply_buttons_success(button_generator, sample_ai_response):
    """Test successful button generation."""
    keyboard = button_generator.generate_reply_buttons(sample_ai_response)

    assert isinstance(keyboard, ReplyKeyboardMarkup)
    assert keyboard.resize_keyboard is True
    assert keyboard.one_time_keyboard is False

    # Check keyboard structure
    assert len(keyboard.keyboard) == 2  # 2 rows for 3 commands with 2 per row
    assert len(keyboard.keyboard[0]) == 2  # First row should have 2 buttons
    assert len(keyboard.keyboard[1]) == 1  # Second row should have 1 button

    # Check button content
    buttons = []
    for row in keyboard.keyboard:
        for button in row:
            buttons.append(button.text)

    assert "/pop@FlibustaRuBot fantasy" in buttons
    assert "@FlibustaRuBot search best books" in buttons
    assert "/pop@FlibustaRuBot recent" in buttons

def test_generate_reply_buttons_no_commands(button_generator):
    """Test button generation with no commands."""
    ai_response = AIResponse(
        text="No commands available",
        suggestions=[],
        commands=[],
        confidence=0.8,
        model_used="mistralai/devstral-2512:free"
    )

    keyboard = button_generator.generate_reply_buttons(ai_response)
    assert keyboard is None

def test_generate_reply_buttons_only_suggestions(button_generator):
    """Test button generation with only suggestions."""
    ai_response = AIResponse(
        text="Here are some suggestions:",
        suggestions=[
            "@FlibustaRuBot try fantasy genre",
            "@FlibustaRuBot explore best authors"
        ],
        commands=[],
        confidence=0.9,
        model_used="mistralai/devstral-2512:free"
    )

    keyboard = button_generator.generate_reply_buttons(ai_response)

    assert isinstance(keyboard, ReplyKeyboardMarkup)
    assert len(keyboard.keyboard) == 1
    assert len(keyboard.keyboard[0]) == 2

    # Check button content
    buttons = []
    for row in keyboard.keyboard:
        for button in row:
            buttons.append(button.text)

    assert "@FlibustaRuBot try fantasy genre" in buttons
    assert "@FlibustaRuBot explore best authors" in buttons

def test_generate_reply_buttons_mixed_commands_and_suggestions(button_generator):
    """Test button generation with both commands and suggestions."""
    ai_response = AIResponse(
        text="Here are options:",
        suggestions=[
            "@FlibustaRuBot try fantasy",
            "@FlibustaRuBot explore sci-fi"
        ],
        commands=[
            "/pop@FlibustaRuBot fantasy",
            "/pop@FlibustaRuBot sci-fi"
        ],
        confidence=0.95,
        model_used="mistralai/devstral-2512:free"
    )

    keyboard = button_generator.generate_reply_buttons(ai_response)

    assert isinstance(keyboard, ReplyKeyboardMarkup)
    assert len(keyboard.keyboard) == 2  # 2 rows for 4 items with 2 per row

    # Check all commands and suggestions are included
    buttons = []
    for row in keyboard.keyboard:
        for button in row:
            buttons.append(button.text)

    assert len(buttons) == 4
    assert "/pop@FlibustaRuBot fantasy" in buttons
    assert "/pop@FlibustaRuBot sci-fi" in buttons
    assert "@FlibustaRuBot try fantasy" in buttons
    assert "@FlibustaRuBot explore sci-fi" in buttons

def test_generate_reply_buttons_max_buttons_limit(button_generator, mock_config):
    """Test button generation with max buttons limit."""
    mock_config.buttons.max_buttons = 2

    ai_response = AIResponse(
        text="Many commands:",
        suggestions=[],
        commands=[
            "/pop@FlibustaRuBot fantasy",
            "/pop@FlibustaRuBot sci-fi",
            "/pop@FlibustaRuBot horror",
            "/pop@FlibustaRuBot romance"
        ],
        confidence=0.95,
        model_used="mistralai/devstral-2512:free"
    )

    keyboard = button_generator.generate_reply_buttons(ai_response)

    assert isinstance(keyboard, ReplyKeyboardMarkup)
    assert len(keyboard.keyboard) == 1
    assert len(keyboard.keyboard[0]) == 2  # Should be limited to max_buttons

    # Check only first 2 commands are included
    buttons = []
    for row in keyboard.keyboard:
        for button in row:
            buttons.append(button.text)

    assert len(buttons) == 2
    assert "/pop@FlibustaRuBot fantasy" in buttons
    assert "/pop@FlibustaRuBot sci-fi" in buttons

def test_generate_reply_buttons_invalid_commands(button_generator):
    """Test button generation with invalid commands."""
    ai_response = AIResponse(
        text="Invalid commands:",
        suggestions=[],
        commands=[
            "invalid command without bot",
            "/pop@WrongBot fantasy",
            "/pop@FlibustaRuBot valid"
        ],
        confidence=0.95,
        model_used="mistralai/devstral-2512:free"
    )

    keyboard = button_generator.generate_reply_buttons(ai_response)

    assert isinstance(keyboard, ReplyKeyboardMarkup)
    assert len(keyboard.keyboard) == 1
    assert len(keyboard.keyboard[0]) == 1  # Only valid command

    # Check only valid command is included
    buttons = []
    for row in keyboard.keyboard:
        for button in row:
            buttons.append(button.text)

    assert len(buttons) == 1
    assert "/pop@FlibustaRuBot valid" in buttons

def test_validate_and_format_commands_valid(button_generator):
    """Test validation of valid commands."""
    commands = [
        "/pop@FlibustaRuBot fantasy",
        "@FlibustaRuBot search best books",
        "/pop@FlibustaRuBot recent"
    ]

    validated = button_generator._validate_and_format_commands(commands)
    assert len(validated) == 3
    assert all(cmd in validated for cmd in commands)

def test_validate_and_format_commands_invalid(button_generator):
    """Test validation of invalid commands."""
    commands = [
        "invalid command",
        "/pop@WrongBot fantasy",
        "another invalid"
    ]

    validated = button_generator._validate_and_format_commands(commands)
    assert len(validated) == 0

def test_validate_and_format_commands_mixed(button_generator):
    """Test validation of mixed valid and invalid commands."""
    commands = [
        "/pop@FlibustaRuBot fantasy",
        "invalid command",
        "@FlibustaRuBot search books",
        "/pop@WrongBot sci-fi"
    ]

    validated = button_generator._validate_and_format_commands(commands)
    assert len(validated) == 2
    assert "/pop@FlibustaRuBot fantasy" in validated
    assert "@FlibustaRuBot search books" in validated

def test_is_valid_command_format(button_generator):
    """Test command format validation."""
    assert button_generator._is_valid_command_format("/pop@FlibustaRuBot fantasy") is True
    assert button_generator._is_valid_command_format("@FlibustaRuBot search books") is True
    assert button_generator._is_valid_command_format("/pop@WrongBot fantasy") is False
    assert button_generator._is_valid_command_format("invalid command") is False
    assert button_generator._is_valid_command_format("/pop fantasy") is False

def test_create_button_grid(button_generator):
    """Test button grid creation."""
    commands = [
        "/pop@FlibustaRuBot fantasy",
        "@FlibustaRuBot search books",
        "/pop@FlibustaRuBot sci-fi",
        "@FlibustaRuBot explore authors"
    ]

    grid = button_generator._create_button_grid(commands)
    assert len(grid) == 2  # 2 rows for 4 commands with 2 per row
    assert len(grid[0]) == 2
    assert len(grid[1]) == 2

def test_create_button_grid_odd_number(button_generator):
    """Test button grid creation with odd number of commands."""
    commands = [
        "/pop@FlibustaRuBot fantasy",
        "@FlibustaRuBot search books",
        "/pop@FlibustaRuBot sci-fi"
    ]

    grid = button_generator._create_button_grid(commands)
    assert len(grid) == 2  # 2 rows: first with 2, second with 1
    assert len(grid[0]) == 2
    assert len(grid[1]) == 1

def test_create_aiogram_keyboard(button_generator):
    """Test aiogram keyboard creation."""
    button_grid = [
        ["/pop@FlibustaRuBot fantasy", "@FlibustaRuBot search books"],
        ["/pop@FlibustaRuBot sci-fi"]
    ]

    keyboard = button_generator._create_aiogram_keyboard(button_grid)

    assert isinstance(keyboard, ReplyKeyboardMarkup)
    assert len(keyboard.keyboard) == 2
    assert len(keyboard.keyboard[0]) == 2
    assert len(keyboard.keyboard[1]) == 1

    # Check button types
    assert isinstance(keyboard.keyboard[0][0], KeyboardButton)
    assert isinstance(keyboard.keyboard[0][1], KeyboardButton)
    assert isinstance(keyboard.keyboard[1][0], KeyboardButton)

    # Check button text
    assert keyboard.keyboard[0][0].text == "/pop@FlibustaRuBot fantasy"
    assert keyboard.keyboard[0][1].text == "@FlibustaRuBot search books"
    assert keyboard.keyboard[1][0].text == "/pop@FlibustaRuBot sci-fi"

def test_validate_button_layout_valid(button_generator):
    """Test validation of valid button layout."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/pop@FlibustaRuBot fantasy")],
            [KeyboardButton(text="@FlibustaRuBot search books")]
        ],
        resize_keyboard=True
    )

    result = button_generator.validate_button_layout(keyboard)
    assert result is True

def test_validate_button_layout_too_many_rows(button_generator):
    """Test validation of button layout with too many rows."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/pop@FlibustaRuBot fantasy")],
            [KeyboardButton(text="@FlibustaRuBot search books")],
            [KeyboardButton(text="/pop@FlibustaRuBot sci-fi")],
            [KeyboardButton(text="@FlibustaRuBot explore authors")],
            [KeyboardButton(text="/pop@FlibustaRuBot horror")],
            [KeyboardButton(text="/pop@FlibustaRuBot romance")]  # 6th row
        ],
        resize_keyboard=True
    )

    result = button_generator.validate_button_layout(keyboard)
    assert result is False

def test_validate_button_layout_too_many_buttons_per_row(button_generator):
    """Test validation of button layout with too many buttons per row."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="/pop@FlibustaRuBot fantasy"),
                KeyboardButton(text="@FlibustaRuBot search books"),
                KeyboardButton(text="/pop@FlibustaRuBot sci-fi"),
                KeyboardButton(text="@FlibustaRuBot explore authors")  # 4th button
            ]
        ],
        resize_keyboard=True
    )

    result = button_generator.validate_button_layout(keyboard)
    assert result is False

def test_validate_button_layout_empty(button_generator):
    """Test validation of empty button layout."""
    keyboard = ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)
    result = button_generator.validate_button_layout(keyboard)
    assert result is False

def test_is_ready(button_generator):
    """Test is_ready property."""
    assert button_generator.is_ready is True

def test_is_not_ready(button_generator, mock_config):
    """Test is_not_ready when config is invalid."""
    mock_config.bot.target_bot_username = None
    assert button_generator.is_ready is False