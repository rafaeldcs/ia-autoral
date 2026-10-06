"""Trusted controller: execute project code only in a verified Linux container."""
import argparse, io, json, os, pathlib, subprocess, sys, tarfile, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
def run(*args):
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError('Controller command failed: '+result.stderr[-2000:])
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--image', required=True)
    p.add_argument('--sha', required=True)
    a = p.parse_args()
    if len(a.sha) != 40 or any(c not in '0123456789abcdef' for c in a.sha):
        raise ValueError('A full immutable SHA is required')
    image = run('docker', 'image', 'inspect', a.image, '--format', '{{.Id}}').stdout.strip()
    container = run('docker', 'create', '--network', 'none', '--read-only', '--user', '10001:10001',
        '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--memory', '3g', '--memory-swap', '3g',
        '--cpus', '3', '--pids-limit', '256', '--tmpfs', '/tmp:rw,exec,nosuid,nodev,size=4g',
        '--mount', f'type=bind,src={ROOT},dst=/input,readonly',
        '-e', f'ORBIT_RELEASE_SHA={a.sha}', '-e', 'NEXT_PUBLIC_ORBIT_HOSTED=1',
        '--entrypoint', 'sleep', image, 'infinity').stdout.strip()
    info = json.loads(run('docker', 'inspect', container).stdout)[0]
    h, config, mounts = info['HostConfig'], info['Config'], info['Mounts']
    assert info['Image'] == image and config['User'] == '10001:10001'
    assert h['NetworkMode'] == 'none' and h['ReadonlyRootfs'] and not h['Privileged']
    assert h['CapDrop'] == ['ALL'] and 'no-new-privileges' in h['SecurityOpt']
    assert h['Memory'] == h['MemorySwap'] == 3*1024**3 and h['NanoCpus'] == 3_000_000_000
    assert h['PidsLimit'] == 256 and not h['PortBindings']
    assert h['Tmpfs'] == {'/tmp': 'rw,exec,nosuid,nodev,size=4g'}
    assert len(mounts) == 1 and mounts[0]['Type'] == 'bind' and not mounts[0]['RW'] and mounts[0]['Destination'] == '/input'
    expected = str(ROOT).replace('\\', '/').lower()
    assert mounts[0]['Source'].replace('\\', '/').lower() in [expected, '/run/desktop/mnt/host/'+expected[0]+expected[2:]]
    output = ROOT / 'artifacts'
    output.mkdir(exist_ok=True)
    (output/'isolation.json').write_text(json.dumps({'container':container,'image':image,'sha':a.sha,'verified':True}),encoding='utf-8')
    run('docker', 'start', container)
    def export(source, target):
        # Docker cp cannot read tmpfs. Recheck the isolation before the read-only export command.
        current=json.loads(run('docker','inspect',container).stdout)[0]
        assert current['State']['Running'] and current['Image']==image
        security=['NetworkMode','ReadonlyRootfs','Privileged','CapDrop','SecurityOpt','Memory','MemorySwap','NanoCpus','PidsLimit','Tmpfs','Binds','Mounts']
        assert all(current['HostConfig'][key]==h[key] for key in security)
        assert not current['HostConfig']['PortBindings'] and current['Mounts']==mounts
        assert current['Config']['User']=='10001:10001' and current['Config']['Entrypoint']==['sleep']
        stream=subprocess.run(['docker','exec',container,'tar','-chf','-','-C',source,'.'],capture_output=True,check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(stream),mode='r:') as archive:
            members=archive.getmembers()
            assert all((m.isfile() or m.isdir()) and not pathlib.PurePosixPath(m.name).is_absolute() and '..' not in pathlib.PurePosixPath(m.name).parts for m in members)
            assert sum(m.size for m in members)<=1024**3
            archive.extractall(target,filter='data')
    try:
        result = subprocess.run(['docker','exec',container,'python3','/input/qa/verify.py'], text=True)
        export('/tmp/evidence',output)
        if result.returncode:
            raise RuntimeError('Verified sandbox checks failed; no release was exported')
        for part in ['api','web']:
            (output/part).mkdir(exist_ok=True)
            export('/tmp/'+part,output/part)
    finally:
        run('docker','stop',container)
    print('Validated immutable build:',a.sha)

if __name__ == '__main__':
    main()
