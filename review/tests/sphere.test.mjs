import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeView, isSphere, sphereUV} from '../web/sphere-geometry.js';
import {sphereReview} from '../web/panels/sphere.js';
import {reviewer} from '../web/panels/reviewer.js';
import {SphereViewer} from '../web/sphere.js';
import {CompareViewer} from '../web/compare.js';

const close = (actual, expected) => assert.ok(Math.abs(actual-expected)<1e-10, `${actual} != ${expected}`);
test('sphere identity is explicit, never inferred from aspect ratio', () => {
  assert.equal(isSphere({width:800,height:400}), false);
  assert.equal(isSphere({metadata:{projection:'rectilinear'}}), false);
  assert.equal(isSphere({metadata:{projection:'equirectangular'}}), true);
});
test('view bounds retain poles and normalize finite longitudes', () => {
  assert.deepEqual(normalizeView({yaw:540,pitch:100,hfov:5}), {yaw:-180,pitch:90,hfov:25});
  assert.deepEqual(normalizeView({yaw:NaN,pitch:-100,hfov:Infinity}), {yaw:0,pitch:-90,hfov:75});
  assert.deepEqual(normalizeView(null), {yaw:0,pitch:0,hfov:75});
});
test('cardinal and seam rays match the export helper convention', () => {
  for(const [yaw,u] of [[0,.5],[90,.75],[-90,.25],[180,0],[-180,0]]) {
    const uv=sphereUV(0,0,1.5,{yaw,pitch:0,hfov:75}); close(uv.u,u);close(uv.v,.5);
  }
  close(sphereUV(0,0,1.5,{pitch:90}).v,0);
  close(sphereUV(0,0,1.5,{pitch:-90}).v,1);
});
test('field of view is horizontal regardless of viewport aspect', () => {
  for(const aspect of [.5,1,1.5,2]) close(sphereUV(1,0,aspect,{hfov:90}).u,.625);
  close(sphereUV(0,1,1,{hfov:90}).v,.25);
  assert.ok(sphereUV(0,1,2,{hfov:90}).v>.25);
});

function panelDOM(t) {
  class TestNode {
    constructor(tag, text = '') {
      this.tagName = tag; this.children = []; this.dataset = {}; this.text = text;
      this.classList = {remove() {}};
    }
    append(...children) {this.children.push(...children);}
    replaceChildren(...children) {this.children = [...children];}
    addEventListener() {}
    setAttribute(name, value) {this[name] = value;}
    querySelector(selector) {
      const match = /^(\w+)(?:\[([^=]+)=["']?([^"'\]]+)["']?\])?$/.exec(selector);
      assert.ok(match, `Unsupported test selector: ${selector}`);
      const [, tag, key, value] = match;
      for (const child of this.children) {
        if (child.tagName === tag && (!key || child[key] === value)) return child;
        const nested = child.querySelector(selector);
        if (nested) return nested;
      }
      return null;
    }
    get textContent() {return this.text + this.children.map(child => child.textContent).join('');}
    set textContent(value) {this.text = value; this.children = [];}
    getContext() {return null;}
  }
  const observers = [], cancelled = [];
  const globals = {
    Node: TestNode,
    document: {createElement: tag => new TestNode(tag), createTextNode: text => new TestNode('#text', text)},
    ResizeObserver: class {
      constructor() {this.disconnected = false; observers.push(this);}
      observe() {}
      disconnect() {this.disconnected = true;}
    },
    requestAnimationFrame: () => 1,
    cancelAnimationFrame: frame => cancelled.push(frame),
  };
  const original = new Map(Object.keys(globals).map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  t.after(() => {
    for (const [key, descriptor] of original) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else delete globalThis[key];
    }
  });
  for (const [key, value] of Object.entries(globals)) Object.defineProperty(globalThis, key, {configurable:true, writable:true, value});
  return {observers, cancelled};
}

const flat = {id:'flat', label:'Normal photo', image:'flat.jpg', metadata:{projection:'rectilinear'}};
const panorama = {id:'panorama', label:'Full sphere', image:'panorama.jpg', metadata:{projection:'equirectangular'}};
const panelContext = (id, left, right) => ({
  dataset:{id:'collection'}, photo:{id, title:id}, left, right,
  review:() => ({}), update:() => {},
});

for (const [label, left, right] of [['normal photo', flat, flat], ['flat left variant', flat, panorama], ['flat right variant', panorama, flat]]) {
  test(`leaving 360 review with a ${label} allows the next photo to load`, t => {
    const {observers, cancelled} = panelDOM(t);
    let activePanel = sphereReview(panelContext('unsupported', left, right));
    assert.match(activePanel.element.textContent, /Choose panorama variants marked as equirectangular/);
    assert.equal(activePanel.viewer, undefined);
    assert.doesNotThrow(() => activePanel.destroy?.());

    activePanel = sphereReview(panelContext('next-panorama', panorama, panorama));
    assert.ok(activePanel.viewer);
    assert.match(activePanel.element.textContent, /360 viewing needs WebGL graphics support/);
    assert.equal(activePanel.viewer.dead, false);
    assert.doesNotThrow(() => activePanel.destroy?.());
    assert.equal(activePanel.viewer.dead, true);
    assert.equal(observers.length, 1);
    assert.equal(observers[0].disconnected, true);
    assert.deepEqual(cancelled, [1]);
  });
}

const widePhoto = {id:'wide', label:'Wide normal photo', image:'wide.jpg', width:800, height:400};
for (const [label, left, right, Viewer] of [
  ['panorama pair', panorama, {...panorama, id:'edited-panorama'}, SphereViewer],
  ['normal photo pair', flat, flat, CompareViewer],
  ['panorama and flat photo', panorama, flat, CompareViewer],
  ['flat photo and panorama', flat, panorama, CompareViewer],
  ['2:1 photo without projection metadata', widePhoto, widePhoto, CompareViewer],
]) {
  test(`Photo reviewer chooses the appropriate viewer for a ${label}`, t => {
    const {observers} = panelDOM(t);
    const panel = reviewer(panelContext(label, left, right));
    assert.ok(panel.viewer instanceof Viewer);
    assert.equal(panel.viewer.root.className, Viewer === SphereViewer ? 'sphere-viewer' : 'compare-viewer');
    assert.doesNotThrow(() => panel.destroy());
    assert.equal(observers.length, 1);
    assert.equal(observers[0].disconnected, true);
  });
}

test('Photo reviewer can navigate sphere to normal photo and back while retaining the selected angle', t => {
  const {observers, cancelled} = panelDOM(t);
  const sphereContext = panelContext('navigation-panorama', panorama, panorama);
  let activePanel = reviewer(sphereContext);
  const firstViewer = activePanel.viewer;
  assert.ok(firstViewer instanceof SphereViewer);
  firstViewer.setView({yaw:65, pitch:12, hfov:80});
  activePanel.destroy();
  assert.equal(firstViewer.dead, true);

  activePanel = reviewer(panelContext('navigation-flat', flat, flat));
  assert.ok(activePanel.viewer instanceof CompareViewer);
  activePanel.destroy();

  activePanel = reviewer(sphereContext);
  assert.ok(activePanel.viewer instanceof SphereViewer);
  assert.notEqual(activePanel.viewer, firstViewer);
  assert.deepEqual(activePanel.viewer.view, {yaw:65, pitch:12, hfov:80});
  activePanel.destroy();
  assert.equal(observers.length, 3);
  assert.ok(observers.every(observer => observer.disconnected));
  assert.deepEqual(cancelled, [1, 1]);
});
