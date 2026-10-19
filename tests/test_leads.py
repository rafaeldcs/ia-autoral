"""Inbox policy, concurrency and evidence controls. Fixtures do not qualify a model."""
import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock

from tests.helpers import WorkspaceCase
from localauthor.errors import ConflictError, PolicyError, NotFoundError
from localauthor.foundation.leads import LeadService, validate_context, validate_event
from localauthor.foundation.lead_contract import validate_proposal


def context():
    return {'brand': 'ShopAir laboratório', 'audience': 'Lojistas e restaurantes',
            'intro': 'Olá! Conheça nossa plataforma.', 'handoff': 'Podemos apresentar uma demonstração.',
            'facts': [{'text': 'Loja online com catálogo e checkout.', 'url': 'https://example.com/', 'checked_at': date.today().isoformat()},
                      {'text': 'Cardápio digital para restaurantes.', 'url': 'https://example.com/', 'checked_at': date.today().isoformat()},
                      {'text': 'Não inclui emissão fiscal ou folha de pagamento.', 'url': 'https://example.com/', 'checked_at': date.today().isoformat()}],
            'questions': ['Qual é o tipo do seu negócio?', 'Como recebe os pedidos hoje?']}


def event(**changes):
    return {'source': 'website', 'event_id': 'test-001', 'company': 'Empresa fictícia', 'name': '',
            'email': 'fixture@example.test', 'phone': '', 'message': 'Quero uma demonstração de loja online.',
            'campaign': 'laboratorio', 'source_url': '', 'permission': 'reply_requested', 'opt_out': False, **changes}


def proposal(**changes):
    return {'fit': 'candidate', 'fact_indices': [1], 'message_indices': [1], 'question_indices': [2], **changes}


class LeadTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.model = Mock();self.model.answer.return_value = {'content': json.dumps(proposal()), 'possibly_truncated': False}
        self.leads = LeadService(self.store, self.model);self.pid = self.project['id']
        self.ctx = self.leads.save_context(self.pid, '', context())
    def lead(self, **changes):
        result = self.leads.ingest(self.pid, event(**changes));return self.leads.get(self.pid, result['id'])
    def analyze(self, item):
        return self.leads.qualify(self.pid, item['id'], item['version'], self.ctx['digest'])
    def review(self, item, **changes):
        return self.leads.review(self.pid, item['id'], item['version'], self.ctx['digest'], item['analysis']['digest'], changes.get('reviewed', True))

    def test_immutable_event_retry_conflict_and_contact_dedup(self):
        first = self.lead()
        result = self.leads.ingest(self.pid, event());self.assertTrue(result['deduplicated'])
        with self.assertRaises(ConflictError):self.leads.ingest(self.pid, event(message='Alterado'))
        result = self.leads.ingest(self.pid, event(event_id='test-002', email='FIXTURE@EXAMPLE.TEST', message='Outro pedido'))
        self.assertEqual(first['id'], result['id']);self.assertEqual(len(self.leads.get(self.pid, first['id'])['events']), 2)
    def test_missing_contact_is_still_delivered(self):
        item = self.lead(email='');self.assertEqual(item['stage'], 'new')
    def test_cross_project_contacts_and_reads_remain_separate(self):
        root = self.root/'second';root.mkdir();other = self.store.add_project('Outro', str(root))['id']
        item = self.lead();result = self.leads.ingest(other, event())
        self.assertNotEqual(item['id'], result['id'])
        with self.assertRaises(NotFoundError):self.leads.get(other, item['id'])
    def test_contact_collision_does_not_merge_people(self):
        self.lead();self.lead(event_id='other', email='other@example.test', phone='+5511999991111')
        with self.assertRaises(ConflictError):self.leads.ingest(self.pid, event(event_id='ambiguous', phone='+5511999991111'))
        self.assertEqual(len(self.leads.list(self.pid)['items']), 2)
    def test_opt_out_blocks_model_review_and_future_event(self):
        item = self.lead(message='Não quero receber contato. Remova meu contato das campanhas.')
        self.assertEqual(item['stage'], 'do_not_contact')
        with self.assertRaises(PolicyError):self.analyze(item)
        self.model.answer.assert_not_called()
        with self.assertRaises(PolicyError):self.leads.move(self.pid, item['id'], item['version'], 'qualified', 'Novo interesse')
        item = self.lead(event_id='later', permission='marketing_opt_in')
        self.assertEqual(item['stage'], 'do_not_contact');self.assertEqual(item['permission'], 'denied')
    def test_suppression_covers_new_and_old_identifiers(self):
        item = self.lead(phone='+5511988887777')
        item = self.lead(event_id='refusal', email='', phone='+5511988887777', opt_out=True)
        item = self.lead(event_id='again', phone='')
        self.assertEqual(item['stage'], 'do_not_contact')
    def test_review_is_required_and_draft_only_uses_approved_literals(self):
        item = self.analyze(self.lead());self.assertEqual(item['stage'], 'new')
        self.assertIn('Loja online com catálogo e checkout.', item['analysis']['draft'])
        self.assertIsNone(item['draft_approved'])
        with self.assertRaises(PolicyError):self.review(item, reviewed=False)
        item = self.review(item);self.assertEqual(item['stage'], 'qualified')
        self.assertEqual(item['draft_approved'], item['analysis']['digest'])
        self.assertFalse(item['history'][-1]['data']['sent'])
    def test_unknown_permission_and_research_never_produce_outreach_draft(self):
        for changes in [{'permission': 'unknown'}, {'source': 'research', 'permission': 'unknown', 'source_url': 'https://example.com/'}]:
            item = self.analyze(self.lead(event_id=str(changes), email='', **changes))
            self.assertEqual(item['analysis']['draft'], '')
            self.assertNotEqual(item['analysis']['suggested_stage'], 'qualified')
            with self.assertRaises(PolicyError):self.leads.move(self.pid, item['id'], item['version'], 'demonstration', 'Ignorar regra')
    def test_new_event_invalidates_old_approval(self):
        item = self.review(self.analyze(self.lead()))
        updated = self.lead(event_id='update', message='Minha necessidade mudou.')
        self.assertIsNone(updated['analysis']);self.assertIsNone(updated['draft_approved'])
    def test_rejected_analysis_feedback_reaches_next_local_attempt(self):
        item = self.analyze(self.lead())
        item = self.leads.reject(self.pid, item['id'], item['version'], 'Pergunte somente o que falta; não invente parceiros.')
        self.assertIsNone(item['analysis']);self.analyze(item)
        self.assertIn('não invente parceiros', self.model.answer.call_args.args[1])
    def test_public_research_does_not_replace_an_existing_customer_request(self):
        item = self.lead()
        updated = self.lead(event_id='public', source='research', permission='unknown', source_url='https://example.com/', company='Outro nome público', message='Uma observação pública.')
        self.assertEqual(updated['last_message'], item['last_message']);self.assertEqual(updated['company'], item['company'])
        self.assertEqual(updated['permission'], 'reply_requested')
    def test_stale_context_and_stale_lead_cannot_be_applied(self):
        item = self.analyze(self.lead());value = context();value['facts'][0]['text'] = 'Novo fato revisado.'
        new = self.leads.save_context(self.pid, self.ctx['digest'], value)
        self.assertNotEqual(new['digest'], self.ctx['digest'])
        with self.assertRaises(ConflictError):self.review(item)
        self.assertTrue(self.leads.get(self.pid, item['id'])['analysis_stale'])
        with self.assertRaises(ConflictError):self.leads.save_context(self.pid, '', context())
    def test_stale_inflight_result_is_logged_not_applied(self):
        item = self.lead()
        def respond(*args, **kwargs):
            self.lead(event_id='during', message='Nova mensagem recebida.')
            return {'content': json.dumps(proposal()), 'possibly_truncated': False}
        self.model.answer.side_effect = respond
        with self.assertRaises(PolicyError):self.analyze(item)
        stored = self.leads.get(self.pid, item['id']);self.assertIsNone(stored['analysis'])
        self.assertFalse(stored['history'][-1]['data']['accepted'])
    def test_malformed_truncated_or_invented_fields_preserve_failed_attempts(self):
        for result in [{'content': 'not JSON'}, {'content': json.dumps(proposal(partner='invented'))},
                       {'content': json.dumps(proposal(fact_indices=[9]))}, {'content': json.dumps(proposal()), 'possibly_truncated': True}]:
            item = self.lead(event_id=str(len(self.leads.list(self.pid)['items'])), email='')
            self.model.answer.return_value = result
            with self.assertRaises(PolicyError):self.analyze(item)
            stored = self.leads.get(self.pid, item['id']);self.assertIsNone(stored['analysis'])
            self.assertEqual(stored['history'][-1]['kind'], 'analysis_attempt');self.assertFalse(stored['history'][-1]['data']['accepted'])
    def test_identifiers_not_sent_to_model_and_single_lead_context(self):
        item = self.analyze(self.lead(phone='+5511999992222'))
        prompt = self.model.answer.call_args.args[1]
        self.assertNotIn('fixture@example.test', prompt);self.assertNotIn('+5511999992222', prompt)
        self.assertEqual(self.model.answer.call_args.args[2:4], ([], []))
    def test_engine_failure_is_logged_without_applying_or_leaking_exception_body(self):
        item = self.lead();self.model.answer.side_effect = RuntimeError('private transport details')
        with self.assertRaises(PolicyError):self.analyze(item)
        stored = self.leads.get(self.pid, item['id']);self.assertIsNone(stored['analysis'])
        self.assertNotIn('private transport details', str(stored['history'][-1]))
    def test_won_and_campaign_metrics_are_recorded_not_claimed_as_revenue(self):
        item = self.review(self.analyze(self.lead()))
        item = self.leads.move(self.pid, item['id'], item['version'], 'won', 'Registro sintético pela equipe')
        self.assertEqual(self.leads.list(self.pid)['campaigns']['laboratorio']['won'], 1)
        with self.assertRaises(ConflictError):self.leads.move(self.pid, item['id'], item['version']-1, 'lost', 'Concorrência')
    def test_expired_context_and_unsafe_event_are_rejected(self):
        value = context();value['facts'][0]['checked_at'] = (date.today()-timedelta(days=31)).isoformat()
        with self.assertRaises(PolicyError):validate_context(value)
        for changes in [{'source_url': 'https://example.com/?token=private'}, {'opt_out': 'false'}, {'token': 'secret'},
                        {'phone': 'extension abc'}, {'source': 'research', 'permission': 'marketing_opt_in', 'source_url': 'https://example.com/'}]:
            with self.assertRaises(PolicyError):validate_event(event(**changes))


class LeadContractTests(WorkspaceCase):
    def test_valid_selection_and_copies(self):
        data = proposal(fact_indices=[1,2], question_indices=[])
        output = validate_proposal(data, 2, 1, 0);self.assertEqual(output, data)
        output['fact_indices'].append(3);self.assertEqual(data['fact_indices'], [1,2])
        self.assertEqual(validate_proposal(proposal(fit='not_fit', fact_indices=[], question_indices=[]), 0, 1, 0)['fit'], 'not_fit')
    def test_invalid_types_ranges_duplicates_and_unhashable_values(self):
        for key in ('fact_indices', 'message_indices', 'question_indices'):
            for bad in (None, '1', [True], [0], [-1], [2.0], [99], [1,1], [[1]], [{}], [1,2,3,4]):
                with self.subTest(key=key, bad=bad), self.assertRaises(PolicyError):validate_proposal(proposal(**{key: bad}), 3, 3, 3)
        for position in range(3):
            for bad in (True, -1, 21, 2.0, None):
                counts = [3,3,3];counts[position] = bad
                with self.assertRaises(PolicyError):validate_proposal(proposal(), *counts)
        for bad in ([], None, {}, proposal(fit=[]), proposal(fit='invented'), proposal(extra='untrusted'), proposal(fact_indices=[]), proposal(message_indices=[])):
            with self.assertRaises(PolicyError):validate_proposal(bad, 3, 3, 3)
