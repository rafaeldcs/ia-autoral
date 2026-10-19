#!/usr/bin/env python3
"""Exercise the visual studio with real ShopAir files and browser encoders.

No model doubles, neural generation, publication or quality score is implied.
Keep the output directory private until the owner reviews the evidence.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.foundation.models import digest
from localauthor.server import create_server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser-channel', choices=['chrome', 'msedge'])
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a new output directory to preserve previous evidence.')
    args.output.mkdir(parents=True)
    from playwright.sync_api import sync_playwright, expect
    report = {'schema': 1, 'model_inference': False, 'training': False,
              'cases': [], 'browser_errors': [], 'exports': []}

    def record(name, passed, detail=''):
        report['cases'].append({'name': name, 'passed': bool(passed), 'detail': detail})

    assets = [ROOT / 'marketing/shopair-orbit/assets' / f'shopair-0{i}.png' for i in (1, 2)]
    report['inputs'] = [{'file': path.name, 'sha256': digest(path)} for path in assets]
    try:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); project = base / 'project'; project.mkdir()
            settings = Settings.load(base / 'home'); app = Application(settings)
            app.store.add_project('ShopAir — QA visual', str(project))
            server = create_server(app, ROOT / 'ui', port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True, channel=args.browser_channel)
                    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
                    page.on('pageerror', lambda error: report['browser_errors'].append(str(error)))
                    page.goto(f'http://127.0.0.1:{server.server_port}/foundation')
                    page.locator('#token').fill(settings.token); page.locator('#connect button').click()
                    expect(page.locator('#workspace')).to_be_visible()
                    record('empty export disabled', page.locator('#video-export').is_disabled())
                    page.locator('#video-images').set_input_files({'name': 'invalid.txt', 'mimeType': 'text/plain', 'buffer': b'not an image'})
                    expect(page.locator('#video-status')).to_contain_text('Selecione até 12')
                    record('unsupported type rejected', page.locator('.video-scene').count() == 0)
                    page.locator('#video-images').set_input_files([str(path) for path in assets])
                    expect(page.locator('.video-scene')).to_have_count(2)
                    # A visible <img> alone does not prove its pixels loaded (CSP).
                    page.wait_for_timeout(300)
                    record('thumbnails decode under product CSP', page.locator('.video-scene img').evaluate_all('(images) => images.every(i => i.complete && i.naturalWidth > 0)'))
                    page.locator('.video-scene').first.locator('input').fill('Sua loja, sua marca')
                    page.locator('.video-scene').first.get_by_role('button', name='↓ Descer').click()
                    record('reorder preserves caption', page.locator('.video-scene').nth(1).locator('input').input_value() == 'Sua loja, sua marca')
                    page.locator('#video-title').fill('ShopAir')
                    page.locator('#video-duration').select_option('2')
                    page.locator('#video-images').set_input_files({'name': 'corrupt.png', 'mimeType': 'image/png', 'buffer': b'not PNG bytes'})
                    expect(page.locator('#video-export')).to_be_enabled()
                    record('corrupt import preserves scenes', page.locator('.video-scene').count() == 2)
                    page.locator('#video-images').set_input_files([
                        {'name': f'case-{i}.png', 'mimeType': 'image/png', 'buffer': assets[0].read_bytes()} for i in range(13)])
                    expect(page.locator('#video-status')).to_contain_text('Selecione até 12')
                    record('excessive import rejected without replacing scenes', page.locator('.video-scene').count() == 2)
                    page.evaluate("() => { window.qaStart = MediaRecorder.prototype.start; MediaRecorder.prototype.start = function() { throw new Error('QA encoder start failure'); }; }")
                    page.locator('#video-export').click()
                    expect(page.locator('#video-status')).to_contain_text('Exportação interrompida')
                    record('encoder startup failure restores editable controls', page.locator('#video-format').is_enabled() and page.locator('#video-export').is_enabled())
                    page.evaluate('() => { MediaRecorder.prototype.start = window.qaStart; delete window.qaStart; }')
                    for format_name, size in [('portrait', (720, 1280)), ('landscape', (1280, 720)), ('square', (720, 720))]:
                        page.locator('#video-format').select_option(format_name)
                        started = time.monotonic()
                        with page.expect_download(timeout=20000) as download_info:
                            page.locator('#video-export').click()
                            locked = all(page.locator(selector).evaluate_all('(nodes) => nodes.length > 0 && nodes.every(n => n.disabled)') for selector in
                                         ['#video-images', '#video-format', '#video-duration', '#video-title', '.video-scene input'])
                            record(f'{format_name}: composition locked during export', locked)
                        target = args.output / f'shopair-{format_name}.webm'
                        download_info.value.save_as(target)
                        expect(page.locator('#video-status')).to_contain_text('Vídeo WebM exportado')
                        data = target.read_bytes()
                        decoder = browser.new_page()
                        decoder.set_content('<input type="file"><video muted controls></video>')
                        decoder.locator('input').set_input_files(str(target))
                        decoder.evaluate("() => { const file=document.querySelector('input').files[0], v=document.querySelector('video'); v.src=URL.createObjectURL(file); }")
                        decoder.wait_for_function("() => document.querySelector('video').readyState >= 2", timeout=10000)
                        actual = decoder.locator('video').evaluate('(v) => [v.videoWidth, v.videoHeight]')
                        record(f'{format_name}: WebM decodes at requested dimensions', data.startswith(bytes.fromhex('1a45dfa3')) and actual == list(size), str(actual))
                        decoder.locator('video').screenshot(path=str(args.output / f'shopair-{format_name}-frame.png'))
                        decoder.close()
                        report['exports'].append({'file': target.name, 'sha256': digest(target), 'bytes': len(data),
                                                  'seconds_including_download': time.monotonic() - started, 'dimensions': actual})
                    page.set_viewport_size({'width': 390, 'height': 844})
                    record('mobile has no horizontal overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    page.locator('#video-studio').screenshot(path=str(args.output / 'shopair-studio-mobile.png'))
                    page.set_viewport_size({'width': 1440, 'height': 1000})
                    page.locator('#video-studio').screenshot(path=str(args.output / 'shopair-studio-desktop.png'))
                    page.locator('.video-scene').first.get_by_role('button', name='Remover').click()
                    expect(page.locator('.video-scene')).to_have_count(1)
                    record('remove preserves remaining scene', page.locator('.video-scene').first.locator('input').input_value() == 'Sua loja, sua marca')
                    browser.close()
            finally:
                server.shutdown(); server.server_close(); thread.join(); app.close()
    except Exception as exc:
        record('execution finished', False, f'{type(exc).__name__}: {exc}')
    report['success'] = bool(report['cases']) and all(row['passed'] for row in report['cases']) and not report['browser_errors']
    (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
