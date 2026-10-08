/** Pinned notes: a note attached to a point on the photograph, in image-relative coordinates. */
export const MAX_PINS = 200;

/** Normalised (0-1) image coordinates of a pointer position, or null when outside the image. */
export function imagePoint(rect, clientX, clientY) {
  if (!rect.width || !rect.height) return null;
  const x = (clientX - rect.left) / rect.width, y = (clientY - rect.top) / rect.height;
  return x >= 0 && x <= 1 && y >= 0 && y <= 1 ? {x: round(x), y: round(y)} : null;
}
const round = value => Math.round(value * 1e5) / 1e5;

export function createPin({x, y, zoom, compareWith}, id = globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`) {
  const pin = {id, x, y, note: '', createdAt: new Date().toISOString()};
  if (Number.isFinite(zoom) && zoom > 0) pin.zoom = round(zoom);
  if (compareWith?.length) pin.compareWith = [...compareWith];
  return pin;
}

/** Marker offset inside the pane for an image drawn at (left, top) with the given pixel size. */
export function markerOffset(pin, {left, top, width, height}) {
  return {left: left + pin.x * width, top: top + pin.y * height};
}

/** View that shows the pinned point: its recorded magnification, or 100% when it was pinned at Fit. */
export function viewFor(pin) {
  return {zoom: pin.zoom ?? 1, center: {x: pin.x, y: pin.y}};
}

export const withoutPin = (pins, id) => pins.filter(pin => pin.id !== id);
export const withNote = (pins, id, note) => pins.map(pin => pin.id === id ? {...pin, note} : pin);
