#!/usr/bin/env python3
"""Declarative editing recipes for a RapidRAW MCP session.

A recipe is a JSON document describing an edit as ordered steps, so a photograph's
edit is data that can be reviewed, versioned, diffed and replayed, instead of a
script that was patched pass after pass.

```json
{
  "version": 1,
  "extends": "base-recipe.json",
  "steps": [
    {"tool": "set_adjustments", "args": {"mode": "replace", "patch": {"exposure": -0.1}}},
    {"as": "subject", "tool": "mask_generate",
     "args": {"kind": "subject", "name": "Subject", "parameters": {"grow": -30, "feather": 2},
              "adjustments": {"exposure": 0.6}}},
    {"as": "environment", "tool": "mask_duplicate",
     "args": {"mask_id": {"$mask": "subject"}, "name": "Environment", "invert": true}},
    {"tool": "mask_update",
     "args": {"mask_id": {"$mask": "environment"}, "patch": {"adjustments": {"exposure": -0.7}}}}
  ]
}
```

* Each step is one MCP tool call. `session_id` is added for you, and so is
  `expected_revision` for every tool whose input schema accepts it. The engine says
  which: the stdio client reads the tool schemas, and another `call` supplies the
  same through a `revision_tools()` method or the `revision_tools` argument of
  `run()`. The revision returned by each step feeds the next.
* `"as": "name"` records the mask the step created. `{"$mask": "name"}` in any later
  argument is replaced by that mask's ID.
* `{"$submask": {"mask": "name", "index": 0}}` resolves to the ID of a submask by
  position, read from the live session when needed.
* `extends` loads another recipe first; the child's steps are appended, and a step
  with the same `"id"` replaces the parent's step in place, so a new pass is a small
  diff against the last one. The parent path is relative to the child.
* `{"$param": "name"}` is replaced from `--param name=value` (JSON values) or the
  `params` mapping, so one recipe can serve a family of photographs.

The engine stays authoritative: this module only sequences calls and resolves
references. Tool names and argument shapes are those of the RapidRAW MCP server.

`run()` takes an injected `call(tool, arguments) -> dict` returning the tool's
structured data and raising on error, so it works with any MCP client. The command
line offers `validate` and `flatten` (no engine needed) and `run`, which drives the
bundled stdio client from the rapidraw-mcp skill.
"""
from __future__ import annotations

import argparse
import collections
import copy
import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

RESERVED_ARGS = {'session_id', 'expected_revision'}
MAX_DISABLED_MASKS = 32


class RecipeError(ValueError):
    pass


def load(path, _seen=()):
    """Read a recipe, resolving `extends` into one flat document."""
    path = Path(path).resolve()
    if path in _seen:
        raise RecipeError(f'recipe extends itself: {path}')
    try:
        recipe = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise RecipeError(f'cannot read recipe {path}: {error}') from error
    if not isinstance(recipe, dict) or not isinstance(recipe.get('steps'), list):
        raise RecipeError(f'{path}: a recipe is an object with a "steps" array')
    parent = recipe.get('extends')
    if parent:
        base = load(path.parent / parent, _seen + (path,))
        recipe = _extend(base, recipe)
    recipe.pop('extends', None)
    validate(recipe, path)
    return recipe


def _extend(base, child):
    steps = copy.deepcopy(base['steps'])
    positions = {step['id']: i for i, step in enumerate(steps) if 'id' in step}
    for step in child['steps']:
        if 'id' in step and step['id'] in positions:
            steps[positions[step['id']]] = copy.deepcopy(step)
        else:
            if 'id' in step:
                positions[step['id']] = len(steps)
            steps.append(copy.deepcopy(step))
    merged = {**base, **{k: v for k, v in child.items() if k != 'steps'}}
    merged['steps'] = steps
    return merged


def validate(recipe, source='recipe'):
    names, ids = set(), set()
    for index, step in enumerate(recipe['steps']):
        where = f'{source} step {index}'
        if not isinstance(step, dict) or not isinstance(step.get('tool'), str):
            raise RecipeError(f'{where}: needs a "tool" name')
        args = step.get('args', {})
        if not isinstance(args, dict):
            raise RecipeError(f'{where}: "args" must be an object')
        if RESERVED_ARGS & set(args):
            raise RecipeError(f'{where}: {sorted(RESERVED_ARGS & set(args))} are managed by the executor')
        if 'id' in step:
            if step['id'] in ids:
                raise RecipeError(f'{where}: duplicate step id {step["id"]!r}')
            ids.add(step['id'])
        for ref in _references(args, '$mask'):
            if ref not in names:
                raise RecipeError(f'{where}: mask {ref!r} is not created by an earlier step')
        for ref in _references(args, '$submask'):
            if not isinstance(ref, dict) or ref.get('mask') not in names or not isinstance(ref.get('index'), int):
                raise RecipeError(f'{where}: $submask needs an earlier mask name and an integer index')
        if step.get('as'):
            if step['tool'] not in {'mask_create', 'mask_generate', 'mask_duplicate'}:
                raise RecipeError(f'{where}: "as" is only for steps that create a mask')
            names.add(step['as'])


def required_parameters(recipe):
    """Names every `{"$param": name}` in the recipe, so a run can fail before its first call."""
    return sorted({name for step in recipe['steps'] for name in _references(step.get('args', {}), '$param')})


def _references(value, key):
    if isinstance(value, dict):
        if set(value) == {key}:
            yield value[key]
            return
        for item in value.values():
            yield from _references(item, key)
    elif isinstance(value, list):
        for item in value:
            yield from _references(item, key)


def _substitute(value, resolve):
    if isinstance(value, dict):
        if len(value) == 1:
            (key, inner), = value.items()
            if key in ('$mask', '$submask', '$param'):
                return resolve(key, inner)
        return {k: _substitute(v, resolve) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, resolve) for v in value]
    return value


def mask_id_of(data):
    """The mask ID a mask-creating tool returned."""
    mask = data.get('mask') if isinstance(data.get('mask'), dict) else {}
    found = data.get('mask_id') or mask.get('id')
    if not found:
        raise RecipeError(f'the engine returned no mask id: {sorted(data)}')
    return found


def revision_tools_of(call, revision_tools=None):
    """Names of the tools that take `expected_revision`: given, or asked of the engine through `call`."""
    if revision_tools is None:
        ask = getattr(call, 'revision_tools', None)
        if ask is None:
            raise RecipeError('cannot tell which tools take expected_revision: give call a revision_tools() '
                              'method or pass revision_tools to run()')
        revision_tools = ask()
    return set(revision_tools)


def run(recipe, call, session_id, params=None, log=None, stop_after=None, revision_tools=None):
    """Replay `recipe` into an open session. Returns {'masks': {name: id}, 'revision': n, 'log': [...]}."""
    params = params or {}
    missing = [name for name in required_parameters(recipe) if name not in params]
    if missing:
        raise RecipeError(f'missing parameters {missing}: pass them with --param NAME=JSON before the run starts')
    versioned = revision_tools_of(call, revision_tools)
    state = call('get_session', {'session_id': session_id})
    revision = state.get('revision', 0)
    masks, journal = {}, [] if log is None else log

    def resolve(key, inner):
        if key == '$param':
            if inner not in params:
                raise RecipeError(f'missing parameter {inner!r}')
            return params[inner]
        if key == '$mask':
            return masks[inner]
        live = call('get_session', {'session_id': session_id, 'include_adjustments': True})
        items = live.get('adjustments', {}).get('masks', [])
        match = next((m for m in items if m.get('id') == masks[inner['mask']]), None)
        subs = (match or {}).get('subMasks') or (match or {}).get('sub_masks') or []
        if inner['index'] >= len(subs):
            raise RecipeError(f'mask {inner["mask"]!r} has {len(subs)} submasks, not index {inner["index"]}')
        return subs[inner['index']]['id']

    for index, step in enumerate(recipe['steps']):
        args = _substitute(step.get('args', {}), resolve)
        full = {'session_id': session_id, **args}
        if step['tool'] in versioned:
            full['expected_revision'] = revision
        data = call(step['tool'], full)
        revision = data.get('revision', revision)
        if step.get('as'):
            masks[step['as']] = mask_id_of(data)
        journal.append({'step': index, 'id': step.get('id'), 'tool': step['tool'], 'args': args, 'revision': revision})
        if stop_after is not None and step.get('id') == stop_after:
            break
    return {'masks': masks, 'revision': revision, 'log': journal}


def render_without_mask_adjustments(call, session_id, render_args=None, mask_ids=None):
    """Render the edit beside a copy with its masks switched off, without touching the session.

    Uses the engine's `render_compare`, which applies the mask disabling to temporary
    variants only: every mask adjustment (curves, colour grading, HSL, LUTs and the
    rest) is excluded, the session revision and history do not change, and there is
    nothing to restore. The result is the `render_compare` reply: variant "Edit" and
    variant "Global only", rendered with the same crop and size, for judging what the
    masks added. `render_args` may hold `long_edge` and `region`; `mask_ids` limits
    which masks are switched off (all of them by default, at most 32).
    """
    live = call('get_session', {'session_id': session_id, 'include_adjustments': True})
    masks = [m['id'] for m in live.get('adjustments', {}).get('masks', []) if mask_ids is None or m.get('id') in mask_ids]
    if not masks:
        raise RecipeError('the session has no masks to switch off')
    if len(masks) > MAX_DISABLED_MASKS:
        raise RecipeError(f'render_compare can switch off at most {MAX_DISABLED_MASKS} masks; pass mask_ids')
    variants = [{'label': 'Edit'}, {'label': 'Global only', 'disabled_masks': masks}]
    return call('render_compare', {'session_id': session_id, **(render_args or {}), 'variants': variants})


class StdioClient:
    """Drive the rapidraw-mcp skill's persistent client (`mcp-client.mjs`) over pipes.

    Output is read on a background thread so every wait has a deadline: a hung or
    crashed client raises a RecipeError that carries the client's last stderr lines
    instead of blocking forever. Lines that are not JSON replies are skipped.
    """

    reply_grace = 30  # seconds beyond a request's own timeout before the client is declared hung

    def __init__(self, command, ready_timeout=60):
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, bufsize=1)
        self._revision_tools = None
        self._replies = queue.Queue()
        self._errors = collections.deque(maxlen=20)
        threading.Thread(target=self._pump_stdout, daemon=True).start()
        threading.Thread(target=self._pump_stderr, daemon=True).start()
        self._read(ready_timeout, lambda line: '"ready"' in line, 'ready signal')

    def _pump_stdout(self):
        try:
            for line in self.process.stdout:
                if line.startswith('{'):
                    self._replies.put(line)
        except (OSError, ValueError):  # stream closed by kill()
            pass
        self._replies.put(None)

    def _pump_stderr(self):
        try:
            for line in self.process.stderr:
                self._errors.append(line.rstrip())
        except (OSError, ValueError):
            pass

    def _diagnostics(self):
        tail = ' | '.join(self._errors)
        return f' (client stderr: {tail[-600:]})' if tail else ''

    def _read(self, timeout, accept, what):
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            try:
                line = self._replies.get(timeout=max(remaining, 0.001))
            except queue.Empty:
                self.kill()
                raise RecipeError(f'client gave no {what} within {timeout:g} s{self._diagnostics()}') from None
            if line is None:
                raise RecipeError(f'client closed before its {what}{self._diagnostics()}')
            if accept(line):
                return line

    def __call__(self, tool, arguments, wait=600):
        try:
            self.process.stdin.write(json.dumps({'tool': tool, 'arguments': arguments, 'timeout_ms': wait * 1000}) + '\n')
            self.process.stdin.flush()
        except OSError as error:
            raise RecipeError(f'client is not accepting requests: {error}{self._diagnostics()}') from error
        reply = json.loads(self._read(wait + self.reply_grace, lambda line: True, f'reply to {tool}'))
        if reply.get('isError'):
            raise RecipeError(f'{tool} failed: {json.dumps(reply)[:800]}')
        return reply.get('data', reply)

    def revision_tools(self):
        """Tools whose input schema accepts `expected_revision`, read once from the engine."""
        if self._revision_tools is None:
            self.process.stdin.write(json.dumps({'list_tools': []}) + '\n')
            self.process.stdin.flush()
            reply = json.loads(self._read(60 + self.reply_grace, lambda line: True, 'tool list'))
            tools = (reply.get('data') or {}).get('tools') if not reply.get('isError') else None
            if not isinstance(tools, list) or not tools:
                raise RecipeError(f'client returned no tool list: {json.dumps(reply)[:300]}')
            self._revision_tools = {tool['name'].removeprefix('rapidraw_') for tool in tools
                                    if 'expected_revision' in (tool.get('inputSchema') or {}).get('properties', {})}
        return set(self._revision_tools)

    def kill(self):
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            try:
                stream.close()
            except OSError:
                pass

    def close(self):
        try:
            self.process.stdin.write('{"close":true}\n')
            self.process.stdin.flush()
        except OSError:
            pass
        try:
            self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
        self.kill()


def _params(pairs):
    result = {}
    for pair in pairs or []:
        name, _, raw = pair.partition('=')
        try:
            result[name] = json.loads(raw)
        except json.JSONDecodeError:
            result[name] = raw
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    for name, text in (('validate', 'Check a recipe and its parents'), ('flatten', 'Print the recipe with `extends` resolved')):
        item = sub.add_parser(name, help=text)
        item.add_argument('recipe', type=Path)
    runner = sub.add_parser('run', help='Replay a recipe into an open session')
    runner.add_argument('recipe', type=Path)
    runner.add_argument('--session', required=True, help='Session ID of the opened photograph')
    runner.add_argument('--param', action='append', metavar='NAME=JSON')
    runner.add_argument('--log', type=Path, help='Write the operation log here')
    runner.add_argument('--client', nargs=argparse.REMAINDER, required=True,
                        help='Command that starts the persistent MCP client, e.g. node mcp-client.mjs --server ...')
    args = parser.parse_args(argv)
    try:
        recipe = load(args.recipe)
        if args.command == 'validate':
            names = required_parameters(recipe)
            print(f'ok: {len(recipe["steps"])} steps' + (f'; parameters: {", ".join(names)}' if names else ''))
        elif args.command == 'flatten':
            print(json.dumps(recipe, indent=2))
        else:
            params = _params(args.param)
            missing = [name for name in required_parameters(recipe) if name not in params]
            if missing:
                raise RecipeError(f'missing parameters {missing}: pass them with --param NAME=JSON')
            client = StdioClient(args.client)
            try:
                result = run(recipe, client, args.session, params)
            finally:
                client.close()
            if args.log:
                args.log.write_text(json.dumps(result['log'], indent=2) + '\n')
            print(json.dumps({'masks': result['masks'], 'revision': result['revision'], 'steps': len(result['log'])}, indent=2))
    except RecipeError as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
