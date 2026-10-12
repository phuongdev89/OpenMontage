import json

import pytest

from lib import output_formats
from lib.checkpoint import init_project


@pytest.fixture(autouse=True)
def clean_config(monkeypatch):
    monkeypatch.setattr(output_formats, 'load_env', lambda: None)
    for key in ('OUTPUT_VIDEO_LANDSCAPE', 'OUTPUT_VIDEO_PORTRAIT'):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize('landscape,portrait,expected', [
    ('true', 'false', ['landscape']), ('false', 'true', ['portrait']),
    ('true', 'true', ['landscape', 'portrait']),
])
def test_init_freezes_output_selection(tmp_path, monkeypatch, landscape, portrait, expected):
    monkeypatch.setenv('OUTPUT_VIDEO_LANDSCAPE', landscape)
    monkeypatch.setenv('OUTPUT_VIDEO_PORTRAIT', portrait)
    project = init_project('test', title='Test', pipeline_type='animation', pipeline_dir=tmp_path)
    assert output_formats.project_output_formats(project) == expected
    monkeypatch.setenv('OUTPUT_VIDEO_LANDSCAPE', 'false')
    monkeypatch.setenv('OUTPUT_VIDEO_PORTRAIT', 'false')
    assert output_formats.project_output_formats(project) == expected


@pytest.mark.parametrize('landscape,portrait', [('false', 'false'), ('yes', 'true'), ('true', '')])
def test_invalid_config_does_not_create_project(tmp_path, monkeypatch, landscape, portrait):
    monkeypatch.setenv('OUTPUT_VIDEO_LANDSCAPE', landscape)
    monkeypatch.setenv('OUTPUT_VIDEO_PORTRAIT', portrait)
    with pytest.raises(ValueError):
        init_project('test', title='Test', pipeline_type='animation', pipeline_dir=tmp_path)
    assert not list(tmp_path.iterdir())


def test_legacy_project_keeps_both(tmp_path):
    (tmp_path/'project.json').write_text(json.dumps({'project_id': 'old'}))
    assert output_formats.project_output_formats(tmp_path) == ['landscape', 'portrait']


def test_compose_rejects_disabled_destination_before_render(tmp_path, monkeypatch):
    from tools.video.video_compose import VideoCompose
    monkeypatch.setenv('OUTPUT_VIDEO_PORTRAIT', 'false')
    project = init_project('test', title='Test', pipeline_type='animation', pipeline_dir=tmp_path)
    def must_not_render(*args):
        pytest.fail('Disabled output reached renderer')
    monkeypatch.setattr(VideoCompose, '_render', must_not_render)
    result = VideoCompose().execute({'operation': 'render', 'output_path': str(project/'renders/video-portrait.mp4')})
    assert not result.success
    assert 'portrait output is disabled' in result.error
    assert not (project/'renders/video-portrait.mp4').exists()
    output_formats.validate_output_destination(project/'renders/video-landscape.mp4')
