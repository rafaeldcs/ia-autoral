"""Inference subprocess used by LocalAuthor's browser, not a Codex UI tool."""
import hashlib
import json
import sys
from pathlib import Path

from .investigation_policy import InvestigationPolicy, FIELDS


def decide(observation, checkpoint):
    required = {'url', 'authorizedOrigin', 'status', 'title', 'loading', 'passwordFilled'}
    if set(observation) != required:
        raise ValueError('Invalid trusted browser observation.')
    from urllib.parse import urlsplit
    parsed = urlsplit(observation['url'])
    state = dict.fromkeys(FIELDS, False)
    state.update(in_scope=f'{parsed.scheme}://{parsed.netloc}' == observation['authorizedOrigin'],
                 access=200 <= observation['status'] < 400,
                 loading=observation['loading'], secret=observation['passwordFilled'])
    if type(state['loading']) is not bool or type(state['secret']) is not bool:
        raise ValueError('Browser state must be boolean.')
    prediction = InvestigationPolicy.load(checkpoint).predict(state)
    # The model's proposal and authorization are separate. No replacement of
    # WAIT, SANITIZE, UNKNOWN or another proposal with an unconditional capture.
    authorized = (prediction == 'RECORD' and state['in_scope'] and state['access']
                  and not state['loading'] and not state['secret'])
    return {'modelAction': prediction, 'tool': 'browser.screenshot' if authorized else None,
            'authorized': authorized, 'state': state,
            'checkpointHash': hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest(),
            'observationHash': hashlib.sha256(json.dumps(observation, sort_keys=True).encode()).hexdigest(),
            'decisionBy': 'LocalAuthor own investigation neural policy',
            'stateExtractionBy': 'trusted browser adapter; not neural visual understanding'}


def main():
    observation = json.loads(sys.stdin.read(10000))
    print(json.dumps(decide(observation, sys.argv[1])))


if __name__ == '__main__':
    main()
