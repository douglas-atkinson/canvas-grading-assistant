"""Abstract interface implemented by every model provider."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ModelRequest, ProviderResponse


class ModelProvider(ABC):
    """Provider-neutral model interface."""

    @abstractmethod
    def describe(self) -> dict[str, str]:
        """Return non-secret provider and model information."""

    @abstractmethod
    def check_availability(self) -> None:
        """Raise an exception when the configured provider is unavailable."""

    @abstractmethod
    def evaluate(self, request: ModelRequest) -> ProviderResponse:
        """Evaluate one canonical grading request."""
