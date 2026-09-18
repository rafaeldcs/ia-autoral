"""Annotate a previously sanitized visible-page observation with local weights.

This is an offline experimental tool. It never logs in, opens a browser or
executes the predicted actions. Observation files must not contain secrets.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from localauthor.browser_investigation import BrowserInvestigation
from localauthor.investigation_text import InvestigationText, annotate_observation
from localauthor.util import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--observation', required=True, type=Path)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    for path in (args.report, args.observation):
        if path.stat().st_size > 1_000_000:
            raise ValueError('Input exceeds the inspection budget.')
    report = json.loads(args.report.read_text(encoding='utf-8'))
    if report.get('labApproved') is not True:
        raise ValueError('Use a checkpoint approved for the bounded synthetic course.')
    models = {}
    for kind in ('status', 'control'):
        checkpoint = report['checkpoints'][kind]
        path = Path(checkpoint['path'])
        if path.stat().st_size > 2_000_000:
            raise ValueError('Checkpoint exceeds budget.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != checkpoint['sha256']:
            raise ValueError('Checkpoint hash changed after evaluation.')
        models[kind] = InvestigationText.load(path, kind)
    session = BrowserInvestigation(args.origin)
    observation = session.observe(json.loads(args.observation.read_text(encoding='utf-8')))
    result = annotate_observation(observation, models['status'], models['control'])
    result['limitations'] = ['Experimental phrase annotations, not a complete investigation.',
                            'Scores are uncalibrated; arbitrary text may be misclassified.',
                            'No browser action is authorized or executed.',
                            'No reasoning across independent text segments.']
    write_json(args.output, result)
    print(json.dumps({'output': str(args.output), 'blocks': len(result['blocks']),
                      'controls': len(result['controls']), 'actionsExecuted': 0}))


if __name__ == '__main__':
    main()
