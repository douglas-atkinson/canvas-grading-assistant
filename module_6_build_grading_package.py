"""Build one provider-neutral grading request package for one submission.

Usage:
    python module_6_build_grading_package.py \
        grading_assets/cars_engines_steering \
        output/assignment_3572383/submission_001

Add --overwrite to replace an existing grading_request directory.
This module contacts neither Canvas nor a model provider.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

MODULE_NUMBER = "6"
SCHEMA_VERSION = "1.1"
CORE_ASSETS = {
    "assignment_spec.md",
    "rubric.json",
    "instructor_notes.md",
    "package_config.json",
}
CPP_SOURCE_EXTENSIONS = {".cc", ".cpp", ".cxx"}
TEXT_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
    ".inl", ".json", ".md", ".txt", ".csv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build one complete Module 6 grading request package."
    )
    parser.add_argument("grading_assets", type=Path)
    parser.add_argument("submission_directory", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--allow-warnings",
        action="store_true",
        help="Allow Module 5.1 warnings while preserving them in the package.",
    )
    parser.add_argument(
        "--compiler",
        default="auto",
        help=(
            "C++ compiler executable or auto. Auto checks CXX, g++, clang++, "
            "and cl in that order."
        ),
    )
    parser.add_argument(
        "--skip-compile",
        action="store_true",
        help="Do not attempt local compilation.",
    )
    parser.add_argument(
        "--require-compiler",
        action="store_true",
        help="Fail Module 6 when no supported compiler is available.",
    )
    parser.add_argument(
        "--run-student-code",
        action="store_true",
        help=(
            "After successful compilation, explicitly allow the student program "
            "to run locally with a hard timeout."
        ),
    )
    parser.add_argument(
        "--run-timeout",
        type=float,
        default=10.0,
        help="Maximum execution time in seconds when --run-student-code is used.",
    )
    parser.add_argument(
        "--max-captured-output",
        type=int,
        default=100_000,
        help="Maximum characters retained from each compiler/program output stream.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in: {path}")
    return value


def read_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Text file not found: {path}")
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(f"Expected UTF-8 text: {path}") from error


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def count_lines(text: str) -> int:
    return len(text.splitlines())


def numbered(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    width = max(4, len(str(len(lines))))
    return "\n".join(
        f"{index:0{width}d}: {line}"
        for index, line in enumerate(lines, 1)
    )


def norm_path(value: str) -> str:
    return value.replace("\\", "/").lstrip("./")


def require_assets(root: Path) -> None:
    missing = sorted(name for name in CORE_ASSETS if not (root / name).is_file())
    if missing:
        raise FileNotFoundError(
            "Required grading assets are missing:\n  - " + "\n  - ".join(missing)
        )


def validate_ai_manifest(
    manifest: dict[str, Any], allow_warnings: bool
) -> tuple[str, int | None, list[str], list[str]]:
    privacy = manifest.get("privacy")
    if not isinstance(privacy, dict):
        raise ValueError("Module 5.1 manifest has no privacy object.")

    required_false = [
        "contains_canvas_user_id",
        "contains_student_name",
        "contains_original_zip_filename",
        "contains_download_urls",
    ]
    unsafe = [key for key in required_false if privacy.get(key) is not False]
    if unsafe:
        raise ValueError(
            "Module 5.1 manifest is not explicitly AI-safe for:\n  - "
            + "\n  - ".join(unsafe)
        )

    submission = manifest.get("submission")
    package = manifest.get("package")
    if not isinstance(submission, dict) or not isinstance(package, dict):
        raise ValueError("Module 5.1 manifest is missing submission/package data.")

    label = submission.get("anonymous_label")
    if not isinstance(label, str) or not label.strip():
        raise ValueError("Module 5.1 manifest has no anonymous label.")
    label = label.strip()

    attempt = submission.get("selected_attempt")
    if attempt is not None and not isinstance(attempt, int):
        raise ValueError("selected_attempt must be an integer or null.")

    if package.get("comments_removed") is not True:
        raise ValueError("Module 5.1 does not confirm comment removal.")
    if package.get("known_identifiers_redacted") is not True:
        raise ValueError("Module 5.1 does not confirm identifier redaction.")

    raw_files = package.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise ValueError("Module 5.1 manifest has no source-file list.")
    expected = []
    for item in raw_files:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("Module 5.1 file paths must be non-empty strings.")
        expected.append(norm_path(item))

    raw_warnings = manifest.get("warnings", [])
    if not isinstance(raw_warnings, list):
        raise ValueError("Module 5.1 warnings must be a list.")
    warnings = [str(item) for item in raw_warnings]
    if warnings and not allow_warnings:
        raise ValueError(
            "Module 5.1 reported warnings. Review them or use --allow-warnings:\n"
            "  - " + "\n  - ".join(warnings)
        )

    return label, attempt, sorted(expected), warnings


def student_records(candidate_root: Path, expected: list[str]) -> list[dict[str, Any]]:
    if not candidate_root.is_dir():
        raise FileNotFoundError(f"AI-candidate directory not found: {candidate_root}")

    actual = sorted(
        path.relative_to(candidate_root).as_posix()
        for path in candidate_root.rglob("*")
        if path.is_file()
    )
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        details = []
        if missing:
            details.append("Missing:\n  - " + "\n  - ".join(missing))
        if unexpected:
            details.append("Unexpected:\n  - " + "\n  - ".join(unexpected))
        raise ValueError(
            "AI-candidate tree does not match the Module 5.1 manifest.\n"
            + "\n".join(details)
        )

    records = []
    for relative in actual:
        path = candidate_root / Path(relative)
        if path.is_symlink():
            raise ValueError(f"Symbolic links are not allowed: {relative}")
        text = read_text(path)
        records.append({
            "relative_path": relative,
            "line_count": count_lines(text),
            "character_count": len(text),
            "sha256": digest(text),
            "numbered_source": numbered(text),
        })
    return records


def inside(root: Path, relative: str, field: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError(f"package_config field '{field}' must be a path string.")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"Configured path escapes grading_assets: {relative}") from error
    return resolved


def text_record(path: Path, display_path: str) -> dict[str, Any]:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        raise ValueError(f"Unsupported grading-asset file type: {path}")
    text = read_text(path)
    return {
        "relative_path": display_path,
        "line_count": count_lines(text),
        "character_count": len(text),
        "sha256": digest(text),
        "numbered_content": numbered(text),
    }


def directory_records(directory: Path, prefix: str) -> list[dict[str, Any]]:
    if not directory.is_dir():
        raise FileNotFoundError(f"Configured asset directory not found: {directory}")
    result = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS:
            relative = path.relative_to(directory).as_posix()
            result.append(text_record(path, f"{prefix.rstrip('/')}/{relative}"))
    return result


def configured_records(
    root: Path,
    configured: Any,
    field: str,
    auto_directory: str | None = None,
) -> list[dict[str, Any]]:
    if configured is None:
        configured = []
    if not isinstance(configured, list):
        raise ValueError(f"package_config field '{field}' must be a list.")

    names = [item.strip() for item in configured if isinstance(item, str) and item.strip()]
    if not names and auto_directory:
        auto_root = root / auto_directory
        if auto_root.is_dir():
            names = [
                path.relative_to(root).as_posix()
                for path in sorted(auto_root.rglob("*"))
                if path.is_file()
                and path.suffix.lower() in TEXT_EXTENSIONS
                and path.name.lower() != "readme.md"
            ]

    result = []
    for name in names:
        path = inside(root, name, field)
        if not path.is_file():
            raise FileNotFoundError(f"Configured asset file not found: {name}")
        result.append(text_record(path, norm_path(name)))
    return result


def validate_rubric(rubric: dict[str, Any]) -> dict[str, Any]:
    total = rubric.get("maximum_points")
    criteria = rubric.get("criteria")
    if not isinstance(total, (int, float)):
        raise ValueError("Rubric maximum_points must be numeric.")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("Rubric criteria must be a non-empty list.")

    criterion_ids: set[str] = set()
    item_ids: set[str] = set()
    criterion_sum = 0.0
    item_count = 0
    max_item = 0.0

    for criterion in criteria:
        if not isinstance(criterion, dict):
            raise ValueError("Every rubric criterion must be an object.")
        cid = criterion.get("id")
        cmax = criterion.get("maximum_points")
        items = criterion.get("items")
        if not isinstance(cid, str) or not cid:
            raise ValueError("Every criterion requires a non-empty id.")
        if cid in criterion_ids:
            raise ValueError(f"Duplicate criterion id: {cid}")
        criterion_ids.add(cid)
        if not isinstance(cmax, (int, float)):
            raise ValueError(f"Criterion {cid} maximum_points must be numeric.")
        if not isinstance(items, list) or not items:
            raise ValueError(f"Criterion {cid} has no rubric items.")

        item_sum = 0.0
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Criterion {cid} contains a non-object item.")
            iid = item.get("id")
            imax = item.get("maximum_points")
            if not isinstance(iid, str) or not iid:
                raise ValueError(f"Criterion {cid} has an item without an id.")
            if iid in item_ids:
                raise ValueError(f"Duplicate rubric item id: {iid}")
            item_ids.add(iid)
            if not isinstance(imax, (int, float)) or imax < 0:
                raise ValueError(f"Rubric item {iid} has invalid maximum_points.")
            item_sum += float(imax)
            item_count += 1
            max_item = max(max_item, float(imax))

        if abs(item_sum - float(cmax)) > 1e-9:
            raise ValueError(
                f"Criterion {cid} item total is {item_sum:g}, not {cmax:g}."
            )
        criterion_sum += float(cmax)

    if abs(criterion_sum - float(total)) > 1e-9:
        raise ValueError(f"Rubric criteria total is {criterion_sum:g}, not {total:g}.")

    rules = rubric.get("global_rules", [])
    if not isinstance(rules, list):
        raise ValueError("Rubric global_rules must be a list.")
    rule_ids: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("id"), str):
            raise ValueError("Every global rule requires a string id.")
        rid = rule["id"]
        if rid in rule_ids:
            raise ValueError(f"Duplicate global rule id: {rid}")
        rule_ids.add(rid)

    return {
        "maximum_points": total,
        "criterion_count": len(criteria),
        "item_count": item_count,
        "global_rule_count": len(rules),
        "criterion_ids": sorted(criterion_ids),
        "item_ids": sorted(item_ids),
        "global_rule_ids": sorted(rule_ids),
        "maximum_item_points": max_item,
    }


def response_schema(summary: dict[str, Any]) -> dict[str, Any]:
    """Build the strict structured-output schema used by every provider."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Programming Assignment Grading Suggestion",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "submission_label",
            "rubric_item_results",
            "global_rule_assessments",
            "student_feedback",
            "instructor_summary",
            "overall_confidence",
            "manual_review_flags",
        ],
        "properties": {
            "submission_label": {"type": "string", "minLength": 1},
            "rubric_item_results": {
                "type": "array",
                "minItems": summary["item_count"],
                "maxItems": summary["item_count"],
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "criterion_id",
                        "item_id",
                        "maximum_points",
                        "assessment_status",
                        "suggested_points",
                        "rationale",
                        "evidence",
                        "confidence",
                        "manual_review_needed",
                    ],
                    "properties": {
                        "criterion_id": {
                            "type": "string",
                            "enum": summary["criterion_ids"],
                        },
                        "item_id": {
                            "type": "string",
                            "enum": summary["item_ids"],
                        },
                        "maximum_points": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": summary["maximum_item_points"],
                        },
                        "assessment_status": {
                            "type": "string",
                            "enum": ["scored", "requires_local_evidence"],
                        },
                        "suggested_points": {
                            "type": ["number", "null"],
                            "minimum": 0,
                            "maximum": summary["maximum_item_points"],
                        },
                        "rationale": {"type": "string"},
                        "evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": [
                                    "file", "line_start", "line_end", "description"
                                ],
                                "properties": {
                                    "file": {"type": "string"},
                                    "line_start": {
                                        "type": ["integer", "null"],
                                        "minimum": 1,
                                    },
                                    "line_end": {
                                        "type": ["integer", "null"],
                                        "minimum": 1,
                                    },
                                    "description": {"type": "string"},
                                },
                            },
                        },
                        "confidence": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "manual_review_needed": {"type": "boolean"},
                    },
                },
            },
            "global_rule_assessments": {
                "type": "array",
                "minItems": summary["global_rule_count"],
                "maxItems": summary["global_rule_count"],
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "rule_id", "applicable", "recommended_action",
                        "recommended_value", "rationale",
                        "objective_evidence_required", "manual_review_needed",
                    ],
                    "properties": {
                        "rule_id": {
                            "type": "string",
                            "enum": summary["global_rule_ids"],
                        },
                        "applicable": {"type": "boolean"},
                        "recommended_action": {
                            "type": "string",
                            "enum": ["none", "deduction", "score_cap"],
                        },
                        "recommended_value": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": summary["maximum_points"],
                        },
                        "rationale": {"type": "string"},
                        "objective_evidence_required": {"type": "boolean"},
                        "manual_review_needed": {"type": "boolean"},
                    },
                },
            },
            "student_feedback": {"type": "string"},
            "instructor_summary": {"type": "string"},
            "overall_confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
            },
            "manual_review_flags": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    }


def reference_validation(asset_root: Path) -> dict[str, Any]:
    path = asset_root / "reference_validation.json"
    if not path.is_file():
        return {"available": False, "note": "No validation report supplied."}
    raw = load_json(path)
    allowed = {
        "compile_return_code", "compiler_stdout", "compiler_stderr",
        "run_return_code", "program_stdout", "program_stderr",
    }
    result = {key: raw.get(key) for key in sorted(allowed) if key in raw}
    result["available"] = True
    return result


def artifact_evidence(
    submission_root: Path, label: str, attempt: int | None
) -> dict[str, Any]:
    """Whitelist harmless objective facts from Module 4's private manifest."""
    result = {
        "available": False,
        "anonymous_label": label,
        "selected_attempt": attempt,
        "artifact_type": "unknown",
        "submission_type": "unknown",
        "archive_entry_count": None,
    }
    path = submission_root / "module_4_private_extraction_manifest.json"
    if not path.is_file():
        return result

    private = load_json(path)
    selection = private.get("selection")
    local = private.get("local_files")
    selection = selection if isinstance(selection, dict) else {}
    local = local if isinstance(local, dict) else {}
    filename = selection.get("original_zip_filename")

    result.update({
        "available": True,
        "artifact_type": (
            "zip_archive"
            if isinstance(filename, str) and filename.lower().endswith(".zip")
            else "unknown"
        ),
        "submission_type": (
            selection.get("submission_type")
            if isinstance(selection.get("submission_type"), str)
            else "unknown"
        ),
        "archive_entry_count": (
            local.get("entry_count")
            if isinstance(local.get("entry_count"), int)
            else None
        ),
    })
    return result



def ensure_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def trim_output(text: str | bytes | None, maximum: int) -> tuple[str, bool]:
    text = ensure_text(text)
    if len(text) <= maximum:
        return text, False
    marker = f"\n...[truncated after {maximum} characters]...\n"
    return text[:maximum] + marker, True


def safe_command(parts: list[str], build_root: Path) -> list[str]:
    """Return a path-neutral command suitable for the outbound package."""
    cleaned: list[str] = []
    root_text = str(build_root.resolve())
    for index, part in enumerate(parts):
        value = str(part).replace(root_text, "<BUILD_DIR>")
        if index == 0:
            value = Path(value).name
        cleaned.append(value)
    return cleaned


def compiler_kind(executable: str) -> str:
    name = Path(executable).name.lower()
    if name in {"cl", "cl.exe"}:
        return "msvc"
    if "clang" in name:
        return "clang"
    return "gcc"


def locate_compiler(requested: str) -> str | None:
    candidates: list[str] = []
    if requested != "auto":
        candidates.append(requested)
    else:
        configured = os.getenv("CXX")
        if configured:
            candidates.append(configured)
        candidates.extend(["g++", "clang++", "cl"])

    for candidate in candidates:
        candidate_path = Path(candidate)
        if candidate_path.is_file():
            return str(candidate_path.resolve())
        found = shutil.which(candidate)
        if found:
            return found
    return None


def compiler_version(executable: str, kind: str, timeout: float = 5.0) -> str:
    command = [executable] if kind == "msvc" else [executable, "--version"]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            errors="replace",
        )
    except Exception as error:
        return f"Unavailable: {error}"
    combined = (result.stdout + "\n" + result.stderr).strip()
    return combined.splitlines()[0] if combined else "Unknown"


def copy_build_inputs(
    candidate_root: Path,
    supporting_files: list[dict[str, Any]],
    asset_root: Path,
    build_root: Path,
) -> list[Path]:
    """Copy AI-safe source and configured support files into a temporary build tree."""
    source_files: list[Path] = []
    for source in sorted(candidate_root.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(candidate_root)
        destination = build_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if source.suffix.lower() in CPP_SOURCE_EXTENSIONS:
            source_files.append(destination)

    copied_names: set[str] = set()
    for record in supporting_files:
        relative = record.get("relative_path")
        if not isinstance(relative, str):
            continue
        source = asset_root / Path(relative)
        if not source.is_file():
            raise FileNotFoundError(f"Supporting build file not found: {source}")
        name = source.name
        if name in copied_names:
            raise ValueError(f"Duplicate supporting filename for build: {name}")
        copied_names.add(name)
        shutil.copy2(source, build_root / name)

    return source_files


def normalized_output(text: str) -> str:
    """Ignore blank lines and insignificant whitespace for output comparison."""
    normalized_lines = []
    for line in text.splitlines():
        collapsed = re.sub(r"\s+", " ", line.strip())
        collapsed = re.sub(r"\s*:\s*", ": ", collapsed)
        if collapsed:
            normalized_lines.append(collapsed.casefold())
    return "\n".join(normalized_lines)


def build_compile_command(
    compiler: str,
    kind: str,
    sources: list[Path],
    executable: Path,
    build_root: Path,
) -> list[str]:
    relative_sources = [str(path.relative_to(build_root)) for path in sources]
    include_dirs = sorted({str(path.parent.relative_to(build_root)) for path in sources})
    include_dirs = [value for value in include_dirs if value != "."]

    if kind == "msvc":
        command = [
            compiler,
            "/nologo",
            "/EHsc",
            "/std:c++17",
            "/W4",
            f"/Fe:{executable.name}",
        ]
        command.extend(f"/I{directory}" for directory in include_dirs)
        command.extend(relative_sources)
        return command

    command = [
        compiler,
        "-std=c++17",
        "-Wall",
        "-Wextra",
        "-pedantic",
    ]
    command.extend([argument for directory in include_dirs for argument in ("-I", directory)])
    command.extend(relative_sources)
    command.extend(["-o", executable.name])
    return command


def local_compile_run_evidence(
    candidate_root: Path,
    supporting_files: list[dict[str, Any]],
    asset_root: Path,
    reference: dict[str, Any],
    compiler_request: str,
    skip_compile: bool,
    require_compiler: bool,
    run_student_code: bool,
    run_timeout: float,
    max_output: int,
) -> dict[str, Any]:
    """Compile locally and optionally execute with an explicit permission flag."""
    if run_timeout <= 0:
        raise ValueError("--run-timeout must be greater than zero.")
    if max_output <= 0:
        raise ValueError("--max-captured-output must be greater than zero.")

    base = {
        "security": {
            "student_code_is_untrusted": True,
            "execution_explicitly_requested": run_student_code,
            "execution_timeout_seconds": run_timeout,
            "note": (
                "Compilation does not execute the program. Execution occurred only "
                "when --run-student-code was explicitly supplied."
            ),
        },
        "student_compilation": {
            "available": False,
            "status": "not_run",
        },
        "student_execution": {
            "available": False,
            "status": "not_run",
        },
        "output_comparison": {
            "available": False,
            "status": "not_run",
        },
    }

    if skip_compile:
        base["student_compilation"].update({
            "status": "skipped",
            "instruction": (
                "Compilation was explicitly skipped. Missing evidence must not "
                "cause a score deduction."
            ),
        })
        base["student_execution"].update({
            "status": "not_run_compile_skipped",
        })
        return base

    compiler = locate_compiler(compiler_request)
    if compiler is None:
        if require_compiler:
            raise RuntimeError(
                "No supported C++ compiler was found. Configure CXX, pass "
                "--compiler, or install g++, clang++, or a Developer Command "
                "Prompt environment containing cl."
            )
        base["student_compilation"].update({
            "status": "compiler_unavailable",
            "instruction": (
                "No compiler was available. Missing evidence must not cause a "
                "score deduction; mark evidence-dependent items as "
                "requires_local_evidence."
            ),
        })
        base["student_execution"].update({
            "status": "not_run_compiler_unavailable",
        })
        return base

    kind = compiler_kind(compiler)
    with tempfile.TemporaryDirectory(prefix="module6_build_") as temp_name:
        build_root = Path(temp_name)
        sources = copy_build_inputs(
            candidate_root,
            supporting_files,
            asset_root,
            build_root,
        )
        if not sources:
            base["student_compilation"].update({
                "available": True,
                "status": "failed_no_source_files",
                "compiler": Path(compiler).name,
                "compiler_version": compiler_version(compiler, kind),
                "return_code": None,
                "stdout": "",
                "stderr": "No C++ implementation source files were found.",
            })
            base["student_execution"].update({
                "status": "not_run_compile_failed",
            })
            return base

        executable = build_root / (
            "student_program.exe" if os.name == "nt" or kind == "msvc" else "student_program"
        )
        command = build_compile_command(
            compiler,
            kind,
            sources,
            executable,
            build_root,
        )
        started = time.perf_counter()
        try:
            compile_result = subprocess.run(
                command,
                cwd=build_root,
                capture_output=True,
                text=True,
                timeout=120,
                errors="replace",
            )
            compile_elapsed = time.perf_counter() - started
            compile_stdout, compile_stdout_truncated = trim_output(
                compile_result.stdout, max_output
            )
            compile_stderr, compile_stderr_truncated = trim_output(
                compile_result.stderr, max_output
            )
            compile_success = compile_result.returncode == 0 and executable.is_file()
            base["student_compilation"] = {
                "available": True,
                "status": "success" if compile_success else "failed",
                "compiler": Path(compiler).name,
                "compiler_kind": kind,
                "compiler_version": compiler_version(compiler, kind),
                "command": safe_command(command, build_root),
                "source_files": [
                    path.relative_to(build_root).as_posix() for path in sources
                ],
                "return_code": compile_result.returncode,
                "elapsed_seconds": round(compile_elapsed, 4),
                "stdout": compile_stdout,
                "stderr": compile_stderr,
                "stdout_truncated": compile_stdout_truncated,
                "stderr_truncated": compile_stderr_truncated,
            }
        except subprocess.TimeoutExpired as error:
            stdout, stdout_truncated = trim_output(error.stdout or "", max_output)
            stderr, stderr_truncated = trim_output(error.stderr or "", max_output)
            base["student_compilation"] = {
                "available": True,
                "status": "timed_out",
                "compiler": Path(compiler).name,
                "compiler_kind": kind,
                "compiler_version": compiler_version(compiler, kind),
                "command": safe_command(command, build_root),
                "return_code": None,
                "elapsed_seconds": 120.0,
                "stdout": stdout,
                "stderr": stderr,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
            }
            base["student_execution"].update({
                "status": "not_run_compile_failed",
            })
            return base

        if base["student_compilation"]["status"] != "success":
            base["student_execution"].update({
                "status": "not_run_compile_failed",
            })
            return base

        if not run_student_code:
            base["student_execution"].update({
                "status": "not_requested",
                "instruction": (
                    "Execution was not authorized. Missing runtime evidence must "
                    "not cause a score deduction; use requires_local_evidence for "
                    "items that truly require runtime evidence."
                ),
            })
            return base

        run_started = time.perf_counter()
        try:
            run_result = subprocess.run(
                [str(executable)],
                cwd=build_root,
                capture_output=True,
                text=True,
                timeout=run_timeout,
                errors="replace",
            )
            run_elapsed = time.perf_counter() - run_started
            run_stdout, run_stdout_truncated = trim_output(
                run_result.stdout, max_output
            )
            run_stderr, run_stderr_truncated = trim_output(
                run_result.stderr, max_output
            )
            base["student_execution"] = {
                "available": True,
                "status": "success" if run_result.returncode == 0 else "nonzero_exit",
                "return_code": run_result.returncode,
                "elapsed_seconds": round(run_elapsed, 4),
                "timeout_seconds": run_timeout,
                "stdout": run_stdout,
                "stderr": run_stderr,
                "stdout_truncated": run_stdout_truncated,
                "stderr_truncated": run_stderr_truncated,
            }
        except subprocess.TimeoutExpired as error:
            stdout, stdout_truncated = trim_output(error.stdout or "", max_output)
            stderr, stderr_truncated = trim_output(error.stderr or "", max_output)
            base["student_execution"] = {
                "available": True,
                "status": "timed_out",
                "return_code": None,
                "elapsed_seconds": run_timeout,
                "timeout_seconds": run_timeout,
                "stdout": stdout,
                "stderr": stderr,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
            }

        expected_output = reference.get("program_stdout")
        actual_output = base["student_execution"].get("stdout")
        if (
            base["student_execution"].get("status") == "success"
            and isinstance(expected_output, str)
            and isinstance(actual_output, str)
        ):
            base["output_comparison"] = {
                "available": True,
                "status": "compared",
                "reference_source": "validated_reference_implementation",
                "exact_match": actual_output == expected_output,
                "normalized_nonblank_lines_match": (
                    normalized_output(actual_output) == normalized_output(expected_output)
                ),
                "normalization": (
                    "Trim each line, collapse internal whitespace, and ignore blank lines."
                ),
            }
        else:
            base["output_comparison"] = {
                "available": False,
                "status": "not_available",
                "reason": (
                    "A successful execution and validated reference output are both required."
                ),
            }

    return base

def preview_text(
    package: dict[str, Any],
    student: dict[str, Any],
    schema: dict[str, Any],
) -> str:
    parts = [
        "Canvas Exploration Module 6 - Grading Request Preview",
        "",
        "No Canvas or model request has been made.",
    ]
    for title, value in [
        ("GRADING PACKAGE", package),
        ("AI-SAFE STUDENT MATERIAL", student),
        ("STRUCTURED RESPONSE SCHEMA", schema),
    ]:
        parts.extend([
            "", "=" * 78, title, "=" * 78,
            json.dumps(value, indent=2, ensure_ascii=False),
        ])
    return "\n".join(parts) + "\n"


def main() -> int:
    args = parse_args()
    asset_root = args.grading_assets.resolve()
    submission_root = args.submission_directory.resolve()
    target = submission_root / "grading_request"
    staging = submission_root / ".grading_request_building"

    try:
        if not asset_root.is_dir():
            raise FileNotFoundError(f"Grading-assets directory not found: {asset_root}")
        if not submission_root.is_dir():
            raise FileNotFoundError(f"Submission directory not found: {submission_root}")
        require_assets(asset_root)

        if target.exists() and not args.overwrite:
            raise FileExistsError(
                f"Grading-request directory already exists: {target}\n"
                "Use --overwrite to replace it."
            )
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)

        config = load_json(asset_root / "package_config.json")
        rubric = load_json(asset_root / "rubric.json")
        summary = validate_rubric(rubric)
        assignment_spec = read_text(asset_root / "assignment_spec.md")
        notes = read_text(asset_root / "instructor_notes.md")

        manifest = load_json(submission_root / "module_5_ai_package_manifest.json")
        label, attempt, expected_paths, warnings = validate_ai_manifest(
            manifest, args.allow_warnings
        )
        student_files = student_records(
            submission_root / "ai_candidate", expected_paths
        )

        reference_dir = inside(
            asset_root,
            config.get("reference_solution_directory"),
            "reference_solution_directory",
        )
        reference_files = directory_records(reference_dir, "instructor_reference")
        if not reference_files:
            raise ValueError("The reference directory contains no supported text files.")

        starter_files = configured_records(
            asset_root,
            config.get("starter_files", []),
            "starter_files",
            auto_directory="starter_files",
        )
        supporting_files = configured_records(
            asset_root,
            config.get("supporting_files", []),
            "supporting_files",
        )
        reference_evidence = reference_validation(asset_root)
        local_evidence = local_compile_run_evidence(
            candidate_root=submission_root / "ai_candidate",
            supporting_files=supporting_files,
            asset_root=asset_root,
            reference=reference_evidence,
            compiler_request=args.compiler,
            skip_compile=args.skip_compile,
            require_compiler=args.require_compiler,
            run_student_code=args.run_student_code,
            run_timeout=args.run_timeout,
            max_output=args.max_captured_output,
        )
        schema = response_schema(summary)

        student_material = {
            "schema_version": SCHEMA_VERSION,
            "package_type": "ai_safe_student_material",
            "privacy": {
                "contains_canvas_user_id": False,
                "contains_student_name": False,
                "contains_original_zip_filename": False,
                "contains_download_urls": False,
                "comments_removed": True,
                "known_identifiers_redacted": True,
            },
            "submission": {
                "anonymous_label": label,
                "selected_attempt": attempt,
            },
            "source_file_count": len(student_files),
            "source_files": student_files,
            "warnings": warnings,
        }

        package = {
            "schema_version": SCHEMA_VERSION,
            "package_type": "provider_neutral_grading_package",
            "module": {
                "number": MODULE_NUMBER,
                "purpose": (
                    "Build one complete grading request without contacting "
                    "Canvas or a model provider."
                ),
            },
            "privacy": {
                "classification": "AI-candidate instructor grading package",
                "contains_canvas_user_id": False,
                "contains_student_name": False,
                "contains_original_zip_filename": False,
                "contains_download_urls": False,
                "human_review_required": True,
            },
            "submission": {
                "anonymous_label": label,
                "selected_attempt": attempt,
            },
            "assignment": {
                "asset_package_id": config.get("asset_package_id"),
                "title": config.get("assignment_title"),
                "language": config.get("language"),
                "expected_standard": config.get("expected_standard"),
            },
            "authority": {
                "order": config.get(
                    "authority_order",
                    rubric.get("scoring_authority_order", []),
                ),
                "reference_solution_role": config.get(
                    "reference_solution_role",
                    "One validated implementation, not a similarity target.",
                ),
            },
            "assignment_specification": assignment_spec,
            "rubric": rubric,
            "instructor_grading_notes": notes,
            "starter_material": {
                "note": config.get(
                    "starter_file_note",
                    "Starter code is context and should not receive authorship credit.",
                ),
                "file_count": len(starter_files),
                "files": starter_files,
            },
            "validated_reference_implementation": {
                "role": config.get("reference_solution_role"),
                "validation": reference_evidence,
                "file_count": len(reference_files),
                "files": reference_files,
            },
            "supporting_material": {
                "file_count": len(supporting_files),
                "files": supporting_files,
            },
            "objective_evidence": {
                "submission_artifact": artifact_evidence(
                    submission_root, label, attempt
                ),
                "ai_preparation": {
                    "source_file_count": len(student_files),
                    "comments_removed": True,
                    "known_identifiers_redacted": True,
                    "warnings": warnings,
                },
                "student_compilation": local_evidence["student_compilation"],
                "student_execution": local_evidence["student_execution"],
                "output_comparison": local_evidence["output_comparison"],
                "local_execution_security": local_evidence["security"],
            },
            "evaluation_constraints": {
                "advisory_only": True,
                "instructor_determines_final_score": True,
                "comments_are_graded": False,
                "accept_valid_alternative_implementations": True,
                "do_not_grade_by_textual_similarity": True,
                "do_not_award_authorship_credit_for_starter_code": True,
                "do_not_invent_compile_or_run_results": True,
                "missing_evidence_never_causes_deduction": True,
                "use_requires_local_evidence_when_needed": True,
                "sanitization_whitespace_is_not_gradable": True,
                "unchanged_starter_code_is_not_gradable": True,
                "do_not_impose_requirements_from_reference_only": True,
                "avoid_double_penalties": True,
                "cite_student_file_and_line_evidence": True,
            },
            "student_material_file": "ai_safe_student_material.json",
            "response_schema_path": "response_schema.json",
        }

        package_compact = json.dumps(
            package, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        student_compact = json.dumps(
            student_material,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        schema_compact = json.dumps(
            schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        local_evidence_compact = json.dumps(
            local_evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

        validation = {
            "module": MODULE_NUMBER,
            "valid": True,
            "checks": {
                "required_assets_present": True,
                "rubric_totals_valid": True,
                "rubric_ids_unique": True,
                "module_5_manifest_ai_safe": True,
                "student_tree_matches_manifest": True,
                "student_comments_removed": True,
                "known_identifiers_redacted": True,
                "reference_files_present": True,
                "response_schema_generated": True,
                "local_compile_stage_completed": (
                    local_evidence["student_compilation"].get("status")
                    not in {"not_run", "skipped"}
                ),
                "local_execution_explicitly_controlled": True,
            },
            "counts": {
                "student_source_files": len(student_files),
                "starter_files": len(starter_files),
                "reference_files": len(reference_files),
                "supporting_files": len(supporting_files),
                "rubric_criteria": summary["criterion_count"],
                "rubric_items": summary["item_count"],
                "global_rules": summary["global_rule_count"],
            },
            "warnings": warnings,
            "limitations": [
                (
                    "Student execution occurs only when --run-student-code is supplied. "
                    "The timeout limits duration but is not a full operating-system sandbox."
                ),
                (
                    "Module 7 performs semantic validation of returned rubric IDs, "
                    "per-item maxima, status/score consistency, filenames, and evidence lines."
                ),
            ],
            "canvas_contacted": False,
            "model_provider_contacted": False,
        }

        manifest_out = {
            "module": MODULE_NUMBER,
            "schema_version": SCHEMA_VERSION,
            "anonymous_label": label,
            "selected_attempt": attempt,
            "assignment_asset_package_id": config.get("asset_package_id"),
            "counts": validation["counts"],
            "files": {
                "grading_package": "grading_package.json",
                "student_material": "ai_safe_student_material.json",
                "response_schema": "response_schema.json",
                "preview": "grading_request_preview.txt",
                "validation_report": "package_validation_report.json",
                "local_evidence": "local_compile_run_evidence.json",
            },
            "sha256": {
                "grading_package": digest(package_compact),
                "student_material": digest(student_compact),
                "response_schema": digest(schema_compact),
                "local_evidence": digest(local_evidence_compact),
            },
            "character_counts": {
                "grading_package": len(package_compact),
                "student_material": len(student_compact),
                "response_schema": len(schema_compact),
                "local_evidence": len(local_evidence_compact),
                "combined_before_prompt": (
                    len(package_compact) + len(student_compact) + len(schema_compact)
                ),
            },
            "canvas_contacted": False,
            "model_provider_contacted": False,
        }

        write_json(staging / "grading_package.json", package)
        write_json(staging / "ai_safe_student_material.json", student_material)
        write_json(staging / "response_schema.json", schema)
        write_json(staging / "local_compile_run_evidence.json", local_evidence)
        write_json(staging / "package_validation_report.json", validation)
        write_json(staging / "grading_request_manifest.json", manifest_out)
        (staging / "grading_request_preview.txt").write_text(
            preview_text(package, student_material, schema), encoding="utf-8"
        )

        preserved_runs = submission_root / ".module_6_preserved_model_runs"
        if preserved_runs.exists():
            shutil.rmtree(preserved_runs)

        if target.exists():
            existing_runs = target / "model_runs"
            if existing_runs.is_dir():
                existing_runs.replace(preserved_runs)
            shutil.rmtree(target)

        staging.replace(target)

        if preserved_runs.is_dir():
            preserved_runs.replace(target / "model_runs")

        print("=" * 78)
        print("MODULE 6 RESULT")
        print("=" * 78)
        print(f"Anonymous label:       {label}")
        print(f"Selected attempt:      {attempt}")
        print(f"Student source files:  {len(student_files)}")
        print(f"Starter files:         {len(starter_files)}")
        print(f"Reference files:       {len(reference_files)}")
        print(f"Supporting files:      {len(supporting_files)}")
        print(
            f"Rubric:                {summary['item_count']} items, "
            f"{summary['maximum_points']:g} points"
        )
        print(f"Warnings:              {len(warnings)}")
        print(
            "Compilation:           "
            f"{local_evidence['student_compilation'].get('status')}"
        )
        print(
            "Execution:             "
            f"{local_evidence['student_execution'].get('status')}"
        )
        print(f"Output directory:      {target}")
        print("\nCreated:")
        for name in [
            "grading_package.json",
            "ai_safe_student_material.json",
            "response_schema.json",
            "local_compile_run_evidence.json",
            "grading_request_preview.txt",
            "package_validation_report.json",
            "grading_request_manifest.json",
        ]:
            print(f"  {target / name}")
        print("\nSafety status:")
        print("  Canvas contacted:          No")
        print("  Model provider contacted:  No")
        print("  Student identity included: No")
        print("  Human review required:     Yes")
        print("\nRESULT: GRADING REQUEST PACKAGE CREATED")
        return 0

    except Exception as error:
        if staging.exists():
            shutil.rmtree(staging)
        print("\nMODULE 6 FAILED")
        print(error)
        print("\nNo Canvas or model request was made.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
