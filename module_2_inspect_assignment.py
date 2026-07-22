"""
Canvas Exploration Module 2
Inspect One Assignment

Purpose
-------
Given a Canvas assignment ID on the command line, this script:

1. Connects to the Canvas course defined in the .env file.
2. Retrieves the assignment and as much assignment-definition data as
   Canvas will return without requesting student submissions or grades.
3. Displays a readable summary.
4. Displays an inventory of all attributes returned by CanvasAPI.
5. Saves the complete assignment data to a JSON file.

Usage
-----
python module_2_inspect_assignment.py <assignment_id>

Example
-------
python module_2_inspect_assignment.py 3900954

Required .env entries
---------------------
CANVAS_URL=https://canvas.tccd.edu
CANVAS_TOKEN=your_canvas_api_token
COURSE_ID=123456
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from canvasapi import Canvas
from dotenv import load_dotenv


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

def display_value(value: Any) -> str:
    """Return a readable version of a Canvas value."""
    if value is None:
        return "Not set"

    if isinstance(value, list):
        if not value:
            return "None"

        return ", ".join(str(item) for item in value)

    if isinstance(value, dict):
        if not value:
            return "None"

        return json.dumps(value, indent=2, default=str)

    return str(value)


def make_json_safe(value: Any) -> Any:
    """
    Convert CanvasAPI values into data that json.dump() can serialize.

    Canvas responses normally contain dictionaries, lists, strings,
    numbers, booleans, and None. This function also safely handles an
    unexpected CanvasAPI object or other non-JSON value.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, list):
        return [make_json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [make_json_safe(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if hasattr(value, "__dict__"):
        return {
            key: make_json_safe(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }

    return str(value)


def get_public_attributes(canvas_object: Any) -> dict[str, Any]:
    """
    Return the public attributes stored on a CanvasAPI object.

    Private CanvasAPI implementation details such as _requester and
    _context are intentionally excluded.
    """
    return {
        key: value
        for key, value in vars(canvas_object).items()
        if not key.startswith("_")
    }


def print_field(
    assignment: Any,
    label: str,
    attribute_name: str,
) -> None:
    """Print one assignment field when it is present."""
    value = getattr(assignment, attribute_name, None)
    print(f"{label:<28} {display_value(value)}")


def print_section(title: str) -> None:
    """Print a visible report section heading."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ------------------------------------------------------------
# Load and validate configuration
# ------------------------------------------------------------

load_dotenv()

CANVAS_URL = os.getenv("CANVAS_URL")
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID_STR = os.getenv("COURSE_ID")

if not all([CANVAS_URL, CANVAS_TOKEN, COURSE_ID_STR]):
    raise ValueError(
        "Missing required environment variables.\n"
        "Make sure your .env file contains:\n"
        "  CANVAS_URL\n"
        "  CANVAS_TOKEN\n"
        "  COURSE_ID"
    )

try:
    COURSE_ID = int(COURSE_ID_STR)
except ValueError as error:
    raise ValueError("COURSE_ID must be a number.") from error


# ------------------------------------------------------------
# Read assignment ID from the command line
# ------------------------------------------------------------

if len(sys.argv) != 2:
    print("Usage:")
    print("  python module_2_inspect_assignment.py <assignment_id>")
    print("\nExample:")
    print("  python module_2_inspect_assignment.py 3900954")
    sys.exit(1)

try:
    ASSIGNMENT_ID = int(sys.argv[1])
except ValueError:
    print("Error: assignment_id must be a number.")
    sys.exit(1)


# ------------------------------------------------------------
# Connect to Canvas and retrieve the assignment
# ------------------------------------------------------------

try:
    print(f"Connecting to Canvas: {CANVAS_URL}")

    canvas = Canvas(CANVAS_URL, CANVAS_TOKEN)
    course = canvas.get_course(COURSE_ID)

    print("Connection successful.")
    print(f"Course: {course.name}")
    print(f"Course ID: {course.id}")
    print(f"Retrieving assignment ID: {ASSIGNMENT_ID}")

    # Ask Canvas for useful assignment-definition information.
    #
    # We deliberately do not request:
    #   submission
    #   observed_users
    #   score_statistics
    #
    # Those fields concern student activity or grading rather than the
    # assignment definition being explored here.
    assignment = course.get_assignment(
        ASSIGNMENT_ID,
        include=[
            "overrides",
            "assignment_visibility",
            "can_edit",
            "peer_review",
        ],
        all_dates=True,
    )

except Exception as error:
    print("\nUnable to retrieve the assignment.")
    print(error)
    print("\nCommon causes:")
    print("  - The assignment ID does not exist in this course.")
    print("  - The Canvas token is invalid or expired.")
    print("  - The account does not have permission to view the assignment.")
    print("  - The Canvas instance does not support one of the optional")
    print("    include values requested by this exploratory script.")
    sys.exit(1)


# ------------------------------------------------------------
# Display a readable assignment summary
# ------------------------------------------------------------

print_section("ASSIGNMENT SUMMARY")

summary_fields = [
    ("Name:", "name"),
    ("Assignment ID:", "id"),
    ("Course ID:", "course_id"),
    ("Assignment Group ID:", "assignment_group_id"),
    ("Position:", "position"),
    ("Points Possible:", "points_possible"),
    ("Grading Type:", "grading_type"),
    ("Published:", "published"),
    ("Due Date:", "due_at"),
    ("Available From:", "unlock_at"),
    ("Available Until:", "lock_at"),
    ("Submission Types:", "submission_types"),
    ("Allowed Extensions:", "allowed_extensions"),
    ("HTML URL:", "html_url"),
    ("Created At:", "created_at"),
    ("Updated At:", "updated_at"),
]

for label, attribute_name in summary_fields:
    print_field(assignment, label, attribute_name)


print_section("ASSIGNMENT BEHAVIOR AND SETTINGS")

settings_fields = [
    ("Peer Reviews Enabled:", "peer_reviews"),
    ("Automatic Peer Reviews:", "automatic_peer_reviews"),
    ("Anonymous Peer Reviews:", "anonymous_peer_reviews"),
    ("Group Category ID:", "group_category_id"),
    ("Grade Group Students Individually:", "grade_group_students_individually"),
    ("Anonymous Grading:", "anonymous_grading"),
    ("Moderated Grading:", "moderated_grading"),
    ("Omit From Final Grade:", "omit_from_final_grade"),
    ("Only Visible to Overrides:", "only_visible_to_overrides"),
    ("Locked for User:", "locked_for_user"),
    ("Can Edit:", "can_edit"),
    ("Quiz ID:", "quiz_id"),
    ("Discussion Topic:", "discussion_topic"),
    ("External Tool Tag:", "external_tool_tag_attributes"),
    ("Turnitin Enabled:", "turnitin_enabled"),
    ("VeriCite Enabled:", "vericite_enabled"),
    ("Post to SIS:", "post_to_sis"),
    ("Integration ID:", "integration_id"),
]

for label, attribute_name in settings_fields:
    print_field(assignment, label, attribute_name)


print_section("RUBRIC INFORMATION")

print_field(assignment, "Rubric Settings:", "rubric_settings")
print_field(assignment, "Rubric Criteria:", "rubric")


print_section("ASSIGNMENT OVERRIDES AND DATE INFORMATION")

print_field(assignment, "Overrides:", "overrides")
print_field(assignment, "All Dates:", "all_dates")
print_field(
    assignment,
    "Assignment Visibility:",
    "assignment_visibility",
)


print_section("DESCRIPTION / INSTRUCTIONS")

description = getattr(assignment, "description", None)

if description:
    print(description)
else:
    print("No description was returned.")


# ------------------------------------------------------------
# Inventory every public attribute returned by CanvasAPI
# ------------------------------------------------------------

attributes = get_public_attributes(assignment)

print_section("ATTRIBUTE INVENTORY")

print(f"CanvasAPI returned {len(attributes)} public attributes.\n")

for number, attribute_name in enumerate(
    sorted(attributes.keys()),
    start=1,
):
    value = attributes[attribute_name]
    value_type = type(value).__name__

    print(
        f"{number:>3}. "
        f"{attribute_name:<40} "
        f"({value_type})"
    )


# ------------------------------------------------------------
# Save the complete assignment data as JSON
# ------------------------------------------------------------

output_directory = Path("output")
output_directory.mkdir(exist_ok=True)

output_path = output_directory / f"assignment_{ASSIGNMENT_ID}.json"

json_data = {
    "exploration": {
        "module": 2,
        "purpose": "Inspect one Canvas assignment",
        "student_submissions_requested": False,
        "grade_information_requested": False,
    },
    "course": {
        "id": course.id,
        "name": course.name,
    },
    "assignment": make_json_safe(attributes),
}

with output_path.open("w", encoding="utf-8") as json_file:
    json.dump(
        json_data,
        json_file,
        indent=2,
        ensure_ascii=False,
        default=str,
    )


print_section("JSON OUTPUT")

print(f"Complete assignment data saved to:")
print(f"  {output_path.resolve()}")
print(f"\nPublic attributes saved: {len(attributes)}")
print("\nModule 2 exploration complete.")
