"""Read-only, project-scoped handoff for published videos."""
from pathlib import Path


def build_publish_package(project: Path, publish_log: dict, completed: bool) -> dict | None:
    if not completed:
        return None
    project = project.resolve()
    extra = publish_log.get('metadata')
    extra = extra if isinstance(extra, dict) else {}
    packaging = extra.get('posting_package')
    packaging = packaging if isinstance(packaging, dict) else {}
    entries = publish_log.get('entries')
    entries = entries if isinstance(entries, list) else []
    metadata = next((e['metadata_used'] for e in entries if isinstance(e, dict) and e.get('status') in ('exported', 'published') and isinstance(e.get('metadata_used'), dict)), {})

    def file_info(raw):
        if not isinstance(raw, str) or not raw:
            return None
        path = Path(raw)
        if not path.is_absolute():
            # Canonical project-relative paths and historical repo-relative paths.
            parts = path.parts
            if len(parts) > 2 and parts[0] == 'projects' and parts[1] == project.name:
                path = project.joinpath(*parts[2:])
            else:
                path = project / path
        path = path.resolve()
        try:
            if not path.is_relative_to(project) or not path.is_file():
                return None
            stat = path.stat()
            if not stat.st_size:
                return None
            return {'path': path.relative_to(project).as_posix(), 'absolute_path': str(path),
                    'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
        except OSError:
            return None

    videos = {}
    for ratio in ('portrait', 'landscape'):
        info = file_info(f'exports/video/video-{ratio}.mp4')
        if info:
            videos[ratio] = info
    thumbnails = []
    supplied = packaging.get('thumbnails')
    supplied = supplied if isinstance(supplied, list) else []
    for thumbnail in supplied:
        if not isinstance(thumbnail, dict):
            continue
        info = file_info(thumbnail.get('path'))
        if info:
            thumbnails.append({**info, 'generated': thumbnail.get('method') == 'image-generate', 'provider': thumbnail.get('provider'), 'label': thumbnail.get('label') or 'Thumbnail', 'prompt': thumbnail.get('prompt') or ''})
    known = {t['path'] for t in thumbnails}
    for path in sorted((project / 'exports/thumbnails').rglob('*')):
        if path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.gif'):
            info = file_info(str(path))
            if info and info['path'] not in known:
                thumbnails.append({**info, 'generated': False, 'label': path.name})
                known.add(info['path'])
    def text(value):
        return value if isinstance(value, str) else ''
    description = text(packaging.get('description')) or text(metadata.get('description'))
    if not packaging.get('description'):
        chapters = metadata.get('chapters')
        chapters = chapters if isinstance(chapters, list) else []
        chapter_text = '\n'.join(f"{c['start_time']} {c['title']}" for c in chapters if isinstance(c, dict) and c.get('start_time') and c.get('title'))
        tags = metadata.get('hashtags')
        hashtags = ' '.join(t for t in tags if isinstance(t, str)) if isinstance(tags, list) else ''
        description = '\n\n'.join(x for x in (description, chapter_text, hashtags) if x)
    package = {'title': text(packaging.get('title')) or text(metadata.get('title')), 'description': description,
            'caption': text(packaging.get('caption')) or text(metadata.get('caption')),
            'thumbnails': thumbnails, 'videos': videos}
    from backlot.posting_support import read_support, selected_thumbnail, package_revision
    support = read_support(project)
    for name in ('title', 'description', 'caption'):
        if not package[name]:
            package[name] = text(support.get(name))
    recorded_prompt = text(packaging.get('thumbnail_prompt')) or next((text(t.get('prompt')) for t in supplied
                if isinstance(t, dict) and text(t.get('prompt'))), '')
    prompt = recorded_prompt or text(support.get('thumbnail_prompt'))
    package['thumbnail_prompt_source'] = 'recorded' if recorded_prompt else 'prepared' if prompt else 'draft'
    if not prompt:
        from backlot.state import REPO_ROOT
        try:
            template = (REPO_ROOT / 'skills/pipelines/shared/thumbnail-prompt.txt').read_text(encoding='utf-8')
        except OSError:
            template = 'Create a concept-led curiosity scene. {{HOOK_SCENE}}. No answer or completed solution.'
        topic = package['title'] or project.name
        prompt = template.replace('{{HOOK_SCENE}}', f'Chủ đề video: {topic}. Chọn nhân vật, đạo cụ và bối cảnh đúng chủ đề; thể hiện một câu hỏi chưa được giải đáp. Không đưa đáp án hoặc phép giải hoàn tất vào ảnh.')
    package['thumbnail_prompt'] = prompt
    selected = selected_thumbnail(project)
    if selected not in {t['path'] for t in thumbnails}:
        selected = thumbnails[0]['path'] if thumbnails else None
    package['selected_thumbnail'] = selected
    selected_prompt = next((t.get('prompt') for t in thumbnails if t['path'] == selected and t.get('prompt')), None)
    if selected_prompt:
        package['thumbnail_prompt'] = selected_prompt
        package['thumbnail_prompt_source'] = 'recorded'
    for thumb in thumbnails:
        thumb['selected'] = thumb['path'] == selected
        thumb.setdefault('prompt', prompt)
    from backlot.copywriter import read_copy, revision, CopywriterError
    try:
        fields = read_copy(project).get('fields') or {}
        for name in ('title', 'caption', 'description'):
            if isinstance(fields.get(name), str):
                package[name] = fields[name]
    except CopywriterError:
        package['copy_warning'] = 'Không đọc được nội dung chỉnh sửa đã lưu.'
    package['revisions'] = {name: revision(package[name]) for name in ('title', 'caption', 'description')}
    package['support_revision'] = package_revision(package)
    return package
