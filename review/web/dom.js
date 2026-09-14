export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value == null || value === false) continue;
    if (key.startsWith('on')) node.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key === 'checked' || key === 'disabled' || key === 'hidden') node[key] = !!value;
    else node.setAttribute(key, value === true ? '' : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child != null && child !== false) node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}
export const button = (text, onClick, attrs = {}) => el('button', { type: 'button', onClick, ...attrs }, text);
export const media = (path, revision) => `/api/media?path=${encodeURIComponent(path)}${revision ? `&revision=${encodeURIComponent(revision)}` : ''}`;
export const pretty = value => String(value || '').replaceAll('_', ' ').replaceAll('-', ' ');
export function select(label, options, value, onChange, attrs = {}) {
  const input = el('select', { 'aria-label': label, onChange: e => onChange(e.target.value), ...attrs },
    options.map(option => el('option', { value: option.value }, option.label)));
  input.value = value;
  return input;
}
export function field(label, input, hint) {
  return el('label', { class: 'field' }, el('span', { class: 'field-label' }, label), input,
    hint && el('span', { class: 'field-hint' }, hint));
}
export function download(name, data) {
  const url = URL.createObjectURL(new Blob([typeof data === 'string' ? data : JSON.stringify(data, null, 2)], {type: 'application/json'}));
  const link = el('a', { href: url, download: name });
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function exportJSON(name, data, title = 'Export feedback') {
  const text = JSON.stringify(data, null, 2);
  const area = el('textarea', {rows: 15, readOnly: true, class: 'json-export', 'aria-label': 'Export JSON'}); area.value = text;
  const status = el('p', {class: 'field-hint', role: 'status'}, 'Copy this record for your agent, or save it as a JSON file.');
  const actions = el('div', {class: 'export-actions'}, button('Select JSON', () => {area.focus(); area.select();}),
    button('Copy JSON', async () => {
      try {await navigator.clipboard.writeText(text); status.textContent = 'JSON copied.';}
      catch {area.focus(); area.select(); status.textContent = 'JSON selected. Use your browser’s Copy command.';}
    }), button('Download JSON', () => download(name, text), {class: 'primary'}));
  return dialog(title, el('div', {class: 'export-content'}, status, area), actions);
}
export function announce(message) { document.querySelector('#announcer').textContent = message; }
export function dialog(title, content, footer) {
  const node = el('dialog', { class: 'dialog', 'aria-label': title },
    el('header', {}, el('h2', {}, title), button('×', () => node.close(), {class: 'icon-button', 'aria-label': 'Close dialog'})), content,
    footer && el('footer', {}, footer));
  let startedOnBackdrop = false;
  const isBackdrop = event => {
    const bounds = node.getBoundingClientRect();
    return event.target === node && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom);
  };
  node.addEventListener('pointerdown', event => {startedOnBackdrop = event.button === 0 && isBackdrop(event);});
  node.addEventListener('pointercancel', () => {startedOnBackdrop = false;});
  node.addEventListener('click', event => {
    const dismiss = startedOnBackdrop && isBackdrop(event);
    startedOnBackdrop = false;
    if (dismiss) node.close();
  });
  node.addEventListener('close', () => node.remove());
  document.body.append(node); node.showModal(); return node;
}
