"""Real Chromium checks for posting-copy submission and background feedback."""
from pathlib import Path

import pytest

pytest.importorskip('playwright.sync_api')
from playwright.sync_api import sync_playwright, expect


@pytest.mark.parametrize('count', [1, 2])
def test_thumbnail_delete_confirmation_and_visible_path(count):
    ui = Path(__file__).resolve().parents[2] / 'backlot/ui'
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        def serve(route):
            path = route.request.url.split('example.test')[-1]
            route.fulfill(body=(ui / path.split('/')[-1]).read_text(encoding='utf-8') if path.startswith('/ui/') else '<html><body></body></html>', content_type='text/javascript' if path.startswith('/ui/') else 'text/html')
        page.route('**/*', serve)
        page.goto('http://example.test/')
        page.evaluate('(count) => window.thumbCount = count', count)
        page.evaluate('''async () => {
            const {renderPublishPackage} = await import('/ui/publish.js');
            window.calls = []; window.updated = false;
            window.fetch = async (url, options) => {
                calls.push({url, body: options?.body ? JSON.parse(options.body) : null});
                return {ok:true, json:async()=>({revision:'revision-a'})};
            };
            const s = {stages:[{name:'publish',status:'completed'}], publish_package:{
                revisions:{}, thumbnails:[{path:'exports/thumbnails/a.png',absolute_path:'D:/film/exports/thumbnails/a.png',generated:true}], videos:{}}};
            if (thumbCount > 1) s.publish_package.thumbnails.push({path:'exports/thumbnails/b.png',absolute_path:'D:/film/exports/thumbnails/b.png',generated:true});
            document.body.append(renderPublishPackage(s, 'film', async()=>{updated=true}));
        }''')
        page.add_style_tag(content=(ui / 'studio.css').read_text(encoding='utf-8').replace("@import url('/ui/tokens.css');", ''))
        page.get_by_role('tab', name='Thumbnail', exact=True).click()
        expect(page.get_by_role('textbox', name='Thumbnail path', exact=True).first).to_be_visible()
        expect(page.locator('.thumbnail-dots button')).to_have_count(count)
        if count > 1:
            page.get_by_role('button', name='Thumbnail 2', exact=True).click()
            expect(page.get_by_role('button', name='Thumbnail 2', exact=True)).to_have_attribute('aria-pressed', 'true')
            page.get_by_role('button', name='Thumbnail 1', exact=True).click()
            expect(page.get_by_role('button', name='Thumbnail 1', exact=True)).to_have_attribute('aria-pressed', 'true')
        else:
            expect(page.locator('.thumbnail-dots')).to_be_hidden()
            expect(page.get_by_role('button', name='Xóa', exact=True)).to_be_disabled()
            assert page.evaluate('calls.length') == 0
            browser.close()
            return
        page.once('dialog', lambda dialog: dialog.dismiss())
        page.get_by_role('button', name='Xóa', exact=True).first.click()
        assert page.evaluate('calls.length') == 0
        expect(page.locator('.thumbnail-candidate')).to_have_count(count)
        page.once('dialog', lambda dialog: dialog.accept())
        page.get_by_role('button', name='Xóa', exact=True).first.click()
        expect(page.locator('.thumbnail-candidate')).to_have_count(count - 1)
        expect(page.locator('.thumbnail-dots')).to_be_hidden()
        expect(page.get_by_role('button', name='Xóa', exact=True)).to_be_disabled()
        assert page.evaluate('calls[1].body') == {'path':'exports/thumbnails/a.png', 'expected_revision':'revision-a'}
        assert page.evaluate('updated') is True
        browser.close()


def test_no_project_zip_download_after_publish():
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
        expect(link).to_have_count(0)
        expect(page.locator('a[href$="/download"]')).to_have_count(0)
        browser.close()


def test_video_title_saves_only_on_blur_and_keeps_failed_draft():
    ui = Path(__file__).resolve().parents[2] / 'backlot/ui'
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        def serve(route):
            path = route.request.url.split('example.test')[-1]
            route.fulfill(body=(ui / path.split('/')[-1]).read_text(encoding='utf-8') if path.startswith('/ui/') else '<html><body></body></html>', content_type='text/javascript' if path.startswith('/ui/') else 'text/html')
        page.route('http://example.test/**', serve)
        page.goto('http://example.test/')
        page.evaluate('''async () => {
            const {renderPublishPackage} = await import('/ui/publish.js');
            window.calls = []; window.fail = false;
            window.fetch = async (url, options) => {
                const body = JSON.parse(options.body); calls.push({url, body});
                return {ok: !fail, json: async()=> fail ? {detail:'Save failed'} : {content:body.title,revision:'new-revision'}};
            };
            window.s = {stages:[{name:'publish',status:'completed'}], publish_package:{title:'Old title',revisions:{title:'old-revision'},thumbnails:[],videos:{}}};
            window.draw = () => document.body.replaceChildren(renderPublishPackage(s, 'film'));
            draw();
        }''')
        title = page.get_by_role('textbox', name='Tiêu đề video', exact=True)
        expect(title).to_be_editable()
        title.fill('Edited title')
        assert page.evaluate('calls.length') == 0
        page.get_by_role('heading', name='Hỗ trợ đăng video', exact=True).click()
        expect(page.locator('.posting-field').first.get_by_role('status')).to_have_text('Đã lưu')
        assert page.evaluate('calls[0].body') == {'title': 'Edited title', 'expected_revision': 'old-revision'}
        page.evaluate('fail = true')
        title.fill('Keep this draft')
        page.get_by_role('heading', name='Hỗ trợ đăng video', exact=True).click()
        expect(page.locator('.posting-field').first.get_by_role('status')).to_have_text('Save failed')
        page.evaluate('draw()')
        expect(page.get_by_role('textbox', name='Tiêu đề video', exact=True)).to_have_value('Keep this draft')
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
        if field == 'caption':
            page.get_by_role('tab', name='Facebook', exact=True).click()
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


@pytest.mark.parametrize('field,label', [('description','Description · YouTube'), ('caption','Caption · Facebook / TikTok')])
def test_manual_copy_saves_on_blur_and_preserves_draft(field, label):
    ui = Path(__file__).resolve().parents[2] / 'backlot/ui'
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        def serve(route):
            path = route.request.url.split('example.test')[-1]
            route.fulfill(body=(ui / path.split('/')[-1]).read_text(encoding='utf-8') if path.startswith('/ui/') else '<html><body></body></html>', content_type='text/javascript' if path.startswith('/ui/') else 'text/html')
        page.route('http://example.test/**', serve)
        page.goto('http://example.test/')
        page.evaluate('''async (field) => {
            const {renderPublishPackage} = await import('/ui/publish.js');
            window.calls = []; window.fail = false;
            window.fetch = async (url, options) => {
                const body = JSON.parse(options.body); calls.push({url, body});
                return {ok: !fail, json: async()=> fail ? {detail:'Save failed'} : {content:body.content,revision:'new-revision'}};
            };
            window.s = {stages:[{name:'publish',status:'completed'}], publish_package:{title:'Old title',revisions:{title:'old-revision', description:'desc-rev', caption:'caption-rev'},thumbnails:[],videos:{}}};
            window.draw = () => document.body.replaceChildren(renderPublishPackage(s, 'film'));
            draw();
        }''', field)
        if field == 'caption':
            page.get_by_role('tab', name='Facebook', exact=True).click()
        title = page.get_by_role('textbox', name=label, exact=True)
        expect(title).to_be_editable()
        title.fill('Edited title')
        assert page.evaluate('calls.length') == 0
        page.get_by_role('heading', name='Hỗ trợ đăng video', exact=True).click()
        expect(page.get_by_role('textbox', name=label, exact=True).locator('..').get_by_role('status')).to_have_text('Đã lưu')
        assert page.evaluate('calls[0].body') == {'field': field, 'content': 'Edited title', 'expected_revision': 'desc-rev' if field == 'description' else 'caption-rev'}
        page.evaluate('fail = true')
        title.fill('Keep this draft')
        page.get_by_role('heading', name='Hỗ trợ đăng video', exact=True).click()
        expect(page.get_by_role('textbox', name=label, exact=True).locator('..').get_by_role('status')).to_have_text('Save failed')
        page.evaluate('draw()')
        expect(page.get_by_role('textbox', name=label, exact=True)).to_have_value('Keep this draft')
        browser.close()


@pytest.mark.parametrize('platform,label,link', [
    ('youtube','YouTube','https://www.youtube.com/watch?v=abc123'),
    ('facebook','Facebook','https://www.facebook.com/example/posts/123'),
])
def test_posted_link_blur_saves_and_preserves_failed_draft(platform, label, link):
    ui = Path(__file__).resolve().parents[2] / 'backlot/ui'
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        def serve(route):
            path = route.request.url.split('example.test')[-1]
            route.fulfill(body=(ui / path.split('/')[-1]).read_text(encoding='utf-8') if path.startswith('/ui/') else '<html><body></body></html>', content_type='text/javascript' if path.startswith('/ui/') else 'text/html')
        page.route('http://example.test/**', serve)
        page.goto('http://example.test/')
        page.evaluate("""async ({platform}) => {
            const {renderPublishPackage}=await import('/ui/publish.js');
            window.calls=[];window.fail=false;
            window.s={stages:[{name:'publish',status:'completed'}],posting_status:{platforms:{youtube:{revision:'old',confirmed:false,url:''},facebook:{revision:'old',confirmed:false,url:''}}},publish_package:{title:'Title',description:'Description',caption:'Caption',revisions:{},thumbnails:[],videos:{}}};
            window.fetch=async(url,options)=>{const body=JSON.parse(options.body);calls.push(body);if(fail)return {ok:false,json:async()=>({detail:'Save failed'})};const record={url:body.url,confirmed:body.confirmed,revision:'new'};s.posting_status.platforms[platform]=record;return {ok:true,json:async()=>({platforms:{[platform]:record}})};};
            window.draw=()=>document.body.replaceChildren(renderPublishPackage(s,'link-test'));
            draw();
        }""", {'platform':platform})
        page.get_by_role('tab',name=label,exact=True).click()
        page.locator('.posting-subpanel:not([hidden]) input[role=switch]').check()
        field=page.get_by_role('textbox',name='Link '+label+' đã đăng',exact=True)
        field.fill(link)
        assert page.evaluate('calls.length')==0
        page.get_by_role('heading',name='Hỗ trợ đăng video',exact=True).click()
        expect(page.locator('.posting-subpanel:not([hidden]) .posting-status-msg')).to_have_text('Đã lưu')
        assert page.evaluate('calls[0]')=={'platform':platform,'confirmed':True,'url':link,'expected_revision':'old'}
        field.focus();page.get_by_role('heading',name='Hỗ trợ đăng video',exact=True).click()
        assert page.evaluate('calls.length')==1
        page.evaluate('fail=true')
        field.fill(link+'4')
        page.get_by_role('heading',name='Hỗ trợ đăng video',exact=True).click()
        expect(page.locator('.posting-subpanel:not([hidden]) .posting-status-msg')).to_have_text('Save failed')
        page.evaluate('draw()')
        expect(page.get_by_role('textbox',name='Link '+label+' đã đăng',exact=True)).to_have_value(link+'4')
        browser.close()


def test_backlot_title_blur_saves():
    ui = Path(__file__).resolve().parents[2] / 'backlot/ui'
    with sync_playwright() as pw:
        browser=pw.chromium.launch();page=browser.new_page()
        def serve(route):
            path=route.request.url.split('example.test')[-1]
            route.fulfill(body=(ui/path.split('/')[-1]).read_text(encoding='utf-8') if path.startswith('/ui/') else '<html><body><button id="outside">Outside</button><main></main></body></html>',content_type='text/javascript' if path.startswith('/ui/') else 'text/html')
        page.route('http://example.test/**',serve);page.goto('http://example.test/')
        page.evaluate("""async()=>{
            const {renderTitleEditor}=await import('/ui/publish.js');window.calls=[];
            window.fetch=async(url,options)=>{const body=JSON.parse(options.body);calls.push(body);return {ok:true,json:async()=>({title:body.title})};};
            document.querySelector('main').append(renderTitleEditor({title:'Original',stages:[{name:'publish',status:'completed'}]},'title-blur'));
        }""")
        page.get_by_role('heading',name='Original',exact=True).dblclick()
        page.get_by_role('textbox',name='Tên project trên Backlot').fill('Changed on blur')
        assert page.evaluate('calls.length')==0
        page.locator('#outside').click()
        expect(page.get_by_role('heading',name='Changed on blur',exact=True)).to_be_visible()
        assert page.evaluate('calls')==[{'title':'Changed on blur','expected_title':'Original'}]
        browser.close()
