"""Exercise the actual .NET password-setup request against an isolated TLS gateway.

Uses a new random test password in memory; never changes the real server password.
"""
import hashlib,json,os,secrets,socket,sqlite3,subprocess,tempfile,time
from contextlib import closing
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
gateway=ROOT/'build/lan-server/LocalAuthor.Lan.exe'
client=ROOT/'build/lan-client/LocalAuthor.Client.exe'
report=ROOT/'reports/password-setup-native.json'
password='áç漢🙂'+secrets.token_urlsafe(32)

def run(*args,input=None):
    return subprocess.run([str(a) for a in args],input=input,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)

with tempfile.TemporaryDirectory(prefix='localauthor-password-check-') as tmp:
    root=Path(tmp);data=root/'lan';home=root/'backend';home.mkdir()
    (home/'api.token').write_text(secrets.token_urlsafe(32))
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    result=run(gateway,'init','--data',data,'--home',home,'--bind','127.0.0.1','--prefix','32','--port',port)
    assert result.returncode==0,'Fixture initialization failed'
    connection=root/'test.localauthor';assert run(gateway,'add-device','--data',data,'--output',connection).returncode==0
    process=subprocess.Popen([str(gateway),'serve','--data',str(data)],creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.2):break
            except OSError:time.sleep(.1)
        first=root/'first.json';run(client,'--password-setup-smoke',connection,first,input=(password+'\n').encode())
        result=json.loads(first.read_text())
        with closing(sqlite3.connect(data/'publication-auth.sqlite3')) as db:
            row=db.execute('SELECT salt,hash,iterations FROM publication_password').fetchone()
        result['databaseConfigured']=row is not None
        result['hashMatches']=row is not None and hashlib.pbkdf2_hmac('sha256',password.encode(),row[0],row[2],32)==row[1]
        if result['passed']:
            second=root/'second.json';run(client,'--password-setup-smoke',connection,second,input=(secrets.token_urlsafe(32)+'\n').encode())
            result['overwriteRefused']=json.loads(second.read_text())['passed'] is False
            with closing(sqlite3.connect(data/'publication-auth.sqlite3')) as db:
                original=db.execute('SELECT hash FROM publication_password').fetchone()[0]
            result['originalPreserved']=original==row[1]
        report.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result))
        if not all(result.get(check) is True for check in ('passed','databaseConfigured','hashMatches','overwriteRefused','originalPreserved')):raise SystemExit(1)
    finally:process.terminate();process.wait(timeout=10)
