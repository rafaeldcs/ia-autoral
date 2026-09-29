"""Original demonstrations, not copied project code; reserve combinations before training."""
import hashlib
import itertools
import json

SCOPE = 'javascript-missing-date-guard-v1'
FUNCTIONS = ('formatDate', 'showDate', 'renderDate', 'displayDate', 'printDate')
PARAMETERS = ('value', 'input', 'raw', 'item')
MESSAGES = ('Data indisponível', 'Sem data', 'Ausente', 'Não informado')


def prompt(name, parameter, fallback):
    return (f'JavaScript: {name}({parameter})\nAtual: new Date({parameter})\n'
            f'Ausente: null\nMensagem: {json.dumps(fallback, ensure_ascii=False)}\nGere guarda e teste:\n')


def examples():
    splits = {key: [] for key in ('train', 'validation', 'test', 'project')}
    for name, parameter, fallback in itertools.product(FUNCTIONS, PARAMETERS, MESSAGES):
        message = prompt(name, parameter, fallback)
        digest = hashlib.sha256(message.encode()).hexdigest()
        label = json.dumps(fallback, ensure_ascii=False)
        row = {'id': digest[:16], 'name': name, 'parameter': parameter, 'fallback': fallback,
               'prompt': message, 'answer': f'if ({parameter} == null) return {label};\nassert.equal({name}(null), {label});'}
        project = (name, parameter, fallback) == ('formatDate', 'value', 'Data indisponível')
        split = 'project' if project else 'validation' if int(digest[:8], 16) % 9 == 0 else 'test' if int(digest[:8], 16) % 7 == 0 else 'train'
        splits[split].append(row)
    return splits
