"""
Canvas Exploration Module 3
List assignment submissions and attachment metadata.

Usage:
    python module_3_list_submissions.py <assignment_id>
    python module_3_list_submissions.py <assignment_id> --show-names

The script creates:
1. A private manifest containing Canvas user IDs and download information.
2. An AI-safe manifest containing anonymous labels only.

It does not download files, send data to an AI, or modify Canvas.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from canvasapi import Canvas
from dotenv import load_dotenv


def json_safe(value: Any) -> Any:
    """Convert CanvasAPI values into JSON-safe data."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if hasattr(value, "__dict__"):
        return {
            key: json_safe(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return str(value)


def readable_bytes(size: Any) -> str:
    """Return a readable file-size string."""
    if not isinstance(size, (int, float)):
        return "Unknown"

    units = ["B", "KB", "MB", "GB"]
    value = float(size)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024

    return str(size)


def print_section(title: str) -> None:
    """Print a report section heading."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def get_attachments(submission: Any) -> list[dict[str, Any]]:
    """Return attachment dictionaries from a Canvas submission."""
    attachments = getattr(submission, "attachments", None)

    if not attachments:
        return []

    result = []

    for attachment in attachments:
        if isinstance(attachment, dict):
            result.append(attachment)
        elif hasattr(attachment, "__dict__"):
            result.append(
                {
                    key: value
                    for key, value in vars(attachment).items()
                    if not key.startswith("_")
                }
            )

    return result


def get_student_name(submission: Any) -> str:
    """Return the locally included student name, when available."""
    user = getattr(submission, "user", None)

    if not isinstance(user, dict):
        return "Not returned"

    return (
        user.get("sortable_name")
        or user.get("name")
        or user.get("short_name")
        or "Not returned"
    )


def private_attachment_record(
    attachment: dict[str, Any],
) -> dict[str, Any]:
    """Create a private attachment record."""
    return {
        "id": attachment.get("id"),
        "filename": (
            attachment.get("filename")
            or attachment.get("display_name")
        ),
        "display_name": attachment.get("display_name"),
        "content_type": (
            attachment.get("content-type")
            or attachment.get("content_type")
        ),
        "size_bytes": attachment.get("size"),
        "url": attachment.get("url"),
        "download_url": attachment.get("download_url"),
        "created_at": attachment.get("created_at"),
        "updated_at": attachment.get("updated_at"),
    }


def ai_safe_attachment_record(
    attachment: dict[str, Any],
) -> dict[str, Any]:
    """Create an attachment record without Canvas IDs or URLs."""
    filename = (
        attachment.get("filename")
        or attachment.get("display_name")
        or "Unnamed attachment"
    )

    return {
        "filename": filename,
        "content_type": (
            attachment.get("content-type")
            or attachment.get("content_type")
        ),
        "size_bytes": attachment.get("size"),
        "is_zip": filename.lower().endswith(".zip"),
    }


# Load configuration.
load_dotenv()

CANVAS_URL = os.getenv("CANVAS_URL")
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID_STR = os.getenv("COURSE_ID")

if not all([CANVAS_URL, CANVAS_TOKEN, COURSE_ID_STR]):
    raise ValueError(
        "Missing required environment variables.\n"
        "Your .env file must contain CANVAS_URL, CANVAS_TOKEN, and COURSE_ID."
    )

try:
    COURSE_ID = int(COURSE_ID_STR)
except ValueError as error:
    raise ValueError("COURSE_ID must be a number.") from error


# Read command-line arguments.
if len(sys.argv) not in (2, 3):
    print("Usage:")
    print("  python module_3_list_submissions.py <assignment_id>")
    print("  python module_3_list_submissions.py <assignment_id> --show-names")
    sys.exit(1)

try:
    ASSIGNMENT_ID = int(sys.argv[1])
except ValueError:
    print("Error: assignment_id must be a number.")
    sys.exit(1)

SHOW_NAMES = False

if len(sys.argv) == 3:
    if sys.argv[2] != "--show-names":
        print(f"Unknown option: {sys.argv[2]}")
        sys.exit(1)
    SHOW_NAMES = True


# Connect to Canvas.
try:
    print(f"Connecting to Canvas: {CANVAS_URL}")

    canvas = Canvas(CANVAS_URL, CANVAS_TOKEN)
    course = canvas.get_course(COURSE_ID)
    assignment = course.get_assignment(ASSIGNMENT_ID)

    print("Connection successful.")
    print(f"Course: {course.name}")
    print(f"Course ID: {course.id}")
    print(f"Assignment: {assignment.name}")
    print(f"Assignment ID: {assignment.id}")

    # Canvas uses the student user ID as the identifier for the submission
    # endpoint. Including user provides a local name for optional display.
    submissions = list(
    assignment.get_submissions(include=["user"])
)

    print(f"Canvas returned {len(submissions)} existing submissions.")

    for submission in submissions:
        user = getattr(submission, "user", {})
        name = user.get("name", "Unknown") if isinstance(user, dict) else "Unknown"

        print(
            submission.user_id,
            name,
            submission.workflow_state,
            submission.submitted_at,
        )

except Exception as error:
    print("\nUnable to retrieve submissions.")
    print(error)
    print("\nCommon causes:")
    print("  - The assignment ID does not exist in this course.")
    print("  - The Canvas token is invalid or expired.")
    print("  - Your account cannot view student submissions.")
    sys.exit(1)


private_records = []
ai_safe_records = []

print_section("SUBMISSION INVENTORY")

print(f"Submissions returned by Canvas: {len(submissions)}")
print(f"Student names displayed: {SHOW_NAMES}")
print("No student identifiers from this report should be sent to an AI.")

for index, submission in enumerate(submissions, start=1):
    anonymous_label = f"submission_{index:03d}"
    student_pid = getattr(submission, "user_id", None)
    attachments = get_attachments(submission)

    submitted_at = getattr(submission, "submitted_at", None)
    workflow_state = getattr(submission, "workflow_state", None)
    submission_type = getattr(submission, "submission_type", None)
    attempt = getattr(submission, "attempt", None)
    late = getattr(submission, "late", None)
    missing = getattr(submission, "missing", None)
    seconds_late = getattr(submission, "seconds_late", None)

    print("\n" + "-" * 78)
    print(f"Anonymous Label:     {anonymous_label}")
    print(f"Canvas Student PID:  {student_pid}")

    if SHOW_NAMES:
        print(f"Student Name:        {get_student_name(submission)}")

    print(f"Workflow State:      {workflow_state}")
    print(f"Submission Type:     {submission_type}")
    print(f"Submitted At:        {submitted_at}")
    print(f"Attempt:             {attempt}")
    print(f"Late:                {late}")
    print(f"Missing:             {missing}")
    print(f"Seconds Late:        {seconds_late}")
    print(f"Attachment Count:    {len(attachments)}")

    private_attachments = []
    safe_attachments = []

    for attachment_number, attachment in enumerate(attachments, start=1):
        private_attachment = private_attachment_record(attachment)
        safe_attachment = ai_safe_attachment_record(attachment)

        private_attachments.append(private_attachment)
        safe_attachments.append(safe_attachment)

        print(f"\n  Attachment {attachment_number}")
        print(f"    File:           {safe_attachment['filename']}")
        print(f"    Type:           {safe_attachment['content_type']}")
        print(
            f"    Size:           "
            f"{readable_bytes(safe_attachment['size_bytes'])}"
        )
        print(f"    ZIP file:       {safe_attachment['is_zip']}")
        print(f"    Canvas File ID: {private_attachment['id']}")

    if not attachments:
        print("  No uploaded attachments were returned.")

    private_records.append(
        {
            "anonymous_label": anonymous_label,
            "canvas_user_id": student_pid,
            "student_name": get_student_name(submission),
            "assignment_id": getattr(
                submission,
                "assignment_id",
                ASSIGNMENT_ID,
            ),
            "submission_type": submission_type,
            "submitted_at": submitted_at,
            "workflow_state": workflow_state,
            "attempt": attempt,
            "late": late,
            "missing": missing,
            "seconds_late": seconds_late,
            "attachments": private_attachments,
        }
    )

    ai_safe_records.append(
        {
            "anonymous_label": anonymous_label,
            "submission_type": submission_type,
            "submitted_at": submitted_at,
            "workflow_state": workflow_state,
            "attempt": attempt,
            "late": late,
            "missing": missing,
            "attachment_count": len(safe_attachments),
            "attachments": safe_attachments,
        }
    )


# Save separate private and AI-safe manifests.
output_directory = Path("output")
output_directory.mkdir(exist_ok=True)

private_output_path = (
    output_directory
    / f"assignment_{ASSIGNMENT_ID}_private_submissions.json"
)

ai_safe_output_path = (
    output_directory
    / f"assignment_{ASSIGNMENT_ID}_ai_safe_manifest.json"
)

private_manifest = {
    "privacy": {
        "classification": "PRIVATE - FERPA-protected",
        "send_to_ai": False,
        "contains_canvas_user_ids": True,
        "contains_student_names": True,
        "contains_attachment_download_information": True,
    },
    "course": {
        "id": course.id,
        "name": course.name,
    },
    "assignment": {
        "id": assignment.id,
        "name": assignment.name,
    },
    "submissions": json_safe(private_records),
}

ai_safe_manifest = {
    "privacy": {
        "classification": "AI-safe submission metadata",
        "send_to_ai": True,
        "contains_canvas_user_ids": False,
        "contains_student_names": False,
        "contains_attachment_download_information": False,
        "contains_grades": False,
        "contains_comments": False,
    },
    "assignment": {
        "title": assignment.name,
    },
    "submissions": json_safe(ai_safe_records),
}

with private_output_path.open("w", encoding="utf-8") as output_file:
    json.dump(private_manifest, output_file, indent=2, ensure_ascii=False)

with ai_safe_output_path.open("w", encoding="utf-8") as output_file:
    json.dump(ai_safe_manifest, output_file, indent=2, ensure_ascii=False)


print_section("OUTPUT FILES")

print("PRIVATE manifest — keep local and do not send to an AI:")
print(f"  {private_output_path.resolve()}")

print("\nAI-safe metadata manifest:")
print(f"  {ai_safe_output_path.resolve()}")

print("\nImportant:")
print("  Add output/ to .gitignore before committing this project.")
print("  Module 3 did not download files or modify Canvas.")
print("  Module 3 exploration complete.")
