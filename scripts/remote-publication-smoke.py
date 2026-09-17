"""Test remote publication with real TLS, native client, isolated server and device roles."""
import hashlib, http.client, json, os, socket, ssl, subprocess, sys, tempfile, threading, time
import base64, secrets, sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server
checks=[]
def check(name,value):
    assert value,name
    checks.append(name)
def run(*args,input_text=None):
    return subprocess.run([str(x) for x in args],input=input_text,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=90,check=True)
gateway=ROOT/'build/lan-server/LocalAuthor.Lan.exe'
client=ROOT/'build/lan-client/LocalAuthor.Client.exe'
binary=client.read_bytes()
digest=hashlib.sha256(binary).hexdigest().upper()
version=ET.parse(ROOT/'dotnet/LocalAuthor.Client/LocalAuthor.Client.csproj').find('.//Version').text+'.0'
password=secrets.token_urlsafe(32)
password_header=base64.b64encode(password.encode()).decode()
with tempfile.TemporaryDirectory(prefix='localauthor-publish-check-') as tmp:
    base=Path(tmp);settings=Settings.load(base/'backend');app=Application(settings);app.start()
    backend=create_server(app,ROOT/'ui',port=0)
    thread=threading.Thread(target=backend.serve_forever,daemon=True);thread.start()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    data=base/'lan'
    run(gateway,'init','--data',data,'--home',settings.home,'--bind','127.0.0.1','--prefix',32,'--port',port,'--backend-port',backend.server_port)
    normal=base/'client.localauthor';admin=base/'admin.localauthor'
    run(gateway,'add-device','--data',data,'--output',normal)
    run(gateway,'add-device','--data',data,'--output',admin,'--role','publisher')
    user=json.loads(normal.read_text());publisher=json.loads(admin.read_text())
    # Old registries did not have a Role property; they must remain non-administrative.
    devices=json.loads((data/'devices.json').read_text());devices[0].pop('Role',None)
    (data/'devices.json').write_text(json.dumps(devices))
    tls=ssl.create_default_context(cadata=ssl.DER_cert_to_PEM_cert((data/'server.cer').read_bytes()))
    process=subprocess.Popen([str(gateway),'serve','--data',str(data)],creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    def request(path,key=None,body=None,extra=None):
        conn=http.client.HTTPSConnection('127.0.0.1',port,context=tls,timeout=30)
        headers={'Authorization':'Bearer '+key} if key else {}
        if body is not None:headers.update({'Content-Type':'application/octet-stream','X-Release-Version':version,'X-Release-Sha256':digest,'X-Publication-Password':password_header})
        headers.update(extra or {})
        conn.request('POST' if body is not None else 'GET',path,body,headers)
        response=conn.getresponse();result=response.status,response.read();conn.close();return result
    upload='/api/client-update/publish'
    try:
        for _ in range(100):
            try:
                if request('/api/health',user['AccessKey'])[0]==200:break
            except OSError:pass
            time.sleep(.1)
        check('Same application exposes publication for any paired device',json.loads(request('/api/device',user['AccessKey'])[1])['canPublishUpdates'])
        check('Initial password setup required',not json.loads(request('/api/device',user['AccessKey'])[1])['publicationPasswordConfigured'])
        check('Publication cannot proceed without initial setup',request(upload,user['AccessKey'],b'x')[0]==428)
        def setup(value,key=user['AccessKey']):return request('/api/publication-password',key,json.dumps({'password':value}).encode(),{'Content-Type':'application/json'})[0]
        check('Password setup requires paired device',setup(password,None)==401)
        check('Short password refused',setup('short')==400)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(setup,[password,password]))
        check('Concurrent first setup has exactly one winner',sorted(results)==[200,409])
        check('Existing password cannot be overwritten',setup(secrets.token_urlsafe(32))==409)
        auth_db=data/'publication-auth.sqlite3'
        with sqlite3.connect(auth_db) as db:
            salt,stored,iterations=db.execute('SELECT salt,hash,iterations FROM publication_password').fetchone()
        db.close()
        check('Database stores salted PBKDF2 hash instead of password',len(salt)==32 and iterations==600000 and stored==hashlib.pbkdf2_hmac('sha256',password.encode(),salt,iterations,32) and password.encode() not in auth_db.read_bytes())
        check('Server reports publisher capability',json.loads(request('/api/device',publisher['AccessKey'])[1])['canPublishUpdates'])
        check('Unauthenticated publication denied',request(upload,body=b'x')[0]==401)
        check('Forged role cannot bypass password',request(upload,user['AccessKey'],b'x',{'X-Role':'publisher','X-Publication-Password':''})[0]==403)
        check('Legacy administrator also needs password',request(upload,publisher['AccessKey'],b'x',{'X-Publication-Password':''})[0]==403)
        check('Invalid declared size denied',request(upload,publisher['AccessKey'],b'x',{'Content-Length':str(300*1024*1024+1)})[0]==400)
        check('Invalid digest denied',request(upload,publisher['AccessKey'],b'x',{'X-Release-Sha256':'../bad'})[0]==400)
        check('Changed body rejected',request(upload,publisher['AccessKey'],b'altered')[0]==400)
        garbage=b'not an executable'
        check('Non executable rejected',request(upload,publisher['AccessKey'],garbage,{'X-Release-Sha256':hashlib.sha256(garbage).hexdigest().upper()})[0]==400)
        for pair,allowed in ((normal,True),(admin,True)):
            report=base/(pair.stem+'.json');run(client,'--smoke',pair,report)
            value=json.loads(report.read_text())
            check('Native publish button matches '+pair.stem+' permission',value['passed'] and value['canPublishUpdates']==allowed)
        # Interrupt an upload and prove that no partial version becomes current.
        conn=http.client.HTTPSConnection('127.0.0.1',port,context=tls,timeout=30)
        conn.putrequest('POST',upload)
        for name,value in {'Authorization':'Bearer '+publisher['AccessKey'],'Content-Type':'application/octet-stream','Content-Length':str(len(binary)),'X-Release-Version':version,'X-Release-Sha256':digest,'X-Publication-Password':password_header}.items():conn.putheader(name,value)
        conn.endheaders();conn.send(binary[:81920]);conn.close();time.sleep(1)
        releases=data/'client-releases'
        check('Interrupted upload does not activate a version',not (releases/'current.json').exists())
        check('Interrupted staging file cleaned',not list(releases.glob('*.upload')))
        report=base/'published.json';run(client,'--publish-smoke',normal,client,report,input_text=(password+'\n').encode())
        check('Native publisher uploads over authenticated HTTPS',json.loads(report.read_text())['passed'])
        manifest=json.loads((releases/'current.json').read_text())
        check('Published version and digest match selected executable',manifest['Version']==version and manifest['Sha256']==digest)
        check('Publisher audit identifies device without credential or password',any(user['DeviceId'] in p.read_text() and user['AccessKey'] not in p.read_text() and password not in p.read_text() for p in releases.glob('publication-*.json')))
        run(client,'--publish-smoke',admin,client,base/'repeat.json',input_text=(password+'\n').encode())
        check('Repeated identical publication is idempotent',json.loads((base/'repeat.json').read_text())['passed'])
        check('Reused version with different digest rejected',request(upload,publisher['AccessKey'],b'x',{'X-Release-Sha256':'B'*64})[0]==409)
        check('Downgrade denied',request(upload,publisher['AccessKey'],b'x',{'X-Release-Version':'0.1.0.0'})[0]==409)
        check('Ordinary client can receive published update',request('/api/client-update',user['AccessKey'])[0]==200)
        wrong=base64.b64encode(secrets.token_urlsafe(32).encode()).decode()
        for _ in range(5):request(upload,user['AccessKey'],b'x',{'X-Publication-Password':wrong})
        check('Repeated wrong passwords trigger cooldown',request(upload,user['AccessKey'],b'x',{'X-Publication-Password':wrong})[0]==429)
        process.terminate();process.wait(timeout=10)
        process=subprocess.Popen([str(gateway),'serve','--data',str(data)],creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                if request('/api/health',user['AccessKey'])[0]==200:break
            except OSError:pass
            time.sleep(.1)
        check('Password and cooldown survive server restart',json.loads(request('/api/device',user['AccessKey'])[1])['publicationPasswordConfigured'] and request(upload,user['AccessKey'],b'x')[0]==429)
        check('Configured password cannot be reset after restart',setup(password)==409)
        with sqlite3.connect(auth_db) as db:db.execute('UPDATE password_attempts SET locked_until=? WHERE device=?',(int(time.time())-1,user['DeviceId']))
        db.close()
        check('Correct password works after cooldown expires',request(upload,user['AccessKey'],b'x',{'X-Release-Version':'0.3.9.0'})[0]==400)
        # A valid newer upload must lose authorization if revoked before it completes.
        previous={'Version':'0.2.99.0','Sha256':'A'*64,'Size':1}
        (releases/'current.json').write_text(json.dumps(previous))
        conn=http.client.HTTPSConnection('127.0.0.1',port,context=tls,timeout=30)
        conn.putrequest('POST',upload)
        for name,value in {'Authorization':'Bearer '+publisher['AccessKey'],'Content-Type':'application/octet-stream','Content-Length':str(len(binary)),'X-Release-Version':version,'X-Release-Sha256':digest,'X-Publication-Password':password_header}.items():conn.putheader(name,value)
        conn.endheaders();conn.send(binary[:81920]);time.sleep(.2)
        run(gateway,'revoke','--data',data,'--id',publisher['DeviceId'])
        conn.send(binary[81920:]);response=conn.getresponse();response.read();conn.close()
        check('Revocation during upload prevents publication',response.status==403 and json.loads((releases/'current.json').read_text())==previous)
        check('Revoked publisher denied on next request',request(upload,publisher['AccessKey'],b'x')[0]==401)
        check('Other devices remain authorized',request('/api/health',user['AccessKey'])[0]==200)
    finally:
        process.terminate();process.wait(timeout=10);backend.shutdown();backend.server_close();thread.join();app.close()
result={'passed':len(checks),'checks':checks,'secondPhysicalComputerTested':False}
(ROOT/'reports/remote-publication-smoke.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
