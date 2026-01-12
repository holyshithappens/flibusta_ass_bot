"""
Button Generator Service for FlibustaUserAssistBot.

This module provides the ButtonGenerator class that creates Telegram reply keyboards
with commands for the target bot (@FlibustaRuBot) using aiogram.
"""

from typing import List, Optional
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from ..core.config import Config
from ..core.logger import BotLogger
from ..core.types import AIResponse

class ButtonGenerator:
    """
    Button Generator Service for creating Telegram reply keyboards.

    Features:
    - Generates reply keyboards from AI response commands
    - Formats buttons for target bot (@FlibustaRuBot)
    - Adaptive button layout (2-3 buttons per row)
    - Command validation and formatting
    - Button categorization by type (command, reply, search)
    - Each button category appears on a separate row
    """

    def __init__(self, config: Config):
        """
        Initialize Button Generator.

        Args:
            config: Bot configuration
        """
        self.config = config
        self.logger = BotLogger(__name__).get_logger()

        # Target bot username for button formatting
        self.target_bot_username = self.config.bot.target_bot_username

        self.logger.info(
            f"ButtonGenerator initialized - target_bot: {self.target_bot_username}, "
            f"buttons_per_row: {self.config.buttons.buttons_per_row}, "
            f"max_buttons: {self.config.buttons.max_buttons}"
        )

    def generate_reply_buttons(self, ai_response: AIResponse) -> Optional[ReplyKeyboardMarkup]:
        """
        Generate Telegram reply keyboard from AI response commands.

        Args:
            ai_response: AI response containing commands

        Returns:
            ReplyKeyboardMarkup object or None if no valid commands
        """
        if not ai_response:
            self.logger.debug("No AI response provided")
            return None

        # Use both commands and suggestions from AI response
        all_commands = []
        if ai_response.commands:
            all_commands.extend(ai_response.commands)
        if ai_response.suggestions:
            all_commands.extend(ai_response.suggestions)

        if not all_commands:
            self.logger.debug("No commands or suggestions to generate buttons")
            return None

        try:
            # Validate and format commands
            valid_commands = self._validate_and_format_commands(all_commands)

            if not valid_commands:
                self.logger.debug("No valid commands after validation")
                return None

            # Create button grid
            button_grid = self._create_button_grid(valid_commands)

            # Create aiogram keyboard
            keyboard = self._create_aiogram_keyboard(button_grid)

            self.logger.info(
                f"Generated reply buttons - commands_count: {len(valid_commands)}, "
                f"rows_count: {len(button_grid)}"
            )

            return keyboard

        except Exception as e:
            self.logger.error(f"Failed to generate reply buttons - error: {str(e)}")
            return None

    def _validate_and_format_commands(self, commands: List[str]) -> List[str]:
        """
        Validate and format commands for buttons.

        Args:
            commands: Raw commands from AI response

        Returns:
            List of validated command strings
        """
        validated_commands = []

        for cmd in commands:
            try:
                # Skip empty commands
                if not cmd or not cmd.strip():
                    continue

                # Clean command
                cleaned_cmd = cmd.strip()

                # Validate command format
                if not self._is_valid_command_format(cleaned_cmd):
                    self.logger.debug(f"Invalid command format - command: {cleaned_cmd}")
                    continue

                validated_commands.append(cleaned_cmd)

            except Exception as e:
                self.logger.warning(f"Failed to process command - command: {cmd}, error: {str(e)}")
                continue

        # Limit to max buttons
        max_buttons = self.config.buttons.max_buttons
        if len(validated_commands) > max_buttons:
            validated_commands = validated_commands[:max_buttons]

        return validated_commands

    def _is_valid_command_format(self, command: str) -> bool:
        """
        Validate command format.

        Args:
            command: Command string to validate

        Returns:
            True if command is valid, False otherwise
        """
        # Must contain target bot username
        if self.target_bot_username not in command:
            return False

        # Must be either /command@bot or @bot request format
        if command.startswith('/') and '@' in command:
            return True

        if command.startswith(self.target_bot_username):
            return True

        return False

    def _create_button_grid(self, commands: List[str]) -> List[List[str]]:
        """
        Create button grid with adaptive layout, organized by category.

        Args:
            commands: List of command strings

        Returns:
            2D list (grid) of command strings, organized by category
        """
        # Categorize commands by type
        command_buttons = []
        reply_buttons = []
        search_buttons = []

        for cmd in commands:
            # Simple categorization based on command patterns
            cmd_lower = cmd.lower()
            if cmd.startswith('/'):
                command_buttons.append(cmd)
            elif '[' in cmd and ']' in cmd:  # Suggestions/options
                reply_buttons.append(cmd)
            elif '<code>' in cmd and '</code>' in cmd:  # Search queries
                search_buttons.append(cmd)
            else:
                # Other types of buttons (navigation, etc.)
                command_buttons.append(cmd)

        # Create button grid with each category on a new line
        button_grid = []
        buttons_per_row = self.config.buttons.buttons_per_row

        # Add command buttons (first category)
        for i in range(0, len(command_buttons), buttons_per_row):
            row = command_buttons[i:i + buttons_per_row]
            if row:
                button_grid.append(row)

        # Add reply buttons (second category)
        for i in range(0, len(reply_buttons), buttons_per_row):
            row = reply_buttons[i:i + buttons_per_row]
            if row:
                button_grid.append(row)

        # Add search buttons (third category)
        for i in range(0, len(search_buttons), buttons_per_row):
            row = search_buttons[i:i + buttons_per_row]
            if row:
                button_grid.append(row)

        return button_grid

    def _create_aiogram_keyboard(self, button_grid: List[List[str]]) -> ReplyKeyboardMarkup:
        """
        Create aiogram ReplyKeyboardMarkup from button grid.

        Args:
            button_grid: 2D list of command strings

        Returns:
            ReplyKeyboardMarkup object
        """
        keyboard_rows = []

        for row in button_grid:
            keyboard_row = []
            for command in row:
                # Create aiogram button with command as text
                keyboard_button = KeyboardButton(text=command)
                keyboard_row.append(keyboard_button)

            keyboard_rows.append(keyboard_row)

        # Create keyboard with resize and one-time options
        keyboard = ReplyKeyboardMarkup(
            keyboard=keyboard_rows,
            resize_keyboard=True,
            one_time_keyboard=False,
            selective=False
        )

        return keyboard

    def validate_button_layout(self, keyboard: ReplyKeyboardMarkup) -> bool:
        """
        Validate button layout meets requirements.

        Args:
            keyboard: ReplyKeyboardMarkup to validate

        Returns:
            True if layout is valid, False otherwise
        """
        if not keyboard or not keyboard.keyboard:
            return False

        # Check row count
        max_rows = 5
        if len(keyboard.keyboard) > max_rows:
            self.logger.warning(f"Too many keyboard rows - count: {len(keyboard.keyboard)}, max: {max_rows}")
            return False

        # Check button count per row
        max_buttons_per_row = 3
        for row in keyboard.keyboard:
            if len(row) > max_buttons_per_row:
                self.logger.warning(f"Too many buttons in row - count: {len(row)}, max: {max_buttons_per_row}")
                return False

        return True

    @property
    def is_ready(self) -> bool:
        """
        Check if service is ready to generate buttons.

        Returns:
            True if service is ready, False otherwise
        """
        return bool(self.config and self.target_bot_username is not None)

# Global instance for convenience
button_generator: Optional[ButtonGenerator] = None

def get_button_generator() -> ButtonGenerator:
    """
    Get global button generator instance.

    Returns:
        ButtonGenerator instance

    Raises:
        RuntimeError: If service is not initialized
    """
    global button_generator
    if button_generator is None:
        raise RuntimeError("ButtonGenerator not initialized")
    return button_generator

__all__ = [
    "ButtonGenerator",
    "get_button_generator",
    "button_generator"
]