"""Build the reviewed neural change in an isolated copy; never touch the host project."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--archive', type=Path, required=True)
parser.add_argument('--proposal', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--dependency-lock', type=Path, help='Reuse a preserved lock from a previous dependency-resolution attempt')
args = parser.parse_args()
if not Path('/.dockerenv').is_file():
    raise RuntimeError('Reviewed sandbox required.')
certificate = json.loads((args.proposal / 'qualification.json').read_text())
source = (args.proposal / 'proposed-source.mjs').read_bytes()
test = (args.proposal / 'proposed-test.mjs').read_bytes()
if (certificate['state'] != 'qualified_scoped' or hashlib.sha256(source).hexdigest() != certificate['afterHash']
        or hashlib.sha256(test).hexdigest() != certificate['testHash']
        or hashlib.sha256(args.archive.read_bytes()).hexdigest() != certificate['baselineArchiveHash']):
    raise ValueError('Archive/proposal changed after qualification.')
args.output.mkdir(parents=True, exist_ok=False)
results = []
with tempfile.TemporaryDirectory() as directory:
    project = Path(directory)
    with tarfile.open(args.archive) as archive:
        members = archive.getmembers()
        if len(members) > 5000 or sum(m.size for m in members) > 100_000_000 or any(not (m.isfile() or m.isdir()) for m in members):
            raise ValueError('Unsafe source archive.')
        archive.extractall(project, filter='data')
    target = project / certificate['sourcePath']
    if hashlib.sha256(target.read_bytes()).hexdigest() != certificate['beforeHash']:
        raise ValueError('Baseline mismatch.')
    target.write_bytes(source)
    (project / 'app/tests/local-ai-date-regression.test.mjs').write_bytes(test)
    if args.dependency_lock:
        (project / 'app/package-lock.json').write_bytes(args.dependency_lock.read_bytes())
    env = {**os.environ, 'NEXT_TELEMETRY_DISABLED': '1', 'DOTNET_CLI_TELEMETRY_OPTOUT': '1',
           'DOTNET_CLI_HOME': '/tmp/dotnet-home', 'NUGET_PACKAGES': '/tmp/nuget',
           'npm_config_cache': '/tmp/npm-cache', 'INTERNAL_API_ORIGIN': 'http://api:8080'}
    dependency_mode = 'ci' if (project / 'app/package-lock.json').is_file() else 'install'
    # Match the repository Dockerfile's documented mode; retain the generated lock
    # as evidence, without silently modifying the product checkout.
    commands = [
        ('npm-dependencies', ['npm', dependency_mode, '--ignore-scripts', '--no-audit', '--no-fund'], project / 'app'),
        ('next-build', ['npm', 'run', 'build'], project / 'app'),
        ('dotnet-test', ['dotnet', 'test', 'api/Tests/Tests.csproj', '-c', 'Release', '--logger', 'trx;LogFileName=date-repair.trx', '--results-directory', str(args.output / 'TestResults')], project),
        ('dotnet-publish', ['dotnet', 'publish', 'api/WebAPI/WebAPI.csproj', '-c', 'Release', '-o', '/tmp/api-publish'], project),
    ]
    for name, command, cwd in commands:
        result = subprocess.run(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=420)
        (args.output / (name + '.log')).write_text(result.stdout)
        results.append({'name': name, 'exitCode': result.returncode, 'passed': result.returncode == 0})
        if name == 'npm-dependencies' and result.returncode == 0:
            (args.output / 'resolved-package-lock.json').write_bytes((project / 'app/package-lock.json').read_bytes())
        (args.output / 'builds.json').write_text(json.dumps({'success': all(r['passed'] for r in results), 'complete': len(results) == len(commands), 'results': results}, indent=2))
        print(json.dumps(results[-1]), flush=True)
        if result.returncode:
            raise SystemExit(1)
