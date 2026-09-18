"""Bounded authoral specialists for the live browser; never a general agent."""
import json
import sys
from .investigation_policy import InvestigationPolicy, FIELDS
from .investigation_text import InvestigationText
from .site_reader import SiteReader


def reason(observation, policy, controls_model, screen_model):
    state = dict.fromkeys(FIELDS, False)
    state.update(in_scope=True, access=observation['accessible'], loading=observation['loading'])
    capture_action = policy.predict(state)
    controls = []
    for control in observation['controls']:
        prediction = controls_model.predict(control['name'])
        controls.append({**control, 'hypothesis': prediction['label'], 'score': prediction['score']})
    candidates = [c for c in controls if c['safe'] and not c['visited'] and c['hypothesis'] == 'navigation'][:2]
    state['recorded'] = True
    for i, candidate in enumerate(candidates, 1):
        state['link'+str(i)] = state['read'+str(i)] = True
    action = policy.predict(state)
    target = candidates[int(action[-1])-1]['id'] if action in ('OPEN_1', 'OPEN_2') and len(candidates) >= int(action[-1]) else None
    interpretation = screen_model.predict(observation['title'], observation['headings'])
    return {'captureAction': capture_action, 'captureAllowed': capture_action == 'RECORD' and state['access'] and not state['loading'],
            'action': action, 'target': target, 'controls': controls, 'interpretation': interpretation,
            'origin': 'own_neural_specialists', 'generalAgent': False}


if __name__ == '__main__':
    observation = json.loads(sys.stdin.read(100000))
    print(json.dumps(reason(observation, InvestigationPolicy.load('/input/policy.npz'),
                           InvestigationText.load('/input/control.npz', 'control'),
                           SiteReader.load('/input/screen.npz', 'screen'))))
