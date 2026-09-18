"""Teach own local weights a bounded next-step task. Never executes actions."""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'qa')]
import numpy as np
from investigation_course import examples
from localauthor.dataset import validate_dataset
from localauthor.nn.checkpoint import load_checkpoint, save_checkpoint
from localauthor.nn.optimizer import AdamW
from localauthor.nn.tensor import Tensor
from localauthor.util import write_json


def batch(rows, tokenizer):
    sequences, starts = [], []
    for row in rows:
        prefix = [tokenizer.bos_id] + tokenizer.encode(row['prompt'])
        sequences.append(prefix + tokenizer.encode(row['answer']) + [tokenizer.eos_id])
        starts.append(len(prefix) - 1)
    size = max(len(s) - 1 for s in sequences)
    x = np.full((len(rows), size), tokenizer.eos_id, dtype=np.int64)
    y, mask = x.copy(), np.zeros_like(x, dtype=np.float64)
    for i, (sequence, start) in enumerate(zip(sequences, starts)):
        end = len(sequence) - 1
        x[i, :end], y[i, :end], mask[i, start:end] = sequence[:-1], sequence[1:], 1
    return x, y, mask


def response_loss(logits: Tensor, targets, mask):
    flat = logits.data.reshape(-1, logits.data.shape[-1])
    shifted = flat - flat.max(axis=1, keepdims=True)
    exponential = np.exp(shifted)
    probabilities = exponential / exponential.sum(axis=1, keepdims=True)
    rows, weights = np.arange(targets.size), mask.ravel() / mask.sum()
    loss = float(((-shifted[rows, targets.ravel()] + np.log(exponential.sum(axis=1))) * weights).sum())
    def backward(g):
        gradient = probabilities.copy()
        gradient[rows, targets.ravel()] -= 1
        logits._add_grad((gradient * weights[:, None]).reshape(logits.data.shape) * float(g))
    return logits._result(loss, (logits,), backward)


def evaluate(model, tokenizer, cases):
    result = []
    for case in cases:
        generated = model.generate([tokenizer.bos_id] + tokenizer.encode(case['prompt']),
                                   max_tokens=64, temperature=.05, seed=31)
        try:
            text = tokenizer.decode(generated)
        except UnicodeError:
            text = '[invalid UTF-8]'
        # No completion repair, lookup substitution, or forgiving JSON extraction.
        result.append({**case, 'generated': text, 'passed': text == case['answer']})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--steps', type=int, default=2000)
    args = parser.parse_args()
    if not 400 <= args.steps <= 6000 or args.steps % 400:
        raise ValueError('Use 400..6000 steps in multiples of 400.')
    home = Path(os.environ['LOCALAPPDATA']) / 'LocalAuthor'
    previous = json.loads((home / 'exports/engineering-report.json').read_text(encoding='utf-8'))
    parent = Path(previous['selectedCheckpoint']).resolve(strict=True)
    if not parent.is_relative_to((home / 'models').resolve()):
        raise ValueError('Parent outside own models directory.')
    if hashlib.sha256(parent.read_bytes()).hexdigest() != previous['checkpointHash']:
        raise ValueError('Parent checksum mismatch.')
    model, _, tokenizer, _, _ = load_checkpoint(parent)
    old_manifest = home / 'corpus' / parent.parent.name / 'manifest.json'
    old = validate_dataset(old_manifest)
    replay = []
    for item in old['splits']['train']:
        prefix, marker, answer = item['text'].replace('\r\n', '\n').partition('\nJSON:\n')
        if marker:
            replay.append({'id': 'replay-' + Path(item['path']).stem,
                           'prompt': prefix + marker, 'answer': answer})
    if not replay:
        raise ValueError('No authorized training rehearsal available.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    name = 'investigation-' + stamp
    out, corpus, export = (home / folder / name for folder in ('models', 'corpus', 'exports'))
    for folder in (out, corpus, export):
        folder.mkdir(parents=True)
    train, validation, final = (examples(split) for split in ('train', 'validation', 'test'))
    records = []
    for split, cases in [('train', train + replay), ('validation', validation), ('test', final)]:
        for case in cases:
            raw = case['prompt'] + case['answer']
            if len(tokenizer.encode(raw)) + 2 > model.config.context_length:
                raise ValueError('Context overflow: ' + case['id'])
            file = corpus / split / (case['id'] + '.txt')
            file.parent.mkdir(exist_ok=True)
            file.write_text(raw, encoding='utf-8', newline='\n')
            records.append({'path': file.relative_to(corpus).as_posix(), 'split': split,
                'group': case['id'], 'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                'training_allowed': split != 'test', 'provenance': {
                    'kind': 'synthetic-authorized', 'owner': 'Rafael; original examples authored by Codex',
                    'license_or_permission': 'User requested teaching investigation. Synthetic examples only; no private site data. Rehearsal copies previously authorized training split.'}})
    manifest = corpus / 'manifest.json'
    write_json(manifest, {'schema_version': 1, 'dataset_id': name, 'records': records})
    validated = validate_dataset(manifest)
    write_json(export / 'frozen-tests.json', final)
    report = {'state': 'training', 'scope': 'synthetic-next-step-classification',
              'parentCheckpoint': str(parent), 'parentHash': previous['checkpointHash'],
              'selectedCheckpoint': str(out / 'best-validation.npz'),
              'manifestHash': validated['manifest_hash'], 'weightsUpdated': False,
              'autonomousBrowserQualified': False, 'chatEnabled': False,
              'counts': {'train': len(train), 'replay': len(replay), 'validation': len(validation), 'test': len(final)},
              'history': [], 'limitations': 'Closed set of 12 next-step labels. New test wording, same families. No browser execution, no real-site autonomous evaluation, no general reasoning qualification.'}
    report['before'] = evaluate(model, tokenizer, final)
    write_json(export / 'report.json', report)
    print(json.dumps({'report': str(export / 'report.json'), 'counts': report['counts']}), flush=True)
    optimizer, rng, best = AdamW(model.parameters, lr=.0007), np.random.default_rng(91826), -1
    for step in range(1, args.steps + 1):
        pool = replay if step % 4 == 0 else train
        selected = [pool[int(i)] for i in rng.integers(0, len(pool), size=2)]
        x, y, mask = batch(selected, tokenizer)
        loss = response_loss(model.forward(x), y, mask)
        loss.backward(); optimizer.step()
        if step % 100 == 0:
            print(json.dumps({'step': step, 'loss': float(loss.data)}), flush=True)
        if step % 400 == 0:
            cases = evaluate(model, tokenizer, validation)
            score = sum(case['passed'] for case in cases)
            report['history'].append({'step': step, 'passed': score, 'total': len(cases)})
            if score > best:
                best = score
                report['selectedStep'] = step
                save_checkpoint(out / 'best-validation.npz', model, optimizer, tokenizer, rng,
                                {'manifest_hash': validated['manifest_hash'], 'test_used_for_selection': False})
            write_json(export / 'report.json', report)
            print(json.dumps(report['history'][-1]), flush=True)
    model, _, tokenizer, _, _ = load_checkpoint(out / 'best-validation.npz')
    report.update(state='evaluated', weightsUpdated=True, after=evaluate(model, tokenizer, final),
                  regression=evaluate(model, tokenizer, previous['evaluation']['cases']),
                  checkpointHash=hashlib.sha256((out / 'best-validation.npz').read_bytes()).hexdigest())
    report['testPassed'] = sum(c['passed'] for c in report['after'])
    report['regressionPassed'] = sum(c['passed'] for c in report['regression'])
    write_json(export / 'report.json', report)
    print(json.dumps({'report': str(export / 'report.json'), 'testPassed': report['testPassed'],
                      'testTotal': len(final), 'regressionPassed': report['regressionPassed'],
                      'regressionTotal': len(report['regression']), 'activated': False}), flush=True)


if __name__ == '__main__':
    main()
