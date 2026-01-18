"""
AI assistant helpers.

This module exposes lightweight helpers that simulate LLM-style reasoning so
the UI can integrate AI driven workflows without requiring a real API key.
Replace implementations inside :mod:`core.assistant.ai_helper` with actual
LLM calls when deploying to production.
"""

from .ai_helper import AIHelper, StrategySuggestion

__all__ = ["AIHelper", "StrategySuggestion"]
