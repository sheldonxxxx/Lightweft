#!/usr/bin/env python3
"""Validate the gallery and copy its explicit runtime files to _site."""
import json
from pathlib import Path
import shutil

from check_public_repo import ROOT, validate_blob
from showcase_media import SEGMENT, is_asset_path, validate_jpeg

RUNTIME = ('index.html', 'styles.css', 'app.js', 'data.json')
SHARE_IMAGE = 'assets/share-card.jpg'


def read_regular(root, relative):
    path = root / relative
    if any(part.is_symlink() for part in (path, *path.parents) if part != root.parent):
        raise ValueError(f'symlink is not permitted: {relative}')
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'missing or invalid file: {relative}')
    return path.read_bytes()


def image_path(value):
    if not isinstance(value, str) or not is_asset_path('showcase/' + value):
        raise ValueError('image src must be a generic relative JPEG path under assets/')
    return value


def checked_fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise ValueError('missing or unsupported gallery fields')


def text_fields(value, fields):
    if any(not isinstance(value[field], str) or not value[field].strip() for field in fields):
        raise ValueError('gallery text fields must be nonempty strings')


def asset_references(data):
    checked_fields(data, ('schemaVersion', 'groups'))
    if data['schemaVersion'] != 1 or not isinstance(data['groups'], list) or not data['groups']:
        raise ValueError('gallery requires schemaVersion 1 and at least one group')
    assets, declared_widths, groups = {SHARE_IMAGE}, {}, set()
    for group in data['groups']:
        checked_fields(group, ('id', 'number', 'title', 'subtitle', 'photos'))
        text_fields(group, ('id', 'number', 'title', 'subtitle'))
        if not SEGMENT.fullmatch(group['id']) or group['id'] in groups:
            raise ValueError('group ids must be unique generic names')
        groups.add(group['id'])
        if not isinstance(group['photos'], list) or not group['photos']:
            raise ValueError('each group needs photos')
        photos = set()
        for photo in group['photos']:
            checked_fields(photo, ('id', 'title', 'description', 'alt', 'width', 'height', 'before', 'after'))
            text_fields(photo, ('id', 'title', 'description', 'alt'))
            if any(type(photo[field]) is not int or photo[field] <= 0 for field in ('width', 'height')):
                raise ValueError('photo width and height must be positive integers')
            if not SEGMENT.fullmatch(photo['id']) or photo['id'] in photos:
                raise ValueError('photo ids must be unique within each group')
            photos.add(photo['id'])
            widths_by_side = []
            for side in ('before', 'after'):
                variant = photo[side]
                checked_fields(variant, ('src', 'srcset'))
                assets.add(image_path(variant['src']))
                if not isinstance(variant['srcset'], list) or not variant['srcset']:
                    raise ValueError('each image needs a nonempty srcset')
                widths = set()
                for item in variant['srcset']:
                    checked_fields(item, ('src', 'width'))
                    source = image_path(item['src'])
                    width = item['width']
                    if type(width) is not int or width <= 0 or width in widths:
                        raise ValueError('srcset widths must be unique positive integers')
                    if source in declared_widths and declared_widths[source] != width:
                        raise ValueError('conflicting width for an image asset')
                    widths.add(width)
                    assets.add(source)
                    declared_widths[source] = width
                widths_by_side.append(widths)
            if widths_by_side[0] != widths_by_side[1]:
                raise ValueError('before and after must provide matching responsive widths')
    return assets, declared_widths


def build(root=ROOT):
    root = Path(root).resolve()
    payloads = {}
    for name in RUNTIME:
        blob = read_regular(root, 'showcase/' + name)
        validate_blob('showcase/' + name, blob)
        payloads[name] = blob
    data = json.loads(payloads['data.json'])
    assets, widths = asset_references(data)
    dimensions = {}
    for name in sorted(assets):
        blob = read_regular(root, 'showcase/' + name)
        validate_blob('showcase/' + name, blob)
        dimensions[name] = validate_jpeg(blob)
        if name in widths and dimensions[name][0] != widths[name]:
            raise ValueError(f'declared srcset width does not match JPEG: {name}')
        payloads[name] = blob
    for group in data['groups']:
        for photo in group['photos']:
            if dimensions[photo['before']['src']] != dimensions[photo['after']['src']]:
                raise ValueError('before and after primary images must have matching dimensions')
            before_sizes = {item['width']: dimensions[item['src']] for item in photo['before']['srcset']}
            after_sizes = {item['width']: dimensions[item['src']] for item in photo['after']['srcset']}
            if before_sizes != after_sizes:
                raise ValueError('before and after responsive images must have matching dimensions')
            for side in ('before', 'after'):
                sources = {photo[side]['src']} | {item['src'] for item in photo[side]['srcset']}
                for source in sources:
                    width, height = dimensions[source]
                    if abs(height - width * photo['height'] / photo['width']) > 1:
                        raise ValueError(f'image aspect ratio does not match the photo dimensions: {source}')
    destination = root / '_site'
    if destination.is_symlink():
        raise ValueError('build output must not be a symlink')
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir()
    for name, blob in payloads.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    print(f'Built {len(data["groups"])} groups and {len(assets)} JPEG assets in _site.')
    return destination


if __name__ == '__main__':
    build()
