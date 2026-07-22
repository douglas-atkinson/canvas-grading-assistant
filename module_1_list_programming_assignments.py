"""
Module 1: List Programming Assignments from Canvas

This script:
1. Loads Canvas settings from a .env file.
2. Connects to a Canvas course.
3. Finds the assignment group named "Programming Assignment".
4. Lists every assignment in that group.

Required .env file:

CANVAS_URL=https://canvas.tccd.edu
CANVAS_TOKEN=your_canvas_api_token
COURSE_ID=123456
"""

import os

from canvasapi import Canvas
from dotenv import load_dotenv


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

ASSIGNMENT_GROUP_NAME = "Programming Assignment"

load_dotenv()

CANVAS_URL = os.getenv("CANVAS_URL")
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID_STR = os.getenv("COURSE_ID")


# ------------------------------------------------------------
# Validate configuration
# ------------------------------------------------------------

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
# Connect to Canvas
# ------------------------------------------------------------

print(f"Connecting to Canvas: {CANVAS_URL}")

canvas = Canvas(CANVAS_URL, CANVAS_TOKEN)
course = canvas.get_course(COURSE_ID)

print("Connection successful.")
print(f"Course: {course.name}")
print(f"Course ID: {course.id}")


# ------------------------------------------------------------
# Find the Programming Assignment group
# ------------------------------------------------------------

assignment_groups = list(course.get_assignment_groups())
programming_group = None

for group in assignment_groups:
    if group.name.strip().casefold() == ASSIGNMENT_GROUP_NAME.casefold():
        programming_group = group
        break


if programming_group is None:
    print(
        f'\nAssignment group "{ASSIGNMENT_GROUP_NAME}" was not found.'
    )

    print("\nAvailable assignment groups:")
    for group in assignment_groups:
        print(f"  - {group.name}")

else:
    print(
        f'\nAssignment group found: "{programming_group.name}" '
        f"(ID: {programming_group.id})"
    )

    # Get all assignments, then keep only assignments in this group.
    all_assignments = course.get_assignments()

    programming_assignments = []

    for assignment in all_assignments:
        if assignment.assignment_group_id == programming_group.id:
            programming_assignments.append(assignment)

    print(
        f"Number of programming assignments found: "
        f"{len(programming_assignments)}"
    )

    # --------------------------------------------------------
    # Display matching assignments
    # --------------------------------------------------------

    for number, assignment in enumerate(
        programming_assignments,
        start=1,
    ):
        print("\n" + "-" * 70)
        print(f"Assignment {number}")
        print("-" * 70)
        print(f"Name:          {assignment.name}")
        print(f"Assignment ID: {assignment.id}")
        print(f"Points:        {assignment.points_possible}")
        print(f"Due Date:      {assignment.due_at}")
        print(f"Published:     {assignment.published}")
        print(f"Canvas URL:    {assignment.html_url}")

    if programming_assignments:
        print("\n" + "-" * 70)
        print("Finished listing programming assignments.")
