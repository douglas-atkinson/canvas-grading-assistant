"""Provider-neutral request and response models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelRequest:
    """The canonical request given to any model provider."""

    system_prompt: str
    user_prompt: str
    response_schema: dict[str, Any]
    response_format_name: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class ProviderResponse:
    """A provider-neutral envelope around a model response."""

    provider_name: str
    model_name: str
    status: str
    response_id: str | None
    output_text: str
    raw_response: dict[str, Any]
    usage: dict[str, Any] | None
    elapsed_seconds: float
    schema_enforced: bool
    finish_reason: str | None = None
    incomplete_details: dict[str, Any] | None = None
