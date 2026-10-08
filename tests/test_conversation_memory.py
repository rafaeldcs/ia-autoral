"""Persistence, revocation and real context contracts; not model quality."""
import json
import threading
from unittest.mock import patch

from tests.helpers import WorkspaceCase
from tests.test_foundation import DummyText, DummyImage, register_fixture
from localauthor.application import Application
from localauthor.errors import PolicyError, NotFoundError
from localauthor.foundation.context import build_context
from localauthor.foundation.service import FoundationService
from localauthor.foundation.experience import ExperienceStore


class ConversationMemoryTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.app = Application(self.settings)
        self.addCleanup(self.app.close)
        self.chat = self.app.chat
        self.conversation = self.chat.create(self.project['id'], 'Preferências')

    def say(self, text, **kwargs):
        return self.chat.respond(self.project['id'], self.conversation['id'], text, **kwargs)

    def test_remember_without_model_persists_and_is_visible_in_history(self):
        with patch.object(self.chat.foundation, 'answer', side_effect=AssertionError('no inference')):
            result = self.say('Lembre-se: Preserve o azul da marca.', mode='foundation')
        row = self.chat.memories(self.project['id'])[0]
        self.assertEqual(row['source_message_id'], result['messages'][0]['id'])
        self.assertEqual(result['messages'][1]['metadata']['origin'], 'project_memory')
        self.assertFalse(result['messages'][1]['metadata']['weights_trained'])
        other = Application(self.settings)
        self.addCleanup(other.close)
        self.assertEqual(other.chat.memories(self.project['id']), [row])
        self.assertEqual(len(other.chat.get(self.project['id'], self.conversation['id'])['messages']), 2)

    def test_duplicate_forget_and_reactivation_keep_original_turns(self):
        for _ in range(2): self.say('Lembre-se: Responda em português.')
        self.assertEqual(len(self.chat.memories(self.project['id'])), 1)
        self.say('Esqueça: Responda em português.')
        self.assertEqual(self.chat.memories(self.project['id']), [])
        self.say('Lembre-se: Responda em português.')
        self.assertEqual(len(self.chat.memories(self.project['id'])), 1)
        self.assertEqual(len(self.chat.get(self.project['id'], self.conversation['id'])['messages']), 8)

    def test_list_and_unknown_forget_do_not_change_memory(self):
        self.say('Lembre-se: Use legendas curtas.')
        row = self.chat.memories(self.project['id'])[0]
        listed = self.say('O que você lembra deste projeto?')
        self.assertIn(row['content'], listed['messages'][-1]['content'])
        result = self.say('Esqueça: Texto inexistente.')
        self.assertIn('Não encontrei', result['messages'][-1]['content'])
        self.assertEqual(self.chat.memories(self.project['id']), [row])

    def test_memory_and_commands_do_not_cross_projects(self):
        self.say('Lembre-se: Azul privado deste projeto.')
        root = self.root/'other'; root.mkdir()
        other = self.store.add_project('Outro', str(root))
        self.assertEqual(self.chat.memories(other['id']), [])
        with self.assertRaises(NotFoundError):
            self.chat.respond(other['id'], self.conversation['id'], 'Lembre-se: Invasão.')
        self.assertEqual(self.chat.memories(other['id']), [])

    def test_code_quotes_and_ordinary_feedback_are_not_persistent_commands(self):
        for message, fmt in [('Lembre-se: Constante de exemplo.', 'code'),
                ('> Lembre-se: Citação de documento.', 'auto'),
                ('Use azul nesta postagem.', 'auto'),
                ('```text\nLembre-se: Exemplo\n```', 'auto')]:
            self.say(message, input_format=fmt)
        self.assertEqual(self.chat.memories(self.project['id']), [])

    def test_secrets_and_invalid_memory_do_not_save_turns(self):
        for message in ['Lembre-se: password="synthetic-private123"', 'Lembre-se: '+self.settings.token,
                        'Lembre-se: ', 'Lembre-se: '+'x'*601]:
            with self.subTest(message=message[:20]), self.assertRaises(PolicyError): self.say(message)
        self.assertEqual(self.chat.memories(self.project['id']), [])
        self.assertEqual(self.chat.get(self.project['id'], self.conversation['id'])['messages'], [])

    def test_limits_do_not_partially_save_command_and_forget_frees_active_slot(self):
        for i in range(20): self.say(f'Lembre-se: Preferência {i}.')
        before = self.chat.get(self.project['id'], self.conversation['id'])
        with self.assertRaises(PolicyError): self.say('Lembre-se: Preferência adicional.')
        self.assertEqual(self.chat.get(self.project['id'], self.conversation['id']), before)
        self.say('Esqueça: Preferência 0.')
        self.say('Lembre-se: Preferência adicional.')
        self.assertEqual(len(self.chat.memories(self.project['id'])), 20)

    def test_cancel_and_quota_roll_back_memory_and_history(self):
        cancel = threading.Event(); cancel.set()
        with self.assertRaises(PolicyError): self.say('Lembre-se: Cancelada.', cancel=cancel)
        with patch.object(self.settings, 'max_store_bytes', 1):
            with self.assertRaises(PolicyError): self.say('Lembre-se: Sem espaço.')
        self.assertEqual(self.chat.memories(self.project['id']), [])
        self.assertEqual(self.chat.get(self.project['id'], self.conversation['id'])['messages'], [])

    def test_failed_assistant_write_rolls_back_user_and_memory(self):
        with self.store.connect() as db:
            db.execute("CREATE TRIGGER fixture_fail BEFORE INSERT ON messages WHEN NEW.role='assistant' BEGIN SELECT RAISE(ABORT,'fixture'); END")
        with self.assertRaises(Exception): self.say('Lembre-se: Escrita incompleta.')
        self.assertEqual(self.chat.memories(self.project['id']), [])
        self.assertEqual(self.chat.get(self.project['id'], self.conversation['id'])['messages'], [])

    def test_new_conversation_receives_memory_and_forgetting_excludes_control_history(self):
        register_fixture(self.settings.home, self.root/'text')
        self.chat.foundation = FoundationService(self.settings.home, text_factory=DummyText, image_factory=DummyImage)
        self.say('Lembre-se: Preserve o azul da marca.')
        memory = self.chat.memories(self.project['id'])[0]
        self.conversation = self.chat.create(self.project['id'], 'Nova conversa')
        result = self.say('Qual direção seguir?', mode='foundation')
        meta = result['messages'][-1]['metadata']
        ctx = ExperienceStore(self.settings.home).get(self.project['id'], meta['experience_id'])['metadata']['generation_context']
        self.assertEqual(meta['memory_used'], [memory['id']])
        self.assertEqual(json.loads(ctx[-1]['content'])['memorias_do_projeto'][0]['content'], memory['content'])
        self.say('O que você lembra deste projeto?')
        self.say('Esqueça: Preserve o azul da marca.')
        # A fresh conversation cannot recover a revoked note through history.
        self.conversation = self.chat.create(self.project['id'], 'Depois de esquecer')
        result = self.say('Qual direção seguir?', mode='foundation')
        meta = result['messages'][-1]['metadata']
        ctx = ExperienceStore(self.settings.home).get(self.project['id'], meta['experience_id'])['metadata']['generation_context']
        self.assertEqual(meta['memory_used'], [])
        self.assertNotIn('Preserve o azul', json.dumps(ctx, ensure_ascii=False))
        # Same-conversation control turns are also not replayed.
        self.say('Lembre-se: Não repita esta nota.')
        self.say('Esqueça: Não repita esta nota.')
        result = self.say('Outro pedido', mode='foundation')
        ctx = ExperienceStore(self.settings.home).get(self.project['id'], result['messages'][-1]['metadata']['experience_id'])['metadata']['generation_context']
        self.assertNotIn('Não repita esta nota', json.dumps(ctx, ensure_ascii=False))

    def test_context_rejects_foreign_or_invalid_memory(self):
        memory = {'id':'a'*32, 'project_id':'p', 'content':'Azul', 'source_message_id':1}
        for changed in [dict(memory,project_id='other'), dict(memory,content='x'*601), dict(memory,source_message_id=True)]:
            with self.assertRaises(PolicyError):
                build_context('Pedido', [], [], scope='p', count=lambda m:len(json.dumps(m)), context_tokens=4096, output_tokens=512, project_memory=[changed])

    def test_context_accounts_omissions_and_keeps_memory_out_of_system_rules(self):
        notes = [{'id':f'{i:032x}', 'project_id':'p', 'content':'Preferência '+str(i)+'x'*500, 'source_message_id':i+1} for i in range(20)]
        ctx = build_context('Pedido atual', [], [], scope='p', count=lambda m:len(json.dumps(m)), context_tokens=4096, output_tokens=512, project_memory=notes)
        self.assertLessEqual(ctx.input_tokens, 3584)
        self.assertGreater(ctx.omitted_memory, 0)
        self.assertEqual(len(ctx.memory_used)+ctx.omitted_memory, 20)
        self.assertNotIn('Preferência', ctx.messages[0]['content'])
        self.assertEqual(json.loads(ctx.messages[-1]['content'])['pedido_atual'], 'Pedido atual')
