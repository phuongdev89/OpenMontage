"""Calendar sync module — integration between Backlot and Script Calendar Management."""
from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

from backlot.copywriter import CopywriterError
from backlot.file_manager import atomic_bytes
from lib.env_loader import get_env, load_env

logger = logging.getLogger(__name__)

DEFAULT_CALENDAR_URL = "http://127.0.0.1:8766"
DEFAULT_KOC = "Toán Olympic Cùng Con"


def normalize_koc_name(name: Optional[str]) -> str:
    if not name:
        return ""
    import unicodedata
    normalized = unicodedata.normalize("NFKD", name.strip().lower().replace("_", " "))
    return "".join(c for c in normalized if not unicodedata.combining(c))


def is_same_koc(koc_a: Optional[str], koc_b: Optional[str]) -> bool:
    if not koc_a or not koc_b:
        return False
    return normalize_koc_name(koc_a) == normalize_koc_name(koc_b)


def get_calendar_management_dir() -> Optional[Path]:
    load_env()
    dir_str = get_env("SCRIPT_CALENDAR_MANAGEMENT_DIR")
    if dir_str and dir_str.strip():
        p = Path(dir_str.strip())
        if p.is_dir() and (p / "cli.py").is_file():
            return p
    return None


def get_python_exe(calendar_dir: Path) -> Path:
    venv_py = calendar_dir / ".venv" / "Scripts" / "python.exe"
    if venv_py.is_file():
        return venv_py
    venv_py_posix = calendar_dir / ".venv" / "bin" / "python"
    if venv_py_posix.is_file():
        return venv_py_posix
    return Path(sys.executable)


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
    env_url = (
        get_env("CALENDAR_API_BASE")
        or get_env("SCRIPT_CALENDAR_URL")
        or get_env("CALENDAR_URL")
    )
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


def extract_project_posting_content(project: Path, state_data: Optional[dict] = None) -> dict:
    from backlot.state import load_board_state
    state = state_data or load_board_state(project)
    package = state.get("publish_package") or {}

    title = (package.get("title") or state.get("title") or project.name).strip()
    disp_file = project / "display_title.json"
    if disp_file.is_file():
        try:
            t = json.loads(disp_file.read_text(encoding="utf-8")).get("title")
            if t and t.strip():
                title = t.strip()
        except Exception:
            pass
    proj_file = project / "project.json"
    if proj_file.is_file():
        try:
            t = json.loads(proj_file.read_text(encoding="utf-8")).get("title")
            if t and t.strip():
                title = t.strip()
        except Exception:
            pass

    yt_title = title
    yt_desc = ""
    fb_cap = ""
    copy_file = project / "artifacts" / "posting_copy.json"
    if copy_file.is_file():
        try:
            cdata = json.loads(copy_file.read_text(encoding="utf-8")).get("fields", {})
            yt_desc = cdata.get("description", "") or cdata.get("youtube_description", "")
            fb_cap = cdata.get("caption", "") or cdata.get("facebook_caption", "")
            if cdata.get("title"):
                yt_title = cdata.get("title")
        except Exception:
            pass

    if not yt_desc and (project / "exports" / "description.txt").is_file():
        try:
            yt_desc = (project / "exports" / "description.txt").read_text(encoding="utf-8")
        except Exception:
            pass
    if not yt_desc and (package.get("description") or package.get("caption")):
        yt_desc = (package.get("description") or package.get("caption") or "").strip()

    if not fb_cap and (project / "exports" / "caption.txt").is_file():
        try:
            fb_cap = (project / "exports" / "caption.txt").read_text(encoding="utf-8")
        except Exception:
            pass
    if not fb_cap and (package.get("caption") or package.get("description")):
        fb_cap = (package.get("caption") or package.get("description") or "").strip()

    return {
        "title": title,
        "youtube_title": yt_title,
        "youtube_description": yt_desc,
        "facebook_caption": fb_cap,
    }


def extract_published_links(project: Path) -> list[dict]:
    links = []
    pub_log_file = project / "artifacts" / "publish_log.json"
    if pub_log_file.is_file():
        try:
            pdata = json.loads(pub_log_file.read_text(encoding="utf-8"))
            for entry in pdata.get("entries", []):
                platform = entry.get("platform")
                url = entry.get("url") or entry.get("link")
                if platform and url:
                    links.append({"platform": platform.lower(), "url": url})
        except Exception:
            pass
    posted_cp = project / "checkpoint_posted.json"
    if posted_cp.is_file():
        try:
            cp_data = json.loads(posted_cp.read_text(encoding="utf-8"))
            platforms = cp_data.get("platforms") or {}
            for p, pinfo in platforms.items():
                if isinstance(pinfo, dict) and pinfo.get("url"):
                    links.append({"platform": p.lower(), "url": pinfo["url"]})
                elif isinstance(pinfo, str) and pinfo.startswith("http"):
                    links.append({"platform": p.lower(), "url": pinfo})
        except Exception:
            pass
    return links


def get_default_sync_info(project: Path) -> dict:
    from backlot.state import load_board_state
    state = load_board_state(project)
    package = state.get("publish_package") or {}
    artifacts = state.get("artifacts") or {}

    content_info = extract_project_posting_content(project, state)
    title = content_info["title"]
    if len(title) > 180:
        title = title[:177] + "..."

    caption = content_info["facebook_caption"] or content_info["youtube_description"] or (package.get("caption") or package.get("description") or "").strip()
    script_data = artifacts.get("script")
    script_md = format_script_markdown(script_data, title=title)

    sync_state = read_sync_state(project)
    today = date.today().isoformat()
    published = is_project_published(project)
    active_url = resolve_calendar_url(sync_state)
    cal_dir = get_calendar_management_dir()
    client = CalendarClient(active_url)

    is_added = False
    koc_schedule = []

    if sync_state.get("status") == "DONE" and sync_state.get("campaign_id"):
        is_added = True

    try:
        raw_campaigns = client.list_campaigns(koc=DEFAULT_KOC, limit=300)
        if not raw_campaigns:
            raw_campaigns = client.list_campaigns(koc="Toan_Olympic_Cung_Con", limit=300)
        koc_schedule = [c for c in raw_campaigns if isinstance(c, dict)] if isinstance(raw_campaigns, list) else []
        target_title = title.strip().lower()
        camp_id = sync_state.get("campaign_id")

        for c in koc_schedule:
            cid = c.get("id")
            c_title = (c.get("title") or "").strip().lower()
            c_folder = (c.get("folder_path") or c.get("folder_name") or "")

            if (camp_id and cid == camp_id) or (target_title and c_title == target_title) or (project.name in c_folder):
                is_added = True
                if sync_state.get("status") != "DONE":
                    sync_state.update({
                        "status": "DONE",
                        "campaign_id": cid,
                        "title": c.get("title") or title,
                        "scheduled_date": c.get("scheduled_date") or c.get("date"),
                        "scheduled_time": c.get("scheduled_time") or "11:30",
                        "koc": DEFAULT_KOC,
                    })
                    write_sync_state(project, sync_state)
                break
    except Exception as e:
        logger.warning("Lỗi quét lịch đăng KOC %s: %s", DEFAULT_KOC, e)

    # Smart default for idea
    idea = sync_state.get("idea") or ""
    if not idea:
        proposal_data = artifacts.get("proposal") or artifacts.get("idea")
        if isinstance(proposal_data, dict):
            packet = proposal_data.get("proposal_packet") or proposal_data
            concepts = packet.get("concept_options") or []
            if concepts and isinstance(concepts[0], dict):
                c0 = concepts[0]
                idea = c0.get("hook") or c0.get("visual_approach") or c0.get("title") or ""
            if not idea:
                idea = proposal_data.get("summary") or proposal_data.get("hook") or ""
        if not idea and caption:
            idea = caption.split("\n")[0].strip()
    if len(idea) > 300:
        idea = idea[:297] + "..."

    koc = sync_state.get("koc") or state.get("koc") or DEFAULT_KOC
    product_url = sync_state.get("product_url") or state.get("product_url") or ""

    today_weekday = date.today().weekday()
    golden_hours = ["09:00", "15:00", "20:00"] if today_weekday in (5, 6) else ["11:45", "19:30", "20:30"]
    suggested_time = "20:00" if today_weekday in (5, 6) else "19:30"
    if sync_state.get("campaign_id"):
        with contextlib.suppress(Exception):
            sugg = client.get_schedule_suggestion(sync_state["campaign_id"], koc=koc)
            if sugg.get("suggested_time"):
                suggested_time = sugg["suggested_time"]
            if sugg.get("golden_hours"):
                golden_hours = sugg["golden_hours"]

    scheduled_time = sync_state.get("scheduled_time") or suggested_time

    workflow = client.get_workflow(koc)

    return {
        "title": title,
        "scheduled_date": sync_state.get("scheduled_date") or today,
        "scheduled_time": scheduled_time,
        "suggested_time": suggested_time,
        "golden_hours": golden_hours,
        "workflow": workflow,
        "koc": koc,
        "idea": idea,
        "product_url": product_url,
        "caption": caption,
        "script": script_md,
        "sync_state": sync_state,
        "has_published_checkpoint": published,
        "calendar_url": active_url,
        "calendar_dir": str(cal_dir) if cal_dir else None,
        "calendar_mode": "cli" if cal_dir else "http",
        "is_added": is_added,
        "koc_schedule": koc_schedule,
    }


class CalendarClient:
    def __init__(self, base_url: str = DEFAULT_CALENDAR_URL, calendar_dir: Optional[Any] = None):
        self.base_url = (base_url or DEFAULT_CALENDAR_URL).rstrip("/")
        if calendar_dir is False:
            self.calendar_dir = None
        else:
            self.calendar_dir = calendar_dir if calendar_dir is not None else get_calendar_management_dir()

    def _find_campaign_dir(self, identifier: str) -> Optional[Path]:
        if not self.calendar_dir:
            return None
        load_env()
        c_root = get_env("CONTENT_ROOT") or "D:/Affiliate/02_Content_Production"
        cand1 = Path(c_root) / identifier
        if cand1.is_dir():
            return cand1
        root_path = Path(c_root)
        if root_path.is_dir():
            with contextlib.suppress(OSError):
                for child in root_path.iterdir():
                    if child.is_dir() and (child / identifier).is_dir():
                        return child / identifier
        return None

    def check_health(self) -> dict:
        if self.calendar_dir:
            if (self.calendar_dir / "cli.py").is_file():
                return {"status": "ok", "mode": "cli", "dir": str(self.calendar_dir)}
            raise CalendarSyncError("Thư mục SCRIPT_CALENDAR_MANAGEMENT_DIR không chứa cli.py.", 502)
        try:
            res = requests.get(f"{self.base_url}/health", timeout=(3, 5))
            if res.ok:
                return res.json()
            raise CalendarSyncError(f"Script Calendar /health trả về lỗi {res.status_code}.", 502)
        except requests.Timeout:
            raise CalendarTimeoutError("Kết nối /health tới Script Calendar quá thời gian.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Không thể kết nối Script Calendar: {e}", 503)

    def list_campaigns(self, koc: Optional[str] = None, limit: int = 200) -> list[dict]:
        if self.calendar_dir:
            python_exe = get_python_exe(self.calendar_dir)
            cmd = [str(python_exe), "cli.py", "list", "--limit", str(limit), "--json"]
            if koc:
                cmd.extend(["--koc", koc])
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(self.calendar_dir),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=15,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    data = json.loads(proc.stdout)
                    return data if isinstance(data, list) else []
            except Exception as e:
                logger.warning("Lỗi list_campaigns CLI: %s", e)
            return []
        try:
            params = {}
            if koc:
                params["koc"] = koc
            if limit:
                params["limit"] = str(limit)
            res = requests.get(f"{self.base_url}/api/campaigns", params=params, timeout=(5, 10))
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
        if self.calendar_dir:
            folder = self._find_campaign_dir(identifier)
            if folder and (folder / "calendar.json").is_file():
                with contextlib.suppress(Exception):
                    return json.loads((folder / "calendar.json").read_text(encoding="utf-8"))
            raise CalendarSyncError(f"Campaign {identifier} không tồn tại.", 404)
        try:
            res = requests.get(f"{self.base_url}/api/campaigns/{identifier}", timeout=(5, 10))
            if res.ok:
                return res.json()
            raise CalendarSyncError(f"Đọc campaign thất bại ({res.status_code}): {res.text}", res.status_code)
        except requests.Timeout:
            raise CalendarTimeoutError("Hết thời gian chờ đọc campaign.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Lỗi kết nối khi đọc campaign: {e}", 503)

    def get_workflow(self, koc_name: str = DEFAULT_KOC) -> dict:
        """Lấy cấu hình workflow của KOC (video_format, outfit_mode, task_kind, ...)."""
        if self.calendar_dir:
            return {
                "key": "toan_olympic",
                "outfit_mode": "none",
                "task_kind": "animation",
                "default_look_count": 0,
                "video_format": "landscape",
                "multiple_outfits": False,
            }
        try:
            res = requests.get(f"{self.base_url}/api/koc-workflows/{koc_name}", timeout=(5, 10))
            if res.ok:
                return res.json()
        except Exception as e:
            logger.warning("Không thể lấy workflow cho KOC %s: %s", koc_name, e)
        return {
            "key": "toan_olympic",
            "outfit_mode": "none",
            "task_kind": "animation",
            "default_look_count": 0,
            "video_format": "landscape",
            "multiple_outfits": False,
        }

    def get_schedule_suggestion(self, campaign_id: str, koc_name: str = DEFAULT_KOC) -> dict:
        """Gợi ý khung giờ vàng đăng bài cho chiến dịch."""
        if self.calendar_dir:
            # Quy tắc: T2-T6 gợi ý 19:30, T7-CN gợi ý 20:00
            today_weekday = date.today().weekday()
            is_weekend = today_weekday in (5, 6)
            golden = ["09:00", "15:00", "20:00"] if is_weekend else ["11:45", "19:30", "20:30"]
            return {
                "campaign_id": campaign_id,
                "koc": koc_name,
                "suggested_time": "20:00" if is_weekend else "19:30",
                "golden_hours": golden,
            }
        try:
            res = requests.get(
                f"{self.base_url}/api/campaigns/{campaign_id}/schedule-suggestion",
                params={"koc": koc_name},
                timeout=(5, 10),
            )
            if res.ok:
                return res.json()
        except Exception as e:
            logger.warning("Không thể lấy gợi ý khung giờ cho %s: %s", campaign_id, e)

        today_weekday = date.today().weekday()
        is_weekend = today_weekday in (5, 6)
        golden = ["09:00", "15:00", "20:00"] if is_weekend else ["11:45", "19:30", "20:30"]
        return {
            "campaign_id": campaign_id,
            "koc": koc_name,
            "suggested_time": "20:00" if is_weekend else "19:30",
            "golden_hours": golden,
        }

    def get_today_check(self, koc_name: str = DEFAULT_KOC) -> dict:
        """Kiểm tra các bài cần đăng trong ngày hôm nay."""
        if self.calendar_dir:
            return {"date": date.today().isoformat(), "total_today": 0, "by_status": {}, "campaigns": []}
        try:
            res = requests.get(
                f"{self.base_url}/api/campaigns/today-check",
                params={"koc": koc_name},
                timeout=(5, 10),
            )
            if res.ok:
                return res.json()
        except Exception as e:
            logger.warning("Lỗi get_today_check: %s", e)
        return {"date": date.today().isoformat(), "total_today": 0, "by_status": {}, "campaigns": []}

    def get_koc_thumbnail(self, koc_name: str = DEFAULT_KOC) -> Optional[bytes]:
        """Lấy avatar / logo của KOC."""
        try:
            res = requests.get(f"{self.base_url}/api/koc-thumbnail/{koc_name}", timeout=(5, 10))
            if res.ok:
                return res.content
        except Exception as e:
            logger.warning("Lỗi get_koc_thumbnail: %s", e)
        return None

    def create_campaign(self, payload: dict) -> dict:
        if self.calendar_dir:
            python_exe = get_python_exe(self.calendar_dir)
            title = (payload.get("title") or "").strip()
            date_str = (payload.get("scheduled_date") or payload.get("date") or "").strip()
            koc = (payload.get("koc") or DEFAULT_KOC).strip() or DEFAULT_KOC
            idea = (payload.get("idea") or "").strip()
            product_url = (payload.get("product_url") or "").strip()
            scheduled_time = (payload.get("scheduled_time") or "").strip()

            cmd = [
                str(python_exe),
                "cli.py",
                "create",
                "--title", title,
                "--date", date_str,
            ]
            if koc:
                cmd.extend(["--koc", koc])
            if idea:
                cmd.extend(["--idea", idea])
            if product_url:
                cmd.extend(["--product-url", product_url])
            if scheduled_time:
                cmd.extend(["--scheduled-time", scheduled_time])
            cmd.append("--json")

            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(self.calendar_dir),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=30,
                )
            except subprocess.TimeoutExpired:
                raise CalendarTimeoutError("Hết thời gian chờ lệnh tạo task trên CLI.")
            except Exception as e:
                raise CalendarSyncError(f"Lỗi khi thực thi CLI: {e}", 500)

            if proc.returncode != 0:
                err = proc.stderr.strip() or proc.stdout.strip() or f"Exit code {proc.returncode}"
                raise CalendarSyncError(f"Lỗi CLI Script Calendar: {err}", 500)

            try:
                data = json.loads(proc.stdout)
                return data if isinstance(data, dict) else {"id": str(data)}
            except Exception as e:
                raise CalendarSyncError(f"Lỗi phân tích JSON từ CLI: {e}", 502)

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
        if self.calendar_dir:
            folder = self._find_campaign_dir(identifier)
            if folder and (folder / "01_scripts/master_script.md").is_file():
                content = (folder / "01_scripts/master_script.md").read_text(encoding="utf-8")
                return {"content": content, "revision": "cli_rev_1"}
            return {"content": "", "revision": ""}
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
        if self.calendar_dir:
            folder = self._find_campaign_dir(identifier)
            if folder:
                s_file = folder / "01_scripts" / "master_script.md"
                s_file.parent.mkdir(parents=True, exist_ok=True)
                atomic_bytes(s_file, content.encode("utf-8"))
            return {"ok": True, "revision": revision or "cli_rev_1"}

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
        if self.calendar_dir:
            folder = self._find_campaign_dir(identifier)
            if folder and (folder / "01_scripts/post.md").is_file():
                content = (folder / "01_scripts/post.md").read_text(encoding="utf-8")
                return {"content": content}
            return {"content": ""}
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
        if self.calendar_dir:
            folder = self._find_campaign_dir(identifier)
            if folder:
                c_file1 = folder / "01_scripts" / "post.md"
                c_file1.parent.mkdir(parents=True, exist_ok=True)
                atomic_bytes(c_file1, content.encode("utf-8"))
                if (folder / "04_output").is_dir():
                    c_file2 = folder / "04_output" / "post.md"
                    atomic_bytes(c_file2, content.encode("utf-8"))
            return {"ok": True, "campaign_id": identifier}
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
        if self.calendar_dir:
            python_exe = get_python_exe(self.calendar_dir)
            with contextlib.suppress(Exception):
                subprocess.run(
                    [str(python_exe), "cli.py", "delete", "--yes", identifier],
                    cwd=str(self.calendar_dir),
                    capture_output=True,
                    timeout=15,
                )
            folder = self._find_campaign_dir(identifier)
            if folder and folder.is_dir():
                with contextlib.suppress(Exception):
                    shutil.rmtree(folder)
            return {"ok": True}
        try:
            res = requests.delete(f"{self.base_url}/api/campaigns/{identifier}", timeout=(5, 10))
            if res.ok:
                return res.json() if res.text else {"ok": True}
            raise CalendarSyncError(f"Xóa campaign thất bại ({res.status_code}): {res.text}", res.status_code)
        except requests.Timeout:
            raise CalendarTimeoutError("Hết thời gian chờ xóa campaign.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Lỗi mạng khi xóa campaign: {e}", 503)

    def update_content(self, identifier: str, content: dict) -> dict:
        """Bước 2: Đồng bộ nội dung bài đăng đa nền tảng (youtube_title, youtube_description, facebook_caption)."""
        if self.calendar_dir:
            folder = self._find_campaign_dir(identifier)
            if folder:
                fb_cap = content.get("facebook_caption") or content.get("caption") or ""
                if fb_cap:
                    c_file = folder / "01_scripts" / "post.md"
                    c_file.parent.mkdir(parents=True, exist_ok=True)
                    atomic_bytes(c_file, fb_cap.encode("utf-8"))
            return {"ok": True, "campaign_id": identifier}
        try:
            res = requests.post(
                f"{self.base_url}/api/campaigns/{identifier}/content",
                json=content,
                headers={"Content-Type": "application/json"},
                timeout=(5, 15),
            )
        except requests.Timeout:
            raise CalendarTimeoutError("Hết thời gian chờ cập nhật nội dung đa nền tảng.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Lỗi mạng khi cập nhật nội dung đa nền tảng: {e}", 503)

        if res.ok:
            return res.json()
        raise CalendarSyncError(f"Cập nhật nội dung thất bại ({res.status_code}): {res.text}", res.status_code)

    def update_status(self, identifier: str, status: str = "CAPTIONED") -> dict:
        """Bước 3: Cập nhật trạng thái sản xuất (PLANNED -> PRODUCED -> CAPTIONED -> PUBLISHED)."""
        if self.calendar_dir:
            return {"ok": True, "status": status}
        try:
            res = requests.post(
                f"{self.base_url}/api/campaigns/{identifier}/status",
                json={"status": status},
                headers={"Content-Type": "application/json"},
                timeout=(5, 10),
            )
        except requests.Timeout:
            raise CalendarTimeoutError("Hết thời gian chờ cập nhật trạng thái.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Lỗi mạng khi cập nhật trạng thái: {e}", 503)

        if res.ok:
            return res.json()
        raise CalendarSyncError(f"Cập nhật trạng thái thất bại ({res.status_code}): {res.text}", res.status_code)

    def update_published_links(self, identifier: str, links: list[dict]) -> dict:
        """Bước 4: Đồng bộ link khi đã xuất bản lên mạng xã hội."""
        if not links:
            return {"ok": True, "links": []}
        if self.calendar_dir:
            return {"ok": True, "links": links}
        try:
            res = requests.post(
                f"{self.base_url}/api/campaigns/{identifier}/published-links",
                json={"links": links},
                headers={"Content-Type": "application/json"},
                timeout=(5, 10),
            )
        except requests.Timeout:
            raise CalendarTimeoutError("Hết thời gian chờ cập nhật link xuất bản.")
        except requests.RequestException as e:
            raise CalendarSyncError(f"Lỗi mạng khi cập nhật link xuất bản: {e}", 503)

        if res.ok:
            return res.json()
        raise CalendarSyncError(f"Cập nhật link xuất bản thất bại ({res.status_code}): {res.text}", res.status_code)


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

        scheduled_time = (params.get("scheduled_time") or state.get("scheduled_time") or "11:30").strip()
        koc = (params.get("koc") if params.get("koc") is not None else state.get("koc", DEFAULT_KOC)).strip() or DEFAULT_KOC
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
            "scheduled_time": scheduled_time,
            "koc": koc,
            "idea": idea,
            "product_url": product_url,
            "planned_outfit_count": planned_outfit_count,
            "script_snapshot": script_content,
            "caption_snapshot": caption_content,
            "calendar_url": base_url,
        })

        # CLI execution when SCRIPT_CALENDAR_MANAGEMENT_DIR is configured and no explicit mock client is injected
        cal_dir = get_calendar_management_dir()
        if client is None and cal_dir is not None:
            return sync_via_cli(
                project=project,
                calendar_dir=cal_dir,
                params=params,
                state=state,
                title=title,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                koc=koc,
                idea=idea,
                product_url=product_url,
                script_content=script_content,
                caption_content=caption_content,
            )

        if client is None:
            client = CalendarClient(base_url)

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
                "planned_outfit_count": 0 if planned_outfit_count is None else int(planned_outfit_count),
                "share_affiliate": False,
                "affiliate_in_caption": False,
                "link_placement": "none",
                "folder_name": project.name,
            }
            if product_url:
                create_payload["product_url"] = product_url

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
            content_info = extract_project_posting_content(project)
            yt_title = params.get("youtube_title") or content_info.get("youtube_title") or title
            yt_desc = params.get("youtube_description") or content_info.get("youtube_description") or caption_content
            fb_cap = params.get("facebook_caption") or content_info.get("facebook_caption") or caption_content

            content_payload = {
                "youtube_title": yt_title,
                "youtube_description": yt_desc,
                "facebook_caption": fb_cap,
            }
            if hasattr(client, "update_content"):
                with contextlib.suppress(Exception):
                    client.update_content(campaign_id, content_payload)

            if hasattr(client, "update_status"):
                with contextlib.suppress(Exception):
                    client.update_status(campaign_id, "CAPTIONED")

            pub_links = extract_published_links(project)
            if pub_links and hasattr(client, "update_published_links"):
                with contextlib.suppress(Exception):
                    client.update_published_links(campaign_id, pub_links)
            if getattr(client, "calendar_dir", None):
                folder_path = None
                if hasattr(client, "_find_campaign_dir"):
                    folder_path = client._find_campaign_dir(campaign_id)
                if folder_path and folder_path.is_dir():
                    state["folder_path"] = str(folder_path)
                    video_candidates = list((project / "exports" / "video").glob("*.mp4"))
                    if not video_candidates:
                        video_candidates = list((project / "renders").glob("*.mp4"))
                    if video_candidates:
                        best_video = video_candidates[0]
                        for v in video_candidates:
                            if "landscape" in v.name:
                                best_video = v
                                break
                        dest_video = folder_path / "04_output" / "video.mp4"
                        dest_video.parent.mkdir(parents=True, exist_ok=True)
                        if not dest_video.is_file() or dest_video.stat().st_size != best_video.stat().st_size:
                            with contextlib.suppress(OSError):
                                shutil.copy2(best_video, dest_video)

                    thumb_candidates = list((project / "exports" / "thumbnails").glob("*.*"))
                    if thumb_candidates:
                        best_thumb = thumb_candidates[0]
                        dest_cover = folder_path / "04_output" / "cover.jpg"
                        dest_cover.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            from PIL import Image
                            with Image.open(best_thumb) as img:
                                rgb = img.convert("RGB")
                                rgb.save(dest_cover, "JPEG", quality=92)
                        except Exception:
                            with contextlib.suppress(OSError):
                                shutil.copy2(best_thumb, dest_cover)

                    with contextlib.suppress(Exception):
                        python_exe = get_python_exe(client.calendar_dir)
                        subprocess.run(
                            [str(python_exe), "cli.py", "sync"],
                            cwd=str(client.calendar_dir),
                            capture_output=True,
                            timeout=15,
                        )

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
            if target_koc and c_koc and not is_same_koc(target_koc, c_koc):
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
