import threading
import hashlib
from unittest.mock import patch
from localauthor.application import Application
from localauthor.errors import PolicyError, NotFoundError
from localauthor.util import write_json
from localauthor.nn.tokenizer import ByteTokenizer
from types import SimpleNamespace
from unittest.mock import Mock
from tests.helpers import WorkspaceCase


class ChatTests(WorkspaceCase):
    def test_browser_mode_records_session_without_claiming_completion(self):
        with patch.object(self.app.browser, 'start', return_value={'id':'a'*32}) as start:
            result=self.chat.respond(self.project['id'],self.conversation['id'],'Investigue https://example.org/','browser')
            start.assert_called_once_with(self.project['id'],'https://example.org/',allow_network=True)
            self.assertEqual(result['messages'][-1]['metadata']['browser_session_id'],'a'*32)
            self.assertIn('Não garante',result['messages'][-1]['metadata']['notice'])
        with self.assertRaises(PolicyError):
            self.chat.respond(self.project['id'],self.conversation['id'],'https://a.test/ https://b.test/','browser')

    def setUp(self):
        super().setUp()
        self.app = Application(self.settings)
        self.chat = self.app.chat
        self.conversation = self.chat.create(self.project['id'], 'Discussão do produto')

    def test_project_isolation_and_persistence(self):
        other_root = self.root/'other'; other_root.mkdir()
        other = self.store.add_project('Outro', str(other_root))
        with self.assertRaises(NotFoundError):
            self.chat.respond(other['id'], self.conversation['id'], 'olá')
        result = self.chat.respond(self.project['id'], self.conversation['id'], 'clean code')
        self.assertEqual(len(result['messages']), 2)
        reopened = Application(self.settings)
        self.assertEqual(len(reopened.chat.get(self.project['id'], self.conversation['id'])['messages']), 2)
        self.assertEqual(reopened.chat.conversations(other['id']), [])

    def test_guide_honestly_identifies_origin_and_project_rules(self):
        self.chat.save_preferences(self.project['id'], 'scrum', 4, 'Aceite específico revisado.')
        result = self.chat.respond(self.project['id'], self.conversation['id'], 'pesquisar boas práticas')
        message = result['messages'][-1]
        self.assertEqual(message['metadata']['origin'], 'project_guide')
        self.assertFalse(message['metadata']['researched_now'])
        self.assertIn('Aceite específico revisado.', message['content'])

    def test_retrieval_does_not_leak_global_or_other_projects(self):
        self.store.ingest('global', 'note:private', 'Mercadoria', 'Mercadoria global confidencial')
        self.store.ingest(self.project['id'], 'note:local', 'Mercadoria', 'Mercadoria deste projeto')
        result = self.chat.respond(self.project['id'], self.conversation['id'], 'Mercadoria', 'knowledge')
        self.assertIn('deste projeto', result['messages'][-1]['content'])
        self.assertNotIn('confidencial', result['messages'][-1]['content'])

    def test_usability_guidance_distinguishes_actions_navigation_and_evidence(self):
        result = self.chat.respond(self.project['id'], self.conversation['id'],
                                   'Como tornar a interface intuitiva para pessoas leigas?')
        message = result['messages'][-1]
        self.assertEqual(message['metadata']['origin'], 'project_guide')
        self.assertFalse(message['metadata']['researched_now'])
        for expected in ['botão nativo', 'link com href', 'preserve o texto',
                         'pessoas leigas', 'não evidência de aprendizado neural']:
            self.assertIn(expected, message['content'])

    def test_secret_empty_and_invalid_mode_not_stored(self):
        for text, mode in [(self.settings.token, 'model'), ('password="superprivate123"', 'guide'), ('', 'guide'), ('hello', 'exec')]:
            with self.subTest(mode=mode), self.assertRaises(PolicyError):
                self.chat.respond(self.project['id'], self.conversation['id'], text, mode)
        self.assertEqual(self.chat.get(self.project['id'], self.conversation['id'])['messages'], [])

    def test_model_failure_does_not_save_half_a_turn(self):
        with patch.object(self.chat, '_generate', side_effect=PolicyError('not ready')):
            with self.assertRaises(PolicyError):
                self.chat.respond(self.project['id'], self.conversation['id'], 'hello', 'model')
        self.assertEqual(self.chat.get(self.project['id'], self.conversation['id'])['messages'], [])

    def test_model_preserves_prompt_whitespace(self):
        prompt = 'Review code\nJSON:\n'
        with patch.object(self.chat, '_generate', return_value={'content':'{}','origin':'local_model'}) as generate:
            result = self.chat.respond(self.project['id'], self.conversation['id'], prompt, 'model')
        generate.assert_called_once_with(prompt)
        self.assertEqual(result['messages'][0]['content'], prompt)

    def test_cancelled_model_does_not_save_messages(self):
        cancel = threading.Event()
        def generate(_):
            cancel.set()
            return {'content':'late answer','origin':'local_model'}
        with patch.object(self.chat, '_generate', side_effect=generate), self.assertRaises(PolicyError):
            self.chat.respond(self.project['id'], self.conversation['id'], 'hello', 'model', cancel)
        self.assertEqual(self.chat.get(self.project['id'], self.conversation['id'])['messages'], [])

    def test_quota_rolls_back_both_messages(self):
        self.settings.max_store_bytes = 10
        with self.assertRaises(PolicyError):
            self.chat.respond(self.project['id'], self.conversation['id'], 'qualidade')
        self.assertEqual(self.chat.get(self.project['id'], self.conversation['id'])['messages'], [])

    def test_preferences_reject_invalid_values(self):
        for method,wip in [('other',3),('scrum',0),('kanban',True)]:
            with self.assertRaises(PolicyError):
                self.chat.save_preferences(self.project['id'],method,wip,'Pronto')

    def test_code_roundtrip_preserves_comments_unicode_and_crlf(self):
        source = '\t// Ação: "não alterar"\r\nstring s = @"C:\\Projetos\\app";  \r\n/* literal */\r\n// `${nome}` &lt; <textarea> 😃 e\u0301\r\n'
        result = self.chat.respond(self.project['id'], self.conversation['id'], source, input_format='code')
        self.assertEqual(result['messages'][0]['content'], source)
        self.assertEqual(result['messages'][0]['metadata']['format'], 'code')
        reopened = Application(self.settings)
        self.assertEqual(reopened.chat.get(self.project['id'], self.conversation['id'])['messages'][0]['content'].encode(), source.encode())

    def test_invalid_unicode_and_overflow_are_rejected_not_truncated(self):
        for source,mode in [('x'*8001,'guide'), ('á'*91,'model'), ('\ud800','guide')]:
            with self.subTest(mode=mode), self.assertRaises(PolicyError):
                self.chat.respond(self.project['id'], self.conversation['id'], source, mode)
        self.assertEqual(self.chat.get(self.project['id'], self.conversation['id'])['messages'], [])

    def test_generator_rejects_invalid_utf8_and_marks_token_limit(self):
        checkpoint=self.settings.home/'models/candidate.npz'
        write_json(self.settings.home/'exports/engineering-report.json', {'state':'evaluated','selectedCheckpoint':str(checkpoint)})
        write_json(self.settings.home/'exports/communication-report.json', {'state':'evaluated','chatEnabled':False,'selectedCheckpoint':'unapproved.npz'})
        model=Mock();model.config=SimpleNamespace(context_length=256)
        with patch('localauthor.nn.checkpoint.load_checkpoint',return_value=(model,None,ByteTokenizer(),None,None)):
            model.generate.return_value=[195]
            with self.assertRaises(PolicyError):
                self.chat.respond(self.project['id'],self.conversation['id'],'Olá','model')
            self.assertEqual(self.chat.get(self.project['id'],self.conversation['id'])['messages'],[])
            model.generate.return_value=[97]*220
            reply=self.chat._generate('Olá')
            self.assertTrue(reply['possibly_truncated'])
            self.assertIn('incompleta',reply['notice'])
            self.assertEqual(reply['content'],'a'*220)
            model.generate.return_value=list('Ação concluída.'.encode())
            self.assertEqual(self.chat._generate('Olá')['content'],'Ação concluída.')

    def test_chat_keeps_complete_test_longer_than_old_output_budget(self):
        checkpoint=self.settings.home/'models/candidate.npz'
        write_json(self.settings.home/'exports/engineering-report.json', {'state':'evaluated','selectedCheckpoint':str(checkpoint)})
        source='[Fact]public async Task Check(){await Client.PutAsync("/version/43",null);var r=await Client.PutAsync("/version/43",null);Assert.Equal(409,(int)r.StatusCode);}'
        model=Mock();model.config=SimpleNamespace(context_length=256)
        model.generate.side_effect=lambda prompt, max_tokens, **kw: list(source.encode())[:max_tokens]
        with patch('localauthor.nn.checkpoint.load_checkpoint',return_value=(model,None,ByteTokenizer(),None,None)):
            result=self.chat.respond(self.project['id'],self.conversation['id'],'Teste conflito','model')
        reply=result['messages'][-1]
        self.assertEqual(reply['content'],source)
        self.assertFalse(reply['metadata']['possibly_truncated'])
        self.assertIn('Assert.Equal(409',reply['content'])

    def test_functional_candidate_requires_execution_and_fault_detection(self):
        path=self.settings.home/'exports/functional-testing-report.json'
        checkpoint=self.settings.home/'models/functional.npz'
        checkpoint.parent.mkdir(exist_ok=True)
        checkpoint.write_bytes(b'qualified checkpoint fixture')
        report={'state':'evaluated','selectedCheckpoint':str(checkpoint),'scope':'orbit-functional-lab','chatEnabled':True,
                'checkpointHash':hashlib.sha256(checkpoint.read_bytes()).hexdigest()}
        for counts in [{}, {'total':36,'passed':36,'faultsDetected':35}]:
            write_json(path,{**report,'functionalTests':counts})
            with self.assertRaises(PolicyError):self.chat._generate('Teste JS h: Login viewer.')
        write_json(path,{**report,'functionalTests':{'total':36,'passed':36,'faultsDetected':36}})
        model=Mock();model.config=SimpleNamespace(context_length=256);model.generate.return_value=list(b'expect(await h.me()).toBe(200);')
        with patch('localauthor.nn.checkpoint.load_checkpoint',return_value=(model,None,ByteTokenizer(),None,None)) as load:
            result=self.chat._generate('Teste JS h: Login viewer.')
        load.assert_called_once_with(checkpoint)
        self.assertEqual(result['skill'],'orbit_functional_tests')
        self.assertIn('sandbox',result['notice'])
        checkpoint.write_bytes(b'changed checkpoint')
        with self.assertRaises(PolicyError):self.chat._generate('Teste JS h: Login viewer.')
