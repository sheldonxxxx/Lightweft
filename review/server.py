#!/usr/bin/env python3
"""Local, dependency-free review workspace. Never serves a media directory wholesale."""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import threading
from urllib.parse import parse_qs, unquote, urlsplit
import uuid

SCHEMA_VERSION = 1
MAX_BODY = 8 * 1024 * 1024
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif', '.tif', '.tiff'}
RECIPE_EXTENSIONS = {'.json', '.rrdata', '.xmp', '.cube', '.yaml', '.yml', '.lrtemplate'}
ID_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}$')


class ReviewError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def valid_id(value, label='id'):
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise ReviewError(f'{label} must be a simple identifier of 1–120 characters')
    return value


def object_value(value, label):
    if not isinstance(value, dict):
        raise ReviewError(f'{label} must be an object')
    return value


def string_value(value, label, limit=10000):
    if not isinstance(value, str) or len(value) > limit:
        raise ReviewError(f'{label} must be text of at most {limit} characters')
    return value


def relative_path(value):
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise ReviewError('Media path must be a nonempty relative path')
    if '\\' in value or '\x00' in value or value.startswith('/'):
        raise ReviewError('Media path must be a portable relative path')
    parts = value.split('/')
    if any(p in ('', '.', '..') for p in parts):
        raise ReviewError('Media path cannot traverse directories')
    return value


@contextmanager
def safe_file(root, relative):
    """Open every component using no-follow descriptors, avoiding symlink races."""
    parts = relative_path(relative).split('/')
    descriptors = []
    stream = None
    try:
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        descriptors.append(fd)
        for part in parts[:-1]:
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            descriptors.append(fd)
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            os.close(file_fd)
            raise ReviewError('Only regular files can be served', 404)
        stream = os.fdopen(file_fd, 'rb')
        yield stream
    except OSError as exc:
        raise ReviewError('Referenced file is unavailable or contains a symlink', 404) from exc
    finally:
        if stream is not None:
            stream.close()
        for fd in reversed(descriptors):
            os.close(fd)


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.parent.is_symlink():
        raise ReviewError('Workspace files cannot be symlinks')
    fd, temporary = tempfile.mkstemp(prefix='.review-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class ReviewStore:
    def __init__(self, workspace, media_root):
        self.workspace = Path(workspace).expanduser().resolve()
        self.workspace_id = hashlib.sha256(os.fsencode(str(self.workspace))).hexdigest()[:24]
        self.media_root = Path(media_root).expanduser().resolve(strict=True)
        if not self.media_root.is_dir():
            raise ReviewError('Media root must be a directory')
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.state_path = self.workspace / 'state.json'
        self.lock_path = self.workspace / '.lock'
        self.thread_lock = threading.RLock()
        self.hash_cache = {}
        self.asset_cache = None

    @contextmanager
    def locked(self):
        with self.thread_lock:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'a+b') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock, fcntl.LOCK_UN)

    def read(self):
        if not self.state_path.exists():
            return {'schemaVersion': 1, 'datasets': {}, 'profiles': []}
        with safe_file(self.workspace, 'state.json') as stream:
            data = json.load(stream)
        if data.get('schemaVersion') != 1 or not isinstance(data.get('datasets'), dict):
            raise ReviewError('Unsupported workspace state format', 500)
        return data

    def write(self, data):
        atomic_write(self.state_path, (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())

    def digest(self, path):
        with safe_file(self.media_root, path) as stream:
            info = os.fstat(stream.fileno())
            signature = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            cached = self.hash_cache.get(path)
            if cached and cached[0] == signature:
                return cached[1]
            hasher = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                hasher.update(chunk)
            digest = hasher.hexdigest()
            self.hash_cache[path] = (signature, digest)
            return digest

    def validate_asset(self, value, recipe=False, require_file=True):
        relative_path(value)
        if PurePosixPath(value).suffix.lower() not in (RECIPE_EXTENSIONS if recipe else IMAGE_EXTENSIONS):
            raise ReviewError('Unsupported recipe file extension' if recipe else 'Use a browser image export (JPEG, PNG, WebP, GIF, AVIF or TIFF)')
        if require_file:
            self.digest(value)

    def validate_dataset(self, dataset, require_files=True):
        d = copy.deepcopy(object_value(dataset, 'dataset'))
        if d.get('schemaVersion') != SCHEMA_VERSION:
            raise ReviewError('dataset.schemaVersion must be 1')
        valid_id(d.get('id'), 'dataset.id')
        string_value(d.get('title'), 'dataset.title', 200)
        string_value(d.setdefault('description', ''), 'dataset.description')
        if 'disabled' in d and not isinstance(d['disabled'], bool):
            raise ReviewError('dataset.disabled must be boolean')
        d.setdefault('disabled', False)
        if 'metadata' in d:
            object_value(d['metadata'], 'dataset.metadata')
        cases = d.get('cases')
        if not isinstance(cases, list) or len(cases) > 10000:
            raise ReviewError('dataset.cases must be a list with at most 10000 cases')
        ids = set()
        for case in cases:
            object_value(case, 'case')
            cid = valid_id(case.get('id'), 'case.id')
            if cid in ids:
                raise ReviewError(f'Duplicate case id: {cid}')
            ids.add(cid)
            string_value(case.get('title'), 'case.title', 500)
            if 'defaultView' in case and case['defaultView'] not in ('single', 'side', 'wipe'):
                raise ReviewError('case.defaultView must be single, side, or wipe')
            if 'metadata' in case:
                object_value(case['metadata'], 'case.metadata')
            for key in ('category', 'split', 'format', 'intent'):
                string_value(case.setdefault(key, ''), f'case.{key}')
            limits = case.setdefault('limits', '')
            if not isinstance(limits, (str, list)) or isinstance(limits, list) and any(not isinstance(x, str) for x in limits):
                raise ReviewError('case.limits must be text or a list of text')
            for key in ('aligned',):
                if not isinstance(case.setdefault(key, False), bool):
                    raise ReviewError(f'case.{key} must be boolean')
            variants = case.get('variants')
            if not isinstance(variants, list) or not variants or len(variants) > 200:
                raise ReviewError('Each case needs 1–200 variants')
            vids = set()
            for variant in variants:
                object_value(variant, 'variant')
                vid = valid_id(variant.get('id'), 'variant.id')
                if vid in vids:
                    raise ReviewError(f'Duplicate variant id: {vid}')
                vids.add(vid)
                string_value(variant.get('label'), 'variant.label', 500)
                if 'defaultView' in variant and variant['defaultView'] not in ('single', 'side', 'wipe'):
                    raise ReviewError('variant.defaultView must be single, side, or wipe')
                if 'metadata' in variant:
                    object_value(variant['metadata'], 'variant.metadata')
                if 'native' in variant and not isinstance(variant['native'], bool):
                    raise ReviewError('variant.native must be boolean')
                if variant.get('role') not in ('baseline', 'candidate', 'reference'):
                    raise ReviewError('variant.role must be baseline, candidate or reference')
                self.validate_asset(variant.get('image'), require_file=require_files)
                for key in ('full', 'recipe'):
                    if variant.get(key):
                        self.validate_asset(variant[key], recipe=key == 'recipe', require_file=require_files)
                for key in ('width', 'height'):
                    if key in variant and (type(variant[key]) is not int or variant[key] <= 0):
                        raise ReviewError(f'variant.{key} must be a positive integer')
                if 'recipeFormat' in variant:
                    string_value(variant['recipeFormat'], 'variant.recipeFormat', 100)
                    if not variant['recipeFormat'].strip():
                        raise ReviewError('variant.recipeFormat cannot be blank')
                if 'description' in variant:
                    string_value(variant['description'], 'variant.description')
                variant.pop('assetRevision', None)
                variant.pop('unavailable', None)
            regions = case.setdefault('regions', [])
            if not isinstance(regions, list) or len(regions) > 200:
                raise ReviewError('case.regions must be a list with at most 200 regions')
            rids = set()
            for region in regions:
                object_value(region, 'region')
                rid = valid_id(region.get('id'), 'region.id')
                if rid in rids:
                    raise ReviewError(f'Duplicate region id: {rid}')
                rids.add(rid)
                string_value(region.get('label'), 'region.label', 500)
                if not isinstance(region.setdefault('aligned', False), bool):
                    raise ReviewError('region.aligned must be boolean')
                if 'native' in region and not isinstance(region['native'], bool):
                    raise ReviewError('region.native must be boolean')
                for key in ('x', 'y', 'width', 'height'):
                    number = region.get(key)
                    if type(number) not in (int, float) or not math.isfinite(number) or number < 0 or key in ('width', 'height') and number == 0:
                        raise ReviewError(f'region.{key} must be a finite positive size or nonnegative coordinate')
                images = region.get('images', [])
                if not isinstance(images, list):
                    raise ReviewError('region.images must be a list')
                seen = set()
                for entry in images:
                    object_value(entry, 'region image')
                    if entry.get('variantId') not in vids or entry['variantId'] in seen:
                        raise ReviewError('Region must reference each known variant at most once')
                    seen.add(entry['variantId'])
                    self.validate_asset(entry.get('image'), require_file=require_files)
        return d

    def variant_revision(self, case, variant):
        material = {k: v for k, v in variant.items() if k not in ('assetRevision', 'unavailable', 'defaultView')}
        assets = [variant[k] for k in ('image', 'full', 'recipe') if variant.get(k)]
        region_material = []
        for region in case.get('regions', []):
            entries = [entry for entry in region.get('images', []) if entry['variantId'] == variant['id']]
            if entries:
                region_material.append({**region, 'images': entries})
                assets.extend(entry['image'] for entry in entries)
        missing = []
        hashes = {}
        for path in assets:
            try:
                hashes[path] = self.digest(path)
            except ReviewError:
                hashes[path] = 'unavailable'
                missing.append(path)
        material.update(_assets=hashes, _regions=region_material, _alignment=case.get('aligned', False))
        revision = hashlib.sha256(json.dumps(material, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        return revision, missing

    def refresh(self, record, previous=None):
        changed = False
        before = previous or record
        old_revisions = {(c['id'], v['id']): v.get('assetRevision') for c in before['dataset']['cases'] for v in c['variants']}
        old_feedback = before.get('feedback', {})
        feedback = {}
        for case in record['dataset']['cases']:
            for variant in case['variants']:
                revision, missing = self.variant_revision(case, variant)
                key = (case['id'], variant['id'])
                if revision != old_revisions.get(key):
                    changed = True
                variant['assetRevision'] = revision
                variant['unavailable'] = missing
                item = copy.deepcopy(old_feedback.get(case['id'], {}).get(variant['id']))
                if item:
                    if revision != old_revisions.get(key) or item.get('assetRevision') != revision:
                        item.update(decision='', checks={}, stale=True, assetRevision=revision, updatedAt=now())
                    feedback.setdefault(case['id'], {})[variant['id']] = item
        record['feedback'] = feedback
        return changed

    def envelope(self, record):
        return {**copy.deepcopy(record), 'workspaceId': self.workspace_id}

    def workspace_summary(self):
        with self.locked():
            state = self.read()
            return {'workspaceId': self.workspace_id, 'datasets': [{'id': r['dataset']['id'], 'title': r['dataset']['title'], 'description': r['dataset'].get('description', ''), 'count': len(r['dataset']['cases']), 'version': r['version'], 'disabled': bool(r['dataset'].get('disabled', False))} for r in state['datasets'].values()], 'profiles': [self.public_profile(p) for p in state['profiles']]}

    def get_dataset(self, dataset_id):
        valid_id(dataset_id)
        with self.locked():
            state = self.read()
            record = state['datasets'].get(dataset_id)
            if record is None:
                raise ReviewError('Dataset not found', 404)
            if self.refresh(record):
                record['version'] += 1
                self.write(state)
            return self.envelope(record)

    def put_dataset(self, dataset_id, dataset, version=0):
        d = self.validate_dataset(dataset)
        if d['id'] != valid_id(dataset_id):
            raise ReviewError('Dataset URL and id differ')
        with self.locked():
            state = self.read()
            previous = state['datasets'].get(dataset_id)
            if previous and 'disabled' not in dataset and previous['dataset'].get('disabled'):
                d['disabled'] = True
            if previous and self.refresh(previous):
                previous['version'] += 1
                self.write(state)
            current_version = previous['version'] if previous else 0
            if type(version) is not int or version != current_version:
                raise ReviewError('Workspace changed; reload before saving', 409)
            record = {'dataset': d, 'feedback': {}, 'version': current_version + 1}
            self.refresh(record, previous)
            state['datasets'][dataset_id] = record
            self.write(state)
            return self.envelope(record)

    def set_disabled(self, dataset_id, disabled, version=None):
        valid_id(dataset_id)
        if not isinstance(disabled, bool):
            raise ReviewError('disabled must be boolean')
        with self.locked():
            state = self.read()
            record = state['datasets'].get(dataset_id)
            if record is None:
                raise ReviewError('Dataset not found', 404)
            if self.refresh(record):
                record['version'] += 1
                self.write(state)
            if version is not None and (type(version) is not int or version != record['version']):
                raise ReviewError('Workspace changed; reload before saving', 409)
            dataset = copy.deepcopy(record['dataset'])
            dataset['disabled'] = disabled
            # A display-only flag change must not require renders to be present;
            # refresh() still marks any missing media unavailable.
            validated = self.validate_dataset(dataset, require_files=False)
            next_record = {'dataset': validated, 'feedback': {}, 'version': record['version'] + 1}
            self.refresh(next_record, record)
            state['datasets'][dataset_id] = next_record
            self.write(state)
            return self.envelope(next_record)

    def put_feedback(self, dataset_id, feedback, version):
        object_value(feedback, 'feedback')
        with self.locked():
            state = self.read()
            record = state['datasets'].get(valid_id(dataset_id))
            if record is None:
                raise ReviewError('Dataset not found', 404)
            if self.refresh(record):
                record['version'] += 1
                self.write(state)
            if type(version) is not int or version != record['version']:
                raise ReviewError('Workspace changed; reload before saving feedback', 409)
            cases = {c['id']: {v['id']: v for v in c['variants']} for c in record['dataset']['cases']}
            clean = {}
            for cid, variants in feedback.items():
                if cid not in cases:
                    raise ReviewError('Feedback references an unknown case')
                object_value(variants, 'case feedback')
                clean[cid] = {}
                for vid, raw in variants.items():
                    if vid not in cases[cid]:
                        raise ReviewError('Feedback references an unknown variant')
                    object_value(raw, 'variant feedback')
                    item = copy.deepcopy(raw)
                    if item.get('decision', '') not in ('', 'accepted', 'revise', 'rejected'):
                        raise ReviewError('Unknown review decision')
                    item.setdefault('decision', '')
                    string_value(item.setdefault('note', ''), 'review note')
                    checks = object_value(item.setdefault('checks', {}), 'review checks')
                    if len(checks) > 50 or any(not isinstance(key, str) or not isinstance(val, bool) for key, val in checks.items()):
                        raise ReviewError('Review checks must be named booleans')
                    if 'style' in item:
                        style = object_value(item['style'], 'style preferences')
                        for key, value in style.items():
                            string_value(key, 'style field', 100)
                            string_value(value, 'style preference')
                    if 'rating' in item and (type(item['rating']) not in (int, float) or not math.isfinite(item['rating']) or not 0 <= item['rating'] <= 5):
                        raise ReviewError('Rating must be between 0 and 5')
                    if item['decision'] == 'accepted' and cases[cid][vid].get('unavailable'):
                        raise ReviewError('Unavailable media cannot be accepted')
                    revision = cases[cid][vid]['assetRevision']
                    if item.get('assetRevision') and item['assetRevision'] != revision:
                        raise ReviewError('Feedback belongs to an older variant; reload', 409)
                    old = record['feedback'].get(cid, {}).get(vid)
                    if item != old:
                        item['updatedAt'] = now()
                    item.update(assetRevision=revision, stale=False)
                    clean[cid][vid] = item
            record['feedback'] = clean
            record['version'] += 1
            self.write(state)
            return self.envelope(record)

    @staticmethod
    def public_profile(profile):
        return {key: value for key, value in profile.items() if key != 'recipeFile'}

    def create_profile(self, payload):
        p = copy.deepcopy(object_value(payload, 'profile'))
        string_value(p.get('name'), 'profile.name', 200)
        if not p['name'].strip():
            raise ReviewError('Give the style a name')
        if p.get('kind') not in ('profile', 'preset'):
            raise ReviewError('Style kind must be profile or preset')
        string_value(p.setdefault('description', ''), 'profile.description')
        preferences = object_value(p.setdefault('preferences', {}), 'profile.preferences')
        if len(preferences) > 50:
            raise ReviewError('Use at most 50 qualitative preference fields')
        for key, value in preferences.items():
            string_value(key, 'preference field', 100)
            string_value(value, 'qualitative preference')
        with self.locked():
            state = self.read()
            record = state['datasets'].get(valid_id(p.get('datasetId'), 'datasetId'))
            if record is None:
                raise ReviewError('Dataset not found', 404)
            if self.refresh(record):
                record['version'] += 1
                self.write(state)
            case = next((c for c in record['dataset']['cases'] if c['id'] == p.get('caseId')), None)
            variant = next((v for v in case['variants'] if v['id'] == p.get('variantId')), None) if case else None
            if not variant:
                raise ReviewError('Choose an existing case and variant')
            if variant.get('unavailable'):
                raise ReviewError('Selected variant has unavailable media')
            if p.get('assetRevision') and p['assetRevision'] != variant['assetRevision']:
                raise ReviewError('Selected variant changed; reload before saving style', 409)
            profile = {'id': uuid.uuid4().hex, 'name': p['name'].strip(), 'kind': p['kind'], 'description': p['description'], 'preferences': p['preferences'], 'createdAt': now(), 'provenance': {'workspaceId': self.workspace_id, 'datasetId': p['datasetId'], 'caseId': case['id'], 'variantId': variant['id'], 'variantLabel': variant['label'], 'assetRevision': variant['assetRevision'], 'datasetVersion': record['version'], 'image': variant['image'], 'variantMetadata': variant.get('metadata', {}), 'review': record['feedback'].get(case['id'], {}).get(variant['id'], {})}}
            if p['kind'] == 'preset':
                if not variant.get('recipe') or not variant.get('recipeFormat'):
                    raise ReviewError('Preset requires an actual exported recipe and its recipeFormat')
                self.validate_asset(variant['recipe'], recipe=True)
                with safe_file(self.media_root, variant['recipe']) as stream:
                    recipe = stream.read(MAX_BODY + 1)
                if not recipe or len(recipe) > MAX_BODY:
                    raise ReviewError('Recipe must contain 1 byte to 8 MiB')
                current_revision, missing = self.variant_revision(case, variant)
                if current_revision != variant['assetRevision'] or missing or hashlib.sha256(recipe).hexdigest() != self.digest(variant['recipe']):
                    raise ReviewError('Recipe or selected variant changed during save; reload', 409)
                snapshot = 'presets/' + profile['id'] + PurePosixPath(variant['recipe']).suffix.lower()
                profile.update(recipeFile=snapshot, recipeFormat=variant['recipeFormat'], recipeSha256=hashlib.sha256(recipe).hexdigest())
                profile['provenance']['recipe'] = variant['recipe']
                atomic_write(self.workspace / snapshot, recipe)
            state['profiles'].append(profile)
            self.write(state)
            return self.public_profile(profile)

    def get_profile(self, profile_id):
        valid_id(profile_id)
        with self.locked():
            state = self.read()
            profile = next((p for p in state['profiles'] if p['id'] == profile_id), None)
            if not profile:
                raise ReviewError('Style not found', 404)
            return copy.deepcopy(profile)

    def allowed_assets(self):
        with self.locked():
            try:
                info = self.state_path.lstat()
                signature = (info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            except FileNotFoundError:
                signature = None
            if self.asset_cache is not None and self.asset_cache[0] == signature:
                return self.asset_cache[1]
            state = self.read()
            assets = {}
            for record in state['datasets'].values():
                for case in record['dataset']['cases']:
                    for variant in case['variants']:
                        for key in ('image', 'full', 'recipe'):
                            if variant.get(key):
                                assets[variant[key]] = 'recipe' if key == 'recipe' else 'image'
                    for region in case.get('regions', []):
                        for entry in region.get('images', []):
                            assets[entry['image']] = 'image'
            self.asset_cache = (signature, assets)
            return assets


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, store, web_root=None):
        if address[0] not in ('127.0.0.1', 'localhost', '0.0.0.0'):
            raise ReviewError('Review server must bind to IPv4 loopback or 0.0.0.0')
        self.store = store
        self.web_root = Path(web_root or Path(__file__).parent / 'web').resolve()
        super().__init__(address, ReviewHandler)


class ReviewHandler(BaseHTTPRequestHandler):
    server_version = 'PhotoReview/1'

    def log_message(self, format, *args):
        # Avoid logging private media filenames or notes.
        pass

    def trusted_request(self, mutation=False):
        port = self.server.server_address[1]
        host = self.headers.get('Host', '')
        if self.server.server_address[0] == '0.0.0.0':
            # LAN mode: accept only the address this connection actually arrived
            # on, plus loopback names. A page served from any other hostname (a
            # DNS-rebinding origin, for example) is rejected even when its Origin
            # header matches its forged Host header.
            name, sep, received = host.rpartition(':')
            hostname, port_ok = (name, received == str(port)) if sep else (host, port == 80)
            if hostname.startswith('[') and hostname.endswith(']'):
                hostname = hostname[1:-1]
            allowed = {'127.0.0.1', 'localhost', '::1', self.connection.getsockname()[0].lower()}
            if not port_ok or hostname.lower() not in allowed:
                raise ReviewError('Untrusted Host header', 403)
        else:
            allowed = {f'127.0.0.1:{port}', f'localhost:{port}'}
            if port == 80:
                allowed |= {'127.0.0.1', 'localhost'}
            if host not in allowed:
                raise ReviewError('Untrusted Host header', 403)
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            raise ReviewError('Cross-site requests are not allowed', 403)
        origin = self.headers.get('Origin')
        if origin is not None and origin != 'http://' + host:
            raise ReviewError('Cross-origin requests are not allowed', 403)
        if mutation and self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            raise ReviewError('Mutations require application/json', 415)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        super().end_headers()

    def json_response(self, data, status=200, filename=None):
        body = (json.dumps(data, ensure_ascii=False, allow_nan=False) + '\n').encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def read_json(self):
        if self.headers.get('Transfer-Encoding'):
            raise ReviewError('Transfer encoding is not supported', 400)
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise ReviewError('Invalid content length')
        if length <= 0 or length > MAX_BODY:
            raise ReviewError('JSON request must be 1 byte to 8 MiB', 413)
        try:
            return object_value(json.loads(self.rfile.read(length), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON number'))), 'request')
        except (ValueError, UnicodeError) as exc:
            raise ReviewError('Request must contain valid JSON') from exc

    def send_file(self, root, path, attachment=False):
        with safe_file(root, path) as stream:
            info = os.fstat(stream.fileno())
            etag = f'"{info.st_ino:x}-{info.st_size:x}-{info.st_mtime_ns:x}-{info.st_ctime_ns:x}"'
            if self.headers.get('If-None-Match') == etag:
                self.send_response(304)
                self.send_header('ETag', etag)
                self.send_header('Cache-Control', 'private, no-cache')
                self.end_headers()
                return
            start, end = 0, info.st_size - 1
            partial = False
            range_header = self.headers.get('Range')
            if range_header and self.headers.get('If-Range', etag) == etag:
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', range_header)
                if not match or not any(match.groups()) or not info.st_size:
                    raise ReviewError('Unsupported byte range', 416)
                first, last = match.groups()
                if not first:
                    suffix = int(last)
                    if suffix <= 0:
                        raise ReviewError('Unsatisfiable byte range', 416)
                    start = max(0, info.st_size - suffix)
                else:
                    start = int(first)
                    end = min(int(last), end) if last else end
                if start >= info.st_size or start > end:
                    self.send_response(416)
                    self.send_header('Content-Range', f'bytes */{info.st_size}')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                partial = True
            length = max(0, end - start + 1)
            self.send_response(206 if partial else 200)
            self.send_header('Content-Type', mimetypes.guess_type(path)[0] or 'application/octet-stream')
            self.send_header('Content-Length', str(length))
            self.send_header('ETag', etag)
            self.send_header('Cache-Control', 'private, no-cache')
            self.send_header('Accept-Ranges', 'bytes')
            if partial:
                self.send_header('Content-Range', f'bytes {start}-{end}/{info.st_size}')
            if attachment:
                filename = re.sub(r'[^A-Za-z0-9_.-]', '_', PurePosixPath(path).name)
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            if self.command != 'HEAD':
                stream.seek(start)
                remaining = length
                while remaining:
                    chunk = stream.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)

    def dispatch(self):
        mutation = self.command in ('PUT', 'POST', 'DELETE')
        self.trusted_request(mutation)
        url = urlsplit(self.path)
        path = unquote(url.path)
        store = self.server.store
        if self.command in ('GET', 'HEAD'):
            if path == '/api/workspace':
                return self.json_response(store.workspace_summary())
            if path == '/api/media':
                values = parse_qs(url.query).get('path', [])
                if len(values) != 1:
                    raise ReviewError('Exactly one media path is required')
                asset = relative_path(values[0])
                kind = store.allowed_assets().get(asset)
                if not kind:
                    raise ReviewError('Media is not registered in a dataset', 404)
                return self.send_file(store.media_root, asset, attachment=kind == 'recipe')
            match = re.fullmatch(r'/api/datasets/([^/]+)(/feedback/export)?', path)
            if match:
                record = store.get_dataset(match[1])
                if match[2]:
                    return self.json_response({'schemaVersion': 1, 'workspaceId': record['workspaceId'], 'datasetId': match[1], 'version': record['version'], 'feedback': record['feedback']}, filename=match[1] + '-feedback.json')
                return self.json_response(record)
            match = re.fullmatch(r'/api/profiles/([^/]+)(/export)?', path)
            if match:
                profile = store.get_profile(match[1])
                if match[2] and profile['kind'] == 'preset':
                    return self.send_file(store.workspace, profile['recipeFile'], attachment=True)
                return self.json_response(store.public_profile(profile), filename=profile['id'] + '-profile.json' if match[2] else None)
            if path.startswith('/api/'):
                raise ReviewError('API route not found', 404)
            asset = 'index.html' if path == '/' else path.lstrip('/')
            if not asset or PurePosixPath(asset).suffix.lower() not in {'.html', '.css', '.js', '.svg', '.png', '.ico', '.woff2'}:
                raise ReviewError('Page not found', 404)
            return self.send_file(self.server.web_root, asset)
        if self.command == 'PUT':
            match = re.fullmatch(r'/api/datasets/([^/]+)(/feedback|/disabled)?', path)
            if not match:
                raise ReviewError('API route not found', 404)
            payload = self.read_json()
            if match[2] == '/disabled':
                return self.json_response(store.set_disabled(match[1], payload.get('disabled'), payload.get('version', 0)))
            if match[2]:
                return self.json_response(store.put_feedback(match[1], payload.get('feedback'), payload.get('version')))
            return self.json_response(store.put_dataset(match[1], payload.get('dataset'), payload.get('version', 0)))
        if self.command == 'POST' and path == '/api/profiles':
            return self.json_response(store.create_profile(self.read_json()), status=201)
        raise ReviewError('Method not allowed', 405)

    def handle_request(self):
        self.connection.settimeout(15)
        try:
            self.dispatch()
        except ReviewError as exc:
            self.json_response({'error': str(exc)}, exc.status)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except Exception:
            self.json_response({'error': 'Workspace operation failed; inspect local state and file permissions'}, 500)

    do_GET = handle_request
    do_HEAD = handle_request
    do_PUT = handle_request
    do_POST = handle_request
    do_DELETE = handle_request
    do_OPTIONS = handle_request


def lan_address():
    """Best-effort LAN IP for display only; opens no connections."""
    import socket
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(('10.255.255.255', 1))
        return probe.getsockname()[0]
    except OSError:
        return None
    finally:
        probe.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path('.local/review'))
    parser.add_argument('--media-root', type=Path, required=True, help='Explicit root for manifest-referenced exports')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--bind', default='127.0.0.1', choices=('127.0.0.1', 'localhost', '0.0.0.0'),
                        help='Interface to listen on: loopback (default) or 0.0.0.0 for LAN access')
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('port must be between 0 and 65535')
    try:
        server = ReviewServer((args.bind, args.port), ReviewStore(args.workspace, args.media_root))
    except (ReviewError, OSError) as exc:
        parser.exit(1, f'{exc}\n')
    if args.bind == '0.0.0.0':
        lan = lan_address()
        print(f'Photo Review listening at http://127.0.0.1:{server.server_port}' + (f' and http://{lan}:{server.server_port} (LAN)' if lan else ' on all interfaces (LAN)'), flush=True)
        print('Warning: 0.0.0.0 exposes your review workspace to the local network without authentication; use only on a trusted network.', flush=True)
    else:
        print(f'Photo Review listening at http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
