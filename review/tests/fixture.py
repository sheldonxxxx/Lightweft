#!/usr/bin/env python3
"""Serve a disposable browser-QA workspace using generated images, not photographs."""
import argparse
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from review.server import ReviewServer, ReviewStore


def png(width, height, warm=False):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            stripe = 35 if (x // 20 + y // 20) % 2 else 0
            row.extend((min(255, 65 + x * 120 // width + (25 if warm else 0)), 80 + y * 90 // height, 85 + stripe))
        rows.append(bytes(row))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b'')


def fixture(root):
    for name, w, h, warm in [('base', 400, 300, False), ('edit', 400, 300, True), ('edit-full', 800, 600, True), ('base-full', 800, 600, False), ('crop-base', 128, 128, False), ('crop-edit', 128, 128, True), ('portrait', 300, 450, True)]:
        (root / (name + '.png')).write_bytes(png(w, h, warm))
    (root / 'recipe.json').write_text('{"schema":"qa-recipe","exposure":0.25}\n')
    return {'schemaVersion': 1, 'id': 'fixture', 'title': 'Review studio · generated QA', 'cases': [
        {'id': 'landscape', 'title': 'Light and texture', 'category': 'landscape', 'aligned': True, 'defaultView': 'side', 'intent': 'Compare light and texture in this generated test image.', 'variants': [
            {'id': 'base', 'label': 'Foundation', 'role': 'baseline', 'image': 'base.png', 'full': 'base-full.png'},
            {'id': 'warm', 'label': 'Warm direction', 'role': 'candidate', 'image': 'edit.png', 'full': 'edit-full.png', 'recipe': 'recipe.json', 'recipeFormat': 'qa-recipe'},
            {'id': 'earlier', 'label': 'Earlier reference', 'role': 'reference', 'image': 'base.png', 'defaultView': 'single'}],
         'regions': [{'id': 'texture', 'label': 'Fine texture', 'x': 40, 'y': 60, 'width': 128, 'height': 128, 'aligned': True, 'native': True, 'images': [{'variantId': 'base', 'image': 'crop-base.png'}, {'variantId': 'warm', 'image': 'crop-edit.png'}]}]},
        {'id': 'portrait', 'title': 'A different frame', 'category': 'portrait', 'aligned': False, 'defaultView': 'wipe', 'variants': [
            {'id': 'base', 'label': 'Original frame', 'role': 'baseline', 'image': 'base.png'},
            {'id': 'crop', 'label': 'Changed frame', 'role': 'candidate', 'image': 'portrait.png'}]}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    with TemporaryDirectory(prefix='lightweft-review-qa-') as tmp:
        root = Path(tmp)
        store = ReviewStore(root / 'workspace', root)
        dataset = fixture(root)
        store.put_dataset('fixture', dataset)
        store.put_dataset('second', {**dataset, 'id': 'second', 'title': 'Second QA collection'})
        server = ReviewServer(('127.0.0.1', args.port), store)
        print(f'Disposable browser QA: http://127.0.0.1:{server.server_port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
