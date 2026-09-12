#!/usr/bin/env python3
"""Rebuild the current RAW suite from deliberate selection.json; never download inputs."""
from collections import Counter
import argparse
import copy
import hashlib
import json
from pathlib import Path

def build(root):
    root = Path(root).resolve()
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    manifest = copy.deepcopy(json.loads((root / 'selection.json').read_text()))
    assets = manifest['assets']
    require(bool(assets), 'Select at least one RAW input')
    require(set(manifest['allowed_input_formats']) == {'CR3', 'DNG'}, 'Expected CR3/DNG input policy')
    ids, hashes, paths = set(), set(), set()
    for case in assets:
        require(case['split'] == 'development' and case['evaluation_status'] == 'exposed_regression', 'This workflow accepts exposed regression cases only')
        original = case['original']
        path = (root / original['path']).resolve()
        require(path.is_relative_to((root.parent / 'originals').resolve()), f'Outside originals: {path}')
        require(original['format'] in manifest['allowed_input_formats'], f'Ineligible format: {case["id"]}')
        require(path.suffix.upper().lstrip('.') == original['format'], f'Format mismatch: {case["id"]}')
        require(path.stat().st_size == original['byte_size'], f'Source size mismatch: {case["id"]}')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == original['sha256'] == case['source_checksum_sha256'], f'Source hash mismatch: {case["id"]}')
        require(case['id'] not in ids and original['sha256'] not in hashes and path not in paths, f'Duplicate: {case["id"]}')
        ids.add(case['id']); hashes.add(original['sha256']); paths.add(path)
        preview = (root / case['preview']['path']).resolve()
        require(preview.is_relative_to((root / 'previews').resolve()), 'Preview outside previews folder')
        require(preview.stat().st_size == case['preview']['byte_size'], 'Preview size mismatch')
        require(hashlib.sha256(preview.read_bytes()).hexdigest() == case['preview']['sha256'], f'Preview hash mismatch: {case["id"]}')
        # Preserve the deliberate selection exactly in the built manifest.
    splits = dict(Counter(a['split'] for a in assets))
    manifest['split_policy'].update(development_count=splits.get('development', 0), holdout_count=splits.get('holdout', 0))
    manifest['verification'] = {
        'original_inputs_ready': True, 'original_count': len(assets), 'preview_count': len(assets),
        'original_bytes': sum(a['original']['byte_size'] for a in assets),
        'formats': dict(Counter(a['original']['format'] for a in assets)),
        'source_integrity_method': 'Original SHA-256, size, format and preview SHA-256 recomputed against selection records.',
        'prior_render_and_edit_exposure': True, 'fresh_holdout_count': 0,
        'limits': 'Input integrity and historical exposure only; this rebuild does not run or approve new edits.'}
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(f'Built {len(assets)} RAW cases: {manifest["verification"]["formats"]}; {splits}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite-dir', type=Path, required=True)
    args = parser.parse_args()
    build(args.suite_dir)
