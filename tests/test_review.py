"""Review persistence and real HTTP boundary tests, using synthetic private media."""
import base64
import copy
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import quote

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'review'))
from server import ReviewError, ReviewServer, ReviewStore


class ReviewFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.media = self.root / 'media'
        self.media.mkdir()
        (self.media / 'base.jpg').write_bytes(b'baseline image bytes')
        (self.media / 'edit.jpg').write_bytes(b'candidate image bytes')
        (self.media / 'detail.png').write_bytes(b'detail image bytes')
        (self.media / 'recipe.json').write_bytes(b'{"exposure":0.25,"authentic":"editor export"}\n')
        (self.media / 'private.jpg').write_bytes(b'never registered')
        self.store = ReviewStore(self.root / 'workspace', self.media)
        self.dataset = {'schemaVersion': 1, 'id': 'test', 'title': 'Example collection', 'cases': [
            {'id': 'one', 'title': 'Example photo', 'variants': [
                {'id': 'baseline', 'label': 'Baseline', 'role': 'baseline', 'image': 'base.jpg'},
                {'id': 'candidate', 'label': 'Candidate', 'role': 'candidate', 'image': 'edit.jpg', 'recipe': 'recipe.json', 'recipeFormat': 'rapidraw', 'metadata': {'editor': 'RapidRAW'}}
            ], 'regions': [{'id': 'detail', 'label': 'Texture', 'x': 10, 'y': 20, 'width': 300, 'height': 200, 'images': [{'variantId': 'candidate', 'image': 'detail.png'}]}]}
        ]}
        self.record = self.store.put_dataset('test', self.dataset, 0)

    def feedback(self, decision='accepted', checks=None):
        return {'one': {'candidate': {'decision': decision, 'note': 'Keep this direction', 'checks': checks or {}, 'style': {'direction': 'Soft color', 'avoid': 'Crunchy edges'}}}}


class StoreTests(ReviewFixture, unittest.TestCase):
    def test_display_defaults_persist_without_invalidating_review(self):
        saved = self.store.put_feedback('test', self.feedback(checks={'detail': True}), self.record['version'])
        data = copy.deepcopy(saved['dataset'])
        data['cases'][0]['defaultView'] = 'side'
        data['cases'][0]['variants'][1]['defaultView'] = 'single'
        updated = self.store.put_dataset('test', data, saved['version'])
        reopened = ReviewStore(self.store.workspace, self.media).get_dataset('test')
        self.assertEqual(reopened, updated)
        self.assertEqual(reopened['dataset']['cases'][0]['defaultView'], 'side')
        self.assertEqual(reopened['dataset']['cases'][0]['variants'][1]['defaultView'], 'single')
        self.assertEqual(reopened['feedback'], saved['feedback'])
        self.assertEqual(reopened['dataset']['cases'][0]['variants'][1]['assetRevision'], saved['dataset']['cases'][0]['variants'][1]['assetRevision'])

    def test_display_defaults_reject_unknown_modes(self):
        for target in ('case', 'variant'):
            for value in ('slider', '', None, True, [], {}):
                with self.subTest(target=target, value=value):
                    data = copy.deepcopy(self.dataset)
                    item = data['cases'][0] if target == 'case' else data['cases'][0]['variants'][1]
                    item['defaultView'] = value
                    with self.assertRaisesRegex(ReviewError, target + '.defaultView'):
                        self.store.validate_dataset(data)
        for mode in ('single', 'side', 'wipe'):
            data = copy.deepcopy(self.dataset)
            data['cases'][0]['defaultView'] = mode
            data['cases'][0]['variants'][1]['defaultView'] = mode
            self.store.validate_dataset(data)

    def test_persistence_metadata_and_compare_and_swap(self):
        saved = self.store.put_feedback('test', self.feedback(), self.record['version'])
        reopened = ReviewStore(self.root / 'workspace', self.media).get_dataset('test')
        self.assertEqual(saved, reopened)
        self.assertFalse(reopened['dataset']['cases'][0]['aligned'])
        self.assertFalse(reopened['dataset']['cases'][0]['regions'][0]['aligned'])
        self.assertEqual(reopened['dataset']['cases'][0]['variants'][1]['metadata'], {'editor': 'RapidRAW'})
        with self.assertRaises(ReviewError) as raised:
            self.store.put_feedback('test', self.feedback('rejected'), self.record['version'])
        self.assertEqual(raised.exception.status, 409)
        self.assertEqual(self.store.get_dataset('test')['feedback']['one']['candidate']['decision'], 'accepted')

    def test_workspace_identity_is_stable_and_namespaces_independent_stores(self):
        workspace_id = self.store.workspace_summary()['workspaceId']
        self.assertEqual(len(workspace_id), 24)
        self.assertNotIn(str(self.store.workspace), workspace_id)
        reopened = ReviewStore(self.store.workspace, self.media)
        self.assertEqual(reopened.get_dataset('test')['workspaceId'], workspace_id)
        self.assertEqual(self.record['workspaceId'], workspace_id)
        saved = self.store.put_feedback('test', self.feedback(), self.record['version'])
        self.assertEqual(saved['workspaceId'], workspace_id)
        other = ReviewStore(self.root / 'another-workspace', self.media)
        self.assertNotEqual(other.workspace_summary()['workspaceId'], workspace_id)

    def test_acceptance_is_independent_of_technical_checks(self):
        saved = self.store.put_feedback('test', self.feedback(), self.record['version'])
        self.assertEqual(saved['feedback']['one']['candidate']['decision'], 'accepted')
        self.assertEqual(saved['feedback']['one']['candidate']['checks'], {})

    def test_asset_replacement_invalidates_only_affected_variant(self):
        feedback = self.feedback(checks={'overview': True, 'detail': True, 'noise': True})
        feedback['one']['baseline'] = {'decision': 'accepted', 'note': 'Original reference', 'checks': {'overview': True}}
        saved = self.store.put_feedback('test', feedback, self.record['version'])
        (self.media / 'edit.jpg').write_bytes(b'new candidate pixels')
        refreshed = self.store.get_dataset('test')
        self.assertEqual(refreshed['version'], saved['version'] + 1)
        candidate = refreshed['feedback']['one']['candidate']
        self.assertEqual(candidate['decision'], '')
        self.assertEqual(candidate['checks'], {})
        self.assertTrue(candidate['stale'])
        self.assertEqual(candidate['note'], 'Keep this direction')
        self.assertEqual(refreshed['feedback']['one']['baseline']['decision'], 'accepted')
        with self.assertRaises(ReviewError) as raised:
            self.store.put_feedback('test', feedback, saved['version'])
        self.assertEqual(raised.exception.status, 409)

    def test_crop_change_invalidates_approval_and_stale_import(self):
        saved = self.store.put_feedback('test', self.feedback(), self.record['version'])
        old_feedback = saved['feedback']
        (self.media / 'detail.png').write_bytes(b'changed detail pixels')
        fresh = self.store.get_dataset('test')
        self.assertEqual(fresh['feedback']['one']['candidate']['decision'], '')
        with self.assertRaises(ReviewError) as raised:
            self.store.put_feedback('test', old_feedback, fresh['version'])
        self.assertEqual(raised.exception.status, 409)

    def test_reimport_preserves_unchanged_decisions_and_resets_changed_variant(self):
        saved = self.store.put_feedback('test', self.feedback(), self.record['version'])
        same = self.store.put_dataset('test', self.dataset, saved['version'])
        self.assertEqual(same['feedback']['one']['candidate']['decision'], 'accepted')
        changed = copy.deepcopy(self.dataset)
        changed['cases'][0]['variants'][1]['description'] = 'A different edit description'
        newer = self.store.put_dataset('test', changed, same['version'])
        self.assertTrue(newer['feedback']['one']['candidate']['stale'])

    def test_missing_media_clears_approval_and_blocks_acceptance(self):
        self.store.put_feedback('test', self.feedback(), self.record['version'])
        (self.media / 'edit.jpg').unlink()
        fresh = self.store.get_dataset('test')
        self.assertTrue(fresh['dataset']['cases'][0]['variants'][1]['unavailable'])
        self.assertEqual(fresh['feedback']['one']['candidate']['decision'], '')
        with self.assertRaisesRegex(ReviewError, 'Unavailable media'):
            self.store.put_feedback('test', self.feedback(), fresh['version'])

    def test_disable_toggle_preserves_feedback_and_asset_revisions(self):
        saved = self.store.put_feedback('test', self.feedback(checks={'overview': True}), self.record['version'])
        revision = saved['dataset']['cases'][0]['variants'][1]['assetRevision']
        disabled = self.store.set_disabled('test', True)
        self.assertTrue(disabled['dataset']['disabled'])
        self.assertEqual(disabled['version'], saved['version'] + 1)
        self.assertEqual(disabled['feedback'], saved['feedback'])
        self.assertEqual(disabled['dataset']['cases'][0]['variants'][1]['assetRevision'], revision)
        self.assertEqual(self.store.workspace_summary()['datasets'][0]['disabled'], True)
        enabled = self.store.set_disabled('test', False)
        self.assertFalse(enabled['dataset']['disabled'])
        self.assertEqual(enabled['feedback']['one']['candidate']['decision'], 'accepted')
        self.assertEqual(enabled['dataset']['cases'][0]['variants'][1]['assetRevision'], revision)
        self.assertEqual(self.store.workspace_summary()['datasets'][0]['disabled'], False)

    def test_disable_toggle_works_while_media_is_missing(self):
        self.store.put_feedback('test', self.feedback(), self.record['version'])
        (self.media / 'edit.jpg').unlink()
        disabled = self.store.set_disabled('test', True)
        self.assertTrue(disabled['dataset']['disabled'])
        self.assertTrue(disabled['dataset']['cases'][0]['variants'][1]['unavailable'])
        enabled = self.store.set_disabled('test', False)
        self.assertFalse(enabled['dataset']['disabled'])

    def test_manifest_replace_without_disabled_field_keeps_state(self):
        disabled = self.store.set_disabled('test', True)
        replaced = self.store.put_dataset('test', copy.deepcopy(self.dataset), disabled['version'])
        self.assertTrue(replaced['dataset']['disabled'])
        explicit = copy.deepcopy(self.dataset)
        explicit['disabled'] = False
        enabled = self.store.put_dataset('test', explicit, replaced['version'])
        self.assertFalse(enabled['dataset']['disabled'])

    def test_validation_rejects_traversal_active_media_symlinks_duplicates(self):
        (self.root / 'outside.jpg').write_bytes(b'private')
        (self.media / 'link.jpg').symlink_to(self.root / 'outside.jpg')
        (self.media / 'local-link.jpg').symlink_to(self.media / 'base.jpg')
        (self.media / 'link-dir').symlink_to(self.root, target_is_directory=True)
        for path in ('../outside.jpg', '/outside.jpg', 'link.jpg', 'local-link.jpg', 'link-dir/outside.jpg', 'base.jpg/../edit.jpg', 'base.jpg\\edit.jpg', 'x.svg'):
            with self.subTest(path=path):
                data = copy.deepcopy(self.dataset)
                data['cases'][0]['variants'][0]['image'] = path
                with self.assertRaises(ReviewError):
                    self.store.validate_dataset(data)
        data = copy.deepcopy(self.dataset)
        data['cases'].append(copy.deepcopy(data['cases'][0]))
        with self.assertRaisesRegex(ReviewError, 'Duplicate case'):
            self.store.validate_dataset(data)

    def test_media_registry_cache_observes_external_manifest_updates(self):
        self.assertNotIn('private.jpg', self.store.allowed_assets())
        updated = copy.deepcopy(self.dataset)
        updated['cases'][0]['variants'][1]['image'] = 'private.jpg'
        other = ReviewStore(self.store.workspace, self.media)
        other.put_dataset('test', updated, 1)
        assets = self.store.allowed_assets()
        self.assertIn('private.jpg', assets)
        self.assertNotIn('edit.jpg', assets)

    def test_region_geometry_and_feedback_reference_validation(self):
        for value in (-1, float('nan'), float('inf'), True):
            data = copy.deepcopy(self.dataset)
            data['cases'][0]['regions'][0]['width'] = value
            with self.assertRaises(ReviewError):
                self.store.validate_dataset(data)
        data = copy.deepcopy(self.dataset)
        data['cases'][0]['regions'][0]['native'] = 'yes'
        with self.assertRaisesRegex(ReviewError, 'region.native'):
            self.store.validate_dataset(data)
        with self.assertRaisesRegex(ReviewError, 'unknown variant'):
            self.store.put_feedback('test', {'one': {'unknown': {'decision': 'accepted'}}}, self.record['version'])
        feedback = self.feedback()
        feedback['one']['candidate']['checks']['noise'] = 'yes'
        with self.assertRaisesRegex(ReviewError, 'booleans'):
            self.store.put_feedback('test', feedback, self.record['version'])

    def test_styles_preserve_provenance_and_exact_preset_snapshot(self):
        payload = {'name': 'Soft winter', 'kind': 'preset', 'datasetId': 'test', 'caseId': 'one', 'variantId': 'candidate', 'preferences': {'keep': 'Gentle highlight falloff'}}
        recipe = (self.media / 'recipe.json').read_bytes()
        saved = self.store.create_profile(payload)
        private = self.store.get_profile(saved['id'])
        self.assertNotIn('recipeFile', saved)
        self.assertEqual((self.store.workspace / private['recipeFile']).read_bytes(), recipe)
        self.assertEqual(saved['provenance']['variantId'], 'candidate')
        (self.media / 'recipe.json').write_bytes(b'{"later":"different recipe"}')
        self.assertEqual((self.store.workspace / private['recipeFile']).read_bytes(), recipe)
        with self.assertRaisesRegex(ReviewError, 'actual exported recipe'):
            self.store.create_profile({**payload, 'variantId': 'baseline'})
        profile = self.store.create_profile({**payload, 'kind': 'profile', 'variantId': 'baseline'})
        self.assertEqual(profile['preferences'], payload['preferences'])
        self.assertNotIn('recipeSha256', profile)

    def test_profile_preferences_are_qualitative_text(self):
        payload = {'name': 'Style', 'kind': 'profile', 'datasetId': 'test', 'caseId': 'one', 'variantId': 'candidate'}
        for preferences in ([], {'keep': {'exposure': 1}}, {'keep': ['sun']}, {'keep': 1}):
            with self.assertRaises(ReviewError):
                self.store.create_profile({**payload, 'preferences': preferences})

    def test_stale_style_selection_is_rejected(self):
        revision = self.record['dataset']['cases'][0]['variants'][1]['assetRevision']
        (self.media / 'edit.jpg').write_bytes(b'next edit')
        with self.assertRaises(ReviewError) as raised:
            self.store.create_profile({'name': 'Style', 'kind': 'profile', 'datasetId': 'test', 'caseId': 'one', 'variantId': 'candidate', 'assetRevision': revision})
        self.assertEqual(raised.exception.status, 409)

    def test_concurrent_writers_one_revision_wins(self):
        outcomes = []
        def write():
            try:
                another = ReviewStore(self.store.workspace, self.media)
                outcomes.append(another.put_feedback('test', self.feedback(), 1)['version'])
            except ReviewError as exc:
                outcomes.append(exc.status)
        threads = [threading.Thread(target=write) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(outcomes), [2, 409, 409, 409])

    def test_native_cli_import_and_feedback_roundtrip(self):
        source = self.root / 'dataset.json'
        source.write_text(json.dumps(self.dataset))
        args = ['--workspace', str(self.root / 'cli-state'), '--media-root', str(self.media)]
        imported = subprocess.run([sys.executable, str(REPO / 'review/cli.py'), 'import', str(source), '--id', 'test', *args], text=True, capture_output=True)
        self.assertEqual(imported.returncode, 0, imported.stderr)
        self.assertEqual(json.loads(imported.stdout)['count'], 1)
        exported = subprocess.run([sys.executable, str(REPO / 'review/cli.py'), 'feedback-export', 'test', *args], text=True, capture_output=True)
        self.assertEqual(exported.returncode, 0, exported.stderr)
        feedback_file = self.root / 'feedback.json'
        feedback_file.write_text(exported.stdout)
        restored = subprocess.run([sys.executable, str(REPO / 'review/cli.py'), 'feedback-import', 'test', str(feedback_file), '--version', '1', *args], text=True, capture_output=True)
        self.assertEqual(restored.returncode, 0, restored.stderr)

    def test_cli_disable_enable_and_import_inheritance(self):
        source = self.root / 'dataset.json'
        source.write_text(json.dumps(self.dataset))
        args = ['--workspace', str(self.root / 'cli-state'), '--media-root', str(self.media)]

        def run(*command):
            result = subprocess.run([sys.executable, str(REPO / 'review/cli.py'), *command, *args], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

        run('import', str(source), '--id', 'test')
        self.assertIs(run('disable', 'test')['disabled'], True)
        self.assertIs(run('list')['datasets'][0]['disabled'], True)
        run('import', str(source), '--id', 'test')
        self.assertIs(run('show', 'test')['dataset']['disabled'], True)
        self.assertIs(run('enable', 'test')['disabled'], False)

    def test_cli_dispatches_embedded_html_to_inert_importer(self):
        from cli import load_dataset
        raw = (self.media / 'base.jpg').read_bytes()
        data = {'assets': {'base': {'src': 'data:image/jpeg;base64,' + base64.b64encode(raw).decode()}}, 'cases': [{'id': 'example', 'before': 'base', 'variants': []}]}
        source = self.media / 'review.html'
        source.write_text('<script id="galleryData" type="application/json">' + json.dumps(data) + '</script>')
        result = load_dataset(source, self.media, 'html-test', None, [])
        self.assertEqual(result['id'], 'html-test')
        self.assertEqual(result['cases'][0]['variants'][0]['image'], 'base.jpg')


class HttpTests(ReviewFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.web = self.root / 'web'
        self.web.mkdir()
        (self.web / 'index.html').write_text('<!doctype html><title>Review</title>')
        self.server = ReviewServer(('127.0.0.1', 0), self.store, self.web)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.port = self.server.server_address[1]

    def request(self, method, path, payload=None, headers=None):
        conn = HTTPConnection('127.0.0.1', self.port, timeout=5)
        self.addCleanup(conn.close)
        body = json.dumps(payload) if payload is not None else None
        headers = dict(headers or {})
        if payload is not None:
            headers.setdefault('Content-Type', 'application/json')
        conn.request(method, path, body=body, headers=headers)
        result = conn.getresponse()
        return result.status, dict(result.getheaders()), result.read()

    def test_http_api_and_origin_protection(self):
        status, headers, body = self.request('GET', '/api/workspace')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['datasets'][0]['id'], 'test')
        self.assertEqual(headers['Cache-Control'], 'no-store')
        for headers in ({'Host': 'attacker.test'}, {'Origin': 'https://attacker.test'}, {'Origin': 'null'}, {'Sec-Fetch-Site': 'cross-site'}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request('GET', '/api/workspace', headers=headers)[0], 403)
        self.assertEqual(self.request('PUT', '/api/datasets/test/feedback', {'version': 1, 'feedback': {}}, {'Origin': f'http://127.0.0.1:{self.port}'})[0], 200)
        self.assertEqual(self.request('PUT', '/api/datasets/test/feedback', {'version': 2, 'feedback': {}}, {'Content-Type': 'text/plain'})[0], 415)
        self.assertEqual(self.request('OPTIONS', '/api/workspace', headers={'Origin': 'https://attacker.test'})[0], 403)

    def test_only_registered_media_and_safe_static_files(self):
        for path in ('private.jpg', '../outside.jpg', '/etc/passwd'):
            status, _, _ = self.request('GET', '/api/media?path=' + quote(path))
            self.assertIn(status, (400, 404))
        status, headers, body = self.request('GET', '/api/media?path=base.jpg')
        self.assertEqual((status, body), (200, b'baseline image bytes'))
        self.assertEqual(headers['Content-Type'], 'image/jpeg')
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        (self.media / 'base.jpg').unlink()
        (self.media / 'base.jpg').symlink_to(self.media / 'private.jpg')
        self.assertEqual(self.request('GET', '/api/media?path=base.jpg')[0], 404)
        self.assertIn(self.request('GET', '/%2e%2e/media/private.jpg')[0], (400, 404))
        (self.web / 'leak.js').symlink_to(self.media / 'private.jpg')
        self.assertEqual(self.request('GET', '/leak.js')[0], 404)

    def test_http_rejects_nonfinite_json_and_oversized_body(self):
        conn = HTTPConnection('127.0.0.1', self.port, timeout=5)
        self.addCleanup(conn.close)
        conn.request('PUT', '/api/datasets/test/feedback', body='{"version": NaN, "feedback": {}}', headers={'Content-Type': 'application/json'})
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        response.read()
        conn.close()
        self.assertEqual(self.request('PUT', '/api/datasets/test/feedback', {'feedback': {}}, {'Content-Length': str(9 * 1024 * 1024)})[0], 413)

    def test_static_content_types_and_script_security(self):
        for filename, content, expected_type in [('app.js', 'export const safe = true;', {'text/javascript', 'application/javascript'}), ('style.css', 'body {color: white;}', {'text/css'}), ('icon.svg', '<svg xmlns="http://www.w3.org/2000/svg"/>', {'image/svg+xml'})]:
            (self.web / filename).write_text(content)
            status, headers, body = self.request('GET', '/' + filename)
            self.assertEqual(status, 200)
            self.assertIn(headers['Content-Type'], expected_type)
            self.assertIn("script-src 'self'", headers['Content-Security-Policy'])

    def test_byte_ranges_cache_and_head(self):
        url = '/api/media?path=base.jpg'
        status, headers, body = self.request('GET', url, headers={'Range': 'bytes=2-5'})
        self.assertEqual((status, body), (206, b'seli'))
        self.assertEqual(headers['Content-Range'], 'bytes 2-5/20')
        self.assertEqual(self.request('GET', url, headers={'Range': 'bytes=-5'})[2], b'bytes')
        self.assertEqual(self.request('GET', url, headers={'Range': 'bytes=900-'})[0], 416)
        status, _, body = self.request('GET', url, headers={'If-None-Match': headers['ETag']})
        self.assertEqual((status, body), (304, b''))
        status, headers, body = self.request('HEAD', url)
        self.assertEqual((status, body, headers['Content-Length']), (200, b'', '20'))

    def test_http_authoring_conflict_and_feedback_export(self):
        status, _, body = self.request('PUT', '/api/datasets/test/feedback', {'version': 1, 'feedback': self.feedback()})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['version'], 2)
        self.assertEqual(self.request('PUT', '/api/datasets/test', {'version': 1, 'dataset': self.dataset})[0], 409)
        status, headers, body = self.request('GET', '/api/datasets/test/feedback/export')
        self.assertEqual(status, 200)
        self.assertIn('attachment', headers['Content-Disposition'])
        self.assertEqual(json.loads(body)['feedback']['one']['candidate']['decision'], 'accepted')

    def test_http_disable_endpoint_guards_versions(self):
        status, _, body = self.request('PUT', '/api/datasets/test/disabled', {'disabled': True, 'version': 1})
        self.assertEqual(status, 200)
        record = json.loads(body)
        self.assertTrue(record['dataset']['disabled'])
        self.assertEqual(record['version'], 2)
        self.assertEqual(json.loads(self.request('GET', '/api/workspace')[2])['datasets'][0]['disabled'], True)
        self.assertEqual(self.request('PUT', '/api/datasets/test/disabled', {'disabled': False, 'version': 1})[0], 409)
        self.assertEqual(self.request('PUT', '/api/datasets/test/disabled', {'disabled': 'yes', 'version': 2})[0], 400)
        status, _, body = self.request('PUT', '/api/datasets/test/disabled', {'disabled': False, 'version': 2})
        self.assertEqual((status, json.loads(body)['dataset']['disabled']), (200, False))

    def test_http_profile_and_preset_export(self):
        payload = {'name': 'Winter', 'kind': 'preset', 'datasetId': 'test', 'caseId': 'one', 'variantId': 'candidate'}
        status, _, body = self.request('POST', '/api/profiles', payload)
        self.assertEqual(status, 201)
        profile_id = json.loads(body)['id']
        status, headers, body = self.request('GET', f'/api/profiles/{profile_id}/export')
        self.assertEqual(status, 200)
        self.assertEqual(body, (self.media / 'recipe.json').read_bytes())
        self.assertIn('attachment', headers['Content-Disposition'])
        self.assertIn(profile_id, self.request('GET', '/api/workspace')[2].decode())

    def test_server_rejects_non_loopback_binding(self):
        with self.assertRaisesRegex(ReviewError, 'loopback'):
            ReviewServer(('192.0.2.1', 0), self.store, self.web)

    def test_server_allows_lan_binding_without_trusting_foreign_hosts(self):
        server = ReviewServer(('0.0.0.0', 0), self.store, self.web)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        lan_port = server.server_address[1]

        def request(headers):
            conn = HTTPConnection('127.0.0.1', lan_port, timeout=5)
            self.addCleanup(conn.close)
            conn.request('GET', '/api/workspace', headers=headers)
            response = conn.getresponse()
            status = response.status
            response.read()
            conn.close()
            return status

        self.assertEqual(request({'Host': f'127.0.0.1:{lan_port}'}), 200)
        # A DNS-rebinding page sends its own hostname consistently in Host and
        # Origin; the local-address allowlist must still reject it.
        self.assertEqual(request({'Host': f'evil.example:{lan_port}', 'Origin': f'http://evil.example:{lan_port}', 'Sec-Fetch-Site': 'same-origin'}), 403)
        self.assertEqual(request({'Host': f'evil.com bad host:{lan_port}'}), 403)
        self.assertEqual(request({'Host': 'localhost'}), 403)


if __name__ == '__main__':
    unittest.main()
