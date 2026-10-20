"""Real persistent browser storage, renderer crash, offline and lost responses.

Synthetic data and deterministic guide responses; no model-quality claim.
"""
import json
import os
import signal
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server
from playwright.sync_api import sync_playwright,expect
from ui_profile_fixture import enter_profile,launch_persistent_browser,launch_browser


def main():
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    report={'success':False,'checks':[],'errors':[],'real_model_tested':False,'temporary_data_only':True}
    def check(name,condition=True):
        assert condition,name;report['checks'].append(name);print('PASS: '+name,flush=True)
    with tempfile.TemporaryDirectory() as temporary:
        base=Path(temporary);app=Application(Settings.load(base/'home'))
        projects=[]
        for label in ('Projeto Alpha','Projeto Beta'):
            folder=base/label;folder.mkdir();projects.append(app.store.add_project(label,str(folder)))
        started=threading.Event();release=threading.Event();original=app.jobs.handlers['chat']
        def slow(payload,cancel):
            if payload['message']=='slow recovery fixture':
                started.set()
                while not release.wait(.02):
                    if cancel.is_set():raise RuntimeError('Synthetic operation cancelled')
            return original(payload,cancel)
        app.jobs.handlers['chat']=slow
        server=create_server(app,ROOT/'ui',port=0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();app.start()
        url=f'http://127.0.0.1:{server.server_port}'
        contexts=[]
        try:
            with sync_playwright() as p:
                def reopen():
                    context=launch_persistent_browser(p.chromium,base/'browser',headless=True,viewport={'width':1360,'height':960});contexts.append(context)
                    page=context.pages[0] if context.pages else context.new_page()
                    page.on('pageerror',lambda error:report['errors'].append(str(error)))
                    connect(page);return context,page
                def connect(page,name=None):
                    page.goto(url);page.locator('#local-token').fill(app.settings.token);page.locator('#connect-form button').click()
                    if name is None:enter_profile(page)
                    else:
                        page.locator('#identity-gate[open],#identity-menu').first.wait_for(state='attached')
                        if not page.evaluate('!!window.LocalAuthorIdentity.user'):
                            page.locator('#identity-name').fill(name);page.locator('#identity-submit').click()
                    expect(page.locator('#studio')).to_be_visible()
                    if page.locator('#project-list button').count():expect(page.locator('#project-list button').first).to_be_enabled()
                def saved(page):expect(page.locator('#chat-recovery')).to_have_attribute('data-saved','true')
                def choose_project(page,name):
                    page.locator('#project-list button').filter(has_text=name).click();expect(page.locator('#project-heading')).to_have_text(name)
                def jobs():
                    with app.store.connect() as db:return db.execute("SELECT count(*) FROM jobs WHERE kind='chat'").fetchone()[0]
                context,page=reopen();choose_project(page,'Projeto Alpha')
                page.locator('#message-input').fill('Como revisar o projeto?');page.locator('#send').click();expect(page.locator('#messages .message')).to_have_count(2)
                conversation=page.evaluate('state.conversation.id');owner=page.evaluate('window.LocalAuthorIdentity.user.id')
                text='const ação = "teste";\n// </textarea><script>window.PWNED=1</script>\n\\path 🛫'
                page.locator('#message-input').fill(text);saved(page)
                check('Code and Unicode drafts are acknowledged only after saving')
                context.close();context,page=reopen()
                expect(page.locator('#message-input')).to_have_value(text);expect(page.locator('#messages .message')).to_have_count(2)
                check('Closing and reopening restores the last project, conversation and exact unsent text',page.evaluate('state.conversation.id')==conversation)
                check('Restored code is inert',page.evaluate('window.PWNED') is None and page.locator('#messages script').count()==0)
                choose_project(page,'Projeto Beta');expect(page.locator('#message-input')).to_have_value('')
                page.locator('#message-input').fill('Rascunho de Beta');saved(page)
                choose_project(page,'Projeto Alpha');page.locator('#conversation-list button').first.click();expect(page.locator('#message-input')).to_have_value(text)
                check('Drafts in different projects and conversations remain separate')
                page.route('**/api/chat-draft**',lambda route:route.abort())
                offline='Última edição com o servidor indisponível: \\arquivo\n// manter exatamente'
                page.locator('#message-input').fill(offline);expect(page.locator('#draft-status')).to_contain_text('Salvo neste computador')
                before=jobs()
                # CDP identifies processes belonging to this temporary browser.
                # Kill only its renderers (including Chromium's spare renderer),
                # not the browser or a user's process.
                browser_session=context.browser.new_browser_cdp_session()
                renderers=[item['id'] for item in browser_session.send('SystemInfo.getProcessInfo')['processInfo'] if item['type']=='renderer']
                assert 1<=len(renderers)<=5,renderers
                with page.expect_event('crash',timeout=10000):
                    for renderer in renderers:
                        try:os.kill(renderer,signal.SIGTERM)
                        except ProcessLookupError:pass
                check('The isolated renderer actually crashes')
                context.close();context,page=reopen();expect(page.locator('#message-input')).to_have_value(offline);saved(page)
                check('Offline edits survive a renderer crash and synchronize after reopening',jobs()==before)
                # Two simultaneous editors keep separate local branches. The
                # second writer must compare before replacing the server copy.
                other=context.new_page();connect(other)
                expect(other.locator('#message-input')).to_have_value(offline)
                page.locator('#message-input').fill('First writer');saved(page)
                other.locator('#message-input').fill('Second writer');expect(other.locator('#draft-status')).to_contain_text('Há outro rascunho')
                with app.store.connect() as db:
                    remote=db.execute('SELECT text FROM chat_drafts WHERE actor=? AND project_id=? AND conversation_id=?',(owner,projects[0]['id'],conversation)).fetchone()[0]
                check('A stale browser cannot silently overwrite another draft',remote=='First writer')
                other.get_by_role('button',name='Ver versões',exact=True).click()
                expect(other.locator('#draft-versions textarea')).to_have_count(2)
                values=other.locator('#draft-versions textarea').evaluate_all('(nodes)=>nodes.map(node=>node.value)')
                check('Version comparison preserves both exact texts',set(values)=={'First writer','Second writer'})
                other.locator('#draft-versions').get_by_role('button',name='Usar esta versão').first.click();expect(other.locator('#draft-versions')).to_have_count(0);saved(other)
                page.close();page=other
                page.screenshot(path=str(reports/'chat-recovery-desktop.png'))
                page.locator('#message-input').fill('slow recovery fixture');saved(page)
                submissions=[]
                def lose_response(route):
                    response=route.fetch();assert response.status==200;submissions.append(1);route.abort()
                page.route('**/api/chat',lose_response)
                page.locator('#send').click();expect(page.locator('#draft-status')).to_contain_text('Envio não confirmado')
                check('The server accepted the request although its response was lost',started.wait(2) and len(submissions)==1)
                count=jobs();context.close();release.set()
                deadline=time.monotonic()+5
                while time.monotonic()<deadline:
                    with app.store.connect() as db:
                        if db.execute("SELECT count(*) FROM jobs WHERE state IN ('running','queued')").fetchone()[0]==0:break
                    time.sleep(.02)
                context,page=reopen()
                expect(page.locator('#messages .message')).to_have_count(4);expect(page.locator('#message-input')).to_have_value('')
                check('Reopening reconciles a lost response without resending the accepted action',jobs()==count)
                context.close();context,page=reopen()
                expect(page.locator('#message-input')).to_have_value('');expect(page.locator('#messages .message')).to_have_count(4)
                check('A completed request does not resurrect an older conflicting draft',jobs()==count)
                page.set_viewport_size({'width':390,'height':844})
                expect(page.locator('#message-input')).to_be_visible()
                check('Recovery controls fit a narrow screen',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                page.screenshot(path=str(reports/'chat-recovery-mobile.png'))
                page.set_viewport_size({'width':1360,'height':960})
                page.route('**/api/chat',lambda route:route.abort())
                page.locator('#message-input').fill('Pedido ainda não recebido');saved(page);page.locator('#send').click()
                expect(page.locator('#draft-status')).to_contain_text('Envio não confirmado');count=jobs();context.close()
                context,page=reopen();expect(page.locator('#draft-status')).to_contain_text('não confirmou');expect(page.locator('#message-input')).to_have_value('Pedido ainda não recebido')
                check('An unknown request is preserved but never automatically replayed',jobs()==count)
                page.get_by_role('button',name='Reenviar com segurança',exact=True).click();expect(page.locator('#messages .message')).to_have_count(6)
                check('An explicit retry sends the preserved request once',jobs()==count+1)
                page.locator('#message-input').fill('Cópia confirmada pelo servidor');saved(page)
                # A separate installation has no IndexedDB snapshots. Even if
                # its local storage is unavailable, server recovery still works.
                fresh_browser=launch_browser(p.chromium,headless=True)
                fresh=fresh_browser.new_context();contexts.append(fresh)
                fresh.add_init_script("Object.defineProperty(window,'indexedDB',{get(){throw Error('Synthetic storage unavailable')}})")
                fresh_page=fresh.new_page();connect(fresh_page)
                expect(fresh_page.locator('#message-input')).to_have_value('Cópia confirmada pelo servidor')
                check('A separate browser installation recovers the confirmed server copy')
                fresh_page.locator('#message-input').fill('Edição sem armazenamento local')
                expect(fresh_page.locator('#draft-status')).to_contain_text('Rascunho salvo no servidor')
                with app.store.connect() as db:
                    remote=db.execute('SELECT text FROM chat_drafts WHERE actor=? AND project_id=? AND conversation_id=?',(owner,projects[0]['id'],conversation)).fetchone()[0]
                check('Unavailable local storage is explicit and does not prevent server saving',remote=='Edição sem armazenamento local')
                fresh_browser.close()
                person=app.identity.create_named_user(app.identity.user(owner),'Marketing fixture')
                page.locator('#identity-menu').click()
                with page.expect_navigation(wait_until='load'):page.get_by_role('button',name='Trocar perfil',exact=True).click()
                connect(page,'Marketing fixture')
                check('Changing profiles does not reveal the previous profile drafts',page.locator('#project-list button').count()==0 and page.locator('#message-input').input_value()=='')
                check('No credentials are stored in web storage',page.evaluate('localStorage.length+sessionStorage.length')==0)
                check('No browser JavaScript errors',not report['errors']);report['success']=True
                context.close()
        except Exception as exc:
            report['errors'].append(str(exc));raise
        finally:
            release.set()
            for context in contexts:
                try:context.close()
                except Exception:pass
            server.shutdown();server.server_close();thread.join();app.close()
            (reports/'chat-recovery-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
