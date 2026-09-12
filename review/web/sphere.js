import {el, button, select, media, exportJSON} from './dom.js';
import {normalizeView, isSphere} from './sphere-geometry.js';

const vertex = `attribute vec2 aPosition;
varying vec2 vPosition;
void main(){vPosition=aPosition;gl_Position=vec4(aPosition,0.,1.);}`;
const fragment = `precision highp float;
varying vec2 vPosition;
uniform sampler2D uImage;
uniform float uAspect, uTanFov, uYaw, uPitch, uWidth;
const float PI=3.141592653589793;
void main(){
  vec3 ray=vec3(vPosition.x*uTanFov,vPosition.y*uTanFov/uAspect,1.);
  float cp=cos(uPitch),sp=sin(uPitch),cy=cos(uYaw),sy=sin(uYaw);
  ray=vec3(ray.x,ray.y*cp+ray.z*sp,ray.z*cp-ray.y*sp);
  ray=vec3(ray.x*cy+ray.z*sy,ray.y,ray.z*cy-ray.x*sy);
  float longitude=fract(.5+atan(ray.x,ray.z)/(2.*PI));
  float latitude=.5-atan(ray.y,length(ray.xz))/PI;
  // Opposite-edge padding preserves bilinear continuity on non-power-of-two textures.
  vec2 uv=vec2((longitude*uWidth+1.)/(uWidth+2.),latitude);
  gl_FragColor=vec4(texture2D(uImage,uv).rgb,1.);
}`;

class SphereSurface {
  constructor(canvas, variant, changed) {
    this.canvas = canvas; this.variant = variant; this.changed = changed; this.dead = false;
    this.gl = canvas.getContext('webgl', {alpha: false, antialias: false, depth: false});
    if (!this.gl) throw new Error('360 viewing needs WebGL graphics support. The flat exports remain available in Photo reviewer.');
    const gl = this.gl;
    const shader = (type, source) => {
      const item = gl.createShader(type); gl.shaderSource(item, source); gl.compileShader(item);
      if (!gl.getShaderParameter(item, gl.COMPILE_STATUS)) {gl.deleteShader(item); throw new Error('The 360 renderer could not start.');}
      return item;
    };
    const vs = shader(gl.VERTEX_SHADER, vertex), fs = shader(gl.FRAGMENT_SHADER, fragment);
    this.program = gl.createProgram(); gl.attachShader(this.program, vs); gl.attachShader(this.program, fs); gl.linkProgram(this.program);
    gl.deleteShader(vs); gl.deleteShader(fs);
    if (!gl.getProgramParameter(this.program, gl.LINK_STATUS)) throw new Error('The 360 renderer could not initialize.');
    gl.useProgram(this.program);
    this.buffer = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]), gl.STATIC_DRAW);
    const position = gl.getAttribLocation(this.program, 'aPosition'); gl.enableVertexAttribArray(position); gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
    this.uniforms = Object.fromEntries(['uImage','uAspect','uTanFov','uYaw','uPitch','uWidth'].map(name => [name, gl.getUniformLocation(this.program, name)]));
    this.texture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, this.texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    canvas.addEventListener('webglcontextlost', event => {event.preventDefault(); this.ready = false; this.error = 'Graphics were interrupted. Reopen the 360 review panel to restore the view.'; changed();});
    this.load();
  }
  async load() {
    try {
      const image = new Image(); image.decoding = 'async'; image.src = media(this.variant.full || this.variant.image, this.variant.assetRevision);
      await image.decode(); if (this.dead) return;
      if (image.naturalWidth !== image.naturalHeight * 2) throw new Error(`The selected export is ${image.naturalWidth} × ${image.naturalHeight}; a full sphere needs exact 2:1 dimensions.`);
      const gl = this.gl, limit = Math.min(gl.getParameter(gl.MAX_TEXTURE_SIZE) - 2, 8190);
      this.width = Math.min(image.naturalWidth, Math.floor(limit / 2) * 2); const height = this.width / 2;
      const padded = document.createElement('canvas'); padded.width = this.width + 2; padded.height = height;
      const ctx = padded.getContext('2d'); ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(image, 1, 0, this.width, height);
      ctx.drawImage(padded, this.width, 0, 1, height, 0, 0, 1, height);
      ctx.drawImage(padded, 1, 0, 1, height, this.width + 1, 0, 1, height);
      gl.bindTexture(gl.TEXTURE_2D, this.texture); gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, padded);
      if (gl.getError() !== gl.NO_ERROR) throw new Error('The panorama exceeds this browser’s graphics capacity. Register a smaller review render.');
      this.size = [image.naturalWidth, image.naturalHeight]; this.scaled = image.naturalWidth !== this.width; this.ready = true; this.changed();
    } catch (error) {if (!this.dead) {this.error = error.message; this.changed();}}
  }
  render(view) {
    if (!this.ready || this.dead) return;
    const gl = this.gl, canvas = this.canvas, dpr = Math.min(devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.round(canvas.clientWidth * dpr)), height = Math.max(1, Math.round(canvas.clientHeight * dpr));
    if (canvas.width !== width || canvas.height !== height) {canvas.width = width; canvas.height = height;}
    gl.viewport(0, 0, width, height); gl.useProgram(this.program); gl.bindTexture(gl.TEXTURE_2D, this.texture);
    gl.uniform1i(this.uniforms.uImage, 0); gl.uniform1f(this.uniforms.uAspect, width / height);
    gl.uniform1f(this.uniforms.uTanFov, Math.tan(view.hfov * Math.PI / 360)); gl.uniform1f(this.uniforms.uYaw, view.yaw * Math.PI / 180);
    gl.uniform1f(this.uniforms.uPitch, view.pitch * Math.PI / 180); gl.uniform1f(this.uniforms.uWidth, this.width);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
  }
  destroy() {
    this.dead = true;
    const gl = this.gl; gl.deleteTexture(this.texture); gl.deleteBuffer(this.buffer); gl.deleteProgram(this.program);
    gl.getExtension('WEBGL_lose_context')?.loseContext();
  }
}

export class SphereViewer {
  constructor({left, right, aligned, defaultView, initialView, blind, onView}) {
    this.view = normalizeView(initialView); this.opening = {...this.view}; this.aligned = aligned; this.onView = onView;
    this.mode = ['single','side','wipe'].includes(defaultView) ? defaultView : (left.id === right.id ? 'single' : 'side');
    if (this.mode === 'wipe' && !aligned) this.mode = 'side';
    this.swapped = false; this.blink = false; this.frame = 0; this.dead = false; this.surfaces = [];
    this.status = el('p', {class: 'field-hint sphere-status', role: 'status'}, 'Loading registered full-sphere exports…');
    this.viewport = el('div', {class: 'sphere-viewport', 'data-mode': this.mode, tabIndex: 0, role: 'group', 'aria-label': '360 comparison. Drag or use arrow keys to look around. Plus and minus change field of view.'});
    this.cells = [left, right].map((variant, index) => {
      const canvas = el('canvas', {'aria-label': blind ? `Version ${index + 1}` : variant.label});
      const cell = el('div', {class: `sphere-cell sphere-cell-${index}`}, canvas,
        el('span', {class: 'sphere-label'}, blind ? `Version ${index + 1}` : variant.label));
      this.viewport.append(cell);
      if (!isSphere(variant)) {this.status.textContent = 'Select two variants registered as equirectangular panoramas, or select the same panorama twice to view it alone.'; return cell;}
      try {this.surfaces.push(new SphereSurface(canvas, variant, () => {this.updateStatus(); this.invalidate();}));}
      catch (error) {this.status.textContent = error.message;}
      return cell;
    });
    this.modeSelect = select('360 comparison mode', [{value:'single',label:'Single image'}, {value:'side',label:'Side by side'}, ...(aligned ? [{value:'wipe',label:'Before / after divider'}] : [])], this.mode, value => {this.mode = value; this.layout();});
    this.divider = el('input', {type: 'range', min: 0, max: 100, value: 50, 'aria-label': '360 comparison divider', class: 'sphere-divider', onInput: event => this.viewport.style.setProperty('--sphere-divider', `${event.target.value}%`)});
    this.fields = {};
    const angles = [['yaw', 'Yaw', -180, 180], ['pitch','Pitch',-90,90], ['hfov','Horizontal FOV',25,120]].map(([key, label, min, max]) => {
      const input = el('input', {type:'number',min,max,step:1,value:this.view[key],'aria-label':label,onChange:event => this.setView({[key]: Number(event.target.value)})});
      this.fields[key] = input; return el('label', {class:'sphere-angle'}, label, input, '°');
    });
    const positions = [['Opening view', this.opening], ['Centre', {yaw:0,pitch:0}], ['Right', {yaw:90,pitch:0}], ['Seam', {yaw:180,pitch:0}], ['Left', {yaw:-90,pitch:0}], ['Zenith', {yaw:0,pitch:90}], ['Nadir', {yaw:0,pitch:-90}]];
    this.root = el('section', {class:'sphere-viewer'}, el('div', {class:'sphere-toolbar'}, this.modeSelect,
      button('Swap sides', () => this.swap()), button('View coordinates', () => exportJSON('sphere-view.json', {...this.view, projection:'rectilinear', fovAxis:'horizontal', yawOrigin:'panorama centre', pitchPositive:'up'}, 'Reframe this angle')),
      button('Full screen', () => {if (document.fullscreenElement) document.exitFullscreen?.(); else this.root.requestFullscreen?.();})),
      this.viewport, this.divider, el('div', {class:'sphere-angles'}, angles),
      el('div', {class:'sphere-positions', role:'group','aria-label':'Sphere inspection viewpoints'}, positions.map(([label, view]) => button(label, () => this.setView(view)))), this.status,
      el('p', {class:'field-hint'}, 'Drag to explore; scroll to zoom. Yaw 0° faces the panorama centre; positive yaw turns right and positive pitch looks up. Both versions follow the same angle.'));
    this.viewport.addEventListener('pointerdown', event => {
      if (event.button !== 0) return; this.viewport.focus(); this.viewport.setPointerCapture(event.pointerId);
      this.drag = {x:event.clientX,y:event.clientY,yaw:this.view.yaw,pitch:this.view.pitch};
    });
    this.viewport.addEventListener('pointermove', event => {
      if (!this.drag) return;
      this.setView({yaw:this.drag.yaw - (event.clientX-this.drag.x)*this.view.hfov/Math.max(1,this.cells[0].clientWidth), pitch:this.drag.pitch+(event.clientY-this.drag.y)*this.view.hfov/Math.max(1,this.cells[0].clientWidth)});
    });
    for (const name of ['pointerup','pointercancel','lostpointercapture']) this.viewport.addEventListener(name, () => {this.drag = null;});
    this.viewport.addEventListener('wheel', event => {event.preventDefault(); this.setView({hfov:this.view.hfov + Math.sign(event.deltaY)*3});}, {passive:false});
    this.viewport.addEventListener('keydown', event => {
      const delta = event.shiftKey ? 15 : 3;
      const changes = {ArrowLeft:{yaw:this.view.yaw-delta}, ArrowRight:{yaw:this.view.yaw+delta}, ArrowUp:{pitch:this.view.pitch+delta}, ArrowDown:{pitch:this.view.pitch-delta}, '+':{hfov:this.view.hfov-3}, '=':{hfov:this.view.hfov-3}, '-':{hfov:this.view.hfov+3}, '0':this.opening};
      if (changes[event.key]) {event.preventDefault();event.stopPropagation();this.setView(changes[event.key]);}
    });
    this.resize = new ResizeObserver(() => this.invalidate()); this.resize.observe(this.viewport); this.layout();
  }
  setView(patch) {this.view = normalizeView({...this.view,...patch});for(const [key,input] of Object.entries(this.fields)) input.value=String(Math.round(this.view[key]*100)/100);this.onView?.(this.view);this.invalidate();}
  updateStatus() {
    const failed = this.surfaces.find(surface => surface.error);
    if (failed) {this.status.textContent = failed.error; return;}
    if (this.surfaces.length !== 2 || this.surfaces.some(surface => !surface.ready)) return;
    if (this.aligned && this.surfaces[0].size.join() !== this.surfaces[1].size.join()) {
      this.aligned = false; this.modeSelect.querySelector('option[value=wipe]')?.remove();
      if (this.mode === 'wipe') {this.mode = 'side'; this.layout();}
    }
    const size = this.surfaces.map(surface => surface.size.join(' × ')).join(' / ');
    const scaled = this.surfaces.some(surface => surface.scaled);
    this.status.textContent = `${size}. ${scaled ? 'Display reduced for graphics limits. ' : ''}Spherical projection resamples pixels; use Detail lab for native detail.${this.aligned ? '' : ' Alignment is unconfirmed; divider unavailable.'}`;
  }
  layout() {
    this.viewport.dataset.mode = this.mode; this.viewport.dataset.swap = String(this.swapped !== this.blink);
    this.divider.hidden = this.mode !== 'wipe'; this.modeSelect.value = this.mode; this.invalidate();
  }
  swap() {this.swapped = !this.swapped; this.layout();}
  setBlink(value) {this.blink = value; this.layout();}
  invalidate() {if (this.dead || this.frame) return;this.frame=requestAnimationFrame(() => {this.frame=0;for(const surface of this.surfaces) surface.render(this.view);Object.assign(this.viewport.dataset,{yaw:String(this.view.yaw),pitch:String(this.view.pitch),hfov:String(this.view.hfov)});});}
  destroy() {this.dead=true;cancelAnimationFrame(this.frame);this.resize.disconnect();for(const surface of this.surfaces) surface.destroy();}
}
