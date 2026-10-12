import json
import pytest
from backlot.project_title import save_title, read_title
from backlot.copywriter import CopywriterError
from backlot.state import _last_activity


def test_title_save_preserves_production_timestamp(tmp_path, monkeypatch):
    p=tmp_path/'project';p.mkdir();(p/'artifacts').mkdir()
    (p/'project.json').write_text('{"title":"Old","created_at":"original"}')
    (p/'checkpoint_compose.json').write_text('{}')
    before={f:(f.read_bytes(),f.stat().st_mtime_ns) for f in p.glob('*.json')}
    activity=_last_activity(p)
    monkeypatch.setattr('backlot.state.load_board_state',lambda _: {'title':read_title(p) or 'Old','stages':[{'name':'compose','status':'completed'}]})
    assert save_title(p,'New','Old')['title']=='New'
    assert read_title(p)=='New'
    assert _last_activity(p)==activity
    assert all(f.read_bytes()==b and f.stat().st_mtime_ns==t for f,(b,t) in before.items())
    with pytest.raises(CopywriterError,match='đã thay đổi'):save_title(p,'Other','Old')


def test_title_requires_completed_delivery(tmp_path,monkeypatch):
    monkeypatch.setattr('backlot.state.load_board_state',lambda _: {'title':'Old','stages':[{'name':'compose','status':'in_progress'}]})
    with pytest.raises(CopywriterError,match='sau compose'):save_title(tmp_path,'New','Old')


def test_backlot_title_does_not_override_video_title(tmp_path):
    from backlot.state import load_board_state
    p=tmp_path/'separate-titles';p.mkdir();(p/'artifacts').mkdir()
    (p/'project.json').write_text(json.dumps({'project_id':'separate-titles','title':'Original project'}))
    (p/'display_title.json').write_text(json.dumps({'project_id':p.name,'title':'Organizational name'}))
    (p/'checkpoint_publish.json').write_text(json.dumps({'stage':'publish','status':'completed','artifacts':{'publish_log':{'metadata':{'posting_package':{'title':'Video title'}}}}}))
    (p/'artifacts/publish_log.json').write_text(json.dumps({'metadata':{'posting_package':{'title':'Video title'}}}))
    state=load_board_state(p)
    assert state['title']=='Organizational name'
    assert state['publish_package']['title']=='Video title'
