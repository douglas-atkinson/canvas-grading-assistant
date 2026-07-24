"""Load Module 6 assets and AI-safe student material."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SUPPORTED_TEXT_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
    ".inl", ".json", ".md", ".txt", ".csv",
}


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object."""
    if not path.is_file():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with path.open("r", encoding="utf-8") as input_file:
        data = json.load(input_file)

    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in: {path}")

    return data


def load_student_material(path: Path) -> dict[str, Any]:
    """
    Load AI-safe student material from JSON, a text file, or a directory.

    A directory is converted to a stable list of relative paths and text.
    """
    if path.is_dir():
        files: list[dict[str, str]] = []

        for file_path in sorted(path.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in SUPPORTED_TEXT_EXTENSIONS:
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError as error:
                raise ValueError(
                    f"Student material is not UTF-8 text: {file_path}"
                ) from error

            files.append({
                "relative_path": str(
                    file_path.relative_to(path)
                ).replace("\\", "/"),
                "content": content,
            })

        if not files:
            raise ValueError(
                f"No supported text files found in: {path}"
            )

        return {"source_type": "directory", "files": files}

    if not path.is_file():
        raise FileNotFoundError(f"Student material not found: {path}")

    if path.suffix.lower() == ".json":
        return load_json(path)

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            f"Student material is not UTF-8 text: {path}"
        ) from error

    return {
        "source_type": "text_file",
        "file_name": path.name,
        "content": content,
    }


def load_response_schema(
    grading_package: dict[str, Any],
    grading_package_path: Path,
    schema_path: Path | None,
) -> dict[str, Any]:
    """
    Load the structured-response schema.

    Priority:
    1. Explicit --response-schema path
    2. Embedded grading_package["response_schema"]
    3. grading_package["response_schema_path"]
    """
    if schema_path is not None:
        return load_json(schema_path)

    embedded = grading_package.get("response_schema")
    if isinstance(embedded, dict):
        return embedded

    relative_path = grading_package.get("response_schema_path")
    if isinstance(relative_path, str) and relative_path.strip():
        candidate = (
            grading_package_path.parent / relative_path
        ).resolve()
        return load_json(candidate)

    raise ValueError(
        "No response schema was supplied. Pass --response-schema, "
        "embed response_schema in the grading package, or provide "
        "response_schema_path in the grading package."
    )
