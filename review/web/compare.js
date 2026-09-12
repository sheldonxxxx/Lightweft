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
    this.zoomSelect = select('Image magnification', [{value: 'fit', label: 'Fit to view'}, {value: '1', label: '100%'}, {value: '2', label: '200%'}, {value: '4', label: '400%'}], String(this.zoom), value => { this.zoom = value === 'fit' ? value : Number(value); this.center = {x: .5, y: .5}; this.renderSurface(); });
    const fullscreen = button('⛶', async () => {
      try { if (document.fullscreenElement) await document.exitFullscreen(); else await this.root.requestFullscreen(); }
      catch { this.note.textContent = 'Fullscreen is unavailable in this browser.'; }
    }, {class: 'icon-button', title: 'Fullscreen', 'aria-label': 'Fullscreen comparison'});
    this.toolbar = el('div', {class: 'viewer-toolbar'}, el('div', {class: 'control-group'}, this.modeSelect, this.zoomSelect),
      el('div', {class: 'control-group'}, button('⇄ Swap', () => this.swap(), {title: 'Swap sides · B'}),
        button('Center', () => { this.center = {x: .5, y: .5}; this.position(); }), fullscreen));
    this.surface = el('div', {class: 'compare-surface'});
    this.note = el('span', {}, 'Loading images…');
    this.hint = el('span', {class: 'viewer-hint'}, 'Hold Space to compare');
    this.root.append(this.toolbar, this.surface, el('div', {class: 'viewer-caption'}, this.note, this.hint));
    this.observer = new ResizeObserver(() => this.position()); this.observer.observe(this.surface);
    this.surface.addEventListener('pointerdown', e => this.pointerDown(e));
    this.surface.addEventListener('pointermove', e => this.pointerMove(e));
    this.surface.addEventListener('pointerup', () => this.stopDrag());
    this.surface.addEventListener('pointercancel', () => this.stopDrag());
    this.renderSurface();
  }
  destroy() { this.cancelDivider(); this.observer.disconnect(); }
  names() { return this.swapped ? [this.right, this.left] : [this.left, this.right]; }
  swap() { this.swapped = !this.swapped; this.renderSurface(); }
  setBlind(value) { this.blind = value; this.renderSurface(); }
  setBlink(value) {
    if (this.blink === value) return;
    this.blink = value;
    this.renderSurface();
  }
  source(item) { return this.zoom !== 'fit' && item.full ? item.full : item.image; }
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
    this.stopDrag();
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
    const scale = this.zoom === 'fit' ? 'Fit to view' : `${this.zoom * 100}% · 1 image pixel = ${this.zoom} CSS pixel${this.zoom === 1 ? '' : 's'}`;
    const hasPreview = this.panes?.some(pane => pane.evidence === 'Preview');
    this.note.textContent = `${scale}${this.zoom !== 'fit' && hasPreview ? ' · preview pixels included' : ''}`;
    this.hint.textContent = !this.aligned ? 'Wipe needs confirmed alignment' : dims.every(Boolean) && !same ? 'Different image dimensions · side by side' : this.mode === 'wipe' ? (this.zoom === 'fit' ? 'Drag the divider to compare' : 'Drag divider to compare · image to pan') : this.zoom === 'fit' ? 'Hold Space to compare' : 'Drag to pan · hold Space to compare';
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
    if (e.target.closest('[role="slider"]') || this.zoom === 'fit' || e.button !== 0) return;
    const pane = this.panes.find(p => p.box.contains(e.target)) || this.panes[0];
    if (!pane.img.naturalWidth) return;
    this.drag = {x: e.clientX, y: e.clientY, center: {...this.center}, width: pane.img.naturalWidth * pane.scale, height: pane.img.naturalHeight * pane.scale};
    this.surface.setPointerCapture(e.pointerId); this.surface.classList.add('panning'); e.preventDefault();
  }
  pointerMove(e) {
    if (!this.drag) return;
    this.center.x = Math.max(0, Math.min(1, this.drag.center.x - (e.clientX - this.drag.x) / this.drag.width));
    this.center.y = Math.max(0, Math.min(1, this.drag.center.y - (e.clientY - this.drag.y) / this.drag.height));
    this.position();
  }
  stopDrag() { this.drag = null; this.surface.classList.remove('panning'); }
}
