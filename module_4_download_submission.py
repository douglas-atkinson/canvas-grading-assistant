"""
Canvas Exploration Module 4
Download and safely extract ONE anonymous submission.

Purpose
-------
This script:

1. Reads the PRIVATE manifest created by Module 3.
2. Resolves one anonymous label to its Canvas user ID locally.
3. Retrieves that student's current submission and submission history.
4. Selects the latest valid submitted attempt.
5. Downloads exactly one ZIP attachment.
6. Saves the ZIP under an anonymous local name.
7. Extracts it safely while preserving internal filenames and folders.
8. Creates a private extraction manifest and local file inventory.

This script is READ-ONLY with respect to Canvas. It performs GET requests only.

It does NOT:
- send anything to an AI,
- modify grades,
- post comments,
- rename extracted source files,
- remove comments or PII from source files.

Usage
-----


To replace an existing local working folder:
python module_4_download_submission.py \
    output/assignment_3572383_historical_private_submissions.json \
    submission_001 \
    --overwrite

Required .env entries
---------------------
CANVAS_URL=https://canvas.tccd.edu
CANVAS_TOKEN=your_canvas_api_token
COURSE_ID=123456
"""

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import requests
from canvasapi import Canvas
from dotenv import load_dotenv


# Conservative safety limits for a small programming assignment.
MAX_ARCHIVE_SIZE_BYTES = 100 * 1024 * 1024
MAX_EXTRACTED_SIZE_BYTES = 200 * 1024 * 1024
MAX_SINGLE_FILE_SIZE_BYTES = 50 * 1024 * 1024
MAX_FILE_COUNT = 2000
MAX_COMPRESSION_RATIO = 200


def parse_arguments() -> argparse.Namespace:
    """Read command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Download and safely extract one Canvas submission selected "
            "by its anonymous Module 3 label."
        )
    )
    parser.add_argument(
        "private_manifest",
        type=Path,
        help="Private submissions manifest created by Module 3",
    )
    parser.add_argument(
        "anonymous_label",
        help="Anonymous label such as submission_001",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the existing local working folder for this submission",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk."""
    if not path.is_file():
        raise FileNotFoundError(f"Manifest not found: {path}")

    with path.open("r", encoding="utf-8") as input_file:
        data = json.load(input_file)

    if not isinstance(data, dict):
        raise ValueError("The manifest must contain a JSON object.")

    return data


def find_private_submission(
    manifest: dict[str, Any],
    anonymous_label: str,
) -> dict[str, Any]:
    """Resolve an anonymous label through the private local manifest."""
    submissions = manifest.get("submissions")

    if not isinstance(submissions, list):
        raise ValueError(
            "The private manifest does not contain a submissions list."
        )

    matches = [
        submission
        for submission in submissions
        if (
            isinstance(submission, dict)
            and submission.get("anonymous_label") == anonymous_label
        )
    ]

    if not matches:
        raise ValueError(
            f"Anonymous label not found in the private manifest: "
            f"{anonymous_label}"
        )

    if len(matches) > 1:
        raise ValueError(
            f"Anonymous label appears more than once: {anonymous_label}"
        )

    record = matches[0]

    if record.get("canvas_user_id") is None:
        raise ValueError(
            f"{anonymous_label} does not contain a Canvas user ID."
        )

    return record


def public_attributes(canvas_object: Any) -> dict[str, Any]:
    """Convert a CanvasAPI object into a public attribute dictionary."""
    if isinstance(canvas_object, dict):
        return canvas_object

    if hasattr(canvas_object, "__dict__"):
        return {
            key: value
            for key, value in vars(canvas_object).items()
            if not key.startswith("_")
        }

    raise TypeError("Unexpected Canvas submission object type.")


def normalize_attachments(value: Any) -> list[dict[str, Any]]:
    """Return attachment dictionaries from a submission candidate."""
    if not isinstance(value, list):
        return []

    result: list[dict[str, Any]] = []

    for attachment in value:
        if isinstance(attachment, dict):
            result.append(attachment)
        elif hasattr(attachment, "__dict__"):
            result.append(public_attributes(attachment))

    return result


def submission_candidates(submission: Any) -> list[dict[str, Any]]:
    """Build candidate attempts from the current submission and history."""
    current = public_attributes(submission)
    candidates = [current]

    history = current.get("submission_history")

    if isinstance(history, list):
        for item in history:
            if isinstance(item, dict):
                candidates.append(item)
            elif hasattr(item, "__dict__"):
                candidates.append(public_attributes(item))

    # Deduplicate candidates representing the same attempt and timestamp.
    unique: dict[tuple[Any, Any], dict[str, Any]] = {}

    for candidate in candidates:
        key = (
            candidate.get("attempt"),
            candidate.get("submitted_at"),
        )
        existing = unique.get(key)

        if existing is None:
            unique[key] = candidate
        elif (
            not normalize_attachments(existing.get("attachments"))
            and normalize_attachments(candidate.get("attachments"))
        ):
            unique[key] = candidate

    return list(unique.values())


def select_latest_valid_attempt(submission: Any) -> dict[str, Any]:
    """Select the latest attempt having a submission time and attachment."""
    valid_candidates = []

    for candidate in submission_candidates(submission):
        submitted_at = candidate.get("submitted_at")
        attachments = normalize_attachments(candidate.get("attachments"))

        if submitted_at and attachments:
            valid_candidates.append(candidate)

    if not valid_candidates:
        raise ValueError(
            "Canvas did not return a submitted attempt with attachments."
        )

    def sort_key(candidate: dict[str, Any]) -> tuple[int, str]:
        attempt = candidate.get("attempt")
        numeric_attempt = attempt if isinstance(attempt, int) else -1
        submitted_at = str(candidate.get("submitted_at") or "")
        return numeric_attempt, submitted_at

    return max(valid_candidates, key=sort_key)


def select_single_zip_attachment(
    attempt: dict[str, Any],
) -> dict[str, Any]:
    """Require exactly one ZIP attachment for the selected attempt."""
    attachments = normalize_attachments(attempt.get("attachments"))
    zip_attachments = []

    for attachment in attachments:
        filename = str(
            attachment.get("filename")
            or attachment.get("display_name")
            or ""
        )
        content_type = str(
            attachment.get("content-type")
            or attachment.get("content_type")
            or ""
        ).lower()

        if (
            filename.lower().endswith(".zip")
            or content_type in {
                "application/zip",
                "application/x-zip-compressed",
            }
        ):
            zip_attachments.append(attachment)

    if not zip_attachments:
        raise ValueError(
            "The latest submitted attempt does not contain a ZIP attachment."
        )

    if len(zip_attachments) > 1:
        names = [
            str(
                item.get("filename")
                or item.get("display_name")
                or "unnamed.zip"
            )
            for item in zip_attachments
        ]
        raise ValueError(
            "The latest attempt contains multiple ZIP attachments. "
            "Module 4 will not guess which one to use: "
            + ", ".join(names)
        )

    return zip_attachments[0]


def resolve_download_url(
    canvas: Canvas,
    attachment: dict[str, Any],
) -> str:
    """Resolve the current Canvas download URL for an attachment."""
    url = attachment.get("url") or attachment.get("download_url")

    if isinstance(url, str) and url.strip():
        return url

    file_id = attachment.get("id")

    if file_id is None:
        raise ValueError(
            "The ZIP attachment has neither a download URL nor a file ID."
        )

    canvas_file = canvas.get_file(file_id)
    url = getattr(canvas_file, "url", None)

    if not isinstance(url, str) or not url.strip():
        raise ValueError(
            "Canvas did not return a download URL for the attachment."
        )

    return url


def sha256_file(path: Path) -> str:
    """Calculate a file's SHA-256 digest."""
    digest = hashlib.sha256()

    with path.open("rb") as input_file:
        for block in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def download_zip(url: str, token: str, destination: Path) -> None:
    """Download one Canvas attachment using an authenticated GET request."""
    headers = {"Authorization": f"Bearer {token}"}

    with requests.get(
        url,
        headers=headers,
        timeout=(15, 120),
        stream=True,
        allow_redirects=True,
    ) as response:
        response.raise_for_status()

        content_length = response.headers.get("Content-Length")

        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = None

            if (
                declared_size is not None
                and declared_size > MAX_ARCHIVE_SIZE_BYTES
            ):
                raise ValueError(
                    "The ZIP exceeds Module 4's archive-size safety limit."
                )

        bytes_written = 0

        with destination.open("wb") as output_file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue

                bytes_written += len(chunk)

                if bytes_written > MAX_ARCHIVE_SIZE_BYTES:
                    raise ValueError(
                        "The ZIP exceeded Module 4's archive-size "
                        "safety limit during download."
                    )

                output_file.write(chunk)


def safe_member_path(
    extraction_root: Path,
    member_name: str,
) -> Path:
    """Return a safe extraction path or reject path traversal."""
    normalized_name = member_name.replace("\\", "/")
    member_path = PurePosixPath(normalized_name)

    if member_path.is_absolute():
        raise ValueError(f"Unsafe absolute path in ZIP: {member_name}")

    if ".." in member_path.parts:
        raise ValueError(
            f"Unsafe parent-directory path in ZIP: {member_name}"
        )

    if member_path.parts and member_path.parts[0].endswith(":"):
        raise ValueError(
            f"Unsafe drive-qualified path in ZIP: {member_name}"
        )

    target = extraction_root.joinpath(*member_path.parts)
    root_resolved = extraction_root.resolve()
    target_resolved = target.resolve()

    if (
        target_resolved != root_resolved
        and root_resolved not in target_resolved.parents
    ):
        raise ValueError(
            f"ZIP entry escapes extraction directory: {member_name}"
        )

    return target


def is_zip_symlink(info: zipfile.ZipInfo) -> bool:
    """Return True when a ZIP entry represents a symbolic link."""
    unix_mode = info.external_attr >> 16
    return stat.S_ISLNK(unix_mode)


def inspect_archive(
    archive: zipfile.ZipFile,
    extraction_root: Path,
) -> list[dict[str, Any]]:
    """Validate every archive member before extracting anything."""
    infos = archive.infolist()

    if len(infos) > MAX_FILE_COUNT:
        raise ValueError(
            f"The ZIP contains {len(infos)} entries; "
            f"the safety limit is {MAX_FILE_COUNT}."
        )

    total_uncompressed = 0
    inventory = []

    for info in infos:
        if info.flag_bits & 0x1:
            raise ValueError(
                f"Encrypted ZIP entry is not supported: {info.filename}"
            )

        if is_zip_symlink(info):
            raise ValueError(
                f"Symbolic links are not permitted: {info.filename}"
            )

        target = safe_member_path(extraction_root, info.filename)

        if not info.is_dir():
            if info.file_size > MAX_SINGLE_FILE_SIZE_BYTES:
                raise ValueError(
                    f"ZIP entry exceeds the single-file safety limit: "
                    f"{info.filename}"
                )

            total_uncompressed += info.file_size

            if total_uncompressed > MAX_EXTRACTED_SIZE_BYTES:
                raise ValueError(
                    "The ZIP exceeds Module 4's total extracted-size "
                    "safety limit."
                )

            if info.compress_size == 0:
                ratio = float("inf") if info.file_size > 0 else 1.0
            else:
                ratio = info.file_size / info.compress_size

            if (
                info.file_size > 1024 * 1024
                and ratio > MAX_COMPRESSION_RATIO
            ):
                raise ValueError(
                    f"Suspicious compression ratio for ZIP entry: "
                    f"{info.filename}"
                )
        else:
            ratio = None

        inventory.append({
            "archive_name": info.filename,
            "relative_path": str(target.relative_to(extraction_root)),
            "is_directory": info.is_dir(),
            "size_bytes": info.file_size,
            "compressed_size_bytes": info.compress_size,
            "compression_ratio": ratio,
        })

    return inventory


def extract_archive(
    zip_path: Path,
    extraction_root: Path,
) -> list[dict[str, Any]]:
    """Safely extract the ZIP while preserving internal filenames."""
    if not zipfile.is_zipfile(zip_path):
        raise ValueError(
            "The downloaded attachment is not a valid ZIP archive."
        )

    extraction_root.mkdir(parents=True, exist_ok=False)

    with zipfile.ZipFile(zip_path, "r") as archive:
        inventory = inspect_archive(archive, extraction_root)

        for info in archive.infolist():
            target = safe_member_path(extraction_root, info.filename)

            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)

            with archive.open(info, "r") as source:
                with target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)

    inventory_by_path = {
        item["relative_path"]: item
        for item in inventory
    }

    for path in extraction_root.rglob("*"):
        if not path.is_file():
            continue

        relative_path = str(path.relative_to(extraction_root))
        item = inventory_by_path.get(relative_path)

        if item is not None:
            item["sha256"] = sha256_file(path)

    return inventory


def private_output_record(
    manifest: dict[str, Any],
    private_submission: dict[str, Any],
    selected_attempt: dict[str, Any],
    attachment: dict[str, Any],
    zip_path: Path,
    extraction_root: Path,
    inventory: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create Module 4's private local extraction manifest."""
    assignment = manifest.get("assignment", {})
    course = manifest.get("course", {})

    original_filename = (
        attachment.get("filename")
        or attachment.get("display_name")
        or "unknown.zip"
    )

    return {
        "privacy": {
            "classification": "PRIVATE - FERPA-protected",
            "send_to_ai": False,
            "contains_canvas_user_id": True,
            "contains_original_zip_filename": True,
            "source_files_have_not_been_sanitized": True,
        },
        "canvas": {
            "course_id": course.get("id"),
            "assignment_id": assignment.get("id"),
            "canvas_user_id": private_submission.get("canvas_user_id"),
        },
        "selection": {
            "anonymous_label": private_submission.get("anonymous_label"),
            "selected_attempt": selected_attempt.get("attempt"),
            "submitted_at": selected_attempt.get("submitted_at"),
            "submission_type": selected_attempt.get("submission_type"),
            "original_zip_filename": original_filename,
            "canvas_file_id": attachment.get("id"),
        },
        "local_files": {
            "stored_zip": str(zip_path),
            "stored_zip_size_bytes": zip_path.stat().st_size,
            "stored_zip_sha256": sha256_file(zip_path),
            "extraction_root": str(extraction_root),
            "entry_count": len(inventory),
            "files": inventory,
        },
        "safety": {
            "canvas_operations": "GET only",
            "canvas_modified": False,
            "internal_filenames_preserved": True,
            "comments_removed": False,
            "pii_sanitized": False,
            "approved_for_ai": False,
        },
    }


def write_inventory_text(
    path: Path,
    anonymous_label: str,
    selected_attempt: dict[str, Any],
    inventory: list[dict[str, Any]],
) -> None:
    """Write a readable local inventory of extracted files."""
    lines = [
        "Canvas Exploration Module 4 - Local File Inventory",
        "",
        f"Anonymous label: {anonymous_label}",
        f"Selected attempt: {selected_attempt.get('attempt')}",
        f"Submitted at: {selected_attempt.get('submitted_at')}",
        "",
        "This inventory is local and has NOT been approved for AI use.",
        "",
        "Extracted entries:",
    ]

    for item in inventory:
        entry_type = "DIR " if item["is_directory"] else "FILE"
        lines.append(
            f"{entry_type:4}  "
            f"{item['size_bytes']:>10} bytes  "
            f"{item['relative_path']}"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Run the Module 4 exploration."""
    args = parse_arguments()

    try:
        manifest = load_json(args.private_manifest)
        private_submission = find_private_submission(
            manifest,
            args.anonymous_label,
        )

        privacy = manifest.get("privacy", {})

        if privacy.get("send_to_ai") is not False:
            raise ValueError(
                "The supplied manifest is not marked as private."
            )

        assignment_data = manifest.get("assignment", {})
        course_data = manifest.get("course", {})

        assignment_id = assignment_data.get("id")
        manifest_course_id = course_data.get("id")
        canvas_user_id = private_submission.get("canvas_user_id")

        if not isinstance(assignment_id, int):
            raise ValueError(
                "The private manifest has no numeric assignment ID."
            )

        if not isinstance(canvas_user_id, int):
            raise ValueError(
                "The private submission has no numeric Canvas user ID."
            )

        load_dotenv()

        canvas_url = os.getenv("CANVAS_URL")
        canvas_token = os.getenv("CANVAS_TOKEN")
        course_id_text = os.getenv("COURSE_ID")

        if not all([canvas_url, canvas_token, course_id_text]):
            raise ValueError(
                "The .env file must contain CANVAS_URL, "
                "CANVAS_TOKEN, and COURSE_ID."
            )

        try:
            configured_course_id = int(course_id_text)
        except ValueError as error:
            raise ValueError(
                "COURSE_ID in .env must be numeric."
            ) from error

        if (
            manifest_course_id is not None
            and configured_course_id != manifest_course_id
        ):
            raise ValueError(
                "COURSE_ID in .env does not match the private manifest."
            )

        print(f"Connecting to Canvas: {canvas_url}")

        canvas = Canvas(canvas_url, canvas_token)
        course = canvas.get_course(configured_course_id)
        assignment = course.get_assignment(assignment_id)

        print("Connection successful.")
        print(f"Course: {course.name}")
        print(f"Assignment: {assignment.name}")
        print(f"Anonymous label: {args.anonymous_label}")
        print("Resolving the latest valid submitted attempt...")

        submission = assignment.get_submission(
            canvas_user_id,
            include=["submission_history"],
        )

        selected_attempt = select_latest_valid_attempt(submission)
        attachment = select_single_zip_attachment(selected_attempt)
        download_url = resolve_download_url(canvas, attachment)

        print(f"Selected attempt: {selected_attempt.get('attempt')}")
        print(f"Submitted at: {selected_attempt.get('submitted_at')}")

        output_root = (
            Path("output")
            / f"assignment_{assignment_id}"
            / args.anonymous_label
        )

        if output_root.exists():
            if not args.overwrite:
                raise FileExistsError(
                    f"Local working folder already exists: "
                    f"{output_root}\n"
                    f"Use --overwrite to replace it."
                )
            shutil.rmtree(output_root)

        original_directory = output_root / "original"
        extraction_root = output_root / "extracted"
        original_directory.mkdir(parents=True)
        zip_path = original_directory / "submission.zip"

        print("Downloading one ZIP attachment...")
        download_zip(download_url, canvas_token, zip_path)

        print("Validating and extracting ZIP...")
        inventory = extract_archive(zip_path, extraction_root)

        module_4_manifest = private_output_record(
            manifest,
            private_submission,
            selected_attempt,
            attachment,
            zip_path,
            extraction_root,
            inventory,
        )

        manifest_path = (
            output_root
            / "module_4_private_extraction_manifest.json"
        )

        with manifest_path.open("w", encoding="utf-8") as output_file:
            json.dump(
                module_4_manifest,
                output_file,
                indent=2,
                ensure_ascii=False,
            )

        inventory_path = output_root / "local_file_inventory.txt"
        write_inventory_text(
            inventory_path,
            args.anonymous_label,
            selected_attempt,
            inventory,
        )

        file_count = sum(
            1 for item in inventory if not item["is_directory"]
        )
        directory_count = sum(
            1 for item in inventory if item["is_directory"]
        )

        print("\n" + "=" * 78)
        print("MODULE 4 RESULT")
        print("=" * 78)
        print("RESULT: SUCCESS")
        print(f"ZIP stored as: {zip_path.resolve()}")
        print(f"Extracted files: {file_count}")
        print(f"Extracted directories: {directory_count}")
        print(
            f"Private extraction manifest: "
            f"{manifest_path.resolve()}"
        )
        print(f"Local file inventory: {inventory_path.resolve()}")

        print("\nSafety status:")
        print("  Canvas operations: GET only")
        print("  Canvas modified: No")
        print("  One submission processed: Yes")
        print("  Latest valid attempt selected: Yes")
        print("  Internal filenames preserved: Yes")
        print("  Sent to AI: No")
        print("  PII sanitization performed: No")
        print("  AI-ready: No")

    except Exception as error:
        print("\nMODULE 4 FAILED")
        print(error)
        print("\nNo grades or comments were changed in Canvas.")
        sys.exit(1)


if __name__ == "__main__":
    main()
