"""Execute frozen neural proposals with real Caddy and .NET, in Docker only."""
import argparse,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src')]
from localauthor.code_repair import parse_request,validate_proposal,SCOPE
from localauthor.nn.checkpoint import load_checkpoint

def run(command,cwd=None):
    result=subprocess.run(command,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120,
        env={**os.environ,'DOTNET_CLI_HOME':'/tmp/dotnet-home','DOTNET_SKIP_FIRST_TIME_EXPERIENCE':'1','DOTNET_CLI_TELEMETRY_OPTOUT':'1','NUGET_PACKAGES':'/tmp/nuget'})
    return result.returncode,result.stdout

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);args=p.parse_args();root=args.model
    if not Path('/.dockerenv').exists():raise RuntimeError('Run only in the reviewed Docker laboratory')
    report=json.loads((root/'report.json').read_text());checkpoint=root/'best-validation.npz'
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest()!=report['checkpointHash']:raise ValueError('Checkpoint changed')
    raw=(root/'frozen-course.json').read_bytes();frozen=json.loads(raw)
    if hashlib.sha256(raw).hexdigest()!=report['provenance']['corpusHash']:raise ValueError('Frozen evaluation changed')
    model,_,tokenizer,_,meta=load_checkpoint(checkpoint)
    if meta['provenance']['corpusHash']!=report['provenance']['corpusHash']:raise ValueError('Checkpoint belongs to another curriculum')
    cases=[]
    for split in ('test','project'):
        for row in frozen[split]:
            # Reproduce from weights now. Never trust editable generated text in a report.
            ids=model.generate([256]+tokenizer.encode(row['prompt']),max_tokens=100,temperature=.05,seed=31)
            source=tokenizer.decode(ids)
            cases.append({**row,'split':split,'generated':source,'exact':source==row['answer']})
    proposal_hash=hashlib.sha256(json.dumps({r['id']:r['generated'] for r in cases},sort_keys=True).encode()).hexdigest()
    results=[];mutations=[]
    cs=[]
    with tempfile.TemporaryDirectory() as folder:
        folder=Path(folder)
        for row in cases:
            request=parse_request(row['prompt']);source=validate_proposal(request,row['generated'])
            if row['family']=='caddy':
                prefix=':8088 {\n'+(f"    {request['matcher']} path /api/*\n" if request['matcher'] else '')
                path=folder/(row['id']+'.caddy');path.write_text(prefix+source+'\n}\n')
                code,log=run(['caddy','validate','--adapter','caddyfile','--config',str(path)])
                results.append({'id':row['id'],'family':'caddy','passed':code==0,'log':log})
                # Same parser must reject the original malformed inline block.
                broken=row['prompt'].split('\n')[1];path.write_text(prefix+broken+'\n}\n')
                code,log=run(['caddy','validate','--adapter','caddyfile','--config',str(path)])
                mutations.append({'id':row['id'],'kind':'original-inline-block','detected':code!=0,'log':log})
            else:cs.append((row,request,source))
        project=folder/'csharp';project.mkdir()
        (project/'Repair.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><ImplicitUsings>enable</ImplicitUsings></PropertyGroup></Project>')
        (project/'NuGet.Config').write_text('<configuration><packageSources><clear /></packageSources></configuration>')
        def program(use_generated):
            methods=[];invocations=[]
            for index,(row,request,source) in enumerate(cs):
                obj,prop=request['expression'].split('.');condition=source if use_generated else request['validator']+'('+request['expression']+' ?? "")'
                methods.append(f'''static void Repair{index}(Data {obj}) {{ Rules.Require({condition}); Rules.Hash({request['expression']}); }}''')
                invocations.append(f'''Check(() => Repair{index}(new Data {{ {prop}=null }}), false);
Check(() => Repair{index}(new Data {{ {prop}="" }}), false);
Check(() => Repair{index}(new Data {{ {prop}="bad" }}), false);
Check(() => Repair{index}(new Data {{ {prop}="https://valid.test" }}), true);''')
            return '''using System.Diagnostics.CodeAnalysis;
class Data { public string? Endpoint {get;set;} public string? Url {get;set;} public string? Address {get;set;} public string? Name {get;set;} }
static class Rules {
public static void Require([DoesNotReturnIf(false)]bool valid){if(!valid)throw new ArgumentException("Rejected");}
public static bool ValidPushEndpoint(string s)=>s.StartsWith("https://");
public static bool ValidText(string s)=>s.StartsWith("https://");
public static bool IsAllowed(string s)=>s.StartsWith("https://");
public static string Hash(string value)=>value.ToUpperInvariant();
}
class Program {
static int checks;
static void Check(Action action,bool expected){bool accepted;try{action();accepted=true;}catch(ArgumentException){accepted=false;}if(accepted!=expected)throw new Exception("Behavior mismatch");checks++;}
'''+ '\n'.join(methods)+'\nstatic void Main(){\n'+'\n'.join(invocations)+'\nConsole.WriteLine("CHECKS="+checks);}\n}'
        (project/'Program.cs').write_text(program(True))
        code,log=run(['dotnet','build',str(project/'Repair.csproj'),'-c','Release'],project)
        if code==0:
            code,execution=run(['dotnet',str(project/'bin/Release/net10.0/Repair.dll')],project)
            log+='\n'+execution
        (root/'csharp-execution.log').write_text(log)
        passed=code==0 and f'CHECKS={4*len(cs)}' in log
        for row,_,_ in cs:results.append({'id':row['id'],'family':'csharp','passed':passed,'behaviorChecks':4})
        (project/'Program.cs').write_text(program(False))
        code,log=run(['dotnet','build',str(project/'Repair.csproj'),'-c','Release','--no-restore'],project)
        mutations.append({'kind':'original-null-coalescing-guard','detected':code!=0 and 'CS8604' in log,'log':log})
    gates={
        'heldout':{'total':len(frozen['test']),'passed':sum(r['exact'] and r['split']=='test' for r in cases)},
        'project':{'total':len(frozen['project']),'passed':sum(r['exact'] and r['split']=='project' for r in cases)},
        **{family:{'total':sum(r['family']==family for r in results),'passed':sum(r['family']==family and r['passed'] for r in results)} for family in ('caddy','csharp')},
        'mutations':{'total':len(mutations),'passed':sum(r['detected'] for r in mutations)}}
    success=all(x['total']>0 and x['total']==x['passed'] for x in gates.values())
    final={'state':'qualified_scoped' if success else 'rejected','scope':SCOPE,'generalProgrammingQualified':False,
           'checkpoint':root.name+'/best-validation.npz','checkpointHash':report['checkpointHash'],'proposalHash':proposal_hash,'gates':gates,
           'runtimeResults':results,'mutationResults':mutations,'limitations':['Two familiar families with reserved parameter combinations','No general site/programming qualification','Caller must review and test any application to a project']}
    (root/'qualification.json').write_text(json.dumps(final,indent=2))
    print(json.dumps({'state':final['state'],'gates':gates}));raise SystemExit(0 if success else 1)

if __name__=='__main__':main()
