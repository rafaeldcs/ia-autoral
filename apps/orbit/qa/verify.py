"""Trusted QA entry point, run only after the container isolation check."""
import json, os, pathlib, shutil, subprocess, sys

os.environ.update(HOME='/tmp', NEXT_TELEMETRY_DISABLED='1', DOTNET_CLI_TELEMETRY_OPTOUT='1')
evidence = pathlib.Path('/tmp/evidence')
evidence.mkdir(exist_ok=True)
checks = []
def execute(name, command, cwd=None):
    with (evidence/(name+'.log')).open('w') as log:
        r = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
    checks.append({'check':name,'exit_code':r.returncode})
    (evidence/'build.json').write_text(json.dumps(checks,indent=2))
    if r.returncode:
        print((evidence/(name+'.log')).read_text()[-8000:])
        raise RuntimeError(name+' failed')

execute('deployment-policy',['python3','/input/qa/test_deployment.py'])
for item in ['backend','frontend','qa']:
    shutil.copytree('/input/'+item,'/tmp/'+item,dirs_exist_ok=True,ignore=shutil.ignore_patterns('node_modules','.next','bin','obj','artifacts'))
shutil.copytree('/opt/orbit-web/node_modules','/tmp/frontend/node_modules',dirs_exist_ok=True)
execute('api-build',['dotnet','publish','/tmp/backend/Orbit.Api.csproj','-c','Release','-o','/tmp/api','-p:NuGetAudit=false','-p:RestoreIgnoreFailedSources=true'])
execute('unit',['dotnet','test','/tmp/qa/Orbit.Testing.Reference/Orbit.Testing.Reference.csproj','-c','Release','-p:NuGetAudit=false','-p:RestoreIgnoreFailedSources=true','--logger','trx;LogFileName=unit.trx','--results-directory',str(evidence)])
execute('web-build',['node','node_modules/next/dist/bin/next','build','--webpack'],'/tmp/frontend')
shutil.copytree('/tmp/frontend/.next/standalone','/tmp/web',dirs_exist_ok=True)
shutil.copytree('/tmp/frontend/.next/static','/tmp/web/.next/static',dirs_exist_ok=True)
if pathlib.Path('/tmp/frontend/public').exists():
    shutil.copytree('/tmp/frontend/public','/tmp/web/public',dirs_exist_ok=True)
execute('functional',['python3','/tmp/qa/functional.py'])
print('All configured build, unit, API and browser checks completed.')
