"""Characterization tests for module_6_build_grading_package.validate_ai_manifest().

These tests document the function's current, already-shipped behavior on
Module 5.1's module_5_ai_package_manifest.json shape. They do not change,
improve, or replace that behavior. Where the current implementation is
surprising (see the bool/int subclassing test below), the surprising
behavior is documented rather than silently treated as a bug.

No Canvas call, model-provider call, compilation, or execution occurs here;
only the pure validate_ai_manifest() function is exercised, in-process, on
synthetic fixture data.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import module_6_build_grading_package as module_6

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "module_5_ai_package_manifest_valid.json"
)

PRIVACY_REQUIRED_FALSE_FIELDS = [
    "contains_canvas_user_id",
    "contains_student_name",
    "contains_original_zip_filename",
    "contains_download_urls",
]


@pytest.fixture
def valid_manifest() -> dict:
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------


def test_valid_manifest_succeeds_with_no_warnings(valid_manifest):
    label, attempt, files, warnings = module_6.validate_ai_manifest(
        valid_manifest, allow_warnings=False
    )
    assert label == "submission_002"
    assert attempt == valid_manifest["submission"]["selected_attempt"]
    assert files == sorted(valid_manifest["package"]["files"])
    assert warnings == []


# ---------------------------------------------------------------------------
# The four required-False privacy fields
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", PRIVACY_REQUIRED_FALSE_FIELDS)
def test_privacy_field_missing_is_rejected(valid_manifest, field):
    manifest = copy.deepcopy(valid_manifest)
    del manifest["privacy"][field]
    with pytest.raises(ValueError, match="not explicitly AI-safe"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


@pytest.mark.parametrize("field", PRIVACY_REQUIRED_FALSE_FIELDS)
def test_privacy_field_true_is_rejected(valid_manifest, field):
    manifest = copy.deepcopy(valid_manifest)
    manifest["privacy"][field] = True
    with pytest.raises(ValueError, match="not explicitly AI-safe"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


@pytest.mark.parametrize("field", PRIVACY_REQUIRED_FALSE_FIELDS)
@pytest.mark.parametrize(
    "bad_value",
    [0, None, "", "false"],
    ids=["zero", "none", "empty_string", "string_false"],
)
def test_privacy_field_false_like_non_boolean_values_are_rejected(
    valid_manifest, field, bad_value
):
    """Only the literal Boolean False is accepted; every false-like stand-in
    (0, None, "", the string "false") is rejected because the implementation
    compares with `is not False`, an identity check, not equality."""
    manifest = copy.deepcopy(valid_manifest)
    manifest["privacy"][field] = bad_value
    with pytest.raises(ValueError, match="not explicitly AI-safe"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


def test_missing_privacy_object_is_rejected(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    del manifest["privacy"]
    with pytest.raises(ValueError, match="no privacy object"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


@pytest.mark.parametrize(
    "bad_value", [None, "not a dict", 123, []], ids=["none", "string", "int", "list"]
)
def test_non_object_privacy_is_rejected(valid_manifest, bad_value):
    manifest = copy.deepcopy(valid_manifest)
    manifest["privacy"] = bad_value
    with pytest.raises(ValueError, match="no privacy object"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


# ---------------------------------------------------------------------------
# submission / package presence
# ---------------------------------------------------------------------------


def test_missing_submission_object_is_rejected(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    del manifest["submission"]
    with pytest.raises(ValueError, match="missing submission/package data"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


@pytest.mark.parametrize(
    "bad_value", [None, "not a dict", 123, []], ids=["none", "string", "int", "list"]
)
def test_non_object_submission_is_rejected(valid_manifest, bad_value):
    manifest = copy.deepcopy(valid_manifest)
    manifest["submission"] = bad_value
    with pytest.raises(ValueError, match="missing submission/package data"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


def test_missing_package_object_is_rejected(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    del manifest["package"]
    with pytest.raises(ValueError, match="missing submission/package data"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


@pytest.mark.parametrize(
    "bad_value", [None, "not a dict", 123, []], ids=["none", "string", "int", "list"]
)
def test_non_object_package_is_rejected(valid_manifest, bad_value):
    manifest = copy.deepcopy(valid_manifest)
    manifest["package"] = bad_value
    with pytest.raises(ValueError, match="missing submission/package data"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


# ---------------------------------------------------------------------------
# anonymous_label
# ---------------------------------------------------------------------------


def test_anonymous_label_missing_is_rejected(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    del manifest["submission"]["anonymous_label"]
    with pytest.raises(ValueError, match="no anonymous label"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


@pytest.mark.parametrize(
    "bad_value",
    [123, "", "   "],
    ids=["non_string", "empty", "whitespace_only"],
)
def test_anonymous_label_invalid_values_are_rejected(valid_manifest, bad_value):
    manifest = copy.deepcopy(valid_manifest)
    manifest["submission"]["anonymous_label"] = bad_value
    with pytest.raises(ValueError, match="no anonymous label"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


def test_anonymous_label_is_stripped(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    manifest["submission"]["anonymous_label"] = "  submission_002  "
    label, *_ = module_6.validate_ai_manifest(manifest, allow_warnings=False)
    assert label == "submission_002"


# ---------------------------------------------------------------------------
# selected_attempt
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value", [None, 1, 0, -1], ids=["none", "positive_int", "zero", "negative_int"]
)
def test_selected_attempt_accepted_values(valid_manifest, value):
    manifest = copy.deepcopy(valid_manifest)
    manifest["submission"]["selected_attempt"] = value
    _, attempt, _, _ = module_6.validate_ai_manifest(manifest, allow_warnings=False)
    assert attempt == value


def test_selected_attempt_missing_key_is_treated_as_none(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    del manifest["submission"]["selected_attempt"]
    _, attempt, _, _ = module_6.validate_ai_manifest(manifest, allow_warnings=False)
    assert attempt is None


@pytest.mark.parametrize("value", [True, False], ids=["true", "false"])
def test_selected_attempt_boolean_is_currently_accepted_due_to_int_subclassing(
    valid_manifest, value
):
    """Surprising current behavior, preserved rather than silently changed:
    Python's bool is a subclass of int, so validate_ai_manifest's
    `isinstance(attempt, int)` check currently accepts both True and False as
    valid selected_attempt values. Future model-design consideration: a
    stricter replacement contract should explicitly reject bool here, the
    same way Module 8's normalize_items already does for score/point
    fields."""
    manifest = copy.deepcopy(valid_manifest)
    manifest["submission"]["selected_attempt"] = value
    _, attempt, _, _ = module_6.validate_ai_manifest(manifest, allow_warnings=False)
    assert attempt is value


@pytest.mark.parametrize(
    "bad_value",
    ["1", 1.5, [], {}],
    ids=["string", "float", "list", "dict"],
)
def test_selected_attempt_non_integer_values_are_rejected(valid_manifest, bad_value):
    manifest = copy.deepcopy(valid_manifest)
    manifest["submission"]["selected_attempt"] = bad_value
    with pytest.raises(ValueError, match="selected_attempt must be an integer or null"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


# ---------------------------------------------------------------------------
# comments_removed / known_identifiers_redacted
# ---------------------------------------------------------------------------


def test_comments_removed_missing_key_is_rejected(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    del manifest["package"]["comments_removed"]
    with pytest.raises(ValueError, match="does not confirm comment removal"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


def test_comments_removed_explicit_null_is_rejected(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    manifest["package"]["comments_removed"] = None
    with pytest.raises(ValueError, match="does not confirm comment removal"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


@pytest.mark.parametrize(
    "bad_value",
    [False, 1, "true"],
    ids=["false", "one", "string_true"],
)
def test_comments_removed_invalid_values_are_rejected(valid_manifest, bad_value):
    manifest = copy.deepcopy(valid_manifest)
    manifest["package"]["comments_removed"] = bad_value
    with pytest.raises(ValueError, match="does not confirm comment removal"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


def test_known_identifiers_redacted_missing_key_is_rejected(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    del manifest["package"]["known_identifiers_redacted"]
    with pytest.raises(ValueError, match="does not confirm identifier redaction"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


def test_known_identifiers_redacted_explicit_null_is_rejected(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    manifest["package"]["known_identifiers_redacted"] = None
    with pytest.raises(ValueError, match="does not confirm identifier redaction"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


@pytest.mark.parametrize(
    "bad_value",
    [False, 1, "true"],
    ids=["false", "one", "string_true"],
)
def test_known_identifiers_redacted_invalid_values_are_rejected(
    valid_manifest, bad_value
):
    manifest = copy.deepcopy(valid_manifest)
    manifest["package"]["known_identifiers_redacted"] = bad_value
    with pytest.raises(ValueError, match="does not confirm identifier redaction"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


# ---------------------------------------------------------------------------
# package.files
# ---------------------------------------------------------------------------


def test_files_missing_is_rejected(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    del manifest["package"]["files"]
    with pytest.raises(ValueError, match="no source-file list"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


@pytest.mark.parametrize(
    "bad_value", ["not a list", None, {}], ids=["string", "none", "dict"]
)
def test_files_non_list_is_rejected(valid_manifest, bad_value):
    manifest = copy.deepcopy(valid_manifest)
    manifest["package"]["files"] = bad_value
    with pytest.raises(ValueError, match="no source-file list"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


def test_files_empty_list_is_rejected(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    manifest["package"]["files"] = []
    with pytest.raises(ValueError, match="no source-file list"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


@pytest.mark.parametrize(
    "bad_entry",
    [123, None, "", "   "],
    ids=["non_string", "none", "empty_string", "whitespace_only"],
)
def test_files_entry_invalid_values_are_rejected(valid_manifest, bad_entry):
    manifest = copy.deepcopy(valid_manifest)
    manifest["package"]["files"] = ["main.cpp", bad_entry]
    with pytest.raises(ValueError, match="must be non-empty strings"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


def test_files_are_path_normalized_and_sorted(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    manifest["package"]["files"] = ["./b.cpp", "a.cpp", ".\\c.cpp"]
    _, _, files, _ = module_6.validate_ai_manifest(manifest, allow_warnings=False)
    assert files == ["a.cpp", "b.cpp", "c.cpp"]


# ---------------------------------------------------------------------------
# warnings / allow_warnings
# ---------------------------------------------------------------------------


def test_warnings_missing_key_defaults_to_empty_list(valid_manifest):
    """manifest.get("warnings", []) means a missing warnings key is currently
    tolerated (defaults to an empty list), unlike a present-but-wrong-typed
    warnings value, which is rejected below."""
    manifest = copy.deepcopy(valid_manifest)
    del manifest["warnings"]
    _, _, _, warnings = module_6.validate_ai_manifest(manifest, allow_warnings=False)
    assert warnings == []


@pytest.mark.parametrize(
    "bad_value", ["not a list", 123, {}, None], ids=["string", "int", "dict", "none"]
)
def test_warnings_non_list_is_rejected(valid_manifest, bad_value):
    manifest = copy.deepcopy(valid_manifest)
    manifest["warnings"] = bad_value
    with pytest.raises(ValueError, match="warnings must be a list"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


def test_nonempty_warnings_rejected_when_not_allowed(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    manifest["warnings"] = ["Something to review."]
    with pytest.raises(ValueError, match="reported warnings"):
        module_6.validate_ai_manifest(manifest, allow_warnings=False)


def test_nonempty_warnings_accepted_when_allowed(valid_manifest):
    manifest = copy.deepcopy(valid_manifest)
    manifest["warnings"] = ["Something to review."]
    _, _, _, warnings = module_6.validate_ai_manifest(manifest, allow_warnings=True)
    assert warnings == ["Something to review."]
