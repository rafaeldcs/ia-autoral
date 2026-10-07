"""Workflow safeguards with fixtures; these are not model-quality evaluations."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from localauthor.config import Settings
from localauthor.errors import ConflictError, NotFoundError, PolicyError
from localauthor.store import Store
from localauthor.foundation.marketing_workflow import MarketingWorkflow, tracking_url
from localauthor.foundation.marketing_channels import MarketingChannels


class Collector:
    def __init__(self,store,settings):self.store,self.settings=store,settings
    def fetch(self,url,scope,cancel=None):
        if 'blocked' in url:raise PolicyError('HTTP429; leitura não confirmada')
        return self.store.ingest(scope,url,'Fonte sintética','Catálogo e estoque.\nPedidos para lojas.\nObjetivo e medição.',kind='web')


class Model:
    def __init__(self):self.calls=0;self.responses=[]
    def answer(self,project,prompt,history,evidence,cancel=None,**kwargs):
        self.calls+=1
        if prompt.startswith('Revise criticamente'):
            return {'content':json.dumps({'supported':True,'problems':[]}),'evidence':[],'possibly_truncated':False}
        content=self.responses.pop(0) if self.responses else json.dumps({'caption':'Conheça catálogo e estoque. Solicite demonstração.','alt_text':'Proposta: vitrine em fundo claro.','fact_indices':[1]},ensure_ascii=False)
        return {'content':content,'evidence':evidence,'possibly_truncated':False}


class Vault:
    def seal(self,token):return 'ciphertext-fixture'
    def open(self,sealed):return 'synthetic-token-for-tests'


class Transport:
    def __init__(self):self.calls=[];self.fail=False;self.wrong_identity=False
    def call(self,version,account,edge,method,params,token):
        self.calls.append((account,edge,method,params))
        if self.fail:raise PolicyError('Falha simulada')
        return {'id':'999' if self.wrong_identity else account if method=='GET' else '12345','can_post':True,'username':'synthetic-business'}


class MarketingWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.settings=Settings(self.root/'home',offline=False,allowed_domains=['example.com']);self.settings.initialize()
        self.store=Store(self.settings.home/'memory.sqlite3')
        (self.root/'project').mkdir();(self.root/'other').mkdir()
        self.project=self.store.add_project('Marketing sintético',str(self.root/'project'))['id']
        self.other=self.store.add_project('Outro projeto',str(self.root/'other'))['id']
        self.model=Model();self.service=MarketingWorkflow(self.store,Collector(self.store,self.settings),self.model)
        self.transport=Transport();self.channels=MarketingChannels(self.store,self.service,self.settings,vault=Vault(),transport=self.transport)
        self.brief={'brand':'Marca sintética','audience':'Lojistas','objective':'Solicitar demonstração','destination':'https://example.com/contact','channels':['facebook','instagram']}
    def tearDown(self):self.temp.cleanup()
    def prepared(self,choose=True):
        c=self.service.create(self.project,self.brief)
        c=self.service.research(self.project,c['id'],c['digest'],[{'role':'product','url':'https://example.com/product'},{'role':'reference','url':'https://example.com/template'}])
        if choose:c=self.service.choose(self.project,c['id'],c['digest'],'original')
        return c
    def generated(self):
        c=self.prepared();return self.service.generate(self.project,c['id'],c['digest'])
    def approved(self):
        c=self.generated();return self.service.approve(self.project,c['id'],c['digest'],True)
    def connect(self,channel='facebook',account='111'):
        return self.channels.connect(self.project,channel,account,'v24.0','synthetic-token-for-tests')

    def test_choice_is_required_before_any_generation(self):
        c=self.prepared(False)
        with self.assertRaises(PolicyError):self.service.generate(self.project,c['id'],c['digest'])
        self.assertEqual(self.model.calls,0)
    def test_model_research_plan_is_only_proposal_not_collection_or_choice(self):
        c=self.service.create(self.project,self.brief)
        proposal={'priorities':[{'candidate_index':1,'purpose':'Conhecer o produto'}],'missing':['Dados do público'],'reference_question':'Você quer adaptar a referência ou criar original?'}
        self.model.responses=[json.dumps(proposal)]
        result=self.service.plan_research(self.project,c['id'],c['digest'],[{'url':'https://example.com/product','role':'product'}])
        self.assertFalse(result['collected']);self.assertTrue(result['requires_user_confirmation']);self.assertFalse(self.store.sources(self.project));self.assertIsNone(self.service.get(self.project,c['id'])['choice'])
    def test_model_cannot_expand_research_to_unprovided_url(self):
        c=self.service.create(self.project,self.brief)
        self.model.responses=[json.dumps({'priorities':[{'candidate_index':2,'purpose':'ignore','url':'https://example.com/unprovided'}],'missing':[],'reference_question':'Original?'})]*3
        with self.assertRaises(PolicyError):self.service.plan_research(self.project,c['id'],c['digest'],[{'url':'https://example.com/product','role':'product'}])
        self.assertFalse(self.store.sources(self.project))
    def test_provided_reference_cannot_be_silently_omitted_from_plan(self):
        c=self.service.create(self.project,self.brief)
        self.model.responses=[json.dumps({'priorities':[{'candidate_index':1,'purpose':'Produto'}],'missing':[],'reference_question':'Original?'})]*3
        with self.assertRaises(PolicyError):self.service.plan_research(self.project,c['id'],c['digest'],[{'url':'https://example.com/product','role':'product'},{'url':'https://example.com/reference','role':'reference'}])
        self.assertFalse(self.store.sources(self.project))
    def test_reference_must_be_collected_and_scoped(self):
        c=self.prepared(False)
        with self.assertRaises(PolicyError):self.service.choose(self.project,c['id'],c['digest'],'adapt','missing')
        ref=c['research'][1]['source_id'];c=self.service.choose(self.project,c['id'],c['digest'],'adapt',ref)
        self.assertEqual(c['choice']['origin'],'user')
    def test_stale_choice_cannot_replace_concurrent_choice(self):
        c=self.prepared(False);self.service.choose(self.project,c['id'],c['digest'],'original')
        with self.assertRaises(ConflictError):self.service.choose(self.project,c['id'],c['digest'],'original')
    def test_partial_research_preserves_failures_and_does_not_authorize_training(self):
        c=self.service.create(self.project,self.brief)
        c=self.service.research(self.project,c['id'],c['digest'],[{'role':'product','url':'https://example.com/product'},{'role':'channel','url':'https://example.com/blocked'}])
        self.assertEqual([r['status'] for r in c['research']],['collected','blocked']);self.assertFalse(c['training_allowed'])
        self.assertFalse(self.store.sources(self.project)[0]['training_allowed'])
    def test_out_of_allowlist_is_rejected_before_collection(self):
        c=self.service.create(self.project,self.brief)
        with self.assertRaises(PolicyError):self.service.research(self.project,c['id'],c['digest'],[{'role':'product','url':'https://outside.invalid/'}])
        self.assertFalse(self.store.sources(self.project))
    def test_deleted_or_changed_source_invalidates_draft(self):
        c=self.prepared();self.store.ingest(self.project,'https://example.com/product','Changed','Novo texto.',kind='web')
        with self.assertRaises(PolicyError):self.service.generate(self.project,c['id'],c['digest'])
        self.assertEqual(self.model.calls,0)
    def test_cross_project_access_is_denied(self):
        c=self.prepared()
        with self.assertRaises(NotFoundError):self.service.get(self.other,c['id'])
    def test_software_product_facts_are_ranked_and_keep_original_line_numbers(self):
        content='Texto introdutório.\nProjetos, tarefas, sprints e quadros Kanban.\nRepositórios Git com pull e push por HTTPS.\nPapéis e permissões para usuários.'
        self.service.research_service.fetch=lambda url,scope,cancel=None:self.store.ingest(scope,url,'Produto sintético',content,kind='web')
        c=self.prepared()
        reply=json.dumps({'caption':'Orbit: projetos e repositórios Git. Conheça a proposta.','alt_text':'Proposta: ícones de tarefas e código.','fact_indices':[1,2]})
        self.model.responses=[reply,reply]
        result=self.service.generate(self.project,c['id'],c['digest'])
        self.assertEqual(result['stage'],'review')
        claims=result['draft']['assets'][0]['claims']
        self.assertEqual([c['start_line'] for c in claims],[2,3])
        self.assertEqual([c['text'] for c in claims],content.splitlines()[1:3])
        self.assertFalse(result['published']);self.assertFalse(result['training_allowed'])
    def test_product_fact_filter_keeps_security_guards_and_word_boundaries(self):
        content='Usuário despedido ontem.\nHTTPS admin manager member viewer.\n[Projetos e tarefas seguros]\nProjetos disponíveis por R$ 20.\n20 projetos e tarefas.\nProjetos aumentam as vendas em 50%.\nProjetos e tarefas com Git.\n'+'Projetos '+('x'*241)
        self.service.research_service.fetch=lambda url,scope,cancel=None:self.store.ingest(scope,url,'Produto sintético',content,kind='web')
        c=self.prepared()
        reply=json.dumps({'caption':'Conheça projetos e tarefas.','alt_text':'Proposta: ícones de projetos.','fact_indices':[1]})
        self.model.responses=[reply,reply]
        result=self.service.generate(self.project,c['id'],c['digest'])
        self.assertEqual(result['stage'],'review')
        self.assertEqual(result['draft']['assets'][0]['claims'][0]['text'],'Projetos e tarefas com Git.')
        self.assertEqual(result['draft']['assets'][0]['claims'][0]['start_line'],7)
    def test_commerce_plural_facts_remain_supported(self):
        content='Catálogos, estoques, pedidos e produtos para lojas.\nRestaurantes e plataformas de produtos.'
        self.service.research_service.fetch=lambda url,scope,cancel=None:self.store.ingest(scope,url,'Produto sintético',content,kind='web')
        c=self.prepared();result=self.service.generate(self.project,c['id'],c['digest'])
        self.assertEqual(result['stage'],'review')
        self.assertEqual(result['draft']['assets'][0]['claims'][0]['text'],content.splitlines()[0])
    def test_invalid_citation_is_rejected_and_originals_preserved(self):
        bad=json.dumps({'caption':'Conheça a marca.','alt_text':'Proposta.','fact_indices':[99]})
        self.model.responses=[bad]*3;c=self.generated()
        self.assertEqual(c['stage'],'rejected');self.assertEqual(len(c['draft']['attempts'][0]['attempts']),3)
        self.assertFalse(c['published']);self.assertIsNone(c['approval'])
    def test_known_promises_cannot_pass_mechanical_checks(self):
        c=self.prepared();source=c['research'][0]['source_id']
        self.model.responses=[json.dumps({'caption':'Aumente suas vendas em50%.','alt_text':'Proposta.','fact_indices':[1]})]*3
        c=self.service.generate(self.project,c['id'],c['digest']);self.assertEqual(c['stage'],'rejected')
    def test_unsupported_claim_in_creative_description_is_also_rejected(self):
        self.model.responses=[json.dumps({'caption':'Conheça a marca.','alt_text':'Proposta: estoque em tempo real.','fact_indices':[1]})]*3
        c=self.generated();self.assertEqual(c['stage'],'rejected')
    def test_illustration_cannot_invent_a_product_screen_without_screenshot_evidence(self):
        self.model.responses=[json.dumps({'caption':'Conheça catálogo e estoque.','alt_text':'Proposta: tablet exibindo dashboard da plataforma.','fact_indices':[1]})]*3
        c=self.generated();self.assertEqual(c['stage'],'rejected');self.assertIsNone(c['approval'])
    def test_unverified_efficiency_is_blocked_even_with_a_real_resource_citation(self):
        self.model.responses=[json.dumps({'caption':'Centralize catálogo e estoque com eficiência.','alt_text':'Proposta: ícones.','fact_indices':[1]})]*3
        c=self.generated();self.assertEqual(c['stage'],'rejected');self.assertFalse(c['draft']['checks_passed'])
    def test_citation_is_resolved_from_exact_received_source_without_rewriting_caption(self):
        c=self.generated();asset=c['draft']['assets'][0]
        self.assertEqual(asset['caption'],'Conheça catálogo e estoque. Solicite demonstração.')
        claim=asset['claims'][0];source=self.store.source(self.project,'https://example.com/product')
        self.assertEqual(claim['text'],source['content'].splitlines()[claim['start_line']-1])
    def test_editorial_rejection_does_not_become_reviewable_approval(self):
        original=self.model.answer
        def reviewer(project,prompt,*args,**kwargs):
            if prompt.startswith('Revise criticamente'):return {'content':json.dumps({'supported':False,'problems':[{'phrase':'Conheça catálogo e estoque.','reason':'A peça extrapola o fato documentado.'}]}),'possibly_truncated':False}
            return original(project,prompt,*args,**kwargs)
        self.model.answer=reviewer;c=self.generated()
        self.assertEqual(c['stage'],'rejected');self.assertIsNone(c['approval'])
    def test_reviewer_cannot_invent_a_phrase_absent_from_the_piece(self):
        original=self.model.answer
        def reviewer(project,prompt,*args,**kwargs):
            if prompt.startswith('Revise criticamente'):return {'content':json.dumps({'supported':False,'problems':[{'phrase':'frase que não existe','reason':'Erro inventado.'}]}),'possibly_truncated':False}
            return original(project,prompt,*args,**kwargs)
        self.model.answer=reviewer;c=self.generated()
        self.assertEqual(c['stage'],'rejected');self.assertIsNone(c['approval'])
    def test_inconsistent_critic_receives_feedback_without_auto_fixing_approval(self):
        replies=[{'supported':True,'problems':[{'phrase':'Conheça catálogo','reason':'Fato não sustentado.'}]},
                 {'supported':False,'problems':[{'phrase':'Conheça catálogo','reason':'Fato não sustentado.'}]}]
        prompts=[]
        def reviewer(project,prompt,*args,**kwargs):
            prompts.append(prompt)
            return {'content':json.dumps(replies.pop(0) if replies else {'supported':True,'problems':[]}),
                    'experience_id':str(len(prompts)),'possibly_truncated':False}
        self.model.answer=reviewer
        result=self.service.review_candidate(self.project,{'brief':self.brief},
            {'channel':'facebook','caption':'Conheça catálogo.','alt_text':'Proposta: ícones.','claims':[]})
        self.assertFalse(result['supported']);self.assertEqual(len(result['phases']),3)
        self.assertEqual(len(result['phases'][0]['attempts']),2)
        self.assertIn('contradiz',result['attempts'][0]['error']);self.assertIn('contradiz',prompts[1])
        self.assertEqual(result['attempts'][0]['experience_id'],'1')
    def test_critic_only_receives_and_quotes_the_field_for_its_phase(self):
        prompts=[]
        def reviewer(project,prompt,*args,**kwargs):
            prompts.append(prompt)
            if 'Etapa creative.' in prompt:
                response={'supported':False,'problems':[{'phrase':'Conheça catálogo.','reason':'Citou um campo que esta etapa não recebeu.'}]}
            else:response={'supported':True,'problems':[]}
            return {'content':json.dumps(response),'possibly_truncated':False}
        self.model.answer=reviewer
        with self.assertRaises(PolicyError):
            self.service.review_candidate(self.project,{'brief':self.brief},
                {'channel':'facebook','caption':'Conheça catálogo.','alt_text':'Proposta: ícones.','claims':[]})
        payloads=[json.loads(p.split(' Dados: ',1)[1].split('. Retorne somente JSON',1)[0]) for p in prompts]
        self.assertEqual(set(payloads[0]),{'brand','caption','facts'})
        self.assertEqual(set(payloads[1]),{'brand','caption','channel'})
        self.assertEqual(set(payloads[2]),{'brand','alt_text'})
        self.assertNotIn('caption',payloads[3]);self.assertIn('campo não recebido',prompts[3])
    def test_good_draft_needs_human_review_and_events_are_not_claimed_installed(self):
        c=self.generated();self.assertEqual(c['stage'],'review');self.assertTrue(c['draft']['human_review_required'])
        self.assertEqual(c['draft']['measurement']['implementation'],'pending');self.assertEqual(c['draft']['budget_spent_cents'],0)
        with self.assertRaises(PolicyError):self.service.export(self.project,c['id'])
    def test_approval_exact_revision_and_new_research_revokes_it(self):
        c=self.approved();self.assertEqual(len(self.service.export(self.project,c['id'])['assets']),2)
        c=self.service.research(self.project,c['id'],c['digest'],[{'role':'product','url':'https://example.com/product'}])
        self.assertIsNone(c['approval'])
        with self.assertRaises(PolicyError):self.service.export(self.project,c['id'])
    def test_changed_source_revokes_export_even_after_approval(self):
        c=self.approved();self.store.delete_source(c['research'][0]['source_id'],self.project)
        with self.assertRaises(PolicyError):self.service.export(self.project,c['id'])
    def test_utm_preserves_business_query_and_unicode_without_pii(self):
        link=tracking_url('https://example.com/contact?plan=base&utm_source=old','facebook','campanha-á','peça-1')
        self.assertIn('plan=base',link);self.assertNotIn('old',link);self.assertIn('utm_source=facebook',link)
        with self.assertRaises(PolicyError):tracking_url('https://example.com/?email=private','facebook','test','one')
    def test_connect_does_not_expose_token_or_claim_publication_permission(self):
        c=self.connect();self.assertFalse(c['publish_permission_verified'])
        self.assertNotIn('token',json.dumps(self.channels.list(self.project)))
        with self.store.connect() as db:self.assertNotIn('synthetic-token',db.execute('SELECT sealed_token FROM marketing_channels').fetchone()[0])
    def test_wrong_account_never_saved(self):
        self.transport.wrong_identity=True
        with self.assertRaises(PolicyError):self.connect()
        self.assertFalse(self.channels.list(self.project))
    def test_authorization_and_preview_hash_required_before_send(self):
        c=self.approved();self.connect();preview=self.channels.preview(self.project,c['id'],'piece-1')
        with self.assertRaises(PolicyError):self.channels.publish(self.project,c['id'],'piece-1',preview['payload_hash'],False)
        with self.assertRaises(ConflictError):self.channels.publish(self.project,c['id'],'piece-1','wrong',True)
        self.assertEqual(len(self.transport.calls),1)
    def test_changed_account_invalidates_preview(self):
        c=self.approved();self.connect();p=self.channels.preview(self.project,c['id'],'piece-1');self.connect(account='222')
        with self.assertRaises(ConflictError):self.channels.publish(self.project,c['id'],'piece-1',p['payload_hash'],True)
    def test_confirmed_delivery_and_duplicate_rejection(self):
        c=self.approved();self.connect();p=self.channels.preview(self.project,c['id'],'piece-1')
        delivery=self.channels.publish(self.project,c['id'],'piece-1',p['payload_hash'],True)
        self.assertEqual(delivery['state'],'confirmed')
        with self.assertRaises(ConflictError):self.channels.publish(self.project,c['id'],'piece-1',p['payload_hash'],True)
        self.assertEqual(len(self.transport.calls),2)
    def test_changing_api_version_cannot_repeat_delivery(self):
        c=self.approved();self.connect();p=self.channels.preview(self.project,c['id'],'piece-1')
        self.channels.publish(self.project,c['id'],'piece-1',p['payload_hash'],True)
        self.channels.connect(self.project,'facebook','111','v25.0','synthetic-token-for-tests')
        p=self.channels.preview(self.project,c['id'],'piece-1')
        with self.assertRaises(ConflictError):self.channels.publish(self.project,c['id'],'piece-1',p['payload_hash'],True)
    def test_uncertain_delivery_stays_uncertain_without_retry(self):
        c=self.approved();self.connect();p=self.channels.preview(self.project,c['id'],'piece-1');self.transport.fail=True
        with self.assertRaises(PolicyError):self.channels.publish(self.project,c['id'],'piece-1',p['payload_hash'],True)
        self.assertEqual(self.channels.deliveries(self.project)[0]['state'],'unknown')
        self.transport.fail=False
        with self.assertRaises(ConflictError):self.channels.publish(self.project,c['id'],'piece-1',p['payload_hash'],True)
    def test_instagram_requires_real_public_jpeg_and_two_step_confirmation(self):
        c=self.approved();self.connect('instagram','333')
        with self.assertRaises(PolicyError):self.channels.preview(self.project,c['id'],'piece-2')
        for url in ('https://127.0.0.1/asset.jpg','https://localhost/asset.jpg','https://machine.local/asset.jpg'):
            with self.subTest(url=url),self.assertRaises(PolicyError):self.channels.preview(self.project,c['id'],'piece-2',url)
        p=self.channels.preview(self.project,c['id'],'piece-2','https://example.com/approved.jpg')
        self.channels.publish(self.project,c['id'],'piece-2',p['payload_hash'],True,'https://example.com/approved.jpg')
        self.assertEqual([c[1] for c in self.transport.calls],['','media','media_publish'])
    def test_disconnected_or_other_project_cannot_use_account(self):
        self.connect();self.assertFalse(self.channels.list(self.other));self.channels.disconnect(self.project,'facebook')
        c=self.approved()
        with self.assertRaises(PolicyError):self.channels.preview(self.project,c['id'],'piece-1')
