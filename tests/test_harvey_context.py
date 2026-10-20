import copy
import json
import unittest

from localauthor.errors import PolicyError
from localauthor.harvey.context import fit_agent_context
from localauthor.harvey.contracts import criterion_messages
from localauthor.foundation.context import build_context
from localauthor.foundation.grounding import COMMERCIAL_GROUNDING,unmentioned_features


class HarveyContextTests(unittest.TestCase):
    def test_feature_guard_rejects_absent_features_but_preserves_confirmed_features(self):
        self.assertEqual(unmentioned_features('Catálogo e controle de estoque','Catálogo e controle de estoque'),[])
        self.assertEqual(unmentioned_features('Catálogo e controle de estoque','Catálogo e pedidos'),['estoque'])
        self.assertEqual(unmentioned_features('Demonstração gratuita','Demonstração gratuita'),[])
        self.assertEqual(unmentioned_features('Processamento automatizado e interface','Catálogo e pedidos'),['automação','interface'])
    def test_judge_receives_only_original_scorer_fields(self):
        variables={'task_description':'task label','agent_output':'evidence','criterion_title':'criterion','match_criteria':'required fact'}
        messages=criterion_messages(variables)
        self.assertEqual(json.loads(messages[-1]['content']),variables)
        with self.assertRaises(PolicyError):criterion_messages({**variables,'assignment':'unrelated finalization requirement'})

    def test_commercial_guidance_is_used_by_normal_chat_and_marketing(self):
        for profile in ['general','marketing']:
            context=build_context('Escreva uma proposta',[],[],scope='demo',count=self.count,context_tokens=8192,output_tokens=768,work_profile=profile)
            self.assertIn(COMMERCIAL_GROUNDING,context.messages[0]['content'])

    def count(self,rows):return len(json.dumps(rows,ensure_ascii=False))//4+1

    def test_small_requests_are_unchanged(self):
        messages=[{'role':'system','content':'rules'},{'role':'user','content':'task'}]
        fitted,event=fit_agent_context(messages,self.count,2000,'/workspace/history/1.json')
        self.assertEqual(fitted,messages);self.assertEqual(event['archived_messages'],0)

    def test_large_tool_result_is_explicitly_paged_without_mutating_original(self):
        messages=[{'role':'system','content':'rules'},{'role':'user','content':'original task'},
                  {'role':'assistant','content':'read document'},
                  {'role':'user','content':'Tool result id: '+'evidence '*8000}]
        original=copy.deepcopy(messages)
        fitted,event=fit_agent_context(messages,self.count,1300,'/workspace/history/1.json')
        self.assertEqual(messages,original);self.assertEqual(fitted[:2],original[:2])
        self.assertLessEqual(self.count(fitted),1300);self.assertEqual(event['excerpts'],[3])
        self.assertIn('EXPLICIT EXCERPT',fitted[-1]['content']);self.assertIn('read-only',fitted[2]['content'])

    def test_old_turns_are_archived_in_pairs_and_latest_result_survives(self):
        messages=[{'role':'system','content':'rules'},{'role':'user','content':'task'}]
        for index in range(20):messages.extend([{'role':'assistant','content':'action '+str(index)+'x'*400},{'role':'user','content':'Tool result '+str(index)+': '+'y'*400}])
        fitted,event=fit_agent_context(messages,self.count,1100,'/workspace/history/2.json')
        self.assertGreater(event['archived_messages'],0);self.assertEqual(event['archived_messages']%2,0)
        self.assertEqual(fitted[-2:],messages[-2:]);self.assertLessEqual(self.count(fitted),1100)

    def test_oversized_assignment_fails_instead_of_discarding_requirements(self):
        messages=[{'role':'system','content':'mandatory rules'},{'role':'user','content':'requirements '*3000}]
        with self.assertRaisesRegex(PolicyError,'context_length_exceeded'):
            fit_agent_context(messages,self.count,1000,'/workspace/history/3.json')

    def test_large_rpc_request_is_reduced_before_counting(self):
        messages=[{'role':'system','content':'rules'},{'role':'user','content':'task'},
                  {'role':'assistant','content':'read'},{'role':'user','content':'Tool result id: '+'x'*200_000}]
        def bounded_count(rows):
            self.assertLessEqual(len(json.dumps(rows,ensure_ascii=False).encode()),110_000)
            return self.count(rows)
        fitted,event=fit_agent_context(messages,bounded_count,1500,'/workspace/history/4.json')
        self.assertIsNone(event['before_tokens']);self.assertLessEqual(self.count(fitted),1500)

    def test_recount_budget_cannot_exhaust_the_inference_protocol(self):
        messages=[{'role':'system','content':'rules'},{'role':'user','content':'task'}]
        for index in range(60):messages.extend([{'role':'assistant','content':'action '+str(index)},{'role':'user','content':'Tool result '+str(index)}])
        calls=[]
        def never_fits(rows):calls.append(1);return 2000
        with self.assertRaisesRegex(PolicyError,'limite de contagem'):
            fit_agent_context(messages,never_fits,1000,'/workspace/history/bounded.json')
        self.assertEqual(len(calls),32)


if __name__=='__main__':unittest.main()
