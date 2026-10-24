"""Manual upload confirmations. Never upload or clean files automatically."""
import json
from datetime import datetime, timezone
from pathlib import Path

from backlot.copywriter import CopywriterError, _storage_lock, revision
from lib.checkpoint import read_checkpoint, write_checkpoint, CheckpointValidationError
from lib.posting_status import PLATFORMS, validate_post_url


def sync_posted_from_calendar(project: Path) -> bool:
    """Detect published links from calendar.json and sync them into posted checkpoint.

    Returns True if any updates were written, False otherwise.
    """
    cal_file = project / "calendar.json"
    if not cal_file.is_file():
        return False

    try:
        data = json.loads(cal_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return False
    except (OSError, ValueError):
        return False

    links_by_platform: dict[str, str] = {}
    raw_links = data.get("published_links")
    if isinstance(raw_links, list):
        for item in raw_links:
            if isinstance(item, dict) and item.get("url"):
                p = (item.get("platform") or "web").lower().strip()
                u = item.get("url", "").strip()
                if p in PLATFORMS and u:
                    links_by_platform[p] = u
            elif isinstance(item, str) and item.strip().startswith("http"):
                u = item.strip()
                p = "youtube" if ("youtube" in u or "youtu.be" in u) else ("facebook" if "facebook" in u else None)
                if p in PLATFORMS and u:
                    links_by_platform[p] = u

    pub_url = (data.get("published_url") or "").strip()
    if pub_url:
        p = "youtube" if ("youtube" in pub_url or "youtu.be" in pub_url) else ("facebook" if "facebook" in pub_url else None)
        if p in PLATFORMS and p not in links_by_platform:
            links_by_platform[p] = pub_url

    if not links_by_platform:
        return False

    # Checkpoint 'posted' requires completed 'publish' stage
    try:
        cp_publish = read_checkpoint(project.parent, project.name, 'publish')
        if not cp_publish or cp_publish.get('status') != 'completed':
            return False
    except Exception:
        return False

    try:
        cp = read_checkpoint(project.parent, project.name, 'posted')
    except (ValueError, OSError):
        cp = None

    log = cp['artifacts']['posted_log'] if cp else {p: {'confirmed': False, 'url': '', 'confirmed_at': None} for p in PLATFORMS}
    changed = False
    published_at = data.get("published_at") or datetime.now(timezone.utc).isoformat()

    for platform, url in links_by_platform.items():
        current_record = log.get(platform) or {}
        if not current_record.get('confirmed') or not current_record.get('url'):
            try:
                valid_url = validate_post_url(platform, url)
                if platform == 'facebook':
                    from lib.embed_urls import resolve_facebook_canonical_url
                    canonical, vid = resolve_facebook_canonical_url(valid_url)
                    if vid and canonical:
                        valid_url = canonical
                log[platform] = {
                    'confirmed': True,
                    'url': valid_url,
                    'confirmed_at': current_record.get('confirmed_at') or published_at,
                    'source': 'backlot_manual'
                }
                changed = True
            except Exception:
                pass

    if changed:
        status = 'completed' if all(log[p]['confirmed'] for p in PLATFORMS) else 'awaiting_human'
        try:
            write_checkpoint(project.parent, project.name, 'posted', status, {'posted_log': log},
                             metadata={'confirmation_source': 'backlot_manual'})
        except Exception:
            return False

        # Synchronize updated posted_links into completed_record if already cleaned
        try:
            cp_completed = read_checkpoint(project.parent, project.name, 'completed')
            if cp_completed and cp_completed.get('status') == 'completed':
                rec = cp_completed.get('artifacts', {}).get('completed_record')
                if isinstance(rec, dict):
                    rec_links = dict(rec.get('posted_links') or {})
                    for p in PLATFORMS:
                        if log[p]['confirmed']:
                            rec_links[p] = log[p]
                    rec['posted_links'] = rec_links
                    write_checkpoint(project.parent, project.name, 'completed', 'completed',
                                     {'completed_record': rec},
                                     metadata=cp_completed.get('metadata') or {})
        except Exception:
            pass
        return True

    return False


def posting_state(project: Path) -> dict:
    sync_posted_from_calendar(project)
    try:
        cp = read_checkpoint(project.parent, project.name, 'posted')
    except (ValueError, OSError):
        raise CopywriterError('Không đọc được checkpoint Đã đăng.', 409)
    log = cp['artifacts']['posted_log'] if cp else {p: {'confirmed': False, 'url': '', 'confirmed_at': None} for p in PLATFORMS}
    return {'status': cp['status'] if cp else 'pending', 'platforms': {
        p: {**log[p], 'revision': revision(json.dumps(log[p], sort_keys=True))} for p in PLATFORMS
    }, 'completed_at': cp['timestamp'] if cp and cp['status'] == 'completed' else None}


def confirm_posted(project: Path, platform: str, confirmed: bool, url: str, expected: str) -> dict:
    if platform not in PLATFORMS:
        raise CopywriterError('Nền tảng không hợp lệ.', 422)
    try:
        url = validate_post_url(platform, url) if confirmed or url.strip() else ''
        if confirmed and platform == 'facebook' and url:
            from lib.embed_urls import resolve_facebook_canonical_url
            canonical, vid = resolve_facebook_canonical_url(url)
            if vid and canonical:
                url = canonical
    except ValueError as exc:
        raise CopywriterError(str(exc), 422)
    with _storage_lock(project):
        current = posting_state(project)
        old = current['platforms'][platform]
        if old['revision'] != expected:
            raise CopywriterError('Trạng thái đăng đã thay đổi. Tải lại rồi lưu lại.', 409)
        log = {p: {k: v for k, v in r.items() if k != 'revision'} for p, r in current['platforms'].items()}
        log[platform] = {'confirmed': confirmed, 'url': url,
                         'confirmed_at': ((old.get('confirmed_at') if old['confirmed'] and old['url'] == url else None)
                         or datetime.now(timezone.utc).isoformat()) if confirmed else None,
                         'source': 'backlot_manual'}
        status = 'completed' if all(log[p]['confirmed'] for p in PLATFORMS) else 'awaiting_human'
        try:
            write_checkpoint(project.parent, project.name, 'posted', status, {'posted_log': log},
                             metadata={'confirmation_source': 'backlot_manual'})
        except (CheckpointValidationError, ValueError) as exc:
            raise CopywriterError(str(exc), 409)

        # Synchronize updated posted_links into completed_record if already cleaned
        try:
            cp_completed = read_checkpoint(project.parent, project.name, 'completed')
            if cp_completed and cp_completed.get('status') == 'completed':
                rec = cp_completed.get('artifacts', {}).get('completed_record')
                if isinstance(rec, dict):
                    rec_links = dict(rec.get('posted_links') or {})
                    rec_links[platform] = log[platform]
                    rec['posted_links'] = rec_links
                    write_checkpoint(project.parent, project.name, 'completed', 'completed',
                                     {'completed_record': rec},
                                     metadata=cp_completed.get('metadata') or {})
        except Exception:
            pass

        return posting_state(project)
