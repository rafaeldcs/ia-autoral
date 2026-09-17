"""An assertion failure is required; crashes and empty suites cannot certify a test."""
import importlib.util
import copy
import hashlib
import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock

spec=importlib.util.spec_from_file_location('functional_sandbox',Path(__file__).resolve().parents[1]/'scripts/functional_sandbox.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
activation_spec=importlib.util.spec_from_file_location('functional_activation',Path(__file__).resolve().parents[1]/'scripts/activate-functional-tests.py')
activation=importlib.util.module_from_spec(activation_spec);activation_spec.loader.exec_module(activation)

class FunctionalEvidenceTests(TestCase):
    def setUp(self):
        self.sandbox=module.FunctionalSandbox.__new__(module.FunctionalSandbox)
        self.sandbox.verified=True
        self.case={'answer':'expect(await h.me()).toBe(401);','kind':'login'}
        self.good={'exit':0,'stats':{'expected':1,'skipped':0}}
        self.fault={'exit':1,'stats':{'unexpected':1},'assertionFailure':True}

    def test_unverified_sandbox_and_altered_contract_do_not_execute(self):
        self.sandbox.run=Mock()
        self.assertFalse(self.sandbox.evaluate(self.case,'expect(true).toBe(true);')['passed'])
        self.sandbox.run.assert_not_called()
        self.sandbox.verified=False
        with self.assertRaises(RuntimeError):self.sandbox.evaluate(self.case,self.case['answer'])
        self.sandbox.run.assert_not_called()

    def test_crash_and_empty_or_skipped_suite_cannot_pass(self):
        for normal,fault in [
            (self.good,{**self.fault,'assertionFailure':False}),
            ({'exit':0,'stats':{'expected':0,'skipped':0}},self.fault),
            ({'exit':0,'stats':{'expected':1,'skipped':1}},self.fault),
            (self.good,self.good),
        ]:
            with self.subTest(normal=normal,fault=fault):
                self.sandbox.run=Mock(side_effect=[normal,fault])
                self.assertFalse(self.sandbox.evaluate(self.case,self.case['answer'])['passed'])

    def test_real_test_and_assertion_failure_are_both_required(self):
        self.sandbox.run=Mock(side_effect=[self.good,self.fault])
        result=self.sandbox.evaluate(self.case,self.case['answer'])
        self.assertTrue(result['passed'])
        self.assertTrue(result['correctApplicationPassed'])
        self.assertTrue(result['controlledFaultDetected'])


class FunctionalActivationTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name);self.folder=self.home/'evidence';self.folder.mkdir()
        checkpoint=self.home/'models/model.npz';checkpoint.parent.mkdir();checkpoint.write_bytes(b'fixture')
        frozen=activation.examples([43,47,61,79])
        def results(cases):
            return {'state':'completed','total':len(cases),'passed':len(cases),'sandbox':{'image':'sha256:fixture'},
                    'cases':[{**c,'generated':c['answer'],'accepted':True,'passed':True,
                              'correctApplicationPassed':True,'controlledFaultDetected':True,
                              'normal':{'exit':0,'stats':{'expected':1,'skipped':0}},
                              'fault':{'exit':1,'stats':{'unexpected':1},'assertionFailure':True}} for c in cases]}
        self.files={'frozen-test-cases.json':frozen,'functional-references.json':results(activation.examples([17])),
                    'functional-execution.json':results(frozen),
                    'report.json':{'state':'awaiting_execution','selectedCheckpoint':str(checkpoint),
                                   'checkpointHash':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                                   'after':[{**c,'generated':c['answer']} for c in frozen],
                                   'regression':[],'limitations':'fixture'}}

    def save(self):
        for name,value in self.files.items():(self.folder/name).write_text(json.dumps(value),encoding='utf-8')

    def test_complete_evidence_produces_scoped_certificate(self):
        self.save();certificate=activation.certify(self.folder,self.home)
        self.assertEqual(certificate['functionalTests']['faultsDetected'],36)
        self.assertFalse(certificate['programmingQualified'])
        self.assertEqual(len(certificate['evidenceHashes']),4)

    def test_duplicate_case_crash_or_changed_image_blocks_activation(self):
        original=copy.deepcopy(self.files)
        for change in ('duplicate','crash','image','source'):
            self.files=copy.deepcopy(original)
            report=self.files['functional-execution.json']
            if change=='duplicate':report['cases'][1]=report['cases'][0]
            elif change=='crash':report['cases'][0]['fault']['assertionFailure']=False
            elif change=='image':report['sandbox']['image']='other'
            else:report['cases'][0]['generated']='expect(true).toBe(true);'
            self.save()
            with self.subTest(change=change),self.assertRaises(ValueError):activation.certify(self.folder,self.home)

    def test_changed_checkpoint_blocks_activation(self):
        self.save();Path(self.files['report.json']['selectedCheckpoint']).write_bytes(b'other')
        with self.assertRaises(ValueError):activation.certify(self.folder,self.home)
