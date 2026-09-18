"""Train and independently reload authored UI-text classifiers; never activate them."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'qa')]
import numpy as np
from investigation_text_course import make_splits
from localauthor.browser_investigation import BrowserInvestigation
from localauthor.dataset import validate_dataset
from localauthor.investigation_text import InvestigationText, LABELS, encode, annotate_observation
from localauthor.nn.optimizer import AdamW
from localauthor.nn.tensor import cross_entropy, no_grad
from localauthor.util import write_json


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def grade(models, rows):
    return [{**row, 'generated': (prediction := models[row['kind']].predict(row['text'])),
             'passed': prediction['label'] == row['label']} for row in rows]


def page_audit(models, rows):
    statuses = [r for r in rows if r['kind'] == 'status']
    controls = [r for r in rows if r['kind'] == 'control']
    # Fictional pages composed of held-out text, longer than the old 256-byte
    # context. This grades independent annotations, not comprehension of a page.
    results = []
    for i, row in enumerate(statuses):
        text = ('Informações gerais do produto\n' * 18) + row['text'] + '\n'
        order = controls[i % len(controls):] + controls[:i % len(controls)]
        payload = {'url': 'https://qa.example.test/pagina-' + str(i),
                   'title': 'Laboratório fictício', 'text': text, 'controls': [
                       {'id': 'c' + str(j), 'name': r['text'], 'role': 'button',
                        'navigation': False, 'href': None} for j, r in enumerate(order)]}
        session = BrowserInvestigation('https://qa.example.test')
        observation = session.observe(payload)
        result = annotate_observation(observation, models['status'], models['control'])
        correct = result['blocks'][-1]['hypothesis']['label'] == row['label']
        correct &= all(b['hypothesis']['label'] == 'unknown' for b in result['blocks'][:-1])
        correct &= all(c['hypothesis']['label'] == r['label'] for c, r in zip(result['controls'], order))
        correct &= ''.join(b['text'] for b in result['blocks']) == text
        correct &= not session.trace and not result['authorizesAction']
        results.append({'id': f'page-{i}', 'utf8Bytes': len(text.encode()), 'passed': bool(correct),
                        'browserExecuted': False, 'crossSegmentReasoning': False})
    return results


def audit(path):
    report = json.loads(path.read_text(encoding='utf-8'))
    frozen = path.parent / 'frozen-test.json'
    if digest(frozen) != report['testHash']:
        raise ValueError('Frozen evaluation hash changed.')
    validation_path = path.parent / 'frozen-validation.json'
    if digest(validation_path) != report['validationHash']:
        raise ValueError('Frozen validation hash changed.')
    models = {}
    for kind, checkpoint in report['checkpoints'].items():
        if digest(checkpoint['path']) != checkpoint['sha256']:
            raise ValueError('Checkpoint hash changed.')
        models[kind] = InvestigationText.load(checkpoint['path'], kind)
    rows = json.loads(frozen.read_text(encoding='utf-8'))
    cases = grade(models, rows)
    validation = grade(models, json.loads(validation_path.read_text(encoding='utf-8')))
    pages = page_audit(models, rows)
    result = {'cases': cases, 'validation': validation, 'pages': pages,
              'validationPassed': sum(r['passed'] for r in validation),
              'passed': sum(r['passed'] for r in cases),
              'total': len(cases), 'pagesPassed': sum(r['passed'] for r in pages),
              'pagesTotal': len(pages),
              'originalUnchanged': all(digest(p) == h for p, h in report['protectedCheckpoints'].items()),
              'realSiteAutonomy': False, 'freeTextInvestigationQualified': False}
    result['approvedScopeOnly'] = (result['passed'] == result['total']
                                  and result['pagesPassed'] == len(pages)
                                  and result['originalUnchanged'] and all(r['passed'] for r in validation))
    write_json(path.parent / 'independent-audit.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('cases', 'pages', 'validation')}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--steps', type=int, default=600)
    parser.add_argument('--corrective', action='store_true')
    args = parser.parse_args()
    if args.audit:
        raise SystemExit(0 if audit(args.audit)['approvedScopeOnly'] else 1)
    if not 100 <= args.steps <= 3000 or args.steps % 50:
        raise ValueError('Use 100..3000 steps, multiple of 50.')
    home = Path(os.environ['LOCALAPPDATA']) / 'LocalAuthor'
    name = 'investigation-text-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    corpus, models_dir, export = [home / folder / name for folder in ('corpus', 'models', 'exports')]
    for folder in (corpus, models_dir, export):
        folder.mkdir(parents=True)
    splits = make_splits(args.corrective)
    records = []
    for split, rows in splits.items():
        for row in rows:
            path = corpus / (row['id'] + '.json')
            write_json(path, row)
            records.append({'path': path.name, 'split': split, 'group': row['id'],
                            'sha256': digest(path), 'training_allowed': split != 'test',
                            'provenance': {'kind': 'synthetic-authorized', 'owner': 'Rafael; lessons authored by Codex',
                            'license_or_permission': 'Requested teaching local AI. New fictional UI text; no private site data.'}})
    manifest = corpus / 'manifest.json'
    write_json(manifest, {'schema_version': 1, 'dataset_id': name, 'records': records})
    validated = validate_dataset(manifest)
    frozen = export / 'frozen-test.json'
    write_json(frozen, splits['test'])
    validation_path = export / 'frozen-validation.json'
    write_json(validation_path, splits['validation'])
    protected = {}
    for report_file in ('engineering-report.json', 'investigation-lab-20260918T132606Z/report.json'):
        prior = home / 'exports' / report_file
        if prior.exists():
            checkpoint = json.loads(prior.read_text(encoding='utf-8'))['selectedCheckpoint']
            protected[checkpoint] = digest(checkpoint)
    report = {'architecture': 'two own 2048-32-class GELU classifiers; fixed text hashing',
              'dependenciesAdded': [], 'activated': False, 'realSiteAutonomy': False,
              'manifestHash': validated['manifest_hash'], 'testHash': digest(frozen),
              'manifestPath': str(manifest), 'validationHash': digest(validation_path),
              'protectedCheckpoints': protected, 'counts': {k: len(v) for k, v in splits.items()},
              'checkpoints': {}, 'history': {}, 'validationAllPassed': True,
              'testUsedForSelection': False, 'originalLanguageModelTrained': False,
              'stepsPerHead': args.steps, 'modelSeed': 71926, 'batchSeed': 891,
              'sourceHashes': {str(p.relative_to(ROOT)): digest(p) for p in (
                  ROOT / 'src/localauthor/investigation_text.py',
                  ROOT / 'qa/investigation_text_course.py', Path(__file__))}}
    report['correctiveCourse'] = args.corrective
    report['evaluationStatus'] = ('Development audit: iterative corrections after contrast and validation failures; '
                                  'includes 12 additional phrases inspected in earlier corrective runs; '
                                  'not an untouched blind benchmark; no held-out gradients.' if args.corrective
                                  else 'Initial small synthetic phrase holdout.')
    output = export / 'report.json'
    write_json(output, report)
    print(json.dumps({'report': str(output), 'counts': report['counts']}), flush=True)
    models = {kind: InvestigationText(kind) for kind in LABELS}
    report['before'] = grade(models, splits['test'])
    started = time.monotonic()
    for kind, model in models.items():
        train = [r for r in splits['train'] if r['kind'] == kind]
        validation = [r for r in splits['validation'] if r['kind'] == kind]
        x = np.stack([encode(r['text']) for r in train])
        y = np.array([LABELS[kind].index(r['label']) for r in train])
        vx = np.stack([encode(r['text']) for r in validation])
        vy = np.array([LABELS[kind].index(r['label']) for r in validation])
        optimizer = AdamW(model.parameters, lr=.003, weight_decay=.0001)
        rng = np.random.default_rng(891)
        best = (-1, float('-inf'))
        checkpoint = models_dir / (kind + '.npz')
        report['history'][kind] = []
        for step in range(1, args.steps + 1):
            indexes = rng.integers(0, len(x), 64)
            loss = cross_entropy(model.forward(x[indexes]), y[indexes])
            loss.backward()
            optimizer.step()
            if step % 50 == 0:
                with no_grad():
                    logits = model.forward(vx)
                    accuracy = int(np.sum(logits.data.argmax(axis=1) == vy))
                    validation_loss = float(cross_entropy(logits, vy).data)
                if (accuracy, -validation_loss) > best:
                    best = (accuracy, -validation_loss)
                    model.save(checkpoint)
                report['history'][kind].append({'step': step, 'validationPassed': accuracy,
                                               'validationTotal': len(vy), 'loss': validation_loss})
        report['checkpoints'][kind] = {'path': str(checkpoint), 'sha256': digest(checkpoint)}
        report['validationAllPassed'] &= best[0] == len(vy)
        print(json.dumps({'kind': kind, 'validationPassed': best[0], 'total': len(vy)}), flush=True)
    report['elapsedSeconds'] = time.monotonic() - started
    write_json(output, report)
    result = audit(output)
    report['labApproved'] = result['approvedScopeOnly']
    report['after'] = result['cases']
    report['pages'] = result['pages']
    write_json(output, report)
    raise SystemExit(0 if report['labApproved'] else 1)


if __name__ == '__main__':
    main()
