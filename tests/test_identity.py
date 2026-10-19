"""Real SQLite, password hashing and HTTP isolation; all identities are fixtures."""
import http.client
import json
import threading
from pathlib import Path

from localauthor.application import Application
from localauthor.errors import AccessDeniedError, AuthenticationError, ConflictError, NotFoundError, PolicyError, RateLimitError
from localauthor.identity import COOKIE_NAME
from localauthor.identity_context import current_actor
from localauthor.project_access import can_access_project
from localauthor.server import create_server
from tests.helpers import WorkspaceCase

FIXTURE_PASSPHRASE = 'Disposable laboratory passphrase 123'


class IdentityTests(WorkspaceCase):
    def setUp(self):
        super().setUp();self.app=Application(self.settings);self.identity=self.app.identity

    def tearDown(self):
        self.app.close();super().tearDown()

    def setup_owner(self):
        return self.identity.bootstrap('owner','Owner fixture',FIXTURE_PASSPHRASE,local=True)

    def test_bootstrap_preserves_history_and_claims_existing_projects_only_once(self):
        conversation=self.app.chat.create(self.project['id'],'Existing conversation')
        self.app.chat.respond(self.project['id'],conversation['id'],'Como revisar o código?')
        before=self.app.chat.get(self.project['id'],conversation['id'])['messages']
        with self.assertRaises(AccessDeniedError):self.identity.bootstrap('owner','Owner',FIXTURE_PASSPHRASE,local=False)
        owner,token=self.setup_owner()
        self.assertEqual(self.identity.current(token)['id'],owner['id'])
        self.assertEqual(self.identity.projects(owner)[0]['id'],self.project['id'])
        self.assertEqual(self.app.chat.get(self.project['id'],conversation['id'])['messages'],before)
        with self.app.store.connect() as db:
            self.assertEqual(db.execute('SELECT user_id FROM profile_conversations WHERE conversation_id=?',(conversation['id'],)).fetchone()[0],owner['id'])
        with self.assertRaises(ConflictError):self.setup_owner()

    def test_bootstrap_does_not_claim_live_jobs_or_enable_partial_setup(self):
        self.app.jobs.submit('index',{'project_id':self.project['id']})
        with self.assertRaises(ConflictError):self.setup_owner()
        self.assertFalse(self.identity.enabled)

    def test_password_hashes_salts_sessions_expiry_and_logout(self):
        owner,token=self.setup_owner()
        other=self.identity.create_user(owner,'other','Other fixture',FIXTURE_PASSPHRASE)
        with self.app.store.connect() as db:
            rows=db.execute('SELECT salt,password_hash FROM profile_users').fetchall()
            self.assertNotEqual(rows[0]['salt'],rows[1]['salt']);self.assertNotEqual(rows[0]['password_hash'],rows[1]['password_hash'])
            serialized=str([dict(r) for r in rows])+str([tuple(r) for r in db.execute('SELECT * FROM profile_sessions')])
            self.assertNotIn(FIXTURE_PASSPHRASE,serialized);self.assertNotIn(token,serialized)
            db.execute('UPDATE profile_sessions SET expires=0')
        self.assertIsNone(self.identity.current(token))
        with self.assertRaises(AuthenticationError):self.identity.login('other','wrong', 'fixture-device')
        user,session=self.identity.login('OTHER',FIXTURE_PASSPHRASE,'fixture-device')
        self.assertEqual(user['id'],other['id']);self.assertIsNotNone(self.identity.current(session))
        self.identity.logout(session);self.assertIsNone(self.identity.current(session))

    def test_login_throttling_is_persistent_and_generic(self):
        self.setup_owner()
        for _ in range(6):
            with self.assertRaises(AuthenticationError):self.identity.login('unknown','wrong','fixture-device')
        with self.assertRaises(RateLimitError):self.identity.login('unknown','wrong','fixture-device')
        from localauthor.identity import IdentityService
        reopened=IdentityService(self.app.store,self.settings.home)
        with self.assertRaises(RateLimitError):reopened.login('unknown',FIXTURE_PASSPHRASE,'fixture-device')

    def test_last_administrator_disable_reset_and_change_password(self):
        owner,session=self.setup_owner()
        with self.assertRaises(PolicyError):self.identity.update_user(owner,owner['id'],owner['name'],'user',True)
        with self.assertRaises(PolicyError):self.identity.update_user(owner,owner['id'],owner['name'],'admin',False)
        other=self.identity.create_user(owner,'other','Other',FIXTURE_PASSPHRASE)
        _,token=self.identity.login('other',FIXTURE_PASSPHRASE,'fixture')
        self.identity.update_user(owner,other['id'],'Other','user',False)
        self.assertIsNone(self.identity.current(token))
        with self.assertRaises(AuthenticationError):self.identity.login('other',FIXTURE_PASSPHRASE,'fixture')
        self.identity.change_password(owner,FIXTURE_PASSPHRASE,'Another disposable passphrase 456')
        self.assertIsNone(self.identity.current(session))
        with self.assertRaises(AuthenticationError):self.identity.login('owner',FIXTURE_PASSPHRASE,'fixture')

    def test_private_projects_explicit_sharing_and_admin_has_no_implicit_membership(self):
        owner,_=self.setup_owner();dev=self.identity.create_user(owner,'developer','Developer',FIXTURE_PASSPHRASE)
        reader=self.identity.create_user(owner,'marketing','Marketing',FIXTURE_PASSPHRASE)
        project=self.identity.add_project(dev,'Private workspace',managed=True)
        self.assertEqual([p['id'] for p in self.identity.projects(dev)],[project['id']])
        self.assertEqual(self.identity.projects(reader),[])
        with self.assertRaises(NotFoundError):self.identity.require_project(owner,project['id'])
        with self.assertRaises(AccessDeniedError):self.identity.create_user(dev,'illegal','Illegal',FIXTURE_PASSPHRASE)
        self.identity.share(dev,project['id'],reader['id'],'reader')
        self.assertEqual(self.identity.require_project(reader,project['id']),'reader')
        for action in ('write','share'):
            with self.assertRaises(AccessDeniedError):self.identity.require_project(reader,project['id'],action)
        self.identity.share(dev,project['id'],reader['id'],'editor')
        self.assertEqual(self.identity.require_project(reader,project['id'],'write'),'editor')
        with self.assertRaises(AccessDeniedError):self.identity.share(reader,project['id'],owner['id'],'editor')
        self.identity.share(dev,project['id'],reader['id'],'none')
        with self.assertRaises(NotFoundError):self.identity.require_project(reader,project['id'])

    def test_directory_alias_and_overlapping_folder_cannot_bypass_ownership(self):
        owner,_=self.setup_owner();dev=self.identity.create_user(owner,'developer','Developer',FIXTURE_PASSPHRASE)
        project=self.identity.add_project(dev,'Private workspace',managed=True)
        child=Path(project['root'])/'child';child.mkdir()
        with self.assertRaises(AccessDeniedError):self.identity.add_project(dev,'Stolen',str(self.project_root))
        with self.assertRaises(AccessDeniedError):self.identity.add_project(owner,'Other workspace',str(child))
        with self.assertRaises(ConflictError):self.identity.add_project(dev,'Nested shadow',str(child))
        with self.assertRaises(PolicyError):self.app.store.add_project('Unowned',str(self.root))

    def test_role_matrix_closes_unknown_values_and_string_subclasses(self):
        class Derived(str):pass
        roles=['owner','editor','reader','admin','OWNER','',None,True,[],{},1,Derived('owner')]
        actions=['read','write','share','delete','',None,False,[],{},Derived('read')]
        for role in roles:
            for action in actions:
                expected=type(role) is str and type(action) is str and ((role=='owner' and action in ('read','write','share')) or (role=='editor' and action in ('read','write')) or (role=='reader' and action=='read'))
                self.assertIs(can_access_project(role,action),expected)

    def test_restoring_backup_keeps_people_but_revokes_old_browser_sessions(self):
        owner,token=self.setup_owner()
        from localauthor.backup import backup_home,restore_home
        from localauthor.config import Settings
        from localauthor.identity import IdentityService
        from localauthor.store import Store
        archive=self.root/'profile-backup.zip';backup_home(self.settings,archive)
        target=self.root/'restored';restore_home(archive,target)
        restored=IdentityService(Store(target/'memory.sqlite3'),target)
        self.assertTrue(restored.enabled);self.assertIsNone(restored.current(token))
        person,new=restored.login('owner',FIXTURE_PASSPHRASE,'fixture')
        self.assertEqual(person['id'],owner['id']);self.assertIsNotNone(restored.current(new))


class IdentityHttpTests(WorkspaceCase):
    def setUp(self):
        super().setUp();self.app=Application(self.settings)
        self.owner,self.owner_token=self.app.identity.identify('Owner',local=True)
        self.dev=self.app.identity.create_named_user(self.owner,'Developer')
        _,self.dev_token=self.app.identity.identify('Developer',local=False)
        self.private=self.app.identity.add_project(self.dev,'Developer private',managed=True)
        self.server=create_server(self.app,Path(__file__).resolve().parents[1]/'ui',port=0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.app.close();super().tearDown()

    def request(self,method,path,body=None,token=None,extra=None):
        headers={'Authorization':'Bearer '+self.settings.token,'Content-Type':'application/json'}
        if token:headers['Cookie']=COOKIE_NAME+'='+token
        if extra:headers.update(extra)
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10)
        try:
            conn.request(method,path,body=None if body is None else json.dumps(body),headers=headers)
            response=conn.getresponse();raw=response.read()
            return response.status,dict(response.getheaders()),json.loads(raw) if 'json' in response.getheader('Content-Type','') else raw
        finally:conn.close()

    def test_transport_token_is_not_a_person_and_cookie_is_httponly(self):
        self.assertEqual(self.request('GET','/api/projects')[0],401)
        status,_,probe=self.request('GET','/api/health')
        self.assertEqual(status,200);self.assertEqual(probe,{'status':'ok','profile_required':True})
        self.assertEqual(self.request('GET','/api/health',extra={'Authorization':'Bearer invalid'})[0],401)
        status,_,data=self.request('GET','/api/identity/status')
        self.assertEqual(status,200);self.assertIsNone(data['user'])
        status,headers,data=self.request('POST','/api/identity/identify',{'name':'Owner'},extra={'X-LocalAuthor-Gateway':'lan','X-LocalAuthor-Device':'a'*32})
        self.assertEqual(status,200)
        for flag in ('HttpOnly','SameSite=Strict','Secure'):self.assertIn(flag,headers['Set-Cookie'])
        self.assertNotIn(FIXTURE_PASSPHRASE,json.dumps(data));self.assertNotIn('password_hash',json.dumps(data))
        self.assertEqual(self.request('GET','/api/projects',token=self.dev_token,extra={'Authorization':'Bearer invalid'})[0],401)

    def test_projects_and_statistics_are_scoped_to_the_person(self):
        status,_,rows=self.request('GET','/api/projects',token=self.dev_token)
        self.assertEqual(status,200);self.assertEqual([r['id'] for r in rows],[self.private['id']])
        rows=self.request('GET','/api/projects',token=self.owner_token)[2]
        self.assertNotIn(self.private['id'],[r['id'] for r in rows])
        self.app.store.ingest('global','fixture','Library','Only administrator library')
        stats=self.request('GET','/api/health',token=self.dev_token)[2]['stats']
        self.assertEqual(stats['projects'],1);self.assertEqual(stats['sources'],0)
        self.assertEqual(self.request('GET','/api/sources?scope=global',token=self.dev_token)[0],403)
        self.assertEqual(self.request('POST','/api/consult',{'query':'library','scope':self.private['id'],'include_global':True},self.dev_token)[0],403)

    def test_all_project_route_families_reject_cross_person_access(self):
        from localauthor.access import PROJECT_GET,PROJECT_POST
        for path in PROJECT_GET:
            status,_,data=self.request('GET',path+'?project_id='+self.project['id'],token=self.dev_token)
            self.assertEqual(status,404,(path,data));self.assertNotIn(str(self.project_root),json.dumps(data))
        for path in PROJECT_POST:
            self.assertEqual(self.request('POST',path,{'project_id':self.project['id']},self.dev_token)[0],404,path)

    def test_foreign_conversation_job_task_and_source_ids_are_not_authority(self):
        convo=self.app.chat.create(self.project['id'],'Private history')
        task=self.app.tasks.create(self.project['id'],'Private task')
        job=self.app.jobs.submit('index',{'project_id':self.project['id']})
        for path in ['/api/jobs/'+job['id'],'/api/tasks/'+task['id'],'/api/tasks/'+task['id']+'/files']:
            self.assertEqual(self.request('GET',path,token=self.dev_token)[0],404,path)
        self.assertEqual(self.request('POST','/api/jobs/'+job['id']+'/cancel',{},self.dev_token)[0],404)
        self.assertEqual(self.request('GET','/api/tasks',token=self.dev_token)[2],[])
        self.assertEqual(self.request('GET','/api/jobs',token=self.dev_token)[2],[])
        self.assertEqual(self.request('GET','/api/conversation?project_id='+self.private['id']+'&id='+convo['id'],token=self.dev_token)[0],404)
        self.assertEqual(self.request('POST','/api/projects',{'name':'Impersonation','managed':True,'owner_id':self.owner['id']},self.dev_token)[0],400)

    def test_readonly_sharing_cannot_write_or_escalate_and_revocation_is_enforced(self):
        self.app.identity.share(self.owner,self.project['id'],self.dev['id'],'reader')
        self.assertEqual(self.request('GET','/api/conversations?project_id='+self.project['id'],token=self.dev_token)[0],200)
        self.assertEqual(self.request('POST','/api/conversations',{'project_id':self.project['id'],'title':'Forbidden'},self.dev_token)[0],403)
        self.assertEqual(self.request('POST','/api/project-members',{'project_id':self.project['id'],'user_id':self.dev['id'],'role':'editor'},self.dev_token)[0],403)
        self.app.identity.share(self.owner,self.project['id'],self.dev['id'],'none')
        self.assertEqual(self.request('GET','/api/conversations?project_id='+self.project['id'],token=self.dev_token)[0],404)

    def test_author_identity_is_server_owned_and_queued_rights_are_rechecked(self):
        body={'project_id':self.private['id'],'title':'Developer conversation'}
        status,_,conversation=self.request('POST','/api/conversations',body,self.dev_token);self.assertEqual(status,200)
        body={'project_id':self.private['id'],'conversation_id':conversation['id'],'message':'Como revisar o código?','mode':'guide'}
        result=self.request('POST','/api/chat',body,self.dev_token)[2]
        self.assertEqual(result['messages'][0]['metadata']['author_id'],self.dev['id'])
        self.assertEqual(result['messages'][0]['metadata']['author_name'],'Developer')
        self.assertEqual(self.request('POST','/api/chat',{**body,'_actor_id':self.owner['id']},self.dev_token)[0],400)
        status,_,result=self.request('POST','/api/jobs/index',{'project_id':self.private['id']},self.dev_token)
        self.assertEqual(status,200);self.assertEqual(result['payload']['_actor_id'],self.dev['id'])
        self.app.identity.update_user(self.owner,self.dev['id'],'Developer','user',False)
        with self.assertRaises(AuthenticationError):self.app.jobs.handlers['index'](result['payload'],threading.Event())
        self.assertEqual(self.request('GET','/api/projects',token=self.dev_token)[0],401)

    def test_profile_changes_and_session_fixation_cannot_reuse_another_tab(self):
        status,_,data=self.request('GET','/api/projects',token=self.dev_token,extra={'X-LocalAuthor-Profile':self.owner['id']})
        self.assertEqual(status,401);self.assertTrue(data['identity_required'])
        self.assertEqual(self.request('GET','/api/projects',token=self.dev_token,extra={'Cookie':COOKIE_NAME+'='+self.dev_token+'; '+COOKIE_NAME+'='+self.owner_token})[0],401)
        self.assertIsNone(current_actor.get())

    def test_name_selection_is_explicitly_not_password_authentication(self):
        status,_,data=self.request('GET','/api/identity/status')
        self.assertEqual(status,200);self.assertEqual(data['identification'],'name')
        self.assertEqual({p['name'] for p in data['profiles']},{'Owner','Developer'})
        status,headers,data=self.request('POST','/api/identity/identify',{'name':' owner '})
        self.assertEqual(status,200);self.assertEqual(data['user']['id'],self.owner['id'])
        self.assertIn('HttpOnly',headers['Set-Cookie'])
        self.assertEqual(self.request('POST','/api/identity/identify',{'name':'Owner'},extra={'Authorization':'Bearer invalid'})[0],401)
        status,_,data=self.request('POST','/api/identity/identify',{'name':'New person'})
        self.assertEqual(status,200);self.assertEqual(data['user']['role'],'user')
        session=self.app.identity.identify('New person',local=False)[1]
        self.assertEqual(self.request('GET','/api/projects',token=session)[2],[])


class NamedProfileTests(WorkspaceCase):
    def setUp(self):
        super().setUp();self.app=Application(self.settings);self.identity=self.app.identity

    def tearDown(self):
        self.app.close();super().tearDown()

    def test_first_name_requires_server_claims_history_and_has_no_password(self):
        conversation=self.app.chat.create(self.project['id'],'Existing history')
        with self.assertRaises(AccessDeniedError):self.identity.identify('Rafa fixture',local=False)
        owner,session=self.identity.identify('Rafa fixture',local=True)
        self.assertEqual(owner['role'],'admin');self.assertEqual(self.identity.current(session)['id'],owner['id'])
        self.assertEqual(self.identity.projects(owner)[0]['id'],self.project['id'])
        with self.app.store.connect() as db:
            row=db.execute('SELECT salt,password_hash FROM profile_users').fetchone()
            self.assertEqual(tuple(row),('',''))
            self.assertEqual(db.execute('SELECT user_id FROM profile_conversations WHERE conversation_id=?',(conversation['id'],)).fetchone()[0],owner['id'])

    def test_name_matching_prevents_accidental_duplicates_and_rejects_disabled_profiles(self):
        first,_=self.identity.identify('João  Silva',local=True)
        again,token=self.identity.identify('  JOÃO Silva ',local=False)
        self.assertEqual(first['id'],again['id'])
        self.assertEqual(len(self.identity.public_profiles()),1)
        other,_=self.identity.identify('Ana fixture',local=False)
        with self.assertRaises(ConflictError):self.identity.create_named_user(first,'joão silva')
        with self.assertRaises(ConflictError):self.identity.update_user(first,other['id'],'JOÃO SILVA','user',True)
        self.identity.update_user(first,other['id'],other['name'],'user',False)
        with self.assertRaises(AccessDeniedError):self.identity.identify('Ana fixture',local=False)
        self.assertEqual(len(self.identity.public_profiles()),1)
        for invalid in ('','   ','x'*81,'Name\nOther',None,{},23):
            with self.assertRaises(PolicyError):self.identity.identify(invalid,local=True)

    def test_new_names_have_separate_workspaces_and_can_deliberately_select_existing_names(self):
        owner,_=self.identity.identify('Owner fixture',local=True)
        person,_=self.identity.identify('Person fixture',local=False)
        project=self.identity.add_project(person,'Personal project',managed=True)
        self.assertEqual(person['role'],'user');self.assertEqual(self.identity.projects(owner)[0]['id'],self.project['id'])
        self.assertNotIn(project['id'],[p['id'] for p in self.identity.projects(owner)])
        selected,_=self.identity.identify('Person fixture',local=False)
        self.assertEqual(self.identity.projects(selected)[0]['id'],project['id'])
        self.assertNotEqual(self.identity.workspace(owner),self.identity.workspace(person))

    def test_initial_selection_waits_for_queue_and_old_password_profiles_can_use_names(self):
        self.app.jobs.submit('index',{'project_id':self.project['id']})
        with self.assertRaises(ConflictError):self.identity.identify('Owner fixture',local=True)
        self.assertFalse(self.identity.enabled)
        with self.app.store.connect() as db:db.execute("UPDATE jobs SET state='cancelled'")
        owner,_=self.identity.bootstrap('legacy-owner','Legacy Owner',FIXTURE_PASSPHRASE,local=True)
        selected,_=self.identity.identify('legacy owner',local=False)
        self.assertEqual(owner['id'],selected['id'])
