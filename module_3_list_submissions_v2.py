"""
Canvas Exploration Module 3 - Revised

Modes:
  live       -> active student enrollments only
  historical -> inactive and completed student enrollments only

READ-ONLY: this script does not download files, send data to AI,
or modify Canvas.

Usage:
  python module_3_list_submissions_v2.py <assignment_id> --mode live
  python module_3_list_submissions_v2.py <assignment_id> --mode historical
  python module_3_list_submissions_v2.py <assignment_id> --mode historical --show-names
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from canvasapi import Canvas
from dotenv import load_dotenv


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if hasattr(value, "__dict__"):
        return {
            k: json_safe(v)
            for k, v in vars(value).items()
            if not k.startswith("_")
        }
    return str(value)


def print_section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def readable_bytes(size: Any) -> str:
    if not isinstance(size, (int, float)):
        return "Unknown"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return str(size)


def get_attachments(submission: Any) -> list[dict[str, Any]]:
    attachments = getattr(submission, "attachments", None)
    if not attachments:
        return []

    result = []
    for attachment in attachments:
        if isinstance(attachment, dict):
            result.append(attachment)
        elif hasattr(attachment, "__dict__"):
            result.append({
                k: v
                for k, v in vars(attachment).items()
                if not k.startswith("_")
            })
    return result


def get_name(enrollment: Any) -> str:
    user = getattr(enrollment, "user", None)
    if not isinstance(user, dict):
        return "Not returned"
    return (
        user.get("sortable_name")
        or user.get("name")
        or user.get("short_name")
        or "Not returned"
    )


def private_attachment(attachment: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": attachment.get("id"),
        "filename": attachment.get("filename") or attachment.get("display_name"),
        "display_name": attachment.get("display_name"),
        "content_type": (
            attachment.get("content-type")
            or attachment.get("content_type")
        ),
        "size_bytes": attachment.get("size"),
        "url": attachment.get("url"),
        "download_url": attachment.get("download_url"),
    }


def safe_attachment(attachment: dict[str, Any]) -> dict[str, Any]:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("assignment_id", type=int)
    parser.add_argument(
        "--mode",
        required=True,
        choices=["live", "historical"],
        help="live=active only; historical=inactive/completed only",
    )
    parser.add_argument("--show-names", action="store_true")
    return parser.parse_args()


def states_for_mode(mode: str) -> list[str]:
    return ["active"] if mode == "live" else ["inactive", "completed"]


def get_target_enrollments(course: Any, mode: str) -> list[Any]:
    by_user_id = {}

    for state in states_for_mode(mode):
        enrollments = course.get_enrollments(
            type=["StudentEnrollment"],
            state=[state],
            include=["user"],
        )

        for enrollment in enrollments:
            user_id = getattr(enrollment, "user_id", None)
            if user_id is not None:
                by_user_id[user_id] = enrollment

    return list(by_user_id.values())


def get_bulk_submissions(
    course: Any,
    assignment_id: int,
    student_ids: list[int],
) -> list[Any]:
    if not student_ids:
        return []

    return list(course.get_multiple_submissions(
        student_ids=student_ids,
        assignment_ids=[assignment_id],
        include=["user"],
    ))


def get_single_submission(
    assignment: Any,
    student_id: int,
) -> Any | None:
    try:
        return assignment.get_submission(
            student_id,
            include=["user"],
        )
    except Exception:
        return None


def reconcile(
    course: Any,
    assignment: Any,
    enrollments: list[Any],
) -> tuple[list[Any], list[int]]:
    student_ids = [
        e.user_id
        for e in enrollments
        if getattr(e, "user_id", None) is not None
    ]

    submissions_by_user = {}

    for submission in get_bulk_submissions(
        course,
        assignment.id,
        student_ids,
    ):
        user_id = getattr(submission, "user_id", None)
        if user_id is not None:
            submissions_by_user[user_id] = submission

    missing = [
        user_id
        for user_id in student_ids
        if user_id not in submissions_by_user
    ]

    for user_id in missing:
        submission = get_single_submission(assignment, user_id)
        if submission is not None:
            submissions_by_user[user_id] = submission

    unresolved = [
        user_id
        for user_id in student_ids
        if user_id not in submissions_by_user
    ]

    ordered = [
        submissions_by_user[user_id]
        for user_id in student_ids
        if user_id in submissions_by_user
    ]

    return ordered, unresolved


def main() -> None:
    args = parse_args()
    load_dotenv()

    canvas_url = os.getenv("CANVAS_URL")
    canvas_token = os.getenv("CANVAS_TOKEN")
    course_id_text = os.getenv("COURSE_ID")

    if not all([canvas_url, canvas_token, course_id_text]):
        raise ValueError(
            "The .env file must contain CANVAS_URL, CANVAS_TOKEN, and COURSE_ID."
        )

    try:
        course_id = int(course_id_text)
    except ValueError as error:
        raise ValueError("COURSE_ID must be numeric.") from error

    try:
        print(f"Connecting to Canvas: {canvas_url}")
        canvas = Canvas(canvas_url, canvas_token)
        course = canvas.get_course(course_id)
        assignment = course.get_assignment(args.assignment_id)

        print("Connection successful.")
        print(f"Course: {course.name}")
        print(f"Course ID: {course.id}")
        print(f"Assignment: {assignment.name}")
        print(f"Assignment ID: {assignment.id}")
        print(f"Mode: {args.mode}")

        enrollments = get_target_enrollments(course, args.mode)
        submissions, unresolved = reconcile(
            course,
            assignment,
            enrollments,
        )

    except Exception as error:
        print("\nUnable to retrieve enrollment or submission data.")
        print(error)
        print("\nNo changes were made to Canvas.")
        sys.exit(1)

    enrollment_by_user = {
        e.user_id: e
        for e in enrollments
        if getattr(e, "user_id", None) is not None
    }

    submitted = [
        s for s in submissions
        if (
            getattr(s, "submitted_at", None) is not None
            or bool(get_attachments(s))
        )
    ]
    unsubmitted = [s for s in submissions if s not in submitted]

    print_section("RECONCILIATION SUMMARY")
    print(f"Target states: {', '.join(states_for_mode(args.mode))}")
    print(f"Target student enrollments: {len(enrollments)}")
    print(f"Submission records retrieved: {len(submissions)}")
    print(f"Actually submitted: {len(submitted)}")
    print(f"Unsubmitted: {len(unsubmitted)}")
    print(f"Unresolved records: {len(unresolved)}")

    if unresolved:
        print("\nFAIL-FAST WARNING:")
        print("Some targeted students could not be reconciled.")

    private_records = []
    safe_records = []

    print_section("SUBMITTED WORK")

    if not submitted:
        print("No submitted work was found for this mode.")

    for index, submission in enumerate(submitted, start=1):
        label = f"submission_{index:03d}"
        user_id = getattr(submission, "user_id", None)
        enrollment = enrollment_by_user.get(user_id)
        name = get_name(enrollment) if enrollment else "Not returned"
        attachments = get_attachments(submission)

        print("\n" + "-" * 78)
        print(f"Anonymous Label:     {label}")
        print(f"Canvas Student PID:  {user_id}")

        if args.show_names:
            print(f"Student Name:        {name}")

        print(
            f"Enrollment State:    "
            f"{getattr(enrollment, 'enrollment_state', 'Unknown')}"
        )
        print(
            f"Submission Type:     "
            f"{getattr(submission, 'submission_type', None)}"
        )
        print(
            f"Submitted At:        "
            f"{getattr(submission, 'submitted_at', None)}"
        )
        print(
            f"Attempt:             "
            f"{getattr(submission, 'attempt', None)}"
        )
        print(
            f"Late:                "
            f"{getattr(submission, 'late', None)}"
        )
        print(f"Attachment Count:    {len(attachments)}")

        private_files = []
        safe_files = []

        for number, attachment in enumerate(attachments, start=1):
            private_file = private_attachment(attachment)
            safe_file = safe_attachment(attachment)
            private_files.append(private_file)
            safe_files.append(safe_file)

            print(f"\n  Attachment {number}")
            print(f"    File:           {safe_file['filename']}")
            print(f"    Type:           {safe_file['content_type']}")
            print(
                f"    Size:           "
                f"{readable_bytes(safe_file['size_bytes'])}"
            )
            print(f"    ZIP file:       {safe_file['is_zip']}")
            print(f"    Canvas File ID: {private_file['id']}")

        private_records.append({
            "anonymous_label": label,
            "canvas_user_id": user_id,
            "student_name": name,
            "enrollment_state": getattr(
                enrollment,
                "enrollment_state",
                None,
            ),
            "assignment_id": assignment.id,
            "submission_type": getattr(
                submission,
                "submission_type",
                None,
            ),
            "submitted_at": getattr(
                submission,
                "submitted_at",
                None,
            ),
            "attempt": getattr(submission, "attempt", None),
            "late": getattr(submission, "late", None),
            "missing": getattr(submission, "missing", None),
            "attachments": private_files,
        })

        safe_records.append({
            "anonymous_label": label,
            "submission_type": getattr(
                submission,
                "submission_type",
                None,
            ),
            "submitted_at": getattr(
                submission,
                "submitted_at",
                None,
            ),
            "attempt": getattr(submission, "attempt", None),
            "late": getattr(submission, "late", None),
            "attachment_count": len(safe_files),
            "attachments": safe_files,
        })

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    private_path = output_dir / (
        f"assignment_{assignment.id}_{args.mode}"
        "_private_submissions.json"
    )
    safe_path = output_dir / (
        f"assignment_{assignment.id}_{args.mode}"
        "_ai_safe_manifest.json"
    )

    private_manifest = {
        "privacy": {
            "classification": "PRIVATE - FERPA-protected",
            "send_to_ai": False,
        },
        "retrieval": {
            "mode": args.mode,
            "target_states": states_for_mode(args.mode),
            "target_enrollment_count": len(enrollments),
            "submission_record_count": len(submissions),
            "submitted_count": len(submitted),
            "unsubmitted_count": len(unsubmitted),
            "unresolved_canvas_user_ids": unresolved,
        },
        "course": {"id": course.id, "name": course.name},
        "assignment": {
            "id": assignment.id,
            "name": assignment.name,
        },
        "submissions": json_safe(private_records),
    }

    safe_manifest = {
        "privacy": {
            "classification": "AI-safe submission metadata",
            "send_to_ai": True,
            "contains_canvas_user_ids": False,
            "contains_student_names": False,
            "contains_grades": False,
            "contains_comments": False,
            "contains_download_urls": False,
        },
        "assignment": {"title": assignment.name},
        "submissions": json_safe(safe_records),
    }

    private_path.write_text(
        json.dumps(private_manifest, indent=2),
        encoding="utf-8",
    )
    safe_path.write_text(
        json.dumps(safe_manifest, indent=2),
        encoding="utf-8",
    )

    print_section("OUTPUT FILES")
    print("PRIVATE manifest:")
    print(f"  {private_path.resolve()}")
    print("\nAI-safe manifest:")
    print(f"  {safe_path.resolve()}")

    print("\nSafety status:")
    print("  Canvas operations: GET only")
    print("  Files downloaded: No")
    print("  Grades/comments changed: No")
    print("  Canvas modified: No")

    if unresolved:
        print("\nRESULT: INCOMPLETE")
        sys.exit(2)

    print("\nRESULT: RECONCILED")
    print("Module 3 exploration complete.")


if __name__ == "__main__":
    main()
