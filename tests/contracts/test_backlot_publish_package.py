import json
import pytest
from jsonschema import ValidationError
from schemas.artifacts import validate_artifact
from backlot.publish_package import build_publish_package


def test_published_handoff_is_scoped_and_preserves_caption(tmp_path):
    project = tmp_path / 'a'
    project.mkdir()
    video = project / 'exports/video/video-portrait.mp4'
    video.parent.mkdir(parents=True)
    video.write_bytes(b'video')
    thumb = project / 'exports/thumbnails/hero.png'
    thumb.parent.mkdir(parents=True)
    thumb.write_bytes(b'image')
    log = {'entries': [], 'metadata': {'posting_package': {
        'title': 'A puzzle', 'description': 'Full details', 'caption': 'Try it!',
        'thumbnails': [{'path': 'exports/thumbnails/hero.png', 'method': 'image-generate', 'provider': 'built-in'}]}}}
    assert build_publish_package(project, log, False) is None
    package = build_publish_package(project, log, True)
    assert package['caption'] == 'Try it!'
    assert package['videos']['portrait']['absolute_path'] == str(video.resolve())
    assert package['thumbnails'][0]['generated']


def test_foreign_thumbnail_cannot_be_served(tmp_path):
    foreign = tmp_path / 'foreign.png'
    foreign.write_bytes(b'image')
    project = tmp_path / 'a'
    project.mkdir()
    log = {'metadata': {'posting_package': {'thumbnails': [{'path': str(foreign)}]}}}
    assert build_publish_package(project, log, True)['thumbnails'] == []


def test_legacy_metadata_formats_chapters_without_inventing_caption(tmp_path):
    log = {'entries': [{'status': 'exported', 'metadata_used': {'title': 'Legacy', 'description': 'Text', 'chapters': [{'start_time': '00:00', 'title': 'Hook'}], 'hashtags': ['#Math']}}]}
    package = build_publish_package(tmp_path, log, True)
    assert package['description'] == 'Text\n\n00:00 Hook\n\n#Math'
    assert package['caption'] == ''


def test_sparse_or_malformed_log_does_not_break_board(tmp_path):
    log = {'entries': [None, {'status': 'exported', 'metadata_used': {'chapters': 1, 'hashtags': 2}}], 'metadata': {'posting_package': {'thumbnails': 5}}}
    assert build_publish_package(tmp_path, log, True)['caption'] == ''


def test_schema_requires_independent_caption_and_generated_thumbnail():
    package = {'title': 'Hook', 'description': 'Details', 'caption': 'Social hook', 'thumbnails': [{'path': 'exports/thumbnails/hero.png', 'method': 'image-generate', 'provider': 'built-in', 'prompt': 'Exact prompt', 'review': {'hook': 'PASS'}}]}
    log = {'version': '1.0', 'entries': [], 'metadata': {'posting_package': package}}
    validate_artifact('publish_log', log)
    package['thumbnails'][0]['method'] = 'video-frame'
    with pytest.raises(ValidationError):
        validate_artifact('publish_log', log)
    package['thumbnails'][0]['method'] = 'image-generate'
    del package['caption']
    with pytest.raises(ValidationError):
        validate_artifact('publish_log', log)
