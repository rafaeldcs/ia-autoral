"""Brand safeguards with explicit doubles, not a creative-quality benchmark."""
import json
import threading
import unittest
from types import SimpleNamespace

from tests import test_marketing_workflow as fixtures
from localauthor.errors import ConflictError, NotFoundError, PolicyError
from localauthor.foundation.marketing_brand import validate_brand

PROFILE = {'instagram':'@Marca.Exemplo','no_instagram':False,'moment':'Lançamento de um produto',
           'identity':'Azul e violeta, logo existente','likes':'Fotos de pessoas e títulos curtos',
           'avoid':'Promessas, excesso de texto e troca de logo','history':'O usuário relata posts educativos; Insights não fornecidos.'}


class MarketingBrandTests(unittest.TestCase):
    setUp = fixtures.MarketingWorkflowTests.setUp
    tearDown = fixtures.MarketingWorkflowTests.tearDown
    prepared = fixtures.MarketingWorkflowTests.prepared
    generated = fixtures.MarketingWorkflowTests.generated
    approved = fixtures.MarketingWorkflowTests.approved

    def profile(self):
        c=self.service.create(self.project,self.brief)
        return self.service.save_brand(self.project,c['id'],c['digest'],PROFILE)

    def test_handle_is_normalized_without_guessing_an_account(self):
        self.assertEqual(validate_brand(PROFILE)['instagram'],'marca.exemplo')
        for handle in ['', 'https://instagram.com/x', 'a..b', '.ab', 'ab.', 'a'*31, 'nome de conta']:
            with self.subTest(handle=handle),self.assertRaises(PolicyError):validate_brand({**PROFILE,'instagram':handle})
        for key in ['identity','likes','avoid','history','moment']:
            with self.subTest(key=key),self.assertRaises(PolicyError):validate_brand({**PROFILE,key:''})

    def test_new_brand_can_explicitly_have_no_instagram(self):
        self.assertEqual(validate_brand({**PROFILE,'instagram':'','no_instagram':True})['instagram'],'')
        with self.assertRaises(PolicyError):validate_brand({**PROFILE,'no_instagram':True})
        with self.assertRaises(PolicyError):validate_brand({**PROFILE,'no_instagram':1})

    def test_unknown_fields_and_secrets_are_not_accepted(self):
        with self.assertRaises(PolicyError):validate_brand({**PROFILE,'password':'never-store'})
        with self.assertRaises(PolicyError):validate_brand({**PROFILE,'history':'password=synthetic-secret'})

    def test_generation_requires_brand_analysis_and_user_style_choice(self):
        c=self.service.create(self.project,self.brief)
        c=self.service.research(self.project,c['id'],c['digest'],[{'role':'product','url':'https://example.com/product'}])
        c=self.service.choose(self.project,c['id'],c['digest'],'original')
        with self.assertRaisesRegex(PolicyError,'preferências'):self.service.generate(self.project,c['id'],c['digest'])
        self.assertEqual(self.model.calls,0)
        c=self.service.save_brand(self.project,c['id'],c['digest'],PROFILE)
        c=self.service.analyze_brand(self.project,c['id'],c['digest'])
        with self.assertRaises(PolicyError):self.service.generate(self.project,c['id'],c['digest'])
        self.assertFalse(c['published']);self.assertFalse(c['training_allowed'])

    def test_analysis_is_by_local_model_and_separates_report_from_visual_access(self):
        c=self.profile();c=self.service.analyze_brand(self.project,c['id'],c['digest'])
        a=c['brand_analysis']
        self.assertEqual(a['origin'],'local_model');self.assertFalse(a['visual_pixels_analyzed'])
        self.assertEqual(a['inputs']['profile_user_reported']['instagram'],'marca.exemplo')
        self.assertIsNone(c['style_approval']);self.assertIsNone(c['draft'])
        self.assertTrue(any('não diga que viu imagens' in p for p in self.model.prompts if p.startswith('Analise a identidade')))

    def test_style_choice_is_scoped_explicit_and_concurrent_safe(self):
        c=self.profile()
        with self.assertRaises(PolicyError):self.service.choose_style(self.project,c['id'],c['digest'],'improve','Preferência')
        c=self.service.analyze_brand(self.project,c['id'],c['digest'])
        with self.assertRaises(PolicyError):self.service.choose_style(self.project,c['id'],c['digest'],'automatic','Preferência')
        with self.assertRaises(NotFoundError):self.service.choose_style(self.other,c['id'],c['digest'],'improve','Preferência')
        chosen=self.service.choose_style(self.project,c['id'],c['digest'],'preserve','Quero preservar minhas cores.')
        self.assertEqual(chosen['style_approval']['origin'],'user')
        with self.assertRaises(ConflictError):self.service.choose_style(self.project,c['id'],c['digest'],'reinvent','Mudar')

    def test_new_preferences_revoke_existing_draft_and_approval(self):
        c=self.approved();old=self.service.get(self.project,c['id'])
        c=self.service.save_brand(self.project,c['id'],c['digest'],PROFILE)
        for key in ['draft','approval','style_approval','brand_analysis']:self.assertIsNone(c[key])
        self.assertIsNotNone(old['draft']);self.assertEqual(old['stage'],'approved')
        with self.assertRaises(PolicyError):self.service.export(self.project,c['id'])

    def test_research_revokes_style_even_if_brand_preferences_stay(self):
        c=self.prepared();profile=c['brand_profile']
        c=self.service.research(self.project,c['id'],c['digest'],[{'role':'brand','url':'https://example.com/history'}])
        self.assertEqual(c['brand_profile'],profile);self.assertIsNone(c['brand_analysis']);self.assertIsNone(c['style_approval'])

    def test_bad_analysis_outputs_are_preserved_without_approval(self):
        c=self.profile()
        self.model.answer=lambda *a,**k:{'content':'{"invented":"schema"}','possibly_truncated':False}
        c=self.service.analyze_brand(self.project,c['id'],c['digest'])
        self.assertEqual(len(c['brand_analysis']['attempts']),3)
        self.assertIsNone(c['brand_analysis']['content']);self.assertIsNone(c['style_approval'])
        self.assertEqual(c['brand_analysis']['attempts'][0]['content'],'{"invented":"schema"}')

    def test_known_instagram_is_not_asked_again_and_originals_are_preserved(self):
        c=self.profile()
        answer={'observed':['Relato do usuário.'],'preserve':['Preservar identidade relatada.'],
                'improve':['Hipótese de título curto.'],'questions':['Qual é o @ do Instagram?']}
        self.model.answer=lambda *a,**k:{'content':json.dumps(answer),'possibly_truncated':False}
        c=self.service.analyze_brand(self.project,c['id'],c['digest'])
        self.assertIsNone(c['brand_analysis']['content']);self.assertEqual(len(c['brand_analysis']['attempts']),3)
        self.assertIn('já foi fornecido',c['brand_analysis']['attempts'][0]['error'])

    def test_editorial_rejection_of_brand_analysis_is_not_approved(self):
        c=self.profile();original=self.model.answer
        def answer(project,prompt,*a,**k):
            if prompt.startswith('Revise criticamente esta análise'):
                return {'content':json.dumps({'supported':False,'problems':[{'phrase':'Preservar as cores declaradas.','reason':'Conflito simulado com a preferência.'}]}),'possibly_truncated':False}
            return original(project,prompt,*a,**k)
        self.model.answer=answer;c=self.service.analyze_brand(self.project,c['id'],c['digest'])
        self.assertIsNone(c['brand_analysis']['content']);self.assertIsNone(c['style_approval'])

    def test_favorite_post_question_is_allowed_for_a_known_account(self):
        c=self.profile();original=self.model.answer
        def answer(project,prompt,*a,**k):
            result=original(project,prompt,*a,**k)
            if prompt.startswith('Analise a identidade'):
                data=json.loads(result['content']);data['questions']=['Qual postagem do Instagram você mais gosta?']
                result['content']=json.dumps(data)
            return result
        self.model.answer=answer;c=self.service.analyze_brand(self.project,c['id'],c['digest'])
        self.assertIsNotNone(c['brand_analysis']['content'])

    def test_cancelled_analysis_does_not_save_partial_authority(self):
        c=self.profile();cancel=threading.Event();cancel.set()
        with self.assertRaises(PolicyError):self.service.analyze_brand(self.project,c['id'],c['digest'],cancel=cancel)
        self.assertEqual(self.model.calls,0);self.assertIsNone(self.service.get(self.project,c['id'])['brand_analysis'])

    def test_browser_observation_must_belong_to_same_project_and_profile(self):
        c=self.profile()
        frame={'number':1,'snapshot':'frozen','title':'Perfil','headings':['marca.exemplo'],
               'image_descriptions':['Foto relatada pelo site'],'controls':[], 'capturedBy':'LocalAuthor own browser'}
        def get(project,ident):
            if project!=self.project or ident!='owned':raise NotFoundError('Sessão não encontrada.')
            return {'url':'https://www.instagram.com/marca.exemplo/','frames':[frame]}
        self.service.browser=SimpleNamespace(get=get)
        with self.assertRaises(NotFoundError):self.service.analyze_brand(self.project,c['id'],c['digest'],'other')
        c=self.service.analyze_brand(self.project,c['id'],c['digest'],'owned')
        observed=c['brand_analysis']['inputs']['local_browser_accessibility'][0]
        self.assertEqual(observed['captured_by'],'LocalAuthor own browser')
        frame['snapshot']='changed'
        with self.assertRaises(PolicyError):self.service.choose_style(self.project,c['id'],c['digest'],'improve','Preservar')
        self.service.browser=SimpleNamespace(get=lambda *a:{'url':'https://www.instagram.com/another/','frames':[frame]})
        with self.assertRaises(PolicyError):self.service._brand_browser(self.project,'owned','marca.exemplo')

    def test_generation_and_editorial_review_receive_user_preferences(self):
        c=self.prepared();c=self.service.generate(self.project,c['id'],c['digest'])
        generation=next(p for p in self.model.prompts if p.startswith('Crie UMA'))
        self.assertIn('Azul e violeta',generation);self.assertIn('Excesso de emojis',generation)
        self.assertEqual(c['draft']['attempts'][0]['attempts'][0]['editorial_review']['phases'][-1]['phase'],'brand')
        self.assertEqual(c['stage'],'review')
