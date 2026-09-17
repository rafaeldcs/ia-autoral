"""Real TLS gateway + temporary backend + packaged Windows client integration."""
import os,sys,json,tempfile,threading,subprocess,ssl,http.client,time,socket,shutil
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from localauthor.application import Application
from localauthor.config import Settings
from localauthor.server import create_server
checks=[];report=ROOT/'reports/lan-smoke.json'
gateway=ROOT/'build/lan-server/LocalAuthor.Lan.exe'
setup=ROOT/'build/lan-setup/LocalAuthor.Setup.exe'
def check(name,result=True):
    assert result,name
    checks.append(name)
def run(*args,timeout=60):
    return subprocess.run([str(a) for a in args],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=timeout,check=True)
def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
with tempfile.TemporaryDirectory(prefix='localauthor-lan-') as tmp:
    base=Path(tmp);settings=Settings.load(base/'backend')
    previous=json.loads((Path(os.environ['LOCALAPPDATA'])/'LocalAuthor/exports/engineering-report.json').read_text(encoding='utf-8'))
    checkpoint=Path(previous['selectedCheckpoint']);target=settings.home/'models/candidate';target.mkdir()
    for suffix in ['', '.sha256']:shutil.copyfile(str(checkpoint)+suffix,str(target/'best.npz')+suffix)
    previous['selectedCheckpoint']=str(target/'best.npz')
    (settings.home/'exports/engineering-report.json').write_text(json.dumps(previous),encoding='utf-8')
    project=base/'project';project.mkdir();app=Application(settings);app.start()
    backend=create_server(app,ROOT/'ui',port=0);thread=threading.Thread(target=backend.serve_forever,daemon=True);thread.start()
    lan=base/'lan';tls_port=port();pair=base/'test.localauthor';pair2=base/'second.localauthor'
    run(gateway,'init','--data',lan,'--home',settings.home,'--bind','127.0.0.1','--prefix','32','--port',tls_port,'--backend-port',backend.server_port)
    run(gateway,'add-device','--data',lan,'--name','Computador de teste','--output',pair)
    run(gateway,'add-device','--data',lan,'--name','Segundo dispositivo de teste','--output',pair2)
    connection=json.loads(pair.read_text());second=json.loads(pair2.read_text());key=connection['AccessKey']
    check('Server device registry contains hashes, not connection keys',key not in (lan/'devices.json').read_text())
    ca=base/'server.pem';ca.write_text(ssl.DER_cert_to_PEM_cert((lan/'server.cer').read_bytes()))
    tls=ssl.create_default_context(cafile=str(ca))
    process=subprocess.Popen([str(gateway),'serve','--data',str(lan)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    def request(path,body=None,key_value=key,headers=None,method=None):
        conn=http.client.HTTPSConnection('127.0.0.1',tls_port,context=tls,timeout=15)
        hdr={'Authorization':'Bearer '+key_value} if key_value else {}
        if body is not None:hdr['Content-Type']='application/json'
        hdr.update(headers or {})
        conn.request(method or ('POST' if body is not None else 'GET'),path,json.dumps(body) if body is not None else None,hdr)
        response=conn.getresponse();raw=response.read();status=response.status;conn.close()
        try:value=json.loads(raw)
        except (ValueError,UnicodeError):value=raw.decode('utf-8')
        return status,value
    try:
        for _ in range(100):
            try:
                if request('/api/health')[0]==200:break
            except (OSError,ssl.SSLError):time.sleep(.1)
        check('Authenticated health over real HTTPS',request('/api/health')[0]==200)
        check('Static UI served over HTTPS',request('/',key_value='')[0]==200)
        check('Missing credential rejected',request('/api/health',key_value='')[0]==401)
        check('Wrong device key rejected',request('/api/projects',key_value='A'*64)[0]==401)
        check('Original backend token not accepted as LAN credential',request('/api/health',key_value=settings.token)[0]==401)
        check('Foreign origin rejected',request('/api/health',headers={'Origin':'https://evil.example'})[0]==403)
        check('Foreign host rejected',request('/api/health',headers={'Host':'evil.example'})[0]==400)
        check('Cross-site browser request rejected',request('/api/health',headers={'Sec-Fetch-Site':'cross-site'})[0]==403)
        check('CORS preflight refused',request('/api/health',method='OPTIONS')[0]==405)
        check('Untrusted certificate rejected by default TLS validation',True)
        try:
            c=http.client.HTTPSConnection('127.0.0.1',tls_port,timeout=3);c.request('GET','/');c.getresponse()
            raise AssertionError('TLS accepted unknown certificate')
        except ssl.SSLCertVerificationError:pass
        status,proj=request('/api/projects',{'name':'Laboratório LAN','root':str(project)});check('Project registered through gateway',status==200)
        status,conv=request('/api/conversations',{'project_id':proj['id'],'title':'Teste na rede'});check('Conversation created',status==200)
        body={'project_id':proj['id'],'conversation_id':conv['id'],'message':'Como tornar a interface intuitiva?','mode':'guide'}
        status,result=request('/api/chat',body);check('Guide response through gateway',status==200 and 'botão nativo' in result['messages'][-1]['content'])
        status,result=request('/api/chat',{**body,'message':key});check('Device key cannot be stored in a chat message',status==400)
        sample=previous['evaluation']['cases'][0]
        status,job=request('/api/chat',{**body,'message':sample['prompt'],'mode':'model'});check('Real model request queued through HTTPS',status==200 and 'job' in job)
        for _ in range(120):
            status,current=request('/api/jobs/'+job['job']['id'])
            if current['state'] in ['completed','failed']:break
            time.sleep(.25)
        check('Own neural model returns expected answer through LAN gateway',current['state']=='completed' and current['result']['messages'][-1]['content']==sample['answer'])
        installer_report=base/'install-report.json';run(setup,'--test-install',installer_report,timeout=90)
        install=json.loads(installer_report.read_text());check('Packaged installer extracts and verifies every payload hash',install['passed'])
        installed=Path(install['path'])/'LocalAuthor.Client.exe'
        desktop_report=ROOT/'reports/lan-desktop.json';run(installed,'--smoke',pair,desktop_report,timeout=70)
        desktop=json.loads(desktop_report.read_text());check('Installed native client verifies TLS, authenticates and opens chat',desktop['passed'])
        bad=base/'bad.localauthor';bad.write_text(json.dumps({**connection,'CertificateSha256':'0'*64}))
        negative=base/'pin-error.json'
        rejected=subprocess.run([str(installed),'--smoke',str(bad),str(negative)],creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
        check('Native client rejects a different certificate pin',rejected.returncode!=0 and not json.loads(negative.read_text())['passed'])
        run(gateway,'revoke','--data',lan,'--id',connection['DeviceId'])
        check('Revocation effective without server restart',request('/api/health')[0]==401)
        check('Revocation does not affect another paired device',request('/api/health',key_value=second['AccessKey'])[0]==200)
        backend.shutdown();backend.server_close();thread.join()
        # Existing keep-alive connections drain at the backend's 15-second timeout.
        time.sleep(16)
        check('Stopped backend produces friendly 503',request('/api/health',key_value=second['AccessKey'])[0]==503)
    finally:
        process.terminate();process.wait(timeout=10)
        if thread.is_alive():backend.shutdown();backend.server_close();thread.join()
        app.close()
report.write_text(json.dumps({'passed':len(checks),'checks':checks,'temporaryDataOnly':True,'secondPhysicalComputerTested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':len(checks),'checks':checks},ensure_ascii=True))
