"""From-scratch training. Frozen target is never used to select a checkpoint."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'qa')]
import numpy as np
from date_guard_course import examples, SCOPE
from localauthor.nn.transformer import Transformer, ModelConfig
from localauthor.nn.optimizer import AdamW
from localauthor.nn.tokenizer import BPETokenizer
from localauthor.nn.checkpoint import load_checkpoint, save_checkpoint

# Reuse reviewed numerical training primitives, without running the other course.
helpers = runpy.run_path(str(ROOT / 'scripts/train-code-repair.py'))
batch, response_loss = helpers['batch'], helpers['response_loss']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=6000)
    args = parser.parse_args()
    if not Path('/.dockerenv').is_file():
        raise RuntimeError('Run in reviewed sandbox, never on the host.')
    out = args.output.resolve()
    if out.is_relative_to(ROOT) or out.exists() and any(out.iterdir()):
        raise ValueError('Use a new private output folder outside the repository.')
    if not 500 <= args.steps <= 10000:
        raise ValueError('Bounded experiment requires 500–10000 steps.')
    out.mkdir(parents=True, exist_ok=True)
    splits = examples()
    frozen = json.dumps(splits, sort_keys=True, ensure_ascii=False).encode()
    (out / 'frozen-course.json').write_bytes(frozen)
    provenance = {'kind': 'original-synthetic-authorized', 'permission': 'User requested teaching, 2026-09-29',
                  'scope': SCOPE, 'corpusHash': hashlib.sha256(frozen).hexdigest(),
                  'testUsedForTraining': False, 'externalWeights': False}
    model, _, tokenizer, _, _ = load_checkpoint(args.baseline)
    target = splits['project'][0]
    before_ids = model.generate([256] + tokenizer.encode(target['prompt']), max_tokens=100, temperature=.05, seed=31)
    try:
        before = tokenizer.decode(before_ids)
    except UnicodeError:
        before = '[invalid UTF-8]'
    (out / 'before-teaching.json').write_text(json.dumps({'checkpointHash': hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
        'prompt': target['prompt'], 'generated': before, 'exact': before == target['answer'],
        'applied': False}, ensure_ascii=False, indent=2), encoding='utf-8')
    tokenizer = BPETokenizer.train([row['prompt'] + row['answer'] for row in splits['train']], vocab_size=384)
    model = Transformer(ModelConfig(vocab_size=tokenizer.vocab_size, context_length=192, dimension=64, heads=4, layers=2, expansion=2, seed=7441))
    optimizer = AdamW(model.parameters, lr=.001)
    rng = np.random.default_rng(7241)
    if max(batch([row], tokenizer)[0].shape[1] for row in splits['train']) > 192:
        raise ValueError('Training context exceeded.')
    def evaluate(rows):
        results = []
        for row in rows:
            ids = model.generate([256] + tokenizer.encode(row['prompt']), max_tokens=100, temperature=.05, seed=31)
            try:
                generated = tokenizer.decode(ids)
            except UnicodeError:
                generated = '[invalid UTF-8]'
            results.append({**row, 'generated': generated, 'exact': generated == row['answer']})
        return results
    report = {'scope': SCOPE, 'provenance': provenance, 'parameters': model.parameter_count,
              'counts': {k: len(v) for k, v in splits.items()}, 'history': [], 'generalProgrammingQualified': False}
    print(json.dumps({'counts': report['counts'], 'parameters': report['parameters'], 'baselinePassed': before == target['answer']}), flush=True)
    best, streak = -1, 0
    start = time.monotonic()
    for step in range(1, args.steps + 1):
        rows = [splits['train'][int(i)] for i in rng.integers(0, len(splits['train']), size=4)]
        x, y, mask = batch(rows, tokenizer)
        loss = response_loss(model.forward(x), y, mask)
        loss.backward()
        optimizer.step()
        if step % 250 == 0:
            print(json.dumps({'step': step, 'loss': float(loss.data), 'seconds': round(time.monotonic() - start)}), flush=True)
        if step % 500 == 0:
            validation = evaluate(splits['validation'])
            score = sum(row['exact'] for row in validation)
            report['history'].append({'step': step, 'passed': score, 'total': len(validation)})
            if score >= best:
                best = score
                save_checkpoint(out / 'best-validation.npz', model, optimizer, tokenizer, rng, provenance)
                report['selectedStep'] = step
            streak = streak + 1 if score == len(validation) else 0
            (out / 'validation-latest.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(report['history'][-1]), flush=True)
            if streak >= 2:
                break
    model, _, tokenizer, _, _ = load_checkpoint(out / 'best-validation.npz')
    report.update(state='awaiting_independent_execution', checkpointHash=hashlib.sha256((out / 'best-validation.npz').read_bytes()).hexdigest(),
                  test=evaluate(splits['test']), project=evaluate(splits['project']))
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'test': sum(r['exact'] for r in report['test']), 'project': sum(r['exact'] for r in report['project'])}), flush=True)


if __name__ == '__main__':
    main()
