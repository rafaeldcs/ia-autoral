"""Trusted finite evaluator. Generated artifacts run ONLY after isolation canaries."""
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path('/tmp/chat-code')
ENV = {**os.environ, 'HOME':'/tmp', 'DOTNET_CLI_HOME':'/tmp',
       'DOTNET_CLI_TELEMETRY_OPTOUT':'1', 'DOTNET_SKIP_FIRST_TIME_EXPERIENCE':'1',
       'DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE':'true', 'NUGET_PACKAGES':'/opt/packages',
       'NEXT_TELEMETRY_DISABLED':'1', 'NODE_OPTIONS':'--max-old-space-size=1536',
       'UV_THREADPOOL_SIZE':'2', 'RAYON_NUM_THREADS':'1', 'LANG':'C.UTF-8'}
report = {'stages':[], 'files':{}, 'cases':[]}


def command(argv, cwd=ROOT, seconds=120):
    start=time.monotonic()
    try:
        result=subprocess.run(argv,cwd=cwd,env=ENV,capture_output=True,text=True,timeout=seconds)
        output=(result.stdout+'\n'+result.stderr)[-100_000:]
        record={'argv':argv,'exit_code':result.returncode,'seconds':round(time.monotonic()-start,3),'output':output}
    except subprocess.TimeoutExpired:
        record={'argv':argv,'exit_code':-1,'seconds':seconds,'output':'Evaluator child timeout'}
    report['stages'].append(record)
    return record


def require(record):
    if record['exit_code']:raise RuntimeError(record['output'][-5000:])
    return record['output'].strip()


def artifact(name, data):
    report['files'][name]=base64.b64encode(data).decode('ascii')


def canaries():
    fields=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    interfaces=sorted(p.name for p in Path('/sys/class/net').iterdir())
    root_ro=any(line.split()[1]=='/' and 'ro' in line.split()[3].split(',') for line in Path('/proc/mounts').read_text().splitlines())
    result={'uid':os.getuid(),'interfaces':interfaces,'root_readonly':root_ro,
            'capabilities':fields['CapEff'].strip(),'no_new_privileges':fields['NoNewPrivs'].strip(),
            'seccomp':fields['Seccomp'].strip()}
    if not (result['uid']==10001 and interfaces==['lo'] and root_ro and result['capabilities']=='0000000000000000'
            and result['no_new_privileges']=='1' and result['seccomp']=='2'):
        raise RuntimeError('Isolation canaries rejected')
    return result


def csharp(files, mutation):
    work=ROOT/'csharp';work.mkdir()
    for name in ('Tarefa.cs','TarefaService.cs','GeneratedTests.cs'):
        source=files[name]
        if mutation:
            if name=='TarefaService.cs':
                if source.count('tarefa.Concluir();')!=1:raise RuntimeError('Mutation site missing')
                source=source.replace('tarefa.Concluir();','return; // controlled evaluator mutation')
        (work/name).write_bytes(source.encode('utf-8'))
    (work/'IndependentContracts.cs').write_bytes(Path('/runner/contracts.cs').read_bytes())
    (work/'Replay.csproj').write_text('''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>
<TargetFramework>net10.0</TargetFramework><IsTestProject>true</IsTestProject><IsPackable>false</IsPackable>
<Nullable>enable</Nullable><ImplicitUsings>disable</ImplicitUsings><NuGetAudit>false</NuGetAudit>
</PropertyGroup><ItemGroup><PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.14.1" />
<PackageReference Include="xunit" Version="2.9.3" /><PackageReference Include="xunit.runner.visualstudio" Version="3.1.4" />
</ItemGroup></Project>''')
    (work/'NuGet.Config').write_text('<configuration><packageSources><clear /></packageSources></configuration>')
    require(command(['dotnet','restore','Replay.csproj','--configfile','NuGet.Config','-p:NuGetAudit=false'],work))
    build=command(['dotnet','build','Replay.csproj','--no-restore','-c','Release','--nologo','-m:1','-p:UseSharedCompilation=false'],work)
    report['csharp_build_passed']=build['exit_code']==0
    if build['exit_code']:return
    test=command(['dotnet','test','Replay.csproj','--no-build','--no-restore','-c','Release','--logger','trx;LogFileName=results.trx','--results-directory','results'],work)
    trx=work/'results/results.trx'
    if not trx.is_file():raise RuntimeError('Missing actual xUnit TRX')
    artifact('csharp-results.trx',trx.read_bytes())
    tree=ET.parse(trx);ns={'t':'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}
    for row in tree.findall('.//t:UnitTestResult',ns):
        report['cases'].append({'area':'csharp','name':row.attrib['testName'],'passed':row.attrib['outcome']=='Passed',
                                'outcome':row.attrib['outcome']})
    report['csharp_test_exit']=test['exit_code']


def frontend(files, mutation):
    work=ROOT/'web';work.mkdir();(work/'app').mkdir()
    (work/'node_modules').symlink_to('/opt/orbit-web/node_modules',target_is_directory=True)
    source=files['ListaTarefas.tsx']
    if mutation:
        source,count=re.subn(r'concluida:\s*true','concluida: false',source,count=1)
        if count!=1:raise RuntimeError('Frontend mutation site missing')
    (work/'app/ListaTarefas.tsx').write_bytes(source.encode('utf-8'))
    (work/'package.json').write_bytes(Path('/opt/orbit-web/package.json').read_bytes())
    (work/'tsconfig.json').write_text(json.dumps({'compilerOptions':{'target':'ES2020','lib':['dom','esnext'],
        'strict':True,'noEmit':True,'skipLibCheck':True,'esModuleInterop':True,'module':'esnext',
        'moduleResolution':'bundler','jsx':'react-jsx','plugins':[{'name':'next'}]},'include':['app/**/*.tsx','next-env.d.ts','.next/types/**/*.ts']}))
    (work/'app/layout.tsx').write_text('export default function Layout({children}:{children:React.ReactNode}) {return <html lang="pt-BR"><body style={{margin:8}}>{children}</body></html>;}')
    tasks=[{'id':1,'titulo':'Revisar código','concluida':False},{'id':2,'titulo':'Escrever testes','concluida':False},
           {'id':3,'titulo':'Documentar API','concluida':True}]
    for route,values in [('',tasks),('empty',[]),('escape',[{'id':9,'titulo':'<img src=x onerror="window.INJECTED=1">','concluida':False}])]:
        folder=work/'app'/route;folder.mkdir(exist_ok=True)
        relative='./' if not route else '../'
        (folder/'page.tsx').write_text('import Lista from "'+relative+'ListaTarefas"; export default function Page(){return <main><h1>Teste real — LocalAuthor</h1><Lista tarefasIniciais={'+json.dumps(values,ensure_ascii=False)+'}/></main>;}')
    (work/'next.config.js').write_text('module.exports={experimental:{cpus:1,webpackBuildWorker:false}};')
    types=command(['node','node_modules/typescript/bin/tsc','--noEmit'],work)
    report['tsx_typecheck_passed']=types['exit_code']==0
    if types['exit_code']:return
    build=command(['node','node_modules/next/dist/bin/next','build','--webpack'],work,seconds=180)
    report['next_build_passed']=build['exit_code']==0
    if build['exit_code']:return
    with (work/'server.log').open('w') as log:
        server=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3217'],cwd=work,env=ENV,stdout=log,stderr=subprocess.STDOUT)
        try:
            for _ in range(60):
                if server.poll() is not None:raise RuntimeError('Next server exited')
                try:
                    urllib.request.urlopen('http://127.0.0.1:3217/',timeout=1).close();break
                except OSError:time.sleep(.5)
            else:raise RuntimeError('Next server not ready')
            require(command(['node','/runner/browser.mjs'],work,seconds=90))
            browser=json.loads((ROOT/'browser-results.json').read_text())
            report['cases'].extend({'area':'tsx',**row} for row in browser['results'])
            for name,data in browser['screenshots'].items():report['files'][name]=data
        finally:
            server.terminate()
            try:server.wait(timeout=10)
            except subprocess.TimeoutExpired:server.kill();server.wait()
    artifact('next-server.txt',(work/'server.log').read_bytes()[-30000:])


def postgres(files, mutation):
    work=ROOT/'pg';work.mkdir();sock=work/'sock';sock.mkdir()
    pg=Path('/usr/lib/postgresql/16/bin')
    require(command([str(pg/'initdb'),'-D',str(work/'db'),'-A','trust','-U','lab','--no-locale','--encoding=UTF8'],work))
    require(command([str(pg/'pg_ctl'),'-D',str(work/'db'),'-l',str(work/'server.log'),'-o','-k '+str(sock)+" -h ''",'-w','start'],work))
    psql=[str(pg/'psql'),'-h',str(sock),'-U','lab','-d','postgres','-X','-q','-At','-v','ON_ERROR_STOP=1','-v','VERBOSITY=verbose']
    def check(name,sql,expected=None,state=None):
        result=command(psql+['-c',sql],work,seconds=15)
        actual=result['output'].strip()
        passed=(result['exit_code']!=0 and state in actual) if state else (result['exit_code']==0 and actual==expected)
        report['cases'].append({'area':'sql','name':name,'passed':bool(passed),'expected':state or expected,'actual':actual[-3000:]})
    source=files['tarefas.sql']
    if mutation:
        target='CHECK (LENGTH(TRIM(titulo)) > 0)'
        if source.count(target)!=1:raise RuntimeError('SQL mutation site missing')
        source=source.replace(target,'CHECK (TRUE)')
    (work/'generated.sql').write_bytes(source.encode('utf-8'))
    try:
        loaded=command(psql+['-f','generated.sql'],work)
        report['sql_script_passed']=loaded['exit_code']==0
        if loaded['exit_code']:return
        check('identity_always',"SELECT is_identity||'|'||identity_generation FROM information_schema.columns WHERE table_name='tarefas' AND column_name='id'",'YES|ALWAYS')
        check('integer_id',"SELECT data_type FROM information_schema.columns WHERE table_name='tarefas' AND column_name='id'",'integer')
        check('title_not_null',"SELECT is_nullable FROM information_schema.columns WHERE table_name='tarefas' AND column_name='titulo'",'NO')
        check('default_false',"INSERT INTO tarefas(titulo) VALUES ('Padrão') RETURNING concluida",'f')
        check('reject_null',"INSERT INTO tarefas(titulo) VALUES (NULL)",state='23502')
        check('reject_empty',"INSERT INTO tarefas(titulo) VALUES ('')",state='23514')
        check('reject_spaces',"INSERT INTO tarefas(titulo) VALUES ('   ')",state='23514')
        check('unicode_and_quotes',"INSERT INTO tarefas(titulo) VALUES ('ação d''água') RETURNING titulo", "ação d'água")
        check('identity_disallows_explicit_id',"INSERT INTO tarefas(id,titulo) VALUES (700,'manual')",state='428C9')
        require(command(psql+['-c',"INSERT INTO tarefas(id,titulo,concluida) OVERRIDING SYSTEM VALUE VALUES (900,'Alta',false),(100,'Baixa',false),(500,'Feita',true)"],work))
        observed=require(command(psql+['-c','SELECT id,titulo,concluida FROM tarefas'],work)).splitlines()
        expected='\n'.join(sorted((row for row in observed if row.endswith('|f')),key=lambda row:int(row.split('|')[0])))
        statements=[part.strip() for part in source.split(';') if part.strip()]
        if len(statements)!=2 or not statements[1].upper().startswith('SELECT'):raise RuntimeError('Expected the original CREATE and SELECT artifact')
        check('original_pending_query_orders_and_filters',statements[1],expected)
        check('update_cannot_blank_title',"UPDATE tarefas SET titulo='   ' WHERE id=100",state='23514')
        check('transaction_rollback',"BEGIN; INSERT INTO tarefas(titulo) VALUES ('Somente rollback'); ROLLBACK; SELECT COUNT(*) FROM tarefas WHERE titulo='Somente rollback'",'0')
        check('positive_generated_ids',"SELECT bool_and(id>0) FROM tarefas",'t')
    finally:
        require(command([str(pg/'pg_ctl'),'-D',str(work/'db'),'-m','fast','-w','stop'],work))


def main():
    report['canaries']=canaries()
    raw=sys.stdin.buffer.read(1_000_001)
    if len(raw)>1_000_000:raise RuntimeError('Input limit exceeded')
    payload=json.loads(raw);files=payload['files'];mode=payload['mode']
    ROOT.mkdir()
    report['versions']={'dotnet':require(command(['dotnet','--version'])),
                        'node':require(command(['node','--version'])),
                        'postgres':require(command(['/usr/lib/postgresql/16/bin/postgres','--version']))}
    for name,execute in [('csharp',csharp),('tsx',frontend),('sql',postgres)]:
        try:execute(files,mode=='mutations')
        except Exception as exc:report[name+'_error']=str(exc)[-6000:]
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'infrastructure_error':str(exc),'partial':report}));sys.exit(2)
