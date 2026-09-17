"""Read-only verification of the published update on this server's actual LAN endpoint."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import ssl
from urllib.parse import urlparse

parser = argparse.ArgumentParser()
parser.add_argument('connection', type=Path)
args = parser.parse_args()
connection = json.loads(args.connection.read_text(encoding='utf-8-sig'))
certificate = (Path(os.environ['LOCALAPPDATA']) / 'LocalAuthor/lan/server.cer').read_bytes()
assert hashlib.sha256(certificate).hexdigest().upper() == connection['CertificateSha256']
context = ssl.create_default_context(cadata=ssl.DER_cert_to_PEM_cert(certificate))
uri = urlparse(connection['Server'])
client = http.client.HTTPSConnection(uri.hostname, uri.port, context=context, timeout=30)
headers = {'Authorization': 'Bearer ' + connection['AccessKey']}
client.request('GET', '/api/client-update', headers=headers)
response = client.getresponse()
assert response.status == 200
manifest = json.loads(response.read())
client.request('GET', '/api/client-update/package?sha256=' + manifest['sha256'], headers=headers)
response = client.getresponse()
assert response.status == 200
digest = hashlib.sha256()
size = 0
while block := response.read(81920):
    digest.update(block)
    size += len(block)
client.close()
assert size == manifest['size'] and digest.hexdigest().upper() == manifest['sha256']
result = {'passed': True, 'version': manifest['version'], 'authenticatedLanDownloadVerified': True, 'secondPhysicalComputerTested': False}
(Path(__file__).resolve().parents[1] / 'reports/published-client-update.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
