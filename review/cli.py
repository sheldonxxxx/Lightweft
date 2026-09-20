#!/usr/bin/env python3
"""Register existing exports and exchange review feedback without a browser."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

if __package__:
    from .server import ReviewError, ReviewStore
    from .import_legacy import load_legacy
else:
    from server import ReviewError, ReviewStore
    from import_legacy import load_legacy


def load_dataset(source, root, dataset_id, title, path_maps):
    if source.is_file() and source.suffix.lower() not in {'.html', '.htm'}:
        data = json.loads(source.read_text(encoding='utf-8'))
        if isinstance(data, dict) and data.get('schemaVersion') == 1:
            dataset = copy.deepcopy(data)
            dataset['id'] = dataset_id
            if title:
                dataset['title'] = title
            return dataset
    return load_legacy(source, root, dataset_id, title, path_maps)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    commands = {}
    for name in ('import', 'list', 'show', 'feedback-export', 'feedback-import', 'disable', 'enable'):
        command = sub.add_parser(name)
        command.add_argument('--workspace', type=Path, default=Path('.local/review'))
        command.add_argument('--media-root', type=Path, required=True)
        commands[name] = command
    imported = commands['import']
    imported.add_argument('source', type=Path)
    imported.add_argument('--id', required=True, dest='dataset_id')
    imported.add_argument('--title')
    imported.add_argument('--path-map', action='append', default=[], metavar='OLD=NEW')
    for name in ('show', 'feedback-export', 'feedback-import', 'disable', 'enable'):
        commands[name].add_argument('dataset_id')
    commands['feedback-export'].add_argument('--output', type=Path)
    commands['feedback-import'].add_argument('source', type=Path)
    commands['feedback-import'].add_argument('--version', type=int, required=True, help='Current destination dataset version; stale versions are rejected')
    args = parser.parse_args(argv)
    try:
        store = ReviewStore(args.workspace, args.media_root)
        if args.command == 'import':
            maps = []
            for value in args.path_map:
                if '=' not in value or not all(value.split('=', 1)):
                    raise ValueError('--path-map must be OLD_PREFIX=NEW_PREFIX')
                maps.append(tuple(value.split('=', 1)))
            dataset = load_dataset(args.source, store.media_root, args.dataset_id, args.title, maps)
            try:
                version = store.get_dataset(args.dataset_id)['version']
            except ReviewError as exc:
                if exc.status != 404:
                    raise
                version = 0
            result = store.put_dataset(args.dataset_id, dataset, version)
            print(json.dumps({'id': args.dataset_id, 'title': dataset['title'], 'count': len(dataset['cases']), 'version': result['version']}, ensure_ascii=False))
        elif args.command == 'list':
            print(json.dumps(store.workspace_summary(), ensure_ascii=False, indent=2))
        elif args.command == 'show':
            print(json.dumps(store.get_dataset(args.dataset_id), ensure_ascii=False, indent=2))
        elif args.command == 'feedback-export':
            record = store.get_dataset(args.dataset_id)
            payload = json.dumps({'schemaVersion': 1, 'workspaceId': record['workspaceId'], 'datasetId': args.dataset_id, 'version': record['version'], 'feedback': record['feedback']}, ensure_ascii=False, indent=2) + '\n'
            if args.output:
                args.output.write_text(payload, encoding='utf-8')
            else:
                print(payload, end='')
        elif args.command == 'feedback-import':
            data = json.loads(args.source.read_text(encoding='utf-8'))
            if data.get('schemaVersion') != 1 or data.get('datasetId') != args.dataset_id:
                raise ValueError('Feedback export must have matching datasetId and schemaVersion 1')
            result = store.put_feedback(args.dataset_id, data.get('feedback'), args.version)
            print(json.dumps({'id': args.dataset_id, 'version': result['version']}))
        elif args.command in ('disable', 'enable'):
            result = store.set_disabled(args.dataset_id, args.command == 'disable')
            print(json.dumps({'id': args.dataset_id, 'disabled': result['dataset'].get('disabled', False), 'version': result['version']}))
    except (ReviewError, ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
