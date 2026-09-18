"""Emit the local reader's unedited category choices and their authored wording.

Experimental candidates are allowed for evaluation, with their course status
included. This tool cannot certify sites, browse, or execute page instructions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from localauthor.site_reader import SiteReader, describe_site
from localauthor.util import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--observations', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for file in (args.report, args.observations):
        if file.stat().st_size > 4_000_000:
            raise ValueError('Input exceeds size budget.')
    report = json.loads(args.report.read_text(encoding='utf-8-sig'))
    models = {}
    for kind in ('site', 'screen'):
        info = report['checkpoints'][kind]
        path = Path(info['path'])
        if path.stat().st_size > 3_000_000 or hashlib.sha256(path.read_bytes()).hexdigest() != info['sha256']:
            raise ValueError('Checkpoint hash/size differs from the evaluated artifact.')
        models[kind] = SiteReader.load(path, kind)
    bundle = json.loads(args.observations.read_text(encoding='utf-8-sig'))
    response = describe_site(bundle, models['site'], models['screen'])
    response['courseApproved'] = report.get('courseApproved') is True
    response['checkpointHashes'] = {k: v['sha256'] for k, v in report['checkpoints'].items()}
    response['inputHash'] = hashlib.sha256(args.observations.read_bytes()).hexdigest()
    write_json(args.output, response)
    def inline(text):
        return str(text).replace('\n', ' ').replace('|', '\\|').replace('<', '&lt;').replace('>', '&gt;')
    lines = [f"# {inline(response['site'])}", '', response['purpose']['description'], '',
             response['notice'], '',
             '**Esta saída contém escolhas reais do classificador local. As frases são descrições fixas, não texto livre gerado.**', '',
             f"Cobertura fornecida: {response['coverage']}. Não significa todas as telas possíveis.", '',
             '| Tela | Resposta do leitor local | Origem da evidência |', '|---|---|---|']
    for screen in response['screens']:
        lines.append('| ' + ' | '.join(inline(screen[k]) for k in ('name', 'response', 'sourceKind')) + ' |')
    lines += ['', 'As previsões não foram corrigidas manualmente. Fonte, data, evidências, escores não calibrados e hashes estão no JSON correspondente.']
    args.output.with_suffix('.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'site': response['site'],
                      'purpose': response['purpose']['label'], 'coverage': response['coverage'],
                      'allSitesQualified': False}))


if __name__ == '__main__':
    main()
