"""Bounded neural tool controller. Sandbox code stays isolated; proposals await review.

The policy chooses tools. Deterministic parsers restrict scope and execute tools, never
select a correction. The previously qualified date model generates guard + assertion.
"""
from __future__ import annotations
import hashlib
import difflib
import json
from pathlib import Path
import re
import subprocess
from .date_repair import parse_request, stage, propose
from .errors import PolicyError
from .safety import PathPolicy, reject_secrets

SCOPE = 'missing-date-investigation-tools-v2'
ACTIONS = {'BUSCAR new Date', 'LER 0', 'PROVAR null', 'PROXIMO', 'CORRIGIR_AUSENCIA',
           'TESTAR', 'ENTREGAR_REVISAO', 'SEM_REPRODUCAO', 'PEDIR_AJUDA'}
ALLOWED = {'inicio': {'BUSCAR new Date', 'PEDIR_AJUDA'}, 'busca': {'LER 0', 'PEDIR_AJUDA'},
           'leitura': {'PROVAR null', 'PEDIR_AJUDA'}, 'leitura_incompativel': {'PROXIMO', 'PEDIR_AJUDA'},
           'prova': {'PROXIMO', 'CORRIGIR_AUSENCIA', 'PEDIR_AJUDA'}, 'erro': {'PEDIR_AJUDA'},
           'proposta': {'TESTAR', 'PEDIR_AJUDA'}, 'testes': {'ENTREGAR_REVISAO', 'PEDIR_AJUDA'},
           'esgotado': {'SEM_REPRODUCAO', 'PEDIR_AJUDA'}}


def observation(stage_name, text):
    return f'Investigacao limitada de datas\nEtapa: {stage_name}\n{text}\nAcao:\n'


def validate_action(stage_name, action):
    if action not in ACTIONS or action not in ALLOWED.get(stage_name, set()):
        raise PolicyError('Ação neural inválida para esta etapa; não foi substituída pelo executor.')
    return action


def inspect_source(path, raw):
    source = raw.decode('utf-8')
    pattern = r'^export function (\w+)\((\w+)\) \{\r?\n.*?^\}'
    contexts = []
    for match in re.finditer(pattern, source, re.M | re.S):
        name, parameter = match[1], match[2]
        body = match.group()
        if f'new Date({parameter})' not in body:
            continue
        fallback = re.search(r"if \(!Number.isFinite\(date.getTime\(\)\)\) return '([^'\n]+)';", body)
        if not fallback:
            continue
        message = (f'JavaScript: {name}({parameter})\nAtual: new Date({parameter})\nAusente: null\n'
                   f'Mensagem: {json.dumps(fallback[1], ensure_ascii=False)}\nGere guarda e teste:\n')
        try:
            request = parse_request(message)
        except PolicyError:
            continue
        contexts.append({'path': path, 'source': source, 'beforeHash': hashlib.sha256(raw).hexdigest(),
                         'prompt': message, 'request': request, 'insertionOffset': source.index('\n', match.start()) + 1})
    if len(contexts) != 1:
        raise PolicyError('sem função compatível' if not contexts else 'múltiplas funções compatíveis')
    return contexts[0]


class NeuralPolicy:
    def __init__(self, checkpoint, expected_hash):
        from .nn.checkpoint import load_checkpoint
        if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != expected_hash:
            raise PolicyError('Checkpoint de investigação alterado.')
        self.model, _, self.tokenizer, _, self.metadata = load_checkpoint(checkpoint)
        if self.metadata['provenance'].get('scope') != SCOPE:
            raise PolicyError('Modelo não corresponde à política de investigação.')

    def __call__(self, prompt):
        ids = [256] + self.tokenizer.encode(prompt)
        if len(ids) > self.model.config.context_length:
            raise PolicyError('Observação excedeu contexto; não foi truncada.')
        return self.tokenizer.decode(self.model.generate(ids, max_tokens=32, temperature=.05, seed=31))


class Investigation:
    def __init__(self, root: Path, output: Path, home: Path, policy, *, max_steps=28):
        if not Path('/.dockerenv').is_file():
            raise PolicyError('Execução de investigação exige a sandbox Docker revisada.')
        self.root, self.output, self.home, self.policy = root, output, home, policy
        self.paths = PathPolicy(root, 100_000)
        self.output.mkdir(parents=True, exist_ok=False)
        if type(max_steps) is not int or not 1 <= max_steps <= 28:
            raise PolicyError('Orçamento de ações inválido.')
        self.max_steps = max_steps
        self.events = []
        self.candidates = []
        self.selected = None
        self.probe_failed = False
        self.test_passed = False
        self.verified = 0
        self.changed = []
        self.skipped = 0

    def record(self, kind, **details):
        self.events.append({'sequence': len(self.events) + 1, 'event': kind, **details})
        (self.output / 'journal.json').write_text(json.dumps(self.events, ensure_ascii=False, indent=2), encoding='utf-8')

    def run_node(self, source, name, *, test=False):
        executable = self.output / (name + ('.test.mjs' if test else '.mjs'))
        executable.write_text(source, encoding='utf-8')
        command = ['node'] + (['--test'] if test else []) + [str(executable)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=10)
        if len(result.stdout) > 100_000:
            raise PolicyError('Saída da ferramenta excedeu quota.')
        (self.output / (name + '.log')).write_text(result.stdout, encoding='utf-8')
        self.record('execution', name=name, exitCode=result.returncode)
        return result.returncode, result.stdout

    def catalog(self):
        if self.candidates:
            return 'busca', f'Resultados: {len(self.candidates)}\nReferencias: ' + ','.join(str(i) for i in range(len(self.candidates)))
        return 'esgotado', f'Provas aprovadas: {self.verified}'

    def module_import(self):
        return f"import * as subject from {json.dumps((self.root / self.selected['path']).as_uri())};\n"

    def execute(self, report):
        if not isinstance(report, str) or not 1 <= len(report) <= 180:
            raise PolicyError('Relato fora do limite avaliado.')
        reject_secrets(report)
        phase, text = 'inicio', report
        state = 'needs_help'
        try:
            for step in range(self.max_steps):
                message = observation(phase, text)
                action = self.policy(message)
                self.record('model_action', stage=phase, prompt=message, action=action)
                validate_action(phase, action)
                if action == 'PEDIR_AJUDA':
                    break
                if action == 'BUSCAR new Date':
                    self.candidates = [p for p in self.paths.files(1000)
                        if p.startswith('app/src/lib/') and p.endswith('.mjs') and 'new Date' in self.paths.read(p).decode('utf-8')]
                    if len(self.candidates) > 5:
                        raise PolicyError('Mais de cinco módulos candidatos: requer investigação mais ampla.')
                    self.record('search', query='new Date', results=self.candidates[:])
                    phase, text = self.catalog()
                elif action == 'LER 0':
                    path = self.candidates[0]
                    try:
                        self.selected = inspect_source(path, self.paths.read(path))
                        req = self.selected['request']
                        phase = 'leitura'
                        text = (f"function {req['name']}({req['parameter']})\nconst date = new Date({req['parameter']});\n"
                                f"Ausencia esperada: {req['fallback']}")
                        self.record('source_read', path=path, hash=self.selected['beforeHash'], context=text)
                    except PolicyError as exc:
                        self.selected = None
                        self.skipped += 1
                        phase, text = 'leitura_incompativel', str(exc)
                elif action == 'PROVAR null':
                    code, log = self.run_node(self.module_import() + f"console.log(JSON.stringify(subject[{json.dumps(self.selected['request']['name'])}](null)));", f'probe-{step}')
                    if code:
                        phase, text = 'erro', 'TypeError'
                        continue
                    try:
                        actual = json.loads(log)
                    except ValueError:
                        phase, text = 'erro', 'saida invalida'
                        continue
                    self.probe_failed = actual != self.selected['request']['fallback']
                    self.verified += int(not self.probe_failed)
                    phase = 'prova'
                    text = f"Entrada: null\nContrato de ausencia: {'falhou' if self.probe_failed else 'passou'}\nSaida: {str(actual)[:65]}"
                    self.record('probe', path=self.selected['path'], input=None, actual=actual, expected=self.selected['request']['fallback'])
                elif action == 'PROXIMO':
                    if phase == 'prova' and self.probe_failed:
                        raise PolicyError('Não é permitido descartar um defeito reproduzido.')
                    self.candidates.pop(0)
                    self.selected = None
                    self.probe_failed = False
                    phase, text = self.catalog()
                elif action == 'CORRIGIR_AUSENCIA':
                    if not self.selected or not self.probe_failed:
                        raise PolicyError('Correção sem reprodução do defeito foi bloqueada.')
                    reply = propose(self.home, self.selected['prompt'])
                    generated = reply['content']
                    patched, assertion = stage(self.selected, generated)
                    self.record('neural_code', **reply)
                    name = self.selected['request']['name']
                    self.regression = self.module_import() + "import assert from 'node:assert/strict';\nimport test from 'node:test';\n" + f"const {name}=subject[{json.dumps(name)}];\n" + "test('regressao neural',()=>{\n" + assertion + '\n});\n'
                    code, log = self.run_node(self.regression, 'red', test=True)
                    if code == 0 or 'ERR_ASSERTION' not in log:
                        raise PolicyError('Teste não demonstrou o defeito original.')
                    current = self.paths.read(self.selected['path'])
                    if hashlib.sha256(current).hexdigest() != self.selected['beforeHash']:
                        raise PolicyError('Fonte mudou durante investigação.')
                    self.paths.resolve(self.selected['path'], write=True).write_bytes(patched.encode('utf-8'))
                    self.changed.append(self.selected['path'])
                    artifact = {'path': self.selected['path'], 'before_sha256': self.selected['beforeHash'],
                                'after_sha256': hashlib.sha256(patched.encode()).hexdigest(), 'content': patched,
                                'assertion': assertion, 'origin': 'local_model', 'requires_review': True, 'state': 'unverified'}
                    (self.output / 'proposal.json').write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding='utf-8')
                    diff = ''.join(difflib.unified_diff(self.selected['source'].splitlines(True), patched.splitlines(True),
                                                      fromfile='a/' + self.selected['path'], tofile='b/' + self.selected['path']))
                    (self.output / 'proposal.diff').write_text(diff, encoding='utf-8')
                    self.record('staged', path=self.selected['path'], beforeHash=self.selected['beforeHash'], afterHash=hashlib.sha256(patched.encode()).hexdigest())
                    phase, text = 'proposta', 'Arquivos na copia: 1\nTeste de regressao criado. Ainda nao executado.'
                elif action == 'TESTAR':
                    code, _ = self.run_node(self.regression, 'green', test=True)
                    req = self.selected['request']
                    # Tutor-owned acceptance contract, independent of model assertion.
                    behavior = self.module_import() + "import assert from 'node:assert/strict';\n" + f"const f=subject[{json.dumps(req['name'])}];\n"
                    behavior += f"for(const v of [null,undefined,'','invalid']) assert.equal(f(v),{json.dumps(req['fallback'])});\n"
                    behavior += "assert.notEqual(f(0),f(null));\nassert.notEqual(f('2024-02-29T12:00:00Z'),f(null));\n"
                    behavior_code, _ = self.run_node(behavior, 'behavior')
                    existing = sorted((self.root / 'app/tests').glob('*.test.mjs'))
                    existing_code = 0
                    if existing:
                        result = subprocess.run(['node', '--test', *map(str, existing)], cwd=self.root / 'app', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
                        existing_code = result.returncode
                        (self.output / 'existing-tests.log').write_text(result.stdout, encoding='utf-8')
                        self.record('execution', name='existing-tests', exitCode=existing_code)
                    self.test_passed = code == behavior_code == existing_code == 0
                    status = 'passou' if self.test_passed else 'falhou'
                    phase, text = 'testes', f'Regressao: {status}\nComportamento: {status}\nVerificacoes: 6'
                elif action == 'ENTREGAR_REVISAO':
                    if not self.changed or not self.test_passed:
                        raise PolicyError('Entrega sem testes aprovados bloqueada.')
                    state = 'awaiting_review'
                    break
                elif action == 'SEM_REPRODUCAO':
                    if self.candidates or not self.verified or self.changed or self.skipped:
                        raise PolicyError('Encerramento sem verificação bloqueado.')
                    state = 'not_reproduced'
                    break
            else:
                self.record('budget_exhausted', limit=self.max_steps)
        except (PolicyError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
            self.record('blocked', reason=str(exc), exception=type(exc).__name__)
        result = {'state': state, 'changed': self.changed, 'testsPassed': self.test_passed,
                  'actions': sum(e['event'] == 'model_action' for e in self.events),
                  'generalProgrammingQualified': False, 'appliedToOriginal': False}
        result['uninspectedModules'] = self.skipped
        proposal_file = self.output / 'proposal.json'
        if proposal_file.is_file():
            artifact = json.loads(proposal_file.read_text(encoding='utf-8'))
            artifact.update(state='awaiting_review' if state == 'awaiting_review' else 'rejected', testsPassed=self.test_passed)
            proposal_file.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding='utf-8')
        self.record('finished', **result)
        (self.output / 'result.json').write_text(json.dumps(result, indent=2))
        return result
