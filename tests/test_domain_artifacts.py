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

import copy
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

NON_BOOLEAN_VALUES = ["true", "false", 1, 0, None]
NON_BOOLEAN_IDS = ["str_true", "str_false", "one", "zero", "none"]


@pytest.fixture
def module_5_1_fixture_data() -> dict:
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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
    """List item 12: send_to_ai=True with all four assertions present and
    exactly False is declared AI-safe."""
    privacy = PrivacyClassification(**_valid_privacy_kwargs())
    assert privacy.is_declared_ai_safe is True


def test_declared_ai_safe_fails_closed_when_zero_contains_fields_present():
    """List item 11: send_to_ai=True with zero contains_* assertions present
    is no longer declared AI-safe under the fail-closed policy."""
    privacy = PrivacyClassification(classification="x", send_to_ai=True)
    assert privacy.is_declared_ai_safe is False


def test_declared_ai_safe_fails_closed_when_only_a_subset_of_contains_fields_present():
    """List item 11: a subset of contains_* assertions present (and false)
    is no longer sufficient; missing assertions are still never invented as
    False, they simply keep the declaration from being declared AI-safe."""
    privacy = PrivacyClassification(
        classification="AI-candidate package metadata",
        send_to_ai=True,
        contains_canvas_user_id=False,
    )
    assert privacy.is_declared_ai_safe is False
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


# ---------------------------------------------------------------------------
# ArtifactMetadata: Module 5.1 historical normalization (list items 3-10)
# ---------------------------------------------------------------------------


def test_canonical_artifact_metadata_input_still_loads():
    """List item 1: canonical input is unaffected by adding the historical
    normalization path."""
    metadata = ArtifactMetadata(**_valid_metadata_kwargs())
    assert metadata.artifact_type == "grading_package"
    assert metadata.schema_version == "1.0"


def test_canonical_input_still_forbids_unknown_fields():
    """List item 2."""
    kwargs = _valid_metadata_kwargs()
    kwargs["unexpected_field"] = 1
    with pytest.raises(ValidationError):
        ArtifactMetadata(**kwargs)


def test_module_5_1_fixture_normalizes_successfully(module_5_1_fixture_data):
    """List items 3-4: the unchanged synthetic fixture loads via
    model_validate and normalizes to the exact expected shape. The fixture's
    approved_for_ai is False, so the result is not declared AI-safe."""
    metadata = ArtifactMetadata.model_validate(module_5_1_fixture_data)
    assert metadata.artifact_type == "ai_candidate_package_manifest"
    assert metadata.schema_version == "prototype-module-5.1"
    assert (
        metadata.privacy.classification
        == module_5_1_fixture_data["privacy"]["classification"]
    )
    assert metadata.privacy.send_to_ai is False
    assert metadata.privacy.contains_canvas_user_id is False
    assert metadata.privacy.contains_student_name is False
    assert metadata.privacy.contains_original_zip_filename is False
    assert metadata.privacy.contains_download_urls is False
    assert metadata.privacy.is_declared_ai_safe is False


def test_module_5_1_variant_with_approved_for_ai_true_is_declared_ai_safe(
    module_5_1_fixture_data,
):
    """List item 5: approved_for_ai=True, with all four contains_* already
    False in the fixture, normalizes to a declared-AI-safe result."""
    variant = copy.deepcopy(module_5_1_fixture_data)
    variant["package"]["approved_for_ai"] = True
    metadata = ArtifactMetadata.model_validate(variant)
    assert metadata.privacy.send_to_ai is True
    assert metadata.privacy.is_declared_ai_safe is True


@pytest.mark.parametrize("bad_value", NON_BOOLEAN_VALUES, ids=NON_BOOLEAN_IDS)
def test_historical_approved_for_ai_rejects_non_boolean_values(
    module_5_1_fixture_data, bad_value
):
    """List item 6."""
    variant = copy.deepcopy(module_5_1_fixture_data)
    variant["package"]["approved_for_ai"] = bad_value
    with pytest.raises(ValidationError):
        ArtifactMetadata.model_validate(variant)


def test_historical_approved_for_ai_missing_key_is_rejected(module_5_1_fixture_data):
    """List item 6 (missing-key case)."""
    variant = copy.deepcopy(module_5_1_fixture_data)
    del variant["package"]["approved_for_ai"]
    with pytest.raises(ValidationError):
        ArtifactMetadata.model_validate(variant)


@pytest.mark.parametrize("field", CONTAINS_FIELDS)
def test_historical_contains_field_missing_is_rejected(module_5_1_fixture_data, field):
    """List item 7 (missing-field case): historical contains_* fields are
    required, unlike PrivacyClassification's own generally-optional
    contains_* fields."""
    variant = copy.deepcopy(module_5_1_fixture_data)
    del variant["privacy"][field]
    with pytest.raises(ValidationError):
        ArtifactMetadata.model_validate(variant)


@pytest.mark.parametrize("field", CONTAINS_FIELDS)
@pytest.mark.parametrize("bad_value", NON_BOOLEAN_VALUES, ids=NON_BOOLEAN_IDS)
def test_historical_contains_field_rejects_non_boolean_values(
    module_5_1_fixture_data, field, bad_value
):
    """List item 7 (present-but-wrong-type case)."""
    variant = copy.deepcopy(module_5_1_fixture_data)
    variant["privacy"][field] = bad_value
    with pytest.raises(ValidationError):
        ArtifactMetadata.model_validate(variant)


@pytest.mark.parametrize("field", CONTAINS_FIELDS)
def test_historical_manifest_with_a_true_contains_field_remains_loadable_but_not_declared_ai_safe(
    module_5_1_fixture_data, field
):
    """List item 8: a true contains_* assertion is structurally valid (not a
    ValidationError) but the result is never declared AI-safe."""
    variant = copy.deepcopy(module_5_1_fixture_data)
    variant["package"]["approved_for_ai"] = True
    variant["privacy"][field] = True
    metadata = ArtifactMetadata.model_validate(variant)
    assert metadata.privacy.is_declared_ai_safe is False


def test_unrecognized_dictionary_with_a_privacy_key_is_not_normalized():
    """List item 9: a dictionary that merely has a "privacy" key, without the
    module/package markers, is not treated as a Module 5.1 manifest and
    instead fails ordinary canonical validation."""
    arbitrary = {
        "privacy": {"classification": "x", "send_to_ai": False},
        "something_else": 1,
    }
    with pytest.raises(ValidationError):
        ArtifactMetadata.model_validate(arbitrary)


def test_dictionary_with_non_5_1_module_number_is_not_normalized(
    module_5_1_fixture_data,
):
    """List item 9: module.number values other than "5.1" do not trigger
    normalization."""
    variant = copy.deepcopy(module_5_1_fixture_data)
    variant["module"]["number"] = "6"
    with pytest.raises(ValidationError):
        ArtifactMetadata.model_validate(variant)


def test_dictionary_missing_package_block_is_not_normalized(module_5_1_fixture_data):
    """List item 9: a missing package object fails recognition cleanly (no
    crash) and falls through to ordinary canonical validation, which also
    rejects it."""
    variant = copy.deepcopy(module_5_1_fixture_data)
    del variant["package"]
    with pytest.raises(ValidationError):
        ArtifactMetadata.model_validate(variant)


def test_module_5_fixture_matches_expected_synthetic_content_and_is_unchanged():
    """List item 10: pins the exact synthetic fixture content, guarding
    against this increment accidentally modifying it."""
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
