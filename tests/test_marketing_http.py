"""Real local HTTP routing/authentication; no Meta or model quality claims."""
import http.client
import json
import threading
from pathlib import Path
from tests.helpers import WorkspaceCase
from localauthor.application import Application
from localauthor.server import create_server


class MarketingHttpTests(WorkspaceCase):
    def setUp(self):
        super().setUp();self.app=Application(self.settings)
        self.server=create_server(self.app,Path(__file__).resolve().parents[1]/'ui',port=0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.app.close();super().tearDown()
    def request(self,path,body=None,auth=True):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10)
        headers={'Authorization':'Bearer '+self.settings.token} if auth else {}
        if body is not None:headers['Content-Type']='application/json'
        conn.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,headers)
        response=conn.getresponse();raw=response.read();conn.close()
        return response.status,json.loads(raw)
    def test_marketing_routes_require_authentication(self):
        for route in ['campaigns','channels','deliveries','export']:
            with self.subTest(route=route):self.assertEqual(self.request('/api/marketing/'+route+'?project_id='+self.project['id'],auth=False)[0],401)
    def test_creation_and_generation_require_project_and_explicit_choice(self):
        brief={'brand':'Marca','audience':'Lojistas','objective':'Demonstração','destination':'https://example.com/','channels':['facebook']}
        status,c=self.request('/api/marketing/campaigns',{'project_id':self.project['id'],'brief':brief});self.assertEqual(status,200)
        status,error=self.request('/api/marketing/generate',{'project_id':self.project['id'],'id':c['id'],'digest':c['digest']})
        self.assertEqual(status,400);self.assertIn('Escolha',error['error']);self.assertFalse(self.app.jobs.list())
        self.assertEqual(self.request('/api/marketing/campaign?project_id=missing&id='+c['id'])[0],404)
    def test_ui_assets_available_with_csp(self):
        for path in ['/marketing','/marketing.js','/marketing.css']:
            conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
            conn.request('GET',path);response=conn.getresponse();response.read()
            self.assertEqual(response.status,200);self.assertIn("script-src 'self'",response.getheader('Content-Security-Policy'));conn.close()
    def test_extra_credential_field_is_rejected_before_persisting_a_job(self):
        brief={'brand':'Marca','audience':'Lojistas','objective':'Demonstração','destination':'https://example.com/','channels':['facebook']}
        _,campaign=self.request('/api/marketing/campaigns',{'project_id':self.project['id'],'brief':brief})
        body={'project_id':self.project['id'],'id':campaign['id'],'digest':campaign['digest'],'token':'synthetic-never-persist'}
        for endpoint,extra in [('plan',{'candidates':[]}),('research',{'plan':[]}),('generate',{})]:
            status,result=self.request('/api/marketing/'+endpoint,{**body,**extra})
            self.assertEqual(status,400);self.assertNotIn(body['token'],json.dumps(result))
        self.assertFalse(self.app.jobs.list())
