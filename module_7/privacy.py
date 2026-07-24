"""Final privacy and transmission safety checks."""

from __future__ import annotations

from typing import Any


FORBIDDEN_STUDENT_KEYS = {
    "canvas_user_id",
    "student_id",
    "student_name",
    "student_email",
    "sis_user_id",
    "login_id",
    "download_url",
    "preview_url",
    "secure_params",
}


def find_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    """Return paths containing forbidden student/private keys."""
    findings: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"

            if key_text.lower() in FORBIDDEN_STUDENT_KEYS:
                findings.append(child_path)

            if key_text == "send_to_ai" and child is False:
                findings.append(f"{child_path}=false")

            findings.extend(find_forbidden_keys(child, child_path))

    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(
                find_forbidden_keys(child, f"{path}[{index}]")
            )

    return findings


def find_explicit_privacy_failures(
    value: Any,
    path: str = "$",
) -> list[str]:
    """Find explicit flags stating that identifying data is present."""
    failures: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"

            if (
                key in {
                    "contains_canvas_user_id",
                    "contains_student_name",
                    "contains_download_urls",
                }
                and child is True
            ):
                failures.append(f"{child_path}=true")

            failures.extend(
                find_explicit_privacy_failures(child, child_path)
            )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            failures.extend(
                find_explicit_privacy_failures(
                    child, f"{path}[{index}]"
                )
            )

    return failures


def assert_ai_safe(student_material: dict[str, Any]) -> None:
    """Refuse transmission when private fields or flags are present."""
    findings = find_forbidden_keys(student_material)
    failures = find_explicit_privacy_failures(student_material)
    all_findings = sorted(set(findings + failures))

    if all_findings:
        joined = "\n  - ".join(all_findings)
        raise ValueError(
            "AI-safe student material failed the final privacy gate:\n"
            f"  - {joined}"
        )
