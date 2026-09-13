import test from 'node:test';
import assert from 'node:assert/strict';
import {CompareViewer} from '../web/compare.js';

const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);
function viewer() {
  const value = Object.create(CompareViewer.prototype);
  const box = {clientWidth: 800, clientHeight: 600,
    getBoundingClientRect() { return {left: 100, top: 50, width: this.clientWidth, height: this.clientHeight}; },
    contains: () => true};
  const pane = {box, img: {naturalWidth: 4000, naturalHeight: 3000, style: {}}};
  Object.assign(value, {zoom: 'fit', center: {x: .5, y: .5}, panes: [pane],
    surface: {classList: {remove() {}, toggle() {}}}, updateScale() {}});
  value.position();
  return value;
}
function imagePoint(value, x, y) {
  const pane = value.panes[0], rect = pane.box.getBoundingClientRect();
  return [(x - rect.left - parseFloat(pane.img.style.left)) / pane.scale,
    (y - rect.top - parseFloat(pane.img.style.top)) / pane.scale];
}

test('continuous zoom from Fit keeps the pixel under the pointer stationary in both directions', () => {
  const value = viewer(), pane = value.panes[0];
  const point = imagePoint(value, 230, 430);
  for (const zoom of [.2137, 1, 4, .06]) {
    value.setZoom(zoom, {pane, x: 230, y: 430});
    imagePoint(value, 230, 430).forEach((coordinate, i) => close(coordinate, point[i]));
    close(pane.scale, zoom);
  }
});

test('100 percent is one CSS pixel per image pixel and remains fixed on resize', () => {
  const value = viewer(), pane = value.panes[0];
  value.setZoom(1);
  assert.equal(pane.img.style.width, '4000px');
  pane.box.clientWidth = 500;
  value.position();
  assert.equal(pane.img.style.width, '4000px');
  value.setZoom('fit');
  assert.equal(pane.img.style.width, '500px');
  assert.deepEqual(value.center, {x: .5, y: .5});
});

test('full-export source stays stable across Fit and custom zoom', () => {
  const value = viewer(), item = {image: 'preview.jpg', full: 'full.jpg'};
  value.left = item; value.right = item; value.mode = 'wipe';
  assert.equal(value.source(item), 'full.jpg');
  value.setZoom(.337);
  assert.equal(value.source(item), 'full.jpg');
  assert.equal(value.source({image: 'crop.jpg'}), 'crop.jpg');
});

test('a lone full export does not break a matched preview comparison', () => {
  const value = viewer();
  value.mode = 'wipe';
  value.left = {image: 'base-preview.jpg'};
  value.right = {image: 'edit-preview.jpg', full: 'edit-full.jpg'};
  assert.equal(value.source(value.right), 'edit-preview.jpg');
  value.setZoom(1);
  assert.equal(value.source(value.right), 'edit-preview.jpg');
  value.mode = 'single';
  assert.equal(value.source(value.right), 'edit-full.jpg');
});

test('wheel handles pixel, line and page deltas without recreating panes', () => {
  for (const [deltaY, deltaMode] of [[48, 0], [3, 1], [.08, 2]]) {
    const value = viewer(), pane = value.panes[0];
    let prevented = false;
    value.wheel({target: {}, deltaY, deltaMode, clientX: 500, clientY: 350,
      preventDefault() { prevented = true; }});
    assert.ok(prevented);
    assert.equal(value.panes[0], pane);
    close(value.zoom, .2 * Math.exp(-48 * .002));
  }
});

test('zoom rejects invalid values and bounds extreme magnification', () => {
  const value = viewer();
  for (const zoom of [NaN, Infinity, -1, 0]) value.setZoom(zoom);
  assert.equal(value.zoom, 'fit');
  value.setZoom(100);
  assert.equal(value.zoom, 16);
  value.setZoom(.00001);
  assert.equal(value.zoom, .001);
});
