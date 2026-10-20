"""Frozen provenance, bounded inputs and strict local tool-call protocol."""
import hashlib
import hmac
import base64
import json
from pathlib import PurePosixPath

from ..errors import PolicyError

UPSTREAM = 'https://github.com/harveyai/harvey-labs'
REVISION = '97810facfd447317b57f6dd02a1469561c573d79'
TOOLS = {'bash', 'read', 'write', 'edit', 'glob', 'grep', 'finish'}
MAX_FRAME = 1_000_000
RECORDS={'transcript':'transcript.jsonl','report':'upstream-report.html.untrusted','result':'worker-result.json'}


def sign_frame(value,key):
    raw=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    return {'body':value,'mac':hmac.new(key,raw,hashlib.sha256).hexdigest()}


def verify_frame(value,key):
    if (not isinstance(value,dict) or set(value)!={'body','mac'} or not isinstance(value['body'],dict)
            or not isinstance(value['mac'],str) or len(value['mac'])!=64
            or any(character not in '0123456789abcdef' for character in value['mac'])):
        raise PolicyError('Frame sem autenticação do controlador.')
    expected=sign_frame(value['body'],key)['mac']
    if not hmac.compare_digest(expected,value['mac']):raise PolicyError('Frame alterado ou de outra execução.')
    return value['body']


def receive_record(root,message):
    kind=message.get('kind');offset=message.get('offset')
    if not isinstance(kind,str) or kind not in RECORDS or type(offset) is not int or offset<0 or not isinstance(message.get('data'),str):
        raise PolicyError('Registro RPC não autorizado.')
    try:data=base64.b64decode(message['data'],validate=True)
    except ValueError as error:raise PolicyError('Registro RPC corrompido.') from error
    target=root/RECORDS[kind]
    if (target.stat().st_size if target.exists() else 0)!=offset or offset+len(data)>64_000_000:
        raise PolicyError('Registro fora de ordem ou acima do orçamento.')
    with target.open('ab') as stream:stream.write(data)


def relative_file(value):
    if not isinstance(value,str) or not value or '\\' in value or ':' in value or '\x00' in value:
        raise PolicyError('Caminho de artefato inválido.')
    path=PurePosixPath(value)
    if path.is_absolute() or any(part in {'','..','.'} for part in value.split('/')):
        raise PolicyError('Artefato precisa permanecer na pasta de saída.')
    return path


def parse_action(text, truncated=False):
    if truncated or not isinstance(text,str) or len(text.encode('utf-8'))>MAX_FRAME:
        raise PolicyError('Resposta incompleta ou fora do orçamento; não executar ferramentas.')
    try:value=json.loads(text)
    except (ValueError,TypeError) as error:raise PolicyError('A IA precisa responder com JSON completo, sem reparo automático.') from error
    if isinstance(value,dict) and set(value)=={'final'} and isinstance(value['final'],str) and value['final'].strip():
        return value
    if (not isinstance(value,dict) or set(value)!={'tool','arguments'} or not isinstance(value['tool'],str) or value['tool'] not in TOOLS
            or not isinstance(value['arguments'],dict)):
        raise PolicyError('Chamada de ferramenta fora do contrato local.')
    return value


def validate_task(task):
    if (not isinstance(task,dict) or not isinstance(task.get('title'),str) or not task['title'].strip()
            or not isinstance(task.get('instructions'),str) or not task['instructions'].strip()
            or not isinstance(task.get('criteria'),list) or not task['criteria']):
        raise PolicyError('Tarefa sem instrução ou critérios completos.')
    ids=set()
    for row in task['criteria']:
        if (not isinstance(row,dict) or not isinstance(row.get('id'),str) or row['id'] in ids
                or not isinstance(row.get('title'),str) or not isinstance(row.get('match_criteria'),str)
                or not row['match_criteria'].strip()):
            raise PolicyError('Critério ausente, vazio ou duplicado.')
        ids.add(row['id'])
        if not isinstance(row.get('deliverables',[]),list):raise PolicyError('Lista de entregáveis inválida.')
        if any(not isinstance(name,str) or not name for name in row.get('deliverables',[])):
            raise PolicyError('Referência de entregável inválida.')
    if not isinstance(task.get('deliverables',{}),dict):raise PolicyError('Mapa de entregáveis inválido.')
    for name in task.get('deliverables',{}).values():relative_file(name)
    return task


def content_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def verify_sandbox(info,image,expected):
    host=info.get('HostConfig',{});mounts=info.get('Mounts',[])
    if (info.get('Image')!=image or info.get('Config',{}).get('User')!='10001:10001'
            or host.get('NetworkMode')!='none' or not host.get('ReadonlyRootfs') or host.get('Privileged')
            or host.get('CapDrop')!=['ALL'] or 'no-new-privileges' not in host.get('SecurityOpt',[])
            or host.get('Memory')!=2*1024**3 or host.get('MemorySwap')!=2*1024**3
            or host.get('NanoCpus')!=2_000_000_000 or host.get('PidsLimit')!=128
            or host.get('PortBindings') or host.get('DeviceRequests')
            or host.get('Tmpfs')!={'/tmp':'rw,nosuid,nodev,size=256m','/workspace':'rw,nosuid,nodev,size=512m,mode=1777','/workspace/output':'rw,nosuid,nodev,size=64m,mode=1777'}
            or set(mount.get('Destination') for mount in mounts)!=set(expected)
            or set(expected)!={'/opt/localauthor','/workspace/documents'} or any(writable for _,writable in expected.values())
            or len(mounts)!=2):
        raise PolicyError('Sandbox Harvey diverge do perfil revisado.')
    for mount in mounts:
        destination=mount.get('Destination');entry=expected.get(destination)
        if not entry or mount.get('Type')!='bind' or bool(mount.get('RW'))!=entry[1]:
            raise PolicyError('Montagem não autorizada na sandbox Harvey.')
        actual=mount.get('Source','').replace('\\','/').rstrip('/').lower()
        wanted=entry[0].replace('\\','/').rstrip('/').lower()
        alternative='/run/desktop/mnt/host/'+wanted[0]+wanted[2:] if wanted[1:3]==':/' else wanted
        if actual not in {wanted,alternative}:raise PolicyError('Origem de montagem não autorizada.')
