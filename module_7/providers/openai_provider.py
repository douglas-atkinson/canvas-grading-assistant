"""OpenAI Responses API provider."""

from __future__ import annotations

import os
import time
from typing import Any

from openai import OpenAI

from ..config import ProviderProfile
from ..models import ModelRequest, ProviderResponse
from .base import ModelProvider


class OpenAIProvider(ModelProvider):
    """Evaluate grading requests with the OpenAI Responses API."""

    def __init__(self, profile: ProviderProfile) -> None:
        self.profile = profile

        api_key = os.getenv(profile.api_key_env)
        if not api_key:
            raise ValueError(
                f"Environment variable {profile.api_key_env} is not set."
            )

        self.client = OpenAI(
            api_key=api_key,
            timeout=profile.timeout_seconds,
            max_retries=profile.max_retries,
        )

    def describe(self) -> dict[str, str]:
        return {
            "provider": "openai",
            "model": self.profile.model,
            "profile": self.profile.profile_name,
        }

    def check_availability(self) -> None:
        """
        Verify that the configured model is visible to the API project.

        This performs a metadata request but does not run inference.
        """
        self.client.models.retrieve(self.profile.model)

    @staticmethod
    def _to_plain_dict(value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value

        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump(mode="json")
            if isinstance(dumped, dict):
                return dumped

        return {"value": str(value)}

    def evaluate(self, request: ModelRequest) -> ProviderResponse:
        arguments: dict[str, Any] = {
            "model": self.profile.model,
            "instructions": request.system_prompt,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": request.user_prompt,
                        }
                    ],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": request.response_format_name,
                    "description": (
                        "A structured advisory grading suggestion for "
                        "one anonymous programming submission."
                    ),
                    "schema": request.response_schema,
                    "strict": True,
                }
            },
            "max_output_tokens": self.profile.max_output_tokens,
            "store": False,
            "metadata": request.metadata,
        }

        if self.profile.reasoning_effort is not None:
            arguments["reasoning"] = {
                "effort": self.profile.reasoning_effort,
            }

        started = time.perf_counter()
        response = self.client.responses.create(**arguments)
        elapsed = time.perf_counter() - started

        raw_response = response.model_dump(mode="json")
        output_text = response.output_text or ""

        status = str(getattr(response, "status", "unknown"))
        incomplete_details = self._to_plain_dict(
            getattr(response, "incomplete_details", None)
        )
        usage = self._to_plain_dict(getattr(response, "usage", None))

        finish_reason = None
        if incomplete_details:
            finish_reason = str(incomplete_details.get("reason"))

        return ProviderResponse(
            provider_name="openai",
            model_name=self.profile.model,
            status=status,
            response_id=getattr(response, "id", None),
            output_text=output_text,
            raw_response=raw_response,
            usage=usage,
            elapsed_seconds=elapsed,
            schema_enforced=True,
            finish_reason=finish_reason,
            incomplete_details=incomplete_details,
        )
