import base64
import json
from pathlib import Path
import pytest
import requests
from fastapi.testclient import TestClient
from backlot import server, state, posting_support
from backlot.publish_package import build_publish_package
from backlot.file_manager import write_file, read_file, delete_file, restore_file, file_revision
from backlot.copywriter import CopywriterError


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / 'projects'
    project = root / 'Film'
    (project / 'artifacts').mkdir(parents=True)
    monkeypatch.setattr(server, 'PROJECTS_DIR', root)
    monkeypatch.setattr(server, '_summary_cache', {})
    async def no_watch(): pass
    monkeypatch.setattr(server, '_watch_projects', no_watch)
    return project


def test_files_crud_revision_and_undo(workspace):
    first = write_file(workspace, 'notes/test.md', 'Tiếng Việt'.encode(), None)
    assert read_file(workspace, 'notes/test.md')['content'] == 'Tiếng Việt'
    with pytest.raises(CopywriterError, match='đã tồn tại'):
        write_file(workspace, 'notes/test.md', b'overwrite', None)
    write_file(workspace, 'notes/test.md', b'new', first['revision'])
    with pytest.raises(CopywriterError, match='đã tồn tại'):
        write_file(workspace, 'notes/test.md', b'stale', first['revision'])
    deletion = delete_file(workspace, 'notes/test.md', file_revision(workspace, 'notes/test.md')['revision'])
    assert not (workspace/'notes/test.md').exists()
    restore_file(workspace, deletion['undo_token'])
    assert (workspace/'notes/test.md').read_bytes() == b'new'


@pytest.mark.parametrize('path', ['../foreign.txt', 'C:/foreign.txt', '/foreign.txt', '.env', '.backlot-trash/x', 'project.json', 'checkpoint_publish.json', 'history/checkpoint_script.json'])
def test_file_writes_reject_escape_and_pipeline_state(workspace, path):
    with pytest.raises(CopywriterError):
        write_file(workspace, path, b'data', None)


@pytest.mark.parametrize('method,endpoint', [
    ('get', '/files'), ('get', '/files/read'),
    ('post', '/files/write'), ('post', '/files/restore'),
])
def test_file_manager_api_removed(workspace, method, endpoint):
    with TestClient(server.create_app()) as client:
        response = getattr(client, method)('/api/project/Film' + endpoint)
        assert response.status_code == 404


def test_all_thumbnails_and_selection_are_project_scoped(workspace):
    folder = workspace/'exports/thumbnails'; folder.mkdir(parents=True)
    (folder/'a.png').write_bytes(b'a'); (folder/'b.png').write_bytes(b'b')
    log = {'metadata':{'posting_package':{'thumbnails':[{'path':'exports/thumbnails/a.png','prompt':'Actual generation prompt','method':'image-generate'}]}}}
    package = build_publish_package(workspace, log, True)
    assert len(package['thumbnails']) == 2
    assert package['thumbnail_prompt'] == 'Actual generation prompt'
    posting_support.select_thumbnail(workspace, 'exports/thumbnails/b.png')
    package = build_publish_package(workspace, log, True)
    assert package['selected_thumbnail'] == 'exports/thumbnails/b.png'
    assert sum(t['selected'] for t in package['thumbnails']) == 1
    assert state._find_poster(workspace, {}) == 'exports/thumbnails/b.png'
    with pytest.raises(CopywriterError):
        posting_support.select_thumbnail(workspace, '../other/a.png')


def test_cannot_delete_last_thumbnail_via_api(workspace):
    folder = workspace / 'exports/thumbnails'
    folder.mkdir(parents=True)
    (folder / 'a.png').write_bytes(b'a')
    with TestClient(server.create_app()) as client:
        base = '/api/project/Film/files/delete'
        def remove(name):
            raw = 'exports/thumbnails/' + name
            return client.post(base, json={'path': raw, 'expected_revision': file_revision(workspace, raw)['revision']})
        assert remove('a.png').status_code == 409
        assert (folder / 'a.png').exists()
        (folder / 'b.png').write_bytes(b'b')
        assert remove('a.png').status_code == 200
        assert remove('b.png').status_code == 409


def test_prompt_exists_without_image_or_posting_metadata(workspace):
    package = build_publish_package(workspace, {}, True)
    assert not package['thumbnails']
    assert package['thumbnail_prompt'] and '{{HOOK_SCENE}}' not in package['thumbnail_prompt']
    assert package['thumbnail_prompt_source'] == 'draft'


def test_create_support_fills_missing_without_overwriting(workspace, monkeypatch):
    log = {'metadata':{'posting_package':{'title':'Keep original title'}}}
    def board(project):
        return {'title':'Source problem', 'project_id':project.name,
                'artifacts':{'script':{'text':'Verified project-only source'}},
                'publish_package':build_publish_package(project, log, True)}
    monkeypatch.setattr(state, 'load_board_state', board)
    monkeypatch.setattr(posting_support, 'load_env', lambda: None)
    for key, value in {'AI_CHAT_URL':'https://provider.invalid/v1', 'AI_CHAT_KEY':'test-key', 'AI_CHAT_MODEL':'configured'}.items(): monkeypatch.setenv(key,value)
    def post(url, **kwargs):
        assert 'Verified project-only source' in kwargs['json']['messages'][1]['content']
        assert 'Nguồn đề:' in kwargs['json']['messages'][0]['content']
        response=requests.Response(); response.status_code=200
        response._content=json.dumps({'choices':[{'message':{'content':json.dumps({'title':'Ignore replacement', 'description':'YouTube details', 'caption':'Social hook', 'hook_scene':'A child compares the actual source clues without showing the answer.'})}}]}).encode()
        return response
    monkeypatch.setattr(posting_support.requests,'post',post)
    before = board(workspace)['publish_package']
    posting_support.create_support(workspace, before['support_revision'])
    after = board(workspace)['publish_package']
    assert after['title'] == 'Keep original title'
    assert after['caption'] == 'Social hook' and after['description'] == 'YouTube details'
    assert after['thumbnail_prompt_source'] == 'prepared'
    assert 'A child compares' in after['thumbnail_prompt']
    assert not list(workspace.glob('checkpoint*'))
    with pytest.raises(CopywriterError, match='đã đổi'):
        posting_support.create_support(workspace, before['support_revision'])


@pytest.mark.parametrize('reply,status', [('',429), ('not-json',200), ('{"title":"Only a title"}',200)])
def test_support_provider_failure_writes_nothing(workspace, monkeypatch, reply, status):
    def board(project):
        return {'title':'Source', 'artifacts':{'script':{'text':'Verified source'}},
                'publish_package':build_publish_package(project,{},True)}
    monkeypatch.setattr(state,'load_board_state',board)
    monkeypatch.setattr(posting_support,'load_env',lambda:None)
    for key,value in {'AI_CHAT_URL':'https://provider.invalid/v1','AI_CHAT_KEY':'test-key','AI_CHAT_MODEL':'configured'}.items(): monkeypatch.setenv(key,value)
    response=requests.Response();response.status_code=status
    response._content=json.dumps({'choices':[{'message':{'content':reply}}]}).encode()
    monkeypatch.setattr(posting_support.requests,'post',lambda *a,**k:response)
    with pytest.raises(CopywriterError):
        posting_support.create_support(workspace,board(workspace)['publish_package']['support_revision'])
    assert not (workspace/'artifacts/posting_support.json').exists()
