#!/usr/bin/env python3
"""Verify the consolidated RAW suite, provenance, previews and local catalogue links."""
from collections import Counter, defaultdict
import argparse
import base64
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

def verify(root, require_clean=False):
    root = Path(root).resolve()
    errors = []
    def check(ok, why):
        if not ok:
            errors.append(why)
    manifest = json.loads((root / 'manifest.json').read_text())
    assets = manifest['assets']
    selection = json.loads((root / 'selection.json').read_text())
    check(assets == selection['assets'], 'Built assets differ from deliberate selection')
    check(set(manifest['allowed_input_formats']) == {'CR3', 'DNG'}, 'Unexpected input format policy')
    ids, hashes, originals, previews, immich_ids = set(), set(), set(), set(), set()
    groups, dates = defaultdict(set), defaultdict(set)
    verified_bytes = 0
    for case in assets:
        key = case['id']; original = case['original']
        check(key not in ids, f'Duplicate case ID: {key}'); ids.add(key)
        check(original['sha256'] not in hashes, f'Duplicate source hash: {key}'); hashes.add(original['sha256'])
        path = (root / original['path']).resolve()
        check(path not in originals, f'Duplicate source path: {key}'); originals.add(path)
        check(path.is_relative_to((root.parent / 'originals').resolve()), f'Original outside canonical folder: {key}')
        check(original['format'] in {'CR3', 'DNG'} and path.suffix.upper() == '.' + original['format'], f'JPEG or unsupported input: {key}')
        if not path.is_relative_to((root.parent / 'originals').resolve()):
            continue
        if path.is_file():
            blob = path.read_bytes()
            check(hashlib.sha256(blob).hexdigest() == original['sha256'] == case['source_checksum_sha256'], f'Original SHA-256 mismatch: {key}')
            check(len(blob) == original['byte_size'], f'Original size mismatch: {key}')
            check(blob[4:8] == b'ftyp' if original['format'] == 'CR3' else blob[:4] in [b'II*\x00', b'MM\x00*'], f'Input container signature mismatch: {key}')
            verified_bytes += len(blob)
            if case.get('origin') in {'immich', 'v2'}:
                check(base64.b64encode(hashlib.sha1(blob).digest()).decode() == original['server_sha1_base64'], f'Immich checksum mismatch: {key}')
                check(case['asset_id'] not in immich_ids and bool(case['asset_id']), f'Invalid Immich identity: {key}')
                immich_ids.add(case['asset_id'])
            else:
                check(original.get('server_sha1_base64') is None and case['asset_id'] is None, f'Invented server provenance: {key}')
        else:
            errors.append(f'Missing original: {key}')
        preview = (root / case['preview']['path']).resolve()
        if not preview.is_relative_to((root / 'previews').resolve()):
            errors.append(f'Preview outside previews folder: {key}')
            continue
        check(preview not in previews, f'Duplicate preview path: {key}'); previews.add(preview)
        if preview.is_file():
            blob = preview.read_bytes()
            check(hashlib.sha256(blob).hexdigest() == case['preview']['sha256'], f'Preview SHA-256 mismatch: {key}')
            check(len(blob) == case['preview']['byte_size'], f'Preview size mismatch: {key}')
            check(blob.startswith(b'\xff\xd8\xff') or (blob[:4] == b'RIFF' and blob[8:12] == b'WEBP'), f'Invalid preview: {key}')
        else:
            errors.append(f'Missing preview: {key}')
        check(case['preview']['original_input'] is False, f'Preview used as input: {key}')
        check(case['split'] == 'development' and case['evaluation_status'] == 'exposed_regression', f'Exposed case presented as fresh holdout: {key}')
        groups[case['group_id']].add(case['split'])
        for date in case['capture_date_candidates']:
            dates[date].add(case['group_id'])
    for case in assets:
        check(set(case.get('related_case_ids', [])) <= ids, f'Dangling related case: {case["id"]}')
    check(all(len(v) == 1 for v in dates.values()), 'Same capture date crosses groups')
    check(all(len(v) == 1 for v in groups.values()), 'Capture group crosses splits')
    check(manifest['verification']['original_count'] == len(assets), 'Original count mismatch')
    check(manifest['verification']['original_bytes'] == verified_bytes, 'Total bytes mismatch')
    check(manifest['split_policy']['holdout_count'] == 0, 'Fresh holdout count must be zero')
    class Links(HTMLParser):
        def __init__(self):
            super().__init__(); self.links = []; self.cards = 0
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'article' and attrs.get('class') == 'card': self.cards += 1
            for field in ['href', 'src']:
                if attrs.get(field): self.links.append(attrs[field])
    parser = Links(); parser.feed((root / 'catalogue.html').read_text())
    check(parser.cards == len(assets), 'Catalogue card count mismatch')
    local_links = 0
    for target in parser.links:
        url = urlsplit(unescape(target))
        if url.scheme or url.netloc or not url.path: continue
        path = root / unquote(url.path)
        check(path.is_file(), f'Broken catalogue link: {target}'); local_links += 1
    if require_clean:
        files = {p.resolve() for p in ((root.parent / 'originals').resolve()).rglob('*') if p.is_file()}
        check(files == originals, 'Orphan or missing canonical originals')
        check({p.resolve() for p in (root / 'previews').rglob('*') if p.is_file()} == previews, 'Orphan or missing active previews')
    return {'valid': not errors, 'errors': errors,
            'summary': {'cases': len(assets), 'formats': dict(Counter(a['original']['format'] for a in assets)),
                        'split_counts': dict(Counter(a['split'] for a in assets)), 'bytes': verified_bytes,
                        'preview_count': len(previews), 'capture_groups': len(groups), 'local_links': local_links,
                        'canonical_folder_clean': require_clean},
            'limits': 'Verifies local input identity and prior exposure, not a new edit evaluation or remote album membership.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite-dir', type=Path, required=True)
    parser.add_argument('--require-clean', action='store_true')
    args = parser.parse_args()
    result = verify(args.suite_dir, require_clean=args.require_clean)
    (args.suite_dir / 'validation-report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['valid'] else 1)
