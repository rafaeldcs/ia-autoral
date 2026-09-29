"""Use a qualified, bounded agent on a Git snapshot; output is a review proposal."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src')]
from localauthor.investigation_agent import Investigation, NeuralPolicy, SCOPE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--repair-model', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not Path('/.dockerenv').is_file():
        raise RuntimeError('Reviewed sandbox required; no host fallback.')
    cert = json.loads((args.model / 'qualification.json').read_text())
    if cert.get('scope') != SCOPE or cert.get('state') != 'qualified_scoped' or cert.get('generalProgrammingQualified') is not False:
        raise ValueError('Investigation model has not passed qualification.')
    for name in ('fresh', 'regression'):
        score = cert.get('gates', {}).get(name, {})
        if score.get('passed') != score.get('total') or score.get('total', 0) < 28:
            raise ValueError('Required gate missing or failed.')
    if hashlib.sha256((args.repair_model / 'best-validation.npz').read_bytes()).hexdigest() != cert['repairCheckpointHash']:
        raise ValueError('Code generator differs from the evaluated version.')
    request = json.loads(args.request.read_text(encoding='utf-8-sig'))
    if set(request) != {'report'}:
        raise ValueError('Only a symptom report is accepted: no answer path/symbol.')
    policy = NeuralPolicy(args.model / 'best-validation.npz', cert['checkpointHash'])
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project = root / 'project'
        project.mkdir()
        with tarfile.open(args.archive) as archive:
            members = archive.getmembers()
            if len(members) > 5000 or sum(m.size for m in members) > 100_000_000 or any(not (m.isfile() or m.isdir()) for m in members):
                raise ValueError('Unsafe source archive.')
            archive.extractall(project, filter='data')
        home = root / 'home'
        (home / 'exports').mkdir(parents=True)
        destination = home / 'models' / args.repair_model.name
        destination.mkdir(parents=True)
        for name in ('best-validation.npz', 'best-validation.npz.sha256'):
            shutil.copyfile(args.repair_model / name, destination / name)
        shutil.copyfile(args.repair_model / 'qualification.json', home / 'exports/date-repair-qualification.json')
        agent = Investigation(project, args.output, home, policy)
        result = agent.execute(request['report'])
        agent.record('provenance', policyHash=cert['checkpointHash'], repairHash=cert['repairCheckpointHash'], archiveHash=hashlib.sha256(args.archive.read_bytes()).hexdigest())
        print(json.dumps(result, ensure_ascii=False), flush=True)
        # A request for help is a valid outcome, but is not a successful repair.
        return 0 if result['state'] in ('awaiting_review', 'not_reproduced') else 2


if __name__ == '__main__':
    raise SystemExit(main())
