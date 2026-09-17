#!/usr/bin/env python3
"""Import authorized training lessons and train through the running local platform.

Validation/test records are never imported into searchable memory. This command
does not execute generated code or qualify the model as a programmer.
"""
import argparse
import http.client
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from localauthor.config import Settings
from localauthor.dataset import validate_dataset
from localauthor.util import write_json, utcnow


class LocalClient:
    def __init__(self, settings):
        self.port = settings.port
        self._token = settings.token

    def request(self, path, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=20)
        try:
            connection.request('GET' if body is None else 'POST', path,
                               json.dumps(body).encode('utf-8') if body is not None else None,
                               {'Authorization': 'Bearer ' + self._token, 'Content-Type': 'application/json'})
            response = connection.getresponse()
            data = json.loads(response.read())
            if response.status != 200:
                raise RuntimeError(f'Local API HTTP {response.status}: {data.get("error", "request failed")}')
            return data
        finally:
            connection.close()


def import_lessons(client, dataset, project_root, name):
    projects = client.request('/api/projects')
    project = next((p for p in projects if Path(p['root']).resolve() == project_root), None)
    if project is None:
        project = client.request('/api/projects', {'name': name, 'root': str(project_root)})
    imported = []
    for record in dataset['splits']['train']:
        title = f'{dataset["dataset_id"]} / {record["path"]}'
        entry = client.request('/api/import', {'scope': project['id'], 'title': title, 'content': record['text']})
        imported.append({'path': record['path'], 'source_id': entry['id'], 'sha256': record['sha256']})
    return project, imported


def main(args):
    if not args.approved_dataset:
        raise ValueError('Use --approved-dataset only after authorizing the corpus and reviewing its provenance.')
    settings = Settings.load(args.home)
    manifest = args.manifest.resolve(strict=True)
    project_root = args.project_root.resolve(strict=True)
    if not project_root.is_dir():
        raise ValueError('The course project must be an existing directory.')
    if manifest.is_relative_to(ROOT) or args.report.resolve().is_relative_to(ROOT):
        raise ValueError('Keep corpus, model and teaching reports outside the source repository.')
    if project_root.is_relative_to(manifest.parent) or manifest.parent.is_relative_to(project_root):
        raise ValueError('The searchable project must be separate from the corpus and evaluation data.')
    relative_manifest = manifest.relative_to((settings.home / 'corpus').resolve()).as_posix()
    dataset = validate_dataset(manifest)
    config = json.loads(args.config.read_text(encoding='utf-8')) if args.config else None
    if config:
        from localauthor.nn.transformer import ModelConfig
        ModelConfig(**config).validate()
    client = LocalClient(settings)
    client.request('/api/health')
    project, imported = import_lessons(client, dataset, project_root, args.name)
    report = {'at': utcnow(), 'dataset_id': dataset['dataset_id'], 'manifest_sha256': dataset['manifest_hash'],
              'project_id': project['id'], 'project_root': str(project_root), 'imported_train_lessons': imported,
              'validation_imported': False, 'test_imported': False, 'programming_qualified': False,
              'training_success': False}
    write_json(args.report, report)
    payload = {'manifest': relative_manifest, 'approved_dataset': True, 'steps': args.steps,
               'batch_size': args.batch_size, 'tokenizer': args.tokenizer}
    if config:
        payload['config'] = config
    job = client.request('/api/jobs/train', payload)
    report['job_id'] = job['id']
    write_json(args.report, report)
    print(json.dumps({'imported': len(imported), 'project_id': project['id'], 'job_id': job['id']}, ensure_ascii=False), flush=True)
    deadline = time.monotonic() + args.timeout
    next_update = 0
    try:
        while job['state'] in {'queued', 'running'}:
            if time.monotonic() >= deadline:
                client.request(f'/api/jobs/{job["id"]}/cancel', {})
                report['cancel_requested'] = True
                raise TimeoutError('Training exceeded the requested time budget; cooperative cancellation requested.')
            if time.monotonic() >= next_update:
                print('Local training: ' + job['state'], flush=True)
                next_update = time.monotonic() + 20
            time.sleep(1)
            job = client.request('/api/jobs/' + job['id'])
        report['training_job'] = job
        report['training_success'] = job['state'] == 'completed'
        if job['state'] != 'completed':
            raise RuntimeError(job.get('error') or f'Training ended: {job["state"]}')
        report['checkpoint'] = str(settings.home / 'models' / job['result']['model_directory'] / 'latest.npz')
    finally:
        report['finished_at'] = utcnow()
        write_json(args.report, report)
    print(json.dumps({'training_success': True, 'report': str(args.report), 'programming_qualified': False}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--home', type=Path)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--approved-dataset', action='store_true')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--steps', type=int, default=500)
    parser.add_argument('--batch-size', type=int, default=2)
    parser.add_argument('--tokenizer', choices=['byte', 'bpe'], default='bpe')
    parser.add_argument('--timeout', type=int, default=900)
    try:
        raise SystemExit(main(parser.parse_args()))
    except (ValueError, RuntimeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
