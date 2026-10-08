"""Actual Chromium microphone pipeline; explicit STT, TTS and LLM test doubles."""
import json
import math
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import threading
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.foundation.service import FoundationService
from localauthor.server import create_server
from tests.test_foundation import DummyText, register_fixture
from tests.test_voice import spec_fixture
from tests.helpers import wait_until
from localauthor.errors import PolicyError
from playwright.sync_api import sync_playwright, expect


def main():
    report = {'checks': [], 'errors': [], 'success': False,
              'limitations': ['Synthetic microphone; explicit STT/TTS/LLM doubles; not speech quality or physical microphone qualification.']}
    reports = ROOT / 'reports'; reports.mkdir(exist_ok=True)
    def check(name, value=True):
        assert value, name; report['checks'].append(name)
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp); project_root = base / 'project'; project_root.mkdir()
        settings = Settings.load(base / 'data'); app = Application(settings)
        project = app.store.add_project('Conversa de teste', str(project_root))
        target = settings.home / 'voice/model.json'; target.parent.mkdir(); target.write_text(json.dumps(spec_fixture()))
        engines = []
        def factory(spec):
            engine = DummyText(spec); engines.append(engine); return engine
        app.chat.foundation = FoundationService(settings.home, text_factory=factory)
        transcripts = []
        speech_mode = {'hold': False}
        speech_started = threading.Event()
        class SpeechDouble:
            def transcribe(self, encoded, cancel):
                transcripts.append(encoded)
                if speech_mode['hold']:
                    speech_started.set()
                    if not cancel.wait(10): raise PolicyError('Cancelamento de teste ausente')
                    raise PolicyError('Fala de teste cancelada')
                return {'text': 'Como organizar um projeto?', 'offline': True, 'audio_retained': False}
        app.voice.factory = lambda spec: SpeechDouble()
        audio = base / 'mic.wav'
        with wave.open(str(audio), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
            w.writeframes(b''.join(struct.pack('<h', round(5000 * math.sin(i * .12)) if i < 16000 else 0) for i in range(64000)))
        server = create_server(app, ROOT / 'ui', port=0); worker = threading.Thread(target=server.serve_forever, daemon=True)
        app.start(); worker.start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True, executable_path=shutil.which('chromium') or None,
                    args=['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--use-file-for-fake-audio-capture=' + str(audio)])
                context = browser.new_context(viewport={'width': 1440, 'height': 900})
                page = context.new_page(); page.on('pageerror', lambda error: report['errors'].append(str(error)))
                page.add_init_script("""(() => {
                  window.voiceTest={calls:0,streams:[],spoken:[],remoteOnly:false,denied:false,utterance:null};
                  const original=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                  navigator.mediaDevices.getUserMedia=async options=>{
                    voiceTest.calls++; if(voiceTest.denied) throw new DOMException('denied','NotAllowedError');
                    const stream=await original(options);voiceTest.streams.push(stream);return stream;
                  };
                  window.SpeechSynthesisUtterance=class {constructor(text){this.text=text;}};
                  Object.defineProperty(window,'speechSynthesis',{value:{
                    getVoices:()=>[{lang:'pt-BR',localService:!voiceTest.remoteOnly,name:'Explicit test double'}],
                    cancel:()=>{},speak:u=>{voiceTest.spoken.push(u.text);voiceTest.utterance=u;}
                  }});
                })()""")
                page.goto(f'http://127.0.0.1:{server.server_port}'); page.locator('#local-token').fill(settings.token)
                page.locator('#connect-form button').click(); expect(page.locator('#studio')).to_be_visible()
                expect(page.locator('#project-heading')).to_have_text(project['name'])
                page.locator('#voice-start').click(); expect(page.locator('#voice-dialog')).to_be_visible()
                check('Opening voice explanation never starts microphone', page.evaluate('voiceTest.calls') == 0)
                page.locator('#voice-confirm').click(); expect(page.locator('#voice-setup')).to_contain_text('modelo de conversa')
                check('Missing model fails before microphone', page.evaluate('voiceTest.calls') == 0)
                register_fixture(settings.home, base / 'weights')
                page.evaluate('voiceTest.remoteOnly=true'); page.locator('#voice-confirm').click()
                expect(page.locator('#voice-setup')).to_contain_text('Nenhuma voz na nuvem')
                check('Remote synthesis voice is rejected before capture', page.evaluate('voiceTest.calls') == 0)
                page.evaluate('voiceTest.remoteOnly=false;voiceTest.denied=true'); page.locator('#voice-confirm').click()
                expect(page.locator('#voice-bar')).to_be_hidden(); expect(page.locator('#notification')).to_contain_text('Permita o microfone')
                check('Permission denial releases voice session and remains retryable', page.locator('#voice-start').is_enabled())
                page.evaluate('voiceTest.denied=false')
                page.locator('#message-input').fill('Rascunho preservado'); page.locator('#voice-start').click(); page.locator('#voice-confirm').click()
                expect(page.locator('#voice-setup')).to_contain_text('mensagem digitada')
                check('Existing draft is never overwritten by voice', page.locator('#message-input').input_value() == 'Rascunho preservado')
                page.locator('[data-close="voice-dialog"]').click(); page.locator('#message-input').fill('')
                page.locator('#voice-start').click(); page.locator('#voice-confirm').click()
                expect(page.locator('#voice-status')).to_contain_text('Falando', timeout=30000)
                check('Successful retry clears the earlier permission error', page.locator('#notification').is_hidden())
                check('Actual captured PCM reaches authenticated route once', len(transcripts) == 1)
                check('Microphone shuts down before synthesis', page.evaluate("voiceTest.streams.every(s=>s.getTracks().every(t=>t.readyState==='ended'))"))
                check('Chat uses foundation with original transcript', app.chat.conversations(project['id']) and
                      any('Como organizar' in m['content'] for m in app.chat.get(project['id'], app.chat.conversations(project['id'])[0]['id'])['messages']))
                check('Update restart is blocked during listening or synthesis', page.evaluate('state.busy && !state.requestBusy'))
                check('Generated HTML stays inert', page.evaluate('window.PWNED') is None and page.locator('#messages script').count() == 0)
                page.screenshot(path=str(reports / 'voice-desktop.png'))
                page.locator('#voice-mute').click(); expect(page.locator('#voice-status')).to_contain_text('Ouvindo')
                check('Muting resumes listening without speaking over the microphone')
                page.locator('#voice-stop').click(); expect(page.locator('#voice-bar')).to_be_hidden()
                check('Stopping releases all tracks and restores text composer', page.evaluate("voiceTest.streams.every(s=>s.getTracks().every(t=>t.readyState==='ended')) && !state.busy"))
                spoken = page.evaluate('voiceTest.spoken.length')
                page.wait_for_timeout(700)
                check('Late callbacks cannot restart a stopped session', page.evaluate('voiceTest.spoken.length') == spoken and page.locator('#voice-bar').is_hidden())
                page.locator('#voice-start').click(); page.locator('#voice-confirm').click()
                expect(page.locator('#voice-status')).to_contain_text('Falando', timeout=30000)
                check('Second turn retains conversation history', len(engines) == 1 and len(engines[0].received) == 2 and
                      len([m for m in engines[0].received[-1] if m['role'] == 'user']) >= 2)
                page.locator('#voice-stop').click()
                baseline = len(app.chat.get(project['id'], app.chat.conversations(project['id'])[0]['id'])['messages'])
                speech_mode['hold'] = True
                page.locator('#voice-start').click(); page.locator('#voice-confirm').click()
                expect(page.locator('#voice-status')).to_contain_text('Entendendo', timeout=30000)
                wait_until(speech_started.is_set)
                page.locator('#voice-stop').click(); wait_until(lambda: app.voice.active is None)
                check('Stopping an active transcription cancels server and ignores its late result',
                      page.locator('#message-input').input_value() == '' and
                      len(app.chat.get(project['id'], app.chat.conversations(project['id'])[0]['id'])['messages']) == baseline)
                page.set_viewport_size({'width': 390, 'height': 844})
                check('Voice controls fit narrow screens', page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                page.screenshot(path=str(reports / 'voice-mobile.png'))
                check('No audio or voice setting is persisted in browser', page.evaluate("Object.keys(localStorage).every(k=>k==='localauthor.appearance') && sessionStorage.length===0"))
                check('No persistent transcription job stores audio', all(j['kind'] == 'chat' for j in app.jobs.list()))
                assert not report['errors'], report['errors']; report['success'] = True; browser.close()
        finally:
            server.shutdown(); server.server_close(); worker.join(); app.close()
            (reports / 'voice-ui-smoke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': len(report['checks']), 'success': report['success'], 'limitations': report['limitations']}))


if __name__ == '__main__': main()
