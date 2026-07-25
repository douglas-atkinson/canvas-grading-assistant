"""Canonical, current-version artifact-metadata contracts.

This module defines the first two shared domain models accepted in
OD-001_DOMAIN_MODEL_LIBRARY.md and ARTIFACT_CONTRACTS.md: PrivacyClassification
and ArtifactMetadata. The canonical ArtifactMetadata input remains
artifact_type/schema_version/privacy, with unknown fields forbidden.

ArtifactMetadata additionally recognizes and normalizes one historical shape:
Module 5.1's module_5_ai_package_manifest.json (see
_normalize_module_5_1_manifest below). This normalization extracts and
validates ArtifactMetadata fields only. It does not validate the complete
Module 5.1 manifest (source-file lists, anonymous label, warnings, and so on)
and must not be treated as a replacement for module_6_build_grading_package.py's
validate_ai_manifest(), which remains the authoritative validator for the
full manifest before a grading package is built. Neither module_5_1_
prepare_ai_copy.py nor module_6_build_grading_package.py is modified or
called by this normalization; it is not yet integrated with either module.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class PrivacyClassification(BaseModel):
    """A producer's declared privacy classification for one artifact.

    This is one of three independent, defense-in-depth layers documented in
    ARTIFACT_CONTRACTS.md and OD-001_DOMAIN_MODEL_LIBRARY.md: a declared
    classification (this model), explicit content assertions (the
    contains_* fields), and a recursive, assert_ai_safe-style structural
    scan of an artifact's actual contents. This model expresses only the
    first two layers.

    IMPORTANT: successfully validating an instance of this model, and
    `is_declared_ai_safe` returning True, is a *declarative* statement only.
    Neither is equivalent to, and neither may replace, the recursive
    structural privacy scan that must still run independently against the
    real payload before any transmission to a model provider. A schema-valid,
    declared-safe PrivacyClassification does not certify that the artifact it
    is attached to is actually safe to send.

    A PrivacyClassification with send_to_ai=False is a completely valid
    description of a private artifact; validity is independent of whether
    the artifact is AI-safe.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    classification: str
    send_to_ai: bool
    contains_canvas_user_id: bool | None = None
    contains_student_name: bool | None = None
    contains_original_zip_filename: bool | None = None
    contains_download_urls: bool | None = None

    @field_validator("classification", mode="after")
    @classmethod
    def _require_nonempty_trimmed_classification(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("classification must be a nonempty string")
        return trimmed

    @property
    def is_declared_ai_safe(self) -> bool:
        """True only when send_to_ai is exactly True AND all four contains_*
        assertions are present (not None) AND each of them is exactly False.

        This fails closed: any missing contains_* assertion, any assertion
        that is exactly True, or send_to_ai that is not exactly True all
        make this False. A PrivacyClassification may still be structurally
        valid (see the class docstring) while omitting one or more contains_*
        assertions - that is a legitimate historical shape - but it is never
        reported as declared AI-safe unless every assertion is explicitly
        known and explicitly False. This is a declarative check only; it
        must never be treated as a substitute for the recursive structural
        AI-safety scan.
        """
        if self.send_to_ai is not True:
            return False
        assertions = (
            self.contains_canvas_user_id,
            self.contains_student_name,
            self.contains_original_zip_filename,
            self.contains_download_urls,
        )
        return all(assertion is False for assertion in assertions)


class ArtifactMetadata(BaseModel):
    """Canonical future metadata envelope for one persisted artifact.

    The canonical input shape is exactly artifact_type, schema_version, and
    a nested PrivacyClassification; unknown fields are forbidden for that
    canonical shape. No timestamp, hash, or other envelope field is added
    here merely because ARCHITECTURE.md shows one in a recommended future
    envelope; those remain out of scope until a concrete, tested need is
    identified.

    This model additionally recognizes and normalizes one historical shape
    before canonical validation runs: Module 5.1's
    module_5_ai_package_manifest.json (see _looks_like_module_5_1_manifest
    and _normalize_module_5_1_manifest below). Recognition requires a
    top-level module object whose number identifies Module 5.1, plus
    top-level privacy and package objects; an arbitrary dictionary that
    merely happens to contain a "privacy" key is not treated as this
    historical shape. Normalizing this historical shape validates
    ArtifactMetadata's own fields only - it does not validate the complete
    Module 5.1 manifest and must not be treated as a replacement for
    module_6_build_grading_package.py's validate_ai_manifest().
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    artifact_type: str
    schema_version: str
    privacy: PrivacyClassification

    @model_validator(mode="before")
    @classmethod
    def _normalize_historical_shapes(cls, data: Any) -> Any:
        if isinstance(data, dict) and _looks_like_module_5_1_manifest(data):
            return _normalize_module_5_1_manifest(data)
        return data

    @field_validator("artifact_type", "schema_version", mode="after")
    @classmethod
    def _require_nonempty_trimmed(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must be a nonempty string")
        return trimmed


def _looks_like_module_5_1_manifest(data: dict) -> bool:
    """Recognize Module 5.1's module_5_ai_package_manifest.json shape.

    Deliberately conservative: requires a top-level module object identifying
    Module 5.1, plus top-level privacy and package objects. A dictionary that
    merely contains a "privacy" key is not, by itself, recognized - that
    would risk silently reinterpreting an unrelated or malformed canonical
    ArtifactMetadata payload as a historical manifest instead of letting it
    fail canonical validation on its own terms.
    """
    module_block = data.get("module")
    privacy_block = data.get("privacy")
    package_block = data.get("package")
    return (
        isinstance(module_block, dict)
        and module_block.get("number") == "5.1"
        and isinstance(privacy_block, dict)
        and isinstance(package_block, dict)
    )


def _require_literal_bool(container: dict, key: str, location: str) -> bool:
    """Require key to be present in container with a literal True/False.

    Used only for the historical Module 5.1 normalization path, where every
    field being copied is documented as always present and always a literal
    Boolean in the producing module (module_5_1_prepare_ai_copy.py). A
    missing key is rejected here rather than silently defaulting to None or
    False, unlike PrivacyClassification's own optional contains_* fields,
    which intentionally tolerate absence for other, less complete historical
    shapes.
    """
    if key not in container:
        raise ValueError(f"Module 5.1 manifest is missing required {location}.")
    value = container[key]
    if not isinstance(value, bool):
        raise ValueError(f"Module 5.1 manifest {location} must be a literal Boolean.")
    return value


def _normalize_module_5_1_manifest(data: dict) -> dict:
    """Normalize Module 5.1's manifest shape into ArtifactMetadata's fields.

    Field mapping:
      - artifact_type is set to the fixed literal
        "ai_candidate_package_manifest". This identifies the artifact as a
        candidate for the AI-facing pipeline; it does not itself assert that
        the artifact is safe or approved (the historical manifest may carry
        package.approved_for_ai=false, mapped to send_to_ai below).
      - schema_version is set to the fixed literal "prototype-module-5.1"
        (Module 5.1's manifest itself carries no schema_version field).
      - privacy.classification is copied from the historical privacy block.
      - privacy.send_to_ai is copied from package.approved_for_ai. This is
        deliberately NOT inferred from the four contains_* assertions - the
        historical manifest already carries an independent approval signal,
        and that signal must remain independently represented rather than
        collapsed or discarded.
      - each of the four contains_* assertions is copied independently from
        the historical privacy block; none is invented, defaulted, or
        collapsed into another field.

    This only extracts and validates ArtifactMetadata's own fields; it does
    not validate the complete Module 5.1 manifest (source-file lists,
    anonymous label, warnings, and so on) and must not be treated as a
    replacement for validate_ai_manifest().
    """
    privacy_block = data["privacy"]
    package_block = data["package"]

    return {
        "artifact_type": "ai_candidate_package_manifest",
        "schema_version": "prototype-module-5.1",
        "privacy": {
            "classification": privacy_block.get("classification"),
            "send_to_ai": _require_literal_bool(
                package_block, "approved_for_ai", "package.approved_for_ai"
            ),
            "contains_canvas_user_id": _require_literal_bool(
                privacy_block,
                "contains_canvas_user_id",
                "privacy.contains_canvas_user_id",
            ),
            "contains_student_name": _require_literal_bool(
                privacy_block, "contains_student_name", "privacy.contains_student_name"
            ),
            "contains_original_zip_filename": _require_literal_bool(
                privacy_block,
                "contains_original_zip_filename",
                "privacy.contains_original_zip_filename",
            ),
            "contains_download_urls": _require_literal_bool(
                privacy_block, "contains_download_urls", "privacy.contains_download_urls"
            ),
        },
    }
