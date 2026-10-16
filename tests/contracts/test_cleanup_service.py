"""Tests for backlot cleanup classification, dry-run, and secure execution."""
from __future__ import annotations

import pytest
from backlot.cleanup import (
    check_cleanup_eligibility,
    classify_project_files,
    preview_cleanup,
    execute_cleanup,
)
from backlot.copywriter import CopywriterError
from lib.checkpoint import init_project, write_checkpoint
from tests.contracts.test_phase0_contracts import sample_artifact


def _create_mock_project(tmp_path, project_id="mock-clean"):
    project_dir = init_project(
        project_id,
        title="Mock Clean Project",
        pipeline_type="animation",
        pipeline_dir=tmp_path,
        style_playbook="math-detective-reference-q16",
    )
    # Write stages
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

    # Create dummy files
    # Preserved
    (project_dir / "decision_log.json").write_text('{"decisions": []}', encoding="utf-8")
    (project_dir / "events.jsonl").write_text('{"tool": "init"}\n', encoding="utf-8")
    conv_dir = project_dir / "exports" / "conversation"
    conv_dir.mkdir(parents=True, exist_ok=True)
    (conv_dir / "chat.md").write_text("# Chat", encoding="utf-8")
    (conv_dir / "chat.json").write_text("{}", encoding="utf-8")
    thumb_dir = project_dir / "exports" / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    (thumb_dir / "hero.png").write_bytes(b"thumb_image_bytes")

    # Deletable
    video_dir = project_dir / "exports" / "video"
    video_dir.mkdir(parents=True, exist_ok=True)
    (video_dir / "video-landscape.mp4").write_bytes(b"dummy_mp4_bytes_123456789")
    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    (audio_dir / "scene1.wav").write_bytes(b"dummy_wav_bytes_123456")
    (project_dir / "index.tsx").write_text("export const Root = () => null;", encoding="utf-8")

    return project_dir


def test_cleanup_ineligible_without_posted_checkpoint(tmp_path):
    project_dir = _create_mock_project(tmp_path)
    with pytest.raises(CopywriterError, match="chưa hoàn tất stage Đã đăng"):
        check_cleanup_eligibility(project_dir)


def test_cleanup_ineligible_with_partial_confirmation(tmp_path):
    project_dir = _create_mock_project(tmp_path)
    posted_log = {
        "youtube": {"confirmed": True, "url": "https://www.youtube.com/watch?v=123", "confirmed_at": "2026-10-16T00:00:00Z", "source": "backlot_manual"},
        "facebook": {"confirmed": False, "url": "", "confirmed_at": None, "source": "backlot_manual"},
    }
    write_checkpoint(
        tmp_path, project_dir.name, "posted", "awaiting_human",
        {"posted_log": posted_log},
        pipeline_type="animation",
    )
    with pytest.raises(CopywriterError, match="chưa hoàn tất stage Đã đăng"):
        check_cleanup_eligibility(project_dir)


def test_cleanup_preview_and_execution_success(tmp_path):
    project_dir = _create_mock_project(tmp_path)
    posted_log = {
        "youtube": {"confirmed": True, "url": "https://www.youtube.com/watch?v=123", "confirmed_at": "2026-10-16T00:00:00Z", "source": "backlot_manual"},
        "facebook": {"confirmed": True, "url": "https://www.facebook.com/share/v/123/", "confirmed_at": "2026-10-16T00:00:00Z", "source": "backlot_manual"},
    }
    write_checkpoint(
        tmp_path, project_dir.name, "posted", "completed",
        {"posted_log": posted_log},
        pipeline_type="animation",
    )

    preview = preview_cleanup(project_dir)
    assert preview["already_cleaned"] is False
    assert preview["files_freed"] == 3  # video.mp4, scene1.wav, index.tsx
    assert preview["bytes_freed"] > 0
    assert any(f["path"] == "exports/video/video-landscape.mp4" for f in preview["deleted_files"])
    assert any(f["path"] == "exports/thumbnails/hero.png" for f in preview["kept_files"])

    # Execution with wrong revision fails
    with pytest.raises(CopywriterError, match="thay đổi sau khi xem trước"):
        execute_cleanup(project_dir, "bad-revision")

    # Execution with valid revision succeeds
    res = execute_cleanup(project_dir, preview["plan_revision"])
    assert res["status"] == "completed"
    assert res["files_freed"] == 3

    # Verify deleted files are gone
    assert not (project_dir / "exports" / "video" / "video-landscape.mp4").exists()
    assert not (project_dir / "audio" / "scene1.wav").exists()
    assert not (project_dir / "index.tsx").exists()

    # Verify preserved files remain
    assert (project_dir / "project.json").exists()
    assert (project_dir / "decision_log.json").exists()
    assert (project_dir / "exports" / "thumbnails" / "hero.png").exists()
    assert (project_dir / "exports" / "conversation" / "chat.md").exists()
    assert (project_dir / "checkpoint_completed.json").exists()

    # Re-running cleanup fails because it's already cleaned
    with pytest.raises(CopywriterError, match="đã được dọn hoàn tất"):
        execute_cleanup(project_dir, preview["plan_revision"])


def test_classify_never_marks_checkpoints_or_metadata_for_deletion(tmp_path):
    project_dir = _create_mock_project(tmp_path)
    kept, deleted = classify_project_files(project_dir)
    deleted_paths = {f["path"] for f in deleted}
    assert "project.json" not in deleted_paths
    assert "checkpoint_publish.json" not in deleted_paths
    assert "decision_log.json" not in deleted_paths
    assert "exports/conversation/chat.md" not in deleted_paths
    assert "exports/thumbnails/hero.png" not in deleted_paths
