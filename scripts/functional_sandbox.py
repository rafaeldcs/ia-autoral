"""Full application sandbox: loopback only, synthetic DB, no host code execution."""
import json,subprocess,tempfile,uuid
from pathlib import Path

def command(args,timeout=180):
    return subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)

class FunctionalSandbox:
    def __init__(self):
        image=command(['docker','image','inspect','localauthor-functional-lab:1','--format','{{.Id}}'])
        if image.returncode:raise RuntimeError('Functional image unavailable')
        self.image=image.stdout.strip();self.verified=False

    def run(self,source=None,fault='',probe=None):
        name='localauthor-functional-'+uuid.uuid4().hex
        with tempfile.TemporaryDirectory(prefix='localauthor-functional-') as folder:
            if source is not None:Path(folder,'code.txt').write_text(source,encoding='utf-8')
            args=['docker','create','--name',name,'--network','none','--read-only','--user','10001:10001',
                '--cap-drop','ALL','--security-opt','no-new-privileges','--memory','3g','--cpus','2',
                '--pids-limit','512','--tmpfs','/tmp:rw,nosuid,nodev,size=1g,mode=1777',
                '-e','LAB_FAULT='+fault]
            if source is not None:args+=['--mount',f'type=bind,source={folder},target=/input,readonly']
            if probe is not None:args+=['--entrypoint','python3']
            args+=[self.image]
            if probe is not None:args+=['-c',probe]
            result=command(args)
            if result.returncode:raise RuntimeError('Container creation failed: '+result.stderr[-500:])
            try:
                config=json.loads(command(['docker','inspect',name]).stdout)[0];h=config['HostConfig']
                if not(h['NetworkMode']=='none' and h['ReadonlyRootfs'] and not h['Privileged']
                    and not h['PortBindings'] and not h['Devices'] and config['Config']['User']=='10001:10001'
                    and 'ALL' in h['CapDrop'] and 'no-new-privileges' in h['SecurityOpt']
                    and h['Memory']==3*1024**3 and h['NanoCpus']==2000000000 and h['PidsLimit']==512
                    and all(m['Destination']=='/input' and not m['RW'] for m in config['Mounts'] if m['Type']=='bind')):
                    raise RuntimeError('Isolation configuration rejected')
                result=command(['docker','start','-a',name])
                if len(result.stdout)>1_000_000:raise RuntimeError('Excessive output')
                try:return json.loads(result.stdout.strip().splitlines()[-1])
                except (ValueError,IndexError):return {'infrastructureError':'NoReport','output':result.stderr[-1000:]}
            finally:command(['docker','rm','-f',name],timeout=20)

    def verify(self):
        probe="""import os,json,pathlib
s=pathlib.Path('/proc/self/status').read_text();write=False
try:pathlib.Path('/root-canary').write_text('denied');write=True
except OSError:pass
print(json.dumps({'uid':os.getuid(),'caps':'CapEff:\\t0000000000000000' in s,'nnp':'NoNewPrivs:\\t1' in s,'seccomp':'Seccomp:\\t2' in s,'rootWrite':write,'interfaces':sorted(p.name for p in pathlib.Path('/sys/class/net').iterdir())}))"""
        result=self.run(probe=probe)
        if not(result.get('uid')==10001 and result.get('caps') and result.get('nnp') and result.get('seccomp')
            and not result.get('rootWrite') and result.get('interfaces')==['lo']):raise RuntimeError('Canaries failed')
        self.verified=True
        return {'image':self.image,'canaries':result,'database':'discarded PostgreSQL 16','network':'none','hostMounts':'snippet only, read-only'}

    def evaluate(self,case,source):
        if not self.verified:raise RuntimeError('Sandbox not verified')
        # Narrow course accepts only the exact supported grammar for each contract.
        # A different valid implementation is not yet supported; no repairs allowed.
        if source!=case['answer']:
            return {'accepted':False,'passed':False,'reason':'outside_frozen_course_contract','generated':source}
        normal=self.run(source)
        if normal.get('infrastructureError'):return {'accepted':True,'passed':False,'normal':normal,'reason':'infrastructure'}
        fault=self.run(source,fault=case['kind'])
        good=normal.get('exit')==0 and normal.get('stats',{}).get('expected')==1 and normal.get('stats',{}).get('skipped')==0
        killed=fault.get('exit',0)!=0 and fault.get('stats',{}).get('unexpected')==1 and fault.get('assertionFailure') is True
        return {'accepted':True,'passed':good and killed,'correctApplicationPassed':good,'controlledFaultDetected':killed,'normal':normal,'fault':fault}
