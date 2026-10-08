#!/usr/bin/env python3
"""Actual browser/API integration; explicit model/collector doubles, no Meta calls."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server
from tests.test_marketing_workflow import Collector,Model


def main():
    from playwright.sync_api import sync_playwright,expect
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    report={'success':False,'model':'explicit double','collector':'synthetic fixture','flows':[],'errors':[]}
    with tempfile.TemporaryDirectory() as tmp:
        base=Path(tmp);project=base/'project';project.mkdir();other=base/'other';other.mkdir()
        settings=Settings(base/'home',offline=False,allowed_domains=['example.com']);settings.initialize()
        app=Application(settings)
        first=app.store.add_project('Marca sintética',str(project))
        second=app.store.add_project('Outra marca',str(other))
        app.marketing.foundation=Model();app.marketing.research_service=Collector(app.store,settings)
        app.chat.foundation.status=lambda:{'capabilities':{'text':{'registered':True}}}
        app.start();server=create_server(app,ROOT/'ui',port=0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium') or None)
                page=browser.new_page(viewport={'width':1440,'height':1000})
                page.on('pageerror',lambda e:report['errors'].append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}/marketing')
                page.locator('#token').fill(settings.token);page.locator('#login-form button').click()
                expect(page.locator('#workspace')).to_be_visible();page.locator('#project').select_option(first['id'])
                page.locator('#brand').fill('Marca sintética');page.locator('#destination').fill('https://example.com/contact')
                page.locator('#brief button').click();expect(page.locator('#brand-section')).to_be_visible()
                expect(page.locator('#generate')).to_be_disabled()
                report['flows'].append('new campaign asks for brand identity and cannot generate')
                page.locator('#instagram-handle').fill('@marca.exemplo')
                values={'moment':'Lançamento','identity':'Azul e violeta','likes':'Fotos de pessoas',
                        'avoid':'Trocar a logo','history':'Posts curtos; Insights ainda indisponíveis.'}
                for key,value in values.items():page.locator('#brand-'+key).fill(value)
                page.locator('#brand-profile button').click()
                expect(page.locator('#message')).to_contain_text('Preferências salvas')
                expect(page.locator('#instagram-handle')).to_have_value('marca.exemplo')
                report['flows'].append('Instagram normalized, preferences persisted without fake access')
                page.locator('#product-url').fill('https://example.com/product')
                page.locator('#research details summary').click()
                page.locator('#measurement-url').fill('');page.locator('#channel-url').fill('')
                page.locator('#brand-url').fill('https://example.com/history')
                page.get_by_role('button',name='Confirmar e pesquisar fontes',exact=True).click()
                expect(page.locator('#choice-section')).to_be_visible(timeout=15000)
                page.locator('#choice button').click();expect(page.locator('#choice-description')).to_contain_text('proposta original')
                expect(page.locator('#generate')).to_be_disabled()
                page.locator('#analyze-brand').click();expect(page.locator('#brand-style')).to_be_visible(timeout=15000)
                expect(page.locator('#brand-analysis')).to_contain_text('O que preservar')
                expect(page.locator('#generate')).to_be_disabled()
                report['flows'].append('reference choice alone insufficient; local-model analysis shown before style approval')
                page.locator('#style-feedback').fill('Preservar cores e logo, melhorar a clareza.')
                page.locator('#brand-style button').click();expect(page.locator('#generate')).to_be_enabled()
                page.locator('#generate').click();expect(page.locator('#draft-section')).to_be_visible(timeout=20000)
                expect(page.locator('#review')).to_be_visible()
                report['flows'].append('explicit style direction reaches actual generation and brand editorial review')
                page.screenshot(path=str(reports/'marketing-desktop.png'),full_page=True)
                page.locator('#brand-likes').fill('Mais fotos reais, menos texto')
                page.locator('#brand-profile button').click();expect(page.locator('#message')).to_contain_text('Preferências salvas')
                expect(page.locator('#draft-section')).to_be_hidden();expect(page.locator('#brand-style')).to_be_hidden()
                expect(page.locator('#generate')).to_be_disabled()
                report['flows'].append('new preference revokes draft and style approval')
                page.locator('#campaigns').select_option('');expect(page.locator('#brand-section')).to_be_hidden()
                page.locator('#campaigns').select_option(index=1);expect(page.locator('#brand-likes')).to_have_value('Mais fotos reais, menos texto')
                report['flows'].append('campaign reopening restores updated preferences')
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(reports/'marketing-mobile.png'),full_page=True)
                report['flows'].append('mobile view has no horizontal overflow')
                page.locator('#project').select_option(second['id']);expect(page.locator('#brand-section')).to_be_hidden()
                assert page.locator('#instagram-handle').input_value()==''
                report['flows'].append('project change clears identity and investigation selection')
                browser.close();report['success']=not report['errors']
        finally:
            server.shutdown();server.server_close();thread.join();app.close()
    (reports/'marketing-ui-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['success'] else 1


if __name__=='__main__':raise SystemExit(main())
