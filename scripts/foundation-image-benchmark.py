#!/usr/bin/env python3
"""Real, offline GPU benchmark worker. Invoke inside an inspected sandbox only.

Use identical frozen cases and a checksum-bound model for before/after runs.
Human approval is deliberately left pending, regardless of successful inference.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import re
import sys
import threading
import time


def validate_cases(document):
    if (not isinstance(document, dict) or set(document) != {'schema', 'frozen', 'cases'}
            or type(document['schema']) is not int or document['schema'] != 1 or document['frozen'] is not True
            or not isinstance(document['cases'], list) or not 1 <= len(document['cases']) <= 20):
        raise ValueError('Use 1–20 frozen benchmark cases, schema 1.')
    seen = set()
    for row in document['cases']:
        if (not isinstance(row, dict) or set(row) != {'id', 'prompt', 'options'}
                or not isinstance(row['id'], str) or not re.fullmatch(r'[a-z0-9_-]{1,80}', row['id'])
                or row['id'] in seen or not isinstance(row['prompt'], str)
                or not row['prompt'].strip() or len(row['prompt']) > 2000 or not isinstance(row['options'], dict)):
            raise ValueError('Invalid, duplicate or incomplete benchmark case.')
        seen.add(row['id'])
    return document['cases']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--source-revision', required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-f0-9]{40}', args.source_revision):
        parser.error('Supply the full source commit verified by the external controller.')
    if args.output.exists():
        parser.error('Use a new output directory; never overwrite evidence.')
    sys.path.insert(0, str(args.source_root / 'src'))
    from localauthor.errors import PolicyError
    from localauthor.foundation.isolation import require_isolated_process
    from localauthor.foundation.models import ModelSpec, digest, read_object, write_new
    from localauthor.foundation.service import FoundationService
    from localauthor.foundation.visual import ImageOptions
    isolation = require_isolated_process()
    rows = validate_cases(read_object(args.cases))
    for row in rows:
        ImageOptions.parse(row['options'])
    args.output.mkdir(parents=True)
    report = {'schema': 1, 'source_revision': args.source_revision, 'isolation': isolation,
              'cases_sha256': digest(args.cases), 'model_manifest_sha256': digest(args.manifest),
              'model_inference': True, 'test_doubles': False, 'training': False,
              'production_activated': False, 'human_quality_approval': 'pending',
              'results': [], 'checks': {}, 'success': False}
    report['source_files'] = {name: digest(args.source_root / name) for name in
        ['src/localauthor/foundation/runtime.py', 'src/localauthor/foundation/visual.py',
         'src/localauthor/foundation/service.py', 'src/localauthor/foundation/models.py']}
    service = None
    try:
        import torch
        if not torch.cuda.is_available() or (torch.arange(4, device='cuda') * 2).sum().item() != 12:
            raise PolicyError('CUDA compute unavailable; no host/CPU fallback.')
        report['runtime'] = {name: importlib.metadata.version(name) for name in
                             ['torch', 'diffusers', 'transformers', 'safetensors', 'Pillow']}
        report['runtime'].update(gpu=torch.cuda.get_device_name(0), cuda=torch.version.cuda)
        home = args.output / 'home'
        manifest = home / 'foundation/image-model.json'
        write_new(manifest, read_object(args.manifest))
        spec = ModelSpec.load(manifest, 'image')
        if spec.device != 'cuda' or spec.dtype != 'float16':
            raise PolicyError('Benchmark requires an explicit CUDA float16 manifest.')
        service = FoundationService(home)
        started = time.perf_counter(); _, engine = service._engine('image'); torch.cuda.synchronize()
        report['load_seconds_including_hash_check'] = time.perf_counter() - started
        if engine.pipeline.unet.device.type != 'cuda' or engine.pipeline.safety_checker is None:
            raise PolicyError('Real CUDA pipeline and active safety checker are required.')
        report['model'] = spec.provenance()
        started = time.perf_counter()
        engine.generate('A yellow ceramic vase on a white table, studio photograph',
                        options={'width': 512, 'height': 512, 'steps': 20, 'seed': 31})
        torch.cuda.synchronize()
        report['warmup_seconds_excluded_from_comparison'] = time.perf_counter() - started
        for row in rows:
            item = {'id': row['id'], 'prompt': row['prompt'], 'options': row['options'], 'delivered': False}
            try:
                torch.cuda.reset_peak_memory_stats(); torch.cuda.synchronize(); started = time.perf_counter()
                result = service.create_image('shopair-benchmark', row['prompt'], options=row['options'])
                torch.cuda.synchronize(); item['generation_seconds'] = time.perf_counter() - started
                item['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
                item['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
                recovered = service.image('shopair-benchmark', result['artifact_id'])
                if recovered['sha256'] != result['artifact_sha256']:
                    raise PolicyError('Stored/retrieved PNG hash mismatch.')
                original = home / 'foundation/artifacts/shopair-benchmark' / (result['artifact_id'] + '.png')
                if digest(original) != recovered['sha256']:
                    raise PolicyError('Original PNG hash mismatch.')
                image_path = args.output / (row['id'] + '.png')
                image_path.write_bytes(original.read_bytes())
                item.update(delivered=True, sha256=digest(image_path), file=image_path.name,
                            width=result['width'], height=result['height'], artifact=result)
            except Exception as exc:
                item.update(error_type=type(exc).__name__, error=str(exc))
            report['results'].append(item)
            write_new(args.output / (row['id'] + '.json'), item)
            print(json.dumps({'case': row['id'], 'delivered': item['delivered'],
                              'seconds': item.get('generation_seconds'), 'error': item.get('error')}), flush=True)
        event = threading.Event(); event.set()
        try:
            service.create_image('shopair-benchmark', 'A white cup', event)
        except PolicyError:
            report['checks']['pre_cancel_rejected'] = True
        try:
            engine.generate('ceramic cup ' * 100)
        except PolicyError:
            report['checks']['oversize_prompt_rejected'] = True
        spec.verify()
        report['checks']['weights_hashes_still_valid'] = True
        report['success'] = all(row['delivered'] for row in report['results']) and all(
            report['checks'].get(name) is True for name in
            ['pre_cancel_rejected', 'oversize_prompt_rejected', 'weights_hashes_still_valid'])
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
    finally:
        try:
            if service is not None:
                service.close()
        except Exception as exc:
            report.update(success=False, close_error=str(exc))
        write_new(args.output / 'report.json', report)
    print(json.dumps({'success': report['success'], 'human_quality_approval': 'pending'}), flush=True)
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
