#!/usr/bin/env python3
"""Untrusted code ONLY in inspected sandbox. Emits observations, never decides passes.

The external operator keeps expected results outside this container and compares
every observation. No shell, no production mount, no weights or credentials.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from localauthor.errors import PolicyError
from localauthor.foundation.isolation import require_isolated_process
from localauthor.foundation.models import read_object


def run(argv, cwd, *, data=None, seconds=40):
    result = subprocess.run(argv, cwd=cwd, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=seconds, shell=False)
    if result.returncode or len(result.stdout) > 100000 or len(result.stderr) > 100000:
        raise PolicyError("Child execution rejected: " + str(result.returncode) + "; " + result.stderr[-1500:])
    return result.stdout


def candidate_code(report, task):
    rows = report.get("results") if isinstance(report, dict) else None
    if not isinstance(rows, list): raise PolicyError("Invalid candidate report.")
    matching = [r for r in rows if isinstance(r, dict) and r.get("id") == task]
    if len(matching) != 1 or matching[0].get("possibly_truncated") is not False or matching[0].get("error"):
        raise PolicyError("No complete candidate artifact.")
    value = json.loads(matching[0]["output"])
    language = {"cs-stock": "csharp", "cs-date": "csharp", "js-escape": "javascript", "sql-order": "sql"}[task]
    if (not isinstance(value, dict) or set(value) != {"language", "code"} or value["language"] != language
            or not isinstance(value["code"], str) or not 1 <= len(value["code"]) <= 16000):
        raise PolicyError("Candidate must be the original JSON code artifact; no repairs.")
    return value["code"]


def parse_inputs(raw, task):
    if len(raw) > 20000: raise PolicyError("Input budget exceeded.")
    values = json.loads(raw)
    if not isinstance(values, list) or not 1 <= len(values) <= 40: raise PolicyError("Invalid observation inputs.")
    if task == "cs-stock" and any(not isinstance(v, list) or len(v) != 2 or any(type(n) is not int or not -2147483648 <= n <= 2147483647 for n in v) for v in values):
        raise PolicyError("Invalid stock inputs.")
    if task == "sql-order" and any(not isinstance(v, list) or len(v) != 2 or type(v[0]) is not int or not -2147483648 <= v[0] <= 2147483647 or (v[1] is not None and (type(v[1]) is not int or not -2147483648 <= v[1] <= 2147483647)) for v in values):
        raise PolicyError("Invalid SQL inputs.")
    if task in {"cs-date", "js-escape"} and any(v is not None and (not isinstance(v, str) or len(v) > 512) for v in values):
        raise PolicyError("Invalid string inputs.")
    return values


def observations(task, code, values, directory):
    if task in {"cs-stock", "cs-date"}:
        (directory / "Probe.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><UseAppHost>false</UseAppHost><Nullable>enable</Nullable></PropertyGroup></Project>')
        (directory / "NuGet.Config").write_text('<configuration><packageSources><clear /></packageSources></configuration>')
        (directory / "Solution.cs").write_text(code, encoding="utf-8")
        expr = "StockRules.Available(v[0],v[1])" if task == "cs-stock" else "DateRules.IsIsoDate(v)"
        typ = "int[][]" if task == "cs-stock" else "string?[]"
        driver = f'''using System;
using System.Collections.Generic;
using System.Text.Json;
var input=JsonSerializer.Deserialize<{typ}>(Console.ReadLine()!)!;
var result=new List<object>();
foreach(var v in input) {{
    try {{ result.Add(new {{kind="value", value={expr}}}); }}
    catch(Exception ex) {{ result.Add(new {{kind="error", error=ex.GetType().Name}}); }}
}}
Console.Write(JsonSerializer.Serialize(result));
'''
        (directory / "Program.cs").write_text(driver, encoding="utf-8")
        run(["dotnet", "build", "Probe.csproj", "-c", "Release", "--nologo", "-m:1", "-p:UseSharedCompilation=false"], directory)
        raw = run(["dotnet", str(directory / "bin/Release/net10.0/Probe.dll")], directory, data=json.dumps(values) + "\n", seconds=15)
        return json.loads(raw)
    if task == "js-escape":
        (directory / "solution.mjs").write_text(code, encoding="utf-8")
        (directory / "driver.mjs").write_text('import {escapeText} from "./solution.mjs"; import fs from "node:fs"; const values=JSON.parse(fs.readFileSync(0,"utf8")); process.stdout.write(JSON.stringify(values.map(value=>{try{return {kind:"value",value:escapeText(value)}}catch(error){return {kind:"error",error:error.name}}})));', encoding="utf-8")
        return json.loads(run(["node", str(directory / "driver.mjs")], directory, data=json.dumps(values), seconds=15))
    if task != "sql-order" or not re.match(r"^\s*SELECT\b", code, re.I) or ";" in code.rstrip().rstrip(";"):
        raise PolicyError("Only one SELECT statement is allowed for the SQL observation task.")
    pg = Path("/usr/lib/postgresql/16/bin")
    db = directory / "db"; sock = directory / "sock"; sock.mkdir()
    run([str(pg / "initdb"), "-D", str(db), "-A", "trust", "-U", "lab"], directory)
    run([str(pg / "pg_ctl"), "-D", str(db), "-l", str(directory / "pg.log"), "-o", "-k " + str(sock) + " -h ''", "-w", "start"], directory)
    psql = [str(pg / "psql"), "-h", str(sock), "-U", "lab", "-d", "postgres", "-X", "-v", "ON_ERROR_STOP=1", "-At"]
    try:
        inserts = ",".join("(" + str(v[0]) + "," + ("NULL" if v[1] is None else str(v[1])) + ")" for v in values)
        run(psql + ["-c", "CREATE TABLE work_items(id int PRIMARY KEY,priority int); INSERT INTO work_items VALUES " + inserts], directory)
        raw = run(psql + ["-c", "SET statement_timeout='5s'; " + code], directory, seconds=10)
        # SET is the trusted setup command, not a result row.
        return [int(line) for line in raw.splitlines() if line.strip() != "SET"]
    finally: run([str(pg / "pg_ctl"), "-D", str(db), "-m", "fast", "-w", "stop"], directory)


def main():
    require_isolated_process()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("task", choices=["cs-stock", "cs-date", "js-escape", "sql-order"])
    args = parser.parse_args()
    code = candidate_code(read_object(args.candidate), args.task)
    values = parse_inputs(sys.stdin.read(20001), args.task)
    with tempfile.TemporaryDirectory(prefix="foundation-code-") as temp:
        output = observations(args.task, code, values, Path(temp))
    print(json.dumps({"task": args.task, "observations": output, "qualification_suite": False}, ensure_ascii=False))


if __name__ == "__main__":
    try: main()
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "detail": str(exc), "qualification_suite": False}), file=sys.stderr)
        raise SystemExit(2)
