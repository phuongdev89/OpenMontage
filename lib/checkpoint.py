"""Checkpoint writer/reader for pipeline state persistence.

Each stage writes a checkpoint after completion. The orchestrator uses
checkpoints to resume pipelines and to present state at human checkpoints.
"""

from __future__ import annotations

import json
import hashlib
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

from schemas.artifacts import ARTIFACT_NAMES, validate_artifact

# All known stages across all pipelines (used only for artifact name lookup).
ALL_KNOWN_STAGES = frozenset([
    "research", "proposal", "idea", "script", "scene_plan",
    "assets", "edit", "compose", "publish",
])

# Backward-compatible alias — existing code / tests that import STAGES still work.
# New code should use get_pipeline_stages(pipeline_type) instead.
STAGES = ["research", "proposal", "idea", "script", "scene_plan",
          "assets", "edit", "compose", "publish"]

CANONICAL_STAGE_ARTIFACTS = {
    "research": "research_brief",
    "proposal": "proposal_packet",
    "idea": "brief",
    "script": "script",
    "scene_plan": "scene_plan",
    "assets": "asset_manifest",
    "edit": "edit_decisions",
    "compose": "render_report",
    "publish": "publish_log",
}

# Additional artifacts that may be produced alongside canonical ones.
# These are not stage-defining but are required by governance contracts.
SUPPLEMENTARY_ARTIFACTS = {
    "source_media_review",  # Required before first planning stage when user media exists
    "final_review",         # Required by compose stage before presenting to user
    "video_analysis_brief", # Reference-video grounding artifact carried alongside stages
}

# Manual distribution milestone; deliberately excluded from production stage
# order so automated pipelines still finish at publish.
MANUAL_POST_STAGES = frozenset({'posted'})


def get_pipeline_stages(pipeline_type: str | None) -> list[str]:
    """Return the ordered stage list for a specific pipeline.

    Falls back to STAGES (deterministic canonical order) when pipeline_type
    is not provided or the manifest cannot be loaded.

    Previous versions used a set intersection here, which produced
    nondeterministic ordering. The fallback now uses a stable list.
    """
    if pipeline_type is None:
        # Deterministic canonical fallback — sorted to ensure stable ordering
        import logging
        logging.getLogger(__name__).warning(
            "get_pipeline_stages called without pipeline_type — "
            "using canonical fallback order. Pass pipeline_type for correctness."
        )
        return list(STAGES)

    try:
        from lib.pipeline_loader import load_pipeline_readonly, get_stage_order
        manifest = load_pipeline_readonly(pipeline_type)
        return get_stage_order(manifest)
    except (FileNotFoundError, Exception):
        # Graceful fallback: return all known stages in canonical order
        return list(STAGES)

CHECKPOINT_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "schemas"
    / "checkpoints"
    / "checkpoint.schema.json"
)

# Canonical project root. Checkpoints, artifacts, and the project marker all
# live under PROJECTS_DIR/<project_id>/ — this is the location the Backlot
# board watches. Callers may still pass a different pipeline_dir (tests do),
# but production runs should use the default.
from lib.paths import PROJECTS_DIR  # noqa: E402  (single source of truth)

PROJECT_MARKER_FILENAME = "project.json"
HISTORY_DIRNAME = "history"


class CheckpointValidationError(ValueError):
    """Raised when a checkpoint or its canonical artifacts are invalid."""


def _validate_style_playbook(style_playbook: str | None) -> None:
    """Fail closed when a checkpoint names a visual identity that cannot load."""

    if style_playbook is None:
        return
    try:
        from styles.playbook_loader import list_playbooks, load_playbook

        load_playbook(style_playbook)
    except Exception as exc:
        try:
            available = list_playbooks()
        except Exception:
            available = []
        raise CheckpointValidationError(
            f"Unknown or invalid style_playbook {style_playbook!r}. "
            f"Available playbooks: {available}. Underlying error: {exc}"
        ) from exc


@lru_cache(maxsize=1)
def _load_checkpoint_schema() -> dict[str, Any]:
    with open(CHECKPOINT_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _validate_artifacts_for_stage(
    stage: str,
    status: str,
    artifacts: dict[str, Any],
) -> None:
    # Valid stages come from the pipeline manifest (get_pipeline_stages), which
    # can declare stages beyond the 9 canonical ones (e.g. character-animation's
    # `character_design`/`rig_plan`, screen-demo's `real_capture`). Those have no
    # canonical artifact, so look it up defensively — a missing entry means the
    # stage simply has no required artifact, not a crash.
    required_artifact = CANONICAL_STAGE_ARTIFACTS.get(stage)
    if (
        required_artifact is not None
        and status in {"completed", "awaiting_human"}
        and required_artifact not in artifacts
    ):
        raise CheckpointValidationError(
            f"Stage {stage!r} with status {status!r} must include "
            f"canonical artifact {required_artifact!r}"
        )

    for artifact_name, artifact_data in artifacts.items():
        if artifact_name not in ARTIFACT_NAMES:
            continue
        if not isinstance(artifact_data, dict):
            raise CheckpointValidationError(
                f"Artifact {artifact_name!r} must be a JSON object matching its schema"
            )
        try:
            validate_artifact(artifact_name, artifact_data)
        except Exception as exc:
            raise CheckpointValidationError(
                f"Artifact {artifact_name!r} failed schema validation: {exc}"
            ) from exc


def validate_checkpoint(checkpoint: dict[str, Any]) -> None:
    """Validate checkpoint structure and canonical artifact payloads.

    Uses pipeline_type (if present) to resolve the valid stage list.
    Falls back to ALL_KNOWN_STAGES when pipeline_type is absent.
    """
    stage = checkpoint.get("stage")
    status = checkpoint.get("status")
    artifacts = checkpoint.get("artifacts")
    pipeline_type = checkpoint.get("pipeline_type")

    valid_stages = (
        set(get_pipeline_stages(pipeline_type)) | MANUAL_POST_STAGES if pipeline_type
        else ALL_KNOWN_STAGES | MANUAL_POST_STAGES
    )

    if not isinstance(stage, str) or stage not in valid_stages:
        raise CheckpointValidationError(
            f"Invalid stage: {stage!r} for pipeline {pipeline_type!r}. "
            f"Valid stages: {sorted(valid_stages)}"
        )
    if not isinstance(status, str):
        raise CheckpointValidationError(f"Invalid status: {status!r}")
    if not isinstance(artifacts, dict):
        raise CheckpointValidationError("Checkpoint artifacts must be a dictionary")

    _validate_artifacts_for_stage(stage, status, artifacts)
    if stage == 'posted':
        from lib.posting_status import validate_posted_checkpoint
        validate_posted_checkpoint(checkpoint)

    try:
        jsonschema.validate(instance=checkpoint, schema=_load_checkpoint_schema())
    except jsonschema.ValidationError as exc:
        raise CheckpointValidationError(f"Checkpoint failed schema validation: {exc.message}") from exc


def _resolve_project_dir(pipeline_dir: Path, project_id: str) -> Path:
    """Resolve the timestamped project directory for a given project_id.

    Looks for an existing directory matching ``*_<project_id>`` under
    ``pipeline_dir``. Falls back to ``pipeline_dir / project_id`` for
    legacy (non-timestamped) directories and for callers that pass a fully
    resolved path as ``project_id``.
    """
    # Fast path: exact match (legacy layout or already resolved).
    exact = pipeline_dir / project_id
    if exact.exists():
        return exact
    # Glob for timestamped layout: YYYY-MM-DD_HH-MM-SS_<project_id>
    matches = sorted(pipeline_dir.glob(f"*_{project_id}"))
    if matches:
        return matches[-1]  # Latest timestamp wins if multiple exist.
    return exact  # Will not exist yet; callers handle mkdir.


def _checkpoint_path(project_dir: Path, stage: str) -> Path:
    return project_dir / f"checkpoint_{stage}.json"


def init_project(
    project_id: str,
    *,
    title: str,
    pipeline_type: str,
    pipeline_dir: Optional[Path] = None,
    style_playbook: Optional[str] = None,
) -> Path:
    """Initialize a project workspace with the canonical layout + marker file.

    Creates projects/YYYY-MM-DD_HH-MM-SS_<project_id>/ with the standard
    subdirectories and writes project.json — the marker the Backlot board uses
    to render a project's identity and stage rail before the first checkpoint
    exists.

    Idempotent: re-running preserves the original created_at and merges fields.
    Returns the project directory.
    """
    _validate_style_playbook(style_playbook)
    from lib.output_formats import configured_output_formats
    output_formats = configured_output_formats()
    from lib.approval_config import configured_stage_approvals
    configured_policy = configured_stage_approvals(pipeline_type)
    configured_policy["authorized_at"] = datetime.now(timezone.utc).isoformat()
    base = pipeline_dir or PROJECTS_DIR
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    project_dir = base / f"{ts}_{project_id}"
    for sub in (
        "artifacts",
        "assets/images",
        "assets/video",
        "assets/audio",
        "assets/music",
        "renders",
    ):
        (project_dir / sub).mkdir(parents=True, exist_ok=True)

    marker_path = project_dir / PROJECT_MARKER_FILENAME
    marker: dict[str, Any] = {}
    if marker_path.exists():
        try:
            with open(marker_path, encoding="utf-8") as f:
                marker = json.load(f)
        except (json.JSONDecodeError, OSError):
            marker = {}

    marker.setdefault("version", "1.0")
    marker.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    marker.setdefault("output_video_formats", output_formats)
    marker.setdefault("approval_policy", configured_policy)
    marker["project_id"] = project_id
    marker["title"] = title
    marker["pipeline_type"] = pipeline_type
    if style_playbook is not None:
        marker["style_playbook"] = style_playbook

    with open(marker_path, "w", encoding="utf-8") as f:
        json.dump(marker, f, indent=2)

    return project_dir


def authorize_auto_approval(
    pipeline_dir: Path,
    project_id: str,
    *,
    authorization_text: str,
) -> Path:
    """Record an explicit user instruction to auto-approve gates for a project.

    This records authorization provenance; it never marks a human as having
    reviewed or approved an individual stage.
    """
    if not authorization_text.strip():
        raise ValueError("authorization_text must preserve the user's instruction")
    project_dir = _resolve_project_dir(pipeline_dir, project_id)
    marker_path = project_dir / PROJECT_MARKER_FILENAME
    if not marker_path.exists():
        raise CheckpointValidationError(
            f"Project {project_id!r} is not initialized; call init_project() first."
        )
    try:
        with open(marker_path, encoding="utf-8") as f:
            marker = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise CheckpointValidationError(
            f"Cannot read project marker for {project_id!r}: {exc}"
        ) from exc
    if not isinstance(marker, dict) or marker.get("project_id") != project_id:
        raise CheckpointValidationError(
            f"Project marker identity does not match {project_id!r}."
        )

    selected_mode = (marker.get('approval_policy') or {}).get('execution_mode')
    if selected_mode in {'manual_all', 'concept_only'}:
        raise CheckpointValidationError('An explicit approval mode is active. Use set_approval_mode() only after a direct user instruction to change it.')
    existing_policy = _auto_approval_policy(marker)
    if existing_policy and existing_policy["authorization_text"] == authorization_text.strip():
        return marker_path
    marker["approval_policy"] = {
        "mode": "auto_approved",
        "authorization_source": "user_instruction",
        "authorization_text": authorization_text.strip(),
        "authorized_at": datetime.now(timezone.utc).isoformat(),
    }
    tmp_path = marker_path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(marker, f, indent=2, ensure_ascii=False)
    import os
    os.replace(tmp_path, marker_path)
    return marker_path


def revoke_auto_approval(pipeline_dir: Path, project_id: str) -> Path:
    """Revoke a project's previously recorded automatic approval policy."""
    project_dir = _resolve_project_dir(pipeline_dir, project_id)
    marker_path = project_dir / PROJECT_MARKER_FILENAME
    if not marker_path.exists():
        raise CheckpointValidationError(
            f"Project {project_id!r} is not initialized; call init_project() first."
        )
    try:
        with open(marker_path, encoding="utf-8") as f:
            marker = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise CheckpointValidationError(
            f"Cannot read project marker for {project_id!r}: {exc}"
        ) from exc
    if not isinstance(marker, dict) or marker.get("project_id") != project_id:
        raise CheckpointValidationError(
            f"Project marker identity does not match {project_id!r}."
        )
    policy = marker.get("approval_policy")
    if isinstance(policy, dict) and policy.get("mode") == "auto_approved":
        policy["mode"] = "revoked"
        policy["revoked_at"] = datetime.now(timezone.utc).isoformat()
    tmp_path = marker_path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(marker, f, indent=2, ensure_ascii=False)
    import os
    os.replace(tmp_path, marker_path)
    return marker_path


def set_approval_mode(pipeline_dir: Path, project_id: str, *, mode: str, authorization_text: str) -> Path:
    """Persist the user's first-question choice for this initialized project."""
    if mode not in {'manual_all', 'concept_only', 'full_auto'}:
        raise ValueError('Unknown approval mode')
    if not authorization_text.strip():
        raise ValueError('Preserve the exact user selection')
    project_dir = _resolve_project_dir(pipeline_dir, project_id)
    marker_path = project_dir / PROJECT_MARKER_FILENAME
    if not marker_path.is_file():
        raise CheckpointValidationError('Project must be initialized before setting approval mode.')
    marker = json.loads(marker_path.read_text(encoding='utf-8'))
    if marker.get('project_id') != project_id:
        raise CheckpointValidationError('Project marker identity mismatch.')
    old = marker.get('approval_policy') or {}
    if old.get('execution_mode') == mode and old.get('authorization_text') == authorization_text.strip() and old.get('mode') != 'revoked':
        return marker_path
    marker['approval_policy'] = {
        'mode': 'manual_all' if mode == 'manual_all' else 'auto_approved',
        'execution_mode': mode,
        'authorization_source': 'user_instruction',
        'authorization_text': authorization_text.strip(),
        'authorized_at': datetime.now(timezone.utc).isoformat(),
    }
    marker.pop('concept_approval', None)
    temporary = marker_path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding='utf-8')
    import os
    os.replace(temporary, marker_path)
    return marker_path


def _concept_fingerprint(artifacts: dict, style_playbook: str | None) -> str | None:
    proposal = artifacts.get('proposal_packet')
    if isinstance(proposal, dict):
        selected = proposal.get('selected_concept') or {}
        concept_id = selected.get('concept_id')
        option = next((c for c in proposal.get('concept_options', []) if c.get('id') == concept_id), None)
        if not concept_id or option is None:
            return None
        value = {'selected': selected, 'option': option, 'style_playbook': style_playbook}
    elif isinstance(artifacts.get('brief'), dict):
        value = {'brief': artifacts['brief'], 'style_playbook': style_playbook}
    else:
        return None
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def record_concept_approval(pipeline_dir: Path, project_id: str, *, artifacts: dict, approval_text: str) -> Path:
    """Record an explicit human concept choice/approval, never stage approval."""
    if not approval_text.strip():
        raise ValueError('Preserve the exact human concept approval')
    project_dir = _resolve_project_dir(pipeline_dir, project_id)
    path = project_dir / PROJECT_MARKER_FILENAME
    if not path.is_file():
        raise CheckpointValidationError('Project must be initialized first.')
    marker = json.loads(path.read_text(encoding='utf-8'))
    if marker.get('project_id') != project_id:
        raise CheckpointValidationError('Project marker identity mismatch.')
    policy = _auto_approval_policy(marker)
    if not policy or policy.get('execution_mode') != 'concept_only':
        raise CheckpointValidationError('Concept approval requires concept_only mode.')
    fingerprint = _concept_fingerprint(artifacts, marker.get('style_playbook'))
    if not fingerprint:
        raise CheckpointValidationError('Concept approval requires the exact selected proposal concept or brief.')
    marker['concept_approval'] = {'fingerprint': fingerprint, 'approval_text': approval_text.strip(),
                                  'approved_at': datetime.now(timezone.utc).isoformat()}
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding='utf-8')
    import os
    os.replace(temporary, path)
    return path


def _concept_auto_allowed(marker: dict, stage: str, artifacts: dict, project_dir: Path) -> bool:
    if stage == 'research':
        return True
    approval = marker.get('concept_approval') or {}
    if not approval.get('approval_text') or not approval.get('approved_at'):
        return False
    selected_artifacts = artifacts
    if stage not in {'proposal', 'idea'}:
        selected_artifacts = {}
        for predecessor in ('proposal', 'idea'):
            path = _checkpoint_path(project_dir, predecessor)
            if path.is_file():
                selected_artifacts = json.loads(path.read_text(encoding='utf-8')).get('artifacts') or {}
                if _concept_fingerprint(selected_artifacts, marker.get('style_playbook')):
                    break
    fingerprint = _concept_fingerprint(selected_artifacts, marker.get('style_playbook'))
    return bool(fingerprint and fingerprint == approval.get('fingerprint'))


def _auto_approval_policy(marker: Any) -> dict[str, str] | None:
    if not isinstance(marker, dict):
        return None
    policy = marker.get("approval_policy")
    if (
        isinstance(policy, dict)
        and policy.get("mode") == "auto_approved"
        and policy.get('execution_mode') in (None, 'full_auto', 'concept_only')
        and policy.get("authorization_source") == "user_instruction"
        and isinstance(policy.get("authorization_text"), str)
        and policy.get("authorization_text").strip()
        and isinstance(policy.get("authorized_at"), str)
    ):
        return policy
    return None


def _stage_requires_approval(pipeline_type: Optional[str], stage: str) -> Optional[bool]:
    """Read human_approval_default for a stage from its pipeline manifest.

    Returns None when the stage isn't declared in the manifest or no
    pipeline_type was given — the caller then falls back to the value the
    agent passed in.

    A *provided but unknown* pipeline_type raises: a typo must not silently
    disable gate enforcement (fail-closed, not fail-open). Other manifest
    load failures are logged and fall back — a corrupt manifest shouldn't
    strand an otherwise-valid run, but the degradation must be visible.
    """
    if not pipeline_type or pipeline_type == "unknown":
        return None
    from lib.pipeline_loader import get_stage_human_approval_default, load_pipeline_readonly
    try:
        manifest = load_pipeline_readonly(pipeline_type)
    except FileNotFoundError:
        raise CheckpointValidationError(
            f"Unknown pipeline_type {pipeline_type!r} — cannot resolve gate "
            f"policy for stage {stage!r}. Check the spelling against "
            f"pipeline_defs/*.yaml."
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Gate policy unavailable for pipeline %r (%s) — falling back to "
            "the caller's human_approval_required flag.", pipeline_type, exc,
        )
        return None
    return get_stage_human_approval_default(manifest, stage)


def _enforce_stage_prerequisites(
    pipeline_dir: Path,
    project_id: str,
    pipeline_type: str | None,
    stage: str,
    status: str,
) -> None:
    """Require completed, approved predecessors before advancing a stage.

    ``in_progress`` and failure heartbeats remain writable so an operator can
    inspect or resume a broken run. Only lifecycle advancement
    (``awaiting_human``/``completed``) is gated.
    """

    if status not in {"awaiting_human", "completed"}:
        return
    if not pipeline_type or pipeline_type == "unknown":
        return

    stages = get_pipeline_stages(pipeline_type)
    if stage not in stages:
        return

    incomplete: list[str] = []
    unapproved: list[str] = []
    project_dir = _resolve_project_dir(pipeline_dir, project_id)
    marker = None
    marker_path = project_dir / PROJECT_MARKER_FILENAME
    if marker_path.exists():
        try:
            with open(marker_path, encoding="utf-8") as handle:
                marker = json.load(handle)
        except (OSError, json.JSONDecodeError):
            marker = None
    auto_policy = marker.get("approval_policy") if isinstance(marker, dict) else None
    if not isinstance(auto_policy, dict):
        auto_policy = None
    for predecessor in stages[: stages.index(stage)]:
        path = _checkpoint_path(project_dir, predecessor)
        if not path.exists():
            incomplete.append(predecessor)
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                checkpoint = json.load(handle)
            validate_checkpoint(checkpoint)
        except (OSError, json.JSONDecodeError, CheckpointValidationError):
            incomplete.append(predecessor)
            continue
        if (
            checkpoint.get("project_id") != project_id
            or checkpoint.get("pipeline_type") != pipeline_type
            or checkpoint.get("stage") != predecessor
        ):
            incomplete.append(predecessor)
            continue
        if checkpoint.get("status") != "completed":
            incomplete.append(predecessor)
            continue
        predecessor_gate = bool(_stage_requires_approval(pipeline_type, predecessor) or checkpoint.get('human_approval_required'))
        if auto_policy and auto_policy.get('execution_mode') == 'stage_config':
            saved = (auto_policy.get('stage_approvals') or {}).get(predecessor)
            if type(saved) is not bool:
                unapproved.append(predecessor)
                continue
            predecessor_gate = saved
        if predecessor_gate and not checkpoint.get(
            "human_approved"
        ):
            resolution = checkpoint.get("approval_resolution", {})
            auto_authorized = bool(
                auto_policy
                and auto_policy.get("authorization_source") == "user_instruction"
                and resolution.get("type") == "auto_authorized"
                and resolution.get("authorization_text")
                == auto_policy.get("authorization_text")
                and resolution.get("authorized_at")
                == auto_policy.get("authorized_at")
            )
            if not auto_authorized:
                unapproved.append(predecessor)

    if incomplete or unapproved:
        details = []
        if incomplete:
            details.append(f"incomplete or missing: {incomplete}")
        if unapproved:
            details.append(f"completed without required approval: {unapproved}")
        raise CheckpointValidationError(
            f"PREREQUISITE VIOLATION: stage {stage!r} cannot advance; "
            + "; ".join(details)
            + f". Pipeline order: {stages}."
        )


def _archive_superseded_checkpoint(path: Path, stage: str) -> None:
    """Copy an existing checkpoint into history/ before it is overwritten.

    Preserves the full run record: stage re-runs (script v1 → v2) and gate
    transitions (awaiting_human → completed) remain reconstructable. Repeated
    in_progress refreshes are NOT archived — they are partial-progress
    heartbeats, not versions.

    Archiving is best-effort and must never crash a checkpoint write: the
    Backlot watcher may hold the file open (Windows denies renames of open
    files), so we copy rather than move, and swallow archival I/O failures.
    """
    if not path.exists():
        return
    try:
        with open(path, encoding="utf-8") as f:
            existing = json.load(f)
    except (json.JSONDecodeError, OSError):
        existing = {}
    if existing.get("status") == "in_progress":
        return

    try:
        import shutil
        stamp = str(existing.get("timestamp", ""))
        safe_stamp = "".join(c for c in stamp if c.isalnum()) or f"{path.stat().st_mtime_ns}"
        history_dir = path.parent / HISTORY_DIRNAME
        history_dir.mkdir(parents=True, exist_ok=True)
        target = history_dir / f"checkpoint_{stage}_{safe_stamp}.json"
        if target.exists():
            target = history_dir / f"checkpoint_{stage}_{safe_stamp}_{path.stat().st_mtime_ns}.json"
        shutil.copyfile(path, target)
    except OSError:
        import logging
        logging.getLogger(__name__).warning(
            "Could not archive superseded checkpoint %s to history/", path
        )


def _decision_log_path(project_dir: Path) -> Path:
    return project_dir / "decision_log.json"


def _merge_decision_log(
    pipeline_dir: Path, project_id: str, new_log: dict[str, Any]
) -> None:
    """Append new decisions to the project-level decision log.

    Each stage may produce decisions. This function merges them into a
    single cumulative file so reviewers and the bench can inspect the
    full audit trail.
    """
    path = _decision_log_path(_resolve_project_dir(pipeline_dir, project_id))
    if path.exists():
        with open(path, encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {
            "version": "1.0",
            "project_id": project_id,
            "decisions": [],
        }

    existing_ids = {d["decision_id"] for d in existing.get("decisions", [])}
    for decision in new_log.get("decisions", []):
        if decision.get("decision_id") not in existing_ids:
            existing["decisions"].append(decision)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def write_checkpoint(
    pipeline_dir: Path,
    project_id: str,
    stage: str,
    status: str,
    artifacts: dict[str, Any],
    *,
    pipeline_type: Optional[str] = None,
    style_playbook: Optional[str] = None,
    checkpoint_policy: str = "guided",
    human_approval_required: bool = False,
    human_approved: bool = False,
    review: Optional[dict] = None,
    cost_snapshot: Optional[dict] = None,
    error: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Path:
    """Write a checkpoint file for a pipeline stage."""
    # Backfill identity fields from the project marker so omitted kwargs
    # cannot bypass either gate enforcement or style validation.
    project_dir = _resolve_project_dir(pipeline_dir, project_id)
    marker_path = project_dir / PROJECT_MARKER_FILENAME
    marker = None
    if marker_path.exists():
        try:
            with open(marker_path, encoding="utf-8") as f:
                marker = json.load(f)
        except (json.JSONDecodeError, OSError):
            marker = None
    if isinstance(marker, dict):
        if not pipeline_type and marker.get("pipeline_type"):
            pipeline_type = marker["pipeline_type"]
        if not style_playbook and marker.get("style_playbook"):
            style_playbook = marker["style_playbook"]
    auto_policy = _auto_approval_policy(marker)
    execution_mode = (marker.get('approval_policy') or {}).get('execution_mode') if isinstance(marker, dict) else None
    configured_gate = None
    if execution_mode == 'stage_config' and stage not in MANUAL_POST_STAGES:
        policy = marker['approval_policy']
        approvals = policy.get('stage_approvals')
        if not isinstance(approvals, dict) or type(approvals.get(stage)) is not bool:
            raise CheckpointValidationError(f'Invalid or missing saved approval setting for {stage!r}.')
        configured_gate = approvals[stage]
        auto_policy = None if configured_gate else policy
    if execution_mode == 'concept_only' and auto_policy and not _concept_auto_allowed(marker, stage, artifacts, project_dir):
        auto_policy = None
    _validate_style_playbook(style_playbook)

    valid_stages = (
        set(get_pipeline_stages(pipeline_type)) | MANUAL_POST_STAGES if pipeline_type
        else ALL_KNOWN_STAGES | MANUAL_POST_STAGES
    )
    if stage not in valid_stages:
        raise ValueError(
            f"Invalid stage: {stage!r} for pipeline {pipeline_type!r}. "
            f"Valid stages: {sorted(valid_stages)}"
        )

    # --- Gate enforcement (GI-4) ---
    # The manifest remains the source of which stages are human-gated. A
    # project-level user authorization may resolve those gates automatically,
    # but is recorded separately and never changes human_approved to True.
    #
    # Enforcement happens at write time only: pre-existing checkpoints written
    # before gating (or by hand) still read as completed — deliberate
    # back-compat so in-flight and legacy projects keep resuming.
    manifest_gate = _stage_requires_approval(pipeline_type, stage) if stage not in MANUAL_POST_STAGES else False
    gated = (bool(manifest_gate) or human_approval_required or execution_mode == 'manual_all'
             or (execution_mode == 'concept_only' and
                 (stage in {'proposal', 'idea'} or (stage != 'research' and not auto_policy))))
    if configured_gate is not None:
        gated = configured_gate
        human_approval_required = configured_gate
    if stage in MANUAL_POST_STAGES:
        # Production auto-approval never marks uploads as done. Each platform
        # must carry a manual UI confirmation and URL in posted_log.
        auto_policy = None
        gated = False
        human_approval_required = False
        human_approved = False
        predecessor = read_checkpoint(pipeline_dir, project_id, 'publish')
        if not predecessor or predecessor.get('status') != 'completed':
            raise CheckpointValidationError('PREREQUISITE VIOLATION: posted requires completed publish.')
    if gated:
        human_approval_required = True
        if status == "completed" and not human_approved and not auto_policy:
            gate_source = (
                'saved NEED_APPROVE_' + stage.upper() + '=true'
                if configured_gate is True
                else 'project approval mode manual_all'
                if execution_mode == 'manual_all'
                else 'project concept_only mode requires approval of the exact current concept'
                if execution_mode == 'concept_only' and not auto_policy
                else f"human_approval_default: true in the {pipeline_type!r} manifest"
                if manifest_gate
                else "human_approval_required=True was passed by the caller"
            )
            raise CheckpointValidationError(
                f"GATE VIOLATION: stage {stage!r} requires human approval "
                f"({gate_source}) but status='completed' was written without "
                f"human_approved=True. Correct protocol: write "
                f"status='awaiting_human', present the artifact summary to the "
                f"user, END YOUR TURN, and only after the user approves "
                f"re-write with status='completed', human_approved=True."
            )

    _enforce_stage_prerequisites(
        pipeline_dir,
        project_id,
        pipeline_type,
        stage,
        status,
    )

    checkpoint = {
        "version": "1.0",
        "project_id": project_id,
        "pipeline_type": pipeline_type or "unknown",
        "stage": stage,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checkpoint_policy": checkpoint_policy,
        "human_approval_required": human_approval_required,
        "human_approved": human_approved,
        "artifacts": artifacts,
    }
    if (gated or configured_gate is False) and status == "completed" and auto_policy and not human_approved:
        checkpoint["approval_resolution"] = {
            "type": "auto_authorized",
            "authorization_source": auto_policy["authorization_source"],
            "authorization_text": auto_policy["authorization_text"],
            "authorized_at": auto_policy["authorized_at"],
        }
    if style_playbook is not None:
        checkpoint["style_playbook"] = style_playbook
    if review is not None:
        checkpoint["review"] = review
    if cost_snapshot is not None:
        checkpoint["cost_snapshot"] = cost_snapshot
    if error is not None:
        checkpoint["error"] = error
    if metadata is not None:
        checkpoint["metadata"] = metadata

    # Merge decision_log: if this checkpoint carries new decisions,
    # append them to the project-level decision log file, then write the
    # reference back into relevant artifacts so downstream consumers can find it.
    if "decision_log" in artifacts and isinstance(artifacts["decision_log"], dict):
        _merge_decision_log(pipeline_dir, project_id, artifacts["decision_log"])
        log_ref = str(_decision_log_path(project_dir))

        # Write decision_log_ref into proposal_packet and render_report
        # artifacts if they are present in this checkpoint.
        for artifact_key in ("proposal_packet", "render_report"):
            if artifact_key in artifacts and isinstance(artifacts[artifact_key], dict):
                plan_or_top = artifacts[artifact_key]
                # proposal_packet stores it under production_plan
                if artifact_key == "proposal_packet":
                    plan = plan_or_top.get("production_plan")
                    if isinstance(plan, dict):
                        plan["decision_log_ref"] = log_ref
                else:
                    plan_or_top["decision_log_ref"] = log_ref

    validate_checkpoint(checkpoint)

    path = _checkpoint_path(project_dir, stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Serialize to a temp file first so a mid-write failure (disk full,
    # unserializable metadata) can never leave the stage with a truncated
    # current checkpoint; then archive the superseded file and swap in the
    # new one atomically.
    tmp_path = path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2)
    # Preserve run history: a superseded completed/awaiting_human checkpoint
    # is copied to history/ (stage versioning, gate audit trail, replay).
    _archive_superseded_checkpoint(path, stage)
    import os
    os.replace(tmp_path, path)

    return path


def read_checkpoint(
    pipeline_dir: Path, project_id: str, stage: str
) -> Optional[dict[str, Any]]:
    """Read a checkpoint file. Returns None if not found."""
    path = _checkpoint_path(_resolve_project_dir(pipeline_dir, project_id), stage)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        checkpoint = json.load(f)
    validate_checkpoint(checkpoint)
    return checkpoint


def get_latest_checkpoint(
    pipeline_dir: Path, project_id: str
) -> Optional[dict[str, Any]]:
    """Find the most recent checkpoint for a project (by file mtime)."""
    project_dir = _resolve_project_dir(pipeline_dir, project_id)
    if not project_dir.exists():
        return None

    checkpoints = sorted(
        project_dir.glob("checkpoint_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not checkpoints:
        return None

    with open(checkpoints[0], encoding="utf-8") as f:
        checkpoint = json.load(f)
    validate_checkpoint(checkpoint)
    return checkpoint


def get_completed_stages(
    pipeline_dir: Path, project_id: str, pipeline_type: str | None = None
) -> list[str]:
    """Return list of stages that have a completed checkpoint.

    When pipeline_type is provided, only checks stages defined in that
    pipeline's manifest — preventing false positives from leftover
    checkpoints of a different pipeline type.
    """
    stages_to_check = get_pipeline_stages(pipeline_type)
    completed = []
    for stage in stages_to_check:
        cp = read_checkpoint(pipeline_dir, project_id, stage)
        if cp and cp.get("status") == "completed":
            completed.append(stage)
    return completed


def get_next_stage(
    pipeline_dir: Path, project_id: str, pipeline_type: str | None = None
) -> Optional[str]:
    """Determine the next stage to run based on completed checkpoints.

    Uses pipeline-specific stage order so that pipelines with different
    stage sequences (e.g. cinematic vs explainer) progress correctly.
    """
    stages = get_pipeline_stages(pipeline_type) if pipeline_type else STAGES
    completed = set(get_completed_stages(pipeline_dir, project_id, pipeline_type))
    for stage in stages:
        if stage not in completed:
            return stage
    return None
