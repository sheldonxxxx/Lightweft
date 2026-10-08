"""Recipe executor tests against a fake MCP engine."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'workflow'))
import edit_recipe


REVISION_TOOLS = {'set_adjustments', 'mask_create', 'mask_generate', 'mask_duplicate', 'mask_update', 'set_metadata', 'save_version'}


class FakeEngine:
    def revision_tools(self):
        return REVISION_TOOLS

    def __init__(self):
        self.revision = 0
        self.calls = []
        self.masks = []
        self.fail_render = False

    def __call__(self, tool, args):
        self.calls.append((tool, copy.deepcopy(args)))
        if tool == 'get_session':
            return {'revision': self.revision, 'adjustments': {'masks': copy.deepcopy(self.masks)}}
        if 'expected_revision' in args and args['expected_revision'] != self.revision:
            raise edit_recipe.RecipeError('REVISION_CONFLICT')
        if tool == 'render_compare':
            return {'images': ['x.jpg']}
        if tool == 'render':
            if self.fail_render:
                raise edit_recipe.RecipeError('render failed')
            return {'images': ['x.jpg']}
        self.revision += 1
        if tool in ('mask_generate', 'mask_create', 'mask_duplicate'):
            mask = {'id': f'mask-{len(self.masks) + 1}', 'adjustments': dict(args.get('adjustments', {})),
                    'subMasks': [{'id': f'sub-{len(self.masks) + 1}-0'}]}
            self.masks.append(mask)
            return {'revision': self.revision, 'mask_id': mask['id']}
        if tool == 'mask_update':
            mask = next(m for m in self.masks if m['id'] == args['mask_id'])
            mask['adjustments'].update(args.get('patch', {}).get('adjustments', {}))
        return {'revision': self.revision}


RECIPE = {
    'steps': [
        {'id': 'base', 'tool': 'set_adjustments', 'args': {'mode': 'replace', 'patch': {'exposure': -0.1}}},
        {'as': 'subject', 'tool': 'mask_generate', 'args': {'kind': 'subject', 'adjustments': {'exposure': 0.6}}},
        {'as': 'environment', 'tool': 'mask_duplicate', 'args': {'mask_id': {'$mask': 'subject'}, 'invert': True}},
        {'tool': 'mask_update', 'args': {'mask_id': {'$mask': 'environment'}, 'patch': {'adjustments': {'exposure': {'$param': 'dark'}}}}},
        {'tool': 'mask_update', 'args': {'mask_id': {'$mask': 'subject'}, 'submask_operations': [
            {'op': 'edit', 'submask_id': {'$submask': {'mask': 'subject', 'index': 0}}}]}},
    ]
}


class RecipeTests(unittest.TestCase):
    def write(self, directory, name, recipe):
        path = Path(directory) / name
        path.write_text(json.dumps(recipe))
        return path

    def test_run_tracks_revisions_and_resolves_references(self):
        engine = FakeEngine()
        result = edit_recipe.run(copy.deepcopy(RECIPE), engine, 'S', {'dark': -0.7})
        self.assertEqual(result['masks'], {'subject': 'mask-1', 'environment': 'mask-2'})
        self.assertEqual(result['revision'], 5)
        updates = [args for tool, args in engine.calls if tool == 'mask_update']
        self.assertEqual(updates[0]['mask_id'], 'mask-2')
        self.assertEqual(updates[0]['patch']['adjustments']['exposure'], -0.7)
        self.assertEqual(updates[1]['submask_operations'][0]['submask_id'], 'sub-1-0')
        self.assertEqual([e['revision'] for e in result['log']], [1, 2, 3, 4, 5])

    def test_missing_parameter_is_an_error(self):
        with self.assertRaisesRegex(edit_recipe.RecipeError, 'dark'):
            edit_recipe.run(copy.deepcopy(RECIPE), FakeEngine(), 'S')

    def test_validate_rejects_unknown_mask_reference_and_managed_args(self):
        bad = {'steps': [{'tool': 'mask_update', 'args': {'mask_id': {'$mask': 'ghost'}}}]}
        with self.assertRaisesRegex(edit_recipe.RecipeError, 'ghost'):
            edit_recipe.validate(bad)
        with self.assertRaisesRegex(edit_recipe.RecipeError, 'managed'):
            edit_recipe.validate({'steps': [{'tool': 'render', 'args': {'session_id': 'x'}}]})
        with self.assertRaisesRegex(edit_recipe.RecipeError, 'only for steps that create'):
            edit_recipe.validate({'steps': [{'as': 'x', 'tool': 'render'}]})

    def test_extends_replaces_steps_by_id_and_appends_others(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write(directory, 'parent.json', RECIPE)
            child = {'extends': 'parent.json', 'steps': [
                {'id': 'base', 'tool': 'set_adjustments', 'args': {'mode': 'replace', 'patch': {'exposure': 0.2}}},
                {'tool': 'render', 'args': {'long_edge': 1600}},
            ]}
            recipe = edit_recipe.load(self.write(directory, 'child.json', child))
        self.assertEqual(len(recipe['steps']), len(RECIPE['steps']) + 1)
        self.assertEqual(recipe['steps'][0]['args']['patch'], {'exposure': 0.2})
        self.assertEqual(recipe['steps'][-1]['tool'], 'render')
        self.assertNotIn('extends', recipe)

    def test_extends_cycle_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write(directory, 'a.json', {'extends': 'b.json', 'steps': []})
            self.write(directory, 'b.json', {'extends': 'a.json', 'steps': []})
            with self.assertRaisesRegex(edit_recipe.RecipeError, 'extends itself'):
                edit_recipe.load(Path(directory) / 'a.json')

    def test_stop_after_halts_at_the_named_step(self):
        engine = FakeEngine()
        result = edit_recipe.run(copy.deepcopy(RECIPE), engine, 'S', {'dark': 0}, stop_after='base')
        self.assertEqual(len(result['log']), 1)

    def test_reference_render_switches_masks_off_without_touching_the_session(self):
        engine = FakeEngine()
        edit_recipe.run(copy.deepcopy(RECIPE), engine, 'S', {'dark': -0.7})
        before, revision = copy.deepcopy(engine.masks), engine.revision
        engine.calls.clear()
        result = edit_recipe.render_without_mask_adjustments(engine, 'S', {'long_edge': 1600})
        self.assertEqual(result, {'images': ['x.jpg']})
        tool, args = engine.calls[-1]
        self.assertEqual(tool, 'render_compare')
        self.assertEqual(args['long_edge'], 1600)
        self.assertEqual([v['label'] for v in args['variants']], ['Edit', 'Global only'])
        self.assertNotIn('disabled_masks', args['variants'][0])
        self.assertEqual(args['variants'][1]['disabled_masks'], ['mask-1', 'mask-2'])
        self.assertEqual({tool for tool, _ in engine.calls}, {'get_session', 'render_compare'})
        self.assertEqual((engine.masks, engine.revision), (before, revision))

    def test_reference_render_can_limit_masks_and_rejects_empty_or_oversized_sets(self):
        engine = FakeEngine()
        with self.assertRaisesRegex(edit_recipe.RecipeError, 'no masks'):
            edit_recipe.render_without_mask_adjustments(engine, 'S')
        edit_recipe.run(copy.deepcopy(RECIPE), engine, 'S', {'dark': 0})
        edit_recipe.render_without_mask_adjustments(engine, 'S', mask_ids={'mask-2'})
        self.assertEqual(engine.calls[-1][1]['variants'][1]['disabled_masks'], ['mask-2'])
        engine.masks = [{'id': f'm{i}', 'adjustments': {}} for i in range(edit_recipe.MAX_DISABLED_MASKS + 1)]
        with self.assertRaisesRegex(edit_recipe.RecipeError, 'at most'):
            edit_recipe.render_without_mask_adjustments(engine, 'S')

    def test_expected_revision_goes_to_exactly_the_tools_the_engine_names(self):
        engine = FakeEngine()
        recipe = {'steps': [
            {'tool': 'set_metadata', 'args': {'rating': 3}},
            {'tool': 'save_version', 'args': {'label': 'first'}},
            {'tool': 'render', 'args': {'long_edge': 800}},
        ]}
        edit_recipe.run(recipe, engine, 'S')
        sent = {tool: 'expected_revision' in args for tool, args in engine.calls if tool != 'get_session'}
        self.assertEqual(sent, {'set_metadata': True, 'save_version': True, 'render': False})
        engine.calls.clear()
        edit_recipe.run(recipe, engine, 'S', revision_tools=set())
        self.assertFalse(any('expected_revision' in args for _, args in engine.calls))

    def test_a_call_that_cannot_name_its_revision_tools_is_refused(self):
        calls = []
        with self.assertRaisesRegex(edit_recipe.RecipeError, 'revision_tools'):
            edit_recipe.run(copy.deepcopy(RECIPE), lambda tool, args: calls.append(tool), 'S', {'dark': 0})
        self.assertEqual(calls, [])

    def test_missing_parameters_fail_before_the_first_engine_call(self):
        self.assertEqual(edit_recipe.required_parameters(RECIPE), ['dark'])
        engine = FakeEngine()
        with self.assertRaisesRegex(edit_recipe.RecipeError, r"missing parameters \['dark'\]"):
            edit_recipe.run(copy.deepcopy(RECIPE), engine, 'S', {})
        self.assertEqual(engine.calls, [])

    def test_cli_reports_parameters_and_rejects_a_run_missing_them_without_starting_a_client(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, 'r.json', RECIPE)
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(edit_recipe.main(['validate', str(path)]), 0)
            self.assertIn('parameters: dark', out.getvalue())
            with contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(edit_recipe.main(['run', str(path), '--session', 'S', '--client', 'definitely-not-a-command']), 1)
            self.assertIn('missing parameters', err.getvalue())
    def test_cli_validate_and_flatten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, 'r.json', RECIPE)
            self.assertEqual(edit_recipe.main(['validate', str(path)]), 0)
            self.assertEqual(edit_recipe.main(['flatten', str(path)]), 0)
            bad = self.write(directory, 'bad.json', {'steps': [{}]})
            self.assertEqual(edit_recipe.main(['validate', str(bad)]), 1)


FAKE_CLIENT = r"""
import json, sys, time
mode = sys.argv[1]
print('startup noise that is not JSON', flush=True)
if mode == 'no-ready':
    sys.stderr.write('cannot connect to engine\n'); sys.stderr.flush(); time.sleep(30)
print(json.dumps({'ready': True}), flush=True)
for line in sys.stdin:
    request = json.loads(line)
    if request.get('close'):
        break
    if 'list_tools' in request:
        tools = [{'name': 'rapidraw_set_adjustments', 'inputSchema': {'properties': {'expected_revision': {}, 'patch': {}}}},
                 {'name': 'rapidraw_render', 'inputSchema': {'properties': {'long_edge': {}}}},
                 {'name': 'rapidraw_save_version', 'inputSchema': {'properties': {'expected_revision': {}}}}]
        print(json.dumps({'isError': False, 'data': {'tools': [] if mode == 'no-tools' else tools}}), flush=True)
        continue
    if mode == 'hang':
        time.sleep(30)
    if mode == 'crash':
        sys.stderr.write('engine exploded\n'); sys.stderr.flush(); sys.exit(3)
    print('log line before the reply', flush=True)
    if request['tool'] == 'bad':
        print(json.dumps({'isError': True, 'message': 'nope'}), flush=True)
    else:
        print(json.dumps({'isError': False, 'data': {'echo': request['arguments'], 'timeout': request['timeout_ms']}}), flush=True)
"""


class StdioClientTests(unittest.TestCase):
    def client(self, mode, **options):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        script = Path(directory.name) / 'client.py'
        script.write_text(FAKE_CLIENT)
        client = edit_recipe.StdioClient([sys.executable, str(script), mode], **options)
        self.addCleanup(client.kill)
        return client

    def test_calls_skip_non_json_lines_and_report_tool_errors(self):
        client = self.client('echo')
        self.assertEqual(client('get_session', {'a': 1}, wait=5), {'echo': {'a': 1}, 'timeout': 5000})
        with self.assertRaisesRegex(edit_recipe.RecipeError, 'bad failed'):
            client('bad', {})
        client.close()

    def test_revision_tools_come_from_the_engine_schemas_once(self):
        client = self.client('echo')
        self.assertEqual(client.revision_tools(), {'set_adjustments', 'save_version'})
        self.assertEqual(client.revision_tools(), {'set_adjustments', 'save_version'})
        client.close()

    def test_an_empty_tool_list_is_an_error_not_an_empty_set(self):
        client = self.client('no-tools')
        with self.assertRaisesRegex(edit_recipe.RecipeError, 'no tool list'):
            client.revision_tools()

    def test_a_client_that_never_becomes_ready_times_out_with_its_stderr(self):
        with self.assertRaisesRegex(edit_recipe.RecipeError, 'ready signal within 1 s.*cannot connect to engine'):
            self.client('no-ready', ready_timeout=1)

    def test_a_hung_request_times_out_instead_of_blocking(self):
        client = self.client('hang')
        client.reply_grace = 0
        started = time.monotonic()
        with self.assertRaisesRegex(edit_recipe.RecipeError, 'no reply to slow within 1 s'):
            client('slow', {}, wait=1)
        self.assertLess(time.monotonic() - started, 10)
        self.assertIsNotNone(client.process.poll())

    def test_a_crashed_client_reports_its_last_stderr_lines(self):
        client = self.client('crash')
        with self.assertRaisesRegex(edit_recipe.RecipeError, 'closed before its reply to x.*engine exploded'):
            client('x', {}, wait=5)


if __name__ == '__main__':
    unittest.main()
