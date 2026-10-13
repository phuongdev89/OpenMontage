"""Project-local file operations with revision checks and reversible deletion."""
from __future__ import annotations
import base64
import hashlib
import json
import os
import tempfile
import threading
import uuid
from pathlib import Path
from backlot.copywriter import CopywriterError

MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TEXT_BYTES = 2 * 1024 * 1024
EXCLUDED = {'.git', 'node_modules', '__pycache__', '.cache', '.venv', 'venv', '.backlot-trash'}
_lock = threading.RLock()


def resolve_file(project: Path, raw: str, *, writable=False) -> Path:
    rel = Path(raw)
    if not raw or rel.is_absolute() or any(x in raw for x in ('\\', ':')) or '..' in rel.parts:
        raise CopywriterError('Đường dẫn tệp không hợp lệ.', 400)
    if any(p.lower() in EXCLUDED or p.startswith('.') for p in rel.parts):
        raise CopywriterError('Thư mục nội bộ không được quản lý tại đây.', 403)
    target = (project / rel).resolve()
    if not target.is_relative_to(project.resolve()) or target == project.resolve():
        raise CopywriterError('Đường dẫn nằm ngoài project.', 403)
    if writable and (protected(target) or protected(rel)):
        raise CopywriterError('Checkpoint và cấu hình project chỉ được sửa qua pipeline.', 403)
    return target


def protected(path: Path) -> bool:
    return path.name.lower() == 'project.json' or path.name.lower().startswith('checkpoint_')


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def file_revision(project: Path, raw: str) -> dict:
    path = resolve_file(project, raw)
    if not path.is_file():
        raise CopywriterError('Không tìm thấy tệp.', 404)
    checksum = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            checksum.update(chunk)
    return {'revision': checksum.hexdigest()}


def atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.backlot-write-', delete=False) as f:
            temporary = Path(f.name)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def list_files(project: Path) -> list[dict]:
    result = []
    for directory, dirs, names in os.walk(project, followlinks=False):
        dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED and not d.startswith('.')
                   and not Path(directory, d).is_symlink()]
        for name in sorted(names):
            path = Path(directory, name)
            if name.startswith('.') or path.is_symlink():
                continue
            try:
                stat = path.stat()
                result.append({'path': path.relative_to(project).as_posix(), 'size': stat.st_size,
                               'mtime': stat.st_mtime, 'protected': protected(path)})
            except OSError:
                continue
    return sorted(result, key=lambda f: f['path'])


def read_file(project: Path, raw: str) -> dict:
    path = resolve_file(project, raw)
    if not path.is_file():
        raise CopywriterError('Không tìm thấy tệp.', 404)
    if path.stat().st_size > MAX_TEXT_BYTES:
        raise CopywriterError('Tệp lớn hơn 2 MB. Hãy tải về để chỉnh sửa.', 413)
    content = path.read_bytes()
    try:
        text = content.decode('utf-8')
        if '\x00' in text:
            raise UnicodeError()
    except UnicodeError:
        raise CopywriterError('Tệp nhị phân. Dùng Xem hoặc Tải xuống.', 415)
    return {'path': raw, 'content': text, 'revision': digest(content), 'protected': protected(path)}


def write_file(project: Path, raw: str, content: bytes, expected: str | None) -> dict:
    path = resolve_file(project, raw, writable=True)
    if len(content) > MAX_FILE_BYTES:
        raise CopywriterError('Tệp vượt giới hạn 16 MB.', 413)
    with _lock:
        if path.exists():
            if not path.is_file() or expected is None or file_revision(project, raw)['revision'] != expected:
                raise CopywriterError('Tệp đã tồn tại hoặc đã đổi. Mở lại trước khi ghi đè.', 409)
        elif expected is not None:
            raise CopywriterError('Tệp đã bị xóa. Mở lại danh sách.', 409)
        atomic_bytes(path, content)
    return {'path': raw, 'revision': digest(content)}


def delete_file(project: Path, raw: str, expected: str) -> dict:
    path = resolve_file(project, raw, writable=True)
    with _lock:
        if not path.is_file():
            raise CopywriterError('Không tìm thấy tệp.', 404)
        if file_revision(project, raw)['revision'] != expected:
            raise CopywriterError('Tệp đã đổi. Mở lại trước khi xóa.', 409)
        token = uuid.uuid4().hex
        trash = project / '.backlot-trash'
        if trash.is_symlink():
            raise CopywriterError('Thư mục khôi phục không hợp lệ.', 403)
        trash.mkdir(exist_ok=True)
        atomic_bytes(trash / (token + '.json'), json.dumps({'path': raw}).encode())
        os.replace(path, trash / (token + '.bin'))
    return {'path': raw, 'undo_token': token}


def restore_file(project: Path, token: str) -> dict:
    if len(token) != 32 or any(c not in '0123456789abcdef' for c in token):
        raise CopywriterError('Mã khôi phục không hợp lệ.', 400)
    trash = project / '.backlot-trash'
    if trash.is_symlink():
        raise CopywriterError('Thư mục khôi phục không hợp lệ.', 403)
    with _lock:
        try:
            info = json.loads((trash / (token + '.json')).read_text())
            target = resolve_file(project, info['path'], writable=True)
            if target.exists():
                raise CopywriterError('Đường dẫn đã có tệp mới; không ghi đè khi khôi phục.', 409)
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(trash / (token + '.bin'), target)
            (trash / (token + '.json')).unlink()
        except FileNotFoundError:
            raise CopywriterError('Không còn tệp để khôi phục.', 404)
    return {'path': info['path']}


def decode_upload(content: str) -> bytes:
    try:
        return base64.b64decode(content, validate=True)
    except ValueError:
        raise CopywriterError('Dữ liệu upload không hợp lệ.', 422)
