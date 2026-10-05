#!/usr/bin/env python3
"""Verify original teaching answers in the fixed local laboratory, no approvals."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from localauthor.foundation.isolation import require_isolated_process
from localauthor.foundation.models import digest, read_object, write_new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-directory", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    isolation = require_isolated_process()
    data = args.dataset_directory
    if args.report.exists(): parser.error("Use relatório novo.")
    javascript = subprocess.run(["node", str(data / "verification/check.cjs")],
                               capture_output=True, text=True, timeout=30, check=True)
    js = json.loads(javascript.stdout)
    if js != {"success": True, "assertions": 3}: raise AssertionError("Missing JavaScript assertions")
    binaries = sorted(Path("/usr/lib/postgresql").glob("*/bin/initdb"))
    if len(binaries) != 1: raise RuntimeError("Choose one explicit PostgreSQL runtime")
    pg = binaries[0].parent
    with tempfile.TemporaryDirectory() as tmp:
        temporary = Path(tmp); database = temporary / "pg"
        subprocess.run([str(pg / "initdb"), "-D", str(database), "-A", "trust", "--no-locale"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30, check=True)
        subprocess.run([str(pg / "pg_ctl"), "-D", str(database), "-l", str(temporary / "pg.log"),
                        "-o", f"-k {temporary} -h '' -p 15432", "-w", "start"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30, check=True)
        try:
            sql = subprocess.run([str(pg / "psql"), "-h", str(temporary), "-p", "15432", "-d", "postgres",
                       "-At", "-v", "ON_ERROR_STOP=1", "-f", str(data / "verification/check.sql")],
                       capture_output=True, text=True, timeout=30, check=True)
            actual = sql.stdout.splitlines()
            if actual[-4:] != ["2", "4", "1", "3"]:
                raise AssertionError("NULL ordering/tie-break failed")
        finally:
            subprocess.run([str(pg / "pg_ctl"), "-D", str(database), "-w", "-m", "fast", "stop"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30, check=True)
    dataset = read_object(data / "dataset-pending.json")
    report = {"status": "technical-subset-verified-not-human-approved", "isolation": isolation,
              "dataset_sha256": digest(data / "dataset-pending.json"), "javascript": js,
              "postgresql": {"success": True, "rows": actual[-4:], "binary": str(pg)},
              "teacher": "Codex original teaching examples", "local_model_trained": False,
              "human_approval": False, "literary_answers": "pending human review",
              "source_hashes": {k: v["sha256"] for k, v in dataset["sources"].items()}}
    write_new(args.report, report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__": main()
