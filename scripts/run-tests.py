#!/usr/bin/env python3
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

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--report",type=Path,default=ROOT/"reports"/"test-results.json"); args=p.parse_args()
    start=time.monotonic()
    suite=unittest.defaultTestLoader.discover(str(ROOT/"tests"),top_level_dir=str(ROOT))
    result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
    report={"at":datetime.now(timezone.utc).isoformat(),"python":sys.version,"platform":sys.platform,"tests_run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),"success":result.wasSuccessful(),"elapsed_seconds":time.monotonic()-start,"records":result.records,"limitations":["Não é teste no notebook do usuário.","GPU, .NET e execução Docker real não são validadas por esta suíte.","Testes numéricos usam padrões minúsculos; não demonstram capacidade de programação."]}
    args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    sys.exit(0 if result.wasSuccessful() else 1)
