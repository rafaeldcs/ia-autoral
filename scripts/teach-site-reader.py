"""Train finite purpose classifiers on fictional lessons; no real-site training."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'qa')]
import numpy as np
from site_reader_course import make_splits
from localauthor.dataset import validate_dataset
from localauthor.nn.optimizer import AdamW
from localauthor.nn.tensor import cross_entropy, no_grad
from localauthor.site_reader import SiteReader, features, PURPOSES
from localauthor.util import write_json


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def grade(models, rows):
    return [{**r, 'generated': (p := models[r['kind']].predict(r['title'], r['elements'])),
             'passed': p['label'] == r['label']} for r in rows]


def audit(path):
    report = json.loads(path.read_text(encoding='utf-8'))
    models = {}
    for kind, info in report['checkpoints'].items():
        if digest(info['path']) != info['sha256']:
            raise ValueError('Checkpoint changed after training.')
        models[kind] = SiteReader.load(info['path'], kind)
    cases = {}
    for split in ('validation', 'test'):
        frozen = path.parent / (split + '.json')
        if digest(frozen) != report['frozenHashes'][split]:
            raise ValueError('Frozen evaluation changed.')
        cases[split] = grade(models, json.loads(frozen.read_text(encoding='utf-8')))
    result = {'cases': cases, 'counts': {s: {'passed': sum(r['passed'] for r in rows),
                  'total': len(rows)} for s, rows in cases.items()},
              'originalsUnchanged': all(digest(p) == h for p, h in report['protected'].items()),
              'allSitesQualified': False, 'autonomousBrowserQualified': False,
              'freeFormLanguageQualified': False}
    result['courseApproved'] = all(all(r['passed'] for r in rows) for rows in cases.values()) and result['originalsUnchanged']
    write_json(path.parent / 'audit.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--steps', type=int, default=1200)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--corrective', action='store_true')
    args = parser.parse_args()
    if args.audit:
        raise SystemExit(0 if audit(args.audit)['courseApproved'] else 1)
    if not 100 <= args.steps <= 3000 or args.steps % 100:
        raise ValueError('Use 100..3000 steps in multiples of 100.')
    home = Path(os.environ['LOCALAPPDATA']) / 'LocalAuthor'
    run = 'site-reader-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    corpus, models_dir, export = [home / p / run for p in ('corpus', 'models', 'exports')]
    for folder in (corpus, models_dir, export): folder.mkdir(parents=True)
    splits, records = make_splits(args.corrective), []
    for split, rows in splits.items():
        for row in rows:
            file = corpus / (row['id'] + '.json'); write_json(file, row)
            records.append({'path': file.name, 'split': split, 'group': row['id'],
                'sha256': digest(file), 'training_allowed': split != 'test',
                'provenance': {'kind': 'synthetic-authorized', 'owner': 'Rafael; authored fictional lessons by Codex',
                    'license_or_permission': 'User requested teaching site interpretation. Original examples; no private site observations.'}})
    manifest = corpus / 'manifest.json'
    write_json(manifest, {'schema_version': 1, 'dataset_id': run, 'records': records})
    validated = validate_dataset(manifest)
    report = {'architecture': 'two own 4096-64-class MLPs, separate title/body hashing, fixed category descriptions',
              'dependenciesAdded': [], 'activated': False, 'allSitesQualified': False,
              'manifestPath': str(manifest), 'manifestHash': validated['manifest_hash'],
              'counts': {s: len(rows) for s, rows in splits.items()}, 'frozenHashes': {},
              'checkpoints': {}, 'history': {}, 'protected': {},
              'selection': 'validation accuracy, then validation cross entropy; no test gradients',
              'evaluationKind': 'authored development course; not independent universal certification',
              'corrective': args.corrective,
              'modelSeed': 92126, 'batchSeed': 128, 'steps': args.steps,
              'sourceHashes': {str(p.relative_to(ROOT)): digest(p) for p in (
                  ROOT / 'src/localauthor/site_reader.py', ROOT / 'qa/site_reader_course.py', Path(__file__))}}
    for split in ('validation', 'test'):
        file = export / (split + '.json'); write_json(file, splits[split])
        report['frozenHashes'][split] = digest(file)
    for prior in (home / 'exports').glob('**/report.json'):
        info = json.loads(prior.read_text(encoding='utf-8'))
        for value in list(info.get('checkpoints', {}).values()):
            if isinstance(value, dict) and Path(value.get('path', '')).is_file():
                report['protected'][value['path']] = digest(value['path'])
    engineering = home / 'exports/engineering-report.json'
    if engineering.exists():
        checkpoint = json.loads(engineering.read_text(encoding='utf-8'))['selectedCheckpoint']
        report['protected'][checkpoint] = digest(checkpoint)
    output = export / 'report.json'; write_json(output, report)
    print(json.dumps({'report': str(output), 'counts': report['counts']}), flush=True)
    models = {kind: SiteReader(kind) for kind in PURPOSES}
    report['before'] = grade(models, splits['test'])
    for kind, model in models.items():
        train = [r for r in splits['train'] if r['kind'] == kind]
        validation = [r for r in splits['validation'] if r['kind'] == kind]
        x = np.stack([features(r['title'], r['elements']) for r in train])
        y = np.array([model.labels.index(r['label']) for r in train])
        vx = np.stack([features(r['title'], r['elements']) for r in validation])
        vy = np.array([model.labels.index(r['label']) for r in validation])
        rng = np.random.default_rng(128)
        optimizer = AdamW(model.parameters, lr=.003, weight_decay=.0001)
        best = (-1, float('-inf')); report['history'][kind] = []
        checkpoint = models_dir / (kind + '.npz')
        for step in range(1, args.steps + 1):
            indexes = rng.integers(0, len(x), 96)
            loss = cross_entropy(model.forward(x[indexes]), y[indexes])
            loss.backward(); optimizer.step()
            if step % 100 == 0:
                with no_grad():
                    logits = model.forward(vx)
                    correct = int(np.sum(logits.data.argmax(axis=1) == vy))
                    vl = float(cross_entropy(logits, vy).data)
                report['history'][kind].append({'step': step, 'correct': correct, 'total': len(vy), 'loss': vl})
                if (correct, -vl) > best:
                    best = (correct, -vl); model.save(checkpoint)
        report['checkpoints'][kind] = {'path': str(checkpoint), 'sha256': digest(checkpoint)}
        print(json.dumps({'kind': kind, 'validationPassed': best[0], 'total': len(vy)}), flush=True)
    write_json(output, report)
    result = audit(output)
    report['courseApproved'] = result['courseApproved']
    write_json(output, report)
    raise SystemExit(0 if result['courseApproved'] else 1)


if __name__ == '__main__':
    main()
