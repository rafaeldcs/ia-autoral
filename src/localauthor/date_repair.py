"""Read bounded source context and validate neural proposals; never fabricate a patch."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from .errors import PolicyError
from .safety import PathPolicy

SCOPE = 'javascript-missing-date-guard-v1'
PREFIX = 'JavaScript: '
FUNCTIONS = ('formatDate', 'showDate', 'renderDate', 'displayDate', 'printDate')
PARAMETERS = ('value', 'input', 'raw', 'item')
MESSAGES = ('Data indisponível', 'Sem data', 'Ausente', 'Não informado')


def parse_request(message):
    if not isinstance(message, str) or len(message.encode('utf-8')) > 180:
        raise PolicyError('Pedido de data fora do protocolo avaliado.')
    match = re.fullmatch(r'JavaScript: (\w+)\((\w+)\)\nAtual: new Date\((\w+)\)\nAusente: null\nMensagem: ("[^"\n]+")\nGere guarda e teste:\n', message)
    if not match:
        raise PolicyError('Pedido de data fora do protocolo avaliado.')
    name, parameter, repeated, literal = match.groups()
    fallback = json.loads(literal)
    if name not in FUNCTIONS or parameter not in PARAMETERS or repeated != parameter or fallback not in MESSAGES:
        raise PolicyError('Identificador ou mensagem fora da distribuição avaliada.')
    return {'name': name, 'parameter': parameter, 'fallback': fallback}


def validate_proposal(request, generated):
    """Validation rejects bad output. No rewriting, repair or answer lookup."""
    if not isinstance(generated, str) or len(generated) > 500:
        raise PolicyError('Proposta inválida.')
    match = re.fullmatch(r'(if \((\w+) == null\) return ("[^"\n]+");)\n(assert.equal\((\w+)\(null\), ("[^"\n]+")\);)', generated)
    if not match or match[2] != request['parameter'] or match[5] != request['name']:
        raise PolicyError('Guarda/teste neural não corresponde ao contrato.')
    if json.loads(match[3]) != request['fallback'] or json.loads(match[6]) != request['fallback']:
        raise PolicyError('A proposta mudou a mensagem de ausência.')
    return {'guard': match[1], 'assertion': match[4]}


def source_context(root: Path, symbol: str):
    """Teacher-specified symbol. Search is deterministic, not claimed as model reasoning."""
    if symbol not in FUNCTIONS:
        raise PolicyError('Função fora do escopo de investigação guiada.')
    policy = PathPolicy(root, 200_000)
    candidates = []
    # Inspect only source modules; no private configuration, tests or dependencies.
    for relative in policy.files(2000):
        if not relative.startswith('app/src/lib/') or not relative.endswith('.mjs'):
            continue
        raw = policy.read(relative)
        source = raw.decode('utf-8')
        pattern = (r'export function ' + re.escape(symbol) + r'\((\w+)\) \{\r?\n'
                   r'  const date = new Date\(\1\);\r?\n'
                   r'  if \(!Number.isFinite\(date.getTime\(\)\)\) return \'([^\'\n]+)\';')
        matches = list(re.finditer(pattern, source))
        for match in matches:
            parameter, fallback = match.groups()
            message = (f'JavaScript: {symbol}({parameter})\nAtual: new Date({parameter})\n'
                       f'Ausente: null\nMensagem: {json.dumps(fallback, ensure_ascii=False)}\nGere guarda e teste:\n')
            request = parse_request(message)
            candidates.append({'path': relative, 'beforeHash': hashlib.sha256(raw).hexdigest(),
                               'prompt': message, 'request': request,
                               'insertionOffset': source.index('\n', match.start()) + 1,
                               'excerpt': match.group(), 'source': source})
    if len(candidates) != 1:
        raise PolicyError('Fonte ausente, ambígua ou diferente do padrão avaliado. Revisão necessária.')
    return candidates[0]


def stage(context, generated):
    parts = validate_proposal(context['request'], generated)
    source = context['source']
    if hashlib.sha256(source.encode('utf-8')).hexdigest() != context['beforeHash']:
        raise PolicyError('Fonte mudou depois da investigação.')
    offset = context['insertionOffset']
    newline = '\r\n' if '\r\n' in source else '\n'
    return source[:offset] + '  ' + parts['guard'] + newline + source[offset:], parts['assertion']


def propose(home: Path, message: str):
    request = parse_request(message)
    certificate = home / 'exports' / 'date-repair-qualification.json'
    if not certificate.is_file():
        raise PolicyError('Especialista de datas ainda não qualificado.')
    cert = json.loads(certificate.read_text(encoding='utf-8'))
    if cert.get('scope') != SCOPE or cert.get('state') != 'qualified_scoped' or cert.get('generalProgrammingQualified') is not False:
        raise PolicyError('Certificado de datas inválido.')
    for gate in ('heldout', 'behavior', 'redGreen', 'negativeControls', 'projectRegression'):
        score = cert.get('gates', {}).get(gate, {})
        if type(score.get('total')) is not int or score['total'] < 1 or score.get('passed') != score['total']:
            raise PolicyError('Qualificação de datas incompleta.')
    relative = Path(cert.get('checkpoint', ''))
    base = (home / 'models').resolve()
    checkpoint = base / relative
    if relative.is_absolute() or not relative.parts or '..' in relative.parts or checkpoint.is_symlink() or not checkpoint.resolve().is_relative_to(base):
        raise PolicyError('Checkpoint fora dos modelos locais.')
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != cert.get('checkpointHash'):
        raise PolicyError('Checkpoint mudou após a avaliação.')
    from .nn.checkpoint import load_checkpoint
    model, _, tokenizer, _, _ = load_checkpoint(checkpoint)
    ids = [256] + tokenizer.encode(message)
    if len(ids) > model.config.context_length:
        raise PolicyError('Contexto excedido.')
    try:
        content = tokenizer.decode(model.generate(ids, max_tokens=100, temperature=.05, seed=31))
    except UnicodeError as exc:
        raise PolicyError('Saída UTF-8 inválida.') from exc
    validate_proposal(request, content)
    return {'origin': 'local_model', 'content': content, 'format': 'code', 'model': relative.as_posix(),
            'checkpoint_hash': cert['checkpointHash'], 'skill': SCOPE, 'qualification': 'scoped',
            'general_programming_qualified': False, 'history_used': False, 'sources': [],
            'notice': 'Guarda e asserção geradas pelos pesos locais. Especialidade restrita a ausência de data; investigação guiada pelo professor. Não aplicada automaticamente.'}
