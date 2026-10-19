"""Unit and integration tests for Backlot Script Calendar sync."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backlot import calendar_sync as cal_mod
from backlot import server as server_mod
from backlot import state as state_mod
from backlot.calendar_sync import (
    CalendarClient,
    CalendarConflictError,
    CalendarLockError,
    CalendarSyncError,
    CalendarTimeoutError,
    format_script_markdown,
    get_default_sync_info,
    project_sync_lock,
    read_sync_state,
    reconcile_unknown_sync,
    resolve_sync_conflict,
    sync_project_to_calendar,
    write_sync_state,
)


@pytest.fixture
def projects_root(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    root.mkdir()
    data_dir = tmp_path / "data" / "calendar_sync"
    data_dir.mkdir(parents=True)

    monkeypatch.setattr(state_mod, "PROJECTS_DIR", root)
    monkeypatch.setattr(server_mod, "PROJECTS_DIR", root)
    monkeypatch.setattr(server_mod, "_summary_cache", {})
    monkeypatch.setattr(server_mod, "_PROJECTS_ROOT_STR", __import__("os").path.normcase(str(root.resolve())))
    monkeypatch.setattr(cal_mod, "get_sync_data_dir", lambda: data_dir)
    return root


@pytest.fixture
def client(projects_root, monkeypatch):
    async def no_watch():
        return None

    monkeypatch.setattr(server_mod, "_watch_projects", no_watch)
    with TestClient(server_mod.create_app()) as c:
        yield c


def _make_sample_project(root: Path, project_id: str = "demo_proj") -> Path:
    proj = root / project_id
    proj.mkdir(parents=True)
    (proj / "artifacts").mkdir()

    script_data = {
        "version": "1.0",
        "title": "Chiếc Đầm Mùa Thu",
        "total_duration_seconds": 30,
        "sections": [
            {
                "id": "hook",
                "label": "Hook 3s",
                "text": "Mọi người có tin chiếc đầm này chưa đến 200k không?",
                "start_seconds": 0,
                "end_seconds": 3,
                "speaker_directions": "Hào hứng, tự nhiên",
            },
            {
                "id": "body",
                "label": "Thân bài",
                "text": "Chất vải voan tơ mềm mại, form dáng chuẩn công sở.",
                "start_seconds": 3,
                "end_seconds": 25,
            },
        ],
    }
    (proj / "artifacts" / "script.json").write_text(json.dumps(script_data), encoding="utf-8")

    publish_log = {
        "metadata": {
            "posting_package": {
                "title": "Chiếc Đầm Mùa Thu Xinh Xắn",
                "caption": "Mẫu đầm siêu xinh dạo phố cuối tuần đây cả nhà ơi! #damxinh #outfit",
                "description": "Chi tiết mẫu đầm mùa thu 2026.",
            }
        },
        "entries": [{"status": "published", "metadata_used": {}}],
    }
    (proj / "artifacts" / "publish_log.json").write_text(json.dumps(publish_log), encoding="utf-8")

    checkpoint = {
        "pipeline_type": "animation",
        "stage": "publish",
        "status": "completed",
        "human_approved": True,
        "timestamp": "2026-10-17T10:00:00Z",
        "artifacts": {"publish_log": "artifacts/publish_log.json"},
    }
    (proj / "checkpoint_publish.json").write_text(json.dumps(checkpoint), encoding="utf-8")

    return proj


def test_format_script_markdown():
    script_data = {
        "title": "Demo Title",
        "sections": [
            {"id": "s1", "label": "Hook", "text": "Hello world", "speaker_directions": "Smiling"},
            {"id": "s2", "label": "Body", "text": "Main content"},
        ],
    }
    md = format_script_markdown(script_data)
    assert "# Demo Title" in md
    assert "## Hook" in md
    assert "> *Smiling*" in md
    assert "Hello world" in md
    assert "## Body" in md
    assert "Main content" in md


def test_sync_project_happy_path(projects_root):
    proj = _make_sample_project(projects_root, "proj_happy")

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.create_campaign.return_value = {"id": "2026-10-18_trang-linh_chiec-dam-mua-thu"}
    mock_client.get_script.return_value = {"content": "", "revision": "rev_001"}
    mock_client.save_script.return_value = {"content": "ok", "revision": "rev_002"}
    mock_client.save_caption.return_value = {"campaign_id": "2026-10-18_trang-linh_chiec-dam-mua-thu"}

    params = {
        "title": "Chiếc Đầm Mùa Thu Xinh Xắn",
        "scheduled_date": "2026-10-18",
        "koc": "Trang Linh",
        "idea": "Đi cà phê cuối tuần",
        "product_url": "https://shopee.vn/product/123",
    }

    result = sync_project_to_calendar(proj, params, client=mock_client)

    assert result["status"] == "DONE"
    assert result["campaign_id"] == "2026-10-18_trang-linh_chiec-dam-mua-thu"
    assert mock_client.create_campaign.called
    assert mock_client.save_script.called
    assert mock_client.save_caption.called

    persisted = read_sync_state(proj)
    assert persisted["status"] == "DONE"
    assert persisted["campaign_id"] == "2026-10-18_trang-linh_chiec-dam-mua-thu"


def test_post_campaign_timeout_and_reconcile(projects_root):
    proj = _make_sample_project(projects_root, "proj_timeout")

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.create_campaign.side_effect = CalendarTimeoutError("Timeout test")

    params = {
        "title": "Video Timeout Test",
        "scheduled_date": "2026-10-19",
    }

    with pytest.raises(CalendarTimeoutError):
        sync_project_to_calendar(proj, params, client=mock_client)

    state = read_sync_state(proj)
    assert state["status"] == "UNKNOWN"

    # Calling sync again without reconcile must fail with 409
    with pytest.raises(CalendarSyncError) as exc_info:
        sync_project_to_calendar(proj, params, client=mock_client)
    assert exc_info.value.status == 409
    assert "UNKNOWN" in str(exc_info.value)

    # Reconcile when campaign was actually created on server
    mock_client.list_campaigns.return_value = [
        {"id": "2026-10-19_video-timeout-test", "title": "Video Timeout Test", "scheduled_date": "2026-10-19"}
    ]

    reconcile_res = reconcile_unknown_sync(proj, client=mock_client)
    assert reconcile_res["reconciled"] is True
    assert reconcile_res["found"] is True
    assert reconcile_res["campaign_id"] == "2026-10-19_video-timeout-test"

    state_after = read_sync_state(proj)
    assert state_after["status"] == "CAMPAIGN_CREATED"
    assert state_after["campaign_id"] == "2026-10-19_video-timeout-test"


def test_reconcile_when_not_found_resets_to_error(projects_root):
    proj = _make_sample_project(projects_root, "proj_not_found")
    write_sync_state(proj, {"status": "UNKNOWN", "title": "Lost Campaign", "scheduled_date": "2026-10-20"})

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.list_campaigns.return_value = []

    res = reconcile_unknown_sync(proj, client=mock_client)
    assert res["reconciled"] is True
    assert res["found"] is False

    state = read_sync_state(proj)
    assert state["status"] == "ERROR"
    assert "không có campaign" in state["error"].lower()


def test_script_conflict_409_and_resolution(projects_root):
    proj = _make_sample_project(projects_root, "proj_conflict")

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.create_campaign.return_value = {"id": "camp_409"}
    mock_client.get_script.return_value = {"content": "Old Remote Content", "revision": "rev_old"}
    mock_client.save_script.side_effect = CalendarConflictError(
        "Revision mismatch",
        remote_content="Remote Edited Content",
        remote_revision="rev_remote_fresh",
    )

    params = {"title": "Conflict Test", "scheduled_date": "2026-10-21"}

    with pytest.raises(CalendarConflictError):
        sync_project_to_calendar(proj, params, client=mock_client)

    state = read_sync_state(proj)
    assert state["status"] == "CONFLICT_409"
    assert state["conflict_detail"]["remote_content"] == "Remote Edited Content"

    # Resolve with overwrite
    mock_client.save_script.side_effect = None
    mock_client.get_script.return_value = {"content": "Remote Edited Content", "revision": "rev_remote_fresh"}
    mock_client.save_script.return_value = {"content": "local overwritten", "revision": "rev_final"}
    mock_client.save_caption.return_value = {"ok": True}

    resolved = resolve_sync_conflict(proj, action="overwrite", client=mock_client)
    assert resolved["status"] == "DONE"


def test_project_sync_lock_concurrency(projects_root):
    proj = _make_sample_project(projects_root, "proj_lock")

    with project_sync_lock(proj):
        with pytest.raises(CalendarLockError):
            with project_sync_lock(proj):
                pass


def test_api_calendar_sync_endpoints(client, projects_root, monkeypatch):
    proj = _make_sample_project(projects_root, "proj_api")

    # 1. Info endpoint
    res_info = client.get(f"/api/project/{proj.name}/calendar-sync/info")
    assert res_info.status_code == 200
    info = res_info.json()
    assert "Chiếc Đầm Mùa Thu" in info["title"]
    assert info["sync_state"]["status"] == "IDLE"

    # 2. Mock sync in start endpoint
    mock_client = MagicMock(spec=CalendarClient)
    mock_client.create_campaign.return_value = {"id": "camp_api_123"}
    mock_client.get_script.return_value = {"content": "", "revision": "r1"}
    mock_client.save_script.return_value = {"content": "", "revision": "r2"}
    mock_client.save_caption.return_value = {"ok": True}

    monkeypatch.setattr(cal_mod, "CalendarClient", lambda base_url: mock_client)

    res_start = client.post(
        f"/api/project/{proj.name}/calendar-sync/start",
        json={
            "title": "API Test Campaign",
            "scheduled_date": "2026-10-22",
            "koc": "Trang Linh",
        },
    )
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "DONE"
    assert res_start.json()["campaign_id"] == "camp_api_123"


def test_retry_after_caption_error_preserves_campaign_id_does_not_duplicate(projects_root):
    """[P1 Fix] When caption fails, retry must NOT call create_campaign again."""
    proj = _make_sample_project(projects_root, "proj_retry")

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.create_campaign.return_value = {"id": "first_campaign_id"}
    mock_client.get_script.return_value = {"content": "", "revision": "rev_1"}
    mock_client.save_script.return_value = {"ok": True}
    mock_client.save_caption.side_effect = CalendarSyncError("Network glitch on caption", 503)

    params = {"title": "Retry Preserves ID", "scheduled_date": "2026-10-23"}

    # First attempt fails on caption
    with pytest.raises(CalendarSyncError, match="Network glitch on caption"):
        sync_project_to_calendar(proj, params, client=mock_client)

    state = read_sync_state(proj)
    assert state["status"] == "ERROR"
    assert state["campaign_id"] == "first_campaign_id"
    assert mock_client.create_campaign.call_count == 1

    # Second attempt: retry after fixing caption error
    mock_client.save_caption.side_effect = None
    mock_client.save_caption.return_value = {"ok": True}

    res2 = sync_project_to_calendar(proj, params, client=mock_client)
    assert res2["status"] == "DONE"
    assert res2["campaign_id"] == "first_campaign_id"
    # CRITICAL: create_campaign was NOT called a second time!
    assert mock_client.create_campaign.call_count == 1
    # CRITICAL [P1]: save_script was NOT called again on caption retry!
    assert mock_client.save_script.call_count == 1
    assert mock_client.save_caption.call_count == 2


def test_url_locked_to_session(projects_root):
    """[P1 Fix] Server URL must be locked to the session once started."""
    proj = _make_sample_project(projects_root, "proj_url_lock")

    client_a = MagicMock(spec=CalendarClient)
    client_a.base_url = "http://server-a.local"
    client_a.list_campaign_ids.return_value = []
    client_a.create_campaign.return_value = {"id": "camp_server_a"}
    client_a.get_script.return_value = {"revision": "r1"}
    client_a.save_script.return_value = {"ok": True}
    client_a.save_caption.return_value = {"ok": True}

    # First run on server A
    sync_project_to_calendar(proj, {"title": "URL Lock", "scheduled_date": "2026-10-23", "calendar_url": "http://server-a.local"}, client=client_a)
    state = read_sync_state(proj)
    assert state["calendar_url"] == "http://server-a.local"

    # Attempting to resume or re-sync with a different URL must resolve back to server-a
    resolved_url = cal_mod.resolve_calendar_url(state, "http://server-b.local")
    assert resolved_url == "http://server-a.local"


def test_snapshot_ids_failure_blocks_post(projects_root):
    """[P1 Fix] If snapshotting existing IDs fails, POST must be blocked."""
    proj = _make_sample_project(projects_root, "proj_snapshot_fail")

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.list_campaign_ids.side_effect = Exception("Cannot read campaigns baseline")

    with pytest.raises(CalendarSyncError, match="Không thể lấy danh sách campaign"):
        sync_project_to_calendar(proj, {"title": "Fail Test", "scheduled_date": "2026-10-23"}, client=mock_client)

    assert mock_client.create_campaign.call_count == 0


def test_resync_from_done_with_conflict_enters_conflict_409(projects_root):
    """[P2 Fix] Resync from DONE hitting 409 must transition state to CONFLICT_409."""
    proj = _make_sample_project(projects_root, "proj_done_conflict")
    write_sync_state(proj, {
        "status": "DONE",
        "campaign_id": "done_camp_conflict",
        "title": "Done Conflict",
        "scheduled_date": "2026-10-27",
    })

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.get_script.return_value = {"content": "Remote Changed", "revision": "rev_conflict"}
    mock_client.save_script.side_effect = CalendarConflictError("Revision mismatch", remote_content="Remote Changed", remote_revision="rev_conflict")

    with pytest.raises(CalendarConflictError):
        sync_project_to_calendar(proj, {"title": "Done Conflict", "scheduled_date": "2026-10-27", "script": "My Local"}, client=mock_client)

    state = read_sync_state(proj)
    assert state["status"] == "CONFLICT_409"
    assert state["conflict_detail"]["remote_content"] == "Remote Changed"


def test_empty_script_with_caption_saves_caption_and_completes_done(projects_root):
    """[P2 Fix] Empty script must not skip caption or prematurely finish."""
    proj = _make_sample_project(projects_root, "proj_empty_script")

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.list_campaign_ids.return_value = []
    mock_client.create_campaign.return_value = {"id": "camp_empty_script"}
    mock_client.save_caption.return_value = {"ok": True}

    params = {
        "title": "Empty Script Title",
        "scheduled_date": "2026-10-28",
        "script": "",
        "caption": "Has Caption Content",
    }

    res = sync_project_to_calendar(proj, params, client=mock_client)
    assert res["status"] == "DONE"
    # save_script was skipped because script is empty
    assert mock_client.save_script.call_count == 0
    # save_caption was executed!
    mock_client.save_caption.assert_called_once_with("camp_empty_script", "Has Caption Content")



def test_reconcile_ignores_pre_existing_campaigns_and_checks_koc(projects_root):
    """[P1 Fix] Reconcile must not misidentify an identical pre-existing task."""
    proj = _make_sample_project(projects_root, "proj_pre_existing")

    mock_client = MagicMock(spec=CalendarClient)
    # Simulate pre-existing task with exact same title and date
    mock_client.list_campaigns.return_value = [
        {"id": "old_existing_task", "title": "Same Title", "scheduled_date": "2026-10-24", "koc": "Trang Linh"}
    ]
    mock_client.list_campaign_ids.return_value = ["old_existing_task"]
    mock_client.create_campaign.side_effect = CalendarTimeoutError("Timeout")

    params = {"title": "Same Title", "scheduled_date": "2026-10-24", "koc": "Trang Linh"}

    with pytest.raises(CalendarTimeoutError):
        sync_project_to_calendar(proj, params, client=mock_client)

    state = read_sync_state(proj)
    assert state["status"] == "UNKNOWN"
    assert state["pre_existing_ids"] == ["old_existing_task"]

    # Server list still only has the old one (POST did NOT succeed on server)
    reconcile_res = reconcile_unknown_sync(proj, client=mock_client)
    assert reconcile_res["reconciled"] is True
    assert reconcile_res["found"] is False
    assert read_sync_state(proj)["status"] == "ERROR"

    # Now simulate server actually created a new one with id "new_created_task"
    write_sync_state(proj, state)  # back to UNKNOWN
    mock_client.list_campaigns.return_value = [
        {"id": "old_existing_task", "title": "Same Title", "scheduled_date": "2026-10-24", "koc": "Trang Linh"},
        {"id": "new_created_task", "title": "Same Title", "scheduled_date": "2026-10-24", "koc": "Trang Linh"},
    ]
    reconcile_res2 = reconcile_unknown_sync(proj, client=mock_client)
    assert reconcile_res2["reconciled"] is True
    assert reconcile_res2["found"] is True
    assert reconcile_res2["campaign_id"] == "new_created_task"


def test_post_failure_unhandled_leaves_unknown_state(projects_root):
    """[P1 Fix] Any network failure or 5xx during POST leaves state as UNKNOWN."""
    proj = _make_sample_project(projects_root, "proj_net_err")

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.list_campaign_ids.return_value = []
    mock_client.create_campaign.side_effect = CalendarSyncError("502 Bad Gateway / Connection reset", 502)

    params = {"title": "Net Error Test", "scheduled_date": "2026-10-25"}

    with pytest.raises(CalendarSyncError):
        sync_project_to_calendar(proj, params, client=mock_client)

    state = read_sync_state(proj)
    assert state["status"] == "UNKNOWN"


def test_conflict_409_blocks_start_cannot_bypass_to_done(projects_root):
    """[P1 Fix] Calling /start while in CONFLICT_409 must NOT bypass to DONE."""
    proj = _make_sample_project(projects_root, "proj_bypass_check")
    write_sync_state(proj, {
        "status": "CONFLICT_409",
        "campaign_id": "camp_conflict_123",
        "title": "Bypass Test",
        "scheduled_date": "2026-10-26",
    })

    mock_client = MagicMock(spec=CalendarClient)

    with pytest.raises(CalendarSyncError) as exc_info:
        sync_project_to_calendar(proj, {"title": "Bypass Test", "scheduled_date": "2026-10-26"}, client=mock_client)

    assert exc_info.value.status == 409
    assert "xung đột" in str(exc_info.value).lower()
    assert read_sync_state(proj)["status"] == "CONFLICT_409"


def test_resync_from_done_updates_script_and_caption(projects_root):
    """[P2 Fix] Syncing again from DONE must actually update script and caption on server."""
    proj = _make_sample_project(projects_root, "proj_done_update")
    write_sync_state(proj, {
        "status": "DONE",
        "campaign_id": "existing_done_camp",
        "title": "Done Title",
        "scheduled_date": "2026-10-27",
    })

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.get_script.return_value = {"content": "Old", "revision": "rev_done_1"}
    mock_client.save_script.return_value = {"ok": True}
    mock_client.save_caption.return_value = {"ok": True}

    params = {
        "title": "Done Title",
        "scheduled_date": "2026-10-27",
        "script": "Updated Script Content",
        "caption": "Updated Caption Content",
    }

    res = sync_project_to_calendar(proj, params, client=mock_client)
    assert res["status"] == "DONE"

    # Both save_script and save_caption must have been called
    mock_client.save_script.assert_called_once_with("existing_done_camp", "Updated Script Content", "rev_done_1")
    mock_client.save_caption.assert_called_once_with("existing_done_camp", "Updated Caption Content")


def test_resync_from_done_caption_failure_retry_does_not_call_script_again(projects_root):
    """[P1 Fix Review 3] When resync from DONE fails on caption, retry must NOT call save_script again."""
    proj = _make_sample_project(projects_root, "proj_resync_retry")
    write_sync_state(proj, {
        "status": "DONE",
        "campaign_id": "done_camp_retry",
        "title": "Done Title",
        "scheduled_date": "2026-10-27",
    })

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.get_script.return_value = {"content": "Old", "revision": "rev_done_1"}
    mock_client.save_script.return_value = {"ok": True}
    mock_client.save_caption.side_effect = CalendarSyncError("Network error on caption", 503)

    params = {
        "title": "Done Title",
        "scheduled_date": "2026-10-27",
        "script": "New Script",
        "caption": "New Caption",
    }

    # First attempt: script succeeds, caption fails
    with pytest.raises(CalendarSyncError, match="Network error on caption"):
        sync_project_to_calendar(proj, params, client=mock_client)

    state = read_sync_state(proj)
    assert state["status"] == "ERROR"
    assert "SCRIPT_SAVED" in state["milestones"]
    assert "CAPTION_SAVED" not in state["milestones"]
    assert mock_client.save_script.call_count == 1
    assert mock_client.save_caption.call_count == 1

    # Second attempt: retry after fixing caption error
    mock_client.save_caption.side_effect = None
    mock_client.save_caption.return_value = {"ok": True}

    res2 = sync_project_to_calendar(proj, params, client=mock_client)
    assert res2["status"] == "DONE"
    # CRITICAL: save_script was NOT called again during retry!
    assert mock_client.save_script.call_count == 1
    assert mock_client.save_caption.call_count == 2


def test_resync_from_done_conflict_409_keep_remote_saves_new_caption_and_completes(projects_root):
    """[P1 Fix Review 3] Resync conflict resolution (keep_remote) must still save new caption and reach DONE."""
    proj = _make_sample_project(projects_root, "proj_resync_conflict_resolve")
    write_sync_state(proj, {
        "status": "DONE",
        "campaign_id": "done_camp_conflict_resolve",
        "title": "Done Conflict Title",
        "scheduled_date": "2026-10-27",
    })

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.get_script.return_value = {"content": "Remote Script", "revision": "rev_conflict"}
    mock_client.save_script.side_effect = CalendarConflictError("Conflict 409", remote_content="Remote Script", remote_revision="rev_conflict")
    mock_client.save_caption.return_value = {"ok": True}

    params = {
        "title": "Done Conflict Title",
        "scheduled_date": "2026-10-27",
        "script": "Local Script",
        "caption": "Local New Caption",
    }

    # Resync hits 409 on script
    with pytest.raises(CalendarConflictError):
        sync_project_to_calendar(proj, params, client=mock_client)

    state = read_sync_state(proj)
    assert state["status"] == "CONFLICT_409"

    # User chooses keep_remote
    resolved = resolve_sync_conflict(proj, action="keep_remote", client=mock_client)
    assert resolved["status"] == "DONE"
    # CRITICAL: save_caption MUST be called with the new caption content!
    mock_client.save_caption.assert_called_once_with("done_camp_conflict_resolve", "Local New Caption")


def test_immutable_title_and_date_on_existing_campaign(projects_root):
    """[P2 Fix Review 3] Reject changing title or scheduled_date once campaign exists."""
    proj = _make_sample_project(projects_root, "proj_immutable")
    write_sync_state(proj, {
        "status": "DONE",
        "campaign_id": "immutable_camp_123",
        "title": "Fixed Title",
        "scheduled_date": "2026-10-27",
    })

    mock_client = MagicMock(spec=CalendarClient)

    # Change title
    with pytest.raises(CalendarSyncError, match="Không thể thay đổi tiêu đề") as e1:
        sync_project_to_calendar(proj, {"title": "New Title", "scheduled_date": "2026-10-27"}, client=mock_client)
    assert e1.value.status == 400

    # Change date
    with pytest.raises(CalendarSyncError, match="Không thể thay đổi ngày lên lịch") as e2:
        sync_project_to_calendar(proj, {"title": "Fixed Title", "scheduled_date": "2026-10-30"}, client=mock_client)
    assert e2.value.status == 400



def test_unpublished_project_blocked(projects_root):
    """Backend must reject project if publish checkpoint is missing."""
    proj = projects_root / "unpub_proj"
    proj.mkdir(parents=True)
    (proj / "artifacts").mkdir()

    with pytest.raises(CalendarSyncError, match="chưa hoàn tất checkpoint publish"):
        sync_project_to_calendar(proj, {"title": "Test", "scheduled_date": "2026-10-28"})


def test_koc_fixed_default_toan_olympic_cung_con(projects_root):
    """KOC must always default to 'Toán Olympic Cùng Con'."""
    proj = _make_sample_project(projects_root, "proj_koc_test")
    info = get_default_sync_info(proj)
    assert info["koc"] == "Toán Olympic Cùng Con"

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.create_campaign.return_value = {"id": "camp_koc_123"}
    mock_client.save_script.return_value = {"ok": True, "revision": "rev1"}
    mock_client.save_caption.return_value = {"ok": True}

    res = sync_project_to_calendar(proj, {"title": "Test KOC", "scheduled_date": "2026-10-30"}, client=mock_client)
    assert res["status"] == "DONE"
    state = read_sync_state(proj)
    assert state["koc"] == "Toán Olympic Cùng Con"
    mock_client.create_campaign.assert_called_once()
    payload = mock_client.create_campaign.call_args[0][0]
    assert payload["koc"] == "Toán Olympic Cùng Con"


def test_live_crud_cycle_against_server():
    """Live verification against http://127.0.0.1:8766 (or 55484): create -> read -> script -> caption -> delete."""
    port = cal_mod.get_calendar_base_url()
    client = CalendarClient(port)
    try:
        health = client.check_health()
        if health.get("status") != "ok":
            pytest.skip(f"Server at {port} is not healthy")
    except Exception:
        pytest.skip(f"Server at {port} is not reachable")

    test_title = f"_test_backlot_sync_{int(__import__('time').time())}"
    test_date = "2026-10-29"

    # 1. Create campaign
    created = client.create_campaign({
        "title": test_title,
        "scheduled_date": test_date,
        "koc": "Test KOC",
        "idea": "Live test automated CRUD verification",
    })
    camp_id = created.get("id")
    assert camp_id is not None

    try:
        # 2. Read back
        detail = client.get_campaign(camp_id)
        assert detail["title"] == test_title

        # 3. Update script with revision guard and read back
        script_resp = client.get_script(camp_id)
        rev = script_resp.get("revision") or ""
        saved_script = client.save_script(camp_id, "# Live Test Script\n\nAutomated script content.", rev)
        assert "revision" in saved_script

        read_script = client.get_script(camp_id)
        assert read_script["content"] == "# Live Test Script\n\nAutomated script content."

        # 4. Update caption and read back
        saved_caption = client.save_caption(camp_id, "Live Test Caption #automated")
        assert saved_caption.get("campaign_id") == camp_id

        read_caption = client.get_caption(camp_id)
        assert read_caption["content"] == "Live Test Caption #automated"

    finally:
        # 5. Clean up: Delete campaign and verify it is gone
        del_res = client.delete_campaign(camp_id)
        assert del_res is not None

        # Independent verification: campaign ID no longer exists in list
        remaining_ids = client.list_campaign_ids()
        assert camp_id not in remaining_ids

        # Direct GET must return 404 (strictly 404)
        with pytest.raises(CalendarSyncError) as exc_info:
            client.get_campaign(camp_id)
        assert exc_info.value.status == 404


def test_browser_calendar_sync_ui(client, projects_root, monkeypatch):
    """Browser Playwright test verifying the Calendar Sync UI elements, submission and update in Backlot."""
    pw_api = pytest.importorskip("playwright.sync_api")
    proj = _make_sample_project(projects_root, "proj_browser")
    ui = Path(__file__).resolve().parents[2] / "backlot/ui"

    # Mock client for server API calls made from browser
    mock_cal_client = MagicMock(spec=CalendarClient)
    mock_cal_client.list_campaign_ids.return_value = []
    mock_cal_client.create_campaign.return_value = {"id": "browser_camp_id_999"}
    mock_cal_client.get_script.return_value = {"content": "", "revision": "r1"}
    mock_cal_client.save_script.return_value = {"ok": True}
    mock_cal_client.save_caption.return_value = {"ok": True}
    monkeypatch.setattr(cal_mod, "CalendarClient", lambda base_url: mock_cal_client)

    with pw_api.sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()

        def serve(route):
            path = route.request.url.split("example.test")[-1]
            if path.startswith("/ui/"):
                file_name = path.split("/")[-1].split("?")[0]
                route.fulfill(body=(ui / file_name).read_text(encoding="utf-8"), content_type="text/javascript")
            elif path.startswith("/api/"):
                response = client.request(
                    route.request.method,
                    path,
                    content=route.request.post_data,
                    headers={"Content-Type": "application/json"},
                )
                route.fulfill(status=response.status_code, body=response.text, content_type="application/json")
            else:
                route.fulfill(body="<html><body></body></html>", content_type="text/html")

        page.route("http://example.test/**", serve)

        page.goto("http://example.test/")
        page.evaluate("""async () => {
            const {renderPublishPackage} = await import('/ui/publish.js');
            window.refresh = async () => {
                const s = await (await fetch('/api/project/proj_browser/state')).json();
                document.body.replaceChildren(renderPublishPackage(s, 'proj_browser', refresh));
            };
            await refresh();
        }""")

        # Verify Calendar Sync card is rendered
        btn = page.get_by_role("button", name="Thêm vào lịch đăng…", exact=True)
        pw_api.expect(btn).to_be_visible()

        # Click to open dialog
        btn.click()
        dialog = page.locator(".calendar-sync-dialog")
        pw_api.expect(dialog).to_be_visible()
        assert page.locator(".calendar-sync-dialog").count() == 1

        # Test backdrop click closes dialog and removes it from DOM
        page.mouse.click(10, 10)
        pw_api.expect(dialog).not_to_be_visible()
        assert page.locator(".calendar-sync-dialog").count() == 0

        # Reopen dialog to continue test - must still be exactly 1 dialog in DOM
        btn.click()
        pw_api.expect(dialog).to_be_visible()
        assert page.locator(".calendar-sync-dialog").count() == 1

        # Verify default title is populated
        title_input = dialog.locator("input[type=text]").first
        pw_api.expect(title_input).to_have_value("Chiếc Đầm Mùa Thu Xinh Xắn")

        # Submit form
        submit_btn = dialog.get_by_role("button", name="Thêm vào lịch đăng", exact=True)
        submit_btn.click()

        # Dialog closes upon success and removes from DOM
        pw_api.expect(dialog).not_to_be_visible()
        assert page.locator(".calendar-sync-dialog").count() == 0

        # Verify card updates to DONE
        success_title = page.locator(".calendar-sync-box strong")
        pw_api.expect(success_title).to_contain_text("Đã thêm vào lịch đăng thành công")

        browser.close()


def test_browser_already_added_button_disabled(client, projects_root, monkeypatch):
    """When a project is already added to the calendar, the button must be disabled with text 'Đã thêm vào lịch đăng'."""
    pw_api = pytest.importorskip("playwright.sync_api")
    proj = _make_sample_project(projects_root, "proj_already_added")
    write_sync_state(proj, {
        "status": "DONE",
        "campaign_id": "existing_camp_888",
        "scheduled_date": "2026-10-25",
        "koc": "Toan_Olympic_Cung_Con",
    })
    ui = Path(__file__).resolve().parents[2] / "backlot/ui"

    mock_cal_client = MagicMock(spec=CalendarClient)
    mock_cal_client.list_campaign_ids.return_value = ["existing_camp_888"]
    mock_cal_client.list_campaigns.return_value = [
        {"id": "existing_camp_888", "title": "Chiếc Đầm Mùa Thu Xinh Xắn", "scheduled_date": "2026-10-25", "koc": "Toan_Olympic_Cung_Con"}
    ]
    monkeypatch.setattr(cal_mod, "CalendarClient", lambda base_url: mock_cal_client)

    with pw_api.sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()

        def serve(route):
            path = route.request.url.split("example.test")[-1]
            if path.startswith("/ui/"):
                file_name = path.split("/")[-1].split("?")[0]
                route.fulfill(body=(ui / file_name).read_text(encoding="utf-8"), content_type="text/javascript")
            elif path.startswith("/api/"):
                response = client.request(
                    route.request.method,
                    path,
                    content=route.request.post_data,
                    headers={"Content-Type": "application/json"},
                )
                route.fulfill(status=response.status_code, body=response.text, content_type="application/json")
            else:
                route.fulfill(body="<html><body></body></html>", content_type="text/html")

        page.route("http://example.test/**", serve)
        page.goto("http://example.test/")
        page.evaluate("""async () => {
            const {renderPublishPackage} = await import('/ui/publish.js');
            const s = await (await fetch('/api/project/proj_already_added/state')).json();
            document.body.replaceChildren(renderPublishPackage(s, 'proj_already_added'));
        }""")

        header_btn = page.get_by_role("button", name="Đã thêm vào lịch đăng", exact=True)
        pw_api.expect(header_btn).to_be_visible()
        pw_api.expect(header_btn).to_be_disabled()

        browser.close()


def test_calendar_sync_calls_content_and_status(projects_root):
    """Step 2 and 3: CalendarClient must invoke update_content and update_status."""
    proj = _make_sample_project(projects_root, "proj_content_status")

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.create_campaign.return_value = {"id": "camp_content_001"}
    mock_client.get_script.return_value = {"content": "", "revision": "rev1"}
    mock_client.save_script.return_value = {"ok": True, "revision": "rev2"}
    mock_client.save_caption.return_value = {"ok": True}
    mock_client.update_content.return_value = {"ok": True}
    mock_client.update_status.return_value = {"ok": True}

    params = {
        "title": "AMO 2022 Grade 2 Question 16",
        "scheduled_date": "2026-10-20",
        "koc": "Toán Olympic Cùng Con",
        "idea": "Bài toán dãy số nhân đôi",
    }
    result = sync_project_to_calendar(proj, params, client=mock_client)

    assert result["status"] == "DONE"
    mock_client.create_campaign.assert_called_once()
    create_args = mock_client.create_campaign.call_args[0][0]
    assert create_args["planned_outfit_count"] == 0
    assert create_args["share_affiliate"] is False
    assert create_args["folder_name"] == "proj_content_status"

    mock_client.update_content.assert_called_once()
    content_args = mock_client.update_content.call_args[0][1]
    assert "youtube_title" in content_args
    assert "youtube_description" in content_args
    assert "facebook_caption" in content_args

    mock_client.update_status.assert_called_once_with("camp_content_001", "CAPTIONED")


def test_calendar_sync_published_links_when_present(projects_root):
    """Step 4: If checkpoint_posted exists, sync published links."""
    proj = _make_sample_project(projects_root, "proj_posted_links")
    posted_data = {
        "platforms": {
            "youtube": {"url": "https://youtu.be/TEST_VID_ID"},
            "facebook": {"url": "https://facebook.com/watch/?v=TEST_FB_ID"},
        }
    }
    (proj / "checkpoint_posted.json").write_text(json.dumps(posted_data), encoding="utf-8")

    mock_client = MagicMock(spec=CalendarClient)
    mock_client.create_campaign.return_value = {"id": "camp_posted_002"}
    mock_client.get_script.return_value = {"content": "", "revision": "rev1"}
    mock_client.save_script.return_value = {"ok": True}
    mock_client.save_caption.return_value = {"ok": True}
    mock_client.update_content.return_value = {"ok": True}
    mock_client.update_status.return_value = {"ok": True}
    mock_client.update_published_links.return_value = {"ok": True}

    params = {
        "title": "AMO 2022 Question 16",
        "scheduled_date": "2026-10-22",
    }
    sync_project_to_calendar(proj, params, client=mock_client)

    mock_client.update_published_links.assert_called_once()
    links = mock_client.update_published_links.call_args[0][1]
    assert any(l["platform"] == "youtube" and "TEST_VID_ID" in l["url"] for l in links)
    assert any(l["platform"] == "facebook" and "TEST_FB_ID" in l["url"] for l in links)


def test_openmontage_calendar_sync_client(projects_root, monkeypatch):
    """Verify openmontage.integrations.calendar_sync.CalendarSyncClient executes all 4 steps."""
    from openmontage.integrations.calendar_sync import CalendarSyncClient
    proj = _make_sample_project(projects_root, "proj_standalone_client")

    posted_data = {
        "platforms": {
            "youtube": {"url": "https://youtu.be/ABC123XYZ"}
        }
    }
    (proj / "checkpoint_posted.json").write_text(json.dumps(posted_data), encoding="utf-8")

    recorded_calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        recorded_calls.append({"url": url, "payload": json})
        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        if "/api/campaigns" in url and not url.endswith(("/content", "/status", "/published-links")):
            resp.json.return_value = {"id": "proj_standalone_client"}
        else:
            resp.json.return_value = {"ok": True}
        return resp

    monkeypatch.setattr("requests.post", fake_post)

    client = CalendarSyncClient(base_url="http://127.0.0.1:8766")
    res = client.sync_project(proj, scheduled_date="2026-10-20")

    assert res["status"] == "CAPTIONED"
    assert res["campaign_id"] == "proj_standalone_client"

    # Verify all 4 endpoint URLs were called
    urls = [c["url"] for c in recorded_calls]
    assert "http://127.0.0.1:8766/api/campaigns" in urls
    assert "http://127.0.0.1:8766/api/campaigns/proj_standalone_client/content" in urls
    assert "http://127.0.0.1:8766/api/campaigns/proj_standalone_client/status" in urls
    assert "http://127.0.0.1:8766/api/campaigns/proj_standalone_client/published-links" in urls


def test_calendar_get_query_apis(monkeypatch):
    """Verify CalendarClient and CalendarSyncClient query GET endpoints."""
    from openmontage.integrations.calendar_sync import CalendarSyncClient

    def fake_get(url, params=None, timeout=None):
        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        if "/api/koc-workflows/" in url:
            resp.json.return_value = {
                "key": "toan_olympic",
                "outfit_mode": "none",
                "task_kind": "animation",
                "video_format": "landscape",
                "default_look_count": 0,
            }
        elif "/schedule-suggestion" in url:
            resp.json.return_value = {
                "campaign_id": "test_camp",
                "suggested_time": "19:30",
                "golden_hours": ["11:45", "19:30", "20:30"],
            }
        elif "/today-check" in url:
            resp.json.return_value = {
                "date": "2026-10-19",
                "total_today": 1,
                "by_status": {"CAPTIONED": 1},
                "campaigns": [{"id": "test_camp", "title": "Test", "status": "CAPTIONED"}],
            }
        elif "/koc-thumbnail/" in url:
            resp.content = b"FAKE_IMAGE_BYTES"
        elif "/api/campaigns" in url:
            resp.json.return_value = [
                {"id": "camp_1", "koc": "Toán Olympic Cùng Con", "title": "Math 1"},
                {"id": "camp_2", "koc": "Other_KOC", "title": "Fashion 1"},
            ]
        return resp

    monkeypatch.setattr("requests.get", fake_get)

    # 1. Test CalendarClient GET methods
    cal_client = CalendarClient("http://127.0.0.1:8766", calendar_dir=False)
    wf = cal_client.get_workflow("Toán Olympic Cùng Con")
    assert wf["video_format"] == "landscape"
    assert wf["outfit_mode"] == "none"

    sugg = cal_client.get_schedule_suggestion("test_camp", "Toán Olympic Cùng Con")
    assert sugg["suggested_time"] == "19:30"
    assert "19:30" in sugg["golden_hours"]

    today = cal_client.get_today_check("Toán Olympic Cùng Con")
    assert today["total_today"] == 1

    thumb = cal_client.get_koc_thumbnail("Toán Olympic Cùng Con")
    assert thumb == b"FAKE_IMAGE_BYTES"

    # 2. Test CalendarSyncClient GET methods
    sync_client = CalendarSyncClient(base_url="http://127.0.0.1:8766")
    wf2 = sync_client.get_workflow("Toán Olympic Cùng Con")
    assert wf2["task_kind"] == "animation"

    koc_camps = sync_client.list_koc_campaigns("Toán Olympic Cùng Con")
    assert len(koc_camps) == 1
    assert koc_camps[0]["id"] == "camp_1"

    sugg2 = sync_client.get_schedule_suggestion("test_camp", "Toán Olympic Cùng Con")
    assert "golden_hours" in sugg2

    today2 = sync_client.get_today_check("Toán Olympic Cùng Con")
    assert today2["date"] == "2026-10-19"

    thumb2 = sync_client.get_koc_thumbnail("Toán Olympic Cùng Con")
    assert thumb2 == b"FAKE_IMAGE_BYTES"




