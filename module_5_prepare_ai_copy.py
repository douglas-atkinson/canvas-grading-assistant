"""
Canvas Exploration Module 5
Prepare one locally extracted C/C++ submission for human review.

This module:
- reads the private Module 4 extraction manifest,
- reads the private Module 3 submission manifest,
- preserves source filenames and directory structure,
- removes C/C++ comments from a separate AI-candidate copy,
- redacts exact known identifiers that remain outside comments,
- creates private and AI-safe reports plus an outbound preview.

It does not modify the original submission, contact Canvas, call an AI,
compile code, or approve the package automatically.

Usage:
    python module_5_prepare_ai_copy.py \
        <module_4_private_extraction_manifest.json> \
        <module_3_private_submissions.json>

Optional:
    --overwrite    Replace an existing ai_candidate folder.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SUPPORTED_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cxx",
    ".h", ".hh", ".hpp", ".hxx", ".inl",
}
SUPPORTED_FILENAMES = {"makefile", "cmakelists.txt"}
TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252")


@dataclass
class CommentStats:
    line_comments: int = 0
    block_comments: int = 0
    replaced_characters: int = 0
    unterminated_block_comment: bool = False
    unterminated_string: bool = False
    unterminated_character: bool = False
    unterminated_raw_string: bool = False


@dataclass
class FileReport:
    relative_path: str
    encoding: str
    lines_before: int
    lines_after: int
    line_comments_removed: int
    block_comments_removed: int
    identifier_redactions: int
    remaining_identifier_matches: int
    warnings: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a reviewable AI-candidate copy of one C/C++ submission."
    )
    parser.add_argument("module_4_manifest", type=Path)
    parser.add_argument("module_3_private_manifest", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as input_file:
        value = json.load(input_file)

    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")

    return value


def require_private(manifest: dict[str, Any], label: str) -> None:
    privacy = manifest.get("privacy")
    if not isinstance(privacy, dict) or privacy.get("send_to_ai") is not False:
        raise ValueError(f"{label} is not explicitly marked send_to_ai=false.")


def find_submission(
    manifest: dict[str, Any], anonymous_label: str
) -> dict[str, Any]:
    submissions = manifest.get("submissions")
    if not isinstance(submissions, list):
        raise ValueError("The Module 3 manifest has no submissions list.")

    matches = [
        item for item in submissions
        if isinstance(item, dict)
        and item.get("anonymous_label") == anonymous_label
    ]

    if len(matches) != 1:
        raise ValueError(
            f"Expected one Module 3 record for {anonymous_label}; found {len(matches)}."
        )

    return matches[0]


def resolve_local_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else (Path.cwd() / path)


def is_supported_source(path: Path) -> bool:
    return (
        path.suffix.lower() in SUPPORTED_EXTENSIONS
        or path.name.lower() in SUPPORTED_FILENAMES
    )


def read_source(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()

    for encoding in TEXT_ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            pass

    raise ValueError(f"Unsupported text encoding: {path}")


def comment_replacement(character: str) -> str:
    return character if character in {"\n", "\r", "\t"} else " "


def find_raw_string_end(text: str, start: int) -> int | None:
    """Return the exclusive end index for R"delimiter(...)delimiter"."""
    if not text.startswith('R"', start):
        return None

    delimiter_start = start + 2
    search_end = min(len(text), delimiter_start + 17)
    open_parenthesis = text.find("(", delimiter_start, search_end)

    if open_parenthesis == -1:
        return None

    delimiter = text[delimiter_start:open_parenthesis]
    if any(ch.isspace() or ch in {"\\", "(", ")"} for ch in delimiter):
        return None

    close_marker = ")" + delimiter + '"'
    close_index = text.find(close_marker, open_parenthesis + 1)
    if close_index == -1:
        return -1

    return close_index + len(close_marker)


def strip_cpp_comments(source: str) -> tuple[str, CommentStats]:
    """Remove C/C++ comments while preserving strings, chars, and line count."""
    NORMAL = "normal"
    LINE = "line"
    BLOCK = "block"
    STRING = "string"
    CHARACTER = "character"

    state = NORMAL
    output: list[str] = []
    stats = CommentStats()
    index = 0

    while index < len(source):
        current = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""

        if state == NORMAL:
            if current == "/" and next_char == "/":
                output.extend((" ", " "))
                stats.line_comments += 1
                stats.replaced_characters += 2
                state = LINE
                index += 2
                continue

            if current == "/" and next_char == "*":
                output.extend((" ", " "))
                stats.block_comments += 1
                stats.replaced_characters += 2
                state = BLOCK
                index += 2
                continue

            if source.startswith('R"', index):
                raw_end = find_raw_string_end(source, index)
                if raw_end == -1:
                    output.append(source[index:])
                    stats.unterminated_raw_string = True
                    index = len(source)
                    continue
                if raw_end is not None:
                    output.append(source[index:raw_end])
                    index = raw_end
                    continue

            if current == '"':
                output.append(current)
                state = STRING
                index += 1
                continue

            if current == "'":
                output.append(current)
                state = CHARACTER
                index += 1
                continue

            output.append(current)
            index += 1
            continue

        if state == LINE:
            output.append(comment_replacement(current))
            if current in {"\n", "\r"}:
                state = NORMAL
            else:
                stats.replaced_characters += 1
            index += 1
            continue

        if state == BLOCK:
            if current == "*" and next_char == "/":
                output.extend((" ", " "))
                stats.replaced_characters += 2
                state = NORMAL
                index += 2
                continue

            output.append(comment_replacement(current))
            stats.replaced_characters += 1
            index += 1
            continue

        if state == STRING:
            output.append(current)
            if current == "\\" and index + 1 < len(source):
                output.append(source[index + 1])
                index += 2
                continue
            if current == '"':
                state = NORMAL
            index += 1
            continue

        if state == CHARACTER:
            output.append(current)
            if current == "\\" and index + 1 < len(source):
                output.append(source[index + 1])
                index += 2
                continue
            if current == "'":
                state = NORMAL
            index += 1
            continue

    if state == BLOCK:
        stats.unterminated_block_comment = True
    elif state == STRING:
        stats.unterminated_string = True
    elif state == CHARACTER:
        stats.unterminated_character = True

    return "".join(output), stats


def derive_identifiers(
    submission: dict[str, Any], module_4: dict[str, Any]
) -> list[tuple[str, str]]:
    """Build conservative exact identifiers; never use first/last name alone."""
    candidates: list[tuple[str, str]] = []
    name = submission.get("student_name")

    if isinstance(name, str) and name.strip() and name != "Not returned":
        cleaned = name.strip()
        candidates.append(("student_name", cleaned))
        candidates.append(("student_name_no_comma", " ".join(cleaned.replace(",", " ").split())))

        if "," in cleaned:
            last, rest = cleaned.split(",", 1)
            natural = f"{rest.strip()} {last.strip()}".strip()
            if natural:
                candidates.append(("student_name_natural", natural))

    user_id = submission.get("canvas_user_id")
    if isinstance(user_id, int):
        candidates.append(("canvas_user_id", str(user_id)))

    selection = module_4.get("selection", {})
    if isinstance(selection, dict):
        original_zip = selection.get("original_zip_filename")
        if isinstance(original_zip, str):
            stem = Path(original_zip).stem.strip()
            if len(stem) >= 6:
                candidates.append(("original_zip_stem", stem))

    unique: dict[str, tuple[str, str]] = {}
    for category, value in candidates:
        if value:
            unique.setdefault(value.casefold(), (category, value))

    return list(unique.values())


def replacement(category: str) -> str:
    if "name" in category:
        return "[STUDENT NAME REDACTED]"
    if "user_id" in category:
        return "[STUDENT IDENTIFIER REDACTED]"
    if "zip" in category:
        return "[SUBMISSION NAME REDACTED]"
    return "[IDENTIFIER REDACTED]"


def redact_identifiers(
    text: str, identifiers: list[tuple[str, str]]
) -> tuple[str, int]:
    result = text
    total = 0

    for category, value in identifiers:
        result, count = re.subn(
            re.escape(value),
            replacement(category),
            result,
            flags=re.IGNORECASE,
        )
        total += count

    return result, total


def count_remaining(
    text: str, identifiers: list[tuple[str, str]]
) -> int:
    return sum(
        len(re.findall(re.escape(value), text, flags=re.IGNORECASE))
        for _, value in identifiers
    )


def path_warnings(
    relative_path: Path, identifiers: list[tuple[str, str]]
) -> list[str]:
    path_text = str(relative_path).casefold()
    warnings = []

    for category, value in identifiers:
        if value.casefold() in path_text:
            warnings.append(
                f"Known identifier category '{category}' appears in the path."
            )

    return warnings


def line_count(text: str) -> int:
    return 0 if not text else text.count("\n") + 1


def write_preview(
    preview_path: Path,
    anonymous_label: str,
    candidate_root: Path,
    candidate_files: list[Path],
    warnings: list[str],
) -> None:
    parts = [
        "Canvas Exploration Module 5 - Outbound Preview",
        "",
        f"Anonymous label: {anonymous_label}",
        "",
        "This is an AI-candidate preview only.",
        "No Canvas or AI request has been made.",
        "",
    ]

    if warnings:
        parts.append("PACKAGE WARNINGS:")
        parts.extend(f"- {warning}" for warning in warnings)
        parts.append("")

    for file_path in candidate_files:
        relative = file_path.relative_to(candidate_root)
        parts.extend([
            "=" * 78,
            f"FILE: {relative}",
            "=" * 78,
            file_path.read_text(encoding="utf-8"),
            "",
        ])

    preview_path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    args = parse_args()

    try:
        module_4 = load_json(args.module_4_manifest)
        module_3 = load_json(args.module_3_private_manifest)
        require_private(module_4, "Module 4 manifest")
        require_private(module_3, "Module 3 manifest")

        selection = module_4.get("selection")
        if not isinstance(selection, dict):
            raise ValueError("The Module 4 manifest has no selection section.")

        anonymous_label = selection.get("anonymous_label")
        if not isinstance(anonymous_label, str):
            raise ValueError("The Module 4 manifest has no anonymous label.")

        submission = find_submission(module_3, anonymous_label)
        module_4_canvas = module_4.get("canvas", {})
        if submission.get("canvas_user_id") != module_4_canvas.get("canvas_user_id"):
            raise ValueError("Module 3 and Module 4 Canvas user IDs do not match.")

        local_files = module_4.get("local_files")
        if not isinstance(local_files, dict):
            raise ValueError("The Module 4 manifest has no local_files section.")

        extraction_text = local_files.get("extraction_root")
        if not isinstance(extraction_text, str):
            raise ValueError("The Module 4 manifest has no extraction_root.")

        extraction_root = resolve_local_path(extraction_text).resolve()
        if not extraction_root.is_dir():
            raise FileNotFoundError(f"Extraction directory not found: {extraction_root}")

        submission_root = args.module_4_manifest.resolve().parent
        candidate_root = submission_root / "ai_candidate"
        private_report_path = submission_root / "module_5_private_sanitization_report.json"
        safe_manifest_path = submission_root / "module_5_ai_package_manifest.json"
        preview_path = submission_root / "module_5_outbound_preview.txt"

        if candidate_root.exists():
            if not args.overwrite:
                raise FileExistsError(
                    f"AI-candidate folder already exists: {candidate_root}\n"
                    "Use --overwrite to replace it."
                )
            shutil.rmtree(candidate_root)

        candidate_root.mkdir(parents=True)
        identifiers = derive_identifiers(submission, module_4)

        all_files = sorted(path for path in extraction_root.rglob("*") if path.is_file())
        source_files = [path for path in all_files if is_supported_source(path)]
        omitted_files = [path for path in all_files if not is_supported_source(path)]

        if not source_files:
            raise ValueError("No supported C/C++ source files were found.")

        reports: list[FileReport] = []
        candidate_files: list[Path] = []
        package_warnings: list[str] = []
        total_comments = 0
        total_redactions = 0
        total_remaining = 0

        for source_file in source_files:
            relative = source_file.relative_to(extraction_root)
            destination = candidate_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)

            original_text, encoding = read_source(source_file)
            comment_free, stats = strip_cpp_comments(original_text)
            sanitized, redactions = redact_identifiers(comment_free, identifiers)
            remaining = count_remaining(sanitized, identifiers)

            warnings = path_warnings(relative, identifiers)
            if stats.unterminated_block_comment:
                warnings.append("Unterminated block comment detected.")
            if stats.unterminated_string:
                warnings.append("Unterminated string literal detected.")
            if stats.unterminated_character:
                warnings.append("Unterminated character literal detected.")
            if stats.unterminated_raw_string:
                warnings.append("Unterminated raw string literal detected.")
            if line_count(original_text) != line_count(sanitized):
                warnings.append("Line count changed unexpectedly.")
            if remaining:
                warnings.append("Known identifier remained after redaction.")

            destination.write_text(sanitized, encoding="utf-8", newline="")
            candidate_files.append(destination)

            total_comments += stats.line_comments + stats.block_comments
            total_redactions += redactions
            total_remaining += remaining

            reports.append(FileReport(
                relative_path=str(relative),
                encoding=encoding,
                lines_before=line_count(original_text),
                lines_after=line_count(sanitized),
                line_comments_removed=stats.line_comments,
                block_comments_removed=stats.block_comments,
                identifier_redactions=redactions,
                remaining_identifier_matches=remaining,
                warnings=warnings,
            ))

            package_warnings.extend(f"{relative}: {warning}" for warning in warnings)

        if omitted_files:
            package_warnings.append(
                f"{len(omitted_files)} unsupported file(s) were omitted from the AI-candidate package."
            )

        private_report = {
            "privacy": {
                "classification": "PRIVATE - FERPA-protected",
                "send_to_ai": False,
                "contains_canvas_user_id": True,
                "contains_student_name": True,
            },
            "selection": {
                "anonymous_label": anonymous_label,
                "canvas_user_id": submission.get("canvas_user_id"),
                "student_name": submission.get("student_name"),
                "selected_attempt": selection.get("selected_attempt"),
            },
            "processing": {
                "source_root": str(extraction_root),
                "candidate_root": str(candidate_root),
                "source_file_count": len(source_files),
                "omitted_file_count": len(omitted_files),
                "comments_removed": total_comments,
                "identifier_redactions": total_redactions,
                "remaining_identifier_matches": total_remaining,
                "known_identifier_categories": [category for category, _ in identifiers],
            },
            "files": [asdict(report) for report in reports],
            "omitted_files": [str(path.relative_to(extraction_root)) for path in omitted_files],
            "warnings": package_warnings,
            "approval": {
                "approved_for_ai": False,
                "human_review_required": True,
            },
        }

        safe_manifest = {
            "privacy": {
                "classification": "AI-candidate package metadata",
                "contains_canvas_user_id": False,
                "contains_student_name": False,
                "contains_original_zip_filename": False,
                "contains_download_urls": False,
            },
            "submission": {
                "anonymous_label": anonymous_label,
                "selected_attempt": selection.get("selected_attempt"),
            },
            "package": {
                "candidate_root": str(candidate_root),
                "source_file_count": len(source_files),
                "comments_removed": True,
                "known_identifiers_redacted": True,
                "human_review_required": True,
                "approved_for_ai": False,
                "files": [report.relative_path for report in reports],
            },
            "warnings": package_warnings,
        }

        private_report_path.write_text(
            json.dumps(private_report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        safe_manifest_path.write_text(
            json.dumps(safe_manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        write_preview(
            preview_path,
            anonymous_label,
            candidate_root,
            candidate_files,
            package_warnings,
        )

        print("=" * 78)
        print("MODULE 5 RESULT")
        print("=" * 78)
        print(f"Anonymous label: {anonymous_label}")
        print(f"Source files processed: {len(source_files)}")
        print(f"Unsupported files omitted: {len(omitted_files)}")
        print(f"Comments removed: {total_comments}")
        print(f"Exact identifier redactions: {total_redactions}")
        print(f"Remaining exact identifier matches: {total_remaining}")
        print(f"Warnings: {len(package_warnings)}")

        print("\nAI-candidate folder:")
        print(f"  {candidate_root}")
        print("\nPrivate sanitization report:")
        print(f"  {private_report_path}")
        print("\nAI-safe package manifest:")
        print(f"  {safe_manifest_path}")
        print("\nOutbound preview:")
        print(f"  {preview_path}")

        print("\nSafety status:")
        print("  Original files modified: No")
        print("  Filenames preserved: Yes")
        print("  Directory structure preserved: Yes")
        print("  Canvas contacted: No")
        print("  AI contacted: No")
        print("  Human review required: Yes")
        print("  Approved for AI: No")

        if total_remaining:
            print("\nRESULT: REVIEW REQUIRED")
            sys.exit(2)

        if package_warnings:
            print("\nRESULT: CREATED WITH WARNINGS")
        else:
            print("\nRESULT: AI CANDIDATE CREATED")

        print("Review the outbound preview before any future API call.")

    except Exception as error:
        print("\nMODULE 5 FAILED")
        print(error)
        print("\nNo Canvas or AI request was made.")
        sys.exit(1)


if __name__ == "__main__":
    main()
