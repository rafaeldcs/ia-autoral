"""Authored text specialist; annotations are hypotheses, never click authority.

Character/word hashing is a fixed encoding, not pretrained embeddings. Only
the two small classifiers learn. No browser, network or activation side effects.
"""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import numpy as np

from .nn.tensor import Tensor, gelu, no_grad

LABELS = {
    'status': ('ready', 'loading', 'error', 'access_denied', 'unknown'),
    'control': ('navigation', 'mutation', 'authentication', 'ambiguous'),
}
FEATURES = 2048
MAX_TEXT = 600


def encode(text):
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
        raise ValueError('Supply a nonempty visible text segment of at most 600 characters.')
    plain = unicodedata.normalize('NFKC', text).casefold()
    words = re.findall(r'\w+|[^\w\s]', plain)
    features = ['w:' + w for w in words]
    features += ['b:' + a + ' ' + b for a, b in zip(words, words[1:])]
    for word in words:
        padded = '^' + word + '$'
        features += ['c:' + padded[i:i+n] for n in (3, 4, 5)
                     for i in range(len(padded)-n+1)]
    result = np.zeros(FEATURES)
    for feature in features:
        digest = hashlib.blake2b(feature.encode('utf-8'), digest_size=8).digest()
        result[int.from_bytes(digest, 'little') % FEATURES] += 1
    return result / max(float(np.linalg.norm(result)), 1)


class InvestigationText:
    def __init__(self, kind, seed=71926):
        if kind not in LABELS:
            raise ValueError('Unsupported text specialist.')
        self.kind = kind
        rng = np.random.default_rng(seed)
        self.parameters = {
            'w1': Tensor(rng.normal(0, .05, (FEATURES, 32)), requires_grad=True),
            'b1': Tensor(np.zeros(32), requires_grad=True),
            'w2': Tensor(rng.normal(0, .1, (32, len(LABELS[kind]))), requires_grad=True),
            'b2': Tensor(np.zeros(len(LABELS[kind])), requires_grad=True),
        }

    def forward(self, x):
        p = self.parameters
        return gelu(Tensor(x) @ p['w1'] + p['b1']) @ p['w2'] + p['b2']

    def predict(self, text):
        with no_grad():
            logits = self.forward(encode(text)[None, :]).data[0]
        if not np.isfinite(logits).all():
            raise ValueError('Invalid model output; no hypothesis available.')
        scores = np.exp(logits - logits.max())
        scores /= scores.sum()
        index = int(np.argmax(scores))
        return {'label': LABELS[self.kind][index], 'score': float(scores[index]),
                'calibrated': False, 'authorizesAction': False}

    def save(self, path):
        meta = {'schema': 1, 'kind': self.kind, 'features': FEATURES,
                'encoding': 'nfkc-casefold-blake2b-word-bigram-char345-v1'}
        np.savez_compressed(path, metadata=np.array(json.dumps(meta)),
                            **{k: v.data for k, v in self.parameters.items()})

    @classmethod
    def load(cls, path, kind):
        result = cls(kind)
        if Path(path).stat().st_size > 2_000_000:
            raise ValueError('Text checkpoint exceeds limit.')
        with np.load(path, allow_pickle=False) as data:
            if set(data.files) != set(result.parameters) | {'metadata'}:
                raise ValueError('Invalid checkpoint fields.')
            if json.loads(str(data['metadata'])) != {
                'schema': 1, 'kind': kind, 'features': FEATURES,
                'encoding': 'nfkc-casefold-blake2b-word-bigram-char345-v1'}:
                raise ValueError('Incompatible text checkpoint.')
            for key, parameter in result.parameters.items():
                weights = data[key]
                if weights.shape != parameter.data.shape or not np.isfinite(weights).all():
                    raise ValueError('Invalid text weights.')
                parameter.data[:] = weights
        return result


def segments(text):
    """Lossless line/size segmentation. Splits may lose cross-segment meaning."""
    if not isinstance(text, str) or len(text) > 12000:
        raise ValueError('Page text exceeds the explicit observation budget.')
    offset = 0
    for line in text.splitlines(keepends=True):
        for start in range(0, len(line), MAX_TEXT):
            part = line[start:start + MAX_TEXT]
            yield {'start': offset + start, 'end': offset + start + len(part), 'text': part}
        offset += len(line)


def annotate_observation(observation, status_model, control_model):
    """Consumes a validated BrowserInvestigation observation, does not mutate it.

    Never promotes the predicted 'navigation' label to trusted navigation=True.
    Text is processed in independent segments, not silently truncated to the
    general Transformer's context. Cross-segment reasoning remains unresolved.
    """
    if status_model.kind != 'status' or control_model.kind != 'control':
        raise ValueError('Use the correct specialist for each input.')
    blocks = []
    for block in segments(observation['text']):
        blocks.append({**block, 'hypothesis': status_model.predict(block['text'])
                       if block['text'].strip() else None})
    return {'snapshot': observation['snapshot'], 'blocks': blocks,
            'controls': [{'id': control['id'], 'text': control['name'],
                          'hypothesis': control_model.predict(control['name'])}
                         for control in observation['controls']],
            'authorizesAction': False, 'crossSegmentReasoning': False}
