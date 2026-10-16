"""Tests for state derivation and API endpoints of project cleanup."""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient
from backlot.server import create_app
from backlot.state import load_board_state, summarize_project
from lib.checkpoint import init_project, write_checkpoint
from tests.contracts.test_phase0_contracts import sample_artifact


def _setup_full_project(tmp_path, project_id="api-clean-test"):
    project_dir = init_project(
        project_id,
        title="API Clean Test Project",
        pipeline_type="animation",
        pipeline_dir=tmp_path,
        style_playbook="math-detective-reference-q16",
    )
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

    # Posted
    posted_log = {
        "youtube": {"confirmed": True, "url": "https://www.youtube.com/watch?v=CXThytdwhyQ", "confirmed_at": "2026-10-16T00:00:00Z", "source": "backlot_manual"},
        "facebook": {"confirmed": True, "url": "https://www.facebook.com/share/v/1A2zheTqZr/", "confirmed_at": "2026-10-16T00:00:00Z", "source": "backlot_manual"},
    }
    write_checkpoint(
        tmp_path, project_id, "posted", "completed",
        {"posted_log": posted_log},
        pipeline_type="animation",
    )

    # Some mock media
    v_dir = project_dir / "exports" / "video"
    v_dir.mkdir(parents=True, exist_ok=True)
    (v_dir / "video-landscape.mp4").write_bytes(b"dummy_mp4_bytes")
    (project_dir / "index.tsx").write_text("export const Root = () => null;", encoding="utf-8")
    t_dir = project_dir / "exports" / "thumbnails"
    t_dir.mkdir(parents=True, exist_ok=True)
    (t_dir / "thumb.png").write_bytes(b"thumb")

    return project_dir


def test_board_state_uncleaned_vs_cleaned(tmp_path):
    project_dir = _setup_full_project(tmp_path)
    state_before = load_board_state(project_dir)
    assert state_before["is_cleaned"] is False
    assert state_before["embeds"] is None
    assert len(state_before["media"]["renders"]) > 0

    # Summary before
    summary_before = summarize_project(project_dir)
    assert summary_before["is_cleaned"] is False

    # Execute cleanup via module
    from backlot.cleanup import preview_cleanup, execute_cleanup
    preview = preview_cleanup(project_dir)
    execute_cleanup(project_dir, preview["plan_revision"])

    # State after
    state_after = load_board_state(project_dir)
    assert state_after["is_cleaned"] is True
    assert state_after["completed_record"] is not None
    assert state_after["embeds"] is not None
    assert state_after["embeds"]["youtube"]["embed_url"] == "https://www.youtube-nocookie.com/embed/CXThytdwhyQ"
    assert "https://www.facebook.com/plugins/video.php" in state_after["embeds"]["facebook"]["embed_url"]
    assert len(state_after["media"]["renders"]) == 0
    # Stage rail has completed stage
    assert any(s["name"] == "completed" and s["status"] == "completed" for s in state_after["stages"])

    # Summary after
    summary_after = summarize_project(project_dir)
    assert summary_after["is_cleaned"] is True
    assert summary_after["bytes_freed"] > 0


def test_cleanup_api_endpoints(tmp_path, monkeypatch):
    project_dir = _setup_full_project(tmp_path)
    monkeypatch.setattr("backlot.server.PROJECTS_DIR", tmp_path)

    app = create_app()
    with TestClient(app) as client:
        # Preview endpoint
        r_prev = client.get(f"/api/project/{project_dir.name}/cleanup/preview")
        assert r_prev.status_code == 200
        data = r_prev.json()
        assert data["already_cleaned"] is False
        assert "plan_revision" in data
        assert data["files_freed"] > 0

        # Execute endpoint without origin or bad origin
        r_exec_no_origin = client.post(
            f"/api/project/{project_dir.name}/cleanup/execute",
            json={"expected_revision": data["plan_revision"]},
            headers={"origin": "https://evil.com"},
        )
        assert r_exec_no_origin.status_code == 403

        # Execute endpoint with valid revision and same origin
        r_exec = client.post(
            f"/api/project/{project_dir.name}/cleanup/execute",
            json={"expected_revision": data["plan_revision"]},
            headers={"origin": "http://testserver"},
        )
        assert r_exec.status_code == 200
        exec_data = r_exec.json()
        assert exec_data["status"] == "completed"

        # Preview again reports already_cleaned
        r_prev2 = client.get(f"/api/project/{project_dir.name}/cleanup/preview")
        assert r_prev2.status_code == 200
        assert r_prev2.json()["already_cleaned"] is True
