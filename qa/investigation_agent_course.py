"""Original, bounded tool-policy lessons. Episode partitions are frozen before training."""
import hashlib
from itertools import product

SCOPE = 'missing-date-investigation-tools-v2'
TRAIN_REPORTS = ('A data ausente aparece como 1969.', 'Sem informar uma data, vejo 1970.',
                 'Uma data vazia virou uma data antiga.', 'A tela mostra data antiga quando não há data.')
UNKNOWN_REPORTS = ('O saldo da mensalidade está errado.', 'Não consigo entrar com minha senha.',
                   'O estoque está negativo.', 'Quero criar um relatório financeiro.')
TEST_REPORT = 'Uma tela mostra 1969 quando a data não foi informada.'


def observation(stage, text):
    return f'Investigacao limitada de datas\nEtapa: {stage}\n{text}\nAcao:\n'


def lessons():
    rows = []
    def add(stage, text, answer, partition=None):
        message = observation(stage, text)
        rows.append({'id': hashlib.sha256(message.encode()).hexdigest()[:16], 'prompt': message, 'answer': answer, 'partition': partition})
    for report in TRAIN_REPORTS:
        add('inicio', report, 'BUSCAR new Date')
    for report in UNKNOWN_REPORTS:
        add('inicio', report, 'PEDIR_AJUDA')
    for lead, subject in product(('Quero', 'Preciso', 'Gostaria de', 'Como posso', 'Ajude a'),
                                 ('alterar a senha', 'redefinir o acesso', 'corrigir o saldo', 'organizar o estoque',
                                  'criar um relatório financeiro', 'mudar permissões', 'cancelar um Pix', 'agendar uma data de reunião')):
        add('inicio', f'{lead} {subject}.', 'PEDIR_AJUDA')
    for place, symptom in product(('A tela', 'O aplicativo', 'A página', 'O sistema'),
                                  ('mostra 1969 sem uma data', 'exibe 1970 quando a data está vazia',
                                   'converte data ausente em data antiga', 'mostra janeiro de 1970 sem data informada',
                                   'exibe dezembro de 1969 para uma data não preenchida')):
        add('inicio', f'{place} {symptom}.', 'BUSCAR new Date')
    for count in range(1, 6):
        listing = f'Resultados: {count}\nReferencias: ' + ','.join(str(i) for i in range(count))
        add('busca', listing, 'LER 0')
    for checked in range(6):
        add('esgotado', f'Provas aprovadas: {checked}', 'SEM_REPRODUCAO' if checked else 'PEDIR_AJUDA')
    for name, parameter, fallback in product(('formatDate', 'showDate', 'renderDate', 'displayDate', 'printDate'),
                                            ('value', 'input', 'raw', 'item'), ('Sem data', 'Ausente', 'Data indisponível', 'Não informado')):
        excerpt = f'function {name}({parameter})\nconst date = new Date({parameter});\nAusencia esperada: {fallback}'
        add('leitura', excerpt, 'PROVAR null')
    for reason in ('sem função compatível', 'múltiplas funções compatíveis', 'formato não suportado', 'nenhuma mensagem de ausência'):
        add('leitura_incompativel', reason, 'PROXIMO')
    for value in ('1969-12-31', '1970-01-01T00:00:00.000Z', '31 de dez. de 1969, 21:00', '01/01/1970', 'Data antiga'):
        add('prova', f'Entrada: null\nContrato de ausencia: falhou\nSaida: {value}', 'CORRIGIR_AUSENCIA')
    for label in ('Sem data', 'Ausente', 'Data indisponível', 'Não informado'):
        add('prova', f'Entrada: null\nContrato de ausencia: passou\nSaida: {label}', 'PROXIMO')
    for error in ('TypeError', 'SyntaxError', 'timeout', 'saida invalida'):
        add('erro', error, 'PEDIR_AJUDA')
    for count in range(1, 9):
        add('proposta', f'Arquivos na copia: {count}\nTeste de regressao criado. Ainda nao executado.', 'TESTAR')
        add('testes', f'Regressao: passou\nComportamento: passou\nVerificacoes: {count}', 'ENTREGAR_REVISAO')
        add('testes', f'Regressao: falhou\nComportamento: falhou\nVerificacoes: {count}', 'PEDIR_AJUDA')
    # Previously evaluated reports are now teaching/regression data, never fresh tests.
    for case in second_round_challenges():
        add('inicio', case['report'], 'PEDIR_AJUDA' if case['kind'] == 'unknown' else 'BUSCAR new Date', 'train')
    for row in language_rows():
        if row['partition'] != 'test':
            add('inicio', row['report'], row['answer'], row['partition'])
    # Every row remains within familiar tool stages; this is not open-ended reasoning.
    reserved = {observation('inicio', r['report']) for r in language_rows() if r['partition'] == 'test'}
    # Initial hand-authored lessons may coincide with a generated phrase. The
    # reserved partition has priority everywhere, not only in the generator.
    unique = {r['prompt']: r for r in rows if r['prompt'] not in reserved}
    splits = {'train': [], 'validation': []}
    for row in unique.values():
        split = row['partition'] or ('validation' if int(row['id'][:8], 16) % 11 == 0 else 'train')
        splits[split].append(row)
    return splits


def previous_challenges():
    """Private concrete tasks are generated only by the evaluator, not the trainer."""
    cases = []
    for index in range(12):
        cases.append({'id': f'bug-{index}', 'kind': 'bug', 'position': index % 4,
                      'report': TEST_REPORT if index % 2 == 0 else 'Sem data cadastrada, a tela exibe 1970.',
                      'seed': 17000 + index, 'expected': 'awaiting_review'})
    for index in range(4):
        cases.append({'id': f'clean-{index}', 'kind': 'clean', 'position': -1,
                      'report': TEST_REPORT, 'seed': 18000 + index, 'expected': 'not_reproduced'})
    for index in range(4):
        cases.append({'id': f'unknown-{index}', 'kind': 'unknown', 'position': -1,
                      'report': ('O Pix foi cobrado duas vezes.', 'Meu estoque desapareceu.', 'Preciso alterar a senha.', 'O total financeiro está incorreto.')[index],
                      'seed': 19000 + index, 'expected': 'needs_help'})
    for index in range(4):
        cases.append({'id': f'error-{index}', 'kind': 'error', 'position': 0,
                      'report': TEST_REPORT, 'seed': 20000 + index, 'expected': 'needs_help'})
    for index in range(4):
        cases.append({'id': f'failed-tests-{index}', 'kind': 'failed-tests', 'position': index,
                      'report': TEST_REPORT, 'seed': 21000 + index, 'expected': 'needs_help'})
    return cases


def second_round_challenges():
    cases = previous_challenges()
    for case in cases:
        case['partition'] = 'fresh'
        case['seed'] += 13000
        if case['kind'] == 'unknown':
            number = int(case['id'].split('-')[-1])
            case['report'] = ('Como posso modificar minha senha?', 'Quero conferir o saldo da conta.',
                              'Preciso revisar as quantidades do estoque.', 'Gostaria de corrigir um pagamento Pix.')[number]
        else:
            case['report'] = ('Uma data não preenchida aparece como janeiro de 1970.' if case['seed'] % 2 == 0
                              else 'No lugar de data ausente, a página mostra dezembro de 1969.')
    for old in previous_challenges():
        cases.append({**old, 'id': 'regression-' + old['id'], 'partition': 'regression'})
    return cases


def language_rows():
    """Finite-language compositional evaluation, not arbitrary Portuguese competence."""
    old = {case['report'] for case in second_round_challenges()}
    reports = []
    for subject, verb, year, condition in product(
            ('A tela', 'O aplicativo', 'A página', 'O sistema', 'O cadastro', 'A agenda', 'O painel', 'Uma tela'),
            ('mostra', 'exibe', 'apresenta'), ('1969', '1970'),
            ('quando a data não foi informada', 'quando a data está ausente', 'sem data cadastrada',
             'quando o campo de data está vazio', 'para data não preenchida')):
        reports.append((f'{subject} {verb} {year} {condition}.', 'BUSCAR new Date'))
    for lead, action, suffix in product(
            ('Quero', 'Preciso', 'Gostaria de', 'Não consigo', 'Como posso', 'Ajude-me a'),
            ('mudar a senha', 'alterar permissões', 'corrigir o saldo', 'revisar o estoque', 'estornar o Pix',
             'confirmar um recebimento', 'agendar uma data de reunião'), ('.', ' no aplicativo.', ' na minha conta.')):
        reports.append((f'{lead} {action}{suffix}', 'PEDIR_AJUDA'))
    rows = []
    for report, answer in reports:
        number = int(hashlib.sha256(report.encode()).hexdigest()[:8], 16)
        partition = 'train' if report in old else 'test' if number % 13 == 0 else 'validation' if number % 11 == 0 else 'train'
        rows.append({'report': report, 'answer': answer, 'partition': partition})
    return rows


def third_round_challenges():
    heldout = [r for r in language_rows() if r['partition'] == 'test']
    dates = [r['report'] for r in heldout if r['answer'] == 'BUSCAR new Date']
    others = [r['report'] for r in heldout if r['answer'] == 'PEDIR_AJUDA']
    cases = previous_challenges()
    for index, case in enumerate(cases):
        case.update(partition='fresh', seed=case['seed'] + 29000)
        case['report'] = others[index % len(others)] if case['kind'] == 'unknown' else dates[index % len(dates)]
    for case in second_round_challenges():
        cases.append({**case, 'id': 'regression-v2-' + case['id'], 'partition': 'regression'})
    return cases


def challenges():
    previous = third_round_challenges()
    fresh = []
    for case in previous:
        if case['partition'] == 'fresh':
            fresh.append({**case, 'seed': case['seed'] + 41000, 'reportPreviouslyEvaluated': True})
    return fresh + [{**case, 'id': 'regression-v3-' + case['id'], 'partition': 'regression'} for case in previous]
