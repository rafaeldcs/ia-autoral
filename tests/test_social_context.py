"""Context selection contracts; generation quality is evaluated with the real model separately."""
import json
import unittest
from localauthor.chat_routing import social_only
from localauthor.foundation.context import build_context


class SocialContextTests(unittest.TestCase):
    def test_narrow_social_detection_does_not_swallow_questions_code_or_approval(self):
        for message in ['Oi, bom dia!', 'Obrigado, ajudou muito!', 'Muito obrigada!',
                        'Valeu, até amanhã!', 'Chat, obrigado pela ajuda.', 'Perfeito, muito grato pela ajuda.']:
            with self.subTest(message=message): self.assertTrue(social_only(message))
        for message in ['Obrigado! Qual era meu projeto?', 'Bom dia, quero o instalador',
                        'Sim', 'Pode fazer', 'Aprovado', 'Obrigado! Apague os arquivos',
                        '```\nobrigado\n```', '"obrigado"', 'obrigado()', '// obrigado',
                        'Oi, responda em inglês.', 'Obrigado por explicar a API. Agora tenho outra dúvida.']:
            with self.subTest(message=message): self.assertFalse(social_only(message))

    def context(self, message):
        history=[{'role':'user','content':'Crie uma campanha'}, {'role':'assistant','content':'Qual o Instagram?'}]
        memory=[{'id':'a'*32,'project_id':'p','content':'Prefiro respostas em inglês.', 'source_message_id':1}]
        evidence=[{'scope':'p','text':'Documento de campanha','title':'Campanha'}]
        return build_context(message,history,evidence,scope='p',count=lambda m:len(json.dumps(m))//4,
            context_tokens=8192,output_tokens=512,work_profile='marketing',project_memory=memory,
            project_guidance={'method':'kanban','wip_limit':3,'definition_of_done':'Conferido'})

    def test_acknowledgement_omits_old_tasks_and_profile_but_keeps_declared_preferences(self):
        context=self.context('Obrigado, ajudou muito!')
        self.assertEqual(context.history_used,0)
        self.assertEqual(context.omitted_history,2)
        self.assertEqual(context.omitted_evidence,1)
        self.assertEqual(context.memory_used,('a'*32,))
        self.assertNotIn('Instagram',context.messages[0]['content'])
        payload=json.loads(context.messages[-1]['content'])
        self.assertNotIn('orientacao_do_projeto',payload)
        self.assertEqual(payload['memorias_do_projeto'][0]['content'],'Prefiro respostas em inglês.')

    def test_mixed_question_retains_history_evidence_and_work_profile(self):
        context=self.context('Obrigado! Qual era a pergunta sobre a campanha?')
        self.assertEqual(context.history_used,2)
        self.assertEqual(context.omitted_history,0)
        self.assertEqual(len(context.evidence),1)
        self.assertIn('Instagram',context.messages[0]['content'])
        self.assertIn('orientacao_do_projeto',json.loads(context.messages[-1]['content']))
