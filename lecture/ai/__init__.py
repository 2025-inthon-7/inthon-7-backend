"""
AI integration package for the lecture app.

This package contains:
- llm_client: low-level Gemini client wrapper
- clean: question cleaning helper
- answer: question answering helper
- prompt_templates: system/user prompt templates
"""

from .clean import clean_question
from .answer import answer_question
from .llm_client import LLMClient


__all__ = [
    'clean_question',
    'answer_question',
    'LLMClient',
]

