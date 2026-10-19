import json

import pytest
from fastapi.testclient import TestClient

from backlot import server
from backlot.state import load_board_state, summarize_project
from backlot.posted import posting_state
from lib.checkpoint import write_checkpoint, read_checkpoint, CheckpointValidationError


@pytest.fixture
def posted_client(tmp_path, monkeypatch):
    root = tmp_path / 'projects'
    project = root / 'film'
    project.mkdir(parents=True)
    write_checkpoint(root, 'film', 'publish', 'completed', {'publish_log': {'version': '1.0', 'entries': []}})
    monkeypatch.setattr(server, 'PROJECTS_DIR', root)
    monkeypatch.setattr(server, '_summary_cache', {})
    async def no_watch():
        pass
    monkeypatch.setattr(server, '_watch_projects', no_watch)
    with TestClient(server.create_app()) as client:
        yield client, project


def save(client, project, platform, confirmed, url, **kwargs):
    revision = posting_state(project)['platforms'][platform]['revision']
    return client.post('/api/project/film/posted', json={
        'platform': platform, 'confirmed': confirmed, 'url': url,
        'expected_revision': revision, **kwargs})


def test_manual_posted_roundtrip_and_revoke(posted_client):
    client, project = posted_client
    publish_bytes = (project / 'checkpoint_publish.json').read_bytes()
    assert posting_state(project)['status'] == 'pending'
    first = save(client, project, 'youtube', True, 'https://youtu.be/video-id')
    assert first.status_code == 200, first.text
    assert first.json()['status'] == 'awaiting_human'
    timestamp = first.json()['platforms']['youtube']['confirmed_at']
    second = save(client, project, 'facebook', True, 'https://www.facebook.com/reel/123')
    assert second.status_code == 200, second.text
    assert second.json()['status'] == 'completed'
    cp = read_checkpoint(project.parent, project.name, 'posted')
    assert cp['human_approved'] is False
    assert 'approval_resolution' not in cp
    assert cp['artifacts']['posted_log']['youtube']['confirmed_at'] == timestamp
    assert load_board_state(project)['posting_status']['status'] == 'completed'
    assert summarize_project(project)['stage_states'][-1] == {'name': 'posted', 'status': 'completed'}
    assert (project / 'checkpoint_publish.json').read_bytes() == publish_bytes
    revoked = save(client, project, 'facebook', False, 'https://www.facebook.com/reel/123')
    assert revoked.json()['status'] == 'awaiting_human'
    assert revoked.json()['platforms']['facebook']['confirmed_at'] is None


@pytest.mark.parametrize('url', ['', 'javascript:alert(1)', 'https://facebook.com/reel/1',
    'https://youtube.com.evil.test/watch?v=1', 'https://youtube.com/', 'https://user@youtube.com/watch?v=1'])
def test_checked_requires_correct_platform_link(posted_client, url):
    client, project = posted_client
    assert save(client, project, 'youtube', True, url).status_code == 422
    assert not (project / 'checkpoint_posted.json').exists()


def test_youtube_link_persists_for_math_news_project(posted_client):
    client, project = posted_client
    (project / 'project.json').write_text(json.dumps({
        'pipeline_type': 'animation', 'style_playbook': 'math-news',
    }), encoding='utf-8')
    response = save(client, project, 'youtube', True, 'https://youtu.be/video-id')
    assert response.status_code == 200, response.text
    state = posting_state(project)
    assert state['platforms']['youtube']['url'] == 'https://youtu.be/video-id'
    assert state['platforms']['youtube']['confirmed'] is True
    assert state['platforms']['facebook']['confirmed'] is False


def test_requires_publish_and_rejects_stale_and_cross_origin(posted_client):
    client, project = posted_client
    old_revision = posting_state(project)['platforms']['youtube']['revision']
    assert save(client, project, 'youtube', True, 'https://youtube.com/watch?v=abc').status_code == 200
    assert save(client, project, 'youtube', False, '', expected_revision=old_revision).status_code == 409
    body = {'platform': 'facebook', 'confirmed': True, 'url': 'https://facebook.com/reel/1',
            'expected_revision': posting_state(project)['platforms']['facebook']['revision']}
    assert client.post('/api/project/film/posted', json=body, headers={'Origin': 'https://evil.test'}).status_code == 403
    (project / 'checkpoint_publish.json').unlink()
    assert save(client, project, 'facebook', True, 'https://facebook.com/reel/1').status_code == 409


def test_auto_policy_does_not_complete_posted_and_production_order_unchanged(posted_client):
    client, project = posted_client
    marker = {'approval_policy': {'execution_mode': 'stage_config', 'stage_approvals': {}}}
    (project / 'project.json').write_text(json.dumps(marker), encoding='utf-8')
    assert save(client, project, 'youtube', True, 'https://youtu.be/abc').status_code == 200
    assert posting_state(project)['status'] == 'awaiting_human'
    with pytest.raises(CheckpointValidationError):
        write_checkpoint(project.parent, 'film', 'posted', 'completed', {})
    from lib.checkpoint import get_pipeline_stages
    assert 'posted' not in get_pipeline_stages('animation')


def test_browser_manual_confirmation_required_links_and_reload(posted_client):
    from pathlib import Path
    pw_api = pytest.importorskip('playwright.sync_api')
    client, project = posted_client
    ui = Path(__file__).resolve().parents[2] / 'backlot/ui'
    with pw_api.sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        def serve(route):
            path = route.request.url.split('example.test')[-1]
            if path.startswith('/ui/'):
                route.fulfill(body=(ui / path.split('/')[-1]).read_text(encoding='utf-8'), content_type='text/javascript')
            elif path.startswith('/api/'):
                response = client.request(route.request.method, path, content=route.request.post_data,
                                          headers={'Content-Type': 'application/json'})
                route.fulfill(status=response.status_code, body=response.text, content_type='application/json')
            else:
                route.fulfill(body='<html><body></body></html>', content_type='text/html')
        page.route('http://example.test/**', serve)
        def mount():
            page.goto('http://example.test/')
            page.evaluate('''async () => {
                const {renderPublishPackage} = await import('/ui/publish.js');
                window.refresh = async () => {
                    const s = await (await fetch('/api/project/film/state')).json();
                    document.body.replaceChildren(renderPublishPackage(s, 'film', refresh));
                };
                await refresh();
            }''')
        mount()
        page.get_by_role('checkbox', name='Đã đăng YouTube', exact=True).check()
        youtube = page.locator('form').filter(has=page.get_by_role('checkbox', name='Đã đăng YouTube', exact=True))
        youtube.get_by_role('button', name='Lưu', exact=True).click()
        assert not (project / 'checkpoint_posted.json').exists()
        page.get_by_role('textbox', name='Link YouTube', exact=True).fill('https://youtu.be/abc')
        youtube.get_by_role('button', name='Lưu', exact=True).click()
        pw_api.expect(page.get_by_text('Đã xác nhận:', exact=False)).to_have_count(1)
        assert posting_state(project)['status'] == 'awaiting_human'
        page.get_by_role('textbox', name='Link Facebook', exact=True).fill('https://facebook.com/reel/123')
        page.get_by_role('checkbox', name='Đã đăng Facebook', exact=True).check()
        facebook = page.locator('form').filter(has=page.get_by_role('checkbox', name='Đã đăng Facebook', exact=True))
        facebook.get_by_role('button', name='Lưu', exact=True).click()
        pw_api.expect(page.locator('.posting-cleanup-hint')).to_be_visible()
        mount()
        pw_api.expect(page.get_by_role('checkbox', name='Đã đăng YouTube', exact=True)).to_be_checked()
        pw_api.expect(page.get_by_role('textbox', name='Link Facebook', exact=True)).to_have_value('https://facebook.com/reel/123')
        page.get_by_role('checkbox', name='Đã đăng Facebook', exact=True).uncheck()
        page.locator('form').filter(has=page.get_by_role('checkbox', name='Đã đăng Facebook', exact=True)).get_by_role('button', name='Lưu', exact=True).click()
        pw_api.expect(page.locator('.posting-cleanup-hint')).to_have_count(0)
        assert posting_state(project)['status'] == 'awaiting_human'
        browser.close()


@pytest.mark.parametrize('reference', ['artifacts/publish_log.json', '../outside.json', 'artifacts/missing.json'])
def test_legacy_publish_reference_for_manual_posting(posted_client, reference):
    client, project = posted_client
    (project/'artifacts').mkdir(exist_ok=True)
    (project/'artifacts/publish_log.json').write_text(json.dumps({'version':'1.0','entries':[]}),encoding='utf-8')
    path=project/'checkpoint_publish.json'
    cp=json.loads(path.read_text(encoding='utf-8'))
    cp['artifacts']={'publish_log':{'path':reference}}
    cp['human_approved']=True
    cp['approval_resolution']={'type':'human_approved','at':cp['timestamp']}
    path.write_text(json.dumps(cp),encoding='utf-8')
    original=path.read_bytes()
    response=save(client,project,'facebook',True,'https://facebook.com/reel/123')
    assert response.status_code==(200 if reference=='artifacts/publish_log.json' else 409)
    assert path.read_bytes()==original


def test_legacy_publish_reference_still_validates_payload(posted_client):
    client,project=posted_client
    (project/'artifacts').mkdir(exist_ok=True)
    (project/'artifacts/publish_log.json').write_text(json.dumps({'entries':[]}),encoding='utf-8')
    path=project/'checkpoint_publish.json';cp=json.loads(path.read_text(encoding='utf-8'))
    cp['artifacts']={'publish_log':{'path':'artifacts/publish_log.json'}}
    path.write_text(json.dumps(cp),encoding='utf-8')
    assert save(client,project,'facebook',True,'https://facebook.com/reel/123').status_code==409
    assert not (project/'checkpoint_posted.json').exists()
