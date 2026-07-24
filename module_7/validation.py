"""Validate one structured grading response."""

from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator


LOCAL_EVIDENCE_FILE = "local_compile_run_evidence.json"
VIRTUAL_PACKAGE_DOCUMENTS = {
    LOCAL_EVIDENCE_FILE,
    "ai_safe_student_material.json",
    "grading_package.json",
}


def find_first_key(value: Any, target_key: str) -> Any | None:
    """Recursively return the first value for a key."""
    if isinstance(value, dict):
        if target_key in value:
            return value[target_key]
        for child in value.values():
            found = find_first_key(child, target_key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_first_key(child, target_key)
            if found is not None:
                return found
    return None


def rubric_maps(
    grading_package: dict[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    """Return expected rubric-item metadata and global-rule IDs."""
    items: dict[str, dict[str, Any]] = {}
    rules: set[str] = set()
    if not isinstance(grading_package, dict):
        return items, rules

    rubric = grading_package.get("rubric")
    if not isinstance(rubric, dict):
        return items, rules

    for criterion in rubric.get("criteria", []):
        if not isinstance(criterion, dict):
            continue
        criterion_id = criterion.get("id")
        for item in criterion.get("items", []):
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            if isinstance(item_id, str):
                items[item_id] = {
                    "criterion_id": criterion_id,
                    "maximum_points": item.get("maximum_points"),
                }

    for rule in rubric.get("global_rules", []):
        if isinstance(rule, dict) and isinstance(rule.get("id"), str):
            rules.add(rule["id"])

    return items, rules


def student_file_lines(
    student_material: dict[str, Any] | None,
) -> dict[str, int]:
    """Map AI-safe student relative paths to line counts."""
    result: dict[str, int] = {}
    if not isinstance(student_material, dict):
        return result

    raw_files = student_material.get("source_files")
    if not isinstance(raw_files, list):
        raw_files = student_material.get("files")
    if not isinstance(raw_files, list):
        return result

    for item in raw_files:
        if not isinstance(item, dict):
            continue
        path = item.get("relative_path")
        count = item.get("line_count")
        if isinstance(path, str) and isinstance(count, int):
            result[path.replace("\\", "/")] = count
    return result


def package_file_lines(
    grading_package: dict[str, Any] | None,
) -> dict[str, int]:
    """Map starter/reference/supporting package files to line counts."""
    result: dict[str, int] = {}
    if not isinstance(grading_package, dict):
        return result

    section_names = (
        "starter_material",
        "validated_reference_implementation",
        "supporting_material",
    )
    for section_name in section_names:
        section = grading_package.get(section_name)
        if not isinstance(section, dict):
            continue

        raw_files = section.get("files")
        if not isinstance(raw_files, list):
            continue

        for item in raw_files:
            if not isinstance(item, dict):
                continue
            path = item.get("relative_path")
            count = item.get("line_count")
            if isinstance(path, str) and isinstance(count, int):
                result[path.replace("\\", "/")] = count

    return result


def resolve_dotted_path(
    root: Any,
    dotted_path: str,
) -> tuple[bool, Any]:
    """Resolve a dot-separated path through dictionaries."""
    current = root
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def text_line_count(value: str) -> int:
    """Return a useful one-based line count for a text evidence value."""
    if value == "":
        return 0
    return len(value.splitlines())


def append_error(
    report: dict[str, Any],
    error_type: str,
    message: str,
    path: str | None = None,
) -> None:
    error: dict[str, Any] = {
        "type": error_type,
        "message": message,
    }
    if path is not None:
        error["path"] = path
    report["errors"].append(error)


def validate_line_range(
    report: dict[str, Any],
    evidence_path: str,
    start: Any,
    end: Any,
    line_count: int,
    description: str,
    require_lines: bool,
) -> None:
    """Validate an optional or required one-based evidence line range."""
    if start is None and end is None:
        if require_lines:
            append_error(
                report,
                "source_evidence_missing_lines",
                f"{description} requires integer line_start and line_end.",
                evidence_path,
            )
        return

    if not isinstance(start, int) or not isinstance(end, int):
        append_error(
            report,
            "invalid_evidence_line_type",
            f"{description} must use two integers or two null values.",
            evidence_path,
        )
        return

    if start > end or start < 1 or end > line_count:
        append_error(
            report,
            "invalid_evidence_line_range",
            f"Line range {start}-{end} is invalid for {line_count} lines.",
            evidence_path,
        )


def validate_evidence_entry(
    report: dict[str, Any],
    evidence_path: str,
    entry: dict[str, Any],
    source_lines: dict[str, int],
    package_lines: dict[str, int],
    grading_package: dict[str, Any] | None,
) -> None:
    """
    Validate one evidence reference.

    Evidence may point to:
    - an AI-safe student source file;
    - a starter/reference/supporting file included in the package;
    - a structured package document;
    - or an existing objective_evidence dotted path.
    """
    filename = entry.get("file")
    start = entry.get("line_start")
    end = entry.get("line_end")

    if not isinstance(filename, str) or not filename.strip():
        append_error(
            report,
            "missing_evidence_file",
            "Evidence must contain a non-empty file/reference name.",
            f"{evidence_path}.file",
        )
        return

    normalized = filename.replace("\\", "/").strip()

    if normalized in source_lines:
        validate_line_range(
            report=report,
            evidence_path=evidence_path,
            start=start,
            end=end,
            line_count=source_lines[normalized],
            description="Student source evidence",
            require_lines=True,
        )
        return

    if normalized in package_lines:
        validate_line_range(
            report=report,
            evidence_path=evidence_path,
            start=start,
            end=end,
            line_count=package_lines[normalized],
            description="Package source evidence",
            require_lines=True,
        )
        return

    if normalized in VIRTUAL_PACKAGE_DOCUMENTS:
        if start is not None or end is not None:
            append_error(
                report,
                "structured_evidence_has_source_lines",
                (
                    f"Structured evidence document {normalized!r} must use "
                    "null line numbers."
                ),
                evidence_path,
            )
        return

    prefix = "objective_evidence"
    if normalized == prefix or normalized.startswith(prefix + "."):
        if not isinstance(grading_package, dict):
            append_error(
                report,
                "objective_evidence_unavailable",
                "The grading package was unavailable for evidence validation.",
                f"{evidence_path}.file",
            )
            return

        objective_root = grading_package.get("objective_evidence")
        relative_path = (
            normalized[len(prefix) + 1 :]
            if normalized.startswith(prefix + ".")
            else ""
        )

        if relative_path:
            exists, value = resolve_dotted_path(
                objective_root,
                relative_path,
            )
        else:
            exists, value = isinstance(objective_root, dict), objective_root

        if not exists:
            append_error(
                report,
                "unknown_objective_evidence",
                f"Evidence references an unknown package path: {filename!r}",
                f"{evidence_path}.file",
            )
            return

        if isinstance(value, str):
            validate_line_range(
                report=report,
                evidence_path=evidence_path,
                start=start,
                end=end,
                line_count=text_line_count(value),
                description=f"Text evidence {normalized!r}",
                require_lines=False,
            )
        elif start is not None or end is not None:
            append_error(
                report,
                "structured_evidence_has_source_lines",
                (
                    f"Structured evidence path {normalized!r} must use "
                    "null line numbers."
                ),
                evidence_path,
            )
        return

    append_error(
        report,
        "unknown_evidence_reference",
        f"Evidence references an unknown source or package path: {filename!r}",
        f"{evidence_path}.file",
    )


def validate_domain_rules(
    result: dict[str, Any],
    report: dict[str, Any],
    grading_package: dict[str, Any] | None,
    student_material: dict[str, Any] | None,
) -> None:
    """Validate rubric identity, status/score semantics, and evidence locations."""
    expected_items, expected_rules = rubric_maps(grading_package)
    source_lines = student_file_lines(student_material)
    package_lines = package_file_lines(grading_package)

    if not expected_items:
        report["warnings"].append({
            "type": "rubric_domain_validation_skipped",
            "message": "No rubric item map was available from the grading package.",
        })
        report["domain_valid"] = None
        return

    raw_results = result.get("rubric_item_results")
    if not isinstance(raw_results, list):
        report["domain_valid"] = False
        return

    seen_items: set[str] = set()
    for index, item in enumerate(raw_results):
        path = f"$.rubric_item_results[{index}]"
        if not isinstance(item, dict):
            continue

        item_id = item.get("item_id")
        criterion_id = item.get("criterion_id")
        maximum_points = item.get("maximum_points")
        status = item.get("assessment_status")
        points = item.get("suggested_points")

        if not isinstance(item_id, str) or item_id not in expected_items:
            append_error(
                report,
                "unknown_rubric_item",
                f"Unknown rubric item ID: {item_id!r}",
                f"{path}.item_id",
            )
            continue

        if item_id in seen_items:
            append_error(
                report,
                "duplicate_rubric_item",
                f"Rubric item {item_id!r} appears more than once.",
                f"{path}.item_id",
            )
        seen_items.add(item_id)

        expected = expected_items[item_id]
        if criterion_id != expected["criterion_id"]:
            append_error(
                report,
                "criterion_item_mismatch",
                f"Item {item_id!r} belongs to criterion {expected['criterion_id']!r}.",
                f"{path}.criterion_id",
            )

        if maximum_points != expected["maximum_points"]:
            append_error(
                report,
                "maximum_points_mismatch",
                (
                    f"Item {item_id!r} maximum_points should be "
                    f"{expected['maximum_points']!r}, not {maximum_points!r}."
                ),
                f"{path}.maximum_points",
            )

        if status == "scored":
            if not isinstance(points, (int, float)) or isinstance(points, bool):
                append_error(
                    report,
                    "scored_item_missing_points",
                    "A scored item must contain numeric suggested_points.",
                    f"{path}.suggested_points",
                )
            elif points > expected["maximum_points"]:
                append_error(
                    report,
                    "item_score_exceeds_maximum",
                    f"Suggested score {points} exceeds {expected['maximum_points']}.",
                    f"{path}.suggested_points",
                )
        elif status == "requires_local_evidence":
            if points is not None:
                append_error(
                    report,
                    "unverified_item_has_numeric_score",
                    (
                        "requires_local_evidence must use suggested_points: null; "
                        "missing evidence cannot become a numeric deduction."
                    ),
                    f"{path}.suggested_points",
                )
            if item.get("manual_review_needed") is not True:
                append_error(
                    report,
                    "unverified_item_not_flagged",
                    "requires_local_evidence must set manual_review_needed to true.",
                    f"{path}.manual_review_needed",
                )

        evidence = item.get("evidence")
        if not isinstance(evidence, list):
            continue

        for evidence_index, entry in enumerate(evidence):
            if not isinstance(entry, dict):
                continue
            validate_evidence_entry(
                report=report,
                evidence_path=f"{path}.evidence[{evidence_index}]",
                entry=entry,
                source_lines=source_lines,
                package_lines=package_lines,
                grading_package=grading_package,
            )

    missing_items = sorted(set(expected_items) - seen_items)
    if missing_items:
        append_error(
            report,
            "missing_rubric_items",
            "Missing rubric item IDs: " + ", ".join(missing_items),
            "$.rubric_item_results",
        )

    raw_rules = result.get("global_rule_assessments")
    if isinstance(raw_rules, list):
        returned_rules = [
            item.get("rule_id")
            for item in raw_rules
            if isinstance(item, dict) and isinstance(item.get("rule_id"), str)
        ]
        if len(returned_rules) != len(set(returned_rules)):
            append_error(
                report,
                "duplicate_global_rules",
                "One or more global rule IDs were returned more than once.",
                "$.global_rule_assessments",
            )
        missing_rules = sorted(expected_rules - set(returned_rules))
        unexpected_rules = sorted(set(returned_rules) - expected_rules)
        if missing_rules:
            append_error(
                report,
                "missing_global_rules",
                "Missing global rule IDs: " + ", ".join(missing_rules),
                "$.global_rule_assessments",
            )
        if unexpected_rules:
            append_error(
                report,
                "unknown_global_rules",
                "Unknown global rule IDs: " + ", ".join(unexpected_rules),
                "$.global_rule_assessments",
            )

    report["domain_valid"] = not any(
        error.get("type") not in {
            "json_parse_error",
            "schema_validation_error",
        }
        for error in report["errors"]
    )


def validate_structured_response(
    output_text: str,
    response_schema: dict[str, Any],
    expected_anonymous_label: str | None,
    grading_package: dict[str, Any] | None = None,
    student_material: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Parse JSON, validate schema, label, and grading-domain invariants."""
    report: dict[str, Any] = {
        "json_parse_valid": False,
        "schema_valid": False,
        "anonymous_label_valid": None,
        "domain_valid": False,
        "errors": [],
        "warnings": [],
    }

    try:
        result = json.loads(output_text)
    except json.JSONDecodeError as error:
        append_error(report, "json_parse_error", str(error))
        return None, report

    if not isinstance(result, dict):
        append_error(
            report,
            "top_level_type_error",
            "Structured response must be a JSON object.",
        )
        return None, report

    report["json_parse_valid"] = True

    validator = Draft202012Validator(response_schema)
    schema_errors = sorted(
        validator.iter_errors(result),
        key=lambda error: list(error.absolute_path),
    )

    if schema_errors:
        for error in schema_errors:
            location = "$"
            for part in error.absolute_path:
                if isinstance(part, int):
                    location += f"[{part}]"
                else:
                    location += f".{part}"
            append_error(
                report,
                "schema_validation_error",
                error.message,
                location,
            )
    else:
        report["schema_valid"] = True

    actual_label = (
        result.get("submission_label")
        or result.get("anonymous_label")
        or find_first_key(result, "submission_label")
        or find_first_key(result, "anonymous_label")
    )

    if expected_anonymous_label is None:
        report["warnings"].append({
            "type": "label_not_available",
            "message": "No anonymous label was found in the request material.",
        })
    elif actual_label == expected_anonymous_label:
        report["anonymous_label_valid"] = True
    else:
        report["anonymous_label_valid"] = False
        append_error(
            report,
            "anonymous_label_mismatch",
            f"Expected {expected_anonymous_label!r}; received {actual_label!r}.",
            "$.submission_label",
        )

    if report["schema_valid"]:
        validate_domain_rules(
            result,
            report,
            grading_package,
            student_material,
        )

    report["valid"] = (
        report["json_parse_valid"]
        and report["schema_valid"]
        and report["anonymous_label_valid"] is not False
        and report["domain_valid"] is not False
        and not report["errors"]
    )

    return result, report
