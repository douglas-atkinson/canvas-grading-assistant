"""Tests for the first Phase 5 shared domain models.

These tests cover canvas_grading_assistant.domain.artifacts
(PrivacyClassification, ArtifactMetadata) only. They construct models
in-process from synthetic dict/kwarg data; they do not call, import for
execution, or otherwise exercise module_6_build_grading_package.py's
validate_ai_manifest() (already covered by
tests/test_module_6_validate_ai_manifest.py), and they do not contact Canvas,
contact a model provider, or compile/execute student code.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from canvas_grading_assistant.domain.artifacts import (
    ArtifactMetadata,
    PrivacyClassification,
)

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "module_5_ai_package_manifest_valid.json"
)

CONTAINS_FIELDS = [
    "contains_canvas_user_id",
    "contains_student_name",
    "contains_original_zip_filename",
    "contains_download_urls",
]


def _valid_privacy_kwargs(**overrides):
    base = dict(
        classification="AI-candidate package metadata",
        send_to_ai=True,
        contains_canvas_user_id=False,
        contains_student_name=False,
        contains_original_zip_filename=False,
        contains_download_urls=False,
    )
    base.update(overrides)
    return base


def _valid_metadata_kwargs(**overrides):
    base = dict(
        artifact_type="grading_package",
        schema_version="1.0",
        privacy=_valid_privacy_kwargs(),
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# PrivacyClassification: declared safety semantics (list items 1-4)
# ---------------------------------------------------------------------------


def test_private_declaration_is_valid_and_not_declared_ai_safe():
    privacy = PrivacyClassification(
        classification="PRIVATE - FERPA-protected", send_to_ai=False
    )
    assert privacy.is_declared_ai_safe is False


def test_ai_safe_declaration_with_all_four_contains_false():
    privacy = PrivacyClassification(**_valid_privacy_kwargs())
    assert privacy.is_declared_ai_safe is True


def test_ai_safe_declaration_with_subset_of_contains_fields_present():
    privacy = PrivacyClassification(
        classification="AI-candidate package metadata",
        send_to_ai=True,
        contains_canvas_user_id=False,
    )
    assert privacy.is_declared_ai_safe is True
    assert privacy.contains_student_name is None
    assert privacy.contains_original_zip_filename is None
    assert privacy.contains_download_urls is None


@pytest.mark.parametrize("field", CONTAINS_FIELDS)
def test_structurally_valid_but_not_declared_ai_safe_when_a_contains_field_is_true(
    field,
):
    """Shape validation and declared transmission safety are distinct:
    send_to_ai=True with one contains_* assertion true is not a validation
    error, but it is not declared AI-safe."""
    kwargs = _valid_privacy_kwargs()
    kwargs[field] = True
    privacy = PrivacyClassification(**kwargs)
    assert privacy.is_declared_ai_safe is False


# ---------------------------------------------------------------------------
# PrivacyClassification: strict Boolean handling (list items 5-6)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    ["true", "false", 1, 0, None],
    ids=["str_true", "str_false", "one", "zero", "none"],
)
def test_send_to_ai_rejects_non_boolean_values(bad_value):
    with pytest.raises(ValidationError):
        PrivacyClassification(classification="x", send_to_ai=bad_value)


@pytest.mark.parametrize("field", CONTAINS_FIELDS)
@pytest.mark.parametrize(
    "bad_value",
    ["true", "false", 1, 0],
    ids=["str_true", "str_false", "one", "zero"],
)
def test_contains_fields_reject_non_boolean_values(field, bad_value):
    kwargs = dict(classification="x", send_to_ai=False)
    kwargs[field] = bad_value
    with pytest.raises(ValidationError):
        PrivacyClassification(**kwargs)


# ---------------------------------------------------------------------------
# PrivacyClassification: classification trimming (list items 7-8)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_value", ["", "   "], ids=["empty", "whitespace_only"])
def test_classification_empty_or_whitespace_is_rejected(bad_value):
    with pytest.raises(ValidationError):
        PrivacyClassification(classification=bad_value, send_to_ai=False)


def test_classification_whitespace_is_trimmed():
    privacy = PrivacyClassification(
        classification="  PRIVATE - FERPA-protected  ", send_to_ai=False
    )
    assert privacy.classification == "PRIVATE - FERPA-protected"


# ---------------------------------------------------------------------------
# PrivacyClassification: unknown fields and immutability (list items 9-10)
# ---------------------------------------------------------------------------


def test_privacy_classification_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        PrivacyClassification(classification="x", send_to_ai=False, unexpected_field=1)


def test_privacy_classification_is_frozen():
    privacy = PrivacyClassification(classification="x", send_to_ai=False)
    with pytest.raises(ValidationError):
        privacy.classification = "changed"


# ---------------------------------------------------------------------------
# ArtifactMetadata (list items 11-20)
# ---------------------------------------------------------------------------


def test_valid_artifact_metadata_loads():
    metadata = ArtifactMetadata(**_valid_metadata_kwargs())
    assert metadata.artifact_type == "grading_package"
    assert metadata.schema_version == "1.0"


def test_nested_privacy_classification_is_constructed_and_available():
    metadata = ArtifactMetadata(**_valid_metadata_kwargs())
    assert isinstance(metadata.privacy, PrivacyClassification)
    assert metadata.privacy.is_declared_ai_safe is True


@pytest.mark.parametrize("bad_value", ["", "   "], ids=["empty", "whitespace_only"])
def test_artifact_type_empty_or_whitespace_is_rejected(bad_value):
    with pytest.raises(ValidationError):
        ArtifactMetadata(**_valid_metadata_kwargs(artifact_type=bad_value))


@pytest.mark.parametrize("bad_value", ["", "   "], ids=["empty", "whitespace_only"])
def test_schema_version_empty_or_whitespace_is_rejected(bad_value):
    with pytest.raises(ValidationError):
        ArtifactMetadata(**_valid_metadata_kwargs(schema_version=bad_value))


def test_artifact_type_and_schema_version_whitespace_is_trimmed():
    metadata = ArtifactMetadata(
        **_valid_metadata_kwargs(
            artifact_type="  grading_package  ", schema_version="  1.0  "
        )
    )
    assert metadata.artifact_type == "grading_package"
    assert metadata.schema_version == "1.0"


def test_artifact_metadata_rejects_unknown_top_level_fields():
    kwargs = _valid_metadata_kwargs()
    kwargs["unexpected_field"] = 1
    with pytest.raises(ValidationError):
        ArtifactMetadata(**kwargs)


def test_artifact_metadata_rejects_unknown_nested_privacy_fields():
    kwargs = _valid_metadata_kwargs()
    kwargs["privacy"] = dict(kwargs["privacy"], unexpected_field=1)
    with pytest.raises(ValidationError):
        ArtifactMetadata(**kwargs)


def test_artifact_metadata_is_frozen():
    metadata = ArtifactMetadata(**_valid_metadata_kwargs())
    with pytest.raises(ValidationError):
        metadata.artifact_type = "changed"


def test_model_dump_json_mode_produces_expected_shape():
    metadata = ArtifactMetadata(**_valid_metadata_kwargs())
    assert metadata.model_dump(mode="json") == {
        "artifact_type": "grading_package",
        "schema_version": "1.0",
        "privacy": {
            "classification": "AI-candidate package metadata",
            "send_to_ai": True,
            "contains_canvas_user_id": False,
            "contains_student_name": False,
            "contains_original_zip_filename": False,
            "contains_download_urls": False,
        },
    }


def test_model_json_schema_includes_nested_privacy_definition():
    schema = ArtifactMetadata.model_json_schema()
    assert "privacy" in schema["properties"]
    defs = schema.get("$defs", schema.get("definitions", {}))
    assert "PrivacyClassification" in defs


def test_module_5_fixture_matches_expected_synthetic_content_and_is_unchanged():
    """Pins the exact synthetic fixture content, guarding against this
    increment accidentally modifying it."""
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        fixture_data = json.load(handle)
    assert fixture_data == {
        "module": {"number": "5.1", "purpose": "Prepare AI-candidate source copy"},
        "privacy": {
            "classification": "AI-candidate package metadata",
            "contains_canvas_user_id": False,
            "contains_student_name": False,
            "contains_original_zip_filename": False,
            "contains_download_urls": False,
        },
        "submission": {"anonymous_label": "submission_002", "selected_attempt": 1},
        "package": {
            "candidate_root": "synthetic_fixture_workspace/submission_002/ai_candidate",
            "source_file_count": 1,
            "comments_removed": True,
            "known_identifiers_redacted": True,
            "human_review_required": True,
            "approved_for_ai": False,
            "files": ["main.cpp"],
        },
        "warnings": [],
    }


def test_module_5_fixture_is_not_falsely_accepted_as_artifact_metadata():
    """The current Module 5.1 manifest shape has no artifact_type or
    schema_version, and carries fields ArtifactMetadata does not define.
    It must not be loadable as ArtifactMetadata; historical-shape
    normalization is out of scope for this increment."""
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        fixture_data = json.load(handle)
    with pytest.raises(ValidationError):
        ArtifactMetadata.model_validate(fixture_data)
