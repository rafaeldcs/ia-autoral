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
                user_requests=[]
                owner.on('request',lambda r:user_requests.append(r.url) if r.url.endswith('/api/identity/users') and r.method=='GET' else None)
                owner.locator('#message-input').fill('Rascunho antes de abrir o perfil')
                owner.locator('#identity-menu').click()
                expect(owner.locator('#identity-account')).to_be_visible()
                check('Personal profile opens compactly without team forms or requests',owner.locator('#identity-account input:visible,#identity-account select:visible').count()==0 and not user_requests and owner.locator('#identity-account').bounding_box()['height']<480)
                expect(owner.locator('.identity-folder')).not_to_be_visible()
                owner.screenshot(path=str(reports/'identity-profile-simple-desktop.png'))
                owner.evaluate("document.documentElement.dataset.theme='dark'")
                check('Profile actions remain readable in the dark theme',owner.evaluate("""() => {
                    function luminance(color) {const values=color.match(/[\\d.]+/g).slice(0,3).map(Number).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4});return values[0]*.2126+values[1]*.7152+values[2]*.0722;}
                    return [...document.querySelectorAll('.identity-account-actions button')].every(button=>{const style=getComputedStyle(button),a=luminance(style.color),b=luminance(style.backgroundColor);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)>=4.5;});
                }"""))
                owner.screenshot(path=str(reports/'identity-profile-simple-dark.png'))
                owner.evaluate("document.documentElement.dataset.theme='light'")
                owner.locator('.identity-profile-details summary').click()
                expect(owner.locator('.identity-folder')).to_be_visible()
                check('Technical folder and name-only explanation stay in optional details','pode escolher outro perfil' in owner.locator('.identity-profile-details').inner_text())
                owner.keyboard.press('Escape');expect(owner.locator('#identity-menu')).to_be_focused()
                check('Closing the personal menu preserves the draft',owner.locator('#message-input').input_value()=='Rascunho antes de abrir o perfil')
                owner.locator('#message-input').fill('')
                owner.locator('#identity-menu').click()
                owner.route('**/api/identity/users',lambda route:route.fulfill(status=503,content_type='application/json',body=json.dumps({'error':'Falha simulada ao carregar a equipe.'})))
                owner.get_by_role('button',name='Gerenciar equipe',exact=True).click()
                expect(owner.locator('#identity-team')).to_be_visible()
                expect(owner.locator('#identity-team>.identity-status')).to_contain_text('Falha simulada')
                expect(owner.locator('#identity-team').get_by_role('button',name='Tentar novamente')).to_be_visible()
                check('Team loading failure stays in the separate screen and offers a retry')
                owner.unroute('**/api/identity/users')
                owner.locator('#identity-team').get_by_role('button',name='Tentar novamente').click()
                expect(owner.locator('#identity-users .identity-user-row')).to_have_count(1)
                expect(owner.locator('#identity-team input:visible')).to_have_count(0)
                own_row=owner.locator(f'.identity-user-row[data-user-id="{owner_id}"]')
                own_row.locator('summary').click()
                own_row.locator('input[type=text]').fill('Browser laboratory revisado')
                own_row.get_by_role('button',name='Salvar perfil').click()
                expect(owner.locator('#identity-menu')).to_contain_text('Browser laboratory revisado')
                expect(owner.locator('.identity-profile-card strong')).to_have_text('Browser laboratory revisado')
                check('Renaming the selected profile immediately updates its menu and sidebar')
                own_row.locator('input[type=text]').fill('Browser laboratory')
                own_row.get_by_role('button',name='Salvar perfil').click()
                expect(owner.locator('#identity-menu .profile-name')).to_have_text('Browser laboratory')
                own_row.locator('summary').click()
                owner.locator('.identity-add-person>summary').click()
                owner.locator('#identity-user-name').fill('Developer fixture')
                owner.locator('#identity-create-user button').click();expect(owner.locator('#identity-create-user .identity-status')).to_contain_text('Pessoa cadastrada')
                check('Named profiles have no username or password fields',owner.locator('#identity-team input[type=password], #identity-user-login').count()==0)
                edited=owner.locator('.identity-user-row').filter(has=owner.locator('summary strong').filter(has_text='Developer fixture'))
                edited.locator('summary').click()
                edited.locator('input[type=text]').fill('Developer fixture editado');edited.locator('input[type=checkbox]').uncheck()
                edited.get_by_role('button',name='Salvar perfil').click();expect(edited.locator('.identity-status')).to_have_text('Perfil atualizado.')
                expect(edited.locator('summary')).to_contain_text('Inativo')
                check('Only the expanded person is edited and inactive state stays explicit')
                edited.locator('input[type=text]').fill('Browser laboratory');edited.locator('input[type=checkbox]').check()
                edited.get_by_role('button',name='Salvar perfil').click();expect(edited.locator('.identity-status')).to_contain_text('Já existe')
                check('Failed editing preserves entered data and the last saved person',edited.locator('input[type=text]').input_value()=='Browser laboratory' and edited.locator('summary strong').inner_text()=='Developer fixture editado')
                edited.locator('input[type=text]').fill('Developer fixture')
                edited.get_by_role('button',name='Salvar perfil').click();expect(edited.locator('.identity-status')).to_have_text('Perfil atualizado.')
                edited.locator('summary').click();owner.locator('.identity-add-person>summary').click()
                owner.screenshot(path=str(reports/'identity-people-desktop.png'))
                owner.locator('#identity-team').get_by_role('button',name='Voltar ao perfil',exact=True).click()
                expect(owner.get_by_role('button',name='Gerenciar equipe',exact=True)).to_be_focused()
                check('Returning from team management restores the simple personal menu')
                owner.locator('#identity-account').get_by_role('button',name='Fechar',exact=True).click()
                project=create_project(owner,'Projeto privado da equipe')
                owner.locator('#message-input').fill('Como definir o critério de pronto?');owner.locator('#send').click();expect(owner.locator('#messages .message')).to_have_count(2)
                connect(person,'Developer fixture')
                person.locator('#identity-menu').click()
                check('Regular profile keeps the same simple menu without team administration',person.locator('#identity-account').get_by_role('button',name='Gerenciar equipe').count()==0 and person.locator('#identity-account input:visible').count()==0)
                person.locator('#identity-account').get_by_role('button',name='Fechar',exact=True).click()
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
                    expect(owner.locator('#identity-account').get_by_role('button',name='Trocar perfil')).to_be_in_viewport()
                    owner.locator('#identity-account').get_by_role('button',name='Gerenciar equipe').click()
                    expect(owner.locator('#identity-users .identity-user-row')).to_have_count(2)
                    check('Team list stays compact and forms closed on mobile '+str(width),owner.locator('#identity-team input:visible').count()==0 and owner.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                    owner.keyboard.press('Escape');expect(owner.get_by_role('button',name='Gerenciar equipe',exact=True)).to_be_focused()
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
                owner.set_viewport_size({'width':1440,'height':960})
                owner.goto(url+'/advanced');owner.locator('#token').fill(settings.token);owner.locator('#login-form button').click()
                expect(owner.locator('#identity-menu')).to_be_visible();owner.locator('#identity-menu').click()
                check('The same compact profile works from advanced tools',owner.locator('#identity-account input:visible').count()==0)
                check('Profile primary action has readable contrast outside the chat theme',owner.evaluate("""() => {
                    const style=getComputedStyle(document.querySelector('.identity-primary'));
                    function l(c){const v=c.match(/[\\d.]+/g).slice(0,3).map(Number).map(x=>{x/=255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4});return v[0]*.2126+v[1]*.7152+v[2]*.0722;}
                    const a=l(style.color),b=l(style.backgroundColor);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)>=4.5;
                }"""))
                owner.screenshot(path=str(reports/'identity-profile-advanced.png'))
                owner.keyboard.press('Escape');connect(owner)
                owner.locator('#identity-menu').click();owner.get_by_role('button',name='Gerenciar equipe',exact=True).click()
                own_row=owner.locator(f'.identity-user-row[data-user-id="{owner_id}"]');own_row.locator('summary').click()
                own_row.locator('input[type=text]').fill('Browser laboratory race fixture')
                # Simulate another tab changing the selected identity between
                # the save and its status refresh. Never keep the old workspace
                # visible after receiving a different identity.
                owner.route('**/api/identity/status',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps({'configured':True,'user':{'id':person_id,'name':'Developer fixture','role':'user'}})))
                with owner.expect_navigation(wait_until='load'):
                    own_row.get_by_role('button',name='Salvar perfil').click()
                owner.unroute('**/api/identity/status')
                expect(owner.locator('#studio')).to_be_hidden()
                check('Concurrent profile change during editing reloads before exposing a different identity in the old workspace')
                browser.close()
            check('No browser JavaScript errors',not report['errors']);report['success']=True
        finally:
            server.shutdown();server.server_close();worker.join();app.close();(reports/'identity-ui-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


def COOKIE_NOT_VISIBLE(page):return 'la_profile' not in page.evaluate('document.cookie')


if __name__=='__main__':main()
