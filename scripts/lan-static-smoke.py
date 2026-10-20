"""Real TLS regression: parallel page assets, bounded admission and API protection."""
import concurrent.futures
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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import make_handler
from http.server import ThreadingHTTPServer

report={'success':False,'checks':[],'scope':'isolated HTTPS gateway and temporary backend; no models or private data'}
def check(name,condition):
    assert condition,name
    report['checks'].append(name)

def port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));return probe.getsockname()[1]

def main():
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    dll=ROOT/'dotnet/LocalAuthor.Lan/bin/Release/net10.0/LocalAuthor.Lan.dll'
    if not dll.is_file():raise RuntimeError('Build LocalAuthor.Lan in Release first.')
    def run(*args):
        result=subprocess.run(['dotnet',str(dll),*map(str,args)],capture_output=True,creationflags=flags,timeout=30)
        if result.returncode:raise RuntimeError('Gateway fixture command failed.')
    with tempfile.TemporaryDirectory(prefix='lan-static-check-') as temp:
        base=Path(temp);settings=Settings.load(base/'backend');app=Application(settings);app.start()
        release=threading.Event();active=0;peak=0;lock=threading.Lock()
        handler=make_handler(app,ROOT/'ui')
        class DelayedAssets(handler):
            def do_GET(self):
                nonlocal active,peak
                if self.path=='/chat.css':
                    with lock:active+=1;peak=max(peak,active)
                    try:
                        release.wait(10)
                        time.sleep(.15)
                        super().do_GET()
                    finally:
                        with lock:active-=1
                else:super().do_GET()
        backend=ThreadingHTTPServer(('127.0.0.1',0),DelayedAssets)
        worker=threading.Thread(target=backend.serve_forever,daemon=True);worker.start()
        gateway=None
        try:
            lan=base/'lan';pair=base/'fixture.localauthor';tls_port=port()
            run('init','--data',lan,'--home',settings.home,'--bind','127.0.0.1','--prefix',32,'--port',tls_port,'--backend-port',backend.server_port)
            run('add-device','--data',lan,'--output',pair)
            connection=json.loads(pair.read_text());ca=base/'ca.pem'
            ca.write_text(ssl.DER_cert_to_PEM_cert((lan/'server.cer').read_bytes()))
            tls=ssl.create_default_context(cafile=str(ca))
            gateway=subprocess.Popen(['dotnet',str(dll),'serve','--data',str(lan)],creationflags=flags,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            def request(path,auth=False):
                client=http.client.HTTPSConnection('127.0.0.1',tls_port,context=tls,timeout=15)
                try:
                    client.request('GET',path,headers={'Authorization':'Bearer '+connection['AccessKey']} if auth else {})
                    response=client.getresponse();return response.status,response.read()
                finally:client.close()
            for _ in range(100):
                try:
                    if request('/')[0]==200:break
                except OSError:time.sleep(.1)
            release.set()
            with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:
                # Hold all four forwarding slots so a browser's parallel burst
                # deterministically needs the static queue instead of racing it.
                release.clear()
                burst=[pool.submit(request,'/chat.css') for _ in range(8)]
                deadline=time.monotonic()+4
                while active<4 and time.monotonic()<deadline:time.sleep(.01)
                check('Four active requests exercise the forwarding limit',active==4)
                check('Protected API still rejects missing authentication during saturation',request('/api/health')[0]==401)
                check('Authenticated API preserves immediate overload rejection',request('/api/health',True)[0]==429)
                release.set()
                replies=[future.result(timeout=10) for future in burst]
                report['parallel_assets']=[{'status':status,'error':body.decode(errors='replace')[:200] if status!=200 else None} for status,body in replies]
                expected=(ROOT/'ui/chat.css').read_bytes()
                check('Eight parallel public assets all load with exact bytes',all(status==200 and body==expected for status,body in replies))
                check('Static queue never increases the four-request forwarding limit',peak==4)
                release.clear()
                holders=[pool.submit(request,'/chat.css') for _ in range(4)]
                deadline=time.monotonic()+4
                while active<4 and time.monotonic()<deadline:time.sleep(.01)
                check('Timeout test holds all forwarding slots',active==4)
                waiting=pool.submit(request,'/appearance.js')
                start=time.monotonic();status,_=waiting.result(timeout=8)
                check('Queued static reads time out instead of waiting indefinitely',status==429 and 4<=time.monotonic()-start<=8)
                release.set()
                check('Active reads finish after a queued timeout',all(f.result(timeout=5)[0]==200 for f in holders))
                assets=['/','/chat.css','/identity.css','/identity.js','/chat-recovery.js','/chat.js','/appearance.js']
                requests=[pool.submit(request,path) for path in assets]
                page_replies=[f.result(timeout=8) for f in requests]
                report['page_assets']=[{'path':path,'status':status,'error':body.decode(errors='replace')[:200] if status!=200 else None} for path,(status,body) in zip(assets,page_replies)]
                check('A complete page asset burst succeeds after saturation',all(status==200 for status,_ in page_replies))
                release.clear()
                overflow=[pool.submit(request,'/chat.css') for _ in range(24)]
                done,_=concurrent.futures.wait(overflow,timeout=3,return_when=concurrent.futures.FIRST_COMPLETED)
                check('The bounded static queue rejects excess requests promptly',bool(done) and any(f.result()[0]==429 for f in done))
                release.set()
                check('Overload releases all admitted slots without leaking capacity',all(f.result(timeout=8)[0] in (200,429) for f in overflow) and request('/chat.css')[0]==200 and peak==4)
                check('Gateway remains healthy and authenticated',request('/api/health',True)[0]==200)
                check('Unknown public paths do not bypass authentication',request('/not-allowlisted.js')[0]==401)
            report['success']=True
        finally:
            release.set()
            if gateway is not None and gateway.poll() is None:gateway.terminate();gateway.wait(timeout=15)
            backend.shutdown();backend.server_close();worker.join();app.close()

try:main()
finally:
    target=ROOT/'reports/lan-static-smoke.json';target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'success':report['success'],'checks':len(report['checks'])}))
