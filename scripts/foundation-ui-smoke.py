#!/usr/bin/env python3
"""Browser integration with explicit doubles, NEVER a real-model benchmark."""
import json
import argparse
from pathlib import Path
import re
import shutil
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.foundation.service import FoundationService
from localauthor.server import create_server
from tests.test_foundation import DummyText, DummyImage, register_fixture


def check_business_tools(page, report, project, other, reports):
    """Real browser plus actual arithmetic API; model conversation remains a double."""
    from playwright.sync_api import expect
    page.locator('#business-tools summary').click()
    def fill(values):
        for field, value in values.items():
            page.locator(f'#business-{field}').fill(str(value))
    fill({'impressions': 12500, 'clicks': 250, 'leads': 50,
          'new_clients': 5, 'spend_cents': '1250,00'})
    page.locator('#business-form button').click()
    result = page.locator('#business-result')
    expect(result).to_contain_text('Custo por lead (R$): 25.00')
    expect(result).to_contain_text('Custo de mídia por cliente (R$): 250.00')
    page.locator('#business-use').click()
    assert '"spend_cents":125000' in page.locator('#prompt').input_value()
    assert page.locator('#messages article').count() == 0
    fill({'spend_cents': '0,29'})
    expect(page.locator('#business-use')).to_be_hidden()
    page.locator('#business-form button').click()
    expect(result).to_contain_text('Custo por lead (R$): 0.01')
    page.locator('#business-use').click()
    assert '"spend_cents":29' in page.locator('#prompt').input_value()
    fill({'spend_cents': '1,234'})
    page.locator('#business-form button').click()
    expect(result).to_contain_text('inválido')
    expect(page.locator('#business-use')).to_be_hidden()
    fill({'spend_cents': '1', 'leads': 251})
    page.locator('#business-form button').click()
    expect(result).to_contain_text('Ordem')
    report['flows'].append('business campaign: real CPL/media-per-client arithmetic, cent precision, invalid format/order, no automatic generation')
    page.locator('#business-kind').select_option('funnel')
    fill({'registrations': 200, 'started': 50, 'completed': 20})
    page.locator('#business-form button').click()
    expect(result).to_contain_text('Conclusão/cadastros (%): 10.00')
    expect(result).to_contain_text('Total sem concluir: 180')
    fill({'registrations': 0, 'started': 0, 'completed': 0})
    page.locator('#business-form button').click()
    expect(result).to_contain_text('Conclusão/cadastros (%): indisponível')
    report['flows'].append('business funnel: denominators, abandoned stages, zero is unknown')
    page.locator('#business-kind').select_option('cash')
    fill({'opening_cents': '8800', 'incoming_cents': '3200', 'outgoing_cents': '4700'})
    page.locator('#business-form button').click()
    expect(result).to_contain_text('Saldo de caixa (R$): 7300.00')
    expect(result).to_contain_text('não lucro')
    page.screenshot(path=str(reports / 'business-metrics-desktop.png'), full_page=True)
    fill({'opening_cents': '0', 'incoming_cents': '0,01', 'outgoing_cents': '1,01'})
    page.locator('#business-form button').click()
    expect(result).to_contain_text('Saldo de caixa (R$): -1.00')
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(reports / 'business-metrics-mobile.png'), full_page=True)
    page.set_viewport_size({'width': 1440, 'height': 1000})
    report['flows'].append('business cash: negative balance, cash not profit, desktop/mobile layout')
    # A stale response must not restore numbers after a field edit or project switch.
    scenario = {'action': None}
    handled_actions = []
    def delayed(route):
        # Mutate after interception, when submission has actually started. A timer
        # set before Playwright scrolls/clicks can fire before the request, making
        # the response current rather than stale and the test nondeterministic.
        if scenario['action'] == 'edit':
            page.evaluate("""() => {
              document.getElementById('business-incoming_cents').value = '2';
              document.getElementById('business-incoming_cents').dispatchEvent(new Event('input', {bubbles:true}));
            }""")
        elif scenario['action'] == 'project':
            page.evaluate("""other => {
              document.getElementById('project').value = other;
              document.getElementById('project').dispatchEvent(new Event('change', {bubbles:true}));
            }""", other)
        if scenario['action']:
            handled_actions.append(scenario['action'])
        route.fulfill(status=200, content_type='application/json', body=json.dumps({
            'kind': 'cash', 'metrics': {'balance_brl': '99999.00'},
            'notice': '<img src=x onerror=window.PWNED=1>'}))
    page.route('**/api/foundation/business-metrics', delayed)
    scenario['action'] = 'edit'
    page.locator('#business-form button').click()
    expect(page.locator('#business-form button')).to_be_enabled()
    expect(result).to_be_empty()
    expect(page.locator('#business-use')).to_be_hidden()
    scenario['action'] = 'project'
    page.locator('#business-form button').click()
    expect(page.locator('#project')).to_have_value(other)
    expect(page.locator('#business-form button')).to_be_enabled()
    expect(result).to_be_empty()
    expect(page.locator('#business-use')).to_be_hidden()
    assert handled_actions == ['edit', 'project'], 'Both mutations happened during an intercepted request'
    scenario['action'] = None
    page.locator('#project').select_option(project)
    page.locator('#business-kind').select_option('cash')
    fill({'opening_cents': '0', 'incoming_cents': '1', 'outgoing_cents': '0'})
    page.locator('#business-form button').click()
    expect(result).to_contain_text('<img src=x')
    assert page.evaluate('window.PWNED') is None
    assert page.locator('#business-result img').count() == 0
    page.unroute('**/api/foundation/business-metrics', delayed)
    page.locator('#project').select_option(other)
    expect(result).to_be_empty()
    page.locator('#project').select_option(project)
    assert page.locator('#business-form input').first.input_value() == ''
    report['flows'].append('business result: stale edit/project response discarded, project cleanup, inert malicious text')


def main(browser_channel=None):
    from playwright.sync_api import sync_playwright, expect
    report = {"success": False, "model_inference": "test doubles only", "flows": [], "errors": []}
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); project = base / "project"; project.mkdir()
            original = "public class Stock { public int Count = 1; }\n"
            (project / "Stock.cs").write_text(original, encoding="utf-8")
            settings = Settings.load(base / "data")
            app = Application(settings)
            item = app.store.add_project("Laboratório visual", str(project))
            second_root = base / "marketing"; second_root.mkdir()
            second = app.store.add_project("Marketing de laboratório", str(second_root))
            app.store.ingest(item["id"], "note:stock", "Estoque", "O estoque não pode ser negativo.", kind="note")
            register_fixture(settings.home, base / "text-weights")
            register_fixture(settings.home, base / "image-weights", "image")
            app.chat.foundation = FoundationService(settings.home, text_factory=DummyText, image_factory=DummyImage)
            app.start()
            server = create_server(app, ROOT / "ui", port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True, channel=browser_channel,
                        executable_path=None if browser_channel else shutil.which("chromium") or None)
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    page.on("pageerror", lambda error: report["errors"].append(str(error)))
                    page.goto(f"http://127.0.0.1:{server.server_port}/foundation")
                    page.locator("#token").fill("invalid-fixture-token")
                    page.locator("#connect button").click()
                    expect(page.locator("#status")).to_contain_text("Token local obrigatório")
                    assert page.locator("#workspace").is_hidden()
                    page.locator("#token").fill(settings.token)
                    page.locator("#connect button").click()
                    expect(page.locator("#workspace")).to_be_visible()
                    page.locator("#project").select_option(item["id"])
                    expect(page.locator("#conversation")).to_have_value("")
                    assert page.locator("#token").input_value() == ""
                    assert page.evaluate("localStorage.length + sessionStorage.length") == 0
                    report["flows"].append("authenticated login, no browser credential persistence")
                    page.locator("#marketing-tools summary").click()
                    for index, impressions, clicks in ((0,3000,60),(1,1000,30)):
                        box=page.locator("[data-campaign]").nth(index)
                        box.locator('[data-field="impressions"]').fill(str(impressions))
                        box.locator('[data-field="clicks"]').fill(str(clicks))
                    page.locator("#marketing-form button").click()
                    expect(page.locator("#marketing-result")).to_contain_text("Maior CTR: B")
                    page.locator("#marketing-use").click()
                    assert '"best_ctr":["B"]' in page.locator("#prompt").input_value()
                    assert page.locator("#messages article").count()==0
                    page.locator('[data-campaign] [data-field="conversions"]').nth(1).fill("31")
                    expect(page.locator("#marketing-use")).not_to_be_visible()
                    page.locator("#marketing-form button").click()
                    expect(page.locator("#marketing-result")).to_contain_text("conversões ≤ cliques")
                    page.locator('[data-campaign] [data-field="conversions"]').nth(1).fill("0")
                    page.locator("#marketing-form button").click()
                    expect(page.locator("#marketing-result")).to_contain_text("Maior CTR: B")
                    report["flows"].append("deterministic campaign rates, invalid counts rejected, draft only, stale results discarded")
                    check_business_tools(page, report, item['id'], second['id'], reports)
                    page.locator("#prompt").fill("Explique estoque")
                    page.locator("#send").click()
                    expect(page.locator("#messages article")).to_have_count(2, timeout=15000)
                    expect(page.locator("#status")).to_contain_text("Concluído")
                    assert page.evaluate("window.PWNED") is None
                    report["flows"].append("text job, automatic conversation creation, inert output rendering")
                    assert page.locator('#mode option[value="code"]').count() == 0
                    page.locator("#prompt").fill('const estoque = 0;\n// Explique uma validação de estoque')
                    page.locator("#send").click()
                    expect(page.locator("#messages article")).to_have_count(4, timeout=15000)
                    saved_code = app.chat.get(item["id"], page.locator("#conversation").input_value())
                    assert saved_code['messages'][-2]['metadata']['format'] == 'code'
                    report["flows"].append("automatic code detection and conversation history")
                    page.locator("#mode").select_option("image")
                    expect(page.locator("#image-options")).to_be_visible()
                    page.locator("#image-seed").fill("17")
                    page.locator("#image-steps").select_option("5")
                    page.locator("#prompt").fill("Um quadrado cinza")
                    page.locator("#send").click()
                    expect(page.locator("#messages article")).to_have_count(6, timeout=15000)
                    page.get_by_role("button", name="Mostrar imagem").click()
                    expect(page.locator("#messages img")).to_be_visible()
                    expect(page.locator("#messages img")).to_have_js_property("naturalWidth", 512)
                    saved = app.chat.get(item["id"], page.locator("#conversation").input_value())
                    meta = saved["messages"][-1]["metadata"]
                    assert (meta["seed"], meta["steps"], meta["width"]) == (17, 5, 512)
                    report["flows"].append("visual job and authenticated PNG retrieval, fixture pixels only")
                    report["flows"].append("image controls reach the job and recorded artifact metadata")
                    page.screenshot(path=str(reports / "foundation-desktop.png"), full_page=True)
                    page.locator("#mode").select_option("text")
                    expect(page.locator("#image-options")).not_to_be_visible()
                    page.locator("#prompt").fill("aguardar cancelamento")
                    page.locator("#send").click()
                    expect(page.locator("#status")).to_contain_text("Gerando", timeout=10000)
                    page.locator("#cancel").click()
                    expect(page.locator("#status")).to_contain_text(re.compile("cancelad", re.I), timeout=15000)
                    expect(page.locator("#send")).to_be_enabled()
                    expect(page.locator("#messages article")).to_have_count(6)
                    assert page.locator("#prompt").input_value() == "aguardar cancelamento"
                    report["flows"].append("cooperative job cancellation without saving a response")
                    page.set_viewport_size({"width": 390, "height": 844})
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Foundation mobile horizontal overflow"
                    page.screenshot(path=str(reports / "foundation-mobile.png"), full_page=True)
                    page.locator("#logout").click()
                    expect(page.locator("#login")).to_be_visible()
                    assert page.locator("#messages").inner_text() == ""
                    assert page.locator('#business-result').inner_text() == ''
                    assert page.locator('#business-form input').first.input_value() == ''
                    report["flows"].append("mobile layout and logout cleanup")
                    page.goto(f"http://127.0.0.1:{server.server_port}/")
                    page.locator("#local-token").fill(settings.token)
                    page.locator("#connect-form button").click()
                    expect(page.locator("#studio")).to_be_visible()
                    page.locator("#open-menu").click()
                    page.locator("#project-list button").filter(has_text="Marketing de laboratório").click()
                    page.locator("#show-rules").click()
                    expect(page.locator("#rules-dialog")).to_be_visible()
                    page.locator("#work-profile").select_option("marketing")
                    page.locator("#done").fill("Conferir fontes; conteúdo é uma proposta até revisão.")
                    page.locator("#rules-form button.primary").click()
                    expect(page.locator("#rules-dialog")).not_to_be_visible()
                    assert app.chat.preferences(second["id"])["work_profile"] == "marketing"
                    page.locator("#show-rules").click()
                    expect(page.locator("#work-profile")).to_have_value("marketing")
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Chat project guidance mobile horizontal overflow"
                    page.screenshot(path=str(reports / "work-profile-mobile.png"), full_page=True)
                    page.locator('[data-close="rules-dialog"]').click()
                    page.locator("#open-menu").click()
                    page.locator("#project-list button").filter(has_text="Laboratório visual").click()
                    page.locator("#show-rules").click()
                    expect(page.locator("#work-profile")).to_have_value("general")
                    page.locator("#work-profile").select_option("developer")
                    page.locator("#rules-form button.primary").click()
                    expect(page.locator("#rules-dialog")).not_to_be_visible()
                    assert app.chat.preferences(item["id"])["work_profile"] == "developer"
                    assert app.chat.preferences(second["id"])["work_profile"] == "marketing"
                    page.reload()
                    page.locator("#local-token").fill(settings.token)
                    page.locator("#connect-form button").click()
                    expect(page.locator("#studio")).to_be_visible()
                    assert app.chat.preferences(second["id"])["work_profile"] == "marketing"
                    report["flows"].append("project work profiles persist independently; mobile guidance dialog")
                    assert (project / "Stock.cs").read_text(encoding="utf-8") == original
                    report["flows"].append("original project file unchanged")
                    report["success"] = not report["errors"]
                    browser.close()
            finally:
                server.shutdown(); server.server_close(); thread.join(); app.close()
    except Exception as exc:
        report["errors"].append(str(exc))
        report["success"] = False
    (reports / "foundation-ui-smoke.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument('--browser-channel',choices=['chrome','msedge'])
    args=parser.parse_args()
    raise SystemExit(main(args.browser_channel))
