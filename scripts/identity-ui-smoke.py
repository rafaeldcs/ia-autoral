"""Functional people/project isolation in two browser contexts; no model qualification."""
import json
import sys
import tempfile
import threading
from pathlib import Path
from ui_profile_fixture import enter_profile, launch_browser

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server
from playwright.sync_api import sync_playwright,expect


def main():
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    report={'success':False,'checks':[],'errors':[],'real_model_tested':False}
    def check(name,condition=True):assert condition,name;report['checks'].append(name)
    with tempfile.TemporaryDirectory() as temporary:
        base=Path(temporary);settings=Settings.load(base/'home');app=Application(settings)
        legacy=base/'legacy';legacy.mkdir();app.store.add_project('Histórico preservado',str(legacy))
        server=create_server(app,ROOT/'ui',port=0);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start();app.start()
        try:
            with sync_playwright() as p:
                browser=launch_browser(p.chromium,headless=True)
                owner_context=browser.new_context(viewport={'width':1440,'height':960})
                person_context=browser.new_context(viewport={'width':1440,'height':960})
                owner=owner_context.new_page();person=person_context.new_page()
                for page in (owner,person):page.on('pageerror',lambda error:report['errors'].append(str(error)))
                url=f'http://127.0.0.1:{server.server_port}'
                def connect(page,username=None):
                    page.goto(url);page.locator('#local-token').fill(settings.token);page.locator('#connect-form button').click()
                    if username is None:enter_profile(page)
                    else:
                        page.locator('#identity-gate[open]:visible, #identity-menu:visible').first.wait_for(state='visible')
                        if not page.evaluate('Boolean(window.LocalAuthorIdentity.user)'):
                            page.locator('#identity-name').fill(username);page.locator('#identity-submit').click()
                    expect(page.locator('#studio')).to_be_visible()
                def create_project(page,name):
                    page.locator('#add-project').click();page.locator('#project-name').fill(name);page.locator('#project-create button.primary').click();expect(page.locator('#project-heading')).to_have_text(name)
                    return page.evaluate('state.project.id')
                connect(owner)
                check('First local administrator receives existing projects',owner.locator('#project-list').inner_text().find('Histórico preservado')>=0)
                owner_id=owner.evaluate('window.LocalAuthorIdentity.user.id')
                owner.locator('#identity-menu').click();owner.locator('#identity-user-name').fill('Developer fixture')
                owner.locator('#identity-create-user button').click();expect(owner.locator('#identity-create-user .identity-status')).to_contain_text('Pessoa cadastrada')
                check('Named profiles have no username or password fields',owner.locator('#identity-account input[type=password], #identity-user-login').count()==0)
                owner.screenshot(path=str(reports/'identity-people-desktop.png'))
                owner.locator('#identity-account').get_by_role('button',name='Fechar',exact=True).click()
                project=create_project(owner,'Projeto privado da equipe')
                owner.locator('#message-input').fill('Como definir o critério de pronto?');owner.locator('#send').click();expect(owner.locator('#messages .message')).to_have_count(2)
                connect(person,'Developer fixture')
                check('Another browser has no access by default',person.locator('#project-list button').count()==0)
                own_project=create_project(person,'Projeto privado pessoal')
                person_id=person.evaluate('window.LocalAuthorIdentity.user.id')
                check('Managed folders belong to separate people',person_id in person.evaluate('state.project.root') and owner_id!=person_id)
                def sharing(role):
                    owner.locator('#show-rules').click();owner.locator('#project-sharing').click();owner.locator('#identity-share-user').select_option(person_id);owner.locator('#identity-share-role').select_option(role)
                    owner.locator('#identity-sharing form button').click();expect(owner.locator('#identity-sharing .identity-status')).to_contain_text('Acesso compartilhado')
                    owner.locator('#identity-sharing').get_by_role('button',name='Fechar',exact=True).click();owner.locator('[data-close="rules-dialog"]').click()
                sharing('reader');connect(person,'Developer fixture')
                person.locator('#project-list button').filter(has_text='Projeto privado da equipe').click()
                expect(person.locator('#new-chat')).to_be_disabled();expect(person.locator('#send')).to_be_disabled()
                check('Shared projects are labeled and readonly controls are disabled','Compartilhados comigo' in person.locator('#project-list').text_content())
                expect(person.locator('#conversation-list button')).to_have_count(0)
                person.locator('#conversation-filter').select_option('all');expect(person.locator('#conversation-list button')).to_have_count(1);person.locator('#conversation-list button').first.click()
                expect(person.locator('#messages .message-label').first).to_have_text('Browser laboratory')
                check('My conversations filter and message authors are explicit')
                status=person.evaluate("""async ({project,token})=>{const r=await fetch('/api/conversations',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({project_id:project,title:'Must not create'})});return r.status}""",{'project':project,'token':settings.token})
                check('Readonly cannot write through direct API',status==403)
                sharing('editor');connect(person,'Developer fixture');person.locator('#project-list button').filter(has_text='Projeto privado da equipe').click()
                person.locator('#message-input').fill('Como planejar os testes?');person.locator('#send').click();expect(person.locator('#messages .message')).to_have_count(2)
                person.locator('#conversation-filter').select_option('mine');expect(person.locator('#conversation-list button')).to_have_count(1)
                person.locator('#conversation-filter').select_option('all');expect(person.locator('#conversation-list button')).to_have_count(2)
                check('Editor creates an attributed conversation without mixing the default personal list')
                check('Administrator does not implicitly see another private project',own_project not in [p['id'] for p in owner.evaluate('state.projects')])
                owner.locator('#show-rules').click();owner.locator('#project-sharing').click();owner.locator(f'#identity-members [data-user-id="{person_id}"] button').click()
                expect(owner.locator(f'#identity-members [data-user-id="{person_id}"]')).to_have_count(0)
                owner.screenshot(path=str(reports/'identity-sharing-desktop.png'))
                owner.locator('#identity-sharing').get_by_role('button',name='Fechar',exact=True).click();owner.locator('[data-close="rules-dialog"]').click()
                connect(person,'Developer fixture');check('Revoked project disappears after refresh','Projeto privado da equipe' not in person.locator('#project-list').inner_text())
                for width in (320,390):
                    owner.set_viewport_size({'width':width,'height':844});owner.locator('#open-menu').click();owner.locator('#identity-menu').click()
                    check('Profile dialog fits mobile '+str(width),owner.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                    if width==390:owner.screenshot(path=str(reports/'identity-mobile.png'))
                    owner.locator('#identity-account').get_by_role('button',name='Fechar',exact=True).click();owner.locator('#close-menu').click()
                check('Credentials are absent from web storage',owner.evaluate('localStorage.length+sessionStorage.length')==0 and person.evaluate('localStorage.length+sessionStorage.length')==0)
                check('Profile session is HttpOnly',COOKIE_NOT_VISIBLE(person))
                second_tab=person_context.new_page();connect(second_tab,'Developer fixture')
                person.locator('#identity-menu').click()
                # Logout intentionally reloads this tab and broadcasts to its
                # sibling. Do not fill a form in either outgoing document.
                with person.expect_navigation(wait_until='load'),second_tab.expect_navigation(wait_until='load'):
                    person.get_by_role('button',name='Trocar perfil',exact=True).click()
                for tab in (person,second_tab):
                    tab.locator('#local-token').fill(settings.token);tab.locator('#connect-form button').click();expect(tab.locator('#identity-gate')).to_be_visible()
                check('Logout clears authenticated views in all tabs of the same browser')
                check('Name-only chooser explains that other people can select a profile',person.locator('#identity-gate').inner_text().find('pode escolher outro perfil')>=0 and person.locator('#identity-gate input[type=password]').count()==0)
                person.locator('#identity-profile').select_option(owner_id);expect(person.locator('#identity-name')).to_have_value('Browser laboratory');person.locator('#identity-submit').click()
                expect(person.locator('#studio')).to_be_visible();expect(person.locator('#project-list')).not_to_contain_text('Projeto privado pessoal')
                check('Switching profiles does not retain the previous private project list')
                browser.close()
            check('No browser JavaScript errors',not report['errors']);report['success']=True
        finally:
            server.shutdown();server.server_close();worker.join();app.close();(reports/'identity-ui-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


def COOKIE_NOT_VISIBLE(page):return 'la_profile' not in page.evaluate('document.cookie')


if __name__=='__main__':main()
