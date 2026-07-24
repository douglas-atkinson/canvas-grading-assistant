"""Canonical, current-version artifact-metadata contracts.

This module defines the first two shared domain models accepted in
OD-001_DOMAIN_MODEL_LIBRARY.md and ARTIFACT_CONTRACTS.md: PrivacyClassification
and ArtifactMetadata. They are the canonical *future* contract only. They do
not yet load any existing prototype artifact, and they are not yet integrated
with module_5_1_prepare_ai_copy.py or module_6_build_grading_package.py.
Historical-shape normalization is deliberately out of scope here and belongs
in a later, explicitly scoped integration increment.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


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
        """True only when send_to_ai is exactly True and every contains_*
        assertion that is present (not None) is exactly False.

        Missing (None) contains_* assertions are never invented or assumed
        to be False; they simply do not, by themselves, disqualify the
        declaration. This is a declarative check only - see the class
        docstring. It must never be treated as a substitute for the
        recursive structural AI-safety scan.
        """
        if self.send_to_ai is not True:
            return False
        for assertion in (
            self.contains_canvas_user_id,
            self.contains_student_name,
            self.contains_original_zip_filename,
            self.contains_download_urls,
        ):
            if assertion is not None and assertion is not False:
                return False
        return True


class ArtifactMetadata(BaseModel):
    """Canonical future metadata envelope for one persisted artifact.

    Intentionally minimal for this increment: artifact_type, schema_version,
    and a nested PrivacyClassification. No timestamp, hash, or other
    envelope field is added here merely because ARCHITECTURE.md shows one in
    a recommended future envelope; those remain out of scope until a
    concrete, tested need is identified.

    No existing prototype artifact (including Module 5.1's
    module_5_ai_package_manifest.json) currently carries artifact_type or
    schema_version, so this model does not attempt to load one directly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    artifact_type: str
    schema_version: str
    privacy: PrivacyClassification

    @field_validator("artifact_type", "schema_version", mode="after")
    @classmethod
    def _require_nonempty_trimmed(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must be a nonempty string")
        return trimmed
