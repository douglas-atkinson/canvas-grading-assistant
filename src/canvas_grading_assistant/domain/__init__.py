"""Shared domain models.

See ARTIFACT_CONTRACTS.md and OD-001_DOMAIN_MODEL_LIBRARY.md for the accepted
extraction order and modeling-library decision. PrivacyClassification and
ArtifactMetadata are the first models introduced under this decision.
"""
from __future__ import annotations

from canvas_grading_assistant.domain.artifacts import (
    ArtifactMetadata,
    PrivacyClassification,
)

__all__ = ["ArtifactMetadata", "PrivacyClassification"]
