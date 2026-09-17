"""Package only named public binaries/documents, never runtime credentials or model data."""
from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parents[2]
files={
 'LocalAuthor.Client.exe':root/'build/lan-client/LocalAuthor.Client.exe',
 'Desinstalar.ps1':root/'scripts/lan/Desinstalar.ps1',
 'LEIA-ME.md':root/'docs/LAN_INSTALL.md',
 'THIRD_PARTY_NOTICES.md':root/'THIRD_PARTY_NOTICES.md',
}
licenses=Path('C:/Program Files/dotnet')
for name in ['LICENSE.txt','ThirdPartyNotices.txt']:
 if (licenses/name).is_file():files['DOTNET-'+name]=licenses/name
webview=Path.home()/'.nuget/packages/microsoft.web.webview2/1.0.4191.47'
for path in webview.glob('*'):
 if path.is_file() and ('license' in path.name.lower() or 'notice' in path.name.lower()):files['WEBVIEW2-'+path.name]=path
manifest={}
with zipfile.ZipFile(root/'build/client-payload.zip','w',zipfile.ZIP_DEFLATED) as archive:
 for name,path in files.items():
  raw=path.read_bytes();manifest[name]=hashlib.sha256(raw).hexdigest().upper();archive.writestr(name,raw)
 archive.writestr('payload-manifest.json',json.dumps(manifest))
print(json.dumps({'files':list(files),'bytes':(root/'build/client-payload.zip').stat().st_size}))
