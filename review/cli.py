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
    for name in ('import', 'list', 'show', 'feedback-export', 'feedback-import', 'disable', 'enable', 'archive', 'unarchive', 'relocate', 'add-variant', 'add-variants'):
        command = sub.add_parser(name)
        command.add_argument('--workspace', type=Path, default=Path('.local/review'))
        command.add_argument('--media-root', type=Path, required=True)
        commands[name] = command
    imported = commands['import']
    imported.add_argument('source', type=Path)
    imported.add_argument('--id', required=True, dest='dataset_id')
    imported.add_argument('--title')
    imported.add_argument('--path-map', action='append', default=[], metavar='OLD=NEW')
    for name in ('show', 'feedback-export', 'feedback-import', 'disable', 'enable', 'archive', 'unarchive', 'add-variant', 'add-variants'):
        commands[name].add_argument('dataset_id')
    commands['archive'].add_argument('--to', dest='archived_to', help='Where the media went, for example the archive file name')
    relocated = commands['relocate']
    relocated.add_argument('--map', action='append', default=[], required=True, metavar='OLD=NEW', help='Folder that moved, relative to the media root; repeatable')
    relocated.add_argument('--dry-run', action='store_true', help='Count the paths that would change without writing')
    relocated.add_argument('--allow-missing', action='store_true', help='Write even when some relocated media is missing')
    single = commands['add-variant']
    single.add_argument('case_id')
    single.add_argument('--id', required=True, dest='variant_id', help='New variant id; an existing id is refused')
    single.add_argument('--image', required=True, help='Review image path relative to the media root')
    single.add_argument('--full', help='Full export path relative to the media root')
    single.add_argument('--label')
    single.add_argument('--role', default='candidate', choices=('baseline', 'candidate', 'reference'))
    single.add_argument('--description')
    single.add_argument('--parent', help='Variant id this render was derived from (metadata.parentVariantId)')
    single.add_argument('--recipe')
    single.add_argument('--recipe-format')
    single.add_argument('--metadata', help='JSON object merged into the variant metadata')
    single.add_argument('--select', action='store_true', help='Open this variant as the selected candidate')
    commands['add-variants'].add_argument('source', type=Path, help='JSON file: {"additions": [{"caseId", "variant", "select"?}, ...]}')
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
        elif args.command in ('add-variant', 'add-variants'):
            if args.command == 'add-variant':
                variant = {'id': args.variant_id, 'label': args.label or args.variant_id, 'role': args.role, 'image': args.image}
                for key, value in (('full', args.full), ('description', args.description), ('recipe', args.recipe), ('recipeFormat', args.recipe_format)):
                    if value:
                        variant[key] = value
                metadata = json.loads(args.metadata) if args.metadata else {}
                if args.parent:
                    metadata['parentVariantId'] = args.parent
                if metadata:
                    variant['metadata'] = metadata
                additions = [{'caseId': args.case_id, 'variant': variant, 'select': args.select}]
            else:
                data = json.loads(args.source.read_text(encoding='utf-8'))
                additions = data.get('additions') if isinstance(data, dict) else data
            result = store.add_variants(args.dataset_id, additions)
            print(json.dumps({'id': args.dataset_id, 'added': len(additions), 'version': result['version']}))
        elif args.command == 'archive':
            result = store.set_archived(args.dataset_id, True, args.archived_to)
            print(json.dumps({'id': args.dataset_id, 'archived': True, 'disabled': True, 'version': result['version']}))
        elif args.command == 'unarchive':
            result = store.set_archived(args.dataset_id, False)
            print(json.dumps({'id': args.dataset_id, 'archived': False, 'disabled': result['dataset'].get('disabled', False), 'version': result['version']}))
        elif args.command == 'relocate':
            maps = []
            for value in args.map:
                if '=' not in value or not all(value.split('=', 1)):
                    raise ValueError('--map must be OLD=NEW')
                maps.append(tuple(value.split('=', 1)))
            print(json.dumps(store.relocate(maps, dry_run=args.dry_run, allow_missing=args.allow_missing)))
        elif args.command in ('disable', 'enable'):
            result = store.set_disabled(args.dataset_id, args.command == 'disable')
            print(json.dumps({'id': args.dataset_id, 'disabled': result['dataset'].get('disabled', False), 'version': result['version']}))
    except (ReviewError, ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
