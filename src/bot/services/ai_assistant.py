"""
AI Assistant Service for FlibustaUserAssistBot.

This module provides the AIAssistantService class that handles AI-powered response generation,
prompt formatting, and integration with the OpenRouter API client.
"""

import asyncio
import os
from typing import List, Dict, Optional

from ..core.config import Config
from ..core.logger import BotLogger
from ..core.types import AIResponse, ChatContext
from ..clients.openrouter_client import OpenRouterClient

class AIAssistantService:
    """
    AI Assistant Service for generating responses using OpenRouter API.

    Features:
    - AI response generation with context-aware prompts
    - AI instruction loading and caching
    - Response validation and sanitization
    - Integration with OpenRouterClient
    - Support for mistralai/devstral-2512:free model
    """

    def __init__(self, config: Config, openrouter_client: OpenRouterClient):
        """
        Initialize AI Assistant Service.

        Args:
            config: Bot configuration
            openrouter_client: OpenRouter client instance
        """
        self.config = config
        self.client = openrouter_client
        self.ai_instruction = self._load_ai_instruction()
        self.logger = BotLogger(__name__).get_logger()

        # Use model from environment variable or default to mistralai/devstral-2512:free
        self.model = os.environ.get("OPENROUTER_MODEL", "mistralai/devstral-2512:free")

        self.logger.info(
            f"AIAssistantService initialized - model: {self.model}, "
            f"instruction_length: {len(self.ai_instruction)}"
        )

    def _load_ai_instruction(self) -> str:
        """
        Load AI instruction from file.

        Returns:
            AI instruction text

        Raises:
            FileNotFoundError: If instruction file is missing
            ValueError: If instruction is empty
        """
        try:
            instruction = self.config.ai_instruction
            if not instruction or not instruction.strip():
                raise ValueError("AI instruction is empty")
            return instruction.strip()
        except Exception as e:
            self.logger.error(f"Failed to load AI instruction - error: {str(e)}")
            raise

    def _format_prompt(self, context: ChatContext) -> List[Dict[str, str]]:
        """
        Format complete prompt for AI model.

        Args:
            context: Chat context containing message history

        Returns:
            List of message dicts for OpenRouter API
        """
        # Build context from message history
        context_messages = []
        for msg in context.message_history[-self.config.ai_assistant.context_window_size:]:
            context_messages.append({
                "role": "user",
                "content": f"User {msg.get('user_id', 'unknown')}: {msg.get('text', '')}"
            })

        # Create complete prompt
        messages = [
            {
                "role": "system",
                "content": self.ai_instruction
            },
            {
                "role": "system",
                "content": f"Current context: Chat ID {context.chat_id}, "
                          f"User ID {context.user_id}, "
                          f"Message: {context.message_text}"
            }
        ]

        # Add context messages
        messages.extend(context_messages)

        # Add current message
        messages.append({
            "role": "user",
            "content": context.message_text
        })

        return messages

    async def get_ai_response(self, context: ChatContext) -> AIResponse:
        """
        Get AI response for given chat context.

        Args:
            context: Chat context containing message and history

        Returns:
            AIResponse object with text, suggestions, and commands

        Raises:
            ValueError: If context is invalid
            Exception: If AI response generation fails
        """
        if not context or not context.message_text:
            raise ValueError("Context must contain valid message text")

        try:
            # Format prompt
            messages = self._format_prompt(context)

            self.logger.debug(
                f"Generating AI response - chat_id: {context.chat_id}, "
                f"user_id: {context.user_id}, "
                f"messages_count: {len(messages)}"
            )

            # Get response from OpenRouter
            response_text = await self.client.chat_completion(
                messages=messages,
                temperature=self.config.openrouter.temperature,
                max_tokens=self.config.openrouter.max_tokens,
                use_cache=self.config.openrouter.enable_caching
            )

            # Debug output raw response
            self.logger.debug(f"Raw AI response - chat_id: {context.chat_id}, "
                            f"response: {response_text[:200]}...")

            # Parse and validate response
            ai_response = self._parse_ai_response(response_text, context)

            self.logger.info(
                f"AI response generated - chat_id: {context.chat_id}, "
                f"response_length: {len(ai_response.text)}, "
                f"commands_count: {len(ai_response.commands)}"
            )

            return ai_response

        except Exception as e:
            self.logger.error(
                f"Failed to generate AI response - chat_id: {context.chat_id}, "
                f"error: {str(e)}"
            )
            raise

    def _parse_ai_response(self, response_text: str, context: ChatContext) -> AIResponse:
        """
        Parse raw AI response text into structured AIResponse object.

        Args:
            response_text: Raw text from AI model
            context: Chat context for reference

        Returns:
            Structured AIResponse object
        """
        # Basic validation
        if not response_text or not response_text.strip():
            raise ValueError("AI response is empty")

        # Clean up response
        cleaned_text = response_text.strip()

        # Extract commands, suggestions, and search queries from response
        commands = []
        suggestions = []
        search_queries = []

        # Parse line by line to categorize content
        lines = cleaned_text.split('\n')
        main_content_lines = []

        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue

            # Extract bot commands (format: /command)
            if stripped_line.startswith('/') and not stripped_line.startswith('//'):
                # Remove any @bot mentions to get clean command
                command = stripped_line.split('@')[0].strip()
                if command not in commands:  # Avoid duplicates
                    commands.append(command)
                continue

            # Extract suggestions (format: [suggestion text])
            if stripped_line.startswith('[') and stripped_line.endswith(']'):
                suggestion_text = stripped_line[1:-1].strip()
                if suggestion_text and suggestion_text not in suggestions:  # Avoid duplicates
                    suggestions.append(suggestion_text)
                continue

            # Extract search queries (format: <code>query text</code>)
            if stripped_line.startswith('<code>') and stripped_line.endswith('</code>'):
                query_text = stripped_line[6:-7].strip()  # Remove <code> and </code> tags
                if query_text and query_text not in search_queries:  # Avoid duplicates
                    search_queries.append(query_text)
                continue

            # Regular content lines
            main_content_lines.append(stripped_line)

        # Join non-special lines as main text
        main_text = '\n'.join(main_content_lines).strip()

        # Create AIResponse object
        return AIResponse(
            text=main_text or "Here's what I found for you:",
            suggestions=suggestions,
            commands=commands,
            search_queries=search_queries,
            confidence=0.95,  # Default confidence
            model_used=self.model
        )

    def _sanitize_response(self, response_text: str) -> str:
        """
        Sanitize AI response text.

        Args:
            response_text: Raw response text

        Returns:
            Sanitized text safe for Telegram
        """
        # Remove potentially harmful content
        sanitized = response_text.replace('\r', '').replace('\t', ' ')

        # Limit length
        max_length = 4000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."

        return sanitized.strip()


    @property
    def is_ready(self) -> bool:
        """
        Check if service is ready to generate responses.

        Returns:
            True if service is ready, False otherwise
        """
        return bool(self.ai_instruction and self.client.is_started)

# Global instance for convenience
ai_assistant: Optional[AIAssistantService] = None

def get_ai_assistant() -> AIAssistantService:
    """
    Get global AI assistant instance.

    Returns:
        AIAssistantService instance

    Raises:
        RuntimeError: If service is not initialized
    """
    global ai_assistant
    if ai_assistant is None:
        raise RuntimeError("AIAssistantService not initialized")
    return ai_assistant

__all__ = [
    "AIAssistantService",
    "get_ai_assistant",
    "ai_assistant"
]