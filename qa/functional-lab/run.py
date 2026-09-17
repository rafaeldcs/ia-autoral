"""Disposable PostgreSQL + actual Orbit API/Next.js, with one generated Playwright body."""
import glob,json,os,pathlib,secrets,subprocess,time,urllib.request
root=pathlib.Path('/tmp/lab');root.mkdir()
processes=[];logs=[]
pg=pathlib.Path(sorted(glob.glob('/usr/lib/postgresql/*/bin'))[-1])
def command(args):
    return subprocess.run([str(x) for x in args],check=True,capture_output=True,text=True)
def start(args,cwd=None):
    log=(root/(str(len(processes))+'.log')).open('w');logs.append(log)
    p=subprocess.Popen([str(x) for x in args],cwd=cwd,stdout=log,stderr=log);processes.append(p);return p
def wait(url):
    for _ in range(180):
        try:
            with urllib.request.urlopen(url,timeout=1) as response:
                if response.status==200:return
        except Exception:pass
        time.sleep(.2)
    raise RuntimeError('Disposable application failed readiness')
try:
    command([pg/'initdb','-D',root/'pg','-A','trust','--no-locale','--encoding=UTF8'])
    command([pg/'pg_ctl','-D',root/'pg','-l',root/'pg.log','-o','-h 127.0.0.1 -k /tmp','-w','start'])
    command([pg/'createdb','-h','127.0.0.1','orbit'])
    fault=os.environ.get('LAB_FAULT','')
    if fault=='wip':command([pg/'psql','-h','127.0.0.1','-d','orbit','-c',"ALTER DATABASE orbit SET app.mutation='wip'"])
    token=secrets.token_hex(32)
    config=root/'runtime.json'
    config.write_text(json.dumps({'connectionString':'Host=127.0.0.1;Port=5432;Database=orbit;Username=lab','proxyToken':token}))
    os.environ.update(ORBIT_RUNTIME=str(config),ORBIT_PROXY_TOKEN=token)
    api=start(['dotnet','/opt/orbit-api/Orbit.Api.dll'])
    web=start(['node','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3100'],cwd='/opt/orbit-web')
    wait('http://127.0.0.1:3100/api/health')
    # A named pipe accepts one fixed operation; generated code cannot select a PID.
    control=root/'restart';os.mkfifo(control)
    import threading
    def restart():
        nonlocal_state={'api':api}
        with control.open() as pipe:
            if pipe.readline().strip()!='restart':return
        nonlocal_state['api'].terminate();nonlocal_state['api'].wait(timeout=10)
        if fault=='recovery':command([pg/'psql','-h','127.0.0.1','-d','orbit','-c','DELETE FROM issues'])
        start(['dotnet','/opt/orbit-api/Orbit.Api.dll'])
        wait('http://127.0.0.1:3100/api/health')
        (root/'restarted').write_text('ready')
    threading.Thread(target=restart,daemon=True).start()
    snippet=pathlib.Path('/input/code.txt').read_text(encoding='utf-8')
    prefix=pathlib.Path('/opt/functional-lab/prefix.js').read_text()
    (root/'case.spec.js').write_text(prefix+snippet+'\n});',encoding='utf-8')
    result=subprocess.run(['node','/opt/node_modules/@playwright/test/cli.js','test','--config=/opt/functional-lab/playwright.config.js'],capture_output=True,text=True,timeout=90)
    evidence=json.loads((root/'result.json').read_text())
    errors=[]
    def collect(node):
        if isinstance(node,dict):
            for error in node.get('errors',[]):
                if isinstance(error,dict):errors.append(error.get('message',''))
            for key,value in node.items():
                if key!='errors':collect(value)
        elif isinstance(node,list):
            for item in node:collect(item)
    collect(evidence)
    print(json.dumps({'exit':result.returncode,'stats':evidence.get('stats',{}),
        'assertionFailure':any('expect(' in e for e in errors),
        'output':(result.stdout+result.stderr)[-5000:],'errors':errors[-3:]}),flush=True)
except Exception as exc:
    tails={p.name:p.read_text()[-2000:] for p in root.glob('*.log')}
    if 'token' in globals():tails={k:v.replace(token,'[redacted]') for k,v in tails.items()}
    print(json.dumps({'infrastructureError':type(exc).__name__,'detail':str(exc)[-500:],'logs':tails}),flush=True)
finally:
    for p in reversed(processes):
        if p.poll() is None:
            p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill()
    for log in logs:log.close()
