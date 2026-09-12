import {test, beforeEach, afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {ReviewStore} from '../web/store.js';

const record = (id, version = 1) => ({workspaceId: 'workspace-a', dataset: {id, cases: [{id: 'photo', variants: [{id: 'candidate', assetRevision: 'render-1'}]}]}, feedback: {}, version});
let memory, stores, originalFetch;
beforeEach(() => {
  memory = new Map(); stores = []; originalFetch = globalThis.fetch;
  globalThis.localStorage = {getItem: key => memory.get(key) ?? null, setItem: (key, value) => memory.set(key, value), removeItem: key => memory.delete(key)};
});
afterEach(() => {for (const store of stores) clearTimeout(store.timer); globalThis.fetch = originalFetch; delete globalThis.localStorage;});
function store() {const value = new ReviewStore(); stores.push(value); return value;}
function response(value, status = 200) {return new Response(JSON.stringify(value), {status, headers: {'Content-Type': 'application/json'}});}
function gate() {let resolve; const promise = new Promise(r => {resolve = r;}); return {promise, resolve};}

test('autosave adopts canonical revisions and stores user decisions independently of detail checks', async () => {
  const data = record('one'), s = store(); s.setRecord(data);
  globalThis.fetch = async (path, options) => {
    assert.equal(path, '/api/datasets/one/feedback'); const payload = JSON.parse(options.body);
    assert.equal(payload.feedback.photo.candidate.assetRevision, 'render-1');
    return response({...data, version: 2, feedback: {photo: {candidate: {...payload.feedback.photo.candidate, updatedAt: 'server-time', stale: false}}}});
  };
  s.update('photo', 'candidate', {decision: 'accepted'}); await s.flush();
  assert.equal(s.review('photo', 'candidate').decision, 'accepted'); assert.equal(s.review('photo', 'candidate').updatedAt, 'server-time');
  assert.equal(s.dirty, false); assert.equal(memory.size, 0); assert.equal(s.export().version, 2);
});

test('edits made during a save are queued with the next server version', async () => {
  const data = record('one'), s = store(), first = gate(); s.setRecord(data);
  const versions = []; let call = 0;
  globalThis.fetch = async (_, options) => {
    const body = JSON.parse(options.body); versions.push(body.version); call++;
    if (call === 1) await first.promise;
    return response({...data, version: body.version + 1, feedback: body.feedback});
  };
  s.update('photo', 'candidate', {note: 'First'}); const saving = s.flush();
  s.update('photo', 'candidate', {note: 'Latest'}); first.resolve(); await saving;
  assert.deepEqual(versions, [1, 2]); assert.equal(s.review('photo', 'candidate').note, 'Latest'); assert.equal(s.dirty, false);
});

test('notes made during a collection fetch are saved to the original collection', async () => {
  const s = store(), request = gate(), waiting = gate(); s.setRecord(record('one'));
  const writes = [];
  globalThis.fetch = async (path, options) => {
    if (!options.method) {waiting.resolve(); await request.promise; return response(record('two'));}
    const payload = JSON.parse(options.body); writes.push({path, payload});
    return response({...record('one', 2), feedback: payload.feedback});
  };
  const loading = s.load('two'); await waiting.promise;
  s.update('photo', 'candidate', {note: 'Keep the late edit'}); request.resolve(); await loading;
  assert.equal(writes.length, 1); assert.equal(writes[0].path, '/api/datasets/one/feedback');
  assert.equal(writes[0].payload.feedback.photo.candidate.note, 'Keep the late edit'); assert.equal(s.dataset.id, 'two');
});

test('conflicts preserve local feedback and do not apply it to new assets', async () => {
  const s = store(); s.setRecord(record('one'));
  globalThis.fetch = async () => response({error: 'Workspace changed'}, 409);
  s.update('photo', 'candidate', {note: 'Preserve me'}); await assert.rejects(s.flush(), /Workspace changed/);
  assert.equal(s.dirty, true); assert.equal(s.error.status, 409); assert.equal(s.review('photo', 'candidate').note, 'Preserve me');
  assert.equal(JSON.parse(memory.get(s.key())).feedback.photo.candidate.note, 'Preserve me');
});

test('automatic refresh cannot overwrite a note entered while fetching', async () => {
  const s = store(), request = gate(); s.setRecord(record('one'));
  globalThis.fetch = async () => {await request.promise; return response(record('one', 2));};
  const refreshing = s.refresh(); s.update('photo', 'candidate', {note: 'Concurrent edit'}); request.resolve();
  assert.equal(await refreshing, false); assert.equal(s.review('photo', 'candidate').note, 'Concurrent edit'); assert.equal(s.version, 1);
});

test('newer workspace revisions keep older browser drafts available without applying them', async () => {
  const s = store(); s.setRecord(record('one')); s.update('photo', 'candidate', {note: 'Older draft'}); clearTimeout(s.timer);
  globalThis.fetch = async () => response(record('one', 8));
  const next = store(); await next.load('one');
  assert.equal(next.dirty, false); assert.equal(next.recovered.feedback.photo.candidate.note, 'Older draft'); assert.deepEqual(next.feedback, {});
});

test('drafts never cross workspace boundaries even with identical dataset IDs and versions', async () => {
  const s = store(); s.setRecord(record('same')); s.update('photo', 'candidate', {note: 'Private to A'}); clearTimeout(s.timer);
  globalThis.fetch = async () => response({...record('same'), workspaceId: 'workspace-b'});
  const next = store(); await next.load('same');
  assert.equal(next.dirty, false); assert.equal(next.recovered, null); assert.deepEqual(next.feedback, {});
  assert.equal(next.export().workspaceId, 'workspace-b'); assert.notEqual(next.key(), s.key());
});

test('conflict recovery remains available after the newer workspace feedback is saved', async () => {
  const s = store(); s.setRecord(record('one')); s.update('photo', 'candidate', {note: 'Recover later'}); clearTimeout(s.timer);
  s.preserveRecovery(); memory.delete(s.key()); s.setRecord(record('one', 3));
  globalThis.fetch = async () => response(record('one', 4));
  const next = store(); await next.load('one');
  assert.equal(next.recovered.feedback.photo.candidate.note, 'Recover later');
  assert.equal(next.recovered.schemaVersion, 1); assert.equal(next.dirty, false);
});
