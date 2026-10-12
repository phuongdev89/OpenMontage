from pathlib import Path
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from tools.base_tool import ToolResult

from tools.video.video_compose import VideoCompose


def test_cross_project_audio_is_rejected_before_render(tmp_path, monkeypatch):
    root = tmp_path / 'projects'
    a, b = root / 'a', root / 'b'
    for project in (a, b):
        project.mkdir(parents=True)
        (project / 'project.json').write_text('{}')
    audio = b / 'narration.wav'
    audio.write_bytes(b'foreign audio')
    called = []
    def compose(*args):
        called.append(True)
        return ToolResult(success=True)
    monkeypatch.setattr(VideoCompose, '_compose', compose)
    result = VideoCompose().execute({'operation': 'compose', 'output_path': str(a / 'renders/video.mp4'), 'audio_path': str(audio)})
    assert not called
    assert not result.success
    assert 'outside' in result.error


def test_project_local_audio_is_accepted(tmp_path):
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'project.json').write_text('{}')
    audio = project / 'narration.wav'
    audio.write_bytes(b'local')
    assert VideoCompose._validate_project_media({'output_path': str(project / 'renders/video.mp4'), 'audio_path': str(audio)}) is None


def test_parallel_renders_in_same_directory_keep_their_props(tmp_path, monkeypatch):
    monkeypatch.setattr(VideoCompose, '_mirror_public_dir', lambda *args: None)
    barrier = threading.Barrier(2)
    received = {}
    def render(marker):
        tool = VideoCompose()
        def run(cmd, **kwargs):
            props = Path(next(arg.split('=', 1)[1] for arg in cmd if arg.startswith('--props=')))
            barrier.wait(timeout=10)
            received[marker] = json.loads(props.read_text())['marker']
            barrier.wait(timeout=10)
            Path(cmd[5]).write_bytes(b'video')
        monkeypatch.setattr(tool, 'run_command', run)
        return tool._remotion_render({'output_path': str(tmp_path / f'{marker}.mp4'), 'composition_data': {'marker': marker, 'cuts': []}})
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(render, ('a', 'b')))
    assert all(result.success for result in results), [r.error for r in results]
    assert received == {'a': 'a', 'b': 'b'}


def test_public_snapshot_survives_source_overwrite(tmp_path):
    source = tmp_path / 'public'
    source.mkdir()
    (source / 'voice.mp3').write_bytes(b'audio A')
    snapshot = tmp_path / 'snapshot'
    VideoCompose._mirror_public_dir(source, snapshot)
    (source / 'voice.mp3').write_bytes(b'audio B')
    assert (snapshot / 'voice.mp3').read_bytes() == b'audio A'
