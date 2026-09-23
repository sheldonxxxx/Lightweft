import { el, button, select, media } from './dom.js';

/** Shared image surface. Panels choose sources; this owns viewing behaviour. */
export class CompareViewer {
  constructor({ left, right, aligned = false, blind = false, native = false, defaultView }) {
    this.left = left; this.right = right; this.aligned = aligned; this.blind = blind;
    this.mode = ['single', 'side', 'wipe'].includes(defaultView) ? defaultView : left.id === right.id ? 'single' : aligned ? 'wipe' : 'side';
    this.zoom = native ? 1 : 'fit'; this.center = {x: .5, y: .5};
    this.division = 50; this.swapped = false; this.blink = false; this.loaded = new Map();
    this.root = el('section', {class: 'compare-viewer', 'aria-label': 'Photo comparison'});
    this.modeSelect = select('Comparison view', [{value: 'wipe', label: 'Before / after'}, {value: 'side', label: 'Side by side'}, {value: 'single', label: 'Single image'}], this.mode, value => { this.mode = value; this.renderSurface(); });
    this.fitButton = button('Fit', () => this.setZoom('fit'), {title: 'Fit photograph to view'});
    this.zoomInput = el('input', {type: 'number', min: '.1', max: '1600', step: 'any',
      'aria-label': 'Image magnification percent', title: 'Enter a zoom percentage',
      onInput: e => this.setZoom(Number(e.target.value) / 100),
      onChange: e => { this.setZoom(Number(e.target.value) / 100); this.updateScale(true); },
      onBlur: () => this.updateScale(true)});
    const zoomControl = el('div', {class: 'zoom-control'}, this.fitButton,
      el('label', {class: 'zoom-percent'}, this.zoomInput, el('span', {'aria-hidden': 'true'}, '%')));
    this.fullscreenButton = button('⛶', async () => {
      try { if (document.fullscreenElement) await document.exitFullscreen(); else await this.root.requestFullscreen(); }
      catch { this.note.textContent = 'Fullscreen is unavailable in this browser.'; }
    }, {class: 'icon-button', title: 'Fullscreen', 'aria-label': 'Fullscreen comparison'});
    this.toolbar = el('div', {class: 'viewer-toolbar'}, el('div', {class: 'control-group'}, this.modeSelect, zoomControl),
      el('div', {class: 'control-group'}, button('⇄ Swap', () => this.swap(), {title: 'Swap sides · B'}),
        button('Center', () => { this.center = {x: .5, y: .5}; this.position(); }), this.fullscreenButton));
    this.surface = el('div', {class: 'compare-surface'});
    this.note = el('span', {}, 'Loading images…');
    this.hint = el('span', {class: 'viewer-hint'}, 'Hold Space to compare');
    this.root.append(this.toolbar, this.surface, el('div', {class: 'viewer-caption'}, this.note, this.hint));
    this.observer = new ResizeObserver(() => this.position()); this.observer.observe(this.surface);
    this.surface.addEventListener('pointerdown', e => this.pointerDown(e));
    this.surface.addEventListener('pointermove', e => this.pointerMove(e));
    this.surface.addEventListener('pointerup', e => this.pointerUp(e));
    this.surface.addEventListener('pointercancel', e => this.pointerUp(e));
    this.surface.addEventListener('lostpointercapture', e => this.pointerUp(e));
    this.surface.addEventListener('wheel', e => this.wheel(e), {passive: false});
    this.pointers = new Map();
    this.onFullscreenChange = () => { this.syncFullscreen(); this.position(); };
    if (typeof document !== 'undefined' && typeof document.addEventListener === 'function') document.addEventListener('fullscreenchange', this.onFullscreenChange);
    this.syncFullscreen();
    this.renderSurface();
  }
  destroy() {
    this.resetPointers(); this.cancelDivider(); this.observer.disconnect();
    if (typeof document !== 'undefined' && typeof document.removeEventListener === 'function') document.removeEventListener('fullscreenchange', this.onFullscreenChange);
  }
  syncFullscreen() {
    const active = typeof document !== 'undefined' && document.fullscreenElement === this.root;
    this.fullscreenButton.textContent = active ? '×' : '⛶';
    this.fullscreenButton.title = active ? 'Exit fullscreen' : 'Fullscreen';
    this.fullscreenButton.setAttribute('aria-label', active ? 'Exit fullscreen comparison' : 'Fullscreen comparison');
    this.fullscreenButton.setAttribute('aria-pressed', String(active));
  }
  names() { return this.swapped ? [this.right, this.left] : [this.left, this.right]; }
  swap() { this.swapped = !this.swapped; this.renderSurface(); }
  setBlind(value) { this.blind = value; this.renderSurface(); }
  setBlink(value) {
    if (this.blink === value) return;
    this.blink = value;
    this.renderSurface();
  }
  source(item) {
    // Keep comparison sources consistent when only one version has a full export.
    const useFull = this.mode === 'single' || (this.left.full && this.right.full);
    return useFull && item.full ? item.full : item.image;
  }
  pane(item, index) {
    const source = this.source(item);
    const img = el('img', {src: media(source, item.assetRevision), alt: this.blind ? `Comparison ${index === 0 ? 'A' : 'B'}` : item.label, draggable: 'false', decoding: 'async'});
    const label = this.blind ? (index === 0 ? 'A' : 'B') : item.label;
    const evidence = item.native ? (item.nativeDomain === 'recorded-render-region' ? 'Recorded crop' : 'Native crop') : item.full && source === item.full ? 'Full export' : 'Preview';
    const meta = el('span', {class: 'image-meta'});
    const box = el('div', {class: `image-pane pane-${index}`}, img, el('span', {class: 'image-label'}, label), meta);
    const pending = el('span', {class: 'image-loading', role: 'status'}, 'Loading photograph…'); box.append(pending);
    const ready = () => {
      if (!img.naturalWidth) return;
      this.loaded.set(source, {width: img.naturalWidth, height: img.naturalHeight});
      meta.textContent = `${evidence} · ${img.naturalWidth} × ${img.naturalHeight}`;
      pending.remove(); this.position(); this.updateCapability();
    };
    img.addEventListener('load', ready, {once: true});
    img.addEventListener('error', () => { img.hidden = true; pending.textContent = 'Image unavailable. Ask your agent to check this artifact.'; this.note.textContent = 'Some review evidence is unavailable.'; });
    if (img.complete) queueMicrotask(ready);
    return {box, img, source, item, evidence};
  }
  renderSurface() {
    this.resetPointers();
    this.cancelDivider();
    const [a, b] = this.names();
    const mode = this.blink ? 'single' : this.mode;
    this.surface.className = `compare-surface mode-${mode}${this.zoom === 'fit' ? '' : ' can-pan'}`;
    this.surface.replaceChildren();
    this.panes = mode === 'single' ? [this.pane(this.blink ? a : b, this.blink ? 0 : 1)] : [this.pane(a, 0), this.pane(b, 1)];
    this.surface.append(...this.panes.map(p => p.box));
    if (mode === 'wipe') {
      this.marker = el('div', {class: 'wipe-marker', role: 'slider', tabIndex: '0',
        'aria-label': 'Before and after divider', 'aria-orientation': 'horizontal',
        'aria-valuemin': '0', 'aria-valuemax': '100',
        onKeydown: e => this.dividerKeyDown(e),
        onPointerdown: e => {
          if (e.button !== 0 || this.dividerPointer != null) return;
          e.preventDefault(); e.stopPropagation();
          this.marker.focus({preventScroll: true});
          this.dividerPointer = e.pointerId;
          this.dividerStart = {x: e.clientX, division: this.division};
          this.marker.setPointerCapture(e.pointerId);
        },
        onPointermove: e => {
          if (e.pointerId !== this.dividerPointer) return;
          const width = this.surface.getBoundingClientRect().width;
          if (width) this.setDivision(this.dividerStart.division + (e.clientX - this.dividerStart.x) / width * 100);
        },
        onPointerup: e => this.releaseDivider(e),
        onPointercancel: e => this.releaseDivider(e),
        onLostpointercapture: () => { this.dividerPointer = null; }
      }, el('span', {'aria-hidden': 'true'}, '↔'));
      this.surface.append(this.marker);
    } else { this.marker = null; }
    this.updateCapability(); this.position();
  }
  updateCapability() {
    const dims = [this.left, this.right].map(item => this.loaded.get(this.source(item)));
    const same = dims.every(Boolean) && dims[0].width === dims[1].width && dims[0].height === dims[1].height;
    this.modeSelect.querySelector('option[value="wipe"]').disabled = !this.aligned || (dims.every(Boolean) && !same);
    if ((!this.aligned || (dims.every(Boolean) && !same)) && this.mode === 'wipe') {
      this.mode = 'side'; this.modeSelect.value = 'side'; this.renderSurface(); return;
    }
    this.updateScale();
    const coarse = typeof globalThis.matchMedia === 'function' ? globalThis.matchMedia('(pointer: coarse)').matches : typeof window !== 'undefined' && typeof window.matchMedia === 'function' ? window.matchMedia('(pointer: coarse)').matches : false;
    const zoomHint = coarse ? 'Pinch to zoom' : 'Scroll to zoom';
    this.hint.textContent = this.mode === 'single' ? `${zoomHint} · drag to pan · hold Space to compare` : !this.aligned ? `${zoomHint} · wipe needs confirmed alignment` : dims.every(Boolean) && !same ? `${zoomHint} · different image dimensions` : this.mode === 'wipe' ? `${zoomHint} · drag divider to compare` : `${zoomHint} · drag to pan · hold Space to compare`;
  }
  updateScale(force = false) {
    const scales = [...new Set((this.panes || []).filter(p => p.scale).map(p => Number((p.scale * 100).toFixed(2))))];
    this.fitButton.setAttribute('aria-pressed', String(this.zoom === 'fit'));
    if (force || document.activeElement !== this.zoomInput) this.zoomInput.value = scales.length === 1 ? String(scales[0]) : '';
    this.zoomInput.placeholder = scales.length > 1 ? 'Mixed' : '…';
    const scale = this.zoom === 'fit' ? `Fit${scales.length ? ` · ${scales.join('% / ')}%` : ''}` : `${Number((this.zoom * 100).toFixed(2))}% · 100% = 1 image pixel per CSS pixel`;
    const hasPreview = this.panes?.some(pane => pane.evidence === 'Preview');
    this.note.textContent = `${scale}${this.zoom !== 'fit' && hasPreview ? ' · preview pixels included' : ''}`;
  }
  setZoom(value, anchor) {
    if (value !== 'fit' && (!Number.isFinite(value) || value <= 0)) return;
    const zoom = value === 'fit' ? value : Math.max(.001, Math.min(16, value));
    this.stopDrag();
    if (zoom === 'fit') this.center = {x: .5, y: .5};
    else if (anchor?.pane.scale) {
      const {pane, x, y} = anchor, rect = pane.box.getBoundingClientRect();
      const center = this.zoom === 'fit' ? {x: .5, y: .5} : this.center;
      this.center = {
        x: center.x + (x - rect.left - rect.width / 2) / pane.img.naturalWidth * (1 / pane.scale - 1 / zoom),
        y: center.y + (y - rect.top - rect.height / 2) / pane.img.naturalHeight * (1 / pane.scale - 1 / zoom)
      };
    }
    this.zoom = zoom;
    this.surface.classList.toggle('can-pan', zoom !== 'fit');
    this.position();
  }
  paneAt(x, y, target) {
    const targetPane = this.panes.find(pane => target && pane.box.contains(target));
    if (targetPane) return targetPane;
    return this.panes.find(pane => {
      const rect = pane.box.getBoundingClientRect();
      return x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom;
    }) || this.panes[0];
  }
  beginDrag(x, y, pointerId, target) {
    const pane = this.paneAt(x, y, target);
    if (!pane?.img.naturalWidth || !pane.scale) return;
    this.drag = {pointerId, x, y, center: {...this.center}, width: pane.img.naturalWidth * pane.scale, height: pane.img.naturalHeight * pane.scale};
    this.surface.classList.add('panning');
  }
  startPinch() {
    const points = [...this.pointers.values()];
    if (points.length < 2) return;
    const [a, b] = points;
    const midpoint = {x: (a.x + b.x) / 2, y: (a.y + b.y) / 2};
    const pane = this.paneAt(midpoint.x, midpoint.y);
    if (!pane?.img.naturalWidth || !pane.scale) return;
    this.pinch = {
      distance: Math.max(1, Math.hypot(b.x - a.x, b.y - a.y)),
      zoom: pane.scale,
      center: {...this.center},
      midpoint,
      pane
    };
    this.touchScroll = null;
  }
  updatePinch() {
    if (!this.pinch || this.pointers.size < 2) return;
    const [a, b] = [...this.pointers.values()];
    const midpoint = {x: (a.x + b.x) / 2, y: (a.y + b.y) / 2};
    const distance = Math.max(1, Math.hypot(b.x - a.x, b.y - a.y));
    const {pane} = this.pinch, width = pane.img.naturalWidth, height = pane.img.naturalHeight;
    const zoom = Math.max(.001, Math.min(16, this.pinch.zoom * distance / this.pinch.distance));
    const rect = pane.box.getBoundingClientRect();
    this.center = {
      x: this.pinch.center.x + (this.pinch.midpoint.x - rect.left - rect.width / 2) / width * (1 / this.pinch.zoom - 1 / zoom) - (midpoint.x - this.pinch.midpoint.x) / (width * zoom),
      y: this.pinch.center.y + (this.pinch.midpoint.y - rect.top - rect.height / 2) / height * (1 / this.pinch.zoom - 1 / zoom) - (midpoint.y - this.pinch.midpoint.y) / (height * zoom)
    };
    this.zoom = zoom;
    this.surface.classList.add('can-pan');
    this.position();
  }
  wheel(e) {
    const pane = this.panes.find(p => p.box.contains(e.target)) || this.panes[0];
    if (!pane?.scale || !e.deltaY) return;
    e.preventDefault();
    const delta = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? pane.box.clientHeight : 1);
    this.setZoom(pane.scale * Math.exp(-Math.max(-500, Math.min(500, delta)) * .002), {pane, x: e.clientX, y: e.clientY});
  }
  position() {
    if (!this.panes) return;
    for (const pane of this.panes) {
      const w = pane.img.naturalWidth, h = pane.img.naturalHeight;
      if (!w || !h) continue;
      const width = pane.box.clientWidth, height = pane.box.clientHeight;
      const scale = this.zoom === 'fit' ? Math.min(width / w, height / h) : this.zoom;
      pane.scale = scale;
      const x = this.zoom === 'fit' ? .5 : this.center.x, y = this.zoom === 'fit' ? .5 : this.center.y;
      Object.assign(pane.img.style, {width: `${w * scale}px`, height: `${h * scale}px`, left: `${width / 2 - x * w * scale}px`, top: `${height / 2 - y * h * scale}px`});
    }
    if (this.marker && this.panes[1]) {
      // B is the full backing image; A occupies the left side of the divider.
      this.panes[0].box.style.clipPath = `inset(0 ${100 - this.division}% 0 0)`;
      const width = this.surface.clientWidth, line = width * this.division / 100;
      const handle = Math.max(22, Math.min(width - 22, line));
      this.marker.style.left = `${handle}px`;
      this.marker.style.setProperty('--line-offset', `${line - handle}px`);
      this.marker.setAttribute('aria-valuenow', String(Math.round(this.division)));
      this.marker.setAttribute('aria-valuetext', `${Math.round(this.division)}% left image`);
    }
    this.updateScale();
  }
  setDivision(value) {
    this.division = Math.max(0, Math.min(100, value));
    this.position();
  }
  dividerKeyDown(e) {
    const step = e.shiftKey ? 10 : 1;
    const values = {ArrowLeft: this.division - step, ArrowDown: this.division - step,
      ArrowRight: this.division + step, ArrowUp: this.division + step,
      PageDown: this.division - 10, PageUp: this.division + 10, Home: 0, End: 100};
    if (!(e.key in values)) return;
    e.preventDefault(); e.stopPropagation(); this.setDivision(values[e.key]);
  }
  releaseDivider(e) {
    if (e.pointerId !== this.dividerPointer) return;
    this.dividerPointer = null;
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
  }
  cancelDivider() {
    const pointerId = this.dividerPointer;
    this.dividerPointer = null;
    if (pointerId != null && this.marker?.hasPointerCapture(pointerId)) this.marker.releasePointerCapture(pointerId);
  }
  pointerDown(e) {
    if (e.target.closest('[role="slider"]')) return;
    if (e.pointerType === 'touch') {
      if (this.pointers.size >= 2) return;
      this.pointers.set(e.pointerId, {x: e.clientX, y: e.clientY});
      this.surface.setPointerCapture(e.pointerId);
      if (this.pointers.size === 2) {
        this.stopDrag(); this.startPinch();
      } else if (this.zoom === 'fit') {
        this.touchScroll = {pointerId: e.pointerId, x: e.clientX, y: e.clientY};
      } else this.beginDrag(e.clientX, e.clientY, e.pointerId, e.target);
      e.preventDefault();
      return;
    }
    if (this.zoom === 'fit' || e.button !== 0) return;
    this.beginDrag(e.clientX, e.clientY, e.pointerId, e.target);
    if (this.drag) { this.surface.setPointerCapture(e.pointerId); e.preventDefault(); }
  }
  pointerMove(e) {
    if (this.pointers.has(e.pointerId)) this.pointers.set(e.pointerId, {x: e.clientX, y: e.clientY});
    if (this.pinch && this.pointers.size >= 2) {
      this.updatePinch(); e.preventDefault(); return;
    }
    if (this.touchScroll?.pointerId === e.pointerId && this.zoom === 'fit') {
      const previous = this.touchScroll;
      const dx = e.clientX - previous.x, dy = e.clientY - previous.y;
      if (!document.fullscreenElement && Math.abs(dy) > Math.abs(dx) * .6) window.scrollBy(0, -dy);
      this.touchScroll = {pointerId: e.pointerId, x: e.clientX, y: e.clientY};
      e.preventDefault(); return;
    }
    if (!this.drag || this.drag.pointerId !== e.pointerId) return;
    this.center.x = this.drag.center.x - (e.clientX - this.drag.x) / this.drag.width;
    this.center.y = this.drag.center.y - (e.clientY - this.drag.y) / this.drag.height;
    this.position(); e.preventDefault();
  }
  pointerUp(e) {
    if (this.pointers.has(e.pointerId)) {
      this.pointers.delete(e.pointerId);
      this.touchScroll = null;
      if (this.pinch) {
        this.pinch = null;
        if (this.pointers.size === 1 && this.zoom !== 'fit') {
          const [pointerId, point] = this.pointers.entries().next().value;
          this.beginDrag(point.x, point.y, pointerId);
        } else this.stopDrag();
      } else if (this.drag?.pointerId === e.pointerId) this.stopDrag();
      return;
    }
    if (this.drag?.pointerId === e.pointerId) this.stopDrag();
  }
  resetPointers() {
    const pointerIds = [...this.pointers.keys()];
    this.pointers.clear(); this.pinch = null; this.touchScroll = null; this.stopDrag();
    for (const pointerId of pointerIds) {
      if (this.surface.hasPointerCapture(pointerId)) this.surface.releasePointerCapture(pointerId);
    }
  }
  stopDrag() { this.drag = null; this.surface.classList.remove('panning'); }
}
