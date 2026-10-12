import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests
from fastapi.testclient import TestClient
from backlot import copywriter, server, state
from backlot.publish_package import build_publish_package


@pytest.fixture
def setup(tmp_path, monkeypatch):
    projects = tmp_path / 'projects'
    for name in ('a', 'b'):
        (projects / name / 'artifacts').mkdir(parents=True)
    monkeypatch.setattr(copywriter, 'load_env', lambda: None)
    for key, value in {'AI_CHAT_URL': 'https://provider.invalid/v1', 'AI_CHAT_KEY': 'private-test-key', 'AI_CHAT_MODEL': 'configured-model'}.items():
        monkeypatch.setenv(key, value)
    log = {'entries': [{'status': 'exported', 'metadata_used': {'title': 'Puzzle', 'description': 'Original description', 'caption': 'Original caption'}}]}
    def board(project):
        return {'project_id': project.name, 'title': 'Problem '+project.name,
                'artifacts': {'script': {'text': 'Source for '+project.name}},
                'publish_package': build_publish_package(project, log, True)}
    monkeypatch.setattr(state, 'load_board_state', board)
    monkeypatch.setattr(server, 'load_board_state', board)
    monkeypatch.setattr(server, 'PROJECTS_DIR', projects)
    async def no_watch():
        return None
    monkeypatch.setattr(server, '_watch_projects', no_watch)
    return projects, board


def response(text='New copy', status=200, sse=False):
    result = requests.Response(); result.status_code = status
    if sse:
        result._content = ('data: '+json.dumps({'choices': [{'delta': {'content': text}}]})+'\n\ndata: [DONE]\n').encode()
    else:
        result._content = json.dumps({'choices': [{'message': {'content': text}}]}).encode()
    return result


@pytest.mark.parametrize('field', ['caption', 'description'])
def test_regeneration_uses_config_and_project_context_then_persists(setup, monkeypatch, field):
    root, board = setup; captured = {}
    def post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return response('Correct new '+field)
    monkeypatch.setattr(copywriter.requests, 'post', post)
    with TestClient(server.create_app()) as client:
        before = board(root/'a')['publish_package']
        result = client.post('/api/project/a/posting-copy/regenerate', json={'field': field, 'instruction': 'Make a strong hook', 'expected_revision': before['revisions'][field]})
        assert result.status_code == 200, result.text
        assert captured['url'] == 'https://provider.invalid/v1/chat/completions'
        assert captured['json']['model'] == 'configured-model'
        prompt = captured['json']['messages'][1]['content']
        assert 'Source for a' in prompt and 'Source for b' not in prompt
        assert 'Make a strong hook' in prompt and before[field] in prompt
        assert board(root/'a')['publish_package'][field] == 'Correct new '+field
        other = 'description' if field == 'caption' else 'caption'
        assert board(root/'a')['publish_package'][other] == before[other]
        assert not (root/'b/artifacts/posting_copy.json').exists()
        assert 'private-test-key' not in (root/'a/artifacts/posting_copy.json').read_text()


def test_provider_error_and_empty_reply_do_not_overwrite(setup, monkeypatch):
    root, board = setup
    for reply in (response(status=429), response('')):
        monkeypatch.setattr(copywriter.requests, 'post', lambda *a, **k: reply)
        with pytest.raises(copywriter.CopywriterError):
            copywriter.regenerate(root/'a', 'caption', 'Shorter', board(root/'a')['publish_package']['revisions']['caption'])
        assert not (root/'a/artifacts/posting_copy.json').exists()


def test_invented_chapter_times_cannot_be_saved(setup, monkeypatch):
    root, board = setup
    monkeypatch.setattr(copywriter.requests, 'post', lambda *a, **k: response('Hook\n00:32 An invented chapter'))
    with pytest.raises(copywriter.CopywriterError, match='mốc chương'):
        copywriter.regenerate(root/'a', 'description', 'Full details', board(root/'a')['publish_package']['revisions']['description'])
    assert not (root/'a/artifacts/posting_copy.json').exists()


def test_stale_revision_and_cross_origin_are_rejected(setup, monkeypatch):
    root, board = setup
    monkeypatch.setattr(copywriter.requests, 'post', lambda *a, **k: pytest.fail('No provider call expected'))
    with TestClient(server.create_app()) as client:
        body = {'field': 'caption', 'instruction': 'Shorter', 'expected_revision': '0'*64}
        assert client.post('/api/project/a/posting-copy/regenerate', json=body).status_code == 409
        assert client.post('/api/project/a/posting-copy/regenerate', json=body, headers={'Origin': 'https://foreign.invalid'}).status_code == 403
        body['field'] = 'thumbnail'
        assert client.post('/api/project/a/posting-copy/regenerate', json=body).status_code == 422


def test_simultaneous_fields_merge_without_losing_either(setup, monkeypatch):
    root, board = setup; barrier = threading.Barrier(2)
    def post(url, **kwargs):
        barrier.wait(timeout=10)
        return response('Concurrent '+threading.current_thread().name, sse=True)
    monkeypatch.setattr(copywriter.requests, 'post', post)
    initial = board(root/'a')['publish_package']
    def run(field):
        return copywriter.regenerate(root/'a', field, 'New hook', initial['revisions'][field])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ('caption', 'description')))
    saved = copywriter.read_copy(root/'a')
    assert len(saved['history']) == 2
    for result in results:
        assert saved['fields'][result['field']] == result['content']


def test_simultaneous_same_field_cannot_silently_overwrite(setup, monkeypatch):
    root, board = setup; barrier = threading.Barrier(2)
    def post(*args, **kwargs):
        barrier.wait(timeout=10)
        return response('A new caption')
    monkeypatch.setattr(copywriter.requests, 'post', post)
    initial = board(root/'a')['publish_package']['revisions']['caption']
    def run(_):
        try:
            return copywriter.regenerate(root/'a', 'caption', 'New hook', initial)
        except copywriter.CopywriterError as error:
            return error.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    assert sum(isinstance(x, dict) for x in results) == 1
    assert 409 in results
