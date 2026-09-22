import {test} from 'node:test';
import assert from 'node:assert/strict';
import {matchCollection} from '../web/collection.js';

test('collection filter matches title, description, and id with every query word', () => {
  const item = {id: 'style-study', title: 'Personal style study', description: 'Warmer light while preserving depth.'};
  assert.equal(matchCollection(item, ''), true);
  assert.equal(matchCollection(item, 'style'), true);
  assert.equal(matchCollection(item, 'warmer depth'), true);
  assert.equal(matchCollection(item, 'STYLE STUDY'), true);
  assert.equal(matchCollection(item, 'missing'), false);
  assert.equal(matchCollection(item, 'style missing'), false);
});
