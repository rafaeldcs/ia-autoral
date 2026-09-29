"""Scoped neural code proposals. No templates, retrieval, execution or auto-apply."""
from pathlib import Path
import hashlib
import json
import re
from .errors import PolicyError

SCOPE='caddy-block-and-csharp-null-guard-v1'
PREFIXES=('Corrigir Caddy:\n','Corrigir C#:\n')

def parse_request(message):
    if not isinstance(message,str) or len(message.encode('utf-8'))>180:
        raise PolicyError('Pedido de correção inválido ou excede 180 bytes.')
    match=re.fullmatch(r'Corrigir Caddy:\nhandle(?: (@api|@web|@files))? \{ reverse_proxy (api|app|files|worker):(3000|5000|8080|8090) \}\nResposta:\n',message)
    if match:return {'family':'caddy','matcher':match[1] or '', 'service':match[2],'port':match[3]}
    match=re.fullmatch(r'Corrigir C#:\nAnulavel: ((?:input|request|data|item)\.(?:Endpoint|Url|Address|Name))\nValidador: (Rules\.(?:ValidPushEndpoint|ValidText|IsAllowed))\nResposta:\n',message)
    if match:return {'family':'csharp','expression':match[1],'validator':match[2]}
    raise PolicyError('Fora do escopo qualificado: use um bloco Caddy ou condição C# do protocolo documentado. Não há correção geral automática.')

def validate_proposal(request,source):
    """Reject changes of intent; this checker never creates replacement source."""
    if not isinstance(source,str) or len(source)>1000:raise PolicyError('Saída inválida.')
    if request['family']=='caddy':
        match=re.fullmatch(r'handle(?: (@\w+))? \{\n[ \t]+reverse_proxy (\w+):(\d+)\n\}',source)
        valid=bool(match and (match[1] or '')==request['matcher'] and match[2]==request['service'] and match[3]==request['port'])
    else:
        match=re.fullmatch(r'([A-Za-z]+\.[A-Za-z]+) != null && (Rules\.[A-Za-z]+)\(([A-Za-z]+\.[A-Za-z]+)\)',source)
        valid=bool(match and match[1]==match[3]==request['expression'] and match[2]==request['validator'])
    if not valid:raise PolicyError('Proposta neural reprovada: sintaxe ou identificadores fora do contrato. Nenhum código foi aplicado.')
    return source

def propose(home:Path,message:str):
    request=parse_request(message)
    certificate=home/'exports'/'code-repair-qualification.json'
    if not certificate.is_file():raise PolicyError('Especialista de correção ainda não qualificado.')
    cert=json.loads(certificate.read_text(encoding='utf-8'))
    if cert.get('scope')!=SCOPE or cert.get('state')!='qualified_scoped' or cert.get('generalProgrammingQualified') is not False:
        raise PolicyError('Qualificação inválida ou fora do escopo.')
    for gate in ('heldout','project','caddy','csharp','mutations'):
        score=cert.get('gates',{}).get(gate,{})
        if type(score.get('total')) is not int or score['total']<1 or score.get('passed')!=score['total']:
            raise PolicyError('Uma etapa obrigatória da qualificação não passou.')
    relative=Path(cert.get('checkpoint',''))
    base=(home/'models').resolve();checkpoint=base/relative
    if relative.is_absolute() or not relative.parts or '..' in relative.parts or checkpoint.is_symlink() or not checkpoint.resolve().is_relative_to(base):
        raise PolicyError('Checkpoint fora da pasta de modelos.')
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest()!=cert.get('checkpointHash'):
        raise PolicyError('O checkpoint mudou após a avaliação.')
    from .nn.checkpoint import load_checkpoint
    model,_,tokenizer,_,_=load_checkpoint(checkpoint)
    ids=[256]+tokenizer.encode(message)
    if len(ids)>model.config.context_length:raise PolicyError('Pedido excede o contexto avaliado.')
    generated=model.generate(ids,max_tokens=100,temperature=.05,seed=31)
    try:source=tokenizer.decode(generated)
    except UnicodeError as exc:raise PolicyError('Saída neural UTF-8 inválida; proposta não aplicada.') from exc
    validate_proposal(request,source)
    return {'origin':'local_model','content':source,'format':'code','model':relative.as_posix(),'checkpoint_hash':cert['checkpointHash'],
            'sources':[],'history_used':False,'skill':SCOPE,'qualification':'scoped','general_programming_qualified':False,
            'notice':'Especialista qualificado somente para duas famílias e o protocolo documentado. Código gerado por pesos locais, sem template de resposta. Proposta não aplicada; exige revisão e testes no projeto.'}
