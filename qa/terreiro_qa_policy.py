"""Original small QA scheduler. It learns priorities, not code or browser perception."""
import json
from pathlib import Path
import numpy as np
from localauthor.nn.tensor import Tensor, gelu, no_grad

STAGES = ('sandbox', 'build', 'unit', 'authentication', 'permissions', 'dues',
          'treasury', 'stock', 'administration', 'communication', 'documents', 'browser', 'evidence')
ACTIONS = ('STOP_SCOPE', 'INVESTIGATE_FAILURE', *(f'CHECK_{x.upper()}' for x in STAGES), 'REPORT')
FIELDS = ('authorized', 'failure', *STAGES, *(f'context_{i}' for i in range(8)))


class TerreiroQaPolicy:
    def __init__(self):
        rng = np.random.default_rng(290926)
        self.parameters = {
            'w1': Tensor(rng.normal(0, .12, (len(FIELDS), 64)), requires_grad=True),
            'b1': Tensor(np.zeros(64), requires_grad=True),
            'w2': Tensor(rng.normal(0, .12, (64, len(ACTIONS))), requires_grad=True),
            'b2': Tensor(np.zeros(len(ACTIONS)), requires_grad=True)}

    def forward(self, x):
        p = self.parameters
        return gelu(Tensor(x) @ p['w1'] + p['b1']) @ p['w2'] + p['b2']

    def predict(self, state):
        if set(state) != set(FIELDS) or any(type(v) is not bool for v in state.values()):
            raise ValueError('Exact boolean QA observations required')
        with no_grad():
            scores = self.forward(np.array([[float(state[k]) for k in FIELDS]])).data[0]
        if not np.isfinite(scores).all():
            raise ValueError('Nonfinite model prediction')
        return ACTIONS[int(np.argmax(scores))]

    def save(self, path):
        np.savez_compressed(path, metadata=np.array(json.dumps({'fields': FIELDS, 'actions': ACTIONS})),
                            **{k: v.data for k, v in self.parameters.items()})

    @classmethod
    def load(cls, path):
        if Path(path).stat().st_size > 1_000_000:
            raise ValueError('Oversized checkpoint')
        model = cls()
        with np.load(path, allow_pickle=False) as data:
            if json.loads(str(data['metadata'])) != {'fields': list(FIELDS), 'actions': list(ACTIONS)}:
                raise ValueError('Wrong checkpoint schema')
            for key, value in model.parameters.items():
                if data[key].shape != value.data.shape or not np.isfinite(data[key]).all():
                    raise ValueError('Invalid weights')
                value.data[:] = data[key]
        return model


def teacher(state):
    """Demonstration/assessment oracle; never called by policy inference."""
    if not state['authorized']:
        return 'STOP_SCOPE'
    if state['failure']:
        return 'INVESTIGATE_FAILURE'
    return next((f'CHECK_{s.upper()}' for s in STAGES if not state[s]), 'REPORT')


def curriculum():
    rng = np.random.default_rng(714)
    splits = {name: [] for name in ('train', 'validation', 'test')}
    seen = set()
    for action in ACTIONS:
        for split, count in [('train', 64), ('validation', 16), ('test', 16)]:
            while sum(row['action'] == action for row in splits[split]) < count:
                state = {k: bool(rng.integers(2)) for k in FIELDS}
                state['authorized'] = action != 'STOP_SCOPE'
                if action != 'STOP_SCOPE':
                    state['failure'] = action == 'INVESTIGATE_FAILURE'
                if action.startswith('CHECK_') or action == 'REPORT':
                    stop = STAGES.index(action[6:].lower()) if action != 'REPORT' else len(STAGES)
                    for i, stage in enumerate(STAGES):
                        if i <= stop:
                            state[stage] = i < stop
                key = ''.join(str(int(state[k])) for k in FIELDS)
                if key in seen or teacher(state) != action:
                    continue
                seen.add(key)
                splits[split].append({'id': key, 'state': state, 'action': action})
    return splits


def reinforcement_curriculum(excluded=()):
    """Fresh synthetic priority examples, including revoked scope after success.

    Dense completion states were underrepresented in the first course. Mix
    sparse, dense and random histories; keep complete state IDs disjoint.
    Observed receipt challenges and the original held-out set are reserved.
    """
    rng = np.random.default_rng(300926)
    splits = {name: [] for name in ('train', 'validation', 'test')}
    seen = set(excluded)
    for action in ACTIONS:
        for split, count in [('train', 128), ('validation', 32), ('test', 32)]:
            accepted = 0
            while accepted < count:
                state = {k: bool(rng.integers(2)) for k in FIELDS}
                pattern = int(rng.integers(4))
                if pattern < 2:
                    for stage in STAGES:
                        state[stage] = bool(pattern)
                    # Keep a mixture of exact extremes and near-extremes.
                    if rng.integers(2):
                        state[STAGES[int(rng.integers(len(STAGES)))]] = not bool(pattern)
                state['authorized'] = action != 'STOP_SCOPE'
                if action != 'STOP_SCOPE':
                    state['failure'] = action == 'INVESTIGATE_FAILURE'
                if action.startswith('CHECK_') or action == 'REPORT':
                    stop = STAGES.index(action[6:].lower()) if action != 'REPORT' else len(STAGES)
                    for i, stage in enumerate(STAGES):
                        if i <= stop:
                            state[stage] = i < stop
                key = ''.join(str(int(state[k])) for k in FIELDS)
                if key in seen or teacher(state) != action:
                    continue
                seen.add(key)
                splits[split].append({'id': key, 'state': state, 'action': action})
                accepted += 1
    return splits
