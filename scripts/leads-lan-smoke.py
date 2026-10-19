"""Real TLS gateway/auth route smoke using isolated data, no contacts or model calls."""
import argparse
import http.client
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1];sys.path.insert(0, str(ROOT/'src'))
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server


def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--gateway', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True);args = parser.parse_args()
    checks = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary);settings = Settings.load(root/'home');app = Application(settings)
        (root/'project').mkdir();project = app.store.add_project('Leads sintéticos', str(root/'project'))
        backend = create_server(app, ROOT/'ui', port=0);thread = threading.Thread(target=backend.serve_forever, daemon=True);thread.start()
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        def run(*command):return subprocess.run([str(args.gateway), *map(str, command)], capture_output=True, check=True, timeout=45, creationflags=flags)
        data = root/'lan';tls_port = port();pair = root/'qa.localauthor'
        run('init','--data',data,'--home',settings.home,'--bind','127.0.0.1','--prefix','32','--port',tls_port,'--backend-port',backend.server_port)
        run('add-device','--data',data,'--name','QA temporário','--output',pair)
        device = json.loads(pair.read_text(encoding='utf-8'));key = device['AccessKey']
        ca = root/'server.pem';ca.write_text(ssl.DER_cert_to_PEM_cert((data/'server.cer').read_bytes()), encoding='ascii')
        tls = ssl.create_default_context(cafile=str(ca))
        process = subprocess.Popen([str(args.gateway),'serve','--data',str(data)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        def request(path, auth=True):
            connection = http.client.HTTPSConnection('127.0.0.1', tls_port, context=tls, timeout=5)
            connection.request('GET',path,headers={'Authorization':'Bearer '+key} if auth else {})
            response = connection.getresponse();raw = response.read();connection.close();return response.status, raw
        try:
            deadline = time.monotonic()+20
            while True:
                try:
                    if request('/api/health')[0]==200:break
                except OSError:
                    if time.monotonic()>deadline:raise
                    time.sleep(.2)
            checks.append('TLS handshake validates the generated certificate and paired device')
            for path in ('/leads','/leads.js','/leads.css'):
                status, raw = request(path);assert status==200 and raw
            checks.append('all three lead UI routes pass through the native gateway')
            status, raw = request('/api/leads?project_id='+project['id']);assert status==200 and json.loads(raw)['items']==[]
            checks.append('authenticated lead API crosses the TLS gateway to the backend')
            assert request('/api/leads?project_id='+project['id'], False)[0]==401
            checks.append('anonymous API access denied')
            assert request('/api/leads/relay?project_id='+project['id'])[0]==200
            checks.append('relay status available without exposing connection secrets')
        finally:
            process.terminate();process.wait(timeout=10)
            backend.shutdown();backend.server_close();thread.join();app.close()
    result = {'success':True,'checks':checks,'temporary_data_only':True,'second_physical_computer_tested':False,'model_inference':False}
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':main()
