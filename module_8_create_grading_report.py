"""Module 8: create one private instructor grading report from one validated Module 7 run.

This module is local-only. It contacts neither Canvas nor a model provider and
never approves or posts a grade.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODULE = "8"
SCHEMA_VERSION = "1.0"
REPORT_DIR_NAME = "module_8_report"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create one validated instructor grading report.")
    parser.add_argument("model_run_directory", type=Path)
    parser.add_argument("--private-manifest", type=Path)
    parser.add_argument("--output-directory", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--allow-anonymous-report",
        action="store_true",
        help="Deliberately create an instructor report without restoring identity.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def validation_path(run_dir: Path) -> Path:
    revalidated = run_dir / "validation_report.revalidated.json"
    return revalidated if revalidated.is_file() else run_dir / "validation_report.json"


def metadata_path(run_dir: Path) -> Path:
    revalidated = run_dir / "run_metadata.revalidated.json"
    return revalidated if revalidated.is_file() else run_dir / "run_metadata.json"


def require_valid(validation: dict[str, Any], path: Path) -> None:
    if validation.get("valid") is not True:
        errors = validation.get("errors")
        count = len(errors) if isinstance(errors, list) else "unknown"
        raise ValueError(
            "Module 8 requires a valid Module 7 result.\n"
            f"Validation file: {path}\n"
            f"Validation valid: {validation.get('valid')!r}\n"
            f"Validation errors: {count}\n"
            "Correct or revalidate Module 7 before creating a report."
        )


def extract_request_material(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    text = payload.get("user_prompt")
    if not isinstance(text, str):
        raise ValueError("request_payload.json has no user_prompt string.")
    match = re.search(
        r"GRADING_PACKAGE_JSON\n(.*?)\n\nAI_SAFE_STUDENT_MATERIAL_JSON\n(.*)\Z",
        text,
        flags=re.DOTALL,
    )
    if match is None:
        raise ValueError("Could not recover the exact sent grading package from request_payload.json.")
    package = json.loads(match.group(1))
    student = json.loads(match.group(2))
    if not isinstance(package, dict) or not isinstance(student, dict):
        raise ValueError("Recovered request material is not a pair of JSON objects.")
    return package, student


def rubric_contract(package: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], float]:
    rubric = package.get("rubric")
    if not isinstance(rubric, dict):
        raise ValueError("The grading package has no rubric object.")
    criteria = rubric.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("The rubric has no criteria.")

    item_map: dict[str, dict[str, Any]] = {}
    ordered_criteria: list[dict[str, Any]] = []
    calculated_max = 0.0

    for criterion in criteria:
        if not isinstance(criterion, dict):
            raise ValueError("Each rubric criterion must be an object.")
        cid = criterion.get("id")
        cname = criterion.get("name") or cid
        cmax = criterion.get("maximum_points")
        items = criterion.get("items")
        if not isinstance(cid, str) or not isinstance(cmax, (int, float)):
            raise ValueError("Every criterion needs an ID and numeric maximum.")
        if not isinstance(items, list) or not items:
            raise ValueError(f"Criterion {cid!r} has no items.")

        ids: list[str] = []
        item_sum = 0.0
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Criterion {cid!r} contains an invalid item.")
            iid = item.get("id")
            imax = item.get("maximum_points")
            if not isinstance(iid, str) or not isinstance(imax, (int, float)):
                raise ValueError(f"Criterion {cid!r} has an item without ID/maximum.")
            if iid in item_map:
                raise ValueError(f"Duplicate rubric item ID: {iid}")
            item_map[iid] = {
                "criterion_id": cid,
                "criterion_name": cname,
                "item_id": iid,
                "description": item.get("description") or iid,
                "maximum_points": imax,
            }
            ids.append(iid)
            item_sum += float(imax)

        if abs(item_sum - float(cmax)) > 1e-9:
            raise ValueError(f"Criterion {cid!r} item totals do not match its maximum.")
        ordered_criteria.append({
            "criterion_id": cid,
            "criterion_name": cname,
            "maximum_points": cmax,
            "item_ids": ids,
        })
        calculated_max += float(cmax)

    declared = rubric.get("maximum_points")
    if not isinstance(declared, (int, float)):
        raise ValueError("The rubric has no numeric maximum_points.")
    if abs(calculated_max - float(declared)) > 1e-9:
        raise ValueError("Criterion maximums do not match the rubric maximum.")
    return item_map, ordered_criteria, float(declared)


def normalize_items(result: dict[str, Any], item_map: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    raw_items = result.get("rubric_item_results")
    if not isinstance(raw_items, list):
        raise ValueError("grading_result.json has no rubric_item_results list.")
    normalized: dict[str, dict[str, Any]] = {}

    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("Each rubric result must be an object.")
        iid = raw.get("item_id")
        if not isinstance(iid, str) or iid not in item_map:
            raise ValueError(f"Unknown rubric item result: {iid!r}")
        if iid in normalized:
            raise ValueError(f"Duplicate rubric item result: {iid}")
        expected = item_map[iid]
        if raw.get("criterion_id") != expected["criterion_id"]:
            raise ValueError(f"Rubric item {iid!r} has the wrong criterion ID.")
        if raw.get("maximum_points") != expected["maximum_points"]:
            raise ValueError(f"Rubric item {iid!r} maximum does not match the rubric.")

        status = raw.get("assessment_status")
        points = raw.get("suggested_points")
        if status == "scored":
            if not isinstance(points, (int, float)) or isinstance(points, bool):
                raise ValueError(f"Scored rubric item {iid!r} has no numeric points.")
            if points < 0 or points > expected["maximum_points"]:
                raise ValueError(f"Rubric item {iid!r} score is outside its allowed range.")
        elif status == "requires_local_evidence":
            if points is not None or raw.get("manual_review_needed") is not True:
                raise ValueError(
                    f"Rubric item {iid!r} requires local evidence but has an invalid score/review state."
                )
        else:
            raise ValueError(f"Rubric item {iid!r} has unsupported status {status!r}.")

        normalized[iid] = {
            **expected,
            "assessment_status": status,
            "suggested_points": points,
            "rationale": raw.get("rationale", ""),
            "evidence": raw.get("evidence", []),
            "confidence": raw.get("confidence"),
            "manual_review_needed": bool(raw.get("manual_review_needed")),
        }

    missing = sorted(set(item_map) - set(normalized))
    if missing:
        raise ValueError("Missing rubric item results: " + ", ".join(missing))
    return normalized


def build_criteria(order: list[dict[str, Any]], items: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], float, list[str]]:
    reports: list[dict[str, Any]] = []
    points_so_far = 0.0
    unresolved: list[str] = []
    for criterion in order:
        criterion_items = [items[iid] for iid in criterion["item_ids"]]
        earned = sum(
            float(item["suggested_points"])
            for item in criterion_items
            if item["assessment_status"] == "scored"
        )
        complete = all(item["assessment_status"] == "scored" for item in criterion_items)
        unresolved.extend(item["item_id"] for item in criterion_items if item["assessment_status"] != "scored")
        points_so_far += earned
        reports.append({
            "criterion_id": criterion["criterion_id"],
            "criterion_name": criterion["criterion_name"],
            "maximum_points": criterion["maximum_points"],
            "suggested_points": earned if complete else None,
            "scored_points_so_far": earned,
            "complete": complete,
            "items": criterion_items,
        })
    return reports, points_so_far, unresolved


def normalize_rules(result: dict[str, Any]) -> tuple[list[dict[str, Any]], float, list[float]]:
    raw_rules = result.get("global_rule_assessments")
    if not isinstance(raw_rules, list):
        raise ValueError("grading_result.json has no global_rule_assessments list.")
    normalized: list[dict[str, Any]] = []
    deductions = 0.0
    caps: list[float] = []
    for raw in raw_rules:
        if not isinstance(raw, dict):
            raise ValueError("Every global-rule assessment must be an object.")
        rid = raw.get("rule_id")
        applicable = raw.get("applicable")
        action = raw.get("recommended_action")
        value = raw.get("recommended_value")
        if not isinstance(rid, str) or not isinstance(applicable, bool):
            raise ValueError("Every global rule needs rule_id and boolean applicable.")
        if action not in {"none", "deduction", "score_cap"}:
            raise ValueError(f"Global rule {rid!r} has unsupported action {action!r}.")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise ValueError(f"Global rule {rid!r} has an invalid recommended value.")
        if not applicable and (action != "none" or value != 0):
            raise ValueError(f"Global rule {rid!r} is not applicable but recommends an adjustment.")
        if applicable and action == "deduction":
            deductions += float(value)
        elif applicable and action == "score_cap":
            caps.append(float(value))
        normalized.append({
            "rule_id": rid,
            "applicable": applicable,
            "recommended_action": action,
            "recommended_value": value,
            "rationale": raw.get("rationale", ""),
            "objective_evidence_required": bool(raw.get("objective_evidence_required")),
            "manual_review_needed": bool(raw.get("manual_review_needed")),
        })
    return normalized, deductions, caps


def score_summary(points_so_far: float, maximum: float, unresolved: list[str], deductions: float, caps: list[float]) -> dict[str, Any]:
    if unresolved:
        return {
            "calculation_status": "incomplete_requires_review",
            "rubric_maximum_points": maximum,
            "base_points": None,
            "scored_points_so_far": points_so_far,
            "recommended_deductions": deductions,
            "recommended_score_caps": caps,
            "suggested_score_after_adjustments": None,
            "unresolved_item_ids": unresolved,
        }
    score = max(0.0, points_so_far - deductions)
    if caps:
        score = min(score, min(caps))
    score = min(score, maximum)
    return {
        "calculation_status": "complete_advisory_score",
        "rubric_maximum_points": maximum,
        "base_points": points_so_far,
        "scored_points_so_far": points_so_far,
        "recommended_deductions": deductions,
        "recommended_score_caps": caps,
        "suggested_score_after_adjustments": score,
        "unresolved_item_ids": [],
    }


def restore_identity(manifest: dict[str, Any], label: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    privacy = manifest.get("privacy")
    if not isinstance(privacy, dict) or privacy.get("send_to_ai") is not False:
        raise ValueError("Identity restoration requires a private manifest marked send_to_ai=false.")
    submissions = manifest.get("submissions")
    if not isinstance(submissions, list):
        raise ValueError("The private manifest has no submissions list.")
    matches = [x for x in submissions if isinstance(x, dict) and x.get("anonymous_label") == label]
    if len(matches) != 1:
        raise ValueError(f"Expected one private record for {label!r}; found {len(matches)}.")
    record = matches[0]
    course = manifest.get("course") if isinstance(manifest.get("course"), dict) else {}
    assignment = manifest.get("assignment") if isinstance(manifest.get("assignment"), dict) else {}
    identity = {
        "identity_restored": True,
        "student_name": record.get("student_name"),
        "canvas_user_id": record.get("canvas_user_id"),
    }
    return identity, course, assignment, record


def determine_status(score: dict[str, Any], result: dict[str, Any], rules: list[dict[str, Any]]) -> str:
    if score["calculation_status"] != "complete_advisory_score":
        return "requires_instructor_review"
    item_flag = any(
        bool(x.get("manual_review_needed"))
        for x in result.get("rubric_item_results", [])
        if isinstance(x, dict)
    )
    rule_flag = any(bool(x.get("manual_review_needed")) for x in rules)
    flags = result.get("manual_review_flags")
    if item_flag or rule_flag or (isinstance(flags, list) and bool(flags)):
        return "complete_with_review_flags"
    return "complete_ready_for_instructor_review"


def build_report(
    run_dir: Path,
    validation_file: Path,
    metadata_file: Path,
    result_file: Path,
    payload_file: Path,
    request_manifest_file: Path | None,
    validation: dict[str, Any],
    metadata: dict[str, Any],
    result: dict[str, Any],
    payload: dict[str, Any],
    package: dict[str, Any],
    student_material: dict[str, Any],
    private_manifest: dict[str, Any] | None,
    private_manifest_file: Path | None,
) -> dict[str, Any]:
    label = result.get("submission_label")
    if not isinstance(label, str) or not label:
        raise ValueError("grading_result.json has no submission_label.")

    item_map, order, maximum = rubric_contract(package)
    items = normalize_items(result, item_map)
    criteria, points_so_far, unresolved = build_criteria(order, items)
    rules, deductions, caps = normalize_rules(result)
    score = score_summary(points_so_far, maximum, unresolved, deductions, caps)

    if private_manifest is None:
        identity = {"identity_restored": False, "student_name": None, "canvas_user_id": None}
        course: dict[str, Any] = {}
        private_assignment: dict[str, Any] = {}
        private_submission: dict[str, Any] = {}
    else:
        identity, course, private_assignment, private_submission = restore_identity(private_manifest, label)

    package_assignment = package.get("assignment") if isinstance(package.get("assignment"), dict) else {}
    package_submission = package.get("submission") if isinstance(package.get("submission"), dict) else {}
    selected_attempt = package_submission.get("selected_attempt") or private_submission.get("attempt")
    if (
        isinstance(package_submission.get("selected_attempt"), int)
        and isinstance(private_submission.get("attempt"), int)
        and package_submission["selected_attempt"] != private_submission["attempt"]
    ):
        raise ValueError("Private-manifest attempt does not match the grading package attempt.")

    source_files = student_material.get("source_files")
    if not isinstance(source_files, list):
        source_files = student_material.get("files")
    prompt_meta = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}

    return {
        "module": MODULE,
        "schema_version": SCHEMA_VERSION,
        "report_type": "one_student_instructor_grading_report",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "privacy": {
            "classification": "PRIVATE - FERPA-protected instructor report" if identity["identity_restored"] else "Instructor report using anonymous submission label",
            "send_to_ai": False,
            "contains_student_name": identity["student_name"] is not None,
            "contains_canvas_user_id": identity["canvas_user_id"] is not None,
            "human_review_required": True,
        },
        "report_status": determine_status(score, result, rules),
        "identity": {"anonymous_label": label, **identity},
        "course": course,
        "assignment": {
            "canvas_assignment_id": private_assignment.get("id"),
            "canvas_assignment_name": private_assignment.get("name"),
            "asset_package_id": package_assignment.get("asset_package_id"),
            "title": private_assignment.get("name") or package_assignment.get("title"),
            "language": package_assignment.get("language"),
            "expected_standard": package_assignment.get("expected_standard"),
        },
        "submission": {
            "selected_attempt": selected_attempt,
            "submitted_at": private_submission.get("submitted_at"),
            "submission_type": private_submission.get("submission_type"),
            "workflow_state": private_submission.get("workflow_state"),
            "late": private_submission.get("late"),
            "missing": private_submission.get("missing"),
            "seconds_late": private_submission.get("seconds_late"),
            "source_file_count": len(source_files) if isinstance(source_files, list) else None,
        },
        "advisory_scoring": score,
        "criteria": criteria,
        "global_rule_assessments": rules,
        "feedback": {
            "student_feedback_draft": result.get("student_feedback", ""),
            "instructor_summary": result.get("instructor_summary", ""),
            "overall_confidence": result.get("overall_confidence"),
            "manual_review_flags": result.get("manual_review_flags", []),
        },
        "provenance": {
            "model_run_directory": str(run_dir),
            "provider": metadata.get("provider"),
            "model": metadata.get("model"),
            "profile": metadata.get("profile"),
            "response_id": metadata.get("response_id"),
            "prompt_version": prompt_meta.get("prompt_version"),
            "provider_status": metadata.get("status"),
            "elapsed_seconds": metadata.get("elapsed_seconds"),
            "usage": metadata.get("usage"),
            "schema_enforced_by_provider": metadata.get("schema_enforced_by_provider"),
            "structured_response_valid": validation.get("valid"),
            "validation_file": str(validation_file),
            "metadata_file": str(metadata_file),
            "private_manifest_file": str(private_manifest_file) if private_manifest_file else None,
            "canvas_contacted": False,
            "model_provider_contacted": False,
        },
        "source_hashes": {
            "grading_result_sha256": sha256(result_file),
            "validation_report_sha256": sha256(validation_file),
            "run_metadata_sha256": sha256(metadata_file),
            "request_payload_sha256": sha256(payload_file),
            "request_manifest_sha256": sha256(request_manifest_file) if request_manifest_file else None,
            "private_manifest_sha256": sha256(private_manifest_file) if private_manifest_file else None,
        },
        "approval": {
            "status": "NOT_APPROVED",
            "final_score": None,
            "approved_feedback": None,
            "approved_by": None,
            "approved_at_utc": None,
            "note": "Module 8 creates an advisory instructor report only. It does not approve or post a grade.",
        },
    }


def n(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def md(value: Any) -> str:
    return "" if value is None else str(value).replace("|", r"\|").replace("\n", "<br>")


def evidence_md(entries: Any) -> str:
    if not isinstance(entries, list) or not entries:
        return "_No evidence entries returned._"
    lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        source = entry.get("file", "unknown")
        start, end = entry.get("line_start"), entry.get("line_end")
        location = f"{source}, lines {start}–{end}" if isinstance(start, int) and isinstance(end, int) else str(source)
        lines.append(f"- **{md(location)}:** {md(entry.get('description', ''))}")
    return "\n".join(lines) or "_No evidence entries returned._"


def render_markdown(report: dict[str, Any]) -> str:
    ident = report["identity"]
    assignment = report["assignment"]
    submission = report["submission"]
    score = report["advisory_scoring"]
    feedback = report["feedback"]
    prov = report["provenance"]

    lines = [
        "# One-Student Grading Report", "",
        "> **PRIVATE INSTRUCTOR REPORT — DO NOT SEND TO A MODEL**", "",
        "This is an advisory grading report. It is not an approved or posted grade.", "",
        "## Student and Submission", "",
        f"- **Student:** {md(ident.get('student_name') or 'Anonymous report')}",
        f"- **Anonymous label:** `{md(ident.get('anonymous_label'))}`",
        f"- **Canvas user ID:** {md(ident.get('canvas_user_id') or 'Not restored')}",
        f"- **Assignment:** {md(assignment.get('title'))}",
        f"- **Canvas assignment ID:** {md(assignment.get('canvas_assignment_id') or 'Unknown')}",
        f"- **Selected attempt:** {md(submission.get('selected_attempt'))}",
        f"- **Submitted at:** {md(submission.get('submitted_at') or 'Unknown')}",
        f"- **Late:** {md(submission.get('late'))}",
        f"- **Source files:** {md(submission.get('source_file_count'))}", "",
        "## Advisory Score Summary", "",
        f"- **Calculation status:** `{md(score.get('calculation_status'))}`",
        f"- **Base rubric points:** {n(score.get('base_points'))} / {n(score.get('rubric_maximum_points'))}",
        f"- **Recommended deductions:** {n(score.get('recommended_deductions'))}",
        f"- **Recommended score caps:** {md(score.get('recommended_score_caps'))}",
        f"- **Suggested score after adjustments:** **{n(score.get('suggested_score_after_adjustments'))} / {n(score.get('rubric_maximum_points'))}**", "",
        "## Criterion Summary", "",
        "| Criterion | Suggested | Maximum | Status |",
        "|---|---:|---:|---|",
    ]
    for c in report["criteria"]:
        lines.append(f"| {md(c['criterion_name'])} | {n(c['suggested_points'])} | {n(c['maximum_points'])} | {'Complete' if c['complete'] else 'Review required'} |")
    lines += ["", "## Detailed Rubric Review", ""]
    for c in report["criteria"]:
        lines += [f"### {md(c['criterion_name'])}", ""]
        for item in c["items"]:
            shown = f"{n(item['suggested_points'])} / {n(item['maximum_points'])}" if item["assessment_status"] == "scored" else "Requires local evidence"
            lines += [
                f"#### {md(item['description'])}", "",
                f"- **Item ID:** `{md(item['item_id'])}`",
                f"- **Assessment:** `{md(item['assessment_status'])}`",
                f"- **Suggested points:** {shown}",
                f"- **Confidence:** {md(item.get('confidence'))}",
                f"- **Manual review needed:** {md(item.get('manual_review_needed'))}", "",
                "**Rationale**", "", md(item.get("rationale")), "",
                "**Evidence**", "", evidence_md(item.get("evidence")), "",
            ]
    lines += [
        "## Global Rule Assessments", "",
        "| Rule | Applicable | Action | Value | Review |",
        "|---|---|---|---:|---|",
    ]
    for rule in report["global_rule_assessments"]:
        lines.append(f"| `{md(rule['rule_id'])}` | {md(rule['applicable'])} | {md(rule['recommended_action'])} | {n(rule['recommended_value'])} | {md(rule['manual_review_needed'])} |")
    lines += [
        "", "## Draft Student Feedback", "", md(feedback.get("student_feedback_draft")) or "_None._", "",
        "## Instructor Summary", "", md(feedback.get("instructor_summary")) or "_None._", "",
        "## Manual Review Flags", "",
    ]
    flags = feedback.get("manual_review_flags")
    if isinstance(flags, list) and flags:
        lines += [f"- {md(flag)}" for flag in flags]
    else:
        lines.append("_No model-generated manual review flags._")
    lines += [
        "", "## Provenance", "",
        f"- **Report status:** `{md(report.get('report_status'))}`",
        f"- **Provider/model:** {md(prov.get('provider'))} / {md(prov.get('model'))}",
        f"- **Prompt version:** {md(prov.get('prompt_version'))}",
        f"- **Response ID:** `{md(prov.get('response_id'))}`",
        f"- **Validated response:** {md(prov.get('structured_response_valid'))}",
        f"- **Model run:** `{md(prov.get('model_run_directory'))}`", "",
        "## Approval State", "",
        "- **Status:** `NOT_APPROVED`",
        "- **Final score:** Not assigned",
        "- **Canvas updated:** No", "",
        "_Instructor review and approval remain required._", "",
    ]
    return "\n".join(lines)


def validation_summary(report: dict[str, Any]) -> dict[str, Any]:
    item_count = sum(len(c["items"]) for c in report["criteria"])
    scored = sum(1 for c in report["criteria"] for i in c["items"] if i["assessment_status"] == "scored")
    score = report["advisory_scoring"]
    return {
        "module": MODULE,
        "schema_version": SCHEMA_VERSION,
        "valid": True,
        "report_status": report["report_status"],
        "identity_restored": report["identity"]["identity_restored"],
        "rubric_item_count": item_count,
        "scored_item_count": scored,
        "unresolved_item_count": item_count - scored,
        "rubric_maximum_points": score["rubric_maximum_points"],
        "suggested_score_after_adjustments": score["suggested_score_after_adjustments"],
        "approval_status": report["approval"]["status"],
        "canvas_contacted": False,
        "model_provider_contacted": False,
        "errors": [],
        "warnings": [] if report["identity"]["identity_restored"] else ["Student identity was not restored."],
    }


def main() -> int:
    args = parse_args()
    run_dir = args.model_run_directory.resolve()
    out_dir = args.output_directory.resolve() if args.output_directory else run_dir / REPORT_DIR_NAME
    staging = out_dir.with_name(f".{out_dir.name}_building")
    try:
        if not run_dir.is_dir():
            raise FileNotFoundError(f"Model-run directory not found: {run_dir}")
        result_file = run_dir / "grading_result.json"
        valid_file = validation_path(run_dir)
        meta_file = metadata_path(run_dir)
        payload_file = run_dir / "request_payload.json"
        request_manifest_file = run_dir / "request_manifest.json"

        result = load_json(result_file)
        validation = load_json(valid_file)
        metadata = load_json(meta_file)
        payload = load_json(payload_file)
        require_valid(validation, valid_file)
        package, student_material = extract_request_material(payload)

        private_file: Path | None = None
        private: dict[str, Any] | None = None
        if args.private_manifest:
            private_file = args.private_manifest.resolve()
            private = load_json(private_file)
        elif not args.allow_anonymous_report:
            raise ValueError(
                "A private manifest is required for the normal instructor report.\n"
                "Pass --private-manifest <path>, or deliberately use --allow-anonymous-report."
            )

        report = build_report(
            run_dir, valid_file, meta_file, result_file, payload_file,
            request_manifest_file if request_manifest_file.is_file() else None,
            validation, metadata, result, payload, package, student_material,
            private, private_file,
        )

        if out_dir.exists() and not args.overwrite:
            raise FileExistsError(f"Module 8 report directory already exists: {out_dir}\nUse --overwrite to replace it.")
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)

        report_json = staging / "one_student_grading_report.json"
        report_md = staging / "one_student_grading_report.md"
        report_validation = staging / "report_validation.json"
        write_json(report_json, report)
        report_md.write_text(render_markdown(report), encoding="utf-8")
        write_json(report_validation, validation_summary(report))
        manifest = {
            "module": MODULE,
            "schema_version": SCHEMA_VERSION,
            "anonymous_label": report["identity"]["anonymous_label"],
            "report_status": report["report_status"],
            "files": {
                "canonical_report": report_json.name,
                "readable_report": report_md.name,
                "validation": report_validation.name,
            },
            "sha256": {
                "canonical_report": sha256(report_json),
                "readable_report": sha256(report_md),
                "validation": sha256(report_validation),
            },
            "privacy": report["privacy"],
            "approval_status": report["approval"]["status"],
            "canvas_contacted": False,
            "model_provider_contacted": False,
        }
        write_json(staging / "module_8_report_manifest.json", manifest)
        if out_dir.exists():
            shutil.rmtree(out_dir)
        staging.replace(out_dir)

        score = report["advisory_scoring"]
        print("=" * 78)
        print("MODULE 8 ONE-STUDENT GRADING REPORT")
        print("=" * 78)
        print(f"Student:          {report['identity'].get('student_name') or '[anonymous]'}")
        print(f"Anonymous label:  {report['identity']['anonymous_label']}")
        print(f"Report status:    {report['report_status']}")
        print(f"Suggested score:  {n(score['suggested_score_after_adjustments'])} / {n(score['rubric_maximum_points'])}")
        print(f"Approval status:  {report['approval']['status']}")
        print(f"Output directory: {out_dir}")
        print("Canvas contacted: No")
        print("Model contacted:  No")
        print("\nRESULT: REPORT CREATED FOR INSTRUCTOR REVIEW")
        return 0
    except Exception as exc:
        if staging.exists():
            shutil.rmtree(staging)
        print("\nMODULE 8 FAILED")
        print(exc)
        print("\nNo Canvas or model request was made.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
