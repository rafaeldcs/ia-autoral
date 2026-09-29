"""Guided apprentice: source context -> neural guard/test -> real red/green -> review.

Teacher supplies the bug hypothesis and symbol. This is a workflow, not general autonomy.
All generated code executes only inside the reviewed, network-disabled container.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src')]
from localauthor.date_repair import SCOPE, parse_request, validate_proposal, source_context, stage
from localauthor.nn.checkpoint import load_checkpoint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True, help='Git archive of the reviewed project baseline, never a live private tree')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not Path('/.dockerenv').is_file():
        raise RuntimeError('A reviewed Docker sandbox is required.')
    snapshot = tempfile.TemporaryDirectory()
    args.project = Path(snapshot.name) / 'source'
    args.project.mkdir()
    with tarfile.open(args.archive) as archive:
        members = archive.getmembers()
        if len(members) > 5000 or sum(m.size for m in members) > 100_000_000 or any(not (m.isfile() or m.isdir()) for m in members):
            raise ValueError('Archive exceeds source-only limits or contains links.')
        archive.extractall(args.project, filter='data')
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('Preserve receipts: use a new output directory.')
    args.output.mkdir(parents=True, exist_ok=True)
    report = json.loads((args.model / 'report.json').read_text())
    frozen_raw = (args.model / 'frozen-course.json').read_bytes()
    frozen = json.loads(frozen_raw)
    checkpoint = args.model / 'best-validation.npz'
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    model, _, tokenizer, _, meta = load_checkpoint(checkpoint)
    if digest != report['checkpointHash'] or hashlib.sha256(frozen_raw).hexdigest() != meta['provenance']['corpusHash'] or meta['provenance']['scope'] != SCOPE:
        raise ValueError('Model or course changed.')
    events = []
    def record(kind, **details):
        events.append({'sequence': len(events) + 1, 'event': kind, **details})
        (args.output / 'journal.json').write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'event': kind, **{k: v for k, v in details.items() if k in ('passed', 'exitCode', 'count')}}), flush=True)
    def run(name, command, cwd):
        result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=90)
        (args.output / (name + '.log')).write_text(result.stdout, encoding='utf-8')
        record(name, exitCode=result.returncode)
        return result.returncode, result.stdout
    def generate(message):
        # No answer/corpus access here. Every inference is reproduced from checkpoint.
        ids = [256] + tokenizer.encode(message)
        if len(ids) > model.config.context_length:
            raise ValueError('Context exceeded.')
        return tokenizer.decode(model.generate(ids, max_tokens=100, temperature=.05, seed=31))
    try:
        context = source_context(args.project, 'formatDate')
        record('source_read', path=context['path'], beforeHash=context['beforeHash'], excerpt=context['excerpt'],
               investigator='deterministic search; teacher supplied symbol and null hypothesis')
        if context['prompt'] not in {row['prompt'] for row in frozen['project']}:
            raise ValueError('Project target differs from the frozen evaluation.')
        generated = generate(context['prompt'])
        record('model_proposal', prompt=context['prompt'], generated=generated, checkpointHash=digest)
        patched, assertion = stage(context, generated)
        proposals = []
        for row in frozen['test'] + frozen['project']:
            output = generate(row['prompt'])
            parts = validate_proposal(parse_request(row['prompt']), output)
            proposals.append({**row, **parts, 'generated': output, 'exact': output == row['answer']})
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            # Source snapshot was archived from tracked files only by the launcher.
            shutil.copytree(args.project, work / 'project', symlinks=False)
            project = work / 'project'
            node_project = project / 'app'
            target = project / context['path']
            if hashlib.sha256(target.read_bytes()).hexdigest() != context['beforeHash']:
                raise ValueError('Snapshot changed during investigation.')
            relative_module = '../src/lib/' + Path(context['path']).name
            test_source = ("import test from 'node:test';\nimport assert from 'node:assert/strict';\n"
                           f"import {{formatDate}} from '{relative_module}';\n"
                           "// Assertion generated by LocalAuthor; test wrapper provided by the tutor.\n"
                           "test('data ausente não vira data de 1969', () => {\n  " + assertion + '\n});\n')
            test_path = node_project / 'tests/local-ai-date-regression.test.mjs'
            test_path.write_text(test_source, encoding='utf-8')
            red_code, red_log = run('project-red', ['node', '--test', 'tests/local-ai-date-regression.test.mjs'], node_project)
            red = red_code != 0 and 'ERR_ASSERTION' in red_log and '# fail 1' in red_log
            target.write_bytes(patched.encode('utf-8'))
            green_code, green_log = run('project-green', ['node', '--test', 'tests/local-ai-date-regression.test.mjs'], node_project)
            regression_code, regression_log = run('project-regression', ['npm', 'test'], node_project)
            # Teacher-owned independent behavior oracle: preserve all previously valid dates,
            # especially timestamp zero, which a truthiness guard would incorrectly reject.
            original = work / 'original.mjs'
            original.write_bytes(context['source'].encode('utf-8'))
            independent = work / 'independent.mjs'
            independent.write_text("import assert from 'node:assert/strict';\n"
                f"import {{formatDate as old}} from {json.dumps(original.as_uri())};\n"
                f"import {{formatDate as fixed}} from {json.dumps(target.as_uri())};\n"
                "for(const value of [null,undefined,'','invalida']) assert.equal(fixed(value),'Data indisponível');\n"
                "for(const value of [0,1,-1,'2026-09-21T12:00:00Z','2000-02-29T00:00:00Z']) assert.equal(fixed(value),old(value));\n"
                "console.log('BEHAVIOR=9');\n", encoding='utf-8')
            independent_code, independent_log = run('project-behavior', ['node', str(independent)], work)
            # Each held-out assertion must fail on the unpatched fixture and pass after repair.
            rows = []
            for row in proposals:
                name, param, fallback = row['name'], row['parameter'], json.dumps(row['fallback'], ensure_ascii=False)
                original_body = f'const date = new Date({param}); if (!Number.isFinite(date.getTime())) return {fallback}; return date.toISOString();'
                rows.append({'name': name, 'parameter': param, 'fallback': row['fallback'], 'guard': row['guard'], 'assertion': row['assertion'], 'original': original_body})
            fixtures = work / 'fixtures.json'
            fixtures.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
            checker = work / 'fixtures.mjs'
            checker.write_text("import assert from 'node:assert/strict';\nimport fs from 'node:fs';\n"
                "const rows=JSON.parse(fs.readFileSync(process.argv[2],'utf8')); let red=0,green=0,mutations=0;\n"
                "for(const r of rows){\n"
                "const run=(guard)=>Function('assert',`function ${r.name}(${r.parameter}){${guard}${r.original}};${r.assertion}`)(assert);\n"
                "try{run('');}catch(e){if(e.code==='ERR_ASSERTION')red++;else throw e;}\n"
                "run(r.guard);green++;\n"
                "const fixed=Function(r.parameter,r.guard+r.original);\n"
                "for(const value of [null,undefined,'','invalid'])assert.equal(fixed(value),r.fallback);\n"
                "for(const value of [0,1,-1,'2024-02-29T12:00:00Z'])assert.equal(fixed(value),new Date(value).toISOString());\n"
                "const wrong=Function(r.parameter,`if (!${r.parameter}) return ${JSON.stringify(r.fallback)};`+r.original);\n"
                "try{assert.equal(wrong(0),new Date(0).toISOString());}catch(e){if(e.code==='ERR_ASSERTION')mutations++;else throw e;}\n"
                "}\nassert.equal(red,rows.length);assert.equal(green,rows.length);assert.equal(mutations,rows.length);\n"
                "console.log(JSON.stringify({cases:rows.length,red,green,mutations,behavior:rows.length*8}));\n", encoding='utf-8')
            fixture_code, fixture_log = run('heldout-runtime', ['node', str(checker), str(fixtures)], work)
            import re
            totals = re.search(r'# tests (\d+)\s+# suites \d+\s+# pass (\d+)\s+# fail (\d+)', regression_log)
            regression_total = int(totals[1]) if totals else 0
            regression_passed = int(totals[2]) if totals else 0
            gates = {'heldout': {'total': len(proposals), 'passed': sum(r['exact'] for r in proposals)},
                     'behavior': {'total': len(proposals) * 8 + 9, 'passed': (len(proposals) * 8 if fixture_code == 0 else 0) + (9 if independent_code == 0 and 'BEHAVIOR=9' in independent_log else 0)},
                     'redGreen': {'total': len(proposals) + 1, 'passed': (len(proposals) if fixture_code == 0 else 0) + int(red and green_code == 0 and '# pass 1' in green_log)},
                     'negativeControls': {'total': len(proposals), 'passed': len(proposals) if fixture_code == 0 else 0},
                     'projectRegression': {'total': regression_total, 'passed': regression_passed if regression_code == 0 else 0}}
            success = all(g['total'] > 0 and g['total'] == g['passed'] for g in gates.values()) and regression_total >= 196
            patch = ''.join(difflib.unified_diff(context['source'].splitlines(True), patched.splitlines(True), fromfile='a/' + context['path'], tofile='b/' + context['path']))
            (args.output / 'neural-proposal.diff').write_text(patch, encoding='utf-8')
            (args.output / 'proposed-source.mjs').write_bytes(patched.encode('utf-8'))
            (args.output / 'proposed-test.mjs').write_text(test_source, encoding='utf-8')
            certificate = {'scope': SCOPE, 'state': 'qualified_scoped' if success else 'rejected',
                           'generalProgrammingQualified': False, 'checkpoint': args.model.name + '/best-validation.npz',
                           'checkpointHash': digest, 'gates': gates, 'sourcePath': context['path'], 'beforeHash': context['beforeHash'],
                           'afterHash': hashlib.sha256(patched.encode('utf-8')).hexdigest(),
                           'testHash': hashlib.sha256(test_source.encode('utf-8')).hexdigest(),
                           'generated': generated, 'proposalAuthor': 'local neural model', 'testWrapperAuthor': 'Codex',
                           'investigation': 'teacher hypothesis and symbol; deterministic source search',
                           'application': 'staged only; requires review', 'corpusHash': meta['provenance']['corpusHash']}
            certificate['baselineArchiveHash'] = hashlib.sha256(args.archive.read_bytes()).hexdigest()
            (args.output / 'qualification.json').write_text(json.dumps(certificate, ensure_ascii=False, indent=2), encoding='utf-8')
            record('awaiting_review' if success else 'rejected', passed=success, gates=gates)
            return 0 if success else 1
    except Exception as exc:
        record('blocked', reason=str(exc), exception=type(exc).__name__)
        raise


if __name__ == '__main__':
    raise SystemExit(main())
