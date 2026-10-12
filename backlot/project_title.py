"""Presentation title overrides, independent of production timestamps."""
import json, os
from pathlib import Path
from backlot.copywriter import CopywriterError, _storage_lock


def read_title(project):
    try:
        data = json.loads((Path(project) / 'display_title.json').read_text(encoding='utf-8'))
        return data.get('title') if data.get('project_id') == Path(project).name else None
    except (OSError, ValueError):
        return None


def save_title(project, title, expected_title):
    from backlot.state import load_board_state
    title = title.strip()
    if not title or len(title) > 300:
        raise CopywriterError('Tiêu đề phải có từ 1 đến 300 ký tự.', 422)
    with _storage_lock(project):
        state = load_board_state(project)
        if not any(s['name'] in ('compose','publish') and s['status']=='completed' for s in state['stages']):
            raise CopywriterError('Chỉ sửa tiêu đề sau compose hoặc publish.', 409)
        if state['title'] != expected_title:
            raise CopywriterError('Tiêu đề đã thay đổi. Hãy tải lại trang.', 409)
        path = Path(project) / 'display_title.json'
        temporary = path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps({'project_id':Path(project).name,'title':title},ensure_ascii=False),encoding='utf-8')
        os.replace(temporary,path)
    return {'title':title}
