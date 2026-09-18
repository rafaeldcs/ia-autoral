"""Ask LocalAuthor's own policy and isolated browser to capture public pages.

No CUA/Codex browser is used. Target URLs are user-supplied, not discovered by
the model. Authentication/click automation is intentionally not implemented.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
from urllib.parse import urlsplit

SOURCE_ROOT = Path(__file__).resolve().parents[1]
from .research import validate_url, public_addresses


def command(args, timeout=30):
    return subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,check=True)


def capture(urls, policy_report, home, asset_hosts=()):
    if not isinstance(urls, list) or not 1 <= len(urls) <= 12:
        raise ValueError('Use 1..12 explicitly requested public URLs.')
    hosts=sorted(set([urlsplit(url).hostname or '' for url in urls]+list(asset_hosts)))
    pins={}
    for host in hosts:
        validate_url('https://'+host,[host]); pins[host]=public_addresses(host)[0]
    for url in urls: validate_url(url,hosts)
    report=json.loads(policy_report.read_text(encoding='utf-8'))
    checkpoint=Path(report['selectedCheckpoint'])
    if not report.get('labApproved') or hashlib.sha256(checkpoint.read_bytes()).hexdigest()!=report['checkpointHash']:
        raise ValueError('Policy must match its approved bounded investigation report.')
    name='localauthor-capture-'+uuid.uuid4().hex
    output=home/'investigations'/('own-browser-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    output.mkdir(parents=True)
    image=command(['docker','image','inspect','localauthor-functional-lab:1','--format','{{.Id}}']).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='localauthor-browser-input-') as folder:
        source=Path(folder)
        shutil.copyfile(checkpoint,source/'policy.npz')
        (source/'job.json').write_text(json.dumps({'urls':urls,'allowedHosts':hosts}),encoding='utf-8')
        create=['docker','create','--name',name,'--network','bridge','--read-only','--user','10001:10001',
            '--cap-drop','ALL','--security-opt','no-new-privileges','--memory','2g','--cpus','2','--pids-limit','256',
            '--tmpfs','/tmp:rw,nosuid,nodev,size=512m,mode=1777','--shm-size','128m',
            '--mount',f'type=bind,source={source},target=/input,readonly',
            '--mount',f'type=bind,source={SOURCE_ROOT},target=/runtime/src,readonly',
            '--mount',f'type=bind,source={output},target=/output',
            '--env','HOME=/tmp','--env','PYTHONDONTWRITEBYTECODE=1','--entrypoint','sleep']
        for host,address in pins.items(): create+=['--add-host',host+':'+address]
        create += [image,'300']
        command(create)
        try:
            config=json.loads(command(['docker','inspect',name]).stdout)[0]; h=config['HostConfig']
            mounts={m['Destination']:m['RW'] for m in config['Mounts'] if m['Type']=='bind'}
            if not (h['NetworkMode']=='bridge' and h['ReadonlyRootfs'] and not h['Privileged']
                and not h['PortBindings'] and not h['Devices'] and config['Config']['User']=='10001:10001'
                and 'ALL' in h['CapDrop'] and 'no-new-privileges' in h['SecurityOpt']
                and mounts=={'/input':False,'/runtime/src':False,'/output':True}
                and h['Memory']==2*1024**3 and h['NanoCpus']==2_000_000_000 and h['PidsLimit']==256):
                raise RuntimeError('Browser container isolation was not verified.')
            command(['docker','start',name])
            probe="import os,json,pathlib; s=pathlib.Path('/proc/self/status').read_text(); print(json.dumps({'uid':os.getuid(),'caps':'CapEff:\\t0000000000000000' in s,'nnp':'NoNewPrivs:\\t1' in s,'seccomp':'Seccomp:\\t2' in s}))"
            canary=json.loads(command(['docker','exec',name,'python3','-c',probe]).stdout)
            if canary!={'uid':10001,'caps':True,'nnp':True,'seccomp':True}:
                raise RuntimeError('Browser sandbox canary failed.')
            receipt={'image':image,'canary':canary,'network':'public DNS-pinned hosts; browser GET/HEAD allowlist',
                     'allowedHosts':hosts,'policyHash':report['checkpointHash'],
                     'executor':'LocalAuthor browser worker','codexCapturedImages':False}
            (output/'runtime.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
            print(json.dumps({'output':str(output),'state':'local_ai_browser_running'}),flush=True)
            run=command(['docker','exec',name,'node','/runtime/src/localauthor/capture_browser.cjs'],timeout=240)
            print(run.stdout.strip())
            captures=json.loads((output/'captures.json').read_text(encoding='utf-8'))
            if len(captures) != len(urls):
                raise RuntimeError('Browser did not return evidence for every requested page.')
            for index, item in enumerate(captures):
                if item['state']=='captured':
                    if item['file'] != f'{index+1:03d}.png':
                        raise RuntimeError('Unexpected capture artifact path.')
                    png=(output/item['file']).read_bytes()
                    if not png.startswith(b'\x89PNG\r\n\x1a\n') or hashlib.sha256(png).hexdigest()!=item['sha256']:
                        raise RuntimeError('Capture artifact verification failed.')
            if not all(c['state']=='captured' for c in captures):
                raise RuntimeError('Some pages were not captured; inspect captures.json in '+str(output))
        finally:
            command(['docker','rm','-f',name])
    return {'output':str(output),'captured':len(captures),'total':len(urls),
            'executor':'LocalAuthor isolated browser','allSitesQualified':False}
