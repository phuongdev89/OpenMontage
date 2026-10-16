"""Post-cleanup experience archive manager for published projects.

Safely purges ephemeral media, source compositions, and caches while preserving
provenance, final scripts, full checkpoint history, prompts, decision logs, and embeds.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backlot.copywriter import CopywriterError, _storage_lock
from backlot.file_manager import EXCLUDED, protected, resolve_file
from lib.checkpoint import read_checkpoint, write_checkpoint, CheckpointValidationError
from lib.posting_status import PLATFORMS, validate_post_url

# Categories of preserved files
PRESERVE_CATEGORIES = {
    "project_metadata": "Project configuration and marker files",
    "checkpoint": "Active lifecycle stage checkpoints",
    "checkpoint_history": "Full chronological checkpoint history",
    "artifact": "Canonical and supplementary production artifacts",
    "decision_log": "Project-level decision and governance audit trail",
    "execution_log": "Tool and execution events log",
    "conversation_transcript": "Markdown and JSON exported chat records",
    "selected_thumbnail": "Published concept thumbnail and channel branding",
    "channel_branding": "Channel logos and watermark assets",
    "posting_copy": "Final published captions, descriptions, and copies",
    "solution_notes": "Grounding math solution and pedagogical notes",
}

# Categories of deletable files
CLEANUP_CATEGORIES = {
    "rendered_video": "Rendered output MP4 videos and local exports",
    "narration_audio": "Intermediate and master audio stems (WAV, MP3)",
    "composition_source": "Atelier/Remotion composition TSX/JS code and font files",
    "inspection_frame": "Excess video test frames and visual inspection stills",
    "backup_draft": "Previous visual revision drafts and refresh backups",
    "trash_cache": "Internal trash bin and build caches",
}


def _is_symlink(path: Path) -> bool:
    try:
        return path.is_symlink()
    except OSError:
        return True


def _safe_resolve_target(project: Path, raw_rel: str) -> Path:
    """Resolve a project-relative path safely with strict traversal & protection guards."""
    rel = Path(raw_rel)
    if not raw_rel or rel.is_absolute() or any(x in raw_rel for x in ("\\", ":")) or ".." in rel.parts:
        raise CopywriterError("Đường dẫn tệp không hợp lệ.", 400)
    target = (project / rel).resolve()
    if not target.is_relative_to(project.resolve()) or target == project.resolve():
        raise CopywriterError("Đường dẫn nằm ngoài project.", 403)
    # Only protect root project.json and root checkpoints
    if target.parent.resolve() == project.resolve():
        name = target.name.lower()
        if name == "project.json" or name.startswith("checkpoint_"):
            raise CopywriterError("Checkpoint và cấu hình project được bảo vệ tuyệt đối.", 403)
    return target


def check_cleanup_eligibility(project: Path) -> dict[str, Any]:
    """Verify that the project has completed publication on both platforms."""
    cp_posted = read_checkpoint(project.parent, project.name, "posted", resolve_legacy_artifacts=True)
    if not cp_posted or cp_posted.get("status") != "completed":
        raise CopywriterError(
            "Project chưa hoàn tất stage Đã đăng (cần completed checkpoint_posted.json).", 400
        )

    log = (cp_posted.get("artifacts") or {}).get("posted_log") or {}
    if not isinstance(log, dict) or set(log) != set(PLATFORMS):
        raise CopywriterError("Dữ liệu đăng bài thiếu bản ghi YouTube hoặc Facebook.", 400)

    for platform in PLATFORMS:
        entry = log.get(platform) or {}
        if not entry.get("confirmed"):
            raise CopywriterError(f"Chưa xác nhận đăng trên {platform.title()}.", 400)
        try:
            validate_post_url(platform, entry.get("url", ""))
        except (ValueError, AttributeError):
            raise CopywriterError(f"Link {platform.title()} không hợp lệ.", 400)

    return log


def classify_project_files(project: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Scan all project files and partition them strictly into kept vs. deletable."""
    project = project.resolve()
    kept: list[dict[str, Any]] = []
    deleted: list[dict[str, Any]] = []

    for root_dir, dirs, files in os.walk(project, followlinks=False):
        # Do not traverse into symlinked directories or .git
        dirs[:] = [d for d in dirs if not _is_symlink(Path(root_dir, d)) and d != ".git"]
        for fname in sorted(files):
            full_path = Path(root_dir, fname)
            if _is_symlink(full_path):
                continue
            try:
                rel = full_path.relative_to(project).as_posix()
                size = full_path.stat().st_size
            except OSError:
                continue

            category = _classify_file(rel, fname)
            item = {"path": rel, "size": size, "category": category}

            if category in PRESERVE_CATEGORIES:
                kept.append(item)
            else:
                deleted.append(item)

    kept.sort(key=lambda x: x["path"])
    deleted.sort(key=lambda x: x["path"])
    return kept, deleted


def _classify_file(rel: str, fname: str) -> str:
    """Classify a project-relative file into a distinct functional role."""
    lower_rel = rel.lower().replace("\\", "/")
    lower_name = fname.lower()
    parts = lower_rel.split("/")

    # 1. Ephemeral folders & caches (always purged, even if they hold old json/backups)
    if any(p.startswith("backup_") for p in parts):
        return "backup_draft"
    if any(p in (".backlot-trash", ".cache") for p in parts):
        return "trash_cache"
    if parts[0] == "renders":
        return "rendered_video"
    if lower_rel.startswith("exports/frames/") or lower_rel.startswith("verify/") or lower_rel.startswith("snapshots/"):
        return "inspection_frame"

    # 2. Checkpoint files & history (preserved)
    if len(parts) == 1 and lower_name.startswith("checkpoint_") and lower_name.endswith(".json"):
        return "checkpoint"
    if parts[0] == "history":
        return "checkpoint_history"

    # 3. Metadata & configuration (preserved)
    if len(parts) == 1 and lower_name in ("project.json", "display_title.json", "meta.json"):
        return "project_metadata"

    # 4. Canonical artifacts directory (preserved)
    if parts[0] == "artifacts":
        if lower_name in ("solution.md", "solution.json"):
            return "solution_notes"
        return "artifact"

    # 5. Decision log & execution events (preserved)
    if lower_rel in ("decision_log.json", "artifacts/decision_log.json"):
        return "decision_log"
    if lower_rel == "events.jsonl":
        return "execution_log"

    # 6. Exported conversation transcripts (preserved)
    if lower_rel.startswith("exports/conversation/"):
        return "conversation_transcript"

    # 7. Selected thumbnails & exports text (preserved)
    if lower_rel.startswith("exports/thumbnails/"):
        return "selected_thumbnail"
    if lower_rel in ("exports/caption.txt", "exports/description.txt"):
        return "posting_copy"

    # 8. Channel branding & logo (preserved)
    if lower_rel.startswith("assets/branding/") or lower_rel == "public/channel-logo.png":
        return "channel_branding"

    # 9. Rendered video outputs & local exports (purged)
    if (
        lower_rel.startswith("exports/video/")
        or lower_name.endswith(".mp4")
        or lower_name.endswith(".webm")
        or lower_name.endswith(".watermark.json")
    ):
        return "rendered_video"

    # 10. Narration audio stems (purged)
    if (
        parts[0] == "audio"
        or lower_name.startswith("master_narration")
        or lower_name.endswith(".wav")
        or (lower_name.endswith(".mp3") and not lower_rel.startswith("assets/branding/"))
    ):
        return "narration_audio"

    # 11. Composition source code & fonts (purged)
    if lower_name.endswith((".tsx", ".jsx", ".ts", ".js", ".ttf", ".otf", ".woff", ".woff2")):
        return "composition_source"

    # Default to backup_draft for unknown ephemeral files
    return "backup_draft"


def extract_provenance_data(project: Path) -> dict[str, Any]:
    """Extract and consolidate final script, storyboard, prompts, and notes."""
    display: dict[str, Any] = {
        "title": project.name,
        "prompts": [],
        "script": None,
        "storyboard": None,
        "thumbnail_path": None,
        "posting_copy": None,
        "render_report": None,
        "decision_log": None,
        "solution": None,
    }

    # Title
    from backlot.project_title import read_title
    marker_file = project / "project.json"
    if marker_file.is_file():
        try:
            m = json.loads(marker_file.read_text(encoding="utf-8"))
            display["title"] = m.get("title") or project.name
        except Exception:
            pass
    override = read_title(project)
    if override:
        display["title"] = override

    # Script
    script_file = project / "artifacts" / "script.json"
    if script_file.is_file():
        try:
            display["script"] = json.loads(script_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Scene plan / storyboard
    sp_file = project / "artifacts" / "scene_plan.json"
    if sp_file.is_file():
        try:
            display["storyboard"] = json.loads(sp_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Solution
    sol_md = project / "artifacts" / "solution.md"
    if sol_md.is_file():
        try:
            display["solution"] = sol_md.read_text(encoding="utf-8")
        except Exception:
            pass

    # Prompts collection
    prompts: list[dict[str, Any]] = []

    # 1. Thumbnail prompt from publish_log / posting_package
    pl_file = project / "artifacts" / "publish_log.json"
    if pl_file.is_file():
        try:
            pl_data = json.loads(pl_file.read_text(encoding="utf-8"))
            pkg = pl_data.get("metadata", {}).get("posting_package", {})
            for t in pkg.get("thumbnails", []):
                p_text = t.get("prompt")
                if p_text:
                    prompts.append({
                        "category": "thumbnail",
                        "content": p_text,
                        "provider": t.get("provider") or "image-generate",
                        "model": t.get("model"),
                        "source_ref": "publish_log.json:metadata.posting_package.thumbnails",
                    })
                if t.get("path") and not display["thumbnail_path"]:
                    display["thumbnail_path"] = t.get("path")
            display["posting_copy"] = {
                "title": pkg.get("title"),
                "description": pkg.get("description"),
                "caption": pkg.get("caption"),
            }
        except Exception:
            pass

    # Selected thumbnail fallback
    if not display["thumbnail_path"]:
        from backlot.posting_support import selected_thumbnail
        st = selected_thumbnail(project)
        if st:
            display["thumbnail_path"] = st

    # 2. Audio voice performance prompts from script.json
    script = display["script"]
    if isinstance(script, dict):
        vp = script.get("voice_performance")
        if isinstance(vp, dict):
            prompts.append({
                "category": "voice_performance",
                "content": f"Voice persona and speed configuration for narration",
                "provider": vp.get("provider"),
                "voice": vp.get("voice"),
                "parameters": vp.get("provider_settings"),
                "source_ref": "script.json:voice_performance",
            })

    # 3. Asset prompts from asset_manifest
    am_file = project / "artifacts" / "asset_manifest.json"
    if am_file.is_file():
        try:
            am_data = json.loads(am_file.read_text(encoding="utf-8"))
            for asset in am_data.get("assets", []):
                if asset.get("prompt"):
                    prompts.append({
                        "category": asset.get("type") or "media",
                        "content": asset["prompt"],
                        "provider": asset.get("provider"),
                        "model": asset.get("model"),
                        "parameters": {"scene_id": asset.get("scene_id"), "id": asset.get("id")},
                        "source_ref": f"asset_manifest.json:asset:{asset.get('id')}",
                    })
        except Exception:
            pass

    display["prompts"] = prompts

    # Render report
    rr_file = project / "artifacts" / "render_report.json"
    if rr_file.is_file():
        try:
            display["render_report"] = json.loads(rr_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Decision log
    dl_file = project / "decision_log.json"
    if not dl_file.is_file():
        dl_file = project / "artifacts" / "decision_log.json"
    if dl_file.is_file():
        try:
            dl_data = json.loads(dl_file.read_text(encoding="utf-8"))
            display["decision_log"] = dl_data.get("decisions") or dl_data
        except Exception:
            pass

    return display


def collect_stage_snapshots(project: Path) -> dict[str, Any]:
    """Capture authentic snapshots of all existing stages without altering status."""
    snapshots: dict[str, Any] = {}
    for p in sorted(project.glob("checkpoint_*.json")):
        stage = p.stem[len("checkpoint_"):]
        if stage == "completed":
            continue
        try:
            cp = json.loads(p.read_text(encoding="utf-8"))
            snapshots[stage] = {
                "status": cp.get("status"),
                "timestamp": cp.get("timestamp"),
                "human_approved": cp.get("human_approved"),
                "human_approval_required": cp.get("human_approval_required"),
                "approval_resolution": cp.get("approval_resolution"),
                "review": cp.get("review"),
                "cost_snapshot": cp.get("cost_snapshot"),
                "error": cp.get("error"),
            }
        except Exception:
            snapshots[stage] = {"status": "unreadable"}
    return snapshots


def preview_cleanup(project: Path) -> dict[str, Any]:
    """Dry-run analysis for cleaning up a published project."""
    posted_log = check_cleanup_eligibility(project)
    kept, deleted = classify_project_files(project)

    bytes_before = sum(f["size"] for f in kept) + sum(f["size"] for f in deleted)
    bytes_freed = sum(f["size"] for f in deleted)
    bytes_after = bytes_before - bytes_freed
    pct_freed = (bytes_freed / bytes_before * 100) if bytes_before > 0 else 0.0

    # Categorical breakdown
    by_category: dict[str, dict[str, int]] = {}
    for f in deleted:
        cat = f["category"]
        if cat not in by_category:
            by_category[cat] = {"count": 0, "size": 0}
        by_category[cat]["count"] += 1
        by_category[cat]["size"] += f["size"]

    # Stable plan revision hash
    plan_sig = "|".join(f"{f['path']}:{f['size']}" for f in deleted)
    revision = hashlib.sha256(plan_sig.encode("utf-8")).hexdigest()

    cp_completed = read_checkpoint(project.parent, project.name, "completed")
    already_cleaned = bool(cp_completed and cp_completed.get("status") == "completed")

    return {
        "project_id": project.name,
        "already_cleaned": already_cleaned,
        "plan_revision": revision,
        "files_count_before": len(kept) + len(deleted),
        "files_count_after": len(kept),
        "files_freed": len(deleted),
        "bytes_before": bytes_before,
        "bytes_after": bytes_after,
        "bytes_freed": bytes_freed,
        "pct_freed": round(pct_freed, 2),
        "categories": by_category,
        "deleted_files": deleted,
        "kept_files": kept,
        "posted_links": posted_log,
    }


def execute_cleanup(project: Path, expected_revision: str) -> dict[str, Any]:
    """Execute the verified purge atomically and record checkpoint_completed.json."""
    project = project.resolve()
    with _storage_lock(project):
        preview = preview_cleanup(project)
        if preview["already_cleaned"]:
            raise CopywriterError("Project đã được dọn hoàn tất từ trước.", 400)
        if preview["plan_revision"] != expected_revision:
            raise CopywriterError(
                "Danh sách tệp hoặc dung lượng đã thay đổi sau khi xem trước. Hãy tải lại và kiểm tra lại.", 409
            )

        # Step 1: Write in_progress checkpoint to indicate active purge
        try:
            write_checkpoint(
                project.parent,
                project.name,
                "completed",
                "in_progress",
                {},
                metadata={"cleanup_stage": "purging_files"},
            )
        except Exception as exc:
            raise CopywriterError(f"Không thể khởi tạo checkpoint dọn dẹp: {exc}", 500) from exc

        # Step 2: Extract provenance data before deleting any files
        display_data = extract_provenance_data(project)
        stage_snapshots = collect_stage_snapshots(project)
        cleaned_at = datetime.now(timezone.utc).isoformat()

        # Step 3: Delete eligible files securely
        deleted_records = []
        try:
            for item in preview["deleted_files"]:
                target = _safe_resolve_target(project, item["path"])
                if target.is_symlink():
                    raise CopywriterError(f"Phát hiện symlink nguy hiểm: {item['path']}", 403)
                if target.is_file():
                    target.unlink()
                    deleted_records.append({**item, "deleted_at": cleaned_at})

            # Clean empty directories
            _clean_empty_dirs(project)
        except Exception as exc:
            # Record failure state in checkpoint
            try:
                write_checkpoint(
                    project.parent,
                    project.name,
                    "completed",
                    "failed",
                    {},
                    error=f"Lỗi khi xóa tệp: {exc}",
                )
            except Exception:
                pass
            raise CopywriterError(f"Lỗi khi thực hiện xóa tệp: {exc}", 500) from exc

        # Step 4: Measure real remaining state
        kept_after, leftover = classify_project_files(project)
        bytes_freed = sum(f["size"] for f in deleted_records)
        bytes_after = sum(f["size"] for f in kept_after)

        # Ensure Facebook share links are canonicalized to have video ID
        posted_links = dict(preview["posted_links"])
        fb_entry = posted_links.get("facebook")
        if isinstance(fb_entry, dict) and fb_entry.get("url"):
            from lib.embed_urls import resolve_facebook_canonical_url
            canonical_fb, vid = resolve_facebook_canonical_url(fb_entry["url"])
            if vid and canonical_fb:
                posted_links["facebook"] = {
                    **fb_entry,
                    "url": canonical_fb,
                    "original_share_url": fb_entry["url"],
                    "video_id": vid,
                }

        completed_record: dict[str, Any] = {
            "version": "1.0",
            "project_id": project.name,
            "cleaned_at": cleaned_at,
            "stage_snapshots": stage_snapshots,
            "posted_links": posted_links,
            "display_data": display_data,
            "cleanup_manifest": {
                "bytes_before": preview["bytes_before"],
                "bytes_after": bytes_after,
                "bytes_freed": bytes_freed,
                "files_count_before": preview["files_count_before"],
                "files_count_after": len(kept_after),
                "files_freed": len(deleted_records),
                "kept_files": kept_after,
                "deleted_files": deleted_records,
            },
        }

        # Step 5: Write final completed checkpoint atomically
        try:
            write_checkpoint(
                project.parent,
                project.name,
                "completed",
                "completed",
                {"completed_record": completed_record},
                metadata={"cleaned_at": cleaned_at},
            )
        except CheckpointValidationError as exc:
            raise CopywriterError(f"Lỗi xác thực hồ sơ dọn dẹp: {exc}", 500) from exc

        return {
            "project_id": project.name,
            "status": "completed",
            "cleaned_at": cleaned_at,
            "bytes_freed": bytes_freed,
            "files_freed": len(deleted_records),
            "bytes_after": bytes_after,
            "files_count_after": len(kept_after),
        }


def _clean_empty_dirs(root: Path) -> None:
    """Remove empty subdirectories left behind by deleted media."""
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        d = Path(dirpath)
        if d == root or d.name in (".git", "history", "artifacts", "exports"):
            continue
        try:
            # Only remove if completely empty
            if not any(d.iterdir()):
                d.rmdir()
        except OSError:
            pass
