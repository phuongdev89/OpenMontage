"""Resolve output switches once per project; preserve legacy project outputs."""
from __future__ import annotations

import json
import os
from pathlib import Path

from lib.env_loader import load_env

VIDEO_FORMATS = {
    'landscape': {'width': 1920, 'height': 1080, 'filename': 'video-landscape.mp4'},
    'portrait': {'width': 1080, 'height': 1920, 'filename': 'video-portrait.mp4'},
}


def configured_output_formats() -> list[str]:
    """Read strict booleans; reject an empty delivery before creating a project."""
    load_env()
    enabled = []
    for ratio in VIDEO_FORMATS:
        key = 'OUTPUT_VIDEO_' + ratio.upper()
        value = os.environ.get(key, 'true').strip().lower()
        if value not in ('true', 'false'):
            raise ValueError(f'{key} must be true or false')
        if value == 'true':
            enabled.append(ratio)
    if not enabled:
        raise ValueError('At least one OUTPUT_VIDEO_LANDSCAPE / OUTPUT_VIDEO_PORTRAIT must be true')
    return enabled


def project_output_formats(project_dir: Path) -> list[str]:
    """Use the run's frozen selection. Legacy projects keep both formats."""
    marker = json.loads((Path(project_dir) / 'project.json').read_text(encoding='utf-8'))
    formats = marker.get('output_video_formats', ['landscape', 'portrait'])
    if not isinstance(formats, list) or not formats or len(formats) != len(set(formats)) or any(x not in VIDEO_FORMATS for x in formats):
        raise ValueError('Invalid project output_video_formats')
    return list(formats)


def validate_output_destination(output_path: str | Path) -> None:
    """Reject a disabled canonical output before a pipeline tool renders it."""
    path = Path(output_path).resolve()
    ratio = next((name for name, spec in VIDEO_FORMATS.items() if path.name == spec['filename']), None)
    if ratio is None:
        return
    project = next((parent for parent in path.parents if (parent / 'project.json').is_file()), None)
    if project is not None and ratio not in project_output_formats(project):
        raise ValueError(f'{ratio} output is disabled for project {project.name}')
