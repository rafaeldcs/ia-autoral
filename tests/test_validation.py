"""Regression tests for trustworthy test reports, not model qualification."""
import importlib.util
import io
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("validation_runner", Path(__file__).resolve().parents[1] / "scripts" / "run-tests.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ValidationTests(unittest.TestCase):
    def result(self, count=119):
        result = runner.Result(unittest.runner._WritelnDecorator(io.StringIO()), True, 0)
        result.testsRun = count
        result.records = [{"status": "passed"}] * count
        return result

    def test_empty_or_partial_suite_cannot_pass(self):
        for count in (0, 1, 118):
            with self.subTest(count=count):
                self.assertFalse(runner.assessment(self.result(count))["success"])

    def test_full_suite_can_pass(self):
        self.assertTrue(runner.assessment(self.result())["success"])

    def test_missing_dependency_skip_cannot_pass(self):
        result = self.result()
        result.skipped.append((unittest.FunctionTestCase(lambda: None), "NumPy absent"))
        report = runner.assessment(result, allow_unavailable_symlinks=True, platform="win32")
        self.assertFalse(report["success"])
        self.assertFalse(report["complete"])

    def test_symlink_exception_is_explicit_and_windows_only(self):
        from tests.test_safety import SafetyTests
        result = self.result()
        result.skipped.append((SafetyTests("test_rejects_symlink_file"), "Privilege absent"))
        self.assertFalse(runner.assessment(result, platform="win32")["success"])
        self.assertFalse(runner.assessment(result, allow_unavailable_symlinks=True, platform="linux")["success"])
        report = runner.assessment(result, allow_unavailable_symlinks=True, platform="win32")
        self.assertTrue(report["success"])
        self.assertFalse(report["complete"])

    def test_subtest_failure_is_recorded(self):
        class Broken(unittest.TestCase):
            def runTest(self):
                with self.subTest(case="regression"):
                    self.fail("expected test fixture failure")
        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=runner.Result).run(Broken())
        self.assertFalse(result.wasSuccessful())
        self.assertEqual(result.records[0]["status"], "failed")
        self.assertIn("regression", result.records[0]["test"])

    def test_expected_failure_is_not_complete_validation(self):
        result = self.result()
        result.expectedFailures.append((unittest.FunctionTestCase(lambda: None), "failure"))
        self.assertFalse(runner.assessment(result)["success"])
