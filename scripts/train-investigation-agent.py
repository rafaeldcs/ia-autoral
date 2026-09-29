"""Train a bounded local tool policy, without external weights or held-out episodes."""
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
from investigation_agent_course import lessons, challenges, SCOPE, TEST_REPORT, observation
from localauthor.nn.transformer import Transformer, ModelConfig
from localauthor.nn.optimizer import AdamW
from localauthor.nn.tokenizer import BPETokenizer
from localauthor.nn.checkpoint import load_checkpoint, save_checkpoint
helpers = runpy.run_path(str(ROOT / 'scripts/train-code-repair.py'))
batch, response_loss = helpers['batch'], helpers['response_loss']


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--steps', type=int, default=6000)
    args = p.parse_args()
    if not Path('/.dockerenv').is_file():
        raise RuntimeError('Reviewed sandbox required.')
    out = args.output.resolve()
    if out.is_relative_to(ROOT) or out.exists() and any(out.iterdir()):
        raise ValueError('Use a new private experiment directory.')
    if not 500 <= args.steps <= 10000:
        raise ValueError('Step budget out of range.')
    out.mkdir(parents=True, exist_ok=True)
    course = {**lessons(), 'challenges': challenges()}
    seen = {row['prompt'] for row in course['train'] + course['validation']}
    if any(observation('inicio', case['report']) in seen for case in course['challenges'] if case.get('partition') == 'fresh'):
        raise ValueError('Reserved report leaked into training/validation. No training performed.')
    raw = json.dumps(course, sort_keys=True, ensure_ascii=False).encode()
    (out / 'frozen-course.json').write_bytes(raw)
    provenance = {'kind': 'original-synthetic-authorized', 'permission': 'User requested investigation teaching, 2026-09-29',
                  'scope': SCOPE, 'corpusHash': hashlib.sha256(raw).hexdigest(), 'fullEvaluationTrajectoriesUsedForTraining': False,
                  'reservedReportsUsedForTraining': False, 'priorFailedReportsUsedForTeaching': True}
    previous, _, previous_tokenizer, _, _ = load_checkpoint(args.baseline)
    initial = observation('inicio', TEST_REPORT)
    try:
        baseline = previous_tokenizer.decode(previous.generate([256] + previous_tokenizer.encode(initial), max_tokens=32, temperature=.05, seed=31))
    except UnicodeError:
        baseline = '[invalid UTF-8]'
    (out / 'baseline.json').write_text(json.dumps({'prompt': initial, 'generated': baseline, 'checkpointHash': hashlib.sha256(args.baseline.read_bytes()).hexdigest(), 'accepted': baseline == 'BUSCAR new Date'}, ensure_ascii=False, indent=2), encoding='utf-8')
    tokenizer = BPETokenizer.train([r['prompt'] + r['answer'] for r in course['train']], vocab_size=512)
    model = Transformer(ModelConfig(vocab_size=tokenizer.vocab_size, context_length=256, dimension=64, heads=4, layers=2, expansion=2, seed=9421))
    optimizer = AdamW(model.parameters, lr=.001)
    rng = np.random.default_rng(4921)
    if max(batch([row], tokenizer)[0].shape[1] for row in course['train'] + course['validation']) > 256:
        raise ValueError('Context exceeded.')
    report = {'scope': SCOPE, 'counts': {k: len(v) for k, v in course.items()}, 'parameters': model.parameter_count,
              'provenance': provenance, 'history': [], 'generalProgrammingQualified': False}
    report['sampling'] = 'uniform action, then uniform training example; language volume must not erase rare tool skills'
    groups = {}
    for row in course['train']:
        groups.setdefault(row['answer'], []).append(row)
    labels = sorted(groups)
    rehearsal = [row for label in labels for row in groups[label][:3]]
    print(json.dumps({'counts': report['counts'], 'parameters': model.parameter_count, 'baseline': baseline}), flush=True)
    best, streak = -1, 0
    for step in range(1, args.steps + 1):
        rows = []
        for index in rng.integers(0, len(labels), size=4):
            pool = groups[labels[int(index)]]
            rows.append(pool[int(rng.integers(0, len(pool)))])
        x, y, mask = batch(rows, tokenizer)
        loss = response_loss(model.forward(x), y, mask)
        loss.backward()
        optimizer.step()
        if step % 500 == 0:
            validation = []
            for row in course['validation'] + rehearsal:
                try:
                    generated = tokenizer.decode(model.generate([256] + tokenizer.encode(row['prompt']), max_tokens=32, temperature=.05, seed=31))
                except UnicodeError:
                    generated = '[invalid UTF-8]'
                validation.append({**row, 'generated': generated, 'passed': generated == row['answer']})
            validation_count = len(course['validation'])
            score = sum(r['passed'] for r in validation[:validation_count])
            rehearsal_ok = all(r['passed'] for r in validation[validation_count:])
            report['history'].append({'step': step, 'passed': score, 'total': validation_count, 'rehearsalPassed': rehearsal_ok, 'loss': float(loss.data)})
            if score >= best:
                best = score
                save_checkpoint(out / 'best-validation.npz', model, optimizer, tokenizer, rng, provenance)
                report['selectedStep'] = step
            streak = streak + 1 if score == validation_count and rehearsal_ok else 0
            (out / 'validation.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(report['history'][-1]), flush=True)
            if streak >= 2:
                break
    report.update(state='awaiting_episode_evaluation', checkpointHash=hashlib.sha256((out / 'best-validation.npz').read_bytes()).hexdigest())
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
