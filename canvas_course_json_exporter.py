"""
Canvas Course JSON Exporter

This script:
1. Connects to Canvas using credentials stored in a .env file
2. Retrieves a course
3. Exports course content and metadata to a formatted JSON file

Exported content includes:
- Course metadata
- Modules and module items
- Pages, including page bodies
- Assignments
- Discussion topics
- Classic quizzes and quiz questions
- New Quizzes, when available
- File metadata and download URLs
- Course tabs and settings

Important:
- This script is read-only. It does not modify the Canvas course.
- File metadata is exported, but the actual files are not downloaded.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from canvasapi import Canvas
from dotenv import load_dotenv


# ============================================================
# Configuration
# ============================================================

load_dotenv()

CANVAS_URL = os.getenv("CANVAS_URL")
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID_STR = os.getenv("COURSE_ID")

OUTPUT_DIRECTORY = Path("canvas_exports")


# ============================================================
# Helper functions
# ============================================================

def validate_configuration() -> int:
    """
    Validate the required environment variables and return
    COURSE_ID as an integer.
    """
    if not all([CANVAS_URL, CANVAS_TOKEN, COURSE_ID_STR]):
        raise ValueError(
            "Missing required environment variables!\n"
            "Please ensure your .env file has:\n"
            "  - CANVAS_URL (for example: "
            "https://your-institution.instructure.com)\n"
            "  - CANVAS_TOKEN (your Canvas API token)\n"
            "  - COURSE_ID (the numeric Canvas course ID)"
        )

    try:
        return int(COURSE_ID_STR)
    except ValueError as error:
        raise ValueError(
            f"COURSE_ID must be a number, but got: {COURSE_ID_STR}\n"
            "Please check your .env file and use only digits."
        ) from error


def make_json_safe(value: Any) -> Any:
    """
    Recursively convert CanvasAPI objects and other Python values
    into data that json.dump() can serialize.

    CanvasAPI objects store their API response fields as object
    attributes. Internal/private attributes such as _requester are
    excluded because they are not course data and are not JSON-safe.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
            if not str(key).startswith("_")
        }

    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]

    if hasattr(value, "__dict__"):
        return {
            key: make_json_safe(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }

    # Last-resort conversion for uncommon CanvasAPI values.
    return str(value)


def sanitize_filename(name: str) -> str:
    """
    Create a Windows-safe filename from a course name.
    """
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", name)
    cleaned = re.sub(r"\s+", "_", cleaned.strip())
    cleaned = cleaned.strip("._")

    return cleaned or "canvas_course"


def export_section(
    section_name: str,
    export_function: Callable[[], Any],
    errors: list[dict[str, str]]
) -> Any:
    """
    Run one export operation without allowing a failure in that
    section to stop the entire course export.
    """
    print(f"   Exporting {section_name}...")

    try:
        result = export_function()
        print(f"   ✅ {section_name} exported")
        return result
    except Exception as error:
        message = str(error)
        print(f"   ⚠️ Could not export {section_name}: {message}")

        errors.append(
            {
                "section": section_name,
                "error": message
            }
        )

        return []


def export_modules(course: Any) -> list[dict[str, Any]]:
    """
    Export modules and the items contained in each module.
    """
    exported_modules = []

    for module in course.get_modules():
        module_data = make_json_safe(module)

        try:
            module_data["items"] = [
                make_json_safe(item)
                for item in module.get_module_items()
            ]
        except Exception as error:
            module_data["items"] = []
            module_data["items_export_error"] = str(error)

        exported_modules.append(module_data)

    return exported_modules


def export_pages(course: Any) -> list[dict[str, Any]]:
    """
    Export every course page.

    Canvas may return only summary information when pages are listed,
    so each page is retrieved individually to capture its body.
    """
    exported_pages = []

    for page_summary in course.get_pages():
        page_identifier = getattr(page_summary, "url", None)

        if page_identifier is None:
            exported_pages.append(make_json_safe(page_summary))
            continue

        try:
            full_page = course.get_page(page_identifier)
            exported_pages.append(make_json_safe(full_page))
        except Exception as error:
            page_data = make_json_safe(page_summary)
            page_data["full_page_export_error"] = str(error)
            exported_pages.append(page_data)

    return exported_pages


def export_assignments(course: Any) -> list[dict[str, Any]]:
    """
    Export assignments and their available metadata.
    Student submissions are intentionally not exported.
    """
    return [
        make_json_safe(assignment)
        for assignment in course.get_assignments()
    ]


def export_discussions(course: Any) -> list[dict[str, Any]]:
    """
    Export discussion-topic definitions.

    Student discussion replies are intentionally not exported.
    """
    return [
        make_json_safe(topic)
        for topic in course.get_discussion_topics()
    ]


def export_classic_quizzes(course: Any) -> list[dict[str, Any]]:
    """
    Export classic quizzes and, when permitted, their questions.
    """
    exported_quizzes = []

    for quiz in course.get_quizzes():
        quiz_data = make_json_safe(quiz)

        try:
            quiz_data["questions"] = [
                make_json_safe(question)
                for question in quiz.get_questions()
            ]
        except Exception as error:
            quiz_data["questions"] = []
            quiz_data["questions_export_error"] = str(error)

        exported_quizzes.append(quiz_data)

    return exported_quizzes


def export_new_quizzes(course: Any) -> list[dict[str, Any]]:
    """
    Export New Quiz metadata when the installed CanvasAPI version
    and the institution's Canvas configuration support it.
    """
    if not hasattr(course, "get_new_quizzes"):
        raise RuntimeError(
            "This CanvasAPI version does not provide get_new_quizzes()."
        )

    return [
        make_json_safe(quiz)
        for quiz in course.get_new_quizzes()
    ]


def export_files(course: Any) -> list[dict[str, Any]]:
    """
    Export Canvas file metadata and URLs.

    This does not download the actual file contents.
    """
    return [
        make_json_safe(file)
        for file in course.get_files()
    ]


def export_tabs(course: Any) -> list[dict[str, Any]]:
    """
    Export course navigation tabs.
    """
    return [
        make_json_safe(tab)
        for tab in course.get_tabs()
    ]


def export_settings(course: Any) -> Any:
    """
    Export course settings.
    """
    return make_json_safe(course.get_settings())


# ============================================================
# Main program
# ============================================================

def main() -> None:
    course_id = validate_configuration()

    print(f"\n🔗 Connecting to Canvas: {CANVAS_URL}")

    try:
        canvas = Canvas(CANVAS_URL, CANVAS_TOKEN)
    except Exception as error:
        print(f"❌ Failed to initialize Canvas connection: {error}")
        print(
            "   Check that CANVAS_URL and CANVAS_TOKEN are correct "
            "in your .env file."
        )
        raise

    try:
        print(f"📚 Fetching course {course_id}...")
        course = canvas.get_course(course_id)

        course_name = getattr(course, "name", f"Course_{course_id}")

        print("\n✅ Successfully connected!")
        print(f"   Course Name: {course_name}")
        print(f"   Course ID: {getattr(course, 'id', course_id)}")

        export_errors: list[dict[str, str]] = []

        print("\n📦 Exporting course content...")

        export_data = {
            "export_information": {
                "exported_at_utc": datetime.now(timezone.utc).isoformat(),
                "canvas_url": CANVAS_URL,
                "course_id": course_id,
                "export_format_version": 1,
                "notes": [
                    "This export contains course structure, text, and metadata.",
                    "Actual Canvas files are not embedded in this JSON file.",
                    "Student submissions, grades, enrollments, and discussion "
                    "replies are intentionally excluded."
                ]
            },

            "course": make_json_safe(course),

            "modules": export_section(
                "modules and module items",
                lambda: export_modules(course),
                export_errors
            ),

            "pages": export_section(
                "pages",
                lambda: export_pages(course),
                export_errors
            ),

            "assignments": export_section(
                "assignments",
                lambda: export_assignments(course),
                export_errors
            ),

            "discussions": export_section(
                "discussion topics",
                lambda: export_discussions(course),
                export_errors
            ),

            "classic_quizzes": export_section(
                "classic quizzes",
                lambda: export_classic_quizzes(course),
                export_errors
            ),

            "new_quizzes": export_section(
                "New Quizzes",
                lambda: export_new_quizzes(course),
                export_errors
            ),

            "files": export_section(
                "file metadata",
                lambda: export_files(course),
                export_errors
            ),

            "tabs": export_section(
                "course navigation tabs",
                lambda: export_tabs(course),
                export_errors
            ),

            "settings": export_section(
                "course settings",
                lambda: export_settings(course),
                export_errors
            )
        }

        export_data["export_information"]["errors"] = export_errors

        OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

        safe_course_name = sanitize_filename(course_name)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        output_path = (
            OUTPUT_DIRECTORY
            / f"{safe_course_name}_{course_id}_{timestamp}.json"
        )

        with output_path.open("w", encoding="utf-8") as output_file:
            json.dump(
                export_data,
                output_file,
                indent=2,
                ensure_ascii=False
            )

        print("\n🎉 Course export complete!")
        print(f"   JSON file: {output_path.resolve()}")

        if export_errors:
            print(
                f"   ⚠️ Export completed with "
                f"{len(export_errors)} section warning(s)."
            )
            print(
                "   Review export_information.errors inside the JSON file "
                "for details."
            )
        else:
            print("   All requested sections exported successfully.")

    except Exception as error:
        print("\n❌ Course export failed:")
        print(f"   {error}")
        print("\nCommon issues:")
        print("   - The COURSE_ID is incorrect")
        print("   - The API token has expired")
        print("   - Your account lacks permission to read part of the course")
        print("   - Your institution has disabled a particular API endpoint")
        raise


if __name__ == "__main__":
    main()