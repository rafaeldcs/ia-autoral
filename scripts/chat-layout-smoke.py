"""Real browser checks of navigation, composer and responsive chat, temporary data only."""
from ui_profile_fixture import enter_profile, existing_folder, launch_browser
import json
import shutil
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'),str(ROOT)]
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server
from localauthor.foundation.service import FoundationService
from tests.test_foundation import DummyText,register_fixture
from localauthor.identity_context import current_actor
from playwright.sync_api import sync_playwright, expect


def main():
    report = {'checks': [], 'errors': [], 'success': False, 'scope': 'temporary projects; automatic chat with explicit generation double; no model qualification'}
    art = ROOT / 'reports'
    art.mkdir(exist_ok=True)

    def check(name, value=True):
        assert value, name
        report['checks'].append(name)

    def check_chat_space(page, name, content):
        # Measure usable edges, not CSS declarations: no centered narrow column,
        # no overlap with the sidebar/panel, and aligned welcome/history/editor.
        metrics = page.evaluate('''(selector) => {
            const chat = document.querySelector('.chat').getBoundingClientRect();
            const composer = document.querySelector('#compose').getBoundingClientRect();
            const content = document.querySelector(selector).getBoundingClientRect();
            return {left:composer.left-chat.left,right:chat.right-composer.right,
                width:chat.width,aligned:Math.abs(content.left-composer.left),
                overflow:document.documentElement.scrollWidth>innerWidth};
        }''', content)
        check(name, 12 <= metrics['left'] <= 40 and 12 <= metrics['right'] <= 40
              and metrics['aligned'] <= 2 and not metrics['overflow'])

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        project = base / 'project'
        project.mkdir()
        settings = Settings.load(base / 'data')
        app = Application(settings)
        class LayoutText(DummyText):
            def generate(self,messages,cancel=None):
                assert json.loads(messages[-1]['content'])['orientacao_do_projeto']['definition_of_done']=='Revisão e testes aprovados.','Saved project criteria must reach the model context'
                return 'Dublê explícito de conversa. Critério recebido: Revisão e testes aprovados.',False
        register_fixture(settings.home,base/'fixture-weights')
        app.chat.foundation=FoundationService(settings.home,text_factory=LayoutText)
        app.start()
        server = create_server(app, ROOT / 'ui', port=0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with sync_playwright() as pw:
                browser = launch_browser(pw.chromium,headless=True, executable_path=shutil.which('chromium') or None)
                page = browser.new_page(viewport={'width': 1440, 'height': 900})
                page.on('pageerror', lambda error: report['errors'].append(str(error)))
                url = f'http://127.0.0.1:{server.server_port}'
                page.goto(url)
                page.locator('#local-token').fill(settings.token)
                page.locator('#connect-form button').click()
                enter_profile(page)
                expect(page.locator('#studio')).to_be_visible()
                check('Login clears credential and never stores it', page.locator('#local-token').input_value() == '' and page.evaluate('localStorage.length + sessionStorage.length') == 0)
                expect(page.locator('#send')).to_be_disabled()
                expect(page.locator('#new-chat')).to_be_disabled()
                page.locator('#start-project').click()
                page.locator('#project-name').fill('Projeto de demonstração')
                existing_folder(page)
                page.locator('#project-root').fill(str(project))
                page.locator('#project-create button.primary').click()
                expect(page.locator('#project-heading')).to_have_text('Projeto de demonstração')
                check('Projects and conversations share one sidebar', page.locator('#sidebar #project-list').count() == page.locator('#sidebar #conversation-list').count() == 1)
                check('Chat width is not consumed by a second navigation rail', page.locator('.chat').bounding_box()['width'] > 1000)
                check('Neither format nor response mode requires a composer choice', page.locator('#input-format').get_attribute('type') == 'hidden' and page.locator('#compose select:visible').count() == 0)
                check('Empty composer is compact and send is disabled', page.locator('#compose').bounding_box()['height'] < 150 and page.locator('#send').is_disabled() and page.locator('#input-count').is_hidden())
                for width in (1440, 1920):
                    page.set_viewport_size({'width': width, 'height': 1080})
                    check_chat_space(page, f'Welcome and composer use the full main area at {width}', '.suggestions')
                page.set_viewport_size({'width': 1440, 'height': 900})
                formats = json.loads((ROOT / 'tests/fixtures/message_formats.json').read_text(encoding='utf-8'))
                for sample in formats:
                    detected = page.evaluate('(value) => looksLikeCode(value)', sample['message'])
                    check('Editor agrees with server fixture: ' + sample['message'].splitlines()[0][:55], detected == (sample['format'] == 'code'))
                for index in range(20):
                    extra = base / f'project-{index}'
                    extra.mkdir()
                    app.store.add_project(f'Outro projeto {index:02d}', str(extra),owner_id=page.evaluate('window.LocalAuthorIdentity.user.id'))
                page.evaluate("async () => { state.projects = await api('/api/projects'); renderProjects(); }")
                expect(page.locator('#project-list button')).to_have_count(21)
                check('Many projects keep conversation navigation visible', page.locator('.conversation-rail').bounding_box()['y'] < 500 and page.locator('.conversation-rail').bounding_box()['y'] + page.locator('.conversation-rail').bounding_box()['height'] <= 900)
                expect(page.locator('#project-list button:visible')).to_have_count(4)
                check('Project preview keeps the selected project visible', page.locator('#project-list button[aria-current="true"]').is_visible())
                page.locator('#toggle-projects').focus()
                page.keyboard.press('Enter')
                expect(page.locator('#toggle-projects')).to_have_attribute('aria-expanded', 'true')
                expect(page.locator('#project-list button:visible')).to_have_count(21)
                page.locator('#project-list button').filter(has_text='Outro projeto 00').click()
                expect(page.locator('#project-heading')).to_have_text('Outro projeto 00')
                expect(page.locator('#toggle-projects')).to_have_attribute('aria-expanded', 'false')
                expect(page.locator('#project-list button:visible')).to_have_count(4)
                expect(page.locator('#message-input')).to_be_focused()
                check('Selecting a project from the full list returns to a compact preview', page.locator('#project-list button[aria-current="true"]').is_visible())
                page.locator('#toggle-projects').click()
                page.locator('#project-list button').filter(has_text='Projeto de demonstração').click()
                expect(page.locator('#repair-examples')).not_to_be_visible()
                draft = 'Revisar interface: acentos, <script>window.PWNED=1</script> e comentários.'
                page.locator('#message-input').fill(draft)
                page.locator('#open-tools').click()
                expect(page.get_by_role('dialog', name='Ferramentas e configurações')).to_be_visible()
                page.locator('[data-appearance]').select_option('dark')
                expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
                check('Dark appearance changes the actual color scheme', page.evaluate("getComputedStyle(document.documentElement).colorScheme === 'dark'"))
                page.locator('[data-appearance]').select_option('system')
                page.emulate_media(color_scheme='dark')
                expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
                page.emulate_media(color_scheme='light')
                expect(page.locator('html')).to_have_attribute('data-theme', 'light')
                check('System appearance follows a changing operating-system preference')
                page.locator('[data-appearance]').select_option('dark')
                check('Only appearance is persisted, never credentials or messages', page.evaluate("Object.keys(localStorage).every(key => key === 'localauthor.appearance') && sessionStorage.length === 0 && localStorage.getItem('localauthor.appearance') === 'dark'"))
                for name, href in [('Marketing', '/marketing'), ('Modelos locais', '/foundation'), ('Ferramentas avançadas', '/advanced')]:
                    check(name + ' has a real destination', page.locator('.tool-links').get_by_role('link', name=name).get_attribute('href') == href)
                page.keyboard.press('Escape')
                expect(page.locator('#open-tools')).to_be_focused()
                check('Closing tools preserves draft and automatic routing', page.locator('#message-input').input_value() == draft and page.locator('#response-mode').input_value() == 'auto')
                page.locator('#close-menu').click()
                expect(page.locator('#sidebar')).not_to_be_visible()
                expect(page.locator('#open-menu')).to_be_focused()
                check('Collapsed navigation preserves draft', page.locator('#message-input').input_value() == draft)
                check_chat_space(page, 'Collapsing the sidebar expands welcome and composer', '.suggestions')
                page.locator('#open-menu').click()
                expect(page.locator('#sidebar')).to_be_visible()
                page.locator('#show-rules').click()
                page.locator('#method').select_option('scrum')
                page.locator('#wip').fill('3')
                page.locator('#done').fill('Revisão e testes aprovados.')
                page.locator('#rules-form button.primary').click()
                page.locator('#send').click()
                expect(page.locator('.message.assistant')).to_have_count(1)
                expect(page.locator('.message.assistant')).to_contain_text('Revisão e testes aprovados.')
                details=page.locator('.message.assistant .response-details')
                expect(details.locator('small')).not_to_be_visible()
                details.locator('summary').focus()
                page.keyboard.press('Enter')
                expect(details.locator('small')).to_contain_text('Memória não é treinamento')
                check('Response provenance remains available by keyboard without repeating a visible technical footer')
                details.locator('summary').click()
                page.evaluate("""() => {state.conversation.messages.push({role:'assistant',content:'Dublê explícito de resposta interrompida.',metadata:{origin:'foundation_text',possibly_truncated:true,notice:'Saída possivelmente incompleta.'}});renderMessages();}""")
                expect(page.locator('.response-warning')).to_be_visible()
                expect(page.locator('.response-warning')).to_have_attribute('role','status')
                check('A truncated response keeps its warning visible outside the provenance disclosure')
                page.evaluate('state.conversation.messages.pop();renderMessages()')
                page.evaluate("() => {state.conversation.messages.push({role:'assistant',content:'Código ainda proposto.',metadata:{instruction_review:{violations:['O limite explícito não foi atendido.']}}});renderMessages();}")
                expect(page.locator('.response-warning')).to_contain_text('O limite explícito não foi atendido.')
                check('Unmet instruction checks remain visible instead of becoming a hidden success claim')
                page.evaluate('state.conversation.messages.pop();renderMessages()')
                fenced_code='\t// Ação: "não alterar"  \r\nconst texto = "é 😀";\r\n</code><script>window.FENCE_RAN=1</script>\r\n'
                fenced_reply='Explicação antes.\r\n```typescript\r\n'+fenced_code+'```\r\nDepois.\n~~~sql\nSELECT 1;\n~~~\n'
                page.evaluate('content=>{state.conversation.messages.push({role:"assistant",content,metadata:{origin:"foundation_text"}});renderMessages()}',fenced_reply)
                blocks=page.locator('.message.assistant').last.locator('.code-block')
                expect(blocks).to_have_count(2)
                check('Mixed replies render fenced code with language labels and exact Unicode/CRLF',blocks.first.locator('code').text_content()==fenced_code and blocks.nth(1).locator('code').text_content()=='SELECT 1;\n' and blocks.first.locator('.code-language').inner_text()=='TypeScript')
                check('Markup inside model code never becomes HTML',page.evaluate('window.FENCE_RAN') is None and blocks.locator('script').count()==0)
                page.evaluate('''() => { window.layoutClipboardOriginal=Object.getOwnPropertyDescriptor(navigator,'clipboard');Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.layoutCopiedText=text;}}}); }''')
                blocks.first.get_by_role('button',name='Copiar código TypeScript',exact=True).click()
                check('Code copy sends only original code bytes to the clipboard adapter',page.evaluate('window.layoutCopiedText')==fenced_code)
                page.locator('.message.assistant').last.locator('.copy-message').click()
                check('Whole-message copy retains the original fence delimiters and prose',page.evaluate('window.layoutCopiedText')==fenced_reply)
                page.evaluate("() => {if(window.layoutClipboardOriginal)Object.defineProperty(navigator,'clipboard',window.layoutClipboardOriginal);else delete navigator.clipboard;state.conversation.messages.pop();renderMessages();}")
                page.evaluate("() => {state.conversation.messages.push({role:'assistant',content:'using System;\\npublic class Tarefa {}',metadata:{format:'code'}});renderMessages();}")
                check('Unfenced model code retains its original text inside a copyable code block',page.locator('.message.assistant').last.locator('.code-block code').text_content()=='using System;\npublic class Tarefa {}')
                page.evaluate('state.conversation.messages.pop();renderMessages()')
                edge_reply='````text\nLinha\n```\nainda no bloco\n````\n~~~sql\nSELECT 2;'
                page.evaluate('content=>{state.conversation.messages.push({role:"assistant",content,metadata:{origin:"foundation_text"}});renderMessages()}',edge_reply)
                blocks=page.locator('.message.assistant').last.locator('.code-block')
                expect(blocks).to_have_count(2)
                check('A shorter fence cannot close a longer opening fence',blocks.first.locator('code').text_content()=='Linha\n```\nainda no bloco\n')
                expect(blocks.last.locator('.code-incomplete')).to_be_visible()
                check('An unclosed generated fence keeps code and warns instead of inventing its end',blocks.last.locator('code').text_content()=='SELECT 2;')
                page.set_viewport_size({'width':320,'height':568})
                page.evaluate(r'''() => {state.conversation.messages.at(-1).content='```text\n'+('long_identifier_'.repeat(150))+'\n```\n';renderMessages();}''')
                pre=page.locator('.message.assistant').last.locator('.fenced-code')
                check('Long code scrolls inside its block without widening the mobile page',pre.evaluate('node=>node.scrollWidth>node.clientWidth') and page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                pre.focus()
                expect(pre).to_be_focused()
                check('Code scrolling remains reachable by keyboard')
                page.screenshot(path=str(art/'chat-code-mobile.png'))
                page.set_viewport_size({'width':1440,'height':900})
                page.evaluate('state.conversation.messages.pop();renderMessages()')
                check('Automatic conversation receives saved project preferences',page.evaluate("state.conversation.messages.at(-1).metadata.routing.selected==='foundation'&&state.conversation.messages.at(-1).metadata.origin==='foundation_text'"))
                check('Messages remain inert text', page.evaluate('window.PWNED') is None and page.locator('.message.user .message-content').text_content() == draft)
                expect(page.locator('#conversation-list button')).to_have_count(1)
                expect(page.locator('#conversation-list button')).to_be_in_viewport()
                check('Saved conversation remains in view with twenty-one projects')
                expect(page.locator('#notification')).to_be_hidden(timeout=10000)
                for width in (1440, 1920):
                    page.set_viewport_size({'width': width, 'height': 1080})
                    check_chat_space(page, f'History and composer use the full main area at {width}', '.message.assistant')
                page.screenshot(path=str(art / 'chat-layout-wide-history.png'))
                page.set_viewport_size({'width': 1440, 'height': 900})
                page.screenshot(path=str(art / 'chat-layout-desktop.png'))
                page.locator('#new-chat').click()
                expect(page.locator('#welcome')).to_be_visible()
                expect(page.locator('#welcome h1')).to_have_text('Vamos dar forma à sua ideia?')
                check('Friendly welcome still identifies the selected project', 'Projeto de demonstração' in page.locator('#welcome-copy').inner_text())
                page.screenshot(path=str(art / 'chat-layout-welcome.png'))
                page.set_viewport_size({'width': 1920, 'height': 1080})
                check_chat_space(page, 'Wide welcome remains aligned with the composer', '.suggestions')
                page.screenshot(path=str(art / 'chat-layout-wide-welcome.png'))
                page.set_viewport_size({'width': 1440, 'height': 900})
                page.locator('#conversation-list button').click()
                expect(page.locator('.message.assistant')).to_have_count(1)
                check('New conversation and persisted history remain reachable')
                code = '\t// Ação: "não alterar"  \nconst texto = "é 😀";\n// </textarea><script>window.CODE_RAN=1</script>\n'
                page.locator('#message-input').fill(code)
                expect(page.locator('#message-input')).to_have_attribute('spellcheck', 'false')
                check('Editor grows for multiline code without rewriting it', page.locator('#message-input').bounding_box()['height'] > 52 and page.locator('#message-input').input_value() == code)
                page.locator('#send').click()
                expect(page.locator('.message.assistant')).to_have_count(2)
                check('Server automatically stores and renders code literally', page.locator('.message.user .code-content').last.text_content() == code and page.evaluate('state.conversation.messages.at(-2).metadata.format') == 'code' and page.evaluate('window.CODE_RAN') is None)
                page.locator('#message-input').fill('Agora explique o projeto em português.')
                expect(page.locator('#message-input')).to_have_attribute('spellcheck', 'true')
                check('Editor returns to prose and hides routine character count', 'code-input' not in (page.locator('#message-input').get_attribute('class') or '') and page.locator('#input-count').is_hidden())
                page.locator('#message-input').fill('á' * 7900)
                check('Length warning appears near the real limit', page.locator('#input-count').is_visible())
                page.locator('#message-input').fill('')
                page.locator('#open-browser').click()
                expect(page.locator('#browser-panel')).to_be_visible()
                expect(page.locator('#browser-url')).to_be_visible()
                check('Evidence and chat do not overlap', page.locator('.main').bounding_box()['x'] + page.locator('.main').bounding_box()['width'] <= page.locator('#browser-panel').bounding_box()['x'] + 1)
                for width in (1440, 1024):
                    page.set_viewport_size({'width': width, 'height': 900})
                    check_chat_space(page, f'History and composer fit beside investigation at {width}', '.message.assistant')
                page.screenshot(path=str(art / 'chat-layout-investigation.png'))
                page.set_viewport_size({'width': 1440, 'height': 900})
                page.keyboard.press('Escape')
                expect(page.locator('#browser-panel')).not_to_be_visible()
                expect(page.locator('#open-browser')).to_be_focused()
                page.locator('#open-tools').click()
                page.locator('#repair-examples summary').click()
                page.get_by_role('button', name='Testar configuração do servidor').click()
                expect(page.locator('#tools-dialog')).not_to_be_visible()
                expect(page.locator('#message-input')).to_be_focused()
                check('Code example is detected automatically and retains experimental mode', page.locator('#input-format').input_value() == 'auto' and page.locator('#response-mode').input_value() == 'model' and page.locator('#message-input').get_attribute('spellcheck') == 'false')
                page.locator('#message-input').fill('Rascunho preservado no celular')
                for width, height in [(1280, 720), (1024, 768), (768, 1024), (390, 844), (320, 568)]:
                    page.set_viewport_size({'width': width, 'height': height})
                    check(f'No horizontal overflow at {width}x{height}', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    box = page.locator('#send').bounding_box()
                    check(f'Composer stays inside viewport at {width}x{height}', box is not None and box['y'] >= 0 and box['y'] + box['height'] <= height)
                    check_chat_space(page, f'History and composer share usable edges at {width}x{height}', '.message.assistant')
                page.set_viewport_size({'width': 390, 'height': 844})
                page.locator('#open-menu').click()
                expect(page.locator('#sidebar-scrim')).to_be_visible()
                expect(page.locator('#close-menu')).to_be_focused()
                page.keyboard.press('Shift+Tab')
                expect(page.locator('#logout')).to_be_focused()
                page.keyboard.press('Tab')
                expect(page.locator('#close-menu')).to_be_focused()
                check('Mobile drawer traps keyboard focus')
                page.keyboard.press('Escape')
                expect(page.locator('#sidebar')).not_to_be_visible()
                expect(page.locator('#open-menu')).to_be_focused()
                check('Escape restores mobile trigger and preserves draft', page.locator('#message-input').input_value() == 'Rascunho preservado no celular')
                page.locator('#open-menu').click()
                page.locator('#new-chat').click()
                expect(page.locator('#sidebar')).not_to_be_visible()
                expect(page.locator('#notification')).to_be_hidden(timeout=10000)
                page.screenshot(path=str(art / 'chat-layout-mobile.png'))
                page.locator('#open-tools').click()
                page.screenshot(path=str(art / 'chat-layout-tools.png'))
                page.keyboard.press('Escape')
                for route in ['/advanced', '/foundation', '/marketing']:
                    page.goto(url + route)
                    check(route + ' preserves appearance and remains responsive', page.evaluate("getComputedStyle(document.documentElement).colorScheme === 'dark' && document.documentElement.scrollWidth <= innerWidth"))
                page.set_viewport_size({'width': 1440, 'height': 900})
                page.goto(url)
                page.locator('#local-token').fill(settings.token)
                page.locator('#connect-form button').click()
                enter_profile(page)
                expect(page.locator('#studio')).to_be_visible()
                page.locator('#project-list button').filter(has_text='Projeto de demonstração').click()
                page.locator('#new-chat').click()
                page.locator('#message-input').fill('Lembre-se: Preserve o azul da marca.')
                page.locator('#send').click()
                expect(page.locator('.message.assistant')).to_contain_text('Guardei esta preferência')
                check('Memory acknowledgement appears as a visible chat turn')
                page.locator('#new-chat').click()
                page.locator('#message-input').fill('O que você lembra deste projeto?')
                page.locator('#send').click()
                expect(page.locator('.message.assistant')).to_contain_text('Preserve o azul da marca.')
                check('New conversations list the saved project memory')
                page.locator('#message-input').fill('Esqueça: Preserve o azul da marca.')
                page.locator('#send').click()
                expect(page.locator('.message.assistant').last).to_contain_text('Deixei de usar')
                page.locator('#new-chat').click()
                page.locator('#message-input').fill('O que você lembra deste projeto?')
                page.locator('#send').click()
                expect(page.locator('.message.assistant')).to_contain_text('Ainda não há memórias')
                check('Revocation remains effective in a subsequent conversation')
                # Long, synthetic histories exercise the actual overflow and focus
                # behavior without writing conversations to the running server.
                project_id=page.evaluate('state.project.id')
                actor=current_actor.set(page.evaluate('window.LocalAuthorIdentity.user.id'))
                try:
                    for index in range(30):
                        app.chat.create(project_id,f'Conversa {index:02d} — planejamento, revisão e próximos passos da equipe')
                finally:
                    current_actor.reset(actor)
                page.evaluate('renderConversations()')
                expect(page.locator('#conversation-list button')).to_have_count(34)
                for theme in ('light','dark'):
                    page.evaluate('(theme) => document.documentElement.dataset.theme=theme',theme)
                    page.locator('.sidebar-scroll').evaluate('(node) => node.scrollTop=0')
                    check(theme+' sidebar has one scroll region',page.evaluate("""() => {
                        const scrollable=[...document.querySelectorAll('#sidebar *')].filter(node=>
                          ['auto','scroll'].includes(getComputedStyle(node).overflowY)&&node.scrollHeight>node.clientHeight+1);
                        return scrollable.length===1&&scrollable[0].classList.contains('sidebar-scroll');
                    }"""))
                    expect(page.locator('#identity-menu')).to_be_in_viewport()
                    expect(page.locator('#sidebar-tools')).to_be_in_viewport()
                    page.screenshot(path=str(art / f'chat-sidebar-{theme}.png'))
                last_title=page.locator('#conversation-list button').last.get_attribute('title')
                page.locator('#conversation-list button').last.click()
                page.wait_for_function('(title) => !state.busy && state.conversation?.title === title',arg=last_title)
                expect(page.locator('#project-list button[aria-current="true"]')).to_have_attribute('title','Projeto de demonstração')
                check('Last conversation in a long history opens without losing the project',page.evaluate('state.conversation.title')==last_title)
                expect(page.locator('#sidebar-tools')).to_be_in_viewport()
                page.locator('#sidebar-tools').click()
                expect(page.locator('#tools-dialog')).to_be_visible()
                page.keyboard.press('Escape')
                expect(page.locator('#sidebar-tools')).to_be_focused()
                check('Compact settings control preserves its accessible name and restores focus')
                for width,height in [(390,844),(320,568),(1024,600)]:
                    page.set_viewport_size({'width':width,'height':height})
                    if width<760:page.locator('#open-menu').click()
                    page.locator('.sidebar-scroll').evaluate('(node) => node.scrollTop=0')
                    expect(page.locator('#identity-menu')).to_be_in_viewport()
                    expect(page.locator('#sidebar-tools')).to_be_in_viewport()
                    check(f'Long histories keep the footer and page within {width}x{height}',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                    page.locator('#conversation-filter').focus()
                    page.keyboard.press('Tab')
                    expect(page.locator('#conversation-list button').first).to_be_focused()
                    check(f'Filter remains in normal keyboard order at {width}px')
                    page.screenshot(path=str(art / f'chat-sidebar-{width}.png'))
                    if width<760:page.keyboard.press('Escape')
                check('No JavaScript exceptions', not report['errors'])
                browser.close()
                report['success'] = True
        finally:
            server.shutdown()
            server.server_close()
            worker.join()
            app.close()
    (art / 'chat-layout-smoke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': len(report['checks']), 'success': report['success']}))


if __name__ == '__main__':
    main()
