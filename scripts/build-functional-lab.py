"""Package only reviewed public application sources for the isolated functional lab."""
import argparse, hashlib, json, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--orbit-root', type=Path, required=True)
args = parser.parse_args()
orbit = args.orbit_root.resolve(strict=True)
target = ROOT / 'build' / ('functional-lab-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
target.mkdir(parents=True)
sources = list((orbit/'backend').glob('*.cs')) + [orbit/'backend/Orbit.Api.csproj']
sources += [orbit/'frontend'/name for name in ('package.json','package-lock.json','tsconfig.json','next-env.d.ts','next.config.mjs')]
sources += [p for p in (orbit/'frontend/app').rglob('*') if p.is_file() and p.suffix in {'.ts','.tsx','.css','.svg'}]
manifest = {}
for source in sources:
    if source.is_symlink() or not source.resolve().is_relative_to(orbit):
        raise ValueError('Source alias refused')
    relative = source.relative_to(orbit)
    destination = target/relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    manifest[relative.as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
shutil.copytree(ROOT/'qa/functional-lab', target/'lab')
shutil.copyfile(ROOT/'qa/functional-lab/Dockerfile', target/'Dockerfile')
(target/'source-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
# Deliberate defects exist only in this disposable copy, selected at runtime.
program=target/'backend/Program.cs'
source=program.read_text(encoding='utf-8')
anchor='    context.Response.Headers.CacheControl="no-store";'
faults='''    var fault=Environment.GetEnvironmentVariable("LAB_FAULT");
    var route=context.Request.Path.Value??"";
    if(fault=="login"&&route=="/api/auth/me") {await context.Response.WriteAsJsonAsync(new{name="Fault",role="admin"});return;}
    if(fault=="password"&&route=="/api/users"&&context.Request.Method=="POST") {context.Response.StatusCode=201;await context.Response.WriteAsJsonAsync(new{id=Guid.NewGuid()});return;}
    if(fault=="permissions"&&route.EndsWith("/sprints")&&context.Request.Method=="POST") {context.Response.StatusCode=201;await context.Response.WriteAsJsonAsync(new{id=Guid.NewGuid()});return;}
    if(fault=="metrics"&&route.EndsWith("/flow")) {await context.Response.WriteAsJsonAsync(new{throughput14Days=99});return;}
    if(fault=="sprint"&&route.EndsWith("/complete")) {context.Response.StatusCode=409;await context.Response.WriteAsJsonAsync(new{error="Controlled defect"});return;}
'''
assert source.count(anchor)==1
source=source.replace(anchor,faults+anchor)
anchor='        await next();'
assert source.count(anchor)==1
source=source.replace(anchor,anchor+'''\n        if(fault=="workflow"&&context.Request.Method=="PUT"&&route.StartsWith("/api/issues/"))
            await context.RequestServices.GetRequiredService<Store>().Execute("UPDATE issues SET status='todo' WHERE status='done'");''')
program.write_text(source,encoding='utf-8')
workflow=target/'backend/Workflow.cs';source=workflow.read_text(encoding='utf-8')
assert '>=capacity THEN' in source
workflow.write_text(source.replace('>=capacity THEN',">=(capacity+(CASE WHEN current_setting('app.mutation',true)='wip' THEN 1 ELSE 0 END)) THEN"),encoding='utf-8')
subprocess.run(['docker','build','-t','localauthor-functional-lab:1',str(target)],check=True)
print(json.dumps({'context':str(target),'sourceManifest':str(target/'source-manifest.json')}))
