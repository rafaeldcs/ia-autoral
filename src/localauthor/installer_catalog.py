"""Operator-published LAN installer. Never expose its embedded connection in chat."""
import hashlib
import json
import re
from pathlib import Path

from .errors import NotFoundError, PolicyError
from .foundation.models import local_path

NAME='Instalar-LocalAuthor-Conectado.exe'


def validate_manifest(data):
    if not isinstance(data,dict) or set(data)!={'folder','sha256','size','version'} or not re.fullmatch('[0-9a-f]{32}',data['folder']) or not re.fullmatch('[0-9A-F]{64}',data['sha256']) or not re.fullmatch(r'\d+\.\d+\.\d+(?:\.\d+)?',data['version']) or type(data['size']) is not int or not 1<=data['size']<=500_000_000:
        raise ValueError('Invalid installer publication')


class InstallerCatalog:
    def __init__(self, home):self.root=Path(home)/'lan'

    def open(self):
        manifest=local_path(self.root/'installer-release.json')
        if not manifest.is_file():raise NotFoundError('O instalador ainda não foi publicado neste servidor.')
        try:
            if manifest.stat().st_size>16384:raise ValueError()
            data=json.loads(manifest.read_text(encoding='utf-8-sig'));validate_manifest(data)
            path=local_path(self.root/'private-installers'/data['folder']/NAME)
            stream=path.open('rb')
            try:
                if path.stat().st_size!=data['size'] or hashlib.file_digest(stream,'sha256').hexdigest().upper()!=data['sha256']:raise ValueError()
                stream.seek(0)
                return data,stream
            except BaseException:stream.close();raise
        except (OSError,ValueError,TypeError,KeyError) as error:
            raise PolicyError('O instalador publicado está indisponível ou falhou na verificação de integridade. Refaça a publicação no servidor.') from error

    def status(self):
        try:data,stream=self.open()
        except (NotFoundError,PolicyError) as error:return {'available':False,'message':str(error)}
        stream.close()
        return {'available':True,'name':NAME,'version':data['version'],'size':data['size'],'sha256':data['sha256'],'download':'/api/app/installer/file'}
