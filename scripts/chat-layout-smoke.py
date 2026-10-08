"""Real browser checks of navigation, composer and responsive chat, temporary data only."""
import json
import shutil
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server
from playwright.sync_api import sync_playwright, expect


def main():
    report = {'checks': [], 'errors': [], 'success': False, 'scope': 'temporary projects; structured guide; no model qualification'}
    art = ROOT / 'reports'
    art.mkdir(exist_ok=True)

    def check(name, value=True):
        assert value, name
        report['checks'].append(name)

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        project = base / 'project'
        project.mkdir()
        settings = Settings.load(base / 'data')
        app = Application(settings)
        app.start()
        server = create_server(app, ROOT / 'ui', port=0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True, executable_path=shutil.which('chromium') or None)
                page = browser.new_page(viewport={'width': 1440, 'height': 900})
                page.on('pageerror', lambda error: report['errors'].append(str(error)))
                url = f'http://127.0.0.1:{server.server_port}'
                page.goto(url)
                page.locator('#local-token').fill(settings.token)
                page.locator('#connect-form button').click()
                expect(page.locator('#studio')).to_be_visible()
                check('Login clears credential and never stores it', page.locator('#local-token').input_value() == '' and page.evaluate('localStorage.length + sessionStorage.length') == 0)
                expect(page.locator('#send')).to_be_disabled()
                expect(page.locator('#new-chat')).to_be_disabled()
                page.locator('#start-project').click()
                page.locator('#project-name').fill('Projeto de demonstração')
                page.locator('#project-root').fill(str(project))
                page.locator('#project-create button.primary').click()
                expect(page.locator('#project-heading')).to_have_text('Projeto de demonstração')
                check('Projects and conversations share one sidebar', page.locator('#sidebar #project-list').count() == page.locator('#sidebar #conversation-list').count() == 1)
                check('Chat width is not consumed by a second navigation rail', page.locator('.chat').bounding_box()['width'] > 1000)
                check('Format selection is absent from the composer', page.locator('#input-format').get_attribute('type') == 'hidden' and page.locator('#compose select').count() == 1)
                check('Empty composer is compact and send is disabled', page.locator('#compose').bounding_box()['height'] < 150 and page.locator('#send').is_disabled() and page.locator('#input-count').is_hidden())
                formats = json.loads((ROOT / 'tests/fixtures/message_formats.json').read_text(encoding='utf-8'))
                for sample in formats:
                    detected = page.evaluate('(value) => looksLikeCode(value)', sample['message'])
                    check('Editor agrees with server fixture: ' + sample['message'].splitlines()[0][:55], detected == (sample['format'] == 'code'))
                for index in range(20):
                    extra = base / f'project-{index}'
                    extra.mkdir()
                    app.store.add_project(f'Outro projeto {index:02d}', str(extra))
                page.evaluate("async () => { state.projects = await api('/api/projects'); renderProjects(); }")
                expect(page.locator('#project-list button')).to_have_count(21)
                check('Many projects keep conversation navigation visible', page.locator('.conversation-rail').bounding_box()['y'] < 500 and page.locator('.conversation-rail').bounding_box()['y'] + page.locator('.conversation-rail').bounding_box()['height'] <= 900)
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
                check('Closing tools preserves draft and mode', page.locator('#message-input').input_value() == draft and page.locator('#response-mode').input_value() == 'guide')
                page.locator('#close-menu').click()
                expect(page.locator('#sidebar')).not_to_be_visible()
                expect(page.locator('#open-menu')).to_be_focused()
                check('Collapsed navigation preserves draft', page.locator('#message-input').input_value() == draft)
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
                check('Guide still uses saved project preferences')
                check('Messages remain inert text', page.evaluate('window.PWNED') is None and page.locator('.message.user .message-content').text_content() == draft)
                expect(page.locator('#conversation-list button')).to_have_count(1)
                expect(page.locator('#conversation-list button')).to_be_in_viewport()
                check('Saved conversation remains in view with twenty-one projects')
                expect(page.locator('#notification')).to_be_hidden(timeout=10000)
                page.screenshot(path=str(art / 'chat-layout-desktop.png'))
                page.locator('#new-chat').click()
                expect(page.locator('#welcome')).to_be_visible()
                page.screenshot(path=str(art / 'chat-layout-welcome.png'))
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
