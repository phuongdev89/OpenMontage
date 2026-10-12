import pytest
from lib.channel_watermark import plan_corner_watermark


@pytest.mark.parametrize('width,height', [(1920,1080),(1080,1920),(1280,720)])
@pytest.mark.parametrize('inset', [0,.02,.05])
def test_schedule_only_anchors_corners_within_five_percent(width,height,inset):
    args = dict(width=width,height=height,duration=33,asset_path='logo.png',seed='project-a',inset=inset)
    plan = plan_corner_watermark(**args)
    assert plan == plan_corner_watermark(**args)
    assert plan != plan_corner_watermark(**{**args, 'seed':'project-b'})
    assert plan['segments'][0]['start_seconds'] == 0
    assert plan['segments'][-1]['end_seconds'] == 33
    assert len(plan['segments']) == 1
    for s in plan['segments']:
        assert s['corner'] == 'top-left'
        assert 0 <= min(s['x'],width-s['x']-s['width']) <= width*.05
        assert 0 <= min(s['y'],height-s['y']-s['height']) <= height*.05
        assert s['x']+s['width']<=width and s['y']+s['height']<=height
    for a,b in zip(plan['segments'],plan['segments'][1:]):
        assert a['end_seconds'] == b['start_seconds']


def test_refuses_margin_outside_requirement():
    with pytest.raises(ValueError):
        plan_corner_watermark(width=1920,height=1080,duration=30,asset_path='logo.png',seed='a',inset=.051)


def test_overlay_consumes_plan_and_applies_real_alpha_filter(tmp_path, monkeypatch):
    import json
    from tools.video.video_compose import VideoCompose
    source, logo, output = [tmp_path/name for name in ('source.mp4','logo.png','final.mp4')]
    source.write_bytes(b'fixture'); logo.write_bytes(b'fixture')
    commands = []
    monkeypatch.setattr(VideoCompose, 'run_command', lambda self,cmd: commands.append(cmd))
    result = VideoCompose().execute({'operation':'overlay','input_path':str(source),
        'output_path':str(output), 'corner_watermark':{
            'width':1920,'height':1080,'duration':17,'asset_path':str(logo),'seed':'project-a'}})
    assert result.success, result.error
    command = commands[0]
    filters = command[command.index('-filter_complex')+1]
    assert 'format=rgba,colorchannelmixer=aa=0.55' in filters
    assert "gte(t,0)*lt(t,17)" in filters
    assert command[command.index('-c:a')+1] == 'copy'
    assert json.loads(output.with_suffix('.watermark.json').read_text())['seed'] == 'project-a'
