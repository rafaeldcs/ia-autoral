"""Disposable PostgreSQL/API/Next integration checks; synthetic accounts only."""
import concurrent.futures, http.cookiejar, json, os, pathlib, secrets, subprocess, time, unittest, urllib.error, urllib.request, uuid

ROOT=pathlib.Path('/tmp'); E=ROOT/'evidence'; E.mkdir(exist_ok=True)
processes=[]; logs=[]
token=secrets.token_hex(32); password=secrets.token_urlsafe(24)
port=3100; origin='http://127.0.0.1:3100'; api='http://127.0.0.1:5088'
env=os.environ.copy(); env.update(ORBIT_RUNTIME='/tmp/runtime.json',ORBIT_KEYS_DIR='/tmp/keys',ORBIT_REPOSITORIES='/tmp/repos',ORBIT_PROXY_TOKEN=token,ORBIT_WEB_PORT='3100',ORBIT_API_PORT='5088',HOSTNAME='127.0.0.1',PORT='3100',NODE_ENV='production')
env.pop('ORBIT_PUBLIC_ORIGIN',None)
pgbin=max(pathlib.Path('/usr/lib/postgresql').glob('*/bin'),key=lambda p:int(p.parent.name))
dbport='55432'
def pg(*args):
    return subprocess.run([str(pgbin/args[0]),*args[1:]],check=True,capture_output=True,text=True)
def sql(statement):
    return pg('psql','-h','127.0.0.1','-p',dbport,'-U','orbit','-d','orbit','-At','-c',statement).stdout.strip()
def start(cmd,name,cwd=None):
    log=(E/(name+'.log')).open('w');logs.append(log)
    p=subprocess.Popen(cmd,env=env,cwd=cwd,stdout=log,stderr=subprocess.STDOUT);processes.append(p);return p
def stop(p):
    p.terminate()
    try:p.wait(15)
    except subprocess.TimeoutExpired:p.kill();p.wait()
def client():return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def request(c,path,method='GET',body=None,base=api,headers=None):
    hs={'X-Orbit-Token':token,'Content-Type':'application/json'} if base==api else {'Origin':origin,'Content-Type':'application/json'}
    hs.update(headers or {})
    r=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers=hs,method=method)
    try:response=c.open(r,timeout=20)
    except urllib.error.HTTPError as ex:response=ex
    raw=response.read(); text=raw.decode()
    try:data=json.loads(text) if text else {}
    except ValueError:data={'raw':text}
    return response.status,data,response.headers
def wait_api():
    for _ in range(80):
        try:
            if request(client(),'/api/health')[0]==200:return
        except OSError:pass
        time.sleep(.25)
    raise RuntimeError('API failed to start')

class Functional(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin=client();s,d,h=request(cls.admin,'/api/auth/setup','POST',{'name':'Administrador QA','email':'admin@orbit.test','password':password})
        assert s==200
        cls.accounts={'admin':cls.admin}
        for role in ['manager','member','viewer']:
            assert request(cls.admin,'/api/users','POST',{'name':'QA '+role,'email':role+'@orbit.test','password':password,'role':role})[0]==201
            c=client();assert request(c,'/api/auth/login','POST',{'email':role+'@orbit.test','password':password})[0]==200;cls.accounts[role]=c
        s,d,_=request(cls.admin,'/api/projects','POST',{'key':'GQA','name':'Git e entregas QA'});assert s==201;cls.project=d['id']
        cls.path='/api/projects/'+cls.project+'/git'
        cls.config={'url':'https://github.com/rafaeldcs/ia-autoral.git','branch':'codex/local-learning-execution','workflow':'orbit-hml.yml','autoDeploy':False,'token':None}
        assert request(cls.admin,cls.path,'POST',cls.config)[0]==200
    def test_01_authentication_required(self):
        self.assertEqual(401,request(client(),self.path)[0])
        self.assertEqual(401,request(client(),'/api/health',headers={'X-Orbit-Token':'invalid'})[0])
    def test_02_roles_configuration(self):
        for role in ['manager','member','viewer']:
            self.assertEqual(403,request(self.accounts[role],self.path,'POST',self.config)[0])
        for c in self.accounts.values():self.assertEqual(200,request(c,self.path)[0])
    def test_03_roles_jobs(self):
        for role in ['member','viewer']:
            self.assertEqual(403,request(self.accounts[role],self.path+'/jobs','POST',{'action':'pull'})[0])
    def test_04_validation(self):
        for changed in [{'url':'https://github.com/owner/repo.git?secret=x'},{'branch':'main\n'},{'workflow':'arbitrary.yml'},{'token':'bad\ntoken'},{'url':'https://evil.test/repo.git'}]:
            self.assertEqual(400,request(self.admin,self.path,'POST',self.config|changed)[0])
        self.assertEqual(400,request(self.admin,self.path+'/jobs','POST',{'action':'push','expectedHead':'short'})[0])
        self.assertEqual(400,request(self.admin,self.path+'/jobs','POST',{'action':'shell'})[0])
        self.assertEqual(400,request(self.admin,self.path+'/jobs','POST',{'action':'deploy','expectedHead':'a'*40})[0])
        self.assertEqual(404,request(self.admin,'/api/projects/'+str(uuid.uuid4())+'/git','POST',self.config)[0])
    def test_05_credential_encryption_and_clear(self):
        dummy='QA-'+secrets.token_hex(16)
        self.assertEqual(200,request(self.admin,self.path,'POST',self.config|{'token':dummy})[0])
        status,data,_=request(self.admin,self.path);self.assertTrue(data['repository']['hasCredential'])
        self.assertNotIn(dummy,json.dumps(data)); encrypted=sql("SELECT credential FROM git_repositories WHERE project_id='"+self.project+"'")
        self.assertNotEqual(dummy,encrypted);self.assertNotIn(dummy,encrypted)
        self.assertEqual(200,request(self.admin,self.path,'POST',self.config)[0])
        self.assertEqual(encrypted,sql("SELECT credential FROM git_repositories WHERE project_id='"+self.project+"'"))
        self.assertEqual(200,request(self.admin,self.path,'POST',self.config|{'token':''})[0])
        self.assertFalse(request(self.admin,self.path)[1]['repository']['hasCredential'])
    def test_06_queue_uniqueness_and_failure(self):
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda _:request(self.admin,self.path+'/jobs','POST',{'action':'pull'})[0],range(2)))
        self.assertEqual([202,409],sorted(results))
        self.assertEqual(409,request(self.admin,self.path,'POST',self.config)[0])
        for _ in range(40):
            jobs=request(self.admin,self.path)[1]['jobs']
            if jobs[0]['status']=='failed':break
            time.sleep(.25)
        self.assertEqual('failed',jobs[0]['status']);self.assertTrue(jobs[0]['message'])
    def test_07_proxy_origin_and_host(self):
        self.assertEqual(403,request(client(),'/api/auth/status',base=origin,headers={'Host':'evil.test'})[0])
        self.assertEqual(403,request(client(),'/api/auth/status',base=origin,headers={'Origin':'https://evil.test'})[0])
        self.assertEqual(403,request(client(),'/api/auth/status',base=origin,headers={'Sec-Fetch-Site':'cross-site'})[0])
        self.assertEqual(200,request(client(),'/api/auth/status',base=origin)[0])
        req=urllib.request.Request(origin+'/api/auth/login',data=b'{}',headers={'Content-Type':'application/json'},method='POST')
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(req)
        self.assertEqual(403,error.exception.code)
    def test_08_proxy_size_and_path(self):
        self.assertEqual(413,request(client(),'/api/auth/login','POST',{'padding':'x'*100001},base=origin)[0])
        self.assertEqual(400,request(client(),'/api/bad%20path',base=origin)[0])
    def test_09_links_use_real_issue_data(self):
        s,d,_=request(self.admin,'/api/projects/'+self.project+'/issues','POST',{'title':'Vincular commit à tarefa','status':'todo','type':'task','priority':'medium'})
        self.assertEqual(201,s);self.assertEqual('GQA-1',d['key'])
        sql("UPDATE git_repositories SET head='"+'a'*40+"', commits='[{\"sha\":\""+'a'*40+'\",\"subject\":\"GQA-1 ligação validada\"}]\'::jsonb WHERE project_id=\''+self.project+"'")
        self.assertEqual('GQA-1 ligação validada',request(self.admin,self.path)[1]['repository']['commits'][0]['subject'])

try:
    pg('initdb','-D','/tmp/pgdata','-U','orbit','-A','trust','--no-locale','--encoding=UTF8')
    pg('pg_ctl','-D','/tmp/pgdata','-l','/tmp/pg.log','-o','-p '+dbport+' -k /tmp -h 127.0.0.1 -c shared_buffers=16MB','-w','start')
    pg('createdb','-h','127.0.0.1','-p',dbport,'-U','orbit','orbit')
    pathlib.Path('/tmp/runtime.json').write_text(json.dumps({'proxyToken':token,'connectionString':'Host=127.0.0.1;Port='+dbport+';Database=orbit;Username=orbit'}))
    api_process=start(['dotnet','/tmp/api/Orbit.Api.dll'],'api');wait_api()
    web_process=start(['node','server.js'],'web','/tmp/web')
    for _ in range(80):
        try:
            if request(client(),'/api/auth/status',base=origin)[0]==200:break
        except OSError:pass
        time.sleep(.25)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Functional))
    report={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped)}
    (E/'functional.json').write_text(json.dumps(report,indent=2))
    if not result.wasSuccessful():raise RuntimeError('API/proxy cases failed')
    from hosted import run_hosted
    run_hosted(Functional,request,client,sql)
    # Startup recovery uses durable DB state. No rerun is attempted for delivery-phase recovery.
    stop(api_process)
    for phase in ['git','delivery']:
        sql("INSERT INTO git_jobs(id,project_id,actor_id,action,status,phase,head) SELECT '"+str(uuid.uuid4())+"','"+Functional.project+"',id,'deploy','running','"+phase+"','"+'a'*40+"' FROM users WHERE role='admin'")
        api_process=start(['dotnet','/tmp/api/Orbit.Api.dll'],'api-resume-'+phase);wait_api()
        for _ in range(40):
            states=json.loads(sql("SELECT json_agg(status)::text FROM git_jobs WHERE project_id='"+Functional.project+"' AND phase='"+phase+"'"))
            if all(x=='failed' for x in states):break
            time.sleep(.25)
        assert all(x=='failed' for x in states)
        stop(api_process)
    env['ORBIT_DISABLE_SETUP']='1';api_process=start(['dotnet','/tmp/api/Orbit.Api.dll'],'api-final');wait_api()
    assert request(client(),'/api/auth/setup','POST',{'name':'x','email':'x@x.test','password':password})[0]==403
    # Synthetic protected credential enables confirmation/cancel tests; no network action is executed.
    assert request(Functional.admin,Functional.path,'POST',Functional.config|{'token':'synthetic-ui-only'})[0]==200
    browser_env=env|{'ORBIT_QA_PASSWORD':password,'ORBIT_QA_PROJECT':Functional.project}
    browser=subprocess.run(['node','/tmp/qa/browser.cjs'],env=browser_env)
    assert browser.returncode==0
    report['startup_recovery']=True;report['setup_disabled']=True
    (E/'functional.json').write_text(json.dumps(report,indent=2))
finally:
    for proc in processes:
        if proc.poll() is None:stop(proc)
    for log in logs:log.close()
    if pathlib.Path('/tmp/pgdata/postmaster.pid').exists():pg('pg_ctl','-D','/tmp/pgdata','-m','fast','-w','stop')
