#!/usr/bin/env python3
"""A green unittest result alone does not prove the full suite executed."""
import argparse
import json
import os
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT)]
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
os.environ.setdefault("OMP_NUM_THREADS","1")

class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.records=[]; self.started={}
    def startTest(self,test):
        self.started[test.id()]=time.monotonic(); super().startTest(test)
    def record(self,test,status,detail=None):
        self.records.append({"test":test.id(),"status":status,"seconds":time.monotonic()-self.started.get(test.id(),time.monotonic()),"detail":detail})
    def addSuccess(self,test):
        self.record(test,"passed"); super().addSuccess(test)
    def addFailure(self,test,err):
        self.record(test,"failed",self._exc_info_to_string(err,test)); super().addFailure(test,err)
    def addError(self,test,err):
        self.record(test,"error",self._exc_info_to_string(err,test)); super().addError(test,err)
    def addSkip(self,test,reason):
        self.record(test,"skipped",reason); super().addSkip(test,reason)
    def addSubTest(self,test,subtest,err):
        if err is not None:
            self.record(subtest,"failed" if issubclass(err[0],test.failureException) else "error",self._exc_info_to_string(err,test))
        super().addSubTest(test,subtest,err)
    def addExpectedFailure(self,test,err):
        self.record(test,"expected_failure",self._exc_info_to_string(err,test)); super().addExpectedFailure(test,err)
    def addUnexpectedSuccess(self,test):
        self.record(test,"unexpected_success"); super().addUnexpectedSuccess(test)

WINDOWS_SYMLINK_TESTS = {
    "tests.test_safety.SafetyTests.test_rejects_symlink_" + kind
    for kind in ("file", "directory", "root")
}

def assessment(result, *, allow_unavailable_symlinks=False, platform=None):
    allowed = WINDOWS_SYMLINK_TESTS if allow_unavailable_symlinks and (platform or sys.platform) == "win32" else set()
    unexpected_skips = [test.id() for test, _ in result.skipped if test.id() not in allowed]
    passed = sum(record["status"] == "passed" for record in result.records)
    success = (result.wasSuccessful() and result.testsRun >= 119 and passed > 0
               and not unexpected_skips and not result.expectedFailures)
    return {"success": success, "complete": not result.skipped and not result.expectedFailures,
            "passed": passed, "minimum_required": 119, "unexpected_skips": unexpected_skips,
            "allowed_skips": [test.id() for test, _ in result.skipped if test.id() in allowed]}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--report",type=Path,default=ROOT/"reports"/"test-results.json")
    p.add_argument("--allow-unavailable-symlinks",action="store_true",help="Allow only the three privilege-dependent Windows symlink tests; coverage remains incomplete.")
    args=p.parse_args()
    start=time.monotonic()
    suite=unittest.defaultTestLoader.discover(str(ROOT/"tests"),top_level_dir=str(ROOT))
    result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
    report={"at":datetime.now(timezone.utc).isoformat(),"python":sys.version,"platform":sys.platform,"tests_run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),"unittest_success":result.wasSuccessful(),**assessment(result,allow_unavailable_symlinks=args.allow_unavailable_symlinks),"elapsed_seconds":time.monotonic()-start,"records":result.records,"limitations":["Resultado do ambiente indicado por python/platform; não mede outros equipamentos.","GPU, .NET e execução Docker real não são validadas por esta suíte.","Testes numéricos usam padrões minúsculos; não demonstram capacidade de programação."]}
    args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    if not report["success"]:
        print("Validation gate failed: errors, insufficient tests or unapproved skips. See JSON report.",file=sys.stderr)
    sys.exit(0 if report["success"] else 1)
