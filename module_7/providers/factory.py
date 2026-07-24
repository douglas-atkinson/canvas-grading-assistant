"""Create a provider from a configuration profile."""

from __future__ import annotations

from ..config import ProviderProfile
from .base import ModelProvider


def create_provider(profile: ProviderProfile) -> ModelProvider:
    """
    Create the requested provider.

    Future local adapters should be registered here without changing the
    grading request, prompt builder, validation, or output workflow.
    """
    if profile.provider == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(profile)

    raise ValueError(
        f"Unsupported model provider: {profile.provider}. "
        "Currently registered providers: openai"
    )
