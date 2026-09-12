"""Synthetic integrity tests. Test bytes are not decodable RAW photographs."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'workflow'))
sys.path.insert(0, str(REPO / 'scripts'))
import build_catalogue
import build_suite
import check_public_repo
import verify_collection


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'suite'
        (self.root / 'previews').mkdir(parents=True)
        (self.base / 'originals').mkdir()
        self.selection = json.loads((REPO / 'workflow/selection.example.json').read_text())
        self.case = self.selection['assets'][0]
        self.original = self.base / 'originals/example.dng'
        self.preview = self.root / 'previews/example.jpg'
        self.original.write_bytes(b'II*\x00synthetic-original')
        self.preview.write_bytes(b'\xff\xd8\xffsynthetic-preview')
        for path, record in [(self.original, self.case['original']), (self.preview, self.case['preview'])]:
            record['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            record['byte_size'] = path.stat().st_size
        self.case['source_checksum_sha256'] = self.case['original']['sha256']
        self.save()

    def save(self):
        (self.root / 'selection.json').write_text(json.dumps(self.selection))

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            build_suite.build(self.root)
            build_catalogue.build(self.root)

    def test_cli_is_portable_and_preserves_inputs(self):
        other = copy.deepcopy(self.case)
        source = self.base / 'originals/example.cr3'
        source.write_bytes(b'\x00\x00\x00\x18ftypcrx synthetic-original')
        preview = self.root / 'previews/nested/second.jpg'
        preview.parent.mkdir()
        preview.write_bytes(b'\xff\xd8\xffsecond-preview')
        other.update(id='example-02', group_id='capture-group-02')
        other['original'].update(path='../originals/example.cr3', filename=source.name, format='CR3',
                                 byte_size=source.stat().st_size, sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        other['source_checksum_sha256'] = other['original']['sha256']
        other['preview'].update(path='previews/nested/second.jpg', byte_size=preview.stat().st_size,
                                sha256=hashlib.sha256(preview.read_bytes()).hexdigest())
        self.selection['assets'].append(other)
        self.save()
        original_bytes = self.original.read_bytes()
        for script in ['build_suite.py', 'build_catalogue.py', 'verify_collection.py']:
            command = [sys.executable, str(REPO / 'workflow' / script), '--suite-dir', str(self.root)]
            if script == 'verify_collection.py':
                command.append('--require-clean')
            result = subprocess.run(command, cwd=self.base, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((self.root / 'validation-report.json').read_text())
        self.assertTrue(report['valid'])
        self.assertEqual(report['summary']['formats'], {'DNG': 1, 'CR3': 1})
        self.assertEqual(self.original.read_bytes(), original_bytes)

    def test_hash_rejection_survives_optimized_python(self):
        self.original.write_bytes(b'II*\x00synthetic-changed!')
        result = subprocess.run([sys.executable, '-O', str(REPO / 'workflow/build_suite.py'),
                                 '--suite-dir', str(self.root)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('hash mismatch', result.stderr)
        self.assertFalse((self.root / 'manifest.json').exists())

    def test_verifier_detects_changed_source_and_orphan_without_deletion(self):
        self.build()
        self.original.write_bytes(b'II*\x00corrupted-original')
        orphan = self.base / 'originals/stray.dng'
        orphan.write_bytes(b'II*\x00stray')
        report = verify_collection.verify(self.root, require_clean=True)
        self.assertFalse(report['valid'])
        self.assertTrue(any('SHA-256 mismatch' in error for error in report['errors']))
        self.assertIn('Orphan or missing canonical originals', report['errors'])
        self.assertTrue(orphan.is_file())

    def test_original_and_preview_cannot_escape_their_folders(self):
        for record, field, destination, message in [
            (self.case['original'], 'path', '../outside.dng', 'Outside originals'),
            (self.case['preview'], 'path', '../outside.jpg', 'Preview outside'),
        ]:
            with self.subTest(field=message):
                previous = record[field]
                record[field] = destination
                self.save()
                with self.assertRaisesRegex(ValueError, message):
                    build_suite.build(self.root)
                record[field] = previous

    def test_duplicates_and_fresh_holdouts_are_rejected(self):
        self.selection['assets'].append(copy.deepcopy(self.case))
        self.save()
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            build_suite.build(self.root)
        self.selection['assets'].pop()
        self.case['split'] = 'holdout'
        self.save()
        with self.assertRaisesRegex(ValueError, 'exposed regression'):
            build_suite.build(self.root)

    def test_catalogue_escapes_labels_and_rejects_active_urls(self):
        self.case['reason'] = '<script>alert("label")</script>'
        self.save()
        self.build()
        html = (self.root / 'catalogue.html').read_text()
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn(self.case['reason'], html)
        self.case['source_url'] = 'javascript:alert(1)'
        self.save()
        with contextlib.redirect_stdout(io.StringIO()):
            build_suite.build(self.root)
        with self.assertRaisesRegex(ValueError, 'HTTP or HTTPS'):
            build_catalogue.build(self.root)

    def test_verifier_detects_broken_catalogue_and_missing_preview(self):
        self.build()
        self.preview.unlink()
        report = verify_collection.verify(self.root)
        self.assertFalse(report['valid'])
        self.assertTrue(any('Missing preview' in error for error in report['errors']))
        self.assertTrue(any('Broken catalogue link' in error for error in report['errors']))


class PublicIndexTests(unittest.TestCase):
    def test_scan_reads_staged_blobs_and_blocks_private_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def git(*args):
                subprocess.run(['git', '-C', folder, *args], check=True, capture_output=True)
            git('init', '-q')
            readme = root / 'README.md'
            readme.write_text('Public documentation\n')
            git('add', 'README.md')
            private_path = '/' + 'Users' + '/example/private/input.dng'
            readme.write_text(private_path)
            with patch.object(check_public_repo, 'ROOT', root), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(check_public_repo.check(), 0)
                git('add', 'README.md')
                self.assertEqual(check_public_repo.check(), 1)
                readme.write_text('Public documentation\n')
                (root / 'photo.dng').write_bytes(b'II*\x00private')
                git('add', 'README.md', 'photo.dng')
                self.assertEqual(check_public_repo.check(), 1)


if __name__ == '__main__':
    unittest.main()
