"""Browser routing and installer download with explicit generation/research doubles."""
import hashlib,json
from pathlib import Path
import sys,tempfile,threading
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from playwright.sync_api import sync_playwright,expect
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.foundation.service import FoundationService
from localauthor.server import create_server
from tests.test_chat_auto import publish_fixture
from tests.test_foundation import DummyText,register_fixture
from ui_profile_fixture import enter_profile,launch_browser
from update_readiness_fixture import native_scripts,check_readiness


def main():
    report={'success':False,'checks':[],'errors':[],'model_inference':'explicit double','research':'explicit double','installer':'synthetic exact-byte download'}
    def check(name,condition=True):assert condition,name;report['checks'].append(name)
    with tempfile.TemporaryDirectory() as temporary:
        base=Path(temporary);app=Application(Settings.load(base/'home'));folder=base/'project';folder.mkdir()
        project=app.store.add_project('Automatic QA fixture',str(folder));data,_=publish_fixture(app.settings.home)
        register_fixture(app.settings.home,base/'fixture-weights');app.chat.foundation=FoundationService(app.settings.home,text_factory=DummyText)
        def research(urls,scope,cancel):
            assert urls==['https://docs.python.org/3/'] and scope==project['id']
            app.store.ingest(scope,urls[0],'Python','Python documentation evidence fixture',kind='web')
            return [{'final_url':urls[0],'reused':False}]
        app.research.collect=research
        server=create_server(app,ROOT/'ui',port=0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();app.start()
        reports=ROOT/'reports';reports.mkdir(exist_ok=True)
        try:
            with sync_playwright() as p:
                browser=launch_browser(p.chromium,headless=True);page=browser.new_page(viewport={'width':1360,'height':960})
                update_scripts=native_scripts();page.add_init_script(update_scripts['TrackScript'])
                page.on('pageerror',lambda error:report['errors'].append(str(error)))
                submissions=[]
                page.on('request',lambda request:submissions.append(request.post_data_json) if request.url.endswith('/api/chat') and request.method=='POST' else None)
                def connect():
                    page.goto(f'http://127.0.0.1:{server.server_port}');page.locator('#local-token').fill(app.settings.token);page.locator('#connect-form button').click();enter_profile(page);expect(page.locator('#studio')).to_be_visible()
                def send(text,count):
                    page.locator('#message-input').fill(text);page.locator('#send').click();expect(page.locator('.message.assistant')).to_have_count(count)
                connect()
                check_readiness(page,check,update_scripts)
                check('Composer exposes no response mode or input format choice',page.locator('#compose select:visible').count()==0 and page.locator('#mode-notice').get_attribute('class').endswith('sr-only'))
                send('chat preciso do instalar do localauthor',1)
                expect(page.locator('.message.assistant')).to_contain_text('Aqui está meu instalador')
                expect(page.get_by_role('link',name='Baixar instalador')).to_be_visible()
                check('The reported installer request returns an actionable answer without a project script',submissions[-1]['mode']=='auto' and 'Vamos organizar' not in page.locator('.message.assistant').inner_text())
                with page.expect_download() as download:page.get_by_role('link',name='Baixar instalador').click()
                check('Browser downloads the exact authenticated installer',Path(download.value.path()).read_bytes()==data)
                page.screenshot(path=str(reports/'chat-auto-installer-desktop.png'))
                page.locator('#new-chat').click();send('Explique a arquitetura deste projeto',1)
                expect(page.locator('.message.assistant')).to_contain_text('Resposta do dublê')
                check('Ordinary chat automatically uses local conversation generation',page.evaluate("state.conversation.messages.at(-1).metadata.routing.selected")== 'foundation')
                check('Generated HTML remains inert',page.evaluate('window.PWNED') is None)
                send('Pesquise o mercado da empresa',2)
                expect(page.locator('.message.assistant').last).to_contain_text('Qual site ou endereço HTTPS')
                check('Missing research scope asks for the site without pretending to browse',page.evaluate('state.conversation.messages.at(-1).metadata.researched_now') is False)
                send('Pesquise Python em https://docs.python.org/3/',3)
                expect(page.locator('.message.assistant').last).to_contain_text('documentation evidence fixture')
                check('Research selects the collection tool and exposes its evidence',page.evaluate("state.conversation.messages.at(-1).metadata.routing.selected")== 'research')
                # Legacy unsent modes migrate to automatic requests; accepted
                # checkpoints keep their original payload in the recovery journal.
                page.locator('#new-chat').click();page.evaluate("async id=>api('/api/chat-draft',{project_id:id,conversation_id:'',text:'Explique a arquitetura',mode:'guide',revision:(await api('/api/chat-draft?project_id='+id+'&conversation_id=')).revision,pending:null})",project['id'])
                connect();expect(page.locator('#message-input')).to_have_value('Explique a arquitetura')
                page.locator('#send').click();expect(page.locator('.message.assistant')).to_have_count(1)
                check('Legacy unsent guide drafts no longer trap new requests in the old mode',submissions[-1]['mode']=='auto' and page.evaluate("state.conversation.messages.at(-1).metadata.origin")== 'foundation_text')
                page.evaluate("""async()=>{
                  const project_id=state.project.id,conversation_id=state.conversation.id,message='Pedido legado aceito',request_id=crypto.randomUUID().replaceAll('-',''),mode='guide';
                  const draft=await api('/api/chat-draft?project_id='+project_id+'&conversation_id='+conversation_id);
                  await api('/api/chat-draft',{project_id,conversation_id,text:message,mode,revision:draft.revision,pending:{request_id,conversation_id,message,mode}});
                  await api('/api/chat',{project_id,conversation_id,message,mode,request_id,input_format:'auto'});
                  for(let i=0;i<50;i++){const result=await api('/api/chat-request?project_id='+project_id+'&request_id='+request_id);if(result.state==='completed')return;await new Promise(resolve=>setTimeout(resolve,50));}
                  throw Error('Legacy fixture did not complete');
                }""")
                before=len(app.jobs.list());connect();expect(page.locator('#message-input')).to_have_value('');expect(page.locator('.message.assistant')).to_have_count(2)
                check('Accepted legacy requests reconcile once and clear their original text after mode migration',len(app.jobs.list())==before)
                page.evaluate("""()=>{const original=recovery.flushLocal;recovery.flushLocal=async()=>{await new Promise(resolve=>window.releaseFixtureFlush=resolve);recovery.flushLocal=original;return original();};}""")
                page.locator('#project-list button').first.click();expect(page.locator('#message-input')).to_be_disabled()
                check('Project navigation blocks editing before awaiting local draft persistence')
                page.evaluate('window.releaseFixtureFlush()');expect(page.locator('#message-input')).to_be_enabled()
                for width in [390,320]:
                    page.set_viewport_size({'width':width,'height':844});check('Automatic composer fits '+str(width),page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                page.screenshot(path=str(reports/'chat-auto-mobile.png'))
                check('No browser JavaScript errors',not report['errors']);report['success']=True;browser.close()
        except Exception as error:report['errors'].append(str(error));raise
        finally:
            server.shutdown();server.server_close();thread.join();app.close();(reports/'chat-auto-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
