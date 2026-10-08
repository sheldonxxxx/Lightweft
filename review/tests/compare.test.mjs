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

test('pin coordinates are image-relative, reject outside points, and recall their zoom', async () => {
  const {imagePoint, createPin, markerOffset, viewFor, withoutPin, withNote} = await import('../web/pins.js');
  const rect = {left: 100, top: 50, width: 800, height: 400};
  assert.deepEqual(imagePoint(rect, 500, 250), {x: .5, y: .5});
  assert.equal(imagePoint(rect, 99, 250), null);
  assert.equal(imagePoint({left: 0, top: 0, width: 0, height: 0}, 0, 0), null);
  const pin = createPin({x: .25, y: .75, zoom: 2, compareWith: ['base']}, 'p1');
  assert.deepEqual({id: pin.id, x: pin.x, y: pin.y, zoom: pin.zoom, compareWith: pin.compareWith}, {id: 'p1', x: .25, y: .75, zoom: 2, compareWith: ['base']});
  assert.equal(createPin({x: 0, y: 0, zoom: null}, 'p2').zoom, undefined);
  assert.deepEqual(markerOffset(pin, {left: 10, top: 20, width: 400, height: 200}), {left: 110, top: 170});
  assert.deepEqual(viewFor(pin), {zoom: 2, center: {x: .25, y: .75}});
  assert.equal(viewFor(createPin({x: .1, y: .2}, 'p3')).zoom, 1);
  assert.deepEqual(withoutPin([pin, {id: 'q'}], 'p1').map(item => item.id), ['q']);
  assert.equal(withNote([pin], 'p1', 'fix').at(0).note, 'fix');
});

test('focusing a pin centres the view on it at the recorded zoom', async () => {
  const {createPin} = await import('../web/pins.js');
  const value = viewer();
  value.focusPin(createPin({x: .3, y: .6, zoom: .5}, 'p'));
  close(value.zoom, .5);
  assert.deepEqual(value.center, {x: .3, y: .6});
  value.focusPin(createPin({x: .8, y: .2}, 'q'));
  close(value.zoom, 1);
});

test('pinning from the keyboard uses the view center and the recorded zoom', () => {
  const value = viewer();
  const added = [];
  Object.assign(value, {left: {id: 'base'}, right: {id: 'edit'}, pinButton: {hidden: true}, pinCenterButton: {hidden: true}, renderPins() {}});
  value.setPins('edit', [], {onAdd: pin => added.push(pin)});
  assert.equal(value.pinCenterButton.hidden, false);
  value.pinCenter();
  assert.deepEqual([added[0].x, added[0].y, added[0].zoom, added[0].compareWith], [.5, .5, undefined, ['base']]);
  value.center = {x: .3, y: .6}; value.zoom = 2;
  value.pinCenter();
  assert.deepEqual([added[1].x, added[1].y, added[1].zoom], [.3, .6, 2]);
  value.setPins('edit', [], null);
  assert.equal(value.pinCenterButton.hidden, true);
  value.pinCenter();
  assert.equal(added.length, 2);
});

test('pins at the server limit remain intact and refuse further pointer or keyboard additions', () => {
  const value = viewer(), added = [];
  Object.assign(value, {pinButton: {}, pinCenterButton: {}, renderPins() {}});
  const pins = Array.from({length: 200}, (_, i) => ({id: String(i), x: .5, y: .5, note: `Note ${i}`}));
  value.setPins('edit', pins, {onAdd: pin => added.push(pin)});
  value.pinCenter();
  value.addPinAt(300, 200, {});
  assert.equal(value.pinButton.disabled, true);
  assert.equal(value.pinCenterButton.disabled, true);
  assert.deepEqual(value.pins, pins);
  assert.equal(added.length, 0);
  value.setPins('edit', pins.slice(1), {onAdd: pin => added.push(pin)});
  assert.equal(value.pinButton.disabled, false);
});

test('pointer pins belong to the reviewed photo and never use an unaligned reference frame', () => {
  const value = viewer(), added = [], candidate = {id: 'edit'}, original = {id: 'base'};
  Object.assign(value, {pinButton: {disabled: false}, pinVariant: 'edit', note: {}, left: original, right: candidate,
    pinHandlers: {onAdd: pin => added.push(pin)},
    paneAt: (_x, _y, item) => ({item, img: {naturalWidth: 300, getBoundingClientRect: () => ({left: 100, top: 50, width: 300, height: 450})}})});
  value.addPinAt(175, 275, original);
  assert.equal(added.length, 0);
  value.addPinAt(175, 275, candidate);
  assert.deepEqual([added[0].x, added[0].y, added[0].compareWith], [.25, .5, ['base']]);
});
