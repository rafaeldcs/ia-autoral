#!/usr/bin/env python3
"""Teste numérico reprodutível, sem corpus de programação e sem exportar pesos."""
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
from localauthor.nn.transformer import Transformer, ModelConfig
from localauthor.nn.optimizer import AdamW
from localauthor.nn.tensor import no_grad

if __name__ == '__main__':
    model = Transformer(ModelConfig(context_length=8, dimension=8, heads=2, layers=1, seed=42))
    optimizer = AdamW(model.parameters, lr=0.01)
    # Integers for a toy cyclic pattern: this is NOT an example of programming teaching data.
    inputs = np.array([[7, 11, 19, 7, 11, 19, 7, 11]], dtype=np.int64)
    targets = np.array([[11, 19, 7, 11, 19, 7, 11, 19]], dtype=np.int64)
    with no_grad():
        initial = float(model.loss(inputs, targets).data)
    start = time.monotonic()
    for _ in range(90):
        loss = model.loss(inputs, targets)
        loss.backward()
        optimizer.step()
    elapsed = time.monotonic() - start
    with no_grad():
        final = float(model.loss(inputs, targets).data)
        predictions = model.forward(inputs).data.argmax(axis=-1)
    report = {
        'at': datetime.now(timezone.utc).isoformat(),
        'kind': 'controlled_numerical_overfit', 'seed': 42,
        'device': 'CPU', 'dtype': 'float64', 'numpy': np.__version__,
        'parameter_count': model.parameter_count,
        'steps': 90, 'tokens_processed': 720,
        'initial_loss': initial, 'final_loss': final,
        'training_positions_correct': int((predictions == targets).sum()),
        'training_positions_total': int(targets.size),
        'elapsed_seconds': elapsed,
        'successful_numeric_smoke': final < initial * 0.2,
        'programming_qualified': False,
        'weights_exported': False,
        'limitations': ['Mesmo padrão usado para ajuste e medição: overfit deliberado, não generalização.',
                       'Nenhum desafio de C# foi resolvido por este experimento.',
                       'Medição no container, não no notebook ou RTX 2060 do usuário.']
    }
    path = ROOT / 'reports' / 'neural-smoke.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(path.read_text(encoding='utf-8'))
    sys.exit(0 if report['successful_numeric_smoke'] else 1)
