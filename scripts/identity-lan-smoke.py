"""Real TLS, paired devices and independent profile cookies; disposable data only."""
import argparse
import http.client
import json
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--gateway',type=Path,required=True);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    checks=[]
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary);settings=Settings.load(root/'home');app=Application(settings)
        owner,_=app.identity.identify('Owner fixture',local=True)
        person=app.identity.create_named_user(owner,'Person fixture')
        first=app.identity.add_project(owner,'Owner project',managed=True)
        second=app.identity.add_project(person,'Person project',managed=True)
        backend=create_server(app,ROOT/'ui',port=0);thread=threading.Thread(target=backend.serve_forever,daemon=True);thread.start()
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
        def run(*command):return subprocess.run([str(args.gateway),*map(str,command)],capture_output=True,check=True,timeout=45,creationflags=flags)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));tls_port=sock.getsockname()[1]
        data=root/'lan';run('init','--data',data,'--home',settings.home,'--bind','127.0.0.1','--prefix','32','--port',tls_port,'--backend-port',backend.server_port)
        keys=[]
        for name in ('A','B'):
            pair=root/(name+'.localauthor');run('add-device','--data',data,'--name','TLS fixture '+name,'--output',pair)
            keys.append(json.loads(pair.read_text(encoding='utf-8'))['AccessKey'])
        ca=root/'server.pem';ca.write_text(ssl.DER_cert_to_PEM_cert((data/'server.cer').read_bytes()),encoding='ascii')
        tls=ssl.create_default_context(cafile=str(ca))
        process=subprocess.Popen([str(args.gateway),'serve','--data',str(data)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
        def request(path,device=0,cookie=None,payload=None,extra=None):
            headers={} if device is None else {'Authorization':'Bearer '+keys[device]}
            if cookie:headers['Cookie']=cookie
            headers.update(extra or {})
            if payload is not None:headers['Content-Type']='application/json'
            connection=http.client.HTTPSConnection('127.0.0.1',tls_port,context=tls,timeout=10)
            connection.request('POST' if payload is not None else 'GET',path,json.dumps(payload) if payload is not None else None,headers)
            response=connection.getresponse();raw=response.read();result=response.status,dict(response.getheaders()),raw;connection.close();return result
        try:
            deadline=time.monotonic()+25
            while True:
                try:
                    if request('/api/identity/status')[0]==200:break
                except OSError:
                    if time.monotonic()>deadline:raise
                    time.sleep(.2)
            checks.append('TLS certificate and both paired device credentials are real')
            def login(device,username):
                status,headers,raw=request('/api/identity/identify',device,payload={'name':username})
                assert status==200,(status,raw)
                cookie=headers['Set-Cookie'];assert 'HttpOnly' in cookie and 'Secure' in cookie and 'SameSite=Strict' in cookie
                assert 'la_profile' not in raw.decode()
                return cookie.split(';',1)[0]
            a=login(0,'Owner fixture')
            assert request('/api/projects',1)[0]==401
            b=login(1,'Person fixture')
            for device,cookie,expected in ((0,a,first['id']),(1,b,second['id'])):
                status,_,raw=request('/api/projects',device,cookie);assert status==200
                assert [p['id'] for p in json.loads(raw)]==[expected]
            checks.append('Two paired devices retain independent HttpOnly Secure profile sessions')
            assert request('/api/projects',0)[0]==401 and request('/api/projects',1)[0]==401
            checks.append('Shared upstream HTTP client never reuses another device profile cookie')
            assert request('/api/projects',None,a)[0]==401
            assert request('/api/projects',0,a,extra={'X-LocalAuthor-Profile':person['id']})[0]==401
            checks.append('Profile cookie cannot bypass device pairing or stale-tab identity checks')
            assert request('/api/conversations?project_id='+first['id'],1,b)[0]==404
            checks.append('Foreign private project IDs fail across real TLS')
            for path in ('/identity.js','/identity.css','/chat-recovery.js'):
                status,_,raw=request(path);assert status==200 and raw
            checks.append('New profile assets are served through the native gateway')
            draft={'project_id':first['id'],'conversation_id':'','text':'TLS draft fixture','mode':'guide','revision':0,'pending':None}
            status,_,raw=request('/api/chat-draft',0,a,payload=draft)
            assert status==200 and json.loads(raw)['revision']==1
            status,_,raw=request('/api/chat-draft?project_id='+first['id']+'&conversation_id=',0,a)
            assert status==200 and json.loads(raw)['text']==draft['text']
            assert request('/api/chat-draft?project_id='+first['id']+'&conversation_id=',1,b)[0]==404
            assert request('/api/chat-workspace',0,a,payload={'project_id':first['id'],'conversation_id':''})[0]==200
            status,_,raw=request('/api/chat-workspace',0,a)
            assert status==200 and json.loads(raw)['selection']['project_id']==first['id']
            checks.append('Draft and workspace recovery work through real TLS and remain profile scoped')
            status,_,raw=request('/api/identity/status',extra={'X-LocalAuthor-Gateway':'lan','X-LocalAuthor-Device':'spoof'})
            assert status==200 and json.loads(raw)['can_setup'] is True
            checks.append('Gateway overwrites client-supplied device and origin headers')
            assert request('/api/device')[0]==200
            checks.append('Device management remains available independently of a personal session')
            status,_,raw=request('/api/health')
            assert status==200 and json.loads(raw)=={'status':'ok','profile_required':True}
            checks.append('Existing discovery and server boot probes work before login without leaking statistics')
            assert request('/api/identity/logout',0,a,payload={})[0]==200
            assert request('/api/projects',0,a)[0]==401 and request('/api/projects',1,b)[0]==200
            checks.append('Logout revokes only the selected profile session')
        finally:
            process.terminate();process.wait(timeout=10);backend.shutdown();backend.server_close();thread.join();app.close()
    result={'success':True,'checks':checks,'temporary_data_only':True,'second_physical_computer_tested':False,'model_inference':False}
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
