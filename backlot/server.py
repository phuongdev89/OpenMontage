"""Backlot server — FastAPI app: board state API, SSE change feed, media.

The watcher observes ``projects/`` with watchfiles; on any change it bumps a
per-project version and wakes SSE subscribers, who tell the browser to
refetch state. User-requested copy revisions only write posting_copy.json;
pipeline checkpoints and media remain disk-derived.
"""

from __future__ import annotations

import asyncio
import errno
import json
import logging
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Optional, Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, StrictBool
from backlot.copywriter import CopywriterError, regenerate

from backlot.state import PROJECTS_DIR, REPO_ROOT, list_projects, load_board_state, summarize_project

UI_DIR = Path(__file__).resolve().parent / "ui"
THUMB_CACHE_DIR = REPO_ROOT / ".backlot" / "thumbs"
THUMB_WIDTHS = (320, 640, 960)

# Paths inside a project whose changes are pure noise for the board.
_IGNORE_PARTS = {"node_modules", ".git", "__pycache__", ".cache", ".backlot-trash"}

SSE_HEARTBEAT_SECONDS = 15
RECONCILE_SECONDS = 5
logger = logging.getLogger(__name__)


class TitleRevisionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    expected_title: str


class CopyRevisionRequest(BaseModel):
    field: Literal['caption', 'description']
    instruction: str = Field(min_length=1, max_length=4000)
    expected_revision: str = Field(pattern=r'^[a-f0-9]{64}$')


class VideoTitleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    expected_revision: str = Field(pattern=r'^[a-f0-9]{64}$')


class SupportRequest(BaseModel):
    expected_revision: str = Field(pattern=r'^[a-f0-9]{64}$')


class PathRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1000)


class PostedRequest(BaseModel):
    platform: Literal['youtube', 'facebook']
    confirmed: StrictBool
    url: str = Field(max_length=2000)
    expected_revision: str = Field(pattern=r'^[a-f0-9]{64}$')


class FileDeleteRequest(PathRequest):
    expected_revision: str = Field(pattern=r'^[a-f0-9]{64}$')


def _ui_html(name: str, assets: tuple[str, ...]) -> HTMLResponse:
    html = (UI_DIR / name).read_text(encoding="utf-8")
    for asset in assets:
        path = UI_DIR / asset
        if path.is_file():
            version = str(int(path.stat().st_mtime))
            html = html.replace(f"/ui/{asset}", f"/ui/{asset}?v={version}")
    return HTMLResponse(html)


class ChangeHub:
    """Fan-out of project-change notifications to SSE subscribers.

    Subscriptions are filtered: a board subscribed to one project only ever
    receives that project's ids, so unrelated-project bursts can't flood its
    queue and starve out the one notification it actually needs.
    """

    def __init__(self) -> None:
        self._subscribers: dict[asyncio.Queue, Optional[str]] = {}

    def subscribe(self, project_id: Optional[str] = None) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._subscribers[q] = project_id
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.pop(q, None)

    def publish(self, project_id: str) -> None:
        for q, only in list(self._subscribers.items()):
            if only is not None and only != project_id:
                continue
            try:
                q.put_nowait(project_id)
            except asyncio.QueueFull:
                # Queue holds only THIS subscriber's relevant ids, so a full
                # queue already guarantees a pending wake-up → safe to drop.
                pass


hub = ChangeHub()

# Library summaries are expensive to derive (full state parse per project);
# cache per project and invalidate from the watcher.
_summary_cache: dict[str, dict] = {}


def _invalidate_summary(project_id: str) -> None:
    _summary_cache.pop(project_id, None)


def _cached_summaries() -> list[dict]:
    if not PROJECTS_DIR.is_dir():
        return []
    summaries = []
    for entry in sorted(PROJECTS_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith(("_", ".")):
            continue
        cached = _summary_cache.get(entry.name)
        if cached is None:
            try:
                cached = summarize_project(entry)
            except Exception:
                cached = {
                    "project_id": entry.name, "title": entry.name,
                    "pipeline_type": "unknown", "has_pipeline_state": False,
                    "poster": None, "live": False, "last_activity": 0,
                    "active_stage": None, "awaiting_human": False,
                    "stage_states": [], "completed_count": 0,
                    "render_count": 0, "scene_count": 0, "error": "unreadable",
                }
            _summary_cache[entry.name] = cached
        summaries.append(cached)
    summaries.sort(key=lambda s: (not s["live"], -(s["last_activity"] or 0)))
    return summaries


# Watch-loop hot path: pure string comparison, no per-path filesystem calls
# (change batches can be thousands of paths during a render).
import os as _os

_PROJECTS_ROOT_STR = _os.path.normcase(str(PROJECTS_DIR.resolve()))


def _project_of_change(path_str: str) -> Optional[str]:
    """Map a changed filesystem path to a project id (None = irrelevant)."""
    original = _os.path.normpath(path_str)
    norm = _os.path.normcase(original)
    if not norm.startswith(_PROJECTS_ROOT_STR + _os.sep):
        return None
    rel = original[len(_PROJECTS_ROOT_STR):].lstrip("\\/")
    if not rel:
        return None
    parts = rel.replace("\\", "/").split("/")
    if _IGNORE_PARTS.intersection(p.lower() for p in parts):
        return None
    return parts[0]


def _project_signatures() -> dict[str, tuple]:
    """Stat files, never read media bytes; prune dependency/build noise."""
    result = {}
    if not PROJECTS_DIR.is_dir():
        return result
    for project in PROJECTS_DIR.iterdir():
        if not project.is_dir() or project.name.startswith(("_", ".")):
            continue
        files = []
        for directory, dirs, names in _os.walk(project, followlinks=False):
            dirs[:] = [d for d in dirs if d.lower() not in _IGNORE_PARTS
                       and d.lower() not in {".venv", "venv"}
                       and not Path(directory, d).is_symlink()]
            for name in sorted(names):
                path = Path(directory, name)
                try:
                    stat = path.stat()
                except OSError:
                    continue  # atomic replace/delete in progress; next scan catches it
                files.append((str(path.relative_to(project)), stat.st_mtime_ns, stat.st_size))
        result[project.name] = tuple(sorted(files))
    return result


async def _watch_native() -> None:
    """Native fast path; reconciliation takes over on resource exhaustion."""
    try:
        from watchfiles import awatch
    except ImportError:
        logger.warning("Backlot: watchfiles unavailable; using filesystem reconciliation")
        return
    while True:
        try:
            if PROJECTS_DIR.is_dir():
                async for changes in awatch(PROJECTS_DIR, recursive=True, step=400):
                    touched = {_project_of_change(path) for _, path in changes}
                    for pid in touched - {None}:
                        _invalidate_summary(pid)
                        hub.publish(pid)
        except Exception as exc:
            # RustNotify wraps OS errors, so errno alone is insufficient.
            message = str(exc).lower()
            if (getattr(exc, "errno", None) in {errno.EMFILE, errno.ENFILE, errno.ENOSPC}
                    or any(marker in message for marker in (
                        "too many open files", "os error 24", "os error 23",
                        "os error 28", "no space left on device",
                        "inotify watch limit", "inotify instance limit",
                    ))):
                logger.warning(
                    "Backlot native watcher disabled for this server session: %s; "
                    "filesystem reconciliation remains active every %s seconds. "
                    "Restart Backlot after resolving OS file/inotify limits to retry.",
                    exc, RECONCILE_SECONDS,
                )
                return
            logger.exception("Backlot native watcher failed; retrying (reconciliation remains active)")
        await asyncio.sleep(RECONCILE_SECONDS)


async def _watch_projects() -> None:
    """Native notifications plus periodic recovery of missed filesystem changes."""
    previous = {}
    # A new lifespan must not reuse summaries from an earlier watch session.
    _summary_cache.clear()
    native = asyncio.create_task(_watch_native())
    try:
        while True:
            try:
                current = await asyncio.to_thread(_project_signatures)
            except OSError:
                logger.exception("Backlot filesystem reconciliation failed; retrying")
                await asyncio.sleep(RECONCILE_SECONDS)
                continue
            for pid in previous.keys() | current.keys():
                if previous.get(pid) != current.get(pid):
                    _invalidate_summary(pid)
                    hub.publish(pid)
            previous = current
            await asyncio.sleep(RECONCILE_SECONDS)
    finally:
        native.cancel()
        with suppress(asyncio.CancelledError):
            await native


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Own and cleanly stop the project watcher with FastAPI's lifespan API."""

    task = asyncio.create_task(_watch_projects())
    app.state.watch_task = task
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


def create_app() -> FastAPI:
    app = FastAPI(title="Backlot", docs_url=None, redoc_url=None, lifespan=_lifespan)

    # ---- API ----------------------------------------------------------

    @app.get("/api/health")
    async def health() -> dict:
        return {"ok": True, "app": "backlot"}

    @app.get("/api/projects")
    async def projects() -> list:
        return await asyncio.to_thread(_cached_summaries)

    @app.get("/api/project/{project_id}/state")
    async def project_state(project_id: str) -> dict:
        project_dir = _safe_project_dir(project_id)
        return await asyncio.to_thread(load_board_state, project_dir)

    def same_origin(request: Request):
        origin = request.headers.get('origin')
        if origin and urlsplit(origin).netloc != request.url.netloc:
            raise HTTPException(status_code=403, detail='Yêu cầu phải gửi từ Backlot đang mở.')

    async def file_operation(project_id, operation, *args, changed=False):
        try:
            result = await asyncio.to_thread(operation, _safe_project_dir(project_id), *args)
        except CopywriterError as exc:
            raise HTTPException(status_code=exc.status, detail=str(exc))
        except OSError:
            raise HTTPException(status_code=500, detail='Không truy cập được tệp. Kiểm tra quyền đọc/ghi của project.')
        if changed:
            _invalidate_summary(project_id)
            hub.publish(project_id)
        return result

    @app.get('/api/project/{project_id}/files/revision')
    async def file_revision(project_id: str, path: str):
        from backlot.file_manager import file_revision
        return await file_operation(project_id, file_revision, path)

    @app.post('/api/project/{project_id}/files/delete')
    async def file_delete(project_id: str, body: FileDeleteRequest, request: Request):
        same_origin(request)
        from backlot.file_manager import delete_file
        return await file_operation(project_id, delete_file, body.path, body.expected_revision, changed=True)

    @app.post('/api/project/{project_id}/posting-support')
    async def posting_support(project_id: str, body: SupportRequest, request: Request):
        same_origin(request)
        from backlot.posting_support import create_support
        return await file_operation(project_id, create_support, body.expected_revision, changed=True)

    @app.post('/api/project/{project_id}/posted')
    async def posted_confirmation(project_id: str, body: PostedRequest, request: Request):
        same_origin(request)
        from backlot.posted import confirm_posted
        return await file_operation(project_id, confirm_posted, body.platform, body.confirmed,
                                    body.url, body.expected_revision, changed=True)

    @app.post('/api/project/{project_id}/thumbnail')
    async def thumbnail_selection(project_id: str, body: PathRequest, request: Request):
        same_origin(request)
        from backlot.posting_support import select_thumbnail
        return await file_operation(project_id, select_thumbnail, body.path, changed=True)

    @app.post('/api/project/{project_id}/title')
    async def edit_project_title(project_id: str, body: TitleRevisionRequest, request: Request) -> dict:
        origin = request.headers.get('origin')
        if origin and urlsplit(origin).netloc != request.url.netloc:
            raise HTTPException(status_code=403, detail='Yêu cầu phải gửi từ Backlot đang mở.')
        from backlot.project_title import save_title
        try:
            result = await asyncio.to_thread(save_title, _safe_project_dir(project_id), body.title, body.expected_title)
        except CopywriterError as exc:
            raise HTTPException(status_code=exc.status, detail=str(exc))
        _invalidate_summary(project_id)
        hub.publish(project_id)
        return result

    @app.post('/api/project/{project_id}/posting-copy/title')
    async def video_title(project_id: str, body: VideoTitleRequest, request: Request):
        same_origin(request)
        from backlot.copywriter import save_video_title
        return await file_operation(project_id, save_video_title, body.title, body.expected_revision, changed=True)

    @app.post('/api/project/{project_id}/posting-copy/regenerate')
    async def regenerate_posting_copy(project_id: str, body: CopyRevisionRequest, request: Request) -> dict:
        origin = request.headers.get('origin')
        if origin and urlsplit(origin).netloc != request.url.netloc:
            raise HTTPException(status_code=403, detail='Yêu cầu phải gửi từ Backlot đang mở.')
        project = _safe_project_dir(project_id)
        if not body.instruction.strip():
            raise HTTPException(status_code=422, detail='Hãy nhập yêu cầu chỉnh sửa.')
        try:
            result = await asyncio.to_thread(regenerate, project, body.field, body.instruction.strip(), body.expected_revision)
        except CopywriterError as exc:
            raise HTTPException(status_code=exc.status, detail=str(exc))
        except OSError:
            raise HTTPException(status_code=500, detail='Không lưu được nội dung mới. Hãy kiểm tra quyền ghi của thư mục project.')
        _invalidate_summary(project_id)
        hub.publish(project_id)
        return result

    @app.get("/api/project/{project_id}/events")
    async def project_events(project_id: str, request: Request) -> StreamingResponse:
        _safe_project_dir(project_id)  # 404 early for unknown projects

        async def stream():
            q = hub.subscribe(project_id)
            try:
                yield _sse({"type": "hello", "project_id": project_id})
                while True:
                    if await request.is_disconnected():
                        return
                    try:
                        await asyncio.wait_for(q.get(), timeout=SSE_HEARTBEAT_SECONDS)
                    except asyncio.TimeoutError:
                        yield _sse({"type": "heartbeat", "ts": time.time()})
                        continue
                    # Coalesce bursts: drain anything else queued.
                    while not q.empty():
                        try:
                            q.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    yield _sse({"type": "change", "project_id": project_id})
            finally:
                hub.unsubscribe(q)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        })

    @app.get("/api/library/events")
    async def library_events(request: Request) -> StreamingResponse:
        async def stream():
            q = hub.subscribe()
            try:
                yield _sse({"type": "hello"})
                while True:
                    if await request.is_disconnected():
                        return
                    try:
                        changed = await asyncio.wait_for(q.get(), timeout=SSE_HEARTBEAT_SECONDS)
                    except asyncio.TimeoutError:
                        yield _sse({"type": "heartbeat", "ts": time.time()})
                        continue
                    while not q.empty():
                        try:
                            q.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    yield _sse({"type": "change", "project_id": changed})
            finally:
                hub.unsubscribe(q)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        })

    # ---- Thumbnails (downscaled, cached on disk) ------------------------

    @app.get("/thumb/{project_id}/{file_path:path}")
    async def thumb(project_id: str, file_path: str, w: int = 640) -> FileResponse:
        project_dir = _safe_project_dir(project_id)
        target = (project_dir / file_path).resolve()
        try:
            target.relative_to(project_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="path escapes project")
        if not target.is_file():
            raise HTTPException(status_code=404, detail="media not found")
        width = min(THUMB_WIDTHS, key=lambda x: abs(x - w))
        cached = await asyncio.to_thread(_thumbnail_for, target, width)
        if cached is None:
            # Never fall back to raw video bytes for an <img> consumer (F-03);
            # non-thumbable images are safe to serve as-is.
            if target.suffix.lower() in {".mp4", ".webm", ".mov"}:
                raise HTTPException(status_code=404, detail="no poster frame available")
            return FileResponse(target)
        return FileResponse(cached, media_type="image/jpeg")

    # ---- Media (range requests handled by FileResponse) ---------------

    @app.get("/media/{project_id}/{file_path:path}")
    async def media(project_id: str, file_path: str) -> FileResponse:
        project_dir = _safe_project_dir(project_id)
        target = (project_dir / file_path).resolve()
        try:
            target.relative_to(project_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="path escapes project")
        if not target.is_file():
            raise HTTPException(status_code=404, detail="media not found")
        return FileResponse(target)

    # ---- UI ------------------------------------------------------------

    @app.get("/p/{project_id}")
    async def board_page(project_id: str) -> HTMLResponse:
        return _ui_html("board.html", ("board.css", "board.js"))

    @app.get("/p/{project_path:path}")
    async def board_page_path(project_path: str) -> HTMLResponse:
        return _ui_html("board.html", ("board.css", "board.js"))

    @app.get("/")
    async def library_page() -> HTMLResponse:
        return _ui_html("index.html", ("board.css", "library.js"))

    @app.get('/ui/tokens.css')
    def studio_tokens():
        return FileResponse(REPO_ROOT / 'tokens.css', media_type='text/css')

    if UI_DIR.is_dir():
        app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")

    # The board is a long-lived SPA: a tab keeps running whatever board.js it
    # loaded, and browsers heuristically cache /ui assets. no-cache forces a
    # conditional revalidation (cheap 304 via ETag) on every load so UI fixes
    # show up on a plain refresh. Media/thumb URLs can be overwritten in place:
    # revalidate those too so updated bytes aren't hidden by browser caching.
    @app.middleware("http")
    async def ui_no_cache(request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path == "/" or path.startswith("/ui") or path.startswith("/p/"):
            response.headers["Cache-Control"] = "no-cache"
        elif path.startswith(("/media/", "/thumb/")):
            response.headers["Cache-Control"] = "no-cache"
        elif path.startswith("/api/") and not path.endswith("/events"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app


def _safe_project_dir(project_id: str) -> Path:
    # ':' rejects Windows drive-relative ids like "C:" (PROJECTS_DIR / "C:"
    # collapses back to PROJECTS_DIR itself).
    if any(c in project_id for c in "/\\:") or project_id in (".", ".."):
        raise HTTPException(status_code=400, detail="invalid project id")
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"unknown project: {project_id}")
    return project_dir


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _thumbnail_for(source: Path, width: int) -> Optional[Path]:
    """Downscale an image (or extract a video poster frame) to a cached JPEG."""
    suffix = source.suffix.lower()
    is_image = suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    is_video = suffix in {".mp4", ".webm", ".mov"}
    if not (is_image or is_video):
        return None
    try:
        import hashlib
        stat = source.stat()
        key = hashlib.sha1(
            f"{source}|{stat.st_mtime_ns}|{stat.st_size}|{width}".encode()
        ).hexdigest()[:20]
        cached = THUMB_CACHE_DIR / f"{key}.jpg"
        if cached.is_file():
            return cached
        THUMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # Unique temp per request — concurrent misses for the same source
        # must not write (and replace from) the same temp file.
        import uuid
        tmp = THUMB_CACHE_DIR / f"{key}.{uuid.uuid4().hex[:8]}.tmp.jpg"
        if is_video:
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-ss", "1.5",
                 "-i", str(source), "-frames:v", "1",
                 "-vf", f"scale={width}:-2", str(tmp)],
                capture_output=True, timeout=30,
            )
            if result.returncode != 0 or not tmp.is_file():
                return None
        else:
            from PIL import Image
            with Image.open(source) as img:
                img = img.convert("RGB")
                img.thumbnail((width, width * 3))
                img.save(tmp, "JPEG", quality=82)
        tmp.replace(cached)
        return cached
    except Exception:
        return None


app = create_app()
