"""Real browser + HTTP + persistence; inference fixture is not model qualification."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server
from tests.test_leads import proposal
from playwright.sync_api import sync_playwright, expect


class FixtureModel:
    def answer(self, *args, **kwargs):
        return {'content': json.dumps(proposal()), 'possibly_truncated': False}


class FixtureVault:
    def seal(self, value):return 'encrypted-fixture'
    def open(self, value):raise AssertionError('Offline collector must not open credentials')


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--browser-channel');parser.add_argument('--output', type=Path, default=ROOT/'reports')
    args = parser.parse_args();args.output.mkdir(parents=True, exist_ok=True)
    report = {'success':False, 'model_inference':False, 'test_doubles':['FoundationService.answer'], 'flows':[], 'errors':[]}
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary);settings = Settings.load(root/'home');app = Application(settings)
        (root/'project').mkdir();first = app.store.add_project('ShopAir · laboratório', str(root/'project'))
        (root/'other').mkdir();other = app.store.add_project('Outro projeto', str(root/'other'))
        app.leads.foundation = FixtureModel();app.lead_connections.vault = FixtureVault();app.start()
        report['test_doubles'].append('WindowsVault.seal for browser fixture; real DPAPI tested separately on Windows')
        server = create_server(app, ROOT/'ui', port=0);thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, **({'channel':args.browser_channel} if args.browser_channel else {}))
                page = browser.new_page(viewport={'width':1440,'height':1000})
                page.on('pageerror', lambda error:report['errors'].append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/leads')
                page.locator('#token').fill(settings.token);page.locator('#login-form button').click()
                page.locator('#project').select_option(first['id'])
                page.locator('[data-tab=context]').click();page.locator('#shopair-example').click()
                page.locator('#context-form button').click();expect(page.locator('#message')).to_contain_text('Contexto salvo')
                report['flows'].append('context saved with source and verified date')
                def intake(company, email, message, source='manual', permission='reply_requested', opt_out=False):
                    page.locator('[data-tab=intake]').click();page.locator('#company').fill(company)
                    page.locator('#email').fill(email);page.locator('#lead-message').fill(message)
                    page.locator('#source').select_option(source);page.locator('#permission').select_option(permission)
                    if source=='research':page.locator('#source-url').fill('https://example.com/')
                    page.locator('#opt-out').set_checked(opt_out);page.locator('#intake-form button').click()
                    expect(page.locator('#inbox')).to_be_visible();expect(page.locator('#detail h2')).to_have_text(company)
                intake('Loja <script> & laboratório', 'shopair-fixture@example.test', 'Quero uma demonstração de loja online.')
                page.locator('#qualify').click();expect(page.locator('#review')).to_be_visible(timeout=15000)
                expect(page.locator('#message')).to_contain_text('Análise pronta', timeout=15000)
                expect(page.locator('#detail')).to_contain_text('Loja online com catálogo, checkout, pagamentos e entregas.')
                page.locator('#review').click();expect(page.locator('#detail .pill')).to_have_text('Qualificado')
                report['flows'].append('real job queue, analysis evidence and human approval; HTML input rendered as text')
                page.locator('#move-stage').select_option('demonstration');page.locator('#move-note').fill('Demonstração combinada em simulação.')
                page.locator('#move-form button').click();expect(page.locator('#detail .pill')).to_have_text('Demonstração')
                report['flows'].append('pipeline transition and recorded metrics')
                intake('Pesquisa sintética', 'research-fixture@example.test', 'Empresa vende presentes no balcão.', 'research', 'unknown')
                page.locator('#qualify').click();expect(page.locator('#review')).to_be_visible(timeout=15000)
                expect(page.locator('#detail')).to_contain_text('Sem rascunho')
                page.locator('#review').click();expect(page.locator('#detail .pill')).to_have_text('Em pesquisa')
                report['flows'].append('public research remains separate; no unsolicited draft')
                intake('Recusa sintética', 'blocked-fixture@example.test', 'Não quero receber contato.', opt_out=True)
                expect(page.locator('#detail .pill')).to_have_text('Não contatar');expect(page.locator('#qualify')).to_be_disabled()
                report['flows'].append('explicit opt-out blocks inference')
                intake('Contexto sintético', 'stale-fixture@example.test', 'Quero conhecer a loja virtual.')
                page.locator('#qualify').click();expect(page.locator('#review')).to_be_visible(timeout=15000)
                page.locator('[data-tab=context]').click();page.locator('#intro').fill('Olá! Nova apresentação conferida.')
                page.locator('#context-form button').click();expect(page.locator('#message')).to_contain_text('Contexto salvo')
                page.locator('[data-tab=inbox]').click();expect(page.locator('#detail')).to_contain_text('desatualizada')
                expect(page.locator('#review')).to_be_disabled()
                report['flows'].append('context change invalidates old analysis and approval')
                page.locator('[data-tab=integration]').click();page.locator('#relay-url').fill('https://example.com/')
                page.locator('#relay-queue').fill('a'*32);page.locator('#relay-key').fill('r'*40)
                page.locator('#relay-form button').first.click();expect(page.locator('#message')).to_contain_text('Conexão salva')
                expect(page.locator('#relay-key')).to_have_value('')
                page.locator('#relay-disable').click();expect(page.locator('#relay-status')).to_contain_text('Coleta pausada')
                report['flows'].append('relay setup clears secret field; pause preserves data; offline prevents network')
                page.locator('[data-tab=inbox]').click()
                page.screenshot(path=str(args.output/'leads-desktop.png'), full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.screenshot(path=str(args.output/'leads-mobile.png'), full_page=True)
                page.locator('[data-appearance]').select_option('dark') if page.locator('[data-appearance]').is_visible() else None
                report['flows'].append('mobile layout has no horizontal overflow')
                page.locator('#project').select_option(other['id']);expect(page.locator('#detail')).to_contain_text('Selecione')
                page.locator('[data-tab=context]').click();expect(page.locator('#brand')).to_have_value('')
                report['flows'].append('project change clears contacts and company context')
                browser.close();report['success'] = not report['errors']
        finally:
            server.shutdown();server.server_close();thread.join();app.close()
    (args.output/'leads-ui-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['success'] else 1


if __name__ == '__main__':raise SystemExit(main())
