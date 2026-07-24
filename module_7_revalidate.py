"""
Revalidate a saved Module 7 run without contacting the provider or Canvas.

Usage:
python module_7_revalidate.py path/to/model_run

By default, writes:
- validation_report.revalidated.json
- run_metadata.revalidated.json

Use --replace-originals to back up and replace validation_report.json and
run_metadata.json in the run directory.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from module_7.validation import validate_structured_response


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Revalidate one saved Module 7 result locally."
    )
    parser.add_argument(
        "run_directory",
        type=Path,
        help="Timestamped Module 7 model-run directory",
    )
    parser.add_argument(
        "--replace-originals",
        action="store_true",
        help=(
            "Back up and replace validation_report.json and "
            "run_metadata.json."
        ),
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as input_file:
        value = json.load(input_file)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def extract_request_material(
    request_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    user_prompt = request_payload.get("user_prompt")
    if not isinstance(user_prompt, str):
        raise ValueError(
            "request_payload.json does not contain user_prompt text."
        )

    pattern = re.compile(
        r"GRADING_PACKAGE_JSON\n(.*?)\n\n"
        r"AI_SAFE_STUDENT_MATERIAL_JSON\n(.*)\Z",
        re.DOTALL,
    )
    match = pattern.search(user_prompt)
    if match is None:
        raise ValueError(
            "Could not extract grading package and student material "
            "from request_payload.json."
        )

    grading_package = json.loads(match.group(1))
    student_material = json.loads(match.group(2))
    if not isinstance(grading_package, dict):
        raise ValueError("Extracted grading package is not a JSON object.")
    if not isinstance(student_material, dict):
        raise ValueError("Extracted student material is not a JSON object.")
    return grading_package, student_material


def load_request_material(
    run_directory: Path,
    request_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = run_directory / "request_manifest.json"
    if manifest_path.is_file():
        manifest = load_json(manifest_path)
        grading_path = manifest.get("grading_package_path")
        student_path = manifest.get("student_material_path")
        if isinstance(grading_path, str) and isinstance(student_path, str):
            grading_file = Path(grading_path)
            student_file = Path(student_path)
            if grading_file.is_file() and student_file.is_file():
                return load_json(grading_file), load_json(student_file)

    # The exact sent request is self-contained, so moved/archived runs remain
    # revalidatable even when the original Module 6 files are unavailable.
    return extract_request_material(request_payload)


def back_up_once(path: Path) -> None:
    if not path.exists():
        return
    backup = path.with_name(
        f"{path.stem}.before_revalidation{path.suffix}"
    )
    if not backup.exists():
        shutil.copy2(path, backup)


def main() -> int:
    args = parse_arguments()
    run_directory = args.run_directory.resolve()

    if not run_directory.is_dir():
        print(f"Run directory not found: {run_directory}")
        return 1

    try:
        request_payload = load_json(
            run_directory / "request_payload.json"
        )
        grading_result = load_json(
            run_directory / "grading_result.json"
        )

        response_schema = request_payload.get("response_schema")
        if not isinstance(response_schema, dict):
            raise ValueError(
                "request_payload.json does not contain response_schema."
            )

        grading_package, student_material = load_request_material(
            run_directory,
            request_payload,
        )

        metadata = request_payload.get("metadata")
        expected_label = (
            metadata.get("anonymous_label")
            if isinstance(metadata, dict)
            else None
        )

        _, validation_report = validate_structured_response(
            output_text=json.dumps(
                grading_result,
                ensure_ascii=False,
            ),
            response_schema=response_schema,
            expected_anonymous_label=expected_label,
            grading_package=grading_package,
            student_material=student_material,
        )

        old_metadata_path = run_directory / "run_metadata.json"
        run_metadata = (
            load_json(old_metadata_path)
            if old_metadata_path.is_file()
            else {}
        )
        run_metadata["structured_response_valid"] = (
            validation_report.get("valid", False)
        )
        run_metadata["revalidated_locally"] = True
        run_metadata["provider_contacted_during_revalidation"] = False
        run_metadata["canvas_contacted_during_revalidation"] = False

        if args.replace_originals:
            validation_path = (
                run_directory / "validation_report.json"
            )
            metadata_path = run_directory / "run_metadata.json"
            back_up_once(validation_path)
            back_up_once(metadata_path)
        else:
            validation_path = (
                run_directory / "validation_report.revalidated.json"
            )
            metadata_path = (
                run_directory / "run_metadata.revalidated.json"
            )

        write_json(validation_path, validation_report)
        write_json(metadata_path, run_metadata)

        print("=" * 78)
        print("MODULE 7 LOCAL REVALIDATION")
        print("=" * 78)
        print(f"Run directory:       {run_directory}")
        print(
            "Structured valid:    "
            f"{validation_report.get('valid', False)}"
        )
        print(f"Validation report:   {validation_path.name}")
        print(f"Run metadata:        {metadata_path.name}")
        print("Provider contacted:  No")
        print("Canvas contacted:    No")

        if validation_report.get("valid", False):
            print("\nRESULT: SAVED RESPONSE IS VALID")
            return 0

        print("\nRESULT: REVIEW STILL REQUIRED")
        for error in validation_report.get("errors", []):
            print(f"- {error.get('type')}: {error.get('message')}")
        return 2

    except Exception as error:
        print("\nMODULE 7 REVALIDATION FAILED")
        print(error)
        print("\nNo provider or Canvas request was made.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
