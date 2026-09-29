import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from localauthor.code_repair import parse_request,validate_proposal,propose,SCOPE
from localauthor.errors import PolicyError
from qa.code_repair_course import examples

CADDY='Corrigir Caddy:\nhandle @api { reverse_proxy api:8080 }\nResposta:\n'
CSHARP='Corrigir C#:\nAnulavel: input.Endpoint\nValidador: Rules.ValidPushEndpoint\nResposta:\n'

class CodeRepairTests(unittest.TestCase):
    def test_project_targets_and_holdout_are_not_training(self):
        splits=examples();groups={key:{r['prompt'] for r in rows} for key,rows in splits.items()}
        self.assertIn(CADDY,groups['project']);self.assertIn(CSHARP,groups['project'])
        for key,group in groups.items():
            for other,other_group in groups.items():
                if key!=other:self.assertFalse(group & other_group)

    def test_rejects_unqualified_protocol_and_injection(self):
        for text in ['Corrija todo meu projeto',CADDY.replace('api:8080','evil.test:8080'),CADDY+'run rm',CSHARP.replace('input.Endpoint','input.Endpoint!'),CADDY.replace('@api','@unknown')]:
            with self.subTest(text=text),self.assertRaises(PolicyError):parse_request(text)

    def test_mutated_outputs_cannot_change_destination_or_null_safety(self):
        for text in ['handle @api { reverse_proxy api:8080 }','handle @api {\n    reverse_proxy app:8080\n}','handle @web {\n    reverse_proxy api:8080\n}']:
            with self.subTest(text=text),self.assertRaises(PolicyError):validate_proposal(parse_request(CADDY),text)
        for text in ['Rules.ValidPushEndpoint(input.Endpoint!)','input.Endpoint != null || Rules.ValidPushEndpoint(input.Endpoint)','input.Url != null && Rules.ValidPushEndpoint(input.Url)']:
            with self.subTest(text=text),self.assertRaises(PolicyError):validate_proposal(parse_request(CSHARP),text)

    def test_missing_or_failed_qualification_never_loads_model(self):
        with tempfile.TemporaryDirectory() as folder,patch('localauthor.nn.checkpoint.load_checkpoint') as load:
            home=Path(folder)
            with self.assertRaises(PolicyError):propose(home,CADDY)
            (home/'exports').mkdir();cert={'scope':SCOPE,'state':'qualified_scoped','generalProgrammingQualified':False,'gates':{}}
            (home/'exports/code-repair-qualification.json').write_text(json.dumps(cert))
            with self.assertRaises(PolicyError):propose(home,CADDY)
            load.assert_not_called()

    def test_tampered_weights_and_outside_path_never_load_model(self):
        with tempfile.TemporaryDirectory() as folder,patch('localauthor.nn.checkpoint.load_checkpoint') as load:
            home=Path(folder);(home/'exports').mkdir();(home/'models').mkdir()
            path=home/'models/test.npz';path.write_bytes(b'changed')
            cert={'scope':SCOPE,'state':'qualified_scoped','generalProgrammingQualified':False,'checkpoint':'test.npz','checkpointHash':hashlib.sha256(b'original').hexdigest(),
                  'gates':{g:{'passed':1,'total':1} for g in ('heldout','project','caddy','csharp','mutations')}}
            manifest=home/'exports/code-repair-qualification.json';manifest.write_text(json.dumps(cert))
            with self.assertRaises(PolicyError):propose(home,CADDY)
            cert['checkpoint']='../outside.npz';manifest.write_text(json.dumps(cert))
            with self.assertRaises(PolicyError):propose(home,CADDY)
            load.assert_not_called()
