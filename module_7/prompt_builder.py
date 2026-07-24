"""Build the provider-neutral grading prompt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ModelRequest


PROMPT_VERSION = "module7-grading-v2"


def load_system_prompt(prompt_path: Path) -> str:
    """Load the version-controlled grading instructions."""
    if not prompt_path.is_file():
        raise FileNotFoundError(
            f"System prompt file not found: {prompt_path}"
        )

    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError("System prompt cannot be empty.")
    return prompt


def compact_json(value: dict[str, Any]) -> str:
    """Serialize compact, stable JSON without removing information."""
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def find_first_anonymous_label(value: Any) -> str | None:
    """Recursively locate the first anonymous_label value."""
    if isinstance(value, dict):
        label = value.get("anonymous_label")
        if isinstance(label, str) and label.strip():
            return label.strip()

        for child in value.values():
            found = find_first_anonymous_label(child)
            if found:
                return found

    elif isinstance(value, list):
        for child in value:
            found = find_first_anonymous_label(child)
            if found:
                return found

    return None


def build_model_request(
    grading_package: dict[str, Any],
    student_material: dict[str, Any],
    response_schema: dict[str, Any],
    system_prompt: str,
    response_format_name: str,
) -> ModelRequest:
    """Construct one canonical provider-neutral request."""
    anonymous_label = (
        find_first_anonymous_label(student_material)
        or find_first_anonymous_label(grading_package)
        or "unknown_submission"
    )

    payload = (
        "Evaluate the anonymous programming submission using the "
        "following authoritative grading package and AI-safe student "
        "material. Return only the structured result required by the "
        "provider-enforced response schema.\n\n"
        "GRADING_PACKAGE_JSON\n"
        f"{compact_json(grading_package)}\n\n"
        "AI_SAFE_STUDENT_MATERIAL_JSON\n"
        f"{compact_json(student_material)}"
    )

    return ModelRequest(
        system_prompt=system_prompt,
        user_prompt=payload,
        response_schema=response_schema,
        response_format_name=response_format_name,
        metadata={
            "module": "7",
            "prompt_version": PROMPT_VERSION,
            "anonymous_label": anonymous_label[:512],
        },
    )
