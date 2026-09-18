import hashlib
import json
from unittest.mock import patch

from tests.helpers import WorkspaceCase
from localauthor.browser_workspace import BrowserWorkspace
from localauthor.browser_reasoner import reason
from localauthor.errors import PolicyError, NotFoundError


class BrowserWorkspaceTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.browser = BrowserWorkspace(self.settings, self.store)

    def session(self):
        with patch('localauthor.browser_workspace.selected_models', return_value={}), patch.object(self.browser, '_run'):
            row = self.browser.start(self.project['id'], 'https://example.org/', True)
        self.item = self.browser.sessions[row['id']]
        self.item['thread'].join()
        self.item['row'].update(state='ready', frames=[{'number':1,'snapshot':'current', 'loginAvailable':True,
            'controls':[{'id':'link-0','safe':True}], 'file':'001.png','sha256':hashlib.sha256(b'png').hexdigest()}])
        (self.browser._path(row['id'])/'001.png').write_bytes(b'png')
        self.browser._save(self.item['row'])
        return row['id']

    def test_network_and_scope_are_explicit(self):
        with self.assertRaises(PolicyError): self.browser.start(self.project['id'],'https://example.org/')
        with self.assertRaises(PolicyError): self.browser.start(self.project['id'],'http://127.0.0.1/',True)
        with self.assertRaises(PolicyError): self.browser.start(self.project['id'],'https://example.org/',True,['a/b'])
        ident = self.session()
        other_root=self.root/'other'; other_root.mkdir()
        other = self.store.add_project('Other',str(other_root))
        with self.assertRaises(NotFoundError): self.browser.get(other['id'],ident)
        with self.assertRaises(NotFoundError): self.browser.image(other['id'],ident,1)
        with self.assertRaises(NotFoundError): self.browser.get(self.project['id'],'../escape')

    def test_stale_and_unobserved_controls_never_enter_queue(self):
        ident=self.session()
        for command in ({'action':'link','snapshot':'old','target':'link-0'},
                        {'action':'link','snapshot':'current','target':'unknown'},
                        {'action':'delete','snapshot':'current'},
                        {'action':'capture','snapshot':'current','password':'not-accepted'}):
            with self.assertRaises(PolicyError): self.browser.act(self.project['id'],ident,command)
        self.assertTrue(self.item['queue'].empty())

    def test_login_secret_is_ephemeral_and_busy_rejects_second_action(self):
        ident=self.session()
        secret='fictional-test-only-19'
        self.browser.act(self.project['id'],ident,{'action':'login','snapshot':'current','username':'test@example.test','password':secret})
        saved=(self.browser._path(ident)/'session.json').read_text(encoding='utf-8')
        self.assertNotIn(secret,saved)
        self.assertNotIn('test@example.test',saved)
        with self.assertRaises(PolicyError): self.browser.act(self.project['id'],ident,{'action':'capture','snapshot':'current'})
        self.assertEqual(self.item['queue'].get_nowait()['password'],secret)
        self.browser.act(self.project['id'],ident,{'action':'stop'})
        self.assertTrue(self.item['stop'].is_set())

    def test_history_survives_restart_but_browser_does_not_resume(self):
        ident=self.session()
        recovered=BrowserWorkspace(self.settings,self.store)
        self.assertEqual(recovered.get(self.project['id'],ident)['state'],'interrupted')
        self.assertEqual(recovered.sessions,{})
        self.assertTrue(recovered.image(self.project['id'],ident,1)['data'].startswith('data:image/png;base64,'))
        (recovered._path(ident)/'001.png').write_bytes(b'changed')
        with self.assertRaises(PolicyError): recovered.image(self.project['id'],ident,1)

    def test_model_proposal_requires_available_safe_candidate(self):
        class Model:
            def __init__(self, result): self.result=result
            def predict(self, *args): return self.result
        class Policy:
            def predict(self, state): return 'OPEN_1' if state['recorded'] else 'RECORD'
        observation={'accessible':True,'loading':False,'title':'Produtos','headings':[],
                     'controls':[{'id':'danger','name':'Excluir','safe':False,'visited':False}]}
        result=reason(observation,Policy(),Model({'label':'navigation','score':1}),Model({'label':'catalog'}))
        self.assertIsNone(result['target'])
        observation['controls'][0]['safe']=True
        result=reason(observation,Policy(),Model({'label':'mutation','score':1}),Model({'label':'catalog'}))
        self.assertIsNone(result['target'])
