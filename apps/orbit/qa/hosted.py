"""Real smart-HTTP Git clients against disposable PostgreSQL/API in the sandbox."""
import base64,http.client,json,os,pathlib,secrets,subprocess,time,unittest,urllib.request,urllib.error,urllib.parse,uuid

def run_hosted(fixture,request,client,sql):
    api='http://127.0.0.1:5088'; root=pathlib.Path('/tmp/hosted-clients');root.mkdir()
    path='/api/projects/'+fixture.project+'/repository'
    def api_call(role,suffix='',method='GET',body=None):
        return request(fixture.accounts[role],path+suffix,method,body)
    def git(directory,*args,access=None,success=True):
        env=os.environ.copy();env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_TERMINAL_PROMPT='0',GIT_ASKPASS='/bin/false')
        env['GIT_CONFIG_COUNT']='2' if access else '1';env['GIT_CONFIG_KEY_0']='credential.helper';env['GIT_CONFIG_VALUE_0']=''
        if access:
            env['GIT_CONFIG_KEY_1']='http.extraHeader';env['GIT_CONFIG_VALUE_1']='Authorization: Basic '+base64.b64encode(access.encode()).decode()
        r=subprocess.run(['/usr/bin/git','-c','core.hooksPath=/dev/null',*args],cwd=directory,env=env,capture_output=True,text=True,input='',timeout=30)
        if success and r.returncode:raise AssertionError('Git client operation failed: '+args[0])
        if not success and not r.returncode:raise AssertionError('Forbidden Git operation unexpectedly succeeded')
        return r.stdout.strip()
    def raw(url,auth=None,method='GET',body=None,headers=None):
        hs={} if auth is None else {'Authorization':'Basic '+base64.b64encode(auth.encode()).decode()}
        hs.update(headers or {})
        try:r=urllib.request.urlopen(urllib.request.Request(url,method=method,data=body,headers=hs),timeout=20)
        except urllib.error.HTTPError as e:r=e
        status=r.status;r.read();return status
    class Hosted(unittest.TestCase):
        def test_01_creation_permissions_and_persistence(self):
            self.assertFalse(api_call('admin')[1]['exists'])
            for role in ['member','viewer']:self.assertEqual(403,api_call(role,method='POST')[0])
            self.assertEqual(201,api_call('manager',method='POST')[0])
            self.assertEqual(409,api_call('admin',method='POST')[0])
            d=api_call('viewer')[1];self.assertTrue(d['exists']);self.assertEqual('',d['head']);self.assertEqual([],d['entries'])
            Hosted.url=api+d['clonePath'];Hosted.repo=pathlib.Path('/tmp/repos/hosted')/(fixture.project+'.git')
        def test_02_project_tokens_hashed_and_scoped(self):
            self.assertEqual(403,api_call('viewer','/tokens','POST',{'label':'No write','write':True})[0])
            self.assertEqual(400,api_call('member','/tokens','POST',{'label':'\n','write':False})[0])
            for role,write in [('member',True),('viewer',False)]:
                s,d,_=api_call(role,'/tokens','POST',{'label':'Cliente QA','write':write});self.assertEqual(201,s)
                setattr(Hosted,role+'_token',d['token']);setattr(Hosted,role+'_token_id',d['id'])
                self.assertNotIn(d['token'],sql("SELECT hash FROM hosted_tokens WHERE id='"+d['id']+"'"))
                self.assertNotIn(d['token'],json.dumps(api_call(role,'/tokens')[1]))
            Hosted.writer='member@orbit.test:'+Hosted.member_token;Hosted.reader='viewer@orbit.test:'+Hosted.viewer_token
            status,read_member,_=api_call('member','/tokens','POST',{'label':'Colaborador sem push','write':False})
            self.assertEqual(201,status)
            self.assertEqual(403,raw(api+'/git/'+fixture.project+'.git/info/refs?service=git-receive-pack','member@orbit.test:'+read_member['token']))
            self.assertEqual(0,len(api_call('admin','/tokens')[1]))
            other=request(fixture.admin,'/api/projects','POST',{'key':'HQ2','name':'ZZZ Escopo Git QA'})[1]['id']
            self.assertEqual(201,request(fixture.admin,'/api/projects/'+other+'/repository','POST')[0])
            self.assertEqual(403,raw(api+'/git/'+other+'.git/info/refs?service=git-upload-pack',Hosted.writer))
        def test_03_private_clone_and_invalid_protocol(self):
            self.assertEqual(401,raw(Hosted.url+'/info/refs?service=git-upload-pack'))
            self.assertEqual(401,raw(Hosted.url+'/info/refs?service=git-upload-pack','member@orbit.test:wrong'))
            for endpoint in ['/HEAD','/objects/info/alternates','/info/refs?service=git-upload-pack&extra=x']:
                self.assertEqual(400,raw(Hosted.url+endpoint,Hosted.writer))
            self.assertEqual(403,raw(Hosted.url+'/info/refs?service=git-receive-pack',Hosted.reader))
            git(root,'clone',Hosted.url,'writer',access=Hosted.writer)
            Hosted.work=root/'writer';git(Hosted.work,'config','user.name','QA Synthetic');git(Hosted.work,'config','user.email','qa@orbit.test')
        def test_04_real_push_browse_and_task_link(self):
            (Hosted.work/'README.md').write_text('    Olá Orbit — arquivo real.\n<script>not executed</script>\n',encoding='utf-8')
            (Hosted.work/'xss.txt').write_text('<script>globalThis.orbitUnsafePreview=true</script>\n',encoding='utf-8')
            (Hosted.work/'src').mkdir();(Hosted.work/'src'/'example.cs').write_text('// QA only; never execute\n',encoding='utf-8')
            (Hosted.work/'large.txt').write_text('x'*17000)
            git(Hosted.work,'add','.');git(Hosted.work,'commit','-m','GQA-1 primeiro código hospedado')
            git(Hosted.work,'push','origin','main',access=Hosted.writer)
            Hosted.first=git(Hosted.work,'rev-parse','HEAD')
            d=api_call('viewer')[1];self.assertEqual(Hosted.first,d['head']);self.assertEqual(['main'],d['branches']);self.assertIn('GQA-1',d['commits'][0]['subject'])
            Hosted.entries=d['entries'];readme=next(x for x in d['entries'] if x['name']=='README.md')
            s,obj,_=api_call('viewer','/object','POST',{'sha':readme['sha'],'type':'blob'});self.assertEqual(200,s);self.assertEqual((Hosted.work/'README.md').read_text(),obj['text'])
            tree=next(x for x in d['entries'] if x['type']=='tree');self.assertEqual(200,api_call('member','/object','POST',{'sha':tree['sha'],'type':'tree'})[0])
            large=next(x for x in d['entries'] if x['name']=='large.txt');self.assertEqual(400,api_call('admin','/object','POST',{'sha':large['sha'],'type':'blob'})[0])
            self.assertIn('operação Git',sql("SELECT action FROM audit ORDER BY id DESC LIMIT 1"))
        def test_05_clone_pull_and_new_branch(self):
            git(root,'clone',Hosted.url,'reader',access=Hosted.reader);reader=root/'reader'
            self.assertEqual(Hosted.first,git(reader,'rev-parse','HEAD'))
            git(Hosted.work,'checkout','-b','feature/qa');(Hosted.work/'new.txt').write_text('segundo commit')
            git(Hosted.work,'add','.');git(Hosted.work,'commit','-m','GQA-1 branch funcional');git(Hosted.work,'push','origin','feature/qa',access=Hosted.writer)
            self.assertIn('feature/qa',api_call('viewer')[1]['branches'])
            git(Hosted.work,'checkout','main');(Hosted.work/'README.md').write_text('Atualizado pelo Git real\n')
            git(Hosted.work,'add','.');git(Hosted.work,'commit','-m','GQA-1 atualização');git(Hosted.work,'push','origin','main',access=Hosted.writer)
            git(reader,'pull','--ff-only',access=Hosted.reader);self.assertEqual(git(Hosted.work,'rev-parse','HEAD'),git(reader,'rev-parse','HEAD'))
        def test_06_readonly_force_and_delete_rejections(self):
            git(Hosted.work,'push','origin','main',access=Hosted.reader,success=False)
            git(Hosted.work,'push','origin',Hosted.first+':main','--force',access=Hosted.writer,success=False)
            git(Hosted.work,'push','origin',':main',access=Hosted.writer,success=False)
        def test_07_tokens_revocation_expiry_user_and_role(self):
            self.assertEqual(404,api_call('admin','/tokens/'+Hosted.viewer_token_id+'/revoke','POST')[0])
            self.assertEqual(200,api_call('viewer','/tokens/'+Hosted.viewer_token_id+'/revoke','POST')[0])
            self.assertEqual(401,raw(Hosted.url+'/info/refs?service=git-upload-pack',Hosted.reader))
            sql("UPDATE users SET role='viewer' WHERE email='member@orbit.test'")
            self.assertEqual(403,raw(Hosted.url+'/info/refs?service=git-receive-pack',Hosted.writer))
            sql("UPDATE users SET active=false WHERE email='member@orbit.test'")
            self.assertEqual(401,raw(Hosted.url+'/info/refs?service=git-upload-pack',Hosted.writer))
            sql("UPDATE users SET role='member',active=true WHERE email='member@orbit.test'")
            sql("UPDATE hosted_tokens SET expires_at=now()-interval '1 day' WHERE id='"+Hosted.member_token_id+"'")
            self.assertEqual(401,raw(Hosted.url+'/info/refs?service=git-upload-pack',Hosted.writer))
            sql("UPDATE hosted_tokens SET expires_at=now()+interval '1 day' WHERE id='"+Hosted.member_token_id+"'")
        def test_08_reachability_types_and_body_limits(self):
            unreachable=git(Hosted.repo,'hash-object','-w','--stdin',success=True) # empty unreferenced blob
            for sha,kind in [('a'*40,'blob'),(unreachable,'blob'),('../config','blob'),(Hosted.first,'blob')]:
                self.assertEqual(400,api_call('viewer','/object','POST',{'sha':sha,'type':kind})[0])
            self.assertEqual(400,raw(Hosted.url+'/git-receive-pack',Hosted.writer,'POST',b'',{'Content-Type':'application/json'}))
            # A server may reject the declared length before reading any body.
            # Sending 20 MiB eagerly with urllib then reports BrokenPipe instead
            # of exposing that response. Read the real early HTTP rejection.
            u=urllib.parse.urlsplit(Hosted.url+'/git-receive-pack');connection=http.client.HTTPConnection(u.hostname,u.port,timeout=20)
            try:
                connection.putrequest('POST',u.path)
                connection.putheader('Authorization','Basic '+base64.b64encode(Hosted.writer.encode()).decode())
                connection.putheader('Content-Type','application/x-git-receive-pack-request')
                connection.putheader('Content-Length',str(20*1024*1024+1));connection.endheaders()
                response=connection.getresponse();self.assertEqual(413,response.status);response.read()
            finally:connection.close()
        def test_09_hooks_do_not_execute(self):
            hook=Hosted.repo/'hooks'/'pre-receive';hook.write_text('#!/bin/sh\ntouch /tmp/forbidden-hook-executed\n');hook.chmod(0o755)
            (Hosted.work/'hooks-check.txt').write_text('static QA')
            git(Hosted.work,'add','.');git(Hosted.work,'commit','-m','GQA-1 hooks desativados');git(Hosted.work,'push','origin','main',access=Hosted.writer)
            self.assertFalse(pathlib.Path('/tmp/forbidden-hook-executed').exists())
            self.assertEqual('true',git(Hosted.repo,'config','receive.denyNonFastForwards'))
            self.assertEqual('/dev/null',git(Hosted.repo,'config','core.hooksPath'))
        def test_09b_empty_commit_subject_remains_readable(self):
            git(Hosted.work,'commit','--allow-empty','--allow-empty-message','-m','')
            git(Hosted.work,'push','origin','main',access=Hosted.writer)
            status,data,_=api_call('viewer')
            self.assertEqual(200,status)
            self.assertEqual(git(Hosted.work,'rev-parse','HEAD'),data['head'])
            self.assertEqual('',data['commits'][0]['subject'])
        def test_09c_cancelled_upload_releases_single_writer(self):
            u=urllib.parse.urlsplit(Hosted.url+'/git-upload-pack')
            connection=http.client.HTTPConnection(u.hostname,u.port,timeout=5)
            try:
                connection.putrequest('POST',u.path)
                connection.putheader('Authorization','Basic '+base64.b64encode(Hosted.writer.encode()).decode())
                connection.putheader('Content-Type','application/x-git-upload-pack-request')
                connection.putheader('Content-Length','8')
                connection.putheader('Expect','100-continue');connection.endheaders()
                # Reading the body emits 100 Continue only after acquiring the
                # writer. Polling GET before that could itself win the gate and
                # reject the upload, producing a fixture race rather than a
                # cancellation failure. Await the real protocol handshake.
                interim=b''
                while b'\r\n\r\n' not in interim:
                    chunk=connection.sock.recv(1024)
                    self.assertTrue(chunk,'Upload ended before the continue handshake')
                    interim+=chunk
                    self.assertLessEqual(len(interim),8192)
                self.assertIn(b' 100 Continue\r\n',interim)
                self.assertEqual(409,raw(Hosted.url+'/info/refs?service=git-upload-pack',Hosted.writer))
            finally:connection.close()
            for _ in range(40):
                status=raw(Hosted.url+'/info/refs?service=git-upload-pack',Hosted.writer)
                if status==200:break
                self.assertEqual(409,status);time.sleep(.05)
            self.assertEqual(200,status,'Client cancellation must release the Git worker')
        def test_10_public_git_requests_are_rate_limited(self):
            statuses=[raw(Hosted.url+'/info/refs?service=git-upload-pack') for _ in range(125)]
            self.assertIn(401,statuses);self.assertIn(429,statuses)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Hosted))
    report={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'real_smart_http_git':True}
    pathlib.Path('/tmp/evidence/hosted.json').write_text(json.dumps(report,indent=2))
    if not result.wasSuccessful():raise RuntimeError('Hosted repository checks failed')
