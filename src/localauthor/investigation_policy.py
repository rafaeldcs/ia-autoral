"""Small learned policy over explicit observations; never controls a browser.

This specialist is separate from the text Transformer. State extraction,
authorization and execution are not learned and must not be credited to it.
"""
from pathlib import Path
import json
import numpy as np
from .nn.tensor import Tensor, gelu, no_grad

FIELDS = ('in_scope', 'secret', 'page_instruction', 'access', 'loading', 'error',
          'stale', 'recorded', 'link1', 'read1', 'seen1', 'link2', 'read2', 'seen2',
          'unknown_question', 'dialog', 'table', 'mobile')
ACTIONS = ('STOP_SCOPE', 'SANITIZE', 'IGNORE_INSTRUCTION', 'PENDING_ACCESS',
           'WAIT', 'RECORD_ERROR', 'REFRESH', 'RECORD', 'OPEN_1', 'OPEN_2',
           'UNKNOWN', 'REPORT_LIMITS')


def vector(observation):
    if not isinstance(observation, dict) or set(observation) != set(FIELDS):
        raise ValueError('Observation must contain the exact documented state fields.')
    if any(type(observation[k]) is not bool for k in FIELDS):
        raise ValueError('State fields must be booleans, never text, credentials or inferred actions.')
    return np.array([float(observation[k]) for k in FIELDS])


class InvestigationPolicy:
    def __init__(self, seed=1926):
        rng = np.random.default_rng(seed)
        self.parameters = {
            'w1': Tensor(rng.normal(0, .15, (len(FIELDS), 64)), requires_grad=True),
            'b1': Tensor(np.zeros(64), requires_grad=True),
            'w2': Tensor(rng.normal(0, .1, (64, len(ACTIONS))), requires_grad=True),
            'b2': Tensor(np.zeros(len(ACTIONS)), requires_grad=True),
        }

    def forward(self, x):
        p = self.parameters
        return gelu(Tensor(x) @ p['w1'] + p['b1']) @ p['w2'] + p['b2']

    def predict(self, observation):
        with no_grad():
            logits = self.forward(vector(observation)[None, :]).data[0]
        if not np.isfinite(logits).all():
            raise ValueError('Nonfinite prediction; no action proposed.')
        # Decoding a learned class is not an authorization or a safety filter.
        return ACTIONS[int(np.argmax(logits))]

    def save(self, path):
        metadata = json.dumps({'schema': 1, 'fields': FIELDS, 'actions': ACTIONS})
        np.savez_compressed(path, metadata=np.array(metadata),
                            **{k: p.data for k, p in self.parameters.items()})

    @classmethod
    def load(cls, path):
        if Path(path).stat().st_size > 1_000_000:
            raise ValueError('Policy checkpoint exceeds limit.')
        result = cls()
        with np.load(path, allow_pickle=False) as data:
            if set(data.files) != set(result.parameters) | {'metadata'}:
                raise ValueError('Invalid policy checkpoint fields.')
            meta = json.loads(str(data['metadata']))
            if meta != {'schema': 1, 'fields': list(FIELDS), 'actions': list(ACTIONS)}:
                raise ValueError('Incompatible policy schema.')
            for key, parameter in result.parameters.items():
                value = data[key]
                if value.shape != parameter.data.shape or not np.isfinite(value).all():
                    raise ValueError('Invalid policy weights.')
                parameter.data[:] = value
        return result
