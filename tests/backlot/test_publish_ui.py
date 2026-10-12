"""Real Chromium checks for posting-copy submission and background feedback."""
from pathlib import Path

import pytest

pytest.importorskip('playwright.sync_api')
from playwright.sync_api import sync_playwright, expect


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
