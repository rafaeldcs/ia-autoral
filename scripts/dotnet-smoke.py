#!/usr/bin/env python3
"""Exercise the compiled facade against an isolated Python backend on loopback."""
import argparse
import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server


def main(args):
    report = {'at': datetime.now(timezone.utc).isoformat(), 'platform': sys.platform,
              'success': False, 'checks': [], 'scope': 'temporary data; compiled local facade; no user data'}
    process = server = app = thread = None
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        try:
            dll = ROOT / 'dotnet/LocalAI.Host/bin/Release/net10.0/LocalAI.Host.dll'
            if not dll.is_file():
                raise RuntimeError('Build LocalAI.Host in Release before running this check.')
            with socket.socket() as probe:
                if probe.connect_ex(('127.0.0.1', 5080)) == 0:
                    raise RuntimeError('Port 5080 is already in use; existing services are never stopped.')
            settings = Settings.load(Path(temporary) / 'data')
            app = Application(settings)
            app.start()
            server = create_server(app, ROOT / 'ui', port=0)
            # Close each backend connection so stopping the listener below
            # also models an unavailable backend, without live keep-alive handlers.
            server.RequestHandlerClass.protocol_version = 'HTTP/1.0'
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            env = dict(os.environ, LOCALAI_BACKEND_PORT=str(server.server_port),
                       DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='true',
                       ASPNETCORE_ENVIRONMENT='Production')
            process = subprocess.Popen(['dotnet', str(dll)], cwd=dll.parent, env=env,
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            def request(path, body=None, *, auth=True, headers=None):
                actual_headers = {'Content-Type': 'application/json'}
                if auth:
                    actual_headers['Authorization'] = 'Bearer ' + settings.token
                actual_headers.update(headers or {})
                connection = http.client.HTTPConnection('127.0.0.1', 5080, timeout=5)
                try:
                    connection.request('POST' if body is not None else 'GET', path,
                                       json.dumps(body).encode('utf-8') if body is not None else None, actual_headers)
                    response = connection.getresponse()
                    raw = response.read()
                    data = json.loads(raw) if 'application/json' in response.getheader('Content-Type', '') else raw
                    return response.status, dict(response.getheaders()), data
                finally:
                    connection.close()

            deadline = time.monotonic() + 25
            while True:
                if process.poll() is not None:
                    raise RuntimeError('Facade stopped during startup.')
                try:
                    response = request('/', auth=False)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Facade startup timeout.')
                    time.sleep(0.1)

            def check(name, condition):
                report['checks'].append({'name': name, 'passed': bool(condition)})
                if not condition:
                    raise AssertionError(name)

            check('static_ui_with_csp', response[0] == 200 and b'LocalAuthor' in response[2]
                  and "frame-ancestors 'none'" in response[1].get('Content-Security-Policy', ''))
            check('missing_token_rejected', request('/api/health', auth=False)[0] == 401)
            check('invalid_token_rejected', request('/api/health', headers={'Authorization': 'Bearer invalid'})[0] == 401)
            status, _, health = request('/api/health')
            check('authenticated_backend_proxy', status == 200 and health['offline'] and not health['model_qualified'])
            check('host_rebinding_rejected', request('/api/health', headers={'Host': 'evil.test:5080'})[0] == 403)
            check('cross_origin_rejected', request('/api/health', headers={'Origin': 'https://evil.test'})[0] == 403)
            check('same_origin_accepted', request('/api/health', headers={'Origin': 'http://127.0.0.1:5080'})[0] == 200)
            check('non_json_rejected', request('/api/import', {}, headers={'Content-Type': 'text/plain'})[0] == 415)
            check('post_forwarded_with_content_length', request('/api/import', {'title': 'Teste .NET', 'content': 'Estoque preservado com revisão humana.'})[0] == 200)
            status, _, answer = request('/api/consult', {'query': 'estoque'})
            check('retrieval_via_facade', status == 200 and len(answer['evidence']) == 1)
            server.shutdown()
            server.server_close()
            thread.join()
            server = None
            check('backend_outage_returns_503', request('/api/health')[0] == 503)
            report['success'] = True
        except Exception as exc:
            report['error'] = str(exc)
        finally:
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if server is not None:
                server.shutdown()
                server.server_close()
                thread.join()
            if app is not None:
                app.close()
            args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report['success'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, default=ROOT / 'reports/dotnet-smoke.json')
    raise SystemExit(main(parser.parse_args()))
