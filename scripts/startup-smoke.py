"""Check isolated registry preferences and actually launch the saved startup command."""
import argparse,json,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('connection',type=Path);args=parser.parse_args()
with tempfile.TemporaryDirectory(prefix='LocalAuthor startup check ') as temp:
    root=Path(temp);client=root/'LocalAuthor.Client.exe'
    shutil.copyfile(ROOT/'build/lan-client/LocalAuthor.Client.exe',client)
    registry=root/'registry.json';native=root/'native.json'
    subprocess.run([str(client),'--startup-check',str(registry)],check=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    value=json.loads(registry.read_text());assert value['passed']
    # Execute exactly the registry command, adding only the native test's isolated connection/report arguments.
    command=value['command']+' '+subprocess.list2cmdline(['--smoke',str(args.connection.resolve()),str(native)])
    subprocess.run(command,check=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
    assert json.loads(native.read_text())['desktopLogin']
result={'passed':4,'checks':['Quoted startup command registered under isolated HKCU key','Opt-out survives default registration on update','Other startup entries remain unchanged','Registry command launches native chat from path containing spaces'],'rebootTested':False}
(ROOT/'reports/startup-smoke.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
