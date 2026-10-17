"""Calendar sync module — integration between Backlot and Script Calendar Management."""
from __future__ import annotations

import contextlib
import json
import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

from backlot.copywriter import CopywriterError
from backlot.file_manager import atomic_bytes
from lib.env_loader import get_env, load_env

logger = logging.getLogger(__name__)

DEFAULT_CALENDAR_URL = "http://127.0.0.1:55484"


class CalendarSyncError(CopywriterError):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message, status)


class CalendarTimeoutError(CalendarSyncError):
    def __init__(self, message: str = "Hết thời gian chờ phản hồi từ Script Calendar."):
        super().__init__(message, 504)


class CalendarConflictError(CalendarSyncError):
    def __init__(self, message: str, remote_content: str = "", remote_revision: str = ""):
        super().__init__(message, 409)
        self.remote_content = remote_content
        self.remote_revision = remote_revision


class CalendarLockError(CalendarSyncError):
    def __init__(self, message: str = "Thao tác đồng bộ lịch đăng đang được thực hiện."):
        super().__init__(message, 409)


def get_calendar_base_url(override_url: Optional[str] = None) -> str:
    if override_url and override_url.strip():
        return override_url.strip().rstrip("/")
    load_env()
    env_url = get_env("SCRIPT_CALENDAR_URL") or get_env("CALENDAR_URL")
    if env_url and env_url.strip():
        return env_url.strip().rstrip("/")
    return DEFAULT_CALENDAR_URL


def resolve_calendar_url(project_state: dict, requested_url: Optional[str] = None) -> str:
    """Lock server URL to existing sync session if one was already started."""
    existing = project_state.get("calendar_url")
    if existing and project_state.get("status") not in ("IDLE", None):
        return existing.rstrip("/")
    return get_calendar_base_url(requested_url)


def get_sync_data_dir() -> Path:
    from backlot.state import REPO_ROOT
    path = REPO_ROOT / "data" / "calendar_sync"
    path.mkdir(parents=True, exist_ok=True)
    return path


def sync_state_path(project: Path) -> Path:
    return get_sync_data_dir() / f"{project.name}.json"


def project_artifact_sync_path(project: Path) -> Path:
    return project / "artifacts" / "calendar_sync.json"


def read_sync_state(project: Path) -> dict:
    primary = sync_state_path(project)
    fallback = project_artifact_sync_path(project)
    target = primary if primary.is_file() else (fallback if fallback.is_file() else None)
    if not target:
        return {
            "project_id": project.name,
            "status": "IDLE",
            "campaign_id": None,
            "last_step": None,
            "milestones": [],
            "updated_at": None,
            "history": [],
        }
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            if "milestones" not in data:
                data["milestones"] = []
            return data
    except (OSError, ValueError):
        pass
    return {
        "project_id": project.name,
        "status": "IDLE",
        "campaign_id": None,
        "last_step": None,
        "milestones": [],
        "updated_at": None,
        "history": [],
    }


def write_sync_state(project: Path, state: dict) -> None:
    state["project_id"] = project.name
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    raw = json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8")
    primary = sync_state_path(project)
    atomic_bytes(primary, raw)
    with contextlib.suppress(OSError):
        project_artifact_sync_path(project).parent.mkdir(parents=True, exist_ok=True)
        atomic_bytes(project_artifact_sync_path(project), raw)


@contextlib.contextmanager
def project_sync_lock(project: Path):
    lock_file = project / "artifacts" / ".calendar_sync.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    file = lock_file.open("a+b")
    try:
        file.seek(0)
        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise CalendarLockError("Tiến trình đồng bộ lịch cho project này đang chạy.")
        else:
            import fcntl
            try:
                fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise CalendarLockError("Tiến trình đồng bộ lịch cho project này đang chạy.")
        try:
            yield
        finally:
            file.seek(0)
            if os.name == "nt":
                import msvcrt
                with contextlib.suppress(OSError):
                    msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                with contextlib.suppress(OSError):
                    fcntl.flock(file, fcntl.LOCK_UN)
    finally:
        file.close()


def is_project_published(project: Path) -> bool:
    from backlot.state import load_board_state
    state = load_board_state(project)
    stages = state.get("stages") or []
    return any(s.get("name") == "publish" and s.get("status") == "completed" for s in stages)


def format_script_markdown(script_data: Optional[dict], title: str = "") -> str:
    if not isinstance(script_data, dict):
        return f"# {title}\n" if title else ""
    t = script_data.get("title") or title or "Script"
    lines = [f"# {t}\n"]
    sections = script_data.get("sections")
    if isinstance(sections, list):
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            header = sec.get("label") or sec.get("id") or "Section"
            text = (sec.get("text") or "").strip()
            speaker = sec.get("speaker_directions")
            lines.append(f"## {header}")
            if speaker:
                lines.append(f"> *{speaker}*\n")
            if text:
                lines.append(f"{text}\n")
    return "\n".join(lines).strip()


def get_default_sync_info(project: Path) -> dict:
    from backlot.state import load_board_state
    state = load_board_state(project)
    package = state.get("publish_package") or {}
    artifacts = state.get("artifacts") or {}

    title = (package.get("title") or state.get("title") or project.name).strip()
    if len(title) > 180:
        title = title[:177] + "..."

    caption = (package.get("caption") or package.get("description") or "").strip()
    script_data = artifacts.get("script")
    script_md = format_script_markdown(script_data, title=title)

    sync_state = read_sync_state(project)
    today = date.today().isoformat()
    published = is_project_published(project)
    active_url = resolve_calendar_url(sync_state)

    return {
        "title": title,
        "scheduled_date": today,
        "koc": "",
        "idea": "",
        "product_url": "",
        "caption": caption,
        "script": script_md,
        "sync_state": sync_state,
        "has_published_checkpoint": published,
        "calendar_url": active_url,
    }


class CalendarClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def check_health(self) -> dict:
        try:
            res = requests.get(f"{self.base_url}/health", timeout=(3, 5))
            if res.ok:
                return res.json()
            raise CalendarSyncError(f"Script Calendar /health trả về lỗi {res.status_code}.", 502)
        except requests.Timeout:
            raise CalendarTimeoutError("Kết nối /health tới Script Calendar quá thời gian.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Không thể kết nối Script Calendar: {e}", 503)

    def list_campaigns(self) -> list[dict]:
        try:
            res = requests.get(f"{self.base_url}/api/campaigns", timeout=(5, 10))
            if res.ok:
                data = res.json()
                return data if isinstance(data, list) else []
            raise CalendarSyncError(f"Lấy danh sách campaign lỗi {res.status_code}.", 502)
        except requests.Timeout:
            raise CalendarTimeoutError("Hết thời gian chờ lấy danh sách campaign.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Lỗi kết nối khi lấy danh sách campaign: {e}", 503)

    def list_campaign_ids(self) -> list[str]:
        campaigns = self.list_campaigns()
        return [c["id"] for c in campaigns if isinstance(c, dict) and c.get("id")]

    def get_campaign(self, identifier: str) -> dict:
        try:
            res = requests.get(f"{self.base_url}/api/campaigns/{identifier}", timeout=(5, 10))
            if res.ok:
                return res.json()
            raise CalendarSyncError(f"Đọc campaign thất bại ({res.status_code}): {res.text}", res.status_code)
        except requests.Timeout:
            raise CalendarTimeoutError("Hết thời gian chờ đọc campaign.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Lỗi kết nối khi đọc campaign: {e}", 503)

    def create_campaign(self, payload: dict) -> dict:
        try:
            res = requests.post(
                f"{self.base_url}/api/campaigns",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=(5, 15),
            )
        except requests.Timeout:
            raise CalendarTimeoutError("POST /api/campaigns hết thời gian chờ.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Lỗi mạng khi tạo campaign: {e}", 503)

        if res.ok:
            return res.json()
        detail = res.text
        with contextlib.suppress(Exception):
            detail = res.json().get("detail", detail)
        raise CalendarSyncError(f"Tạo campaign thất bại ({res.status_code}): {detail}", res.status_code)

    def get_script(self, identifier: str) -> dict:
        try:
            res = requests.get(f"{self.base_url}/api/campaigns/{identifier}/script", timeout=(5, 10))
        except requests.Timeout:
            raise CalendarTimeoutError("Hết thời gian chờ đọc kịch bản.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Lỗi mạng khi đọc kịch bản: {e}", 503)

        if res.ok:
            return res.json()
        raise CalendarSyncError(f"Đọc kịch bản thất bại ({res.status_code}): {res.text}", res.status_code)

    def save_script(self, identifier: str, content: str, revision: str) -> dict:
        try:
            res = requests.put(
                f"{self.base_url}/api/campaigns/{identifier}/script",
                json={"content": content, "revision": revision},
                headers={"Content-Type": "application/json"},
                timeout=(5, 15),
            )
        except requests.Timeout:
            raise CalendarTimeoutError("Hết thời gian chờ lưu kịch bản.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Lỗi mạng khi lưu kịch bản: {e}", 503)

        if res.status_code == 409:
            remote = {}
            with contextlib.suppress(Exception):
                remote = self.get_script(identifier)
            raise CalendarConflictError(
                "Xung đột kịch bản (409): Revision kịch bản trên server đã thay đổi.",
                remote_content=remote.get("content", ""),
                remote_revision=remote.get("revision", ""),
            )
        if res.ok:
            return res.json()
        raise CalendarSyncError(f"Lưu kịch bản thất bại ({res.status_code}): {res.text}", res.status_code)

    def get_caption(self, identifier: str) -> dict:
        try:
            res = requests.get(f"{self.base_url}/api/campaigns/{identifier}/caption", timeout=(5, 10))
        except requests.Timeout:
            raise CalendarTimeoutError("Hết thời gian chờ đọc caption.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Lỗi mạng khi đọc caption: {e}", 503)

        if res.ok:
            return res.json()
        raise CalendarSyncError(f"Đọc caption thất bại ({res.status_code}): {res.text}", res.status_code)

    def save_caption(self, identifier: str, content: str) -> dict:
        try:
            res = requests.put(
                f"{self.base_url}/api/campaigns/{identifier}/caption",
                json={"content": content},
                headers={"Content-Type": "application/json"},
                timeout=(5, 15),
            )
        except requests.Timeout:
            raise CalendarTimeoutError("Hết thời gian chờ lưu caption.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Lỗi mạng khi lưu caption: {e}", 503)

        if res.ok:
            return res.json()
        raise CalendarSyncError(f"Lưu caption thất bại ({res.status_code}): {res.text}", res.status_code)

    def delete_campaign(self, identifier: str) -> dict:
        try:
            res = requests.delete(f"{self.base_url}/api/campaigns/{identifier}", timeout=(5, 10))
            if res.ok:
                return res.json() if res.text else {"ok": True}
            raise CalendarSyncError(f"Xóa campaign thất bại ({res.status_code}): {res.text}", res.status_code)
        except requests.Timeout:
            raise CalendarTimeoutError("Hết thời gian chờ xóa campaign.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Lỗi mạng khi xóa campaign: {e}", 503)


def sync_project_to_calendar(
    project: Path,
    params: dict,
    client: Optional[CalendarClient] = None,
) -> dict:
    """Executes the step-by-step sync or resumes from prior state."""
    # 0. Governance check: Project must have completed publish checkpoint
    if not is_project_published(project):
        raise CalendarSyncError("Project chưa hoàn tất checkpoint publish. Không thể chuyển sang lịch đăng.", 400)

    with project_sync_lock(project):
        state = read_sync_state(project)
        history = state.get("history") or []
        milestones = set(state.get("milestones") or [])

        # Server URL lock: prioritize existing session URL
        base_url = resolve_calendar_url(state, params.get("calendar_url"))
        if client is None:
            client = CalendarClient(base_url)

        # 1. State UNKNOWN check: requires reconciliation before proceeding
        if state.get("status") == "UNKNOWN":
            raise CalendarSyncError(
                "Trạng thái trước đó là UNKNOWN (mất phản hồi mạng khi tạo campaign). Cần bấm 'Đối soát' để kiểm tra danh sách campaign trước khi thử lại.",
                409,
            )

        # 2. State CONFLICT_409 check: block /start until resolved
        if state.get("status") == "CONFLICT_409":
            raise CalendarSyncError(
                "Trạng thái hiện tại đang có xung đột kịch bản (409). Cần chọn xử lý xung đột (ghi đè hoặc giữ bản server) trước khi tiếp tục.",
                409,
            )

        # Extract or reuse campaign payload and snapshots
        title = (params.get("title") or state.get("title") or "").strip()
        if not title or len(title) > 180:
            raise CalendarSyncError("Tiêu đề chiến dịch bắt buộc và từ 1 đến 180 ký tự.", 422)

        scheduled_date = (params.get("scheduled_date") or state.get("scheduled_date") or "").strip()
        if not scheduled_date:
            raise CalendarSyncError("Ngày lên lịch (YYYY-MM-DD) là bắt buộc.", 422)

        koc = (params.get("koc") if params.get("koc") is not None else state.get("koc", "")).strip()
        idea = (params.get("idea") if params.get("idea") is not None else state.get("idea", "")).strip()
        product_url = (params.get("product_url") if params.get("product_url") is not None else state.get("product_url", "")).strip()
        planned_outfit_count = params.get("planned_outfit_count") or state.get("planned_outfit_count")

        defaults = get_default_sync_info(project)
        script_content = params.get("script") if params.get("script") is not None else (state.get("script_snapshot") or defaults["script"])
        caption_content = params.get("caption") if params.get("caption") is not None else (state.get("caption_snapshot") or defaults["caption"])

        campaign_id = state.get("campaign_id")
        old_title = (state.get("title") or "").strip()
        old_date = (state.get("scheduled_date") or "").strip()
        if campaign_id:
            if old_title and title != old_title:
                raise CalendarSyncError("Không thể thay đổi tiêu đề của chiến dịch đã được tạo trên Script Calendar.", 400)
            if old_date and scheduled_date != old_date:
                raise CalendarSyncError("Không thể thay đổi ngày lên lịch của chiến dịch đã được tạo trên Script Calendar.", 400)

        # Snapshot data into state
        state.update({
            "title": title,
            "scheduled_date": scheduled_date,
            "koc": koc,
            "idea": idea,
            "product_url": product_url,
            "planned_outfit_count": planned_outfit_count,
            "script_snapshot": script_content,
            "caption_snapshot": caption_content,
            "calendar_url": base_url,
        })

        # Handle Re-sync when already DONE: reset update milestones to ensure fresh script & caption sync
        if state.get("status") == "DONE" and campaign_id:
            logger.info("Project already DONE. Starting re-sync for existing campaign %s", campaign_id)
            milestones = {"CAMPAIGN_CREATED"}
            state["milestones"] = list(milestones)
            state["status"] = "CAMPAIGN_CREATED"
            history.append({
                "step": "START_UPDATE",
                "campaign_id": campaign_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            state["history"] = history
            write_sync_state(project, state)

        # Step A: Create campaign ONLY IF NOT ALREADY CREATED
        if not campaign_id or "CAMPAIGN_CREATED" not in milestones:
            # Snapshot existing IDs before sending POST. Must NOT proceed if baseline fails!
            try:
                raw_ids = client.list_campaign_ids()
                pre_ids = [str(x) for x in raw_ids if isinstance(x, (str, int))] if isinstance(raw_ids, (list, set, tuple)) else []
            except Exception as e:
                raise CalendarSyncError(f"Không thể lấy danh sách campaign hiện tại để làm mốc đối soát ({e}). Hủy tạo campaign để bảo vệ dữ liệu.", 502)

            state.update({
                "status": "UNKNOWN",
                "last_step": "CREATE_CAMPAIGN_IN_FLIGHT",
                "pre_existing_ids": pre_ids,
            })
            write_sync_state(project, state)

            create_payload = {
                "title": title,
                "scheduled_date": scheduled_date,
                "koc": koc,
                "idea": idea,
                "product_url": product_url,
            }
            if planned_outfit_count is not None:
                create_payload["planned_outfit_count"] = int(planned_outfit_count)

            try:
                created = client.create_campaign(create_payload)
            except CalendarSyncError as ce:
                # If server returned definite client validation error (4xx except 408/429), it was NOT created
                if getattr(ce, "status", None) in (400, 422):
                    state.update({
                        "status": "ERROR",
                        "error": str(ce),
                        "last_step": "CREATE_CAMPAIGN_REJECTED",
                    })
                    write_sync_state(project, state)
                else:
                    # Connection reset, 5xx, timeout, or unknown network failure -> keep UNKNOWN
                    state.update({
                        "status": "UNKNOWN",
                        "error": str(ce),
                        "last_step": "CREATE_CAMPAIGN_UNDETERMINED",
                    })
                    history.append({"step": "CREATE_CAMPAIGN", "status": "UNKNOWN", "error": str(ce), "timestamp": datetime.now(timezone.utc).isoformat()})
                    state["history"] = history
                    write_sync_state(project, state)
                raise

            except Exception as e:
                state.update({
                    "status": "UNKNOWN",
                    "error": str(e),
                    "last_step": "CREATE_CAMPAIGN_UNDETERMINED",
                })
                history.append({"step": "CREATE_CAMPAIGN", "status": "UNKNOWN", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()})
                state["history"] = history
                write_sync_state(project, state)
                raise CalendarSyncError(f"Lỗi không xác định khi tạo campaign: {e}")

            campaign_id = created.get("id")
            if not campaign_id:
                state.update({"status": "UNKNOWN", "error": "Server không trả về ID campaign sau khi tạo."})
                write_sync_state(project, state)
                raise CalendarSyncError("Server không trả về ID campaign sau khi tạo.", 502)

            milestones.add("CAMPAIGN_CREATED")
            state.update({
                "status": "CAMPAIGN_CREATED",
                "campaign_id": campaign_id,
                "milestones": list(milestones),
                "error": None,
                "last_step": "CAMPAIGN_CREATED",
            })
            history.append({"step": "CAMPAIGN_CREATED", "campaign_id": campaign_id, "timestamp": datetime.now(timezone.utc).isoformat()})
            state["history"] = history
            write_sync_state(project, state)

        # Step B: Save script if not yet satisfied
        if "SCRIPT_SAVED" not in milestones:
            if script_content:
                try:
                    script_resp = client.get_script(campaign_id)
                    current_revision = script_resp.get("revision") or ""
                    client.save_script(campaign_id, script_content, current_revision)
                except CalendarConflictError as ce:
                    state.update({
                        "status": "CONFLICT_409",
                        "error": str(ce),
                        "last_step": "SCRIPT_CONFLICT",
                        "conflict_detail": {
                            "remote_content": ce.remote_content,
                            "remote_revision": ce.remote_revision,
                            "local_content": script_content,
                        },
                    })
                    history.append({"step": "SAVE_SCRIPT", "status": "CONFLICT_409", "timestamp": datetime.now(timezone.utc).isoformat()})
                    state["history"] = history
                    write_sync_state(project, state)
                    raise ce
                except Exception as e:
                    state.update({"status": "ERROR", "error": str(e), "last_step": "SAVE_SCRIPT_ERROR"})
                    write_sync_state(project, state)
                    raise

            milestones.add("SCRIPT_SAVED")
            state.update({
                "status": "SCRIPT_SAVED",
                "milestones": list(milestones),
                "error": None,
                "last_step": "SCRIPT_SAVED",
            })
            history.append({"step": "SCRIPT_SAVED", "timestamp": datetime.now(timezone.utc).isoformat()})
            state["history"] = history
            write_sync_state(project, state)

        # Step C: Save caption if not yet satisfied
        if "CAPTION_SAVED" not in milestones:
            if caption_content:
                try:
                    client.save_caption(campaign_id, caption_content)
                except Exception as e:
                    state.update({"status": "ERROR", "error": str(e), "last_step": "SAVE_CAPTION_ERROR"})
                    write_sync_state(project, state)
                    raise

            milestones.add("CAPTION_SAVED")
            state.update({
                "status": "CAPTION_SAVED",
                "milestones": list(milestones),
                "error": None,
                "last_step": "CAPTION_SAVED",
            })
            history.append({"step": "CAPTION_SAVED", "timestamp": datetime.now(timezone.utc).isoformat()})
            state["history"] = history
            write_sync_state(project, state)

        # Step D: Complete when all steps are satisfied
        if {"CAMPAIGN_CREATED", "SCRIPT_SAVED", "CAPTION_SAVED"}.issubset(milestones):
            state.update({
                "status": "DONE",
                "error": None,
                "last_step": "DONE",
            })
            history.append({"step": "DONE", "timestamp": datetime.now(timezone.utc).isoformat()})
            state["history"] = history
            write_sync_state(project, state)

        return state


def reconcile_unknown_sync(
    project: Path,
    override_url: Optional[str] = None,
    client: Optional[CalendarClient] = None,
) -> dict:
    """Checks remote campaigns to see if an in-flight POST actually succeeded without misidentifying tasks."""
    with project_sync_lock(project):
        state = read_sync_state(project)
        if state.get("status") != "UNKNOWN":
            return {"reconciled": False, "message": "Trạng thái không phải UNKNOWN.", "state": state}

        base_url = resolve_calendar_url(state, override_url)
        if client is None:
            client = CalendarClient(base_url)

        target_title = (state.get("title") or "").strip().lower()
        target_date = (state.get("scheduled_date") or "").strip()
        target_koc = (state.get("koc") or "").strip().lower()

        pre_existing = set(state.get("pre_existing_ids") or [])
        campaigns = client.list_campaigns()

        matched_candidates = []
        for c in campaigns:
            cid = c.get("id")
            if not cid or cid in pre_existing:
                continue
            c_title = (c.get("title") or "").strip().lower()
            c_date = (c.get("scheduled_date") or c.get("date") or "").strip()
            c_koc = (c.get("koc") or "").strip().lower()

            if c_title != target_title:
                continue
            if target_date and c_date != target_date:
                continue
            if target_koc and c_koc != target_koc:
                continue

            matched_candidates.append(c)

        history = state.get("history") or []
        milestones = set(state.get("milestones") or [])

        if len(matched_candidates) == 1:
            matched = matched_candidates[0]
            milestones.add("CAMPAIGN_CREATED")
            state.update({
                "status": "CAMPAIGN_CREATED",
                "campaign_id": matched["id"],
                "milestones": list(milestones),
                "error": None,
                "last_step": "RECONCILED_FOUND",
            })
            history.append({
                "step": "RECONCILE",
                "status": "MATCHED",
                "campaign_id": matched["id"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            state["history"] = history
            write_sync_state(project, state)
            return {
                "reconciled": True,
                "found": True,
                "campaign_id": matched["id"],
                "state": state,
                "message": f"Đối soát thành công: Xác nhận campaign '{matched['id']}' đã được tạo trên server.",
            }

        if len(matched_candidates) > 1:
            state.update({
                "status": "UNKNOWN",
                "error": f"Tìm thấy {len(matched_candidates)} campaign trùng khớp. Cần xác nhận ID thủ công.",
                "last_step": "RECONCILE_AMBIGUOUS",
            })
            write_sync_state(project, state)
            return {
                "reconciled": False,
                "ambiguous": True,
                "candidates": [c.get("id") for c in matched_candidates],
                "message": f"Tìm thấy {len(matched_candidates)} campaign phù hợp. Vui lòng chọn campaign ID chính xác.",
                "state": state,
            }

        # 0 matches: safe to reset to ERROR so user can retry creation cleanly without duplicating
        state.update({
            "status": "ERROR",
            "error": "Đối soát: Xác nhận không có campaign mới nào được tạo trên server. Có thể thử tạo lại.",
            "last_step": "RECONCILED_NOT_FOUND",
        })
        history.append({
            "step": "RECONCILE",
            "status": "NOT_FOUND",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        state["history"] = history
        write_sync_state(project, state)
        return {
            "reconciled": True,
            "found": False,
            "state": state,
            "message": "Không tìm thấy campaign tương ứng trên server. Đã chuyển về trạng thái cho phép tạo lại an toàn.",
        }


def resolve_sync_conflict(
    project: Path,
    action: str,
    override_url: Optional[str] = None,
    client: Optional[CalendarClient] = None,
) -> dict:
    """Handles revision 409 conflict when saving script: overwrite with latest revision or keep remote."""
    with project_sync_lock(project):
        state = read_sync_state(project)
        if state.get("status") != "CONFLICT_409":
            raise CalendarSyncError("Trạng thái hiện tại không có xung đột 409.", 400)

        base_url = resolve_calendar_url(state, override_url)
        if client is None:
            client = CalendarClient(base_url)

        campaign_id = state.get("campaign_id")
        if not campaign_id:
            raise CalendarSyncError("Thiếu ID campaign.", 400)

        conflict_detail = state.get("conflict_detail") or {}
        local_content = conflict_detail.get("local_content") or state.get("script_snapshot") or ""
        milestones = set(state.get("milestones") or [])

        if action == "overwrite":
            script_resp = client.get_script(campaign_id)
            fresh_revision = script_resp.get("revision") or ""
            client.save_script(campaign_id, local_content, fresh_revision)
            milestones.add("SCRIPT_SAVED")
            state.update({
                "status": "SCRIPT_SAVED",
                "milestones": list(milestones),
                "error": None,
                "conflict_detail": None,
                "last_step": "SCRIPT_SAVED_OVERWRITE",
            })
        elif action == "keep_remote":
            milestones.add("SCRIPT_SAVED")
            state.update({
                "status": "SCRIPT_SAVED",
                "milestones": list(milestones),
                "error": None,
                "conflict_detail": None,
                "last_step": "SCRIPT_KEPT_REMOTE",
            })
        else:
            raise CalendarSyncError(f"Hành động không hợp lệ: {action}. Chọn 'overwrite' hoặc 'keep_remote'.", 422)

        write_sync_state(project, state)

    return sync_project_to_calendar(project, {"calendar_url": override_url}, client=client)
