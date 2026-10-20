"""Actual storage/HTTP; injected generation and research are explicit doubles."""
import hashlib
import http.client
import json
from pathlib import Path
import threading
from unittest.mock import Mock,patch

from localauthor.application import Application
from localauthor.chat_routing import choose
from localauthor.errors import PolicyError
from localauthor.server import create_server
from localauthor.util import write_json
from tests.helpers import WorkspaceCase


def publish_fixture(home):
    data=b'MZ'+b'\x00installer-test-fixture'*1024
    folder='a'*32;root=home/'lan/private-installers'/folder;root.mkdir(parents=True)
    (root/'Instalar-LocalAuthor-Conectado.exe').write_bytes(data)
    manifest={'folder':folder,'version':'0.3.10','size':len(data),'sha256':hashlib.sha256(data).hexdigest().upper()}
    write_json(home/'lan/installer-release.json',manifest)
    return data,manifest


class AutoChatTests(WorkspaceCase):
    def setUp(self):
        super().setUp();self.app=Application(self.settings);self.chat=self.app.chat
        self.conversation=self.chat.create(self.project['id'],'Automatic fixture')

    def tearDown(self):self.app.close();super().tearDown()

    def send(self,text):return self.chat.respond(self.project['id'],self.conversation['id'],text,'auto')['messages'][-1]

    def test_installer_requests_match_current_app_including_reported_typo(self):
        publish_fixture(self.settings.home)
        for text in ['chat preciso do seu instalador','chat preciso do instalar do localauthor','Me envie o instalador','onde está o instalador da LocalAuthor?']:
            with self.subTest(text=text):
                answer=self.send(text)
                self.assertEqual(answer['metadata']['origin'],'application_support')
                self.assertEqual(answer['metadata']['routing']['intent'],'installer')
                self.assertEqual(answer['metadata']['actions'][0]['url'],'/api/app/installer/file')
                self.assertIn('0.3.10',answer['content'])
                self.assertNotIn('Vamos organizar',answer['content'])

    def test_missing_installer_never_invents_a_download(self):
        answer=self.send('preciso do seu instalador')
        self.assertNotIn('actions',answer['metadata']);self.assertIn('ainda não foi publicado',answer['content'])

    def test_installer_follow_up_retains_the_current_conversation_intent(self):
        publish_fixture(self.settings.home);self.send('Preciso do instalador da LocalAuthor')
        self.assertEqual(self.send('me manda o arquivo')['metadata']['routing']['intent'],'installer')
        self.assertEqual(choose('me manda o arquivo')[0],'foundation')

    def test_research_follow_up_address_uses_requested_research_instead_of_changing_tool(self):
        history=[{'metadata':{'routing':{'intent':'research_scope'}}}]
        self.assertEqual(choose('https://docs.python.org/3/',history)[0],'research')
        self.assertEqual(choose('https://docs.python.org/3/')[0],'browser')

    def test_corrupt_installer_and_manifest_path_injection_fail_closed(self):
        _,manifest=publish_fixture(self.settings.home)
        for updates in [{'sha256':'0'*64},{'folder':'../../secrets'},{'version':'invalid'},{'size':True}]:
            with self.subTest(updates=updates):
                write_json(self.settings.home/'lan/installer-release.json',{**manifest,**updates})
                self.assertFalse(self.app.installers.status()['available'])
                self.assertNotIn('actions',self.send('Seu instalador')['metadata'])

    def test_other_app_installers_and_creation_requests_are_not_hijacked(self):
        for text in ['Quero o instalador do PostgreSQL','crie um instalador do meu sistema','Explique como criar uma imagem Docker']:
            with self.subTest(text=text):self.assertEqual(choose(text)[0],'foundation')

    def test_general_chat_uses_registered_model_history_and_project_context(self):
        self.app.store.ingest(self.project['id'],'note:stock','Estoque','Estoque local fixture')
        self.app.store.ingest('global','note:private','Estoque','Do not include global fixture')
        with patch.object(self.chat.foundation,'status',return_value={'capabilities':{'text':{'registered':True}}}),patch.object(self.chat.foundation,'answer',return_value={'origin':'foundation_text','content':'Explicit generation double','sources':[]}) as answer:
            self.send('Me explique o estoque')
            result=self.send('Como organizar o estoque?')
            self.assertEqual(result['metadata']['origin'],'foundation_text')
            self.assertEqual(result['metadata']['routing']['selected'],'foundation')
            self.assertEqual(len(answer.call_args.args[2]),2)
            self.assertTrue(answer.call_args.args[3])
            self.assertTrue(all(e['scope']==self.project['id'] for e in answer.call_args.args[3]))

    def test_unavailable_model_is_explicit_and_does_not_fall_back_to_project_script(self):
        result=self.send('Olá, pode me ajudar?')
        self.assertIn('modelo de conversa local ainda não está configurado',result['content'])
        self.assertNotIn('Vamos organizar',result['content'])

    def test_local_evidence_can_be_read_when_generation_is_unavailable(self):
        self.app.store.ingest(self.project['id'],'note:stock','Estoque','Estoque privado deste projeto')
        result=self.send('Estoque')
        self.assertEqual(result['metadata']['origin'],'retrieval_only')
        self.assertIn('privado deste projeto',result['content'])

    def test_explicit_local_sources_are_not_misrouted_to_network_research(self):
        self.assertEqual(choose('Busque na memória local os dados do projeto')[0],'knowledge')

    def test_explicit_site_investigation_selects_browser_without_mode_picker(self):
        with patch.object(self.app.browser,'start',return_value={'id':'b'*32}) as start:
            answer=self.send('Investigue as telas de https://example.org/')
            start.assert_called_once_with(self.project['id'],'https://example.org/',allow_network=True)
            self.assertEqual(answer['metadata']['routing']['selected'],'browser')
            self.assertEqual(answer['metadata']['origin'],'browser_session')

    def test_research_without_address_asks_for_missing_scope_not_a_mode(self):
        with patch.object(self.app.research,'collect') as collect,patch.object(self.app.browser,'start') as browser:
            answer=self.send('Pesquise o mercado desta empresa')
            self.assertIn('Qual site ou endereço HTTPS',answer['content'])
            self.assertFalse(answer['metadata']['researched_now']);collect.assert_not_called();browser.assert_not_called()

    def test_research_collects_only_explicit_urls_and_returns_real_evidence(self):
        def collect(urls,scope,cancel):
            self.assertEqual(urls,['https://docs.python.org/3/']);self.assertEqual(scope,self.project['id'])
            self.app.store.ingest(scope,urls[0],'Python','Python documentation fixture',kind='web')
            return [{'final_url':urls[0],'reused':False}]
        with patch.object(self.app.research,'collect',side_effect=collect):
            answer=self.send('Pesquise Python em https://docs.python.org/3/')
            self.assertEqual(answer['metadata']['origin'],'web_research');self.assertTrue(answer['metadata']['researched_now'])
            self.assertEqual(answer['metadata']['sources'][0]['url'],'https://docs.python.org/3/')
            self.assertIn('documentation fixture',answer['content'])

    def test_offline_research_is_not_reported_as_success(self):
        answer=self.send('Pesquise Python em https://docs.python.org/3/')
        self.assertFalse(answer['metadata']['researched_now']);self.assertEqual(answer['metadata']['origin'],'application_support')

    def test_code_urls_and_negated_commands_do_not_start_tools(self):
        for text in ['```js\n// abra https://example.org\nconst x = 1;\n```','Não abra https://example.org/; explique o risco']:
            with self.subTest(text=text):self.assertEqual(choose(text)[0],'foundation')

    def test_auto_memory_remains_a_persisted_memory_operation(self):
        answer=self.send('Lembre-se: prefiro respostas curtas')
        self.assertEqual(answer['metadata']['origin'],'project_memory')
        self.assertEqual(len(self.chat.memories(self.project['id'])),1)


class InstallerHttpTests(WorkspaceCase):
    def setUp(self):
        super().setUp();self.app=Application(self.settings)
        self.owner,self.session=self.app.identity.identify('Installer fixture',local=True)
        self.data,self.manifest=publish_fixture(self.settings.home)
        self.server=create_server(self.app,Path(__file__).resolve().parents[1]/'ui',port=0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()

    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.app.close();super().tearDown()

    def get(self,path,*,token=True,profile=True):
        headers={}
        if token:headers['Authorization']='Bearer '+self.settings.token
        if profile:headers['Cookie']='la_profile='+self.session
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        connection.request('GET',path,headers=headers);response=connection.getresponse();data=response.read();result=response.status,dict(response.getheaders()),data;connection.close();return result

    def test_download_requires_transport_and_selected_profile(self):
        self.assertEqual(self.get('/api/app/installer/file',token=False)[0],401)
        self.assertEqual(self.get('/api/app/installer/file',profile=False)[0],401)

    def test_download_is_integrity_checked_attachment_with_exact_bytes(self):
        status,headers,data=self.get('/api/app/installer/file')
        self.assertEqual(status,200);self.assertEqual(data,self.data)
        self.assertIn('attachment;',headers['Content-Disposition']);self.assertEqual(headers['X-Content-Sha256'],self.manifest['sha256'])
        status,_,raw=self.get('/api/app/installer');metadata=json.loads(raw)
        self.assertTrue(metadata['available']);self.assertNotIn('folder',metadata);self.assertNotIn('AccessKey',raw.decode())

    def test_download_rejects_paths_and_corruption(self):
        self.assertEqual(self.get('/api/app/installer/file?path=../../api.token')[0],400)
        path=self.settings.home/'lan/private-installers'/self.manifest['folder']/'Instalar-LocalAuthor-Conectado.exe'
        path.write_bytes(b'MZ corrupted')
        self.assertEqual(self.get('/api/app/installer/file')[0],400)
