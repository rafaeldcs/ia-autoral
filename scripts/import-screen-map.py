"""Import reviewed browser observations into project memory; never imports credentials."""
import argparse
import http.client
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screens', type=Path, required=True)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--reviewed', action='store_true', help='Confirm review of collected labels and notes; excludes credentials and record values.')
    args = parser.parse_args()
    if not args.reviewed:
        raise ValueError('Review observations before importing; use --reviewed after that review.')
    home = Path(os.environ['LOCALAPPDATA']) / 'LocalAuthor'
    token = (home / 'api.token').read_text().strip()
    rows = json.loads(args.screens.read_text(encoding='utf-8'))
    if not isinstance(rows, list) or not 1 <= len(rows) <= 500:
        raise ValueError('Expected one to 500 reviewed screens')
    root = args.project_root.resolve(strict=True)
    def request(path, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', 8765, timeout=30)
        try:
            connection.request('GET' if body is None else 'POST', path,
                               json.dumps(body).encode() if body is not None else None,
                               {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
            response = connection.getresponse()
            result = json.loads(response.read())
            if response.status != 200:
                raise RuntimeError('Import rejected: ' + str(response.status))
            return result
        finally:connection.close()
    projects = request('/api/projects')
    project = next((p for p in projects if Path(p['root']).resolve() == root), None)
    if project is None:
        project = request('/api/projects', {'name': args.name, 'root': str(root)})
    run = request('/api/investigations', {'project_id': project['id'], 'name': args.name, 'origin': args.origin})
    output = {'project_id': project['id'], 'investigation_id': run['id'], 'state': 'importing', 'imported': 0}
    report = args.screens.parent / ('import-' + run['id'] + '.json')
    report.write_text(json.dumps(output, indent=2), encoding='utf-8')
    for row in rows:
        run = request('/api/investigations/observe', {'project_id': project['id'], 'investigation_id': run['id'], 'screen': row})
        output['imported'] += 1
        report.write_text(json.dumps(output, indent=2), encoding='utf-8')
    output.update(state='completed', coverage=run['coverage'], weights_updated=False)
    report.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps(output))


if __name__ == '__main__':
    main()
