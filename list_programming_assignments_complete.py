"""
List assignments from a Canvas assignment group.

This script:
1. Loads Canvas credentials from a .env file.
2. Connects to a Canvas course.
3. Finds the assignment group named "Programming Assignment".
4. Prints identifying information for every assignment in that group.

Required .env entries:
    CANVAS_URL=https://your-school.instructure.com
    CANVAS_TOKEN=your_canvas_api_token
    COURSE_ID=123456
"""

import os
import sys
from typing import Optional

from canvasapi import Canvas
from canvasapi.assignment import Assignment
from dotenv import load_dotenv


TARGET_GROUP_NAME = "Programming Assignment"


def get_required_environment_variable(name: str) -> str:
    """
    Return a required environment variable.

    Raises:
        ValueError: If the variable is missing or blank.
    """
    value = os.getenv(name)

    if value is None or not value.strip():
        raise ValueError(
            f"Missing required environment variable: {name}\n"
            "Please check your .env file."
        )

    return value.strip()


def load_configuration() -> tuple[str, str, int]:
    """
    Load and validate Canvas configuration from the .env file.

    Returns:
        A tuple containing:
            Canvas URL,
            Canvas API token,
            Canvas course ID.
    """
    load_dotenv()

    canvas_url = get_required_environment_variable("CANVAS_URL")
    canvas_token = get_required_environment_variable("CANVAS_TOKEN")
    course_id_text = get_required_environment_variable("COURSE_ID")

    try:
        course_id = int(course_id_text)
    except ValueError as error:
        raise ValueError(
            f"COURSE_ID must contain only digits, but received: {course_id_text}"
        ) from error

    return canvas_url, canvas_token, course_id


def find_assignment_group(
    assignment_groups,
    target_name: str,
):
    """
    Find an assignment group by name.

    Matching is case-insensitive and ignores surrounding whitespace.
    """
    normalized_target = target_name.strip().casefold()

    for group in assignment_groups:
        if group.name.strip().casefold() == normalized_target:
            return group

    return None


def format_canvas_date(value: Optional[str]) -> str:
    """
    Convert a Canvas date value into display text.

    Canvas returns ISO 8601 strings or None.
    """
    return value if value else "Not set"


def format_submission_types(assignment: Assignment) -> str:
    """
    Return submission types as a readable comma-separated string.
    """
    submission_types = getattr(assignment, "submission_types", None)

    if not submission_types:
        return "Not specified"

    return ", ".join(submission_types)


def display_assignment(assignment, number: int) -> None:
    """
    Display identifying information for one assignment.
    """
    print("-" * 78)
    print(f"Assignment {number}")
    print("-" * 78)
    print(f"Name:             {assignment.name}")
    print(f"Assignment ID:    {assignment.id}")
    print(f"Points Possible:  {getattr(assignment, 'points_possible', 'Not set')}")
    print(f"Due Date:         {format_canvas_date(getattr(assignment, 'due_at', None))}")
    print(f"Available From:   {format_canvas_date(getattr(assignment, 'unlock_at', None))}")
    print(f"Available Until:  {format_canvas_date(getattr(assignment, 'lock_at', None))}")
    print(f"Published:        {getattr(assignment, 'published', 'Unknown')}")
    print(f"Submission Types: {format_submission_types(assignment)}")
    print(f"Canvas URL:       {getattr(assignment, 'html_url', 'Not available')}")


def main() -> None:
    """
    Connect to Canvas and list assignments in the target assignment group.
    """
    try:
        canvas_url, canvas_token, course_id = load_configuration()

        print(f"Connecting to Canvas at: {canvas_url}")
        canvas = Canvas(canvas_url, canvas_token)

        print(f"Retrieving course ID: {course_id}")
        course = canvas.get_course(course_id)

        print("\nConnection successful.")
        print(f"Course Name: {course.name}")
        print(f"Course ID:   {course.id}")

        assignment_groups = list(course.get_assignment_groups())

        target_group = find_assignment_group(
            assignment_groups,
            TARGET_GROUP_NAME,
        )

        if target_group is None:
            print(
                f'\nAssignment group "{TARGET_GROUP_NAME}" was not found.'
            )

            if assignment_groups:
                print("\nAvailable assignment groups:")
                for group in assignment_groups:
                    print(f"  - {group.name} (ID: {group.id})")
            else:
                print("\nNo assignment groups were found in this course.")

            sys.exit(1)

        #assignments = list(
        #    course.get_assignments_for_group(target_group.id)
        #)

        assignments = []
        for assignment in course.get_assignments():
            if assignment.assignment_group_id == group.id:
                assignments.append(assignment)

        print("\nTarget assignment group found.")
        print(f"Group Name: {target_group.name}")
        print(f"Group ID:   {target_group.id}")
        print(f"Assignments Found: {len(assignments)}")

        if not assignments:
            print(
                f'\nThe assignment group "{target_group.name}" contains no assignments.'
            )
            return

        for index, assignment in enumerate(assignments, start=1):
            display_assignment(assignment, index)

        print("-" * 78)
        print(
            f'Finished. Listed {len(assignments)} assignment(s) from '
            f'"{target_group.name}".'
        )

    except ValueError as error:
        print(f"\nConfiguration error:\n{error}")
        sys.exit(1)

    except Exception as error:
        print("\nCanvas API error:")
        print(error)
        print("\nCommon causes:")
        print("  - The Canvas URL is incorrect.")
        print("  - The API token is invalid or expired.")
        print("  - The course ID does not exist.")
        print("  - Your account does not have permission to view the course.")
        sys.exit(1)


if __name__ == "__main__":
    main()
