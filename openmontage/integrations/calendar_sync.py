"""Calendar Sync Client for OpenMontage -> Script Calendar Management integration."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from lib.env_loader import get_env, load_env

logger = logging.getLogger(__name__)

load_env()
CALENDAR_BASE_URL = (
    get_env("CALENDAR_API_BASE")
    or get_env("SCRIPT_CALENDAR_URL")
    or get_env("CALENDAR_URL")
    or os.getenv("CALENDAR_API_BASE", "http://127.0.0.1:8766")
).rstrip("/")


class CalendarSyncClient:
    def __init__(self, base_url: str = CALENDAR_BASE_URL):
        self.base_url = (base_url or CALENDAR_BASE_URL).rstrip("/")

    def sync_project(
        self,
        project_dir: Path,
        scheduled_date: str,
        koc_name: str = "Toán Olympic Cùng Con",
        scheduled_time: str = "11:30",
    ) -> Dict[str, Any]:
        """Đọc metadata từ dự án OpenMontage và đồng bộ toàn diện sang Script Calendar Management."""
        project_dir = Path(project_dir).resolve()
        folder_name = project_dir.name

        # 1. Đọc metadata bài toán từ display_title.json / project.json
        title = folder_name
        disp_file = project_dir / "display_title.json"
        if disp_file.is_file():
            try:
                title = json.loads(disp_file.read_text(encoding="utf-8")).get("title") or title
            except Exception:
                pass

        proj_file = project_dir / "project.json"
        if proj_file.is_file():
            try:
                title = json.loads(proj_file.read_text(encoding="utf-8")).get("title") or title
            except Exception:
                pass

        # 2. Đọc nội dung đa nền tảng từ posting_copy.json hoặc exports/
        yt_desc = ""
        fb_cap = ""
        copy_file = project_dir / "artifacts" / "posting_copy.json"
        if copy_file.is_file():
            try:
                cdata = json.loads(copy_file.read_text(encoding="utf-8")).get("fields", {})
                yt_desc = cdata.get("description", "") or cdata.get("youtube_description", "")
                fb_cap = cdata.get("caption", "") or cdata.get("facebook_caption", "")
                if cdata.get("title"):
                    title = cdata.get("title")
            except Exception:
                pass

        if not yt_desc and (project_dir / "exports" / "description.txt").is_file():
            try:
                yt_desc = (project_dir / "exports" / "description.txt").read_text(encoding="utf-8")
            except Exception:
                pass
        if not fb_cap and (project_dir / "exports" / "caption.txt").is_file():
            try:
                fb_cap = (project_dir / "exports" / "caption.txt").read_text(encoding="utf-8")
            except Exception:
                pass

        # 3. Bước 1: Khởi tạo/đăng ký chiến dịch
        create_payload = {
            "title": title,
            "scheduled_date": scheduled_date,
            "scheduled_time": scheduled_time,
            "koc": koc_name,
            "idea": yt_desc[:200] if yt_desc else title,
            "planned_outfit_count": 0,
            "share_affiliate": False,
            "affiliate_in_caption": False,
            "link_placement": "none",
            "folder_name": folder_name,
        }

        res = requests.post(
            f"{self.base_url}/api/campaigns",
            json=create_payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        res.raise_for_status()
        created_data = res.json()
        campaign_id = created_data.get("id") or folder_name

        # 4. Bước 2: Đồng bộ nội dung bài đăng đa nền tảng
        content_payload = {
            "youtube_title": title,
            "youtube_description": yt_desc,
            "facebook_caption": fb_cap,
        }
        res_content = requests.post(
            f"{self.base_url}/api/campaigns/{campaign_id}/content",
            json=content_payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        res_content.raise_for_status()

        # 5. Bước 3: Cập nhật trạng thái sản xuất
        res_status = requests.post(
            f"{self.base_url}/api/campaigns/{campaign_id}/status",
            json={"status": "CAPTIONED"},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        res_status.raise_for_status()

        # 6. Bước 4 (Tùy chọn): Đồng bộ link khi đã xuất bản
        links = self._extract_published_links(project_dir)
        if links:
            try:
                requests.post(
                    f"{self.base_url}/api/campaigns/{campaign_id}/published-links",
                    json={"links": links},
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )
            except Exception as e:
                logger.warning("Không thể đồng bộ published-links: %s", e)

        return {
            "campaign_id": campaign_id,
            "title": title,
            "scheduled_date": scheduled_date,
            "status": "CAPTIONED",
            "created": created_data,
        }

    def _extract_published_links(self, project_dir: Path) -> List[Dict[str, str]]:
        links: List[Dict[str, str]] = []
        pub_log = project_dir / "artifacts" / "publish_log.json"
        if pub_log.is_file():
            try:
                data = json.loads(pub_log.read_text(encoding="utf-8"))
                for e in data.get("entries", []):
                    p = e.get("platform")
                    u = e.get("url") or e.get("link")
                    if p and u:
                        links.append({"platform": p.lower(), "url": u})
            except Exception:
                pass
        posted_cp = project_dir / "checkpoint_posted.json"
        if posted_cp.is_file():
            try:
                data = json.loads(posted_cp.read_text(encoding="utf-8"))
                platforms = data.get("platforms") or {}
                for p, val in platforms.items():
                    if isinstance(val, dict) and val.get("url"):
                        links.append({"platform": p.lower(), "url": val["url"]})
                    elif isinstance(val, str) and val.startswith("http"):
                        links.append({"platform": p.lower(), "url": val})
            except Exception:
                pass
        return links

    def get_workflow(self, koc_name: str = "Toán Olympic Cùng Con") -> Dict[str, Any]:
        """1. Lấy cấu hình workflow của KOC (video_format, outfit_mode, task_kind, ...)."""
        res = requests.get(f"{self.base_url}/api/koc-workflows/{koc_name}", timeout=10)
        res.raise_for_status()
        return res.json()

    def list_koc_campaigns(self, koc_name: str = "Toán Olympic Cùng Con") -> List[Dict[str, Any]]:
        """2. Lấy danh sách tất cả các bài đã lên lịch của KOC."""
        res = requests.get(f"{self.base_url}/api/campaigns", timeout=10)
        res.raise_for_status()
        all_camps = res.json()
        if not isinstance(all_camps, list):
            return []
        import unicodedata
        def norm(s: Optional[str]) -> str:
            if not s: return ""
            nk = unicodedata.normalize("NFKD", s.strip().lower().replace("_", " "))
            return "".join(c for c in nk if not unicodedata.combining(c))
        target = norm(koc_name)
        return [c for c in all_camps if isinstance(c, dict) and norm(c.get("koc")) == target]

    def get_campaign_detail(self, campaign_id: str) -> Dict[str, Any]:
        """3. Lấy chi tiết 1 chiến dịch / bài toán cụ thể."""
        res = requests.get(f"{self.base_url}/api/campaigns/{campaign_id}", timeout=10)
        res.raise_for_status()
        return res.json()

    def get_schedule_suggestion(
        self, campaign_id: str, koc_name: str = "Toán Olympic Cùng Con"
    ) -> Dict[str, Any]:
        """4. Gợi ý khung giờ vàng đăng bài cho Toán Olympic."""
        res = requests.get(
            f"{self.base_url}/api/campaigns/{campaign_id}/schedule-suggestion",
            params={"koc": koc_name},
            timeout=10,
        )
        res.raise_for_status()
        return res.json()

    def get_today_check(self, koc_name: str = "Toán Olympic Cùng Con") -> Dict[str, Any]:
        """5. Kiểm tra các bài cần đăng trong ngày hôm nay."""
        res = requests.get(
            f"{self.base_url}/api/campaigns/today-check",
            params={"koc": koc_name},
            timeout=10,
        )
        res.raise_for_status()
        return res.json()

    def get_koc_thumbnail(self, koc_name: str = "Toán Olympic Cùng Con") -> bytes:
        """6. Lấy avatar / logo của kênh."""
        res = requests.get(f"{self.base_url}/api/koc-thumbnail/{koc_name}", timeout=10)
        res.raise_for_status()
        return res.content

