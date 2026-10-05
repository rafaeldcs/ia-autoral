#!/usr/bin/env python3
"""Browser integration with explicit doubles, NEVER a real-model benchmark."""
import json
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


def main():
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
            app.store.ingest(item["id"], "note:stock", "Estoque", "O estoque não pode ser negativo.", kind="note")
            register_fixture(settings.home, base / "text-weights")
            register_fixture(settings.home, base / "image-weights", "image")
            app.chat.foundation = FoundationService(settings.home, text_factory=DummyText, image_factory=DummyImage)
            app.start()
            server = create_server(app, ROOT / "ui", port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True, executable_path=shutil.which("chromium") or None)
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
                    assert page.locator("#token").input_value() == ""
                    assert page.evaluate("localStorage.length + sessionStorage.length") == 0
                    report["flows"].append("authenticated login, no browser credential persistence")
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
                    page.locator("#prompt").fill("Um quadrado cinza")
                    page.locator("#send").click()
                    expect(page.locator("#messages article")).to_have_count(6, timeout=15000)
                    page.get_by_role("button", name="Mostrar imagem").click()
                    expect(page.locator("#messages img")).to_be_visible()
                    page.wait_for_function("document.querySelector('#messages img')?.naturalWidth === 512")
                    report["flows"].append("visual job and authenticated PNG retrieval, fixture pixels only")
                    page.screenshot(path=str(reports / "foundation-desktop.png"), full_page=True)
                    page.locator("#mode").select_option("text")
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
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    page.screenshot(path=str(reports / "foundation-mobile.png"), full_page=True)
                    page.locator("#logout").click()
                    expect(page.locator("#login")).to_be_visible()
                    assert page.locator("#messages").inner_text() == ""
                    report["flows"].append("mobile layout and logout cleanup")
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
    raise SystemExit(main())
