"""Opt-in browser cycle with real local STT, LLM and Windows/browser TTS; synthetic microphone only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server
from localauthor.voice import validate_audio
from ui_profile_fixture import enter_profile, launch_browser
from playwright.sync_api import sync_playwright, expect
import base64


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-real', action='store_true', required=True)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--turns', type=int, choices=(1, 2, 3), default=2)
    args = parser.parse_args()
    audio = args.audio.resolve()
    validate_audio(base64.b64encode(audio.read_bytes()).decode('ascii'))
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'success': False, 'audio_sha256': hashlib.sha256(audio.read_bytes()).hexdigest(),
              'synthetic_microphone': True, 'stt_double': False, 'llm_double': False, 'tts_double': False,
              'requested_turns': args.turns,
              'limitations': ['Physical microphone and another computer were not tested.',
                             'Reader completion does not prove perceived sound quality.']}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            # The browser loops its synthetic microphone file. A silence tail
            # lets the real VAD observe a pause instead of hitting the 30s cap.
            capture_audio = base / 'microphone.wav'
            with wave.open(str(audio), 'rb') as reader:
                pcm = reader.readframes(reader.getnframes())
            with wave.open(str(capture_audio), 'wb') as writer:
                writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(16000)
                writer.writeframes(pcm + b'\0' * 64000)
            report['capture_silence_seconds'] = 2
            report['capture_sha256'] = hashlib.sha256(capture_audio.read_bytes()).hexdigest()
            settings = Settings.load(base / 'data')
            for relative in ['foundation/text-model.json', 'voice/model.json']:
                target = settings.home / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(args.home / relative, target)
            project_root = base / 'project'; project_root.mkdir()
            app = Application(settings)
            app.store.add_project('Laboratório de conversa real', str(project_root))
            server = create_server(app, ROOT / 'ui', port=0)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            app.start(); worker.start()
            try:
                with sync_playwright() as pw:
                    browser = launch_browser(pw.chromium, headless=True,
                        args=['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
                              '--use-file-for-fake-audio-capture=' + str(capture_audio)])
                    page = browser.new_page(viewport={'width': 1440, 'height': 900})
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    # Observe the actual platform APIs, without substituting a decoder,
                    # voice, model, stream or a completion callback.
                    page.add_init_script("""(() => {
                        window.realVoice={captures:0,captureTimes:[],spoken:[],events:[]};
                        const capture=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                        navigator.mediaDevices.getUserMedia=async options=>{
                            const stream=await capture(options);realVoice.captures++;realVoice.captureTimes.push(performance.now());return stream;
                        };
                        const speak=speechSynthesis.speak.bind(speechSynthesis);
                        speechSynthesis.speak=u=>{
                            realVoice.spoken.push({text:u.text,voice:u.voice?.name,local:u.voice?.localService,at_ms:performance.now()});
                            u.addEventListener('end',()=>realVoice.events.push('end'));
                            u.addEventListener('error',e=>realVoice.events.push(e.error));
                            return speak(u);
                        };
                    })()""")
                    page.goto(f'http://127.0.0.1:{server.server_port}')
                    page.locator('#local-token').fill(settings.token)
                    page.locator('#connect-form button').click(); enter_profile(page)
                    expect(page.locator('#studio')).to_be_visible()
                    started = time.monotonic()
                    page.locator('#voice-start').click(); page.locator('#voice-confirm').click()
                    try:
                        page.wait_for_function("turns => realVoice.events.filter(e=>e==='end').length>=turns && realVoice.captures>turns", arg=args.turns, timeout=180000)
                        report['cycle_seconds'] = round(time.monotonic() - started, 3)
                        report['events'] = page.evaluate('realVoice')
                        report['messages'] = page.locator('#messages').inner_text()
                        conversation = app.chat.conversations(app.store.projects()[0]['id'])[0]
                        turns = app.chat.get(conversation['project_id'], conversation['id'])['messages']
                        report['history_messages_used'] = [m['metadata'].get('history_messages_used') for m in turns if m['role'] == 'assistant']
                        assert all(s['local'] is True for s in report['events']['spoken'])
                        assert not errors, errors
                        report['success'] = True
                    finally:
                        report['observed'] = page.evaluate('realVoice')
                        report['status'] = page.locator('#voice-status').inner_text()
                        report['setup'] = page.locator('#voice-setup').inner_text()
                        report['notice'] = page.locator('#notification').inner_text()
                        report['errors'] = errors
                        page.screenshot(path=str(args.output / 'voice-real.png'))
                        page.locator('#voice-stop').click()
                        browser.close()
            finally:
                server.shutdown(); server.server_close(); worker.join(); app.close()
    finally:
        (args.output / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'success': report['success'], 'cycle_seconds': report.get('cycle_seconds')}))


if __name__ == '__main__':
    main()
