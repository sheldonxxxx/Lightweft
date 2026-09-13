"""Publication boundary tests use generated solid-colour JPEGs, never personal photos."""
import contextlib
import copy
from io import BytesIO, StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageCms

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_showcase
import check_public_repo


def jpeg(size=(24, 16), **options):
    output = BytesIO()
    Image.new('RGB', size, '#172031').save(output, 'JPEG', **options)
    return output.getvalue()


class ShowcaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.site = self.root / 'showcase'
        (self.site / 'assets/nightscapes').mkdir(parents=True)
        for name in build_showcase.RUNTIME:
            (self.site / name).write_text('Static public source\n')
        self.before = 'assets/nightscapes/ridge-before.jpg'
        self.after = 'assets/nightscapes/ridge-after.jpg'
        for name in (self.before, self.after, build_showcase.SHARE_IMAGE):
            (self.site / name).write_bytes(jpeg())
        photo = {'id': 'ridge', 'title': 'Ridge', 'description': 'A starry ridge.', 'alt': 'Stars over a ridge.',
                 'width': 2400, 'height': 1600}
        for side, source in (('before', self.before), ('after', self.after)):
            photo[side] = {'src': source, 'srcset': [{'src': source, 'width': 24}]}
        self.data = {'schemaVersion': 1, 'groups': [{'id': 'nightscapes', 'number': '01', 'title': 'Nightscapes',
                     'subtitle': 'A first group.', 'photos': [photo]}]}
        self.save()

    def save(self):
        (self.site / 'data.json').write_text(json.dumps(self.data))

    def build(self):
        with contextlib.redirect_stdout(StringIO()):
            return build_showcase.build(self.root)

    def test_build_copies_only_runtime_and_referenced_assets(self):
        (self.site / 'README.md').write_text('Contributor guide')
        (self.site / 'private.dng').write_bytes(b'private source')
        (self.site / 'assets/nightscapes/unused.jpg').write_bytes(jpeg())
        output = self.build()
        expected = set(build_showcase.RUNTIME) | {self.before, self.after, build_showcase.SHARE_IMAGE}
        self.assertEqual({path.relative_to(output).as_posix() for path in output.rglob('*') if path.is_file()}, expected)
        (output / 'stale.txt').write_text('old build')
        self.build()
        self.assertFalse((output / 'stale.txt').exists())

    def test_additional_group_uses_the_same_build_contract(self):
        second = copy.deepcopy(self.data['groups'][0])
        second.update(id='reflections', number='02', title='Reflections')
        self.data['groups'].append(second)
        self.save()
        self.assertTrue((self.build() / 'data.json').is_file())

    def test_side_labels_and_descriptions_are_optional_and_preserved(self):
        before = self.data['groups'][0]['photos'][0]['before']
        after = self.data['groups'][0]['photos'][0]['after']
        for labels in ({}, {'label': 'Corrected base'}, {'description': 'Photographic corrections'},
                       {'label': 'Corrected base', 'description': 'Photographic corrections'}):
            with self.subTest(labels=labels):
                before.pop('label', None)
                before.pop('description', None)
                before.update(labels)
                after.update(label='Quiet Story', description='The same base with the Quiet Story preset')
                self.save()
                published = json.loads((self.build() / 'data.json').read_text())
                self.assertEqual(published, self.data)

    def test_invalid_optional_side_text_fails_without_replacing_output(self):
        output = self.build()
        snapshot = (output / 'data.json').read_bytes()
        photo = self.data['groups'][0]['photos'][0]
        for side in ('before', 'after'):
            for field in ('label', 'description'):
                for value in ('', ' \n\t', None, 42, False, [], {}):
                    with self.subTest(side=side, field=field, value=value):
                        photo[side][field] = value
                        self.save()
                        with self.assertRaisesRegex(ValueError, 'nonempty strings'):
                            self.build()
                        self.assertEqual((output / 'data.json').read_bytes(), snapshot)
                        del photo[side][field]

    def test_optional_side_fields_do_not_allow_unknown_or_misplaced_fields(self):
        photo = self.data['groups'][0]['photos'][0]
        for target, field in ((photo['before'], 'caption'), (photo['after'], 'descripton'),
                              (photo['before']['srcset'][0], 'label'), (photo, 'beforeLabel')):
            with self.subTest(field=field):
                target[field] = 'Corrected base'
                self.save()
                with self.assertRaisesRegex(ValueError, 'unsupported gallery fields'):
                    self.build()
                del target[field]

    def test_portrait_photos_preserve_their_declared_aspect_ratio(self):
        photo = self.data['groups'][0]['photos'][0]
        photo.update(width=2400, height=3000)
        self.save()
        with self.assertRaisesRegex(ValueError, 'aspect ratio'):
            self.build()
        for source in (self.before, self.after):
            (self.site / source).write_bytes(jpeg(size=(24, 30)))
        self.assertTrue((self.build() / self.after).is_file())
        photo['height'] = 0
        self.save()
        with self.assertRaisesRegex(ValueError, 'positive integers'):
            self.build()

    def test_external_traversal_and_private_paths_are_rejected(self):
        for source in ('../secret.jpg', 'assets/../secret.jpg', '/photo.jpg', 'https://example.com/photo.jpg',
                       'assets/nightscapes/capture_123.jpg', 'assets/nightscapes/photo.jpg?key=value',
                       'assets/nightscapes/abcdefab-1234-1234-1234-abcdefabcdef.jpg'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                build_showcase.image_path(source)
        for name in ('photo.jpg', 'showcase/photo.jpg', 'showcase/assets/photo.png', 'showcase/assets/../photo.jpg'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                check_public_repo.validate_blob(name, jpeg())

    def test_decode_size_and_metadata_checks(self):
        srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
        self.assertEqual(check_public_repo.validate_jpeg(jpeg(icc_profile=srgb, progressive=True)), (24, 16))
        exif = Image.Exif()
        exif[0x010e] = 'source information'
        cases = [jpeg(exif=exif), b'not a JPEG', jpeg()[:-8], jpeg() + b'trailing information',
                 b'\xff\xd8' + b'x' * check_public_repo.JPEG_LIMIT]
        for marker, payload in ((0xe1, b'http://ns.adobe.com/xap/1.0/\x00test'), (0xfe, b'comment'),
                                (0xed, b'Photoshop 3.0\x00private')):
            segment = bytes((0xff, marker)) + (len(payload) + 2).to_bytes(2, 'big') + payload
            cases.append(jpeg()[:2] + segment + jpeg()[2:])
        for blob in cases:
            with self.subTest(length=len(blob)), self.assertRaises(ValueError):
                check_public_repo.validate_jpeg(blob)

    def test_missing_asset_or_false_width_fails_before_changing_output(self):
        output = self.build()
        snapshot = (output / 'data.json').read_bytes()
        self.data['groups'][0]['photos'][0]['before']['srcset'][0]['width'] = 23
        self.data['groups'][0]['photos'][0]['after']['srcset'][0]['width'] = 23
        self.save()
        with self.assertRaisesRegex(ValueError, 'width does not match'):
            self.build()
        self.assertEqual((output / 'data.json').read_bytes(), snapshot)
        for side in ('before', 'after'):
            self.data['groups'][0]['photos'][0][side]['srcset'][0]['width'] = 24
        self.save()
        (self.site / self.before).unlink()
        with self.assertRaisesRegex(ValueError, 'missing or invalid'):
            self.build()

    def test_symlink_asset_is_never_copied(self):
        original = self.site / self.before
        original.unlink()
        original.symlink_to(self.site / self.after)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.build()

    def test_git_index_check_reads_staged_bytes_and_rejects_other_binaries(self):
        def git(*arguments):
            subprocess.run(['git', '-C', str(self.root), *arguments], check=True, capture_output=True)
        git('init', '-q')
        path = self.site / self.before
        git('add', 'showcase')
        path.write_bytes(jpeg(comment=b'source notes'))
        with patch.object(check_public_repo, 'ROOT', self.root), contextlib.redirect_stdout(StringIO()), contextlib.redirect_stderr(StringIO()):
            self.assertEqual(check_public_repo.check(), 0)
            self.assertEqual(check_public_repo.check(working_tree=True), 1)
            (self.root / 'original.raw').write_bytes(b'private photo')
            git('add', 'original.raw')
            self.assertEqual(check_public_repo.check(), 1)


if __name__ == '__main__':
    unittest.main()
