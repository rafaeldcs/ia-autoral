"""Compare frozen, human-reviewed coarse purposes to unedited local predictions."""
import argparse
import hashlib
import json
from pathlib import Path


def assess(response, expected):
    if response['inputHash'] != expected['observationsHash']:
        raise ValueError('The evidence differs from the frozen review.')
    identifiers = [s['id'] for s in response['screens']]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError('Duplicate screen identifiers could conceal a failed prediction.')
    observed = {s['id']: s for s in response['screens'] if s['state'] == 'observed'}
    if set(observed) != set(expected['expected']):
        raise ValueError('Every observed screen must be graded; no hidden omissions.')
    cases = [{'id': key, 'name': observed[key]['name'], 'expected': label,
              'actual': (actual := observed[key]['prediction']['label']),
              'passed': actual == label} for key, label in expected['expected'].items()]
    withheld = [s for s in response['screens'] if s['state'] != 'observed']
    return {'cases': cases, 'passed': sum(c['passed'] for c in cases), 'total': len(cases),
            'sitePurposeCorrect': response['purpose']['label'] == expected['expectedSite'],
            'unobservedNotInvented': all(s['prediction'] is None for s in withheld),
            'unobservedCount': len(withheld), 'allSitesQualified': False,
            'gradeLevel': expected['gradeLevel']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--response', required=True, type=Path)
    parser.add_argument('--expected', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = assess(json.loads(args.response.read_text(encoding='utf-8')),
                    json.loads(args.expected.read_text(encoding='utf-8')))
    result['responseHash'] = hashlib.sha256(args.response.read_bytes()).hexdigest()
    result['expectedHash'] = hashlib.sha256(args.expected.read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}))
    print(json.dumps({'failures': [c for c in result['cases'] if not c['passed']]}, ensure_ascii=True))
    raise SystemExit(0 if result['passed'] == result['total'] and result['sitePurposeCorrect'] and result['unobservedNotInvented'] else 1)


if __name__ == '__main__':
    main()
