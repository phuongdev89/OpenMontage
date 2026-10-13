"""Real Chromium checks for posting-copy submission and background feedback."""
from pathlib import Path

import pytest

pytest.importorskip('playwright.sync_api')
from playwright.sync_api import sync_playwright, expect


def test_project_archive_link_after_publish():
    ui = Path(__file__).resolve().parents[2] / 'backlot/ui'
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        def serve(route):
            path = route.request.url.split('example.test')[-1]
            if path.startswith('/ui/'):
                route.fulfill(body=(ui / path.split('/')[-1]).read_text(encoding='utf-8'), content_type='text/javascript')
            else:
                route.fulfill(body='<html><body></body></html>', content_type='text/html')
        page.route('http://example.test/**', serve)
        page.goto('http://example.test/')
        page.evaluate('''async () => {
            const {renderPublishPackage} = await import('/ui/publish.js');
            const s = {stages:[{name:'publish',status:'pending'}], publish_package:{videos:{},thumbnails:[],revisions:{}}};
            if (renderPublishPackage(s, 'film') !== null) throw new Error('Shown before publish');
            s.stages[0].status = 'completed';
            document.body.append(renderPublishPackage(s, 'film'));
        }''')
        link = page.get_by_role('link', name='Tải project (.zip)')
        expect(link).to_be_visible()
        expect(link).to_have_attribute('href', '/api/project/film/download')
        expect(link).to_have_attribute('download', '')
        browser.close()


@pytest.mark.parametrize('field', ['caption', 'description'])
def test_background_copy_regeneration(field):
    ui = Path(__file__).resolve().parents[2] / 'backlot/ui'
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        def serve(route):
            path = route.request.url.split('example.test')[-1]
            if path.startswith('/ui/'):
                route.fulfill(body=(ui / path.split('/')[-1]).read_text(encoding='utf-8'), content_type='text/javascript')
            else:
                route.fulfill(body='<html><body></body></html>', content_type='text/html')
        page.route('**/*', serve)
        page.goto('http://example.test/')
        page.evaluate("""async () => {
          const {renderPublishPackage} = await import('/ui/publish.js');
          window.pending = [];
          window.fetch = (url, options) => new Promise(resolve => pending.push({url, options, resolve}));
          window.packageData = {description:'Old description', caption:'Old caption', title:'Puzzle', revisions:{caption:'a'.repeat(64),description:'b'.repeat(64)}};
          window.redraw = () => document.body.replaceChildren(renderPublishPackage({publish_package:packageData, stages:[{name:'publish',status:'completed'}]}, 'project-a'));
          redraw();
        }""")
        button = page.get_by_role('button', name='Tạo lại '+field, exact=True)
        button.click()
        page.locator('#copy-instruction').fill('Viết ngắn hơn')
        page.get_by_role('button', name='Tạo lại', exact=True).click()
        expect(page.locator('dialog')).to_have_count(0)
        expect(button).to_be_disabled()
        expect(button).to_have_attribute('aria-busy', 'true')
        page.evaluate('redraw()')  # SSE refresh must not lose the pending spinner.
        expect(button).to_be_disabled()
        page.evaluate("pending[0].resolve({ok:true,json:async()=>({content:'New copy',revision:'c'.repeat(64)})})")
        textarea = page.get_by_role('textbox', name='Description · YouTube' if field == 'description' else 'Caption · Facebook / TikTok', exact=True)
        expect(textarea).to_have_value('New copy')
        expect(button).to_be_enabled()
        button.click()
        page.locator('#copy-instruction').fill('Lại nữa')
        page.get_by_role('button', name='Tạo lại', exact=True).click()
        page.evaluate("pending[1].resolve({ok:false,json:async()=>({detail:'Provider failed'})})")
        expect(page.get_by_role('alert')).to_have_text('Provider failed')
        expect(textarea).to_have_value('New copy')
        expect(button).to_be_enabled()
        browser.close()


def test_title_editor_and_editable_thumbnail_prompt():
    ui = Path(__file__).resolve().parents[2] / 'backlot/ui'
    with sync_playwright() as pw:
        browser=pw.chromium.launch();page=browser.new_page()
        def serve(route):
            path=route.request.url.split('example.test')[-1]
            route.fulfill(body=(ui/path.split('/')[-1]).read_text(encoding='utf-8') if path.startswith('/ui/') else '<html><body></body></html>',content_type='text/javascript' if path.startswith('/ui/') else 'text/html')
        page.route('**/*',serve);page.goto('http://example.test/')
        page.evaluate("""async () => {
          const {renderTitleEditor,renderPublishPackage}=await import('/ui/publish.js');
          window.saved=null;window.updated=false;
          window.fetch=async (url,options)=>{saved={url,body:JSON.parse(options.body)};return {ok:true,json:async()=>({title:'New title'})};};
          const s={title:'Old title',stages:[{name:'compose',status:'completed'},{name:'publish',status:'completed'}],publish_package:{title:'Old title',description:'Desc',caption:'Cap',revisions:{},thumbnails:[{path:'thumb.png',absolute_path:'thumb.png',prompt:'Actual prompt',generated:true}],videos:{}}};
          document.body.append(renderTitleEditor(s,'project-a',async()=>{updated=true}),renderPublishPackage(s,'project-a'));
        }""")
        page.get_by_role('tab',name='Thumbnail',exact=True).click()
        prompt=page.get_by_role('textbox',name='Prompt tạo thumbnail · có thể sửa để gen thủ công')
        expect(prompt).to_have_value('Actual prompt');prompt.fill('Manual variation')
        expect(prompt).to_have_value('Manual variation')
        page.get_by_role('heading',name='Old title',exact=True).dblclick()
        page.get_by_role('textbox',name='Tên project trên Backlot').fill('New title')
        page.get_by_role('button',name='Lưu tiêu đề',exact=True).click()
        expect(page.locator('dialog')).to_have_count(0)
        assert page.evaluate('saved.body')=={'title':'New title','expected_title':'Old title'}
        assert page.evaluate('updated') is True
        expect(page.get_by_role('heading',name='New title',exact=True)).to_be_visible()
        browser.close()
