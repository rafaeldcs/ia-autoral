"""Verify the actual installed launcher without stopping or replacing servers."""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
CLIENT = Path(os.environ['LOCALAPPDATA']) / 'Programs/LocalAuthorServer/LocalAuthor.ServerLauncher.exe'

def listeners():
    script = 'Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 8765,8443 | Select-Object LocalPort,OwningProcess | ConvertTo-Json -Compress'
    raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', script], text=True)
    values = json.loads(raw)
    return sorted(values, key=lambda value: value['LocalPort'])

before = listeners()
checks = []
for attempt in range(2):
    report = REPORTS / f'server-launcher-native-{attempt + 1}.json'
    process = subprocess.Popen([str(CLIENT), '--smoke', str(report)], creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        code = process.wait(timeout=60)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError('Launcher did not complete its check within 60 seconds')
    result = json.loads(report.read_text(encoding='utf-8'))
    assert code == 0 and result['success'] and result['BackendReady'] and result['NetworkReady'], result
    checks.append(f'Native UI launch {attempt + 1}: authenticated backend and pinned HTTPS ready')
    assert listeners() == before, 'Existing server processes were replaced'
    checks.append(f'Launch {attempt + 1} and closing window preserve original server PIDs')

(REPORTS / 'server-launcher-smoke.json').write_text(json.dumps({
    'success': True, 'checks': checks, 'passed': len(checks),
    'limitations': ['Existing running services were preserved. This check does not reboot Windows or prove access from a second physical PC.']
}, indent=2), encoding='utf-8')
print(json.dumps({'success': True, 'passed': len(checks)}))
