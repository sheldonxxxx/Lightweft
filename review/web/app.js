import {el, button, select, field, media, pretty, dialog, exportJSON, announce} from './dom.js';
import {ReviewStore, api} from './store.js';
import {panels} from './panels/index.js';

const store = new ReviewStore();
const params = new URLSearchParams(location.search);
const ui = {workspace: {datasets: [], profiles: []}, photoId: params.get('case') || '', panel: params.get('panel') || 'review', leftId: '', rightId: '', regionId: '', detailTool: 'zoom', query: '', category: '', decision: '', format: '', split: '', blind: false, live: true};
let activePanel, libraryButton, collectionSelect, main, rail, list, saveStatus, warning, tabs, pairControls, count, summary;
let loading = false;
const candidates = photo => photo.variants.filter(v => v.role === 'candidate');
const candidate = photo => candidates(photo).at(-1) || photo.variants.at(-1);
const currentPhoto = () => store.dataset?.cases.find(photo => photo.id === ui.photoId);
const reviewCount = () => store.dataset?.cases.filter(photo => Object.values(store.feedback[photo.id] || {}).some(item => item.decision === 'accepted')).length || 0;

function catchError(error) { showWarning(error.message); }
function showWarning(message) { warning.replaceChildren(el('span', {}, message)); warning.hidden = false; }
function updateURL() {
  const query = new URLSearchParams({dataset: store.dataset.id, case: ui.photoId, panel: ui.panel});
  history.replaceState(null, '', `?${query}`);
}
function filters() {
  if (!store.dataset) return [];
  return store.dataset.cases.filter(photo => {
    const text = [photo.id, photo.title, photo.category, photo.intent, photo.format].join(' ').toLowerCase();
    const decision = store.review(photo.id, candidate(photo).id).decision || 'pending';
    return (!ui.query || ui.query.toLowerCase().split(/\s+/).every(word => text.includes(word))) && (!ui.category || photo.category === ui.category) && (!ui.decision || decision === ui.decision)
      && (!ui.format || photo.format === ui.format) && (!ui.split || photo.split === ui.split);
  });
}
function normalizeSelection() {
  const photos = filters();
  if (!photos.some(photo => photo.id === ui.photoId)) ui.photoId = photos[0]?.id || '';
  const photo = currentPhoto();
  if (!photo) return;
  if (!photo.variants.some(v => v.id === ui.leftId)) ui.leftId = (photo.variants.find(v => v.role === 'baseline') || photo.variants[0]).id;
  if (!photo.variants.some(v => v.id === ui.rightId)) ui.rightId = candidate(photo).id;
}
function renderList() {
  const photos = filters(); list.replaceChildren();
  count.textContent = `${photos.length} photograph${photos.length === 1 ? '' : 's'}`;
  summary.textContent = `${reviewCount()} accepted · ${store.dataset?.cases.length || 0} total`;
  for (const photo of photos) {
    const chosen = candidate(photo), decision = store.review(photo.id, chosen.id).decision;
    const row = button('', () => choosePhoto(photo.id), {class: 'photo-row', 'data-case': photo.id, 'aria-current': photo.id === ui.photoId ? 'true' : 'false', 'aria-label': photo.title || `Photograph ${photo.id}`});
    row.append(el('img', {src: media(chosen.image), alt: '', loading: 'lazy'}),
      el('span', {class: 'photo-row-copy'}, el('span', {class: 'photo-row-title'}, photo.title || `Photograph ${photo.id}`), el('small', {}, `${photo.id} · ${pretty(photo.category || photo.format || 'Photo')}`)),
      el('span', {class: `status-dot ${decision || 'pending'}`, title: pretty(decision || 'pending'), 'aria-label': pretty(decision || 'pending')}, decision === 'accepted' ? '✓' : decision === 'revise' ? '↻' : ''));
    list.append(row);
  }
  if (!photos.length) list.append(el('p', {class: 'empty-list'}, 'No photographs match your filters.'));
}
function updateListStatus() {
  summary.textContent = `${reviewCount()} accepted · ${store.dataset?.cases.length || 0} total`;
  for (const row of list.querySelectorAll('.photo-row')) {
    const photo = store.dataset.cases.find(item => item.id === row.dataset.case);
    if (!photo) continue;
    const decision = store.review(photo.id, candidate(photo).id).decision || 'pending';
    const dot = row.querySelector('.status-dot');
    dot.className = `status-dot ${decision}`; dot.title = pretty(decision); dot.setAttribute('aria-label', pretty(decision));
    dot.textContent = decision === 'accepted' ? '✓' : decision === 'revise' ? '↻' : '';
  }
}
function applyFilters() { normalizeSelection(); renderList(); renderPanel(); }
function renderFilters() {
  const mount = document.querySelector('#facets'); mount.replaceChildren();
  for (const [key, label] of [['category', 'Genre'], ['format', 'Format'], ['split', 'Group']]) {
    const values = [...new Set(store.dataset.cases.map(photo => photo[key]).filter(Boolean))].sort();
    if (values.length < 2) {ui[key] = ''; continue;}
    mount.append(select(label, [{value: '', label: `All ${key === 'category' ? 'genres' : key === 'format' ? 'formats' : 'groups'}`}, ...values.map(value => ({value, label: pretty(value)}))], ui[key], value => {ui[key] = value; applyFilters();}));
  }
  mount.append(select('Review status', [{value: '', label: 'All decisions'}, {value: 'pending', label: 'Unreviewed'}, {value: 'accepted', label: 'Accepted'}, {value: 'revise', label: 'Needs refinement'}, {value: 'rejected', label: 'Passed'}], ui.decision, value => {ui.decision = value; applyFilters();}));
}
function renderTabs() {
  tabs.replaceChildren(...panels.map(panel => button(`${panel.icon}  ${panel.label}`, () => {ui.panel = panel.id; ui.regionId = ''; renderTabs(); renderPanel();}, {class: 'page-tab', role: 'tab', 'aria-selected': panel.id === ui.panel ? 'true' : 'false', 'aria-controls': 'main', id: `tab-${panel.id}`, tabIndex: panel.id === ui.panel ? '0' : '-1'})));
}
function renderPanel() {
  activePanel?.destroy?.(); activePanel = null; main.replaceChildren(); pairControls.replaceChildren();
  const photo = currentPhoto();
  if (!photo) { main.append(el('div', {class: 'empty-state'}, el('span', {class: 'empty-symbol'}, '◫'), el('h2', {}, 'A little more room to look.'), el('p', {}, store.dataset ? 'Adjust the filters to bring your photographs back into view.' : 'Add a review collection to begin. Your agent can bring in previous reviews, style candidates, and detail comparisons.'), button('Import collection', importCollection, {class: 'primary'}))); return; }
  const left = photo.variants.find(v => v.id === ui.leftId), right = photo.variants.find(v => v.id === ui.rightId);
  for (const [key, label] of [['leftId', 'Compare'], ['rightId', 'With']]) pairControls.append(field(label,
    select(`${label} version`, photo.variants.map((v, index) => ({value: v.id, label: ui.blind ? `Version ${index + 1}` : v.label})), ui[key], value => {ui[key] = value; renderPanel();})));
  const blindButton = button(ui.blind ? '◉ Reveal names' : '◎ Hide names', () => {ui.blind = !ui.blind; renderPanel();}, {'aria-label': ui.blind ? 'Reveal names' : 'Hide names', 'aria-pressed': ui.blind ? 'true' : 'false', class: 'blind-button', title: 'Hide version names for a less biased comparison'});
  pairControls.append(blindButton);
  const panel = panels.find(item => item.id === ui.panel) || panels[0]; ui.panel = panel.id;
  main.setAttribute('aria-labelledby', `tab-${panel.id}`);
  const ctx = {dataset: store.dataset, photo, left, right, blind: ui.blind, regionId: ui.regionId, detailTool: ui.detailTool,
    review: () => store.review(photo.id, right.id), update: patch => store.update(photo.id, right.id, patch), flush: () => store.flush(), refreshLibrary,
    selectCandidate: id => {ui.rightId = id; renderPanel();}, inspectRegion: id => {ui.panel = 'detail'; ui.regionId = id; renderTabs(); renderPanel();},
    setRegion: id => {ui.regionId = id;}, setDetailTool: value => {ui.detailTool = value;}};
  activePanel = panel.render(ctx); main.append(activePanel.element); updateURL();
}
function choosePhoto(id) { ui.photoId = id; ui.leftId = ''; ui.rightId = ''; ui.regionId = ''; normalizeSelection(); renderList(); renderPanel(); }
function navigate(direction) {
  const photos = filters(); if (!photos.length) return;
  const index = photos.findIndex(photo => photo.id === ui.photoId);
  choosePhoto(photos[(index + direction + photos.length) % photos.length].id);
}
async function loadDataset(id) {
  if (loading) return; loading = true;
  collectionSelect.disabled = true;
  main.inert = true; main.setAttribute('aria-busy', 'true'); pairControls.inert = true;
  try { await store.load(id); ui.query = ''; ui.category = ''; ui.decision = ''; ui.format = ''; ui.split = ''; document.querySelector('#search').value = ''; renderFilters(); normalizeSelection(); renderList(); renderPanel(); collectionSelect.value = id; }
  catch (error) { catchError(error); if (store.dataset) collectionSelect.value = store.dataset.id; }
  finally {loading = false; collectionSelect.disabled = !ui.workspace.datasets.length; main.inert = false; main.removeAttribute('aria-busy'); pairControls.inert = false;}
}
function status() {
  saveStatus.textContent = store.error ? 'Save needs attention' : store.saving ? 'Saving…' : store.dirty ? 'Unsaved changes' : 'Saved to workspace';
  saveStatus.classList.toggle('has-error', !!store.error);
  if (store.error) {
    const conflict = store.error.status === 409;
    warning.replaceChildren(el('span', {}, conflict ? 'The collection changed in another session. Your feedback is kept here; export it before loading the new version.' : `Feedback is still in this browser. ${store.error.message}`),
      button('Export my feedback', exportFeedback),
      conflict ? button('Load workspace version', async () => {
        const recovery = store.preserveRecovery();
        exportJSON(`${store.dataset.id}-unsaved-feedback.json`, recovery, 'Your earlier feedback is preserved');
        try {const data = await api(`/api/datasets/${encodeURIComponent(store.dataset.id)}`); try {localStorage.removeItem(store.key());} catch {} store.setRecord(data); store.recovered = recovery; store.emit(); normalizeSelection(); renderList(); renderPanel();} catch (error) {catchError(error);}
      }) : button('Retry save', () => store.flush().catch(catchError)));
    warning.hidden = false;
  } else if (store.recovered) {
    warning.replaceChildren(el('span', {}, 'An earlier browser draft is available for recovery.'), button('Export older draft', () => exportJSON(`${store.dataset.id}-older-draft.json`, {schemaVersion: 1, workspaceId: store.workspaceId, datasetId: store.dataset.id, ...store.recovered})));
    warning.hidden = false;
  } else warning.hidden = true;
  if (store.dataset) updateListStatus();
}
function exportFeedback() { if (store.dataset) exportJSON(`${store.dataset.id}-feedback.json`, store.export()); }
function chooseJSON(onFile) {
  const input = el('input', {type: 'file', accept: '.json,application/json'});
  input.addEventListener('change', async () => {
    try { if (input.files[0]) await onFile(JSON.parse(await input.files[0].text())); }
    catch (error) {catchError(error);}
  }); input.click();
}
function importCollection() {
  chooseJSON(async data => {
    await store.flush(); const dataset = data.dataset || data;
    if (ui.workspace.datasets.some(item => item.id === dataset.id)) throw new Error('That collection already exists. Ask your agent to publish a versioned update, or import with a new ID.');
    await api(`/api/datasets/${encodeURIComponent(dataset.id)}`, {method: 'PUT', body: JSON.stringify({dataset, version: 0})});
    await refreshLibrary(); await loadDataset(dataset.id);
  });
}
function importFeedback() {
  if (!store.dataset) return;
  chooseJSON(async data => {
    await store.flush();
    if ((data.workspaceId && data.workspaceId !== store.workspaceId) || data.datasetId !== store.dataset.id || data.version !== store.version) throw new Error('This feedback belongs to a different workspace, collection, or revision. Ask your agent to reconcile it with the current candidates.');
    const feedback = data.feedback;
    if (!feedback || typeof feedback !== 'object' || Array.isArray(feedback)) throw new Error('No valid feedback was found in this file.');
    // The server validates every case and candidate before replacing feedback.
    const record = await api(`/api/datasets/${encodeURIComponent(store.dataset.id)}/feedback`, {method: 'PUT', body: JSON.stringify({version: store.version, feedback})});
    store.setRecord(record); renderList(); renderPanel(); announce('Feedback imported.');
  });
}
async function refreshLibrary() {
  ui.workspace = await api('/api/workspace');
  if (collectionSelect) {
    collectionSelect.replaceChildren(...ui.workspace.datasets.map(item => el('option', {value: item.id}, item.title)));
    collectionSelect.value = store.dataset?.id || ui.workspace.datasets[0]?.id || '';
    collectionSelect.disabled = !ui.workspace.datasets.length;
  }
  if (libraryButton) libraryButton.textContent = `◈ Style library${ui.workspace.profiles.length ? ` · ${ui.workspace.profiles.length}` : ''}`;
}
async function showLibrary() {
  try { await refreshLibrary(); } catch (error) {catchError(error); return;}
  const content = el('div', {class: 'library-grid'});
  if (!ui.workspace.profiles.length) content.append(el('div', {class: 'empty-inline'}, el('h3', {}, 'Your style, collected over time.'), el('p', {}, 'Save a visual profile or an editor preset from the Style builder. They will be available here and to your agent.')));
  for (const profile of ui.workspace.profiles) {
    content.append(el('article', {class: 'library-card'}, el('span', {class: 'eyebrow'}, profile.kind === 'preset' ? 'Editor preset' : 'Edit profile'), el('h3', {}, profile.name),
      profile.description && el('p', {}, profile.description),
      el('dl', {}, Object.entries(profile.preferences || {}).filter(([, value]) => value).map(([key, value]) => [el('dt', {}, pretty(key)), el('dd', {}, value)])),
      el('a', {class: 'button-link', href: `/api/profiles/${encodeURIComponent(profile.id)}/export`, download: ''}, profile.kind === 'preset' ? 'Download recipe ↓' : 'Download profile ↓')));
  }
  dialog('Your style library', content);
}
function shortcuts() {
  dialog('A few useful shortcuts', el('div', {class: 'shortcut-list'},
    [['← / →', 'Previous / next photograph'], ['Space (hold)', 'Temporarily show the other version'], ['B', 'Swap the comparison sides'], ['1 / 2 / 3 / 4', 'Reviewer / Style builder / Detail lab / 360 review'], ['Drag', 'Pan both images together at 100% or above']].map(([key, description]) => el('p', {}, el('kbd', {}, key), el('span', {}, description)))));
}
function buildShell() {
  saveStatus = el('span', {class: 'save-status', role: 'status'}, 'Connecting…');
  libraryButton = button('◈ Style library', showLibrary, {class: 'library-button', 'aria-label': 'Style library'});
  collectionSelect = select('Review collection', [], '', loadDataset, {class: 'collection-select'});
  const top = el('header', {class: 'topbar'}, el('a', {class: 'brand', href: '/'}, el('img', {src: '/icon.svg', alt: '', width: 30, height: 30}), el('span', {}, 'lightweft', el('small', {}, 'REVIEW STUDIO'))),
    el('div', {class: 'workspace-switch'}, el('span', {class: 'eyebrow'}, 'Workspace collection'), collectionSelect),
    el('div', {class: 'top-actions'}, saveStatus, libraryButton, button('?', shortcuts, {class: 'icon-button', 'aria-label': 'Keyboard shortcuts'})));
  count = el('span', {}); summary = el('small', {});
  list = el('nav', {class: 'photo-list', 'aria-label': 'Photographs'});
  rail = el('aside', {class: 'collection-rail'}, el('div', {class: 'rail-heading'}, el('span', {class: 'eyebrow'}, 'The collection'), button('+', importCollection, {class: 'icon-button', 'aria-label': 'Import collection'})),
    el('input', {id: 'search', type: 'search', placeholder: 'Find a photograph…', 'aria-label': 'Search photographs', onInput: e => {ui.query = e.target.value; applyFilters();}}),
    el('div', {id: 'facets', class: 'filter-grid'}), el('div', {class: 'collection-count'}, count, summary), list,
    el('footer', {class: 'rail-footer'}, el('div', {class: 'rail-footer-actions'}, button('Export feedback', exportFeedback), button('Import feedback', importFeedback)),
      el('label', {class: 'live-control'}, el('input', {type: 'checkbox', checked: ui.live, onChange: e => {ui.live = e.target.checked;}}), 'Follow agent updates'),
      el('span', {class: 'field-hint'}, 'Feedback and styles stay in this workspace.')));
  tabs = el('nav', {class: 'page-tabs', role: 'tablist', 'aria-label': 'Review tools'});
  tabs.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    event.stopPropagation(); event.preventDefault(); const index = panels.findIndex(p => p.id === ui.panel);
    ui.panel = panels[(index + (event.key === 'ArrowRight' ? 1 : panels.length - 1)) % panels.length].id;
    renderTabs(); renderPanel(); tabs.querySelector('[aria-selected="true"]').focus();
  });
  pairControls = el('div', {class: 'pair-controls'});
  warning = el('div', {class: 'warning-banner', role: 'alert', hidden: true});
  main = el('main', {id: 'main', tabIndex: '-1', role: 'tabpanel'});
  const work = el('div', {class: 'work-area'}, el('div', {class: 'work-toolbar'}, tabs, el('div', {class: 'navigation'}, button('←', () => navigate(-1), {'aria-label': 'Previous photograph', class: 'icon-button'}), button('→', () => navigate(1), {'aria-label': 'Next photograph', class: 'icon-button'}))), warning, pairControls, main);
  document.querySelector('#app').replaceChildren(top, el('div', {class: 'studio'}, rail, work)); renderTabs();
}
store.addEventListener('status', status);
store.addEventListener('loaded', () => {
  normalizeSelection(); if (store.dataset) renderFilters(); renderList(); renderPanel();
  if (store.recovered) { warning.replaceChildren(el('span', {}, 'An earlier browser draft is available for recovery.'), button('Export older draft', () => exportJSON(`${store.dataset.id}-older-draft.json`, {schemaVersion: 1, workspaceId: store.workspaceId, datasetId: store.dataset.id, ...store.recovered}))); warning.hidden = false; }
});
document.addEventListener('keydown', event => {
  if (document.querySelector('dialog[open]') || event.altKey || event.ctrlKey || event.metaKey || event.target.closest('input,textarea,select,[role="slider"],[contenteditable="true"]')) return;
  if (event.code === 'Space' && !event.target.closest('button,a')) {event.preventDefault(); activePanel?.viewer?.setBlink(true);}
  if (event.key === 'ArrowRight') {event.preventDefault(); navigate(1);}
  if (event.key === 'ArrowLeft') {event.preventDefault(); navigate(-1);}
  if (event.key.toLowerCase() === 'b') activePanel?.viewer?.swap();
  if (['1', '2', '3', '4'].includes(event.key)) {ui.panel = panels[Number(event.key) - 1].id; renderTabs(); renderPanel();}
});
document.addEventListener('keyup', event => {if (event.code === 'Space') activePanel?.viewer?.setBlink(false);});
window.addEventListener('blur', () => activePanel?.viewer?.setBlink(false));
window.addEventListener('beforeunload', event => {if (store.dirty) {event.preventDefault(); event.returnValue = '';}});
buildShell();
try {
  await refreshLibrary();
  const requested = params.get('dataset'), id = ui.workspace.datasets.some(item => item.id === requested) ? requested : ui.workspace.datasets[0]?.id;
  if (id) await loadDataset(id); else {renderPanel(); saveStatus.textContent = 'Local workspace';}
} catch (error) {catchError(error); renderPanel();}
setInterval(async () => {
  if (!ui.live || loading || document.hidden || document.querySelector('dialog[open]') || store.dirty || store.saving) return;
  try {await refreshLibrary(); if (await store.refresh()) announce('The collection was updated.');} catch { /* Preserve the current review while disconnected. */ }
}, 10000);
