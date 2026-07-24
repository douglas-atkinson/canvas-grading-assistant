"""Load and validate model-provider profiles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProviderProfile:
    """Configuration for one model provider profile."""

    profile_name: str
    provider: str
    model: str
    api_key_env: str
    timeout_seconds: float
    max_retries: int
    max_output_tokens: int
    reasoning_effort: str | None
    response_format_name: str
    store: bool
    max_input_characters: int


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Profile field '{field_name}' must be a non-empty string."
        )
    return value.strip()


def load_profile(
    config_path: Path,
    requested_profile: str | None,
) -> ProviderProfile:
    """Load one named profile from a JSON configuration file."""
    if not config_path.is_file():
        raise FileNotFoundError(
            f"Model profile configuration not found: {config_path}"
        )

    with config_path.open("r", encoding="utf-8") as input_file:
        config = json.load(input_file)

    if not isinstance(config, dict):
        raise ValueError("Model profile configuration must be a JSON object.")

    profiles = config.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError(
            "Model profile configuration must contain a non-empty "
            "'profiles' object."
        )

    profile_name = requested_profile or config.get("active_profile")
    profile_name = _require_string(profile_name, "active_profile")

    raw_profile = profiles.get(profile_name)
    if not isinstance(raw_profile, dict):
        raise ValueError(f"Model profile '{profile_name}' was not found.")

    provider = _require_string(
        raw_profile.get("provider"), "provider"
    ).lower()
    model = _require_string(raw_profile.get("model"), "model")
    api_key_env = _require_string(
        raw_profile.get("api_key_env", "OPENAI_API_KEY"),
        "api_key_env",
    )

    timeout_seconds = float(raw_profile.get("timeout_seconds", 180))
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero.")

    max_retries = int(raw_profile.get("max_retries", 0))
    if max_retries < 0:
        raise ValueError("max_retries cannot be negative.")

    max_output_tokens = int(raw_profile.get("max_output_tokens", 8000))
    if max_output_tokens <= 0:
        raise ValueError("max_output_tokens must be greater than zero.")

    reasoning_effort = raw_profile.get("reasoning_effort")
    if reasoning_effort is not None:
        reasoning_effort = _require_string(
            reasoning_effort, "reasoning_effort"
        )

    response_format_name = _require_string(
        raw_profile.get("response_format_name", "grading_suggestion"),
        "response_format_name",
    )

    store = raw_profile.get("store", False)
    if store is not False:
        raise ValueError(
            "Module 7 requires profile field 'store' to be false."
        )

    max_input_characters = int(
        raw_profile.get("max_input_characters", 500_000)
    )
    if max_input_characters <= 0:
        raise ValueError(
            "max_input_characters must be greater than zero."
        )

    return ProviderProfile(
        profile_name=profile_name,
        provider=provider,
        model=model,
        api_key_env=api_key_env,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        max_output_tokens=max_output_tokens,
        reasoning_effort=reasoning_effort,
        response_format_name=response_format_name,
        store=False,
        max_input_characters=max_input_characters,
    )
