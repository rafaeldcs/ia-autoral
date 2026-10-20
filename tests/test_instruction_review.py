import unittest
from localauthor.foundation.instruction_review import code_blocks, review_code_request
from tests.helpers import WorkspaceCase
from tests.test_foundation import register_fixture, DummyText
from localauthor.foundation.service import FoundationService
from localauthor.foundation.experience import ExperienceStore


class ExplicitCodeReviewTests(unittest.TestCase):
    def test_fences_and_unicode_are_read_without_changing_code(self):
        text='Antes\r\n````ts\r\n\t// ação 😀\r\n```\r\ncontinua\r\n````\r\n~~~sql\nSELECT 1;\n~~~\n'
        self.assertEqual(code_blocks(text),['\t// ação 😀\r\n```\r\ncontinua\r\n','SELECT 1;\n'])

    def test_line_limit_counts_all_code_blocks_and_blank_lines(self):
        code='```cs\na\n\nb\n```\n~~~sql\nc\n~~~'
        result=review_code_request('Código com até 3 linhas.',code)
        self.assertEqual(result['checked'],['code_line_limit'])
        self.assertEqual(len(result['violations']),1)
        self.assertIn('4 linhas',result['violations'][0])

    def test_ambiguous_or_absent_limits_do_not_invent_a_constraint(self):
        for prompt in ['Texto até 2 linhas e código até 30 linhas.','Escreva código.']:
            self.assertNotIn('code_line_limit',review_code_request(prompt,'```cs\na\n```')['checked'])

    def test_bans_apply_only_when_explicit_in_current_request(self):
        code='```tsx\nimport { Tarefa } from "./tipo";\nuseEffect(()=>{});\n<div className="p-4 bg-blue-500 rounded"/>\n```'
        self.assertEqual(review_code_request('Use React e Tailwind.',code)['violations'],[])
        result=review_code_request('Sem useEffect, Tailwind ou imports locais.',code)
        self.assertEqual(len(result['violations']),3)
        self.assertEqual(review_code_request('Sem useEffect, Tailwind ou imports locais.','```tsx\nimport {useState} from "react";\n<div/>\n```')['violations'],[])

    def test_postgres_identity_is_distinct_from_serial(self):
        prompt='SQL PostgreSQL com id gerado como identidade.'
        self.assertEqual(len(review_code_request(prompt,'```sql\nCREATE TABLE t(id SERIAL PRIMARY KEY);\n```')['violations']),1)
        self.assertEqual(review_code_request(prompt,'```sql\nCREATE TABLE t(id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY);\n```')['violations'],[])

    def test_native_css_values_are_not_misidentified_as_tailwind_classes(self):
        prompt='Sem Tailwind.'
        native='```tsx\n<span style={{textDecoration: concluida ? "line-through" : "none"}}>Tarefa</span>\n```'
        self.assertEqual(review_code_request(prompt,native)['violations'],[])
        for attribute in ('className="line-through"', 'className={concluida ? "line-through" : ""}', 'class="p-4"'):
            self.assertTrue(review_code_request(prompt,'```tsx\n<span '+attribute+'>Tarefa</span>\n```')['violations'])

    def test_plain_prose_is_not_claimed_as_verified_code(self):
        self.assertEqual(review_code_request('Até 2 linhas.','Proposta sem código.'),{'checked':[],'violations':[]})


class BoundedInstructionRetryTests(WorkspaceCase):
    def generate(self,outputs):
        register_fixture(self.settings.home,self.root/'instruction-double')
        calls=[]
        class ExplicitRetryDouble(DummyText):
            def generate(self,messages,cancel=None):
                calls.append(messages)
                return outputs[min(len(calls)-1,len(outputs)-1)],False
        service=FoundationService(self.settings.home,text_factory=ExplicitRetryDouble)
        result=service.answer(self.project['id'],'Gere código com até 1 linhas.',[],[])
        return result,calls

    def test_real_retry_path_preserves_original_and_uses_the_models_second_output(self):
        original='```cs\nlinha 1\nlinha 2\n```'
        revised='```cs\nlinha única\n```'
        result,calls=self.generate([original,revised])
        self.assertEqual(len(calls),2)
        self.assertEqual(result['content'],revised)
        self.assertEqual(result['instruction_review']['violations'],[])
        row=ExperienceStore(self.settings.home).get(self.project['id'],result['experience_id'])
        self.assertEqual(row['metadata']['generation_attempts'][0]['content'],original)
        self.assertEqual(row['metadata']['generation_attempts'][1]['content'],revised)
        self.assertIn('limite explícito',calls[1][-1]['content'])

    def test_unfixed_reply_stops_after_one_retry_and_retains_visible_failure_metadata(self):
        wrong='```cs\nlinha 1\nlinha 2\n```'
        result,calls=self.generate([wrong,wrong])
        self.assertEqual(len(calls),2)
        self.assertTrue(result['instruction_review']['violations'])
        self.assertEqual(result['content'],wrong)

    def test_replacing_code_with_prose_cannot_clear_the_failed_checks(self):
        result,calls=self.generate(['```cs\nlinha 1\nlinha 2\n```','Não incluí código.'])
        self.assertEqual(len(calls),2)
        self.assertTrue(result['instruction_review']['violations'])

    def test_unfenced_model_code_has_an_automatic_presentation_hint(self):
        original='using System;\npublic class Tarefa {}'
        result,calls=self.generate([original])
        self.assertEqual(result['format'],'code')
        self.assertEqual(result['content'],original)
        self.assertEqual(len(calls),1)
        self.assertNotIn('instruction_review',result)
