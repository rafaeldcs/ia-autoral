import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest

from localauthor.capture_decision import decide
from localauthor.investigation_policy import InvestigationPolicy


class CaptureDecisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'policy.npz'
        InvestigationPolicy().save(self.path)
        self.observation = {'url':'https://qa.example.test/', 'authorizedOrigin':'https://qa.example.test',
            'status':200, 'title':'Teste', 'loading':False, 'passwordFilled':False}

    def test_capture_requires_actual_record_proposal(self):
        for action in ('WAIT', 'SANITIZE', 'UNKNOWN', 'STOP_SCOPE', 'RECORD_ERROR'):
            with patch.object(InvestigationPolicy, 'predict', return_value=action):
                result=decide(self.observation,self.path)
                self.assertEqual(result['modelAction'],action)
                self.assertFalse(result['authorized'])
                self.assertIsNone(result['tool'])
        with patch.object(InvestigationPolicy, 'predict', return_value='RECORD'):
            result=decide(self.observation,self.path)
            self.assertTrue(result['authorized'])
            self.assertEqual(result['tool'],'browser.screenshot')
            self.assertEqual(len(result['checkpointHash']),64)

    def test_wrong_record_prediction_cannot_bypass_guard(self):
        for change in ({'url':'https://other.example.test/'}, {'status':403},
                       {'loading':True}, {'passwordFilled':True}):
            with patch.object(InvestigationPolicy,'predict',return_value='RECORD'):
                result=decide({**self.observation,**change},self.path)
                self.assertFalse(result['authorized'])

    def test_secret_fields_and_truthy_strings_are_rejected(self):
        for change in ({'password':'private'}, {'loading':'false'}, {'passwordFilled':'no'}):
            with self.assertRaises(ValueError): decide({**self.observation,**change},self.path)


if __name__=='__main__': unittest.main()
