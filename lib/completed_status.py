"""Validation and utilities for the post-cleanup completed milestone record."""
from __future__ import annotations

from typing import Any
from lib.posting_status import PLATFORMS, validate_post_url


def validate_completed_checkpoint(checkpoint: dict[str, Any]) -> None:
    """Validate structure and provenance of checkpoint_completed.json."""
    from lib.checkpoint import CheckpointValidationError
    from schemas.artifacts import validate_artifact

    if checkpoint.get("stage") != "completed":
        raise CheckpointValidationError("Expected stage 'completed'.")

    # Milestone record uses manual upload & cleanup evidence, not production approval flags.
    if checkpoint.get("approval_resolution") or checkpoint.get("human_approved"):
        raise CheckpointValidationError(
            "completed record uses cleanup provenance, not production approval."
        )

    artifacts = checkpoint.get("artifacts") or {}
    record = artifacts.get("completed_record")

    status = checkpoint.get("status")
    if status in {"completed", "awaiting_human"}:
        if not isinstance(record, dict):
            raise CheckpointValidationError("completed stage requires 'completed_record' artifact.")
        try:
            validate_artifact("completed_record", record)
        except Exception as exc:
            raise CheckpointValidationError(
                f"Artifact 'completed_record' failed schema validation: {exc}"
            ) from exc

        # Verify posted links integrity
        posted_links = record.get("posted_links") or {}
        for platform in PLATFORMS:
            entry = posted_links.get(platform)
            if not isinstance(entry, dict) or not entry.get("confirmed"):
                raise CheckpointValidationError(
                    f"completed_record requires confirmed {platform} publication."
                )
            try:
                validate_post_url(platform, entry.get("url", ""))
            except (ValueError, AttributeError):
                raise CheckpointValidationError(
                    f"completed_record requires a valid {platform} URL."
                ) from None

        # Verify snapshots exist and are dict
        snapshots = record.get("stage_snapshots")
        if not isinstance(snapshots, dict) or not snapshots:
            raise CheckpointValidationError("completed_record requires valid stage_snapshots.")

        manifest = record.get("cleanup_manifest")
        if not isinstance(manifest, dict):
            raise CheckpointValidationError("completed_record requires valid cleanup_manifest.")
