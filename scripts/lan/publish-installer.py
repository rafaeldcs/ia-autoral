"""Publish one reviewed connected installer already present on this LAN server."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from localauthor.config import default_home
from localauthor.installer_catalog import InstallerCatalog,NAME,validate_manifest
from localauthor.util import write_json

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--home',type=Path,default=default_home());parser.add_argument('--folder',required=True)
    args=parser.parse_args()
    import re
    if not re.fullmatch('[0-9a-f]{32}',args.folder):raise ValueError('Invalid installer folder')
    root=args.home/'lan';package=root/'private-installers'/args.folder
    metadata=json.loads((package/'package.json').read_text(encoding='utf-8-sig'))
    path=package/NAME
    with path.open('rb') as stream:
        if stream.read(2)!=b'MZ':raise ValueError('Expected a reviewed Windows executable')
        stream.seek(0);checksum=hashlib.file_digest(stream,'sha256').hexdigest().upper()
    if checksum!=metadata['sha256'].upper():raise ValueError('Installer digest differs from reviewed package')
    manifest={'folder':args.folder,'version':metadata['version'],'size':path.stat().st_size,'sha256':checksum}
    validate_manifest(manifest)
    # Validate before changing the published pointer.
    from localauthor.foundation.models import local_path
    local_path(path)
    write_json(root/'installer-release.json',manifest)
    status=InstallerCatalog(args.home).status()
    if not status['available']:raise ValueError(status['message'])
    print(json.dumps({'published':True,'version':status['version'],'size':status['size'],'sha256':status['sha256']}))

if __name__=='__main__':main()
