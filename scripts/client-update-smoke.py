"""Real HTTPS download, native process replacement/restart, and rollback in isolated folders."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
from ui_profile_fixture import enter_profile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server
from localauthor.util import write_json

checks = []
FLAGS = subprocess.CREATE_NO_WINDOW
native_environment = None
def check(name, result):
    assert result, name
    checks.append(name)
    print('PASS: '+name,flush=True)
def run(*args):
    result = subprocess.run([str(a) for a in args], creationflags=FLAGS, capture_output=True, timeout=90,
                            env=native_environment if Path(str(args[0])).name=='LocalAuthor.Client.exe' else None)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace'))
    return result
def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest().upper()
def wait_file(path, timeout=50):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding='utf-8-sig'))
            except json.JSONDecodeError:
                pass
        time.sleep(.1)
    raise AssertionError('Test report did not arrive')

gateway = ROOT / 'build/lan-server/LocalAuthor.Lan.exe'
old = ROOT / 'build/update-fixture/LocalAuthor.Client.exe'
new = ROOT / 'build/lan-client/LocalAuthor.Client.exe'
version = ET.parse(ROOT/'dotnet/LocalAuthor.Client/LocalAuthor.Client.csproj').find('.//Version').text+'.0'
broken = ROOT / 'build/update-failure/LocalAuthor.UpdateFailureFixture.exe'
with tempfile.TemporaryDirectory(prefix='localauthor-update-check-') as temp:
    base = Path(temp)
    # Drive the actual onboarding form in isolated native WebViews. No production
    # auth bypass or test credential is built into the application. Debugging is
    # enabled only for these disposable subprocesses, bound to loopback.
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));debug_port=sock.getsockname()[1]
    native_environment=dict(os.environ,WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=f'--remote-debugging-address=127.0.0.1 --remote-debugging-port={debug_port}')
    profile_stop=threading.Event();profile_checks=[];profile_errors=[]
    def drive_profiles():
        # Keep one driver alive. Repeated driver teardown can leave the next
        # native WebView undiscovered when the previous process closes.
        with sync_playwright() as playwright:
            browser=None;last_diagnostic=None
            while not profile_stop.is_set():
                try:
                    if browser is None or not browser.is_connected():
                        browser=playwright.chromium.connect_over_cdp(f'http://127.0.0.1:{debug_port}',timeout=1000)
                        heartbeat=browser.new_browser_cdp_session()
                    # Pump the protocol even if a closing WebView has no pages;
                    # otherwise the disconnect event can remain undelivered.
                    heartbeat.send('Browser.getVersion')
                    for context in browser.contexts:
                        for page in context.pages:
                            page.wait_for_timeout(20)
                            location=urlsplit(page.url)
                            if (location.scheme,location.hostname,location.port,location.path,location.query,location.fragment)!=('https','127.0.0.1',port,'/','',''):continue
                            if page.locator('#identity-gate[open]:visible').count():
                                try:
                                    enter_profile(page);profile_checks.append('native form login')
                                    print('PASS: Native fixture selected its profile through the real form',flush=True)
                                except Exception as exc:
                                    if not page.is_closed():profile_errors.append(type(exc).__name__)
                            download=page.locator('#native-installer-fixture-download')
                            if download.count():
                                download.click();download.evaluate('(node)=>node.remove()')
                except Exception as error:
                    diagnostic=type(error).__name__+': '+str(error).splitlines()[0]
                    if diagnostic!=last_diagnostic:
                        print('Native driver reconnect: '+diagnostic,flush=True);last_diagnostic=diagnostic
                    browser=None  # Native updater closes/reopens the WebView.
                profile_stop.wait(.25)
    settings = Settings.load(base / 'backend')
    app = Application(settings)
    installer_fixture=b'MZ'+b'explicit installer download fixture'*1024
    installer_folder=settings.home/'lan/private-installers'/('a'*32);installer_folder.mkdir(parents=True)
    (installer_folder/'Instalar-LocalAuthor-Conectado.exe').write_bytes(installer_fixture)
    write_json(settings.home/'lan/installer-release.json',{'folder':'a'*32,'version':'0.3.10','size':len(installer_fixture),'sha256':hashlib.sha256(installer_fixture).hexdigest().upper()})
    app.start()
    backend = create_server(app, ROOT / 'ui', port=0)
    thread = threading.Thread(target=backend.serve_forever, daemon=True)
    thread.start()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    data = base / 'lan'
    pair = base / 'test.localauthor'
    run(gateway, 'init', '--data', data, '--home', settings.home, '--bind', '127.0.0.1', '--prefix', 32, '--port', port, '--backend-port', backend.server_port)
    run(gateway, 'add-device', '--data', data, '--output', pair)
    connection = json.loads(pair.read_text())
    ca = base / 'server.pem'
    ca.write_text(ssl.DER_cert_to_PEM_cert((data / 'server.cer').read_bytes()))
    tls = ssl.create_default_context(cafile=str(ca))
    process = subprocess.Popen([str(gateway), 'serve', '--data', str(data)], creationflags=FLAGS, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    def request(path, key=connection['AccessKey']):
        client = http.client.HTTPSConnection('127.0.0.1', port, context=tls, timeout=10)
        headers = {'Authorization': 'Bearer ' + key} if key else {}
        client.request('GET', path, headers=headers)
        response = client.getresponse()
        body = response.read()
        status = response.status
        client.close()
        return status, body
    releases = data / 'client-releases'
    releases.mkdir()
    def publish(binary, version, *, corrupt=False):
        digest = sha(binary)
        manifest = {'Version': version, 'Sha256': digest, 'Size': binary.stat().st_size}
        target = releases / (digest + '.exe')
        shutil.copyfile(binary, target)
        if corrupt:
            with target.open('r+b') as stream:
                stream.seek(-1, 2)
                original = stream.read(1)[0]
                stream.seek(-1, 2)
                stream.write(bytes([original ^ 255]))
        (releases / 'current.json').write_text(json.dumps(manifest))
        return digest
    def attempt(name, expected_success=True, source=pair, automatic=False, extra_args=()):
        folder = base / name
        folder.mkdir()
        executable = folder / 'LocalAuthor.Client.exe'
        shutil.copyfile(old, executable)
        sentinel = folder / 'connection-preserved.txt'
        sentinel.write_text('configuration untouched')
        report = folder / 'result.json'
        try:
            parent = subprocess.run([str(executable), '--auto-update-smoke' if automatic else '--update-smoke', str(source), str(report), *extra_args], creationflags=FLAGS, timeout=90,env=native_environment)
        except subprocess.TimeoutExpired:
            # Save only this disposable native fixture's UI for diagnosis.
            try:
                with sync_playwright() as playwright:
                    browser=playwright.chromium.connect_over_cdp(f'http://127.0.0.1:{debug_port}',timeout=3000)
                    for context in browser.contexts:
                        for page in context.pages:
                            page.screenshot(path=str(ROOT/'reports/client-update-timeout.png'))
                            print(page.evaluate("({path:location.pathname,identityLoaded:!!window.LocalAuthorIdentity,profile:!!window.LocalAuthorIdentity?.user,recoveryLoaded:!!window.LocalAuthorRecovery,studioHidden:document.querySelector('#studio')?.hidden,notice:document.querySelector('#notification')?.textContent,busy:typeof state!=='undefined'?state.busy:null})"),flush=True)
            except Exception as diagnostic:
                print('Native fixture diagnostic unavailable: '+type(diagnostic).__name__,flush=True)
            raise
        if expected_success:
            check(name + ': old process exits for update', parent.returncode == 0)
            job = Path(Path(str(report) + '.job').read_text())
            state_path = job / 'state.json'
            deadline = time.monotonic() + 50
            state = {}
            while time.monotonic() < deadline:
                if state_path.exists():
                    state = wait_file(state_path)
                    if state['state'] != 'replaced':
                        break
                time.sleep(.1)
            return executable, report, state, job
        check(name + ': rejected before replacement', parent.returncode != 0 and sha(executable) == sha(old))
        check(name + ': configuration preserved', sentinel.read_text() == 'configuration untouched')
        return executable, report, None, None
    try:
        profile_thread=threading.Thread(target=drive_profiles,daemon=True);profile_thread.start()
        for _ in range(100):
            try:
                if request('/api/health')[0] == 200: break
            except OSError: pass
            time.sleep(.1)
        installer_report=base/'native-installer.json';installer_target=base/'downloaded-installer.exe'
        run(new,'--installer-download-smoke',pair,installer_report,installer_target)
        native_installer=wait_file(installer_report)
        (ROOT/'reports/native-installer-download.json').write_text(json.dumps(native_installer),encoding='utf-8')
        print('Native installer result: '+json.dumps(native_installer),flush=True)
        check('Native WebView downloads the exact published installer through authenticated TLS',native_installer['passed'] and installer_target.read_bytes()==installer_fixture)
        check('Native installer download accepts only its pinned server endpoint',native_installer['restricted'])
        check('No publication returns 404', request('/api/client-update')[0] == 404)
        check('Update manifest requires device authentication', request('/api/client-update', '')[0] == 401)
        publisher = ROOT / 'scripts/lan/Publish-ClientUpdate.ps1'
        run('powershell', '-NoProfile', '-File', publisher, '-ClientPath', new, '-DataRoot', data)
        check('Publisher creates verified release', json.loads((releases / 'current.json').read_text(encoding='utf-8-sig'))['Sha256'] == sha(new))
        run('powershell', '-NoProfile', '-File', publisher, '-ClientPath', new, '-DataRoot', data)
        check('Publishing identical release is idempotent', True)
        refused = subprocess.run(['powershell', '-NoProfile', '-File', str(publisher), '-ClientPath', str(old), '-DataRoot', str(data)], creationflags=FLAGS, capture_output=True, timeout=30)
        check('Publisher refuses version downgrade', refused.returncode != 0 and json.loads((releases / 'current.json').read_text(encoding='utf-8-sig'))['Sha256'] == sha(new))
        digest = publish(new, version)
        check('Package requires device authentication', request('/api/client-update/package?sha256=' + digest, '')[0] == 401)
        check('Package traversal rejected', request('/api/client-update/package?sha256=../../server.pfx')[0] == 400)
        check('Authenticated manifest exposes version and digest only', set(json.loads(request('/api/client-update')[1])) == {'version', 'sha256', 'size'})
        draft_folder = base / 'draft-check'
        draft_folder.mkdir()
        draft_client = draft_folder / 'LocalAuthor.Client.exe'
        shutil.copyfile(old, draft_client)
        draft_report = draft_folder / 'draft.json'
        run(draft_client, '--auto-update-smoke', pair, draft_report, '--draft')
        check('Unsent draft defers automatic restart in real native chat', wait_file(draft_report)['passed'] and sha(draft_client) == sha(old))
        executable, report, state, job = attempt('successful-update', automatic=True, extra_args=('--appearance',))
        check('Updater confirms new process startup', state.get('state') == 'completed')
        check('New native application reopens authenticated chat', wait_file(report)['desktopLogin'])
        check('New native application has no connection header', wait_file(report)['nativeHeaderAbsent'])
        check('Changing saved appearance does not block automatic update', state.get('state') == 'completed' and sha(executable) == sha(new))
        check('Installed binary equals published version', sha(executable) == sha(new))
        check('Old executable remains recoverable', any(sha(p) == sha(old) for p in executable.parent.glob('*.previous')))
        check('Adjacent configuration remains untouched', (executable.parent / 'connection-preserved.txt').read_text() == 'configuration untouched')
        check('Verified download removed after success', not (job / 'download.exe').exists())
        publish(new, version, corrupt=True)
        attempt('corrupt-package', expected_success=False)
        publish(new, '0.3.99.0')
        attempt('wrong-executable-version', expected_success=False)
        publish(new, '0.1.0.0')
        attempt('downgrade', expected_success=False)
        publish(new, version)
        wrong = dict(connection)
        wrong['CertificateSha256'] = 'A' * 64
        bad_pair = base / 'wrong.localauthor'
        bad_pair.write_text(json.dumps(wrong))
        attempt('wrong-server-identity', expected_success=False, source=bad_pair)
        broken_hash = publish(broken, '0.4.0.0')
        blocked = Path(os.environ['LOCALAPPDATA']) / 'LocalAuthorClient/updates' / ('blocked-' + broken_hash)
        if blocked.exists(): blocked.unlink()  # Only this deterministic failure fixture's marker.
        executable, report, state, job = attempt('failed-new-startup')
        check('Failed startup rolls back', state.get('state') == 'rolled-back')
        check('Rollback restores exact previous executable', sha(executable) == sha(old))
        check('Previous version reopens chat after rollback', wait_file(Path(str(report) + '.rollback'))['desktopLogin'])
        check('Broken release blocked from repeated automatic installation', blocked.exists())
        run(gateway, 'revoke', '--data', data, '--id', connection['DeviceId'])
        check('Revoked device cannot download updates', request('/api/client-update')[0] == 401)
        check('Native profile onboarding and login use real forms',len(profile_checks)>=3 and not profile_errors)
    finally:
        profile_stop.set();profile_thread.join(timeout=5)
        (ROOT/'reports/client-update-profile-driver.json').write_text(json.dumps({'logins':len(profile_checks),'errors':profile_errors}),encoding='utf-8')
        process.terminate()
        process.wait(timeout=10)
        backend.shutdown()
        backend.server_close()
        app.close()
result = {'passed': len(checks), 'checks': checks, 'secondPhysicalComputerTested': False}
(ROOT / 'reports/client-update-smoke.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
