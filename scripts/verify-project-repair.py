"""Apply only frozen neural outputs to original source in a disposable container."""
import argparse,difflib,hashlib,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src')]
from localauthor.code_repair import parse_request,validate_proposal

p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
if not Path('/.dockerenv').exists():raise RuntimeError('Reviewed Docker sandbox required')
report=json.loads((args.model/'report.json').read_text());certificate=json.loads((args.model/'qualification.json').read_text())
if certificate['state']!='qualified_scoped' or hashlib.sha256((args.model/'best-validation.npz').read_bytes()).hexdigest()!=report['checkpointHash']:raise ValueError('Unqualified or modified checkpoint')
proposal_hash=hashlib.sha256(json.dumps({r['id']:r['generated'] for r in report['test']+report['project']},sort_keys=True).encode()).hexdigest()
if proposal_hash!=certificate.get('proposalHash'):raise ValueError('Proposals changed after independent inference')
args.output.mkdir(parents=True,exist_ok=True)
evidence={'checkpointHash':report['checkpointHash'],'source':'original Git baseline 35586e8','codeAuthor':'local neural repair specialist','application':'mechanical substitution by reviewed harness','results':[]}
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    with tarfile.open(args.baseline) as archive:archive.extractall(root,filter='data')
    targets={path:(root/path).read_text() for path in ('infra/Caddyfile','api/WebAPI/Program.cs')};before=targets.copy()
    for row in report['project']:
        request=parse_request(row['prompt']);generated=validate_proposal(request,row['generated'])
        if row['family']=='caddy':path='infra/Caddyfile';old=row['prompt'].split('\n')[1];replacement=generated
        else:path='api/WebAPI/Program.cs';old=request['validator']+'('+request['expression']+' ?? "")';replacement=generated
        if targets[path].count(old)!=1:raise ValueError('Original source span absent or ambiguous')
        targets[path]=targets[path].replace(old,replacement,1)
    patch=[]
    for path,source in targets.items():
        (root/path).write_text(source);destination=args.output/path;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(source)
        patch.extend(difflib.unified_diff(before[path].splitlines(True),source.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
    (args.output/'neural-proposal.diff').write_text(''.join(patch))
    env={**os.environ,'DOTNET_CLI_HOME':'/tmp/dotnet-home','DOTNET_CLI_TELEMETRY_OPTOUT':'1','NUGET_PACKAGES':'/tmp/nuget'}
    commands=[('caddy',['caddy','validate','--config',str(root/'infra/Caddyfile'),'--adapter','caddyfile']),
              ('api-publish',['dotnet','publish',str(root/'api/WebAPI/WebAPI.csproj'),'-c','Release','-o',str(root/'publish')]),
              ('api-tests',['dotnet','test',str(root/'api/Tests/Tests.csproj'),'-c','Release','--logger','trx;LogFileName=repair.trx','--results-directory',str(args.output/'TestResults')])]
    for name,command in commands:
        result=subprocess.run(command,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240,env=env)
        (args.output/(name+'.log')).write_text(result.stdout);evidence['results'].append({'name':name,'exitCode':result.returncode,'passed':result.returncode==0})
        print(json.dumps(evidence['results'][-1]),flush=True)
    evidence['success']=all(r['passed'] for r in evidence['results'])
    (args.output/'project-verification.json').write_text(json.dumps(evidence,indent=2))
raise SystemExit(0 if evidence['success'] else 1)
