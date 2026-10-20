import http.client
import json
from pathlib import Path
import threading
import uuid

from localauthor.application import Application
from localauthor.server import create_server
from tests.helpers import WorkspaceCase


class RecoveryHttpTests(WorkspaceCase):
    def setUp(self):
        super().setUp();self.app=Application(self.settings)
        self.owner,self.session=self.app.identity.identify('HTTP owner fixture',local=True)
        self.other,self.other_session=self.app.identity.identify('Other fixture',local=False)
        self.server=create_server(self.app,Path(__file__).resolve().parents[1]/'ui',port=0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()

    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.app.close();super().tearDown()

    def request(self,path,body=None,session='owner',token=True):
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+self.settings.token
        chosen=self.session if session=='owner' else self.other_session if session=='other' else None
        if chosen:headers['Cookie']='la_profile='+chosen
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=8)
        try:
            conn.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,headers)
            result=conn.getresponse();raw=result.read();return result.status,json.loads(raw)
        finally:conn.close()

    def draft(self,**updates):
        return {'project_id':self.project['id'],'conversation_id':'','text':'Código "ação"\n// original','mode':'guide','revision':0,'pending':None,**updates}

    def test_transport_and_profile_are_required_and_blank_conversation_is_valid(self):
        path='/api/chat-draft?project_id='+self.project['id']+'&conversation_id='
        self.assertEqual(self.request(path,token=False)[0],401)
        self.assertEqual(self.request(path,session=None)[0],401)
        self.assertEqual(self.request(path,session='other')[0],404)
        self.assertEqual(self.request('/api/chat-workspace',session='other')[1],{'selection':None})
        self.assertEqual(self.request(path)[1]['revision'],0)
        self.assertEqual(self.request('/api/chat-draft',self.draft())[0],200)
        self.assertEqual(self.request(path)[1]['text'],self.draft()['text'])
        self.assertEqual(self.request('/api/chat-draft',self.draft(text='stale'))[0],409)

    def test_workspace_and_draft_fields_cannot_inject_another_actor_or_conversation(self):
        self.assertEqual(self.request('/api/chat-draft',self.draft(_actor_id=self.other['id']))[0],400)
        self.assertEqual(self.request('/api/chat-workspace',{'project_id':self.project['id'],'conversation_id':uuid.uuid4().hex})[0],404)
        self.assertEqual(self.request('/api/chat-workspace',{'project_id':self.project['id'],'conversation_id':''})[0],200)
        self.assertEqual(self.request('/api/chat-workspace')[1]['selection']['project_id'],self.project['id'])
        self.assertEqual(self.request('/api/chat-workspace',{'project_id':self.project['id'],'conversation_id':''},session='other')[0],404)

    def test_acceptance_response_can_be_retried_without_duplicate_conversation_or_job(self):
        conversation_id=uuid.uuid4().hex;request_id=uuid.uuid4().hex
        body={'project_id':self.project['id'],'id':conversation_id,'title':'Only once'}
        self.assertEqual(self.request('/api/conversations',body)[0],200)
        self.assertEqual(self.request('/api/conversations',body)[0],200)
        body={'project_id':self.project['id'],'conversation_id':conversation_id,'request_id':request_id,'message':'Como revisar o código?','mode':'guide','input_format':'auto'}
        status,first=self.request('/api/chat',body);self.assertEqual(status,200)
        status,again=self.request('/api/chat',body);self.assertEqual(status,200);self.assertEqual(first['job']['id'],again['job']['id'])
        self.assertEqual(self.request('/api/chat',{**body,'message':'Changed'})[0],409)
        self.assertEqual(self.request('/api/chat',{**body,'request_id':None})[0],400)
        self.assertEqual(self.request('/api/chat-request?project_id='+self.project['id']+'&request_id='+request_id)[1]['state'],'queued')
        self.assertEqual(len(self.app.chat.conversations(self.project['id'])),1)
        self.assertEqual(len(self.app.jobs.list()),1)

    def test_no_request_lookup_can_see_a_receipt_from_another_profile(self):
        ident=uuid.uuid4().hex;conversation=self.request('/api/conversations',{'project_id':self.project['id'],'title':'Owner'})[1]
        self.request('/api/chat',{'project_id':self.project['id'],'conversation_id':conversation['id'],'request_id':ident,'message':'Como testar?','mode':'guide'})
        self.app.identity.share(self.owner,self.project['id'],self.other['id'],'editor')
        self.assertEqual(self.request('/api/chat-request?project_id='+self.project['id']+'&request_id='+ident,session='other')[0],404)
        self.assertEqual(self.request('/api/chat-draft?project_id='+self.project['id']+'&conversation_id=',session='other')[1]['text'],'')

    def test_unknown_request_and_invalid_draft_fail_without_side_effects(self):
        ident=uuid.uuid4().hex
        self.assertEqual(self.request('/api/chat-request?project_id='+self.project['id']+'&request_id='+ident)[0],404)
        self.assertEqual(self.request('/api/chat-draft',self.draft(pending={'request_id':ident}))[0],400)
        self.assertEqual(self.app.jobs.list(),[])
        self.assertEqual(self.request('/api/chat-draft?project_id='+self.project['id']+'&conversation_id=')[1]['revision'],0)
