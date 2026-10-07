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

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.foundation.service import FoundationService
from localauthor.server import create_server
from tests.test_foundation import DummyText, DummyImage, register_fixture


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
                    page.locator("#prompt").fill("Explique estoque")
                    page.locator("#send").click()
                    expect(page.locator("#messages article")).to_have_count(2, timeout=15000)
                    expect(page.locator("#status")).to_contain_text("Concluído")
                    assert page.evaluate("window.PWNED") is None
                    report["flows"].append("text job, automatic conversation creation, inert output rendering")
                    page.locator("#mode").select_option("code")
                    page.locator("#prompt").fill("Escreva uma validação de estoque")
                    page.locator("#send").click()
                    expect(page.locator("#messages article")).to_have_count(4, timeout=15000)
                    report["flows"].append("code mode and conversation history")
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
