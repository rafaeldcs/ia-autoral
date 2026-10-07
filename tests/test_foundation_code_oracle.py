"""Artifact/input rejection contracts; no generated code executes in this suite."""
import importlib.util
import json
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from localauthor.errors import PolicyError

spec=importlib.util.spec_from_file_location("code_oracle_contract",Path(__file__).resolve().parents[1]/"scripts/foundation-code-oracle-worker.py")
worker=importlib.util.module_from_spec(spec); spec.loader.exec_module(worker)


class OracleControlTests(unittest.TestCase):
    def test_compilation_error_feedback_keeps_stdout_and_stderr(self):
        with patch.object(worker.subprocess,"run",return_value=SimpleNamespace(returncode=1,stdout="CS0103 fixture missing symbol",stderr="SDK warning fixture")):
            with self.assertRaisesRegex(PolicyError,"CS0103.*SDK warning"):
                worker.run(["dotnet","build"],Path("fixture"))
    def test_unverified_sandbox_rejects_before_reading_candidate_or_input(self):
        with patch.object(worker,"require_isolated_process",side_effect=PolicyError("fixture")), patch.object(worker,"read_object") as read:
            with self.assertRaises(PolicyError):worker.main()
            read.assert_not_called()

    def test_no_format_repairs_truncation_or_duplicate_artifact_can_be_scored(self):
        row={"id":"js-escape","output":json.dumps({"language":"javascript","code":"export function escapeText(){}"}),"possibly_truncated":False,"error":None}
        self.assertTrue(worker.candidate_code({"results":[row]},"js-escape").startswith("export"))
        for candidate in ({"results":[row,row]}, {"results":[{**row,"possibly_truncated":True}]},
                          {"results":[{**row,"output":"```json\n"+row["output"]+"\n```"}]},
                          {"results":[{**row,"output":json.dumps({"language":"shell","code":"ignored"})}]}):
            with self.subTest(candidate=candidate),self.assertRaises((PolicyError,json.JSONDecodeError)):
                worker.candidate_code(candidate,"js-escape")

    def test_inputs_cannot_inject_sql_or_change_integer_contracts(self):
        for task, values in (("sql-order",[[1,"1); DROP TABLE work_items;"]]),("cs-stock",[[True,0]]),
                             ("cs-stock",[[2147483648,0]]),("cs-date",[{}]),("js-escape",["x"*513])):
            with self.subTest(task=task),self.assertRaises(PolicyError):worker.parse_inputs(json.dumps(values),task)
