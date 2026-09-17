from __future__ import annotations
import hashlib
import json
import os
import re
import sqlite3
import stat
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path, PurePosixPath
from .config import Settings
from .errors import PolicyError
from .store import Store
from .util import canonical_json, atomic_writer, read_json, write_json

MAX_BYTES = 512_000_000
MAX_ARCHIVE_BYTES = 520_000_000
MAX_FILES = 20_000
MAX_MANIFEST_BYTES = 4_000_000
CHUNK_BYTES = 1024 * 1024
RESERVED = {'con', 'prn', 'aux', 'nul', *(f'com{i}' for i in range(1, 10)), *(f'lpt{i}' for i in range(1, 10))}


def reject_links(path: Path):
    for part in (path, *path.parents):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise PolicyError('Backup/restauração não pode usar links ou junctions.')


def safe_name(name: str) -> str:
    p = PurePosixPath(name)
    if (name in {'', '.'} or name != p.as_posix() or p.is_absolute() or '\\' in name
            or any(ord(c) < 32 or c in ':<>"|?*' for c in name)
            or any(part in {'.', '..'} or part.endswith((' ', '.'))
                   or part.split('.')[0].casefold() in RESERVED for part in p.parts)):
        raise PolicyError('Caminho inseguro no backup.')
    if p.name.casefold() in {'api.token', 'server.lock'}:
        raise PolicyError('Backup não deve importar credenciais ou locks.')
    return name


def copy_hash(source, destination, budget: int):
    digest = hashlib.sha256()
    size = 0
    while chunk := source.read(CHUNK_BYTES):
        size += len(chunk)
        if size > budget:
            raise PolicyError('Backup excede o limite de bytes.')
        destination.write(chunk)
        digest.update(chunk)
    return digest.hexdigest(), size


def backup_home(settings: Settings, output: Path):
    home = settings.home.absolute()
    output = output.expanduser().absolute()
    reject_links(home)
    reject_links(output)
    if (home / 'server.lock').exists():
        raise PolicyError('Encerre o servidor antes do backup consistente de banco e arquivos.')
    if output.resolve().is_relative_to(home.resolve()):
        raise PolicyError('Salve o backup fora da pasta de dados, preferencialmente em outro dispositivo.')
    manifest = {}
    total = 0
    with tempfile.TemporaryDirectory() as tmp:
        snapshot = Path(tmp) / 'memory.sqlite3'
        Store(home / 'memory.sqlite3').backup(snapshot)

        def files():
            yield snapshot, 'memory.sqlite3'
            for directory, dirs, names in os.walk(home, followlinks=False):
                # Exports are deliberately excluded, as in the original format.
                if Path(directory) == home:
                    dirs[:] = [name for name in dirs if name != 'exports']
                for name in dirs:
                    reject_links(Path(directory) / name)
                for name in sorted(names):
                    path = Path(directory) / name
                    relative = path.relative_to(home).as_posix()
                    if relative in {'api.token', 'server.lock', 'memory.sqlite3', 'memory.sqlite3-wal', 'memory.sqlite3-shm', 'memory.sqlite3-journal'}:
                        continue
                    reject_links(path)
                    yield path, safe_name(relative)

        # ZIP bytes and payloads are streamed, never accumulated in RAM.
        with atomic_writer(output) as stream:
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
                aliases = set()
                for path, relative in files():
                    if relative.casefold() == 'backup_manifest.json' or relative.casefold() in aliases:
                        raise PolicyError('Nome reservado ou duplicado no backup.')
                    aliases.add(relative.casefold())
                    if len(aliases) >= MAX_FILES:
                        raise PolicyError('Quantidade de arquivos excede o limite do backup.')
                    with path.open('rb') as source:
                        info = os.fstat(source.fileno())
                        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                            raise PolicyError('Backup aceita somente arquivos regulares sem hardlinks.')
                        with archive.open(relative, 'w') as target:
                            digest, size = copy_hash(source, target, MAX_BYTES - total)
                    total += size
                    manifest[relative] = digest
                raw_manifest = canonical_json(manifest)
                if len(raw_manifest) > MAX_MANIFEST_BYTES or total + len(raw_manifest) > MAX_BYTES:
                    raise PolicyError('Manifesto excede o limite do backup.')
                archive.writestr('BACKUP_MANIFEST.json', raw_manifest)
            if stream.tell() > MAX_ARCHIVE_BYTES:
                raise PolicyError('Backup grande demais.')
    return {'files': len(manifest), 'bytes': total, 'path': str(output), 'token_included': False, 'streaming': True}


def restore_home(archive_path: Path, destination: Path):
    destination = destination.expanduser().absolute()
    reject_links(destination)
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise PolicyError('Restauração exige diretório vazio; não sobrescreve uma instalação existente.')
    if archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise PolicyError('Backup grande demais.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(names) > MAX_FILES or sum(entry.file_size for entry in entries) > MAX_BYTES:
                raise PolicyError('Backup excedendo limites.')
            aliases = set()
            for entry in entries:
                safe_name(entry.filename)
                mode = (entry.external_attr >> 16) & 0o170000
                if entry.is_dir() or mode not in {0, stat.S_IFREG} or entry.flag_bits & 1:
                    raise PolicyError('Backup contém tipo de arquivo não permitido.')
                key = entry.filename.casefold()
                if key in aliases:
                    raise PolicyError('Backup contém caminhos duplicados.')
                aliases.add(key)
            for name in names:
                if any(parent.as_posix().casefold() in aliases for parent in PurePosixPath(name).parents if parent.as_posix() != '.'):
                    raise PolicyError('Conflito entre arquivo e diretório no backup.')
            if 'BACKUP_MANIFEST.json' not in names:
                raise PolicyError('Manifesto do backup ausente.')
            if archive.getinfo('BACKUP_MANIFEST.json').file_size > MAX_MANIFEST_BYTES:
                raise PolicyError('Manifesto do backup grande demais.')
            manifest = json.loads(archive.read('BACKUP_MANIFEST.json'))
            if (not isinstance(manifest, dict) or set(manifest) != set(names) - {'BACKUP_MANIFEST.json'}
                    or not {'settings.json', 'memory.sqlite3'} <= set(manifest)
                    or any(not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest) for digest in manifest.values())):
                raise PolicyError('Manifesto do backup divergente.')
            # Validate all bytes, settings and database in a sibling directory.
            # A failure leaves the requested destination untouched and retryable.
            with tempfile.TemporaryDirectory(prefix='.localai-restore-', dir=destination.parent) as tmp:
                staged = Path(tmp) / 'data'
                staged.mkdir()
                total = 0
                for name, expected in manifest.items():
                    with archive.open(name) as source, atomic_writer(staged / name) as target:
                        digest, size = copy_hash(source, target, MAX_BYTES - total)
                    total += size
                    if digest != expected:
                        raise PolicyError('Backup corrompido.')
                with closing(sqlite3.connect(staged / 'memory.sqlite3')) as db:
                    if db.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                        raise PolicyError('Banco restaurado corrompido.')
                    if db.execute('SELECT version FROM schema_version').fetchall() != [(1,)]:
                        raise PolicyError('Versão de banco não suportada.')
                config = read_json(staged / 'settings.json')
                if not isinstance(config, dict):
                    raise PolicyError('Configuração do backup inválida.')
                config['offline'] = True
                config['docker_image'] = ''
                write_json(staged / 'settings.json', config)
                Settings.load(staged)
                reject_links(destination)
                existed = destination.exists()
                if existed:
                    # rmdir only removes an empty directory, never user content.
                    destination.rmdir()
                try:
                    os.replace(staged, destination)
                except OSError:
                    if existed:
                        destination.mkdir(exist_ok=True)
                    raise
    except (zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError, sqlite3.DatabaseError) as exc:
        raise PolicyError('Backup inválido ou corrompido.') from exc
    return {'restored': True, 'files': len(manifest), 'offline': True,
            'token_regenerated': True, 'review_project_roots': True, 'streaming': True}
