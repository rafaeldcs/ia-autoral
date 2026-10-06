#!/usr/bin/python3
"""Install once as a root-owned forced SSH command; only the Orbit recipe is allowed.

Input: gzip tar containing exactly api.tar and web.tar, Docker image archives.
No uploaded script, Compose file, shell command or path is executed on the host.
"""
import fcntl, hashlib, json, os, pathlib, re, shutil, subprocess, sys, tarfile, tempfile, time, urllib.request

ROOT=pathlib.Path('/opt/orbit-hml')
MAX=400*1024**2
def run(*args,**kwargs):
    return subprocess.run(args,check=True,capture_output=True,text=True,timeout=180,**kwargs)
def check_revision(sha):
    request=urllib.request.Request('https://api.github.com/repos/rafaeldcs/ia-autoral/git/ref/heads/codex/local-learning-execution',headers={'User-Agent':'Orbit-HML-deployer','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request,timeout=20) as response:
        data=json.loads(response.read(65537))
    if data['object']['sha']!=sha:raise ValueError('Stale revision rejected')
def compose(*args):
    return run('docker','compose','--project-directory',str(ROOT),'--env-file',str(ROOT/'.env'),'-f',str(ROOT/'compose.yml'),*args)
def environment():
    return dict(line.split('=',1) for line in (ROOT/'.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
def save_environment(values):
    target=ROOT/'.env.new';target.write_text('\n'.join(k+'='+v for k,v in values.items())+'\n');target.chmod(0o600);target.replace(ROOT/'.env')
def health(sha):
    for _ in range(60):
        try:
            req=urllib.request.Request('http://127.0.0.1:8089/api/health',headers={'Host':'orbit.hml-app.shopair.com.br'})
            with urllib.request.urlopen(req,timeout=5) as response:data=json.loads(response.read(4096))
            if data.get('status')=='ok' and data.get('revision')==sha:return
        except Exception:pass
        time.sleep(2)
    raise RuntimeError('Orbit revision health check failed')
def validate_image(path,tag,sha):
    with tarfile.open(path,'r:') as archive:
        manifest=json.load(archive.extractfile('manifest.json'))
        if len(manifest)!=1 or manifest[0].get('RepoTags')!=[tag]:raise ValueError('Unexpected image tags')
        config_name=manifest[0]['Config']
        if not re.fullmatch(r'(?:blobs/sha256/)?[0-9a-f]{64}(?:\.json)?',config_name):raise ValueError('Invalid config path')
        config_bytes=archive.extractfile(config_name).read(1024*1024)
        config=json.loads(config_bytes)
        expected=config_name.removeprefix('blobs/sha256/').removesuffix('.json')
        if hashlib.sha256(config_bytes).hexdigest()!=expected:raise ValueError('Image config digest mismatch')
        c=config['config']
        if c.get('User')!='10001:10001' or c.get('Labels',{}).get('org.opencontainers.image.revision')!=sha:raise ValueError('Image identity check failed')
def main():
    command=os.environ.get('SSH_ORIGINAL_COMMAND','')
    match=re.fullmatch(r'deploy ([0-9a-f]{40})',command)
    if not match:raise ValueError('Only deploy SHA is allowed')
    sha=match[1]
    ROOT.mkdir(mode=0o700,exist_ok=True)
    lock=(ROOT/'deploy.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
    check_revision(sha)
    if shutil.disk_usage(ROOT).free<1024**3:raise ValueError('Insufficient disk capacity; no other applications are cleaned')
    with tempfile.TemporaryDirectory(prefix='incoming-',dir=ROOT) as work:
        work=pathlib.Path(work);bundle=work/'bundle.tgz';total=0
        with bundle.open('wb') as output:
            while chunk:=sys.stdin.buffer.read(1024*1024):
                total+=len(chunk)
                if total>MAX:raise ValueError('Release exceeds upload limit')
                output.write(chunk)
        with tarfile.open(bundle,'r:gz') as archive:
            members=archive.getmembers()
            if sorted(m.name for m in members)!=['api.tar','web.tar']:raise ValueError('Unexpected release contents')
            if any(not m.isfile() or m.size>MAX for m in members) or sum(m.size for m in members)>MAX:raise ValueError('Archive size/type rejected')
            for member in members:
                with (work/member.name).open('wb') as output:shutil.copyfileobj(archive.extractfile(member),output)
        for part in ['api','web']:
            path=work/(part+'.tar');validate_image(path,'orbit-hml-'+part+':'+sha,sha)
            run('docker','load','-i',str(path))
        check_revision(sha)
        old=environment(); previous=old.get('ORBIT_RELEASE_SHA','')
        # Additive schema changes only; backup before restarting this application's single worker.
        if previous:
            backups=ROOT/'backups';backups.mkdir(mode=0o700,exist_ok=True)
            with (backups/(time.strftime('%Y%m%d-%H%M%S')+'.sql')).open('wb') as output:
                r=subprocess.run(['docker','compose','--project-directory',str(ROOT),'exec','-T','db','pg_dump','-U','orbit','orbit'],stdout=output,stderr=subprocess.PIPE,timeout=60)
                if r.returncode:raise RuntimeError('Orbit backup failed')
        save_environment(old|{'ORBIT_RELEASE_SHA':sha})
        try:
            compose('up','-d','--no-build','--pull','never');health(sha)
        except Exception:
            save_environment(old)
            if previous:compose('up','-d','--no-build','--pull','never');health(previous)
            raise
        # Retain only this application's current and immediately preceding runtime image tags.
        for part in ['api','web']:
            images=run('docker','images','--format','{{.Repository}}:{{.Tag}}','orbit-hml-'+part).stdout.splitlines()
            for image in images:
                tag=image.rsplit(':',1)[-1]
                if re.fullmatch('[0-9a-f]{40}',tag) and tag not in [sha,previous]:
                    subprocess.run(['docker','image','rm',image],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        print(json.dumps({'status':'healthy','revision':sha,'application':'orbit-hml'}))
if __name__=='__main__':
    try:main()
    except Exception as error:
        # Do not echo subprocess output, environment, database or SSH credentials.
        print('Orbit deploy failed: '+type(error).__name__,file=sys.stderr);sys.exit(1)
