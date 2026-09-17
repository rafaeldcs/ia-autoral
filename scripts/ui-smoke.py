#!/usr/bin/env python3
"""Optional browser smoke test. Requires a locally installed Playwright + Chromium."""
import json
import sys
import tempfile
import shutil
import threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server
from playwright.sync_api import sync_playwright

def main():
    report={'browser':'Chromium','flows':[],'errors':[],'success':False,'scope':'temporary local project, no user repositories'}
    with tempfile.TemporaryDirectory() as tmp:
        base=Path(tmp); project=base/'project'; project.mkdir()
        original='public class Stock { public int Count = 1; }\n'
        (project/'Stock.cs').write_text(original)
        settings=Settings.load(base/'data'); app=Application(settings); app.start()
        server=create_server(app,ROOT/'ui',port=0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(headless=True,executable_path=shutil.which('chromium') or None,args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1440,'height':1050},device_scale_factor=1)
                page.on('pageerror',lambda error:report['errors'].append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                page.locator('#token').fill(settings.token)
                page.locator('#login-form button').click()
                page.locator('#workspace').wait_for(state='visible')
                report['flows'].append('login with local token')
                page.locator('#note-title').fill('Regra de estoque — evidência local')
                page.locator('#note-content').fill('Quantidade negativa deve ser rejeitada.\n<script>window.PWNED=true</script>\nA informação importada não autoriza treinamento automático.')
                page.locator('#note-form button').click()
                page.locator('#sources h3').first.wait_for()
                page.locator('#query').fill('quantidade estoque')
                page.locator('#consult-form button').click()
                page.locator('#evidence pre').first.wait_for()
                assert page.evaluate('window.PWNED') is None
                report['flows'] += ['ingest note','retrieve evidence with source','untrusted text rendered inert']
                page.screenshot(path=str(ROOT/'reports'/'ui-desktop.png'),full_page=True)
                page.locator('[data-tab="projects"]').click()
                page.locator('#project-name').fill('Laboratório local')
                page.locator('#project-root').fill(str(project))
                page.locator('#project-form button').click()
                page.locator('#projects h3').first.wait_for()
                page.locator('#scope').select_option(label='Laboratório local')
                page.locator('[data-tab="tasks"]').click()
                page.locator('#instruction').fill('Revisar alteração da quantidade inicial de 1 para 2.')
                page.locator('#task-form button').click()
                page.wait_for_function("document.querySelector('#task-file').options.length > 1")
                page.locator('#task-file').select_option('Stock.cs')
                page.locator('#load-file').click()
                page.wait_for_function("document.querySelector('#proposal').value.includes('Stock.cs')")
                changes=json.loads(page.locator('#proposal').input_value())
                changes[0]['content']=original.replace('Count = 1','Count = 2')
                page.locator('#proposal').fill(json.dumps(changes))
                page.locator('#proposal-form button').click()
                page.wait_for_function("document.querySelector('#diff').textContent.includes('Count = 2')")
                assert (project/'Stock.cs').read_text()==original
                report['flows'].append('stage proposal while preserving original')
                page.locator('#without-tests').check()
                page.once('dialog',lambda dialog:dialog.accept())
                page.locator('#apply-task').click()
                page.wait_for_function("document.querySelector('#task-state').textContent.startsWith('applied')")
                assert 'Count = 2' in (project/'Stock.cs').read_text()
                report['flows'].append('explicit reviewed application with baseline hash check')
                page.locator('[data-tab="knowledge"]').click()
                page.locator('#scope').select_option('global')
                page.set_viewport_size({'width':390,'height':844})
                page.screenshot(path=str(ROOT/'reports'/'ui-mobile.png'),full_page=True)
                report['flows'].append('responsive mobile view rendered')
                browser.close()
                report['success']=not report['errors']
        finally:
            server.shutdown();server.server_close();thread.join();app.close()
    (ROOT/'reports'/'ui-smoke.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return 0 if report['success'] else 1
if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        report={"success":False,"status":"blocked_or_failed","error":str(exc),"note":"Do not report this as a successful browser test. HTTP API tests are separate."}
        (ROOT/'reports'/'ui-smoke.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
        print(json.dumps(report,indent=2,ensure_ascii=False),file=sys.stderr)
        raise SystemExit(1)
