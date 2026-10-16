"""Manual upload confirmations. Never upload or clean files automatically."""
import json
from datetime import datetime, timezone
from pathlib import Path

from backlot.copywriter import CopywriterError, _storage_lock, revision
from lib.checkpoint import read_checkpoint, write_checkpoint, CheckpointValidationError
from lib.posting_status import PLATFORMS, validate_post_url


def posting_state(project: Path) -> dict:
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
        return posting_state(project)
