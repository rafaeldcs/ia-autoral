"""Check automatic provisioning and native startup without manual import.

Uses an authorized paired installer; creates only temporary client configuration.
The real server is queried read-only. No key or screenshot goes into source reports.
"""
import argparse,json,os,subprocess,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('installer',type=Path)
parser.add_argument('--generic',type=Path)

args=parser.parse_args()
checks=[]
def run(*command,timeout=90):
    result=subprocess.run([str(c) for c in command],creationflags=subprocess.CREATE_NO_WINDOW,timeout=timeout)
    if result.returncode:raise RuntimeError('Native test failed; inspect the private test report.')
def check(name,value):
    assert value,name
    checks.append(name)
with tempfile.TemporaryDirectory(prefix='localauthor-paired-check-') as folder:
    root=Path(folder);install_report=root/'install.json'
    run(args.installer,'--test-install',install_report)
    install=json.loads(install_report.read_text(encoding='utf-8-sig'))
    check('Installer provisions connection without selecting a file',install['passed'] and install['provisioned']=='created')
    check('Stored credential is DPAPI-encrypted and roundtrips correctly',install['encrypted'])
    check('Reinstall preserves existing encrypted configuration',install['preserved'])
    client=Path(install['path'])/'LocalAuthor.Client.exe'
    native_report=root/'native.json'
    run(client,'--smoke-saved',install['clientHome'],native_report)
    native=json.loads(native_report.read_text(encoding='utf-8-sig'))
    check('Fresh native client opens chat using saved connection, without import',native['passed'] and native['desktopLogin'])
    check('Automatic connection still verifies server TLS and authentication',native['pinnedTls'] and native['authenticated'])
    if args.generic:
        generic_report=root/'generic.json';run(args.generic,'--test-install',generic_report)
        generic=json.loads(generic_report.read_text(encoding='utf-8-sig'))
        check('Generic installer does not contain paired provisioning resource',generic['provisioned']=='not-included')
result={'passed':len(checks),'checks':checks,'savedConnectionStartup':True,'serverAccess':'read-only on this machine','secondPhysicalComputerTested':False}
(ROOT/'reports/paired-installer-smoke.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
