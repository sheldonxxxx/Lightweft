import test from 'node:test';
import assert from 'node:assert/strict';
import {sequenceForPhoto, sequenceComparison, photoReviewURL} from '../web/sequence.js';

const photo = (id, metadata = {}, variants = [{id: 'base'}, {id: 'a'}, {id: 'b'}]) =>
  ({id, title: id, category: 'street', split: 'development', metadata, variants});

test('only an explicit sequenceGroup joins photographs, regardless of matching genre or split', () => {
  const selected = photo('one', {sequenceGroup: 'walk'});
  const neighbour = photo('two', {sequenceGroup: 'walk'});
  const other = photo('three', {sequenceGroup: 'another-walk'});
  const ungrouped = photo('four');
  const dataset = {cases: [selected, other, neighbour, ungrouped]};
  assert.deepEqual(sequenceForPhoto(dataset, selected).cases.map(item => item.id), ['one', 'two']);
  assert.equal(sequenceForPhoto(dataset, ungrouped), null);
});

test('absent, non-string and empty group values never create an implicit set', () => {
  for (const sequenceGroup of [undefined, null, '', '   ', 0, false, {}]) {
    const selected = photo('one', {sequenceGroup});
    assert.equal(sequenceForPhoto({cases: [selected, photo('two', {sequenceGroup})]}, selected), null);
  }
});

test('finite numeric order takes priority, with stable manifest order for ties and unspecified order', () => {
  const cases = [photo('unspecified', {sequenceGroup: 'walk'}),
    photo('third', {sequenceGroup: 'walk', sequenceOrder: 3}),
    photo('first', {sequenceGroup: 'walk', sequenceOrder: 0}),
    photo('tie', {sequenceGroup: 'walk', sequenceOrder: 3}),
    photo('string-order', {sequenceGroup: 'walk', sequenceOrder: '1'}),
    photo('invalid', {sequenceGroup: 'walk', sequenceOrder: Infinity})];
  assert.deepEqual(sequenceForPhoto({cases}, cases[0]).cases.map(item => item.id),
    ['first', 'third', 'tie', 'unspecified', 'string-order', 'invalid']);
});

test('group label comes from the ordered set and stays stable when the selected neighbour changes', () => {
  const cases = [photo('later', {sequenceGroup: 'walk', sequenceLabel: 'Later label', sequenceOrder: 2}),
    photo('earlier', {sequenceGroup: 'walk', sequenceLabel: ' Evening walk ', sequenceOrder: 1})];
  assert.equal(sequenceForPhoto({cases}, cases[0]).label, 'Evening walk');
  assert.equal(sequenceForPhoto({cases}, cases[1]).label, 'Evening walk');
  assert.equal(sequenceForPhoto({cases: [photo('plain', {sequenceGroup: 'explicit-id'})]},
    photo('plain', {sequenceGroup: 'explicit-id'})).label, 'explicit-id');
});

test('comparison matches exact variant IDs and leaves a gap rather than substituting a labelled look', () => {
  const cases = [photo('one', {sequenceGroup: 'walk'}), photo('two', {sequenceGroup: 'walk'},
    [{id: 'base'}, {id: 'different', label: 'A'}, {id: 'b'}])];
  const rows = sequenceComparison(sequenceForPhoto({cases}, cases[0]), 'a', 'b');
  assert.equal(rows[0].left.id, 'a');
  assert.equal(rows[1].left, null);
  assert.equal(rows[1].right.id, 'b');
  assert.equal(rows.length, 2);
});

test('variant order and missing media do not change the selected comparison identity', () => {
  const missing = {id: 'a', image: 'a.jpg', unavailable: ['a.jpg']};
  const cases = [photo('one', {sequenceGroup: 'walk'}, [{id: 'b'}, missing, {id: 'base'}])];
  const rows = sequenceComparison(sequenceForPhoto({cases}, cases[0]), 'a', 'base');
  assert.equal(rows[0].left, missing);
  assert.equal(rows[0].right.id, 'base');
});

test('grouping and comparison preserve source order, metadata and variants without mutation', () => {
  const dataset = {cases: [photo('two', {sequenceGroup: 'walk', sequenceOrder: 2}),
    photo('one', {sequenceGroup: 'walk', sequenceOrder: 1})]};
  const original = structuredClone(dataset);
  sequenceComparison(sequenceForPhoto(dataset, dataset.cases[0]), 'a', 'b');
  assert.deepEqual(dataset, original);
});

test('photo-review links retain dataset and case identities and encode query delimiters', () => {
  const href = photoReviewURL('dataset & other', 'case/one?panel=set');
  const url = new URL(href, 'http://localhost/');
  assert.equal(url.searchParams.get('dataset'), 'dataset & other');
  assert.equal(url.searchParams.get('case'), 'case/one?panel=set');
  assert.equal(url.searchParams.get('panel'), 'review');
});
