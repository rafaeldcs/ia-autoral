"""Execute reviewed saravaAPP builds/tests in a verified container and fresh copy."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
args = p.parse_args()
if not Path('/.dockerenv').is_file():
    raise RuntimeError('Container required; no host fallback')
args.output.mkdir(exist_ok=False)
results = []
with tempfile.TemporaryDirectory() as directory:
    project = Path(directory) / 'project'
    shutil.copytree(args.source, project, ignore=shutil.ignore_patterns('.env', '.secrets', 'artifacts', '.git', 'node_modules', 'bin', 'obj', '.next'))
    env = {**os.environ, 'NEXT_TELEMETRY_DISABLED': '1', 'DOTNET_CLI_TELEMETRY_OPTOUT': '1',
           'DOTNET_CLI_HOME': '/tmp/dotnet-home', 'NUGET_PACKAGES': '/tmp/nuget',
           'npm_config_cache': '/tmp/npm-cache', 'INTERNAL_API_ORIGIN': 'http://api:8080'}
    commands = [
        ('node-test', ['node', '--test', *map(str, sorted((project / 'app/tests').glob('*.test.mjs')))], project),
        ('processor-dependencies', ['python3', '-c', "from importlib.metadata import version; assert version('Pillow') == '11.3.0'; assert version('pypdf') == '6.0.0'"], project / 'processor'),
        ('processor-test', ['python3', '-m', 'unittest', 'discover'], project / 'processor'),
        ('npm-dependencies', ['npm', 'install', '--ignore-scripts', '--no-audit', '--no-fund'], project / 'app'),
        ('next-build', ['npm', 'run', 'build'], project / 'app'),
        ('dotnet-test', ['dotnet', 'test', 'api/Tests/Tests.csproj', '-c', 'Release', '--logger', 'trx;LogFileName=simulation.trx', '--results-directory', str(args.output / 'TestResults')], project),
        ('dotnet-publish', ['dotnet', 'publish', 'api/WebAPI/WebAPI.csproj', '-c', 'Release', '-o', '/tmp/api-publish'], project),
    ]
    for name, command, cwd in commands:
        result = subprocess.run(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=600)
        (args.output / (name + '.log')).write_text(result.stdout)
        passed = result.returncode == 0
        count = None
        if name == 'node-test':
            total = re.search(r'^# tests (\d+)$', result.stdout, re.M)
            successes = re.search(r'^# pass (\d+)$', result.stdout, re.M)
            count = int(total[1]) if total else 0
            passed = passed and count > 0 and successes is not None and int(successes[1]) == count
        elif name == 'processor-test':
            total = re.search(r'Ran (\d+) tests? in ', result.stdout)
            count = int(total[1]) if total else 0
            passed = passed and count > 0 and re.search(r'^OK\s*$', result.stdout, re.M) is not None
        elif name == 'dotnet-test':
            trx = args.output / 'TestResults/simulation.trx'
            counters = ET.parse(trx).find('.//{*}Counters') if trx.is_file() else None
            count = int(counters.get('total', '0')) if counters is not None else 0
            passed = passed and count > 0 and int(counters.get('passed', '0')) == count
        results.append(dict(name=name, exitCode=result.returncode, passed=bool(passed), **({'tests': count} if count is not None else {})))
        if name == 'npm-dependencies' and result.returncode == 0:
            shutil.copyfile(project / 'app/package-lock.json', args.output / 'resolved-package-lock.json')
        (args.output / 'builds.json').write_text(json.dumps(dict(success=all(r['passed'] for r in results),
             complete=len(results) == len(commands), results=results), indent=2))
        print(json.dumps(results[-1]), flush=True)
        if not passed:
            raise SystemExit(1)
