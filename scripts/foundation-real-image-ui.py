#!/usr/bin/env python3
"""Display an already-generated REAL artifact through authenticated product UI.

Does not regenerate pixels, does not use image/text doubles, not a quality rubric.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.foundation.experience import ExperienceStore
from localauthor.foundation.isolation import require_isolated_process
from localauthor.foundation.models import digest, read_object, write_new
from localauthor.server import create_server
from localauthor.util import utcnow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    isolation = require_isolated_process()
    if args.report.exists(): parser.error("Use relatório novo.")
    sample = read_object(args.probe / "simple.json")["result"]
    if sample["model"]["model_id"] != "stable-diffusion-v1-5/stable-diffusion-v1-5":
        raise ValueError("Expected recorded real model, no double")
    home = args.probe / "home"
    row = ExperienceStore(home).get("visual-probe", sample["artifact_id"])
    original = home / "foundation/artifacts/visual-probe" / (sample["artifact_id"] + ".png")
    if digest(original) != sample["artifact_sha256"]: raise ValueError("Actual artifact hash mismatch")
    from playwright.sync_api import sync_playwright, expect
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"; project.mkdir()
        app = Application(Settings.load(home))
        with app.store.connect() as db:
            db.execute("INSERT OR IGNORE INTO projects VALUES(?,?,?,?)",
                       ("visual-probe", "Imagem real — laboratório", str(project), utcnow()))
        conversation = app.chat.create("visual-probe", "Imagem gerada pelo modelo local")
        with app.store.connect() as db:
            for role, content, meta in (("user", row["prompt"], {}), ("assistant", sample["content"], sample)):
                db.execute("INSERT INTO messages(conversation_id,role,content,metadata,created_at) VALUES(?,?,?,?,?)",
                           (conversation["id"], role, content, json.dumps(meta, ensure_ascii=False), utcnow()))
        server = create_server(app, ROOT / "ui", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        errors = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, executable_path=shutil.which("chromium") or None)
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/foundation")
                page.locator("#token").fill(app.settings.token)
                page.locator("#connect button").click()
                expect(page.get_by_role("button", name="Mostrar imagem")).to_be_visible()
                page.get_by_role("button", name="Mostrar imagem").click()
                expect(page.locator("#messages img")).to_have_js_property("naturalWidth", sample["width"])
                expect(page.locator("#messages img")).to_be_visible()
                if page.locator("#token").input_value(): raise AssertionError("Token remained visible")
                screenshot = args.report.with_suffix(".png")
                page.screenshot(path=str(screenshot), full_page=True)
                browser.close()
            if errors: raise AssertionError(errors)
            write_new(args.report, {"status": "passed", "original_artifact_sha256": digest(original),
                "real_model": sample["model"], "regenerated": False, "test_doubles": False,
                "isolation": isolation, "browser_errors": errors, "screenshot": screenshot.name,
                "scope": "authenticated retrieval/display of an actual generated PNG; not a quality rating"})
        finally:
            server.shutdown(); server.server_close(); thread.join(); app.close()


if __name__ == "__main__": main()
