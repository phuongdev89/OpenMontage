"""Tests for the post-cleanup completed checkpoint and completed_record artifact."""
from __future__ import annotations

import pytest
from lib.checkpoint import (
    CheckpointValidationError,
    init_project,
    read_checkpoint,
    write_checkpoint,
)
from tests.contracts.test_phase0_contracts import sample_artifact


def _setup_published_project(tmp_path, project_id="proj-test"):
    init_project(
        project_id,
        title="Test Completed Milestone",
        pipeline_type="animation",
        pipeline_dir=tmp_path,
        style_playbook="math-detective-reference-q16",
    )
    # Write canonical stages up to publish
    for stage, art in [
        ("research", "research_brief"),
        ("proposal", "proposal_packet"),
        ("script", "script"),
        ("scene_plan", "scene_plan"),
        ("assets", "asset_manifest"),
        ("edit", "edit_decisions"),
        ("compose", "render_report"),
        ("publish", "publish_log"),
    ]:
        data = sample_artifact(art)
        if art == "edit_decisions":
            data = {**data, "render_runtime": "remotion"}
        write_checkpoint(
            tmp_path, project_id, stage, "completed",
            {art: data},
            pipeline_type="animation",
            style_playbook="math-detective-reference-q16",
            human_approved=True,
        )


def _sample_valid_record(project_id="proj-test"):
    posted_log = {
        "youtube": {"confirmed": True, "url": "https://www.youtube.com/watch?v=123", "confirmed_at": "2026-10-16T00:00:00Z", "source": "backlot_manual"},
        "facebook": {"confirmed": True, "url": "https://www.facebook.com/share/v/123/", "confirmed_at": "2026-10-16T00:00:00Z", "source": "backlot_manual"},
    }
    return {
        "version": "1.0",
        "project_id": project_id,
        "cleaned_at": "2026-10-16T04:00:00Z",
        "stage_snapshots": {
            "research": {"status": "completed", "human_approved": True},
            "script": {"status": "completed", "human_approved": True},
            "publish": {"status": "completed", "human_approved": True},
            "posted": {"status": "completed", "human_approved": False},
        },
        "posted_links": posted_log,
        "display_data": {
            "title": "Test Completed Milestone",
            "script": {"version": "1.0", "title": "Script", "sections": []},
            "storyboard": {"scenes": []},
            "prompts": [
                {
                    "category": "thumbnail",
                    "content": "A colorful 16:9 thumbnail prompt",
                    "provider": "image-generate",
                    "model": "gpt-image-2",
                    "source_ref": "publish_log.json",
                }
            ],
            "thumbnail_path": "exports/thumbnails/thumb.png",
            "posting_copy": {"title": "Title", "description": "Desc", "caption": "Cap"},
        },
        "cleanup_manifest": {
            "bytes_before": 1000000,
            "bytes_after": 50000,
            "bytes_freed": 950000,
            "files_count_before": 50,
            "files_count_after": 10,
            "files_freed": 40,
            "kept_files": [{"path": "project.json", "size": 500, "category": "metadata"}],
            "deleted_files": [{"path": "video.mp4", "size": 950000, "category": "rendered_video", "deleted_at": "2026-10-16T04:00:00Z"}],
        },
    }


def test_completed_requires_posted_completed(tmp_path):
    _setup_published_project(tmp_path)
    with pytest.raises(CheckpointValidationError, match="PREREQUISITE VIOLATION: completed requires completed posted stage"):
        write_checkpoint(
            tmp_path, "proj-test", "completed", "completed",
            {"completed_record": {"some": "data"}},
            pipeline_type="animation",
        )


def test_completed_requires_both_youtube_and_facebook_confirmed(tmp_path):
    _setup_published_project(tmp_path)
    posted_log = {
        "youtube": {"confirmed": True, "url": "https://www.youtube.com/watch?v=123", "confirmed_at": "2026-10-16T00:00:00Z", "source": "backlot_manual"},
        "facebook": {"confirmed": False, "url": "", "confirmed_at": None, "source": "backlot_manual"},
    }
    write_checkpoint(
        tmp_path, "proj-test", "posted", "awaiting_human",
        {"posted_log": posted_log},
        pipeline_type="animation",
    )
    with pytest.raises(CheckpointValidationError, match="PREREQUISITE VIOLATION"):
        write_checkpoint(
            tmp_path, "proj-test", "completed", "completed",
            {"completed_record": {"some": "data"}},
            pipeline_type="animation",
        )


def test_completed_checkpoint_write_and_read_success(tmp_path):
    _setup_published_project(tmp_path)
    posted_log = {
        "youtube": {"confirmed": True, "url": "https://www.youtube.com/watch?v=123", "confirmed_at": "2026-10-16T00:00:00Z", "source": "backlot_manual"},
        "facebook": {"confirmed": True, "url": "https://www.facebook.com/share/v/123/", "confirmed_at": "2026-10-16T00:00:00Z", "source": "backlot_manual"},
    }
    write_checkpoint(
        tmp_path, "proj-test", "posted", "completed",
        {"posted_log": posted_log},
        pipeline_type="animation",
    )

    record = _sample_valid_record("proj-test")
    path = write_checkpoint(
        tmp_path, "proj-test", "completed", "completed",
        {"completed_record": record},
        pipeline_type="animation",
    )
    assert path.name == "checkpoint_completed.json"
    assert path.is_file()

    cp = read_checkpoint(tmp_path, "proj-test", "completed")
    assert cp is not None
    assert cp["stage"] == "completed"
    assert cp["status"] == "completed"
    assert cp["artifacts"]["completed_record"]["project_id"] == "proj-test"
    assert cp["artifacts"]["completed_record"]["cleanup_manifest"]["bytes_freed"] == 950000


def test_completed_checkpoint_rejects_human_approved_flag(tmp_path):
    _setup_published_project(tmp_path)
    posted_log = {
        "youtube": {"confirmed": True, "url": "https://www.youtube.com/watch?v=123", "confirmed_at": "2026-10-16T00:00:00Z", "source": "backlot_manual"},
        "facebook": {"confirmed": True, "url": "https://www.facebook.com/share/v/123/", "confirmed_at": "2026-10-16T00:00:00Z", "source": "backlot_manual"},
    }
    write_checkpoint(
        tmp_path, "proj-test", "posted", "completed",
        {"posted_log": posted_log},
        pipeline_type="animation",
    )
    record = _sample_valid_record("proj-test")
    # write_checkpoint with stage="completed" sets human_approved=False automatically
    cp_path = write_checkpoint(
        tmp_path, "proj-test", "completed", "completed",
        {"completed_record": record},
        pipeline_type="animation",
    )
    cp = read_checkpoint(tmp_path, "proj-test", "completed")
    assert cp["human_approved"] is False
    assert "approval_resolution" not in cp


def test_completed_checkpoint_invalid_record_fails(tmp_path):
    _setup_published_project(tmp_path)
    posted_log = {
        "youtube": {"confirmed": True, "url": "https://www.youtube.com/watch?v=123", "confirmed_at": "2026-10-16T00:00:00Z", "source": "backlot_manual"},
        "facebook": {"confirmed": True, "url": "https://www.facebook.com/share/v/123/", "confirmed_at": "2026-10-16T00:00:00Z", "source": "backlot_manual"},
    }
    write_checkpoint(
        tmp_path, "proj-test", "posted", "completed",
        {"posted_log": posted_log},
        pipeline_type="animation",
    )
    # Missing required field 'cleanup_manifest' in completed_record
    record = _sample_valid_record("proj-test")
    del record["cleanup_manifest"]
    with pytest.raises(CheckpointValidationError):
        write_checkpoint(
            tmp_path, "proj-test", "completed", "completed",
            {"completed_record": record},
            pipeline_type="animation",
        )
