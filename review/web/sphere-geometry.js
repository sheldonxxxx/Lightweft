const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
const finite = (value, fallback) => typeof value === 'number' && Number.isFinite(value) ? value : fallback;
export function normalizeView(value = {}) {
  if (!value || typeof value !== 'object') value = {};
  return {yaw: ((finite(value.yaw, 0) + 180) % 360 + 360) % 360 - 180,
    pitch: clamp(finite(value.pitch, 0), -90, 90), hfov: clamp(finite(value.hfov, 75), 25, 120)};
}
export function isSphere(variant) { return variant?.metadata?.projection === 'equirectangular'; }
export function sphereUV(x, y, aspect, view) {
  const {yaw, pitch, hfov} = normalizeView(view), rad = Math.PI / 180;
  const scale = Math.tan(hfov * rad / 2), xx = x * scale, yy = y * scale / aspect;
  const cp = Math.cos(pitch * rad), sp = Math.sin(pitch * rad), cy = Math.cos(yaw * rad), sy = Math.sin(yaw * rad);
  const ry = yy * cp + sp, rz = cp - yy * sp;
  const rx = xx * cy + rz * sy, zz = rz * cy - xx * sy;
  return {u: ((.5 + Math.atan2(rx, zz) / (2 * Math.PI)) % 1 + 1) % 1,
    v: .5 - Math.atan2(ry, Math.hypot(rx, zz)) / Math.PI};
}
