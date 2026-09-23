import {el, button, select, field, media, pretty, dialog, exportJSON, announce} from './dom.js';
import {ReviewStore, api} from './store.js';
import {panels} from './panels/index.js';
import {createCollectionPicker} from './collection.js';

const store = new ReviewStore();
const params = new URLSearchParams(location.search);
const ui = {workspace: {datasets: [], profiles: []}, photoId: params.get('case') || '', panel: params.get('panel') || 'review', leftId: '', rightId: '', regionId: '', detailTool: 'zoom', query: '', category: '', decision: '', format: '', split: '', blind: false, live: true, showDisabled: false};
try { ui.showDisabled = localStorage.getItem('lightweft-show-disabled') === '1'; } catch {}
let activePanel, libraryButton, collectionPicker, showDisabledControl, disabledButton, main, rail, list, saveStatus, warning, tabs, pairControls, count, summary;
let navigationButtons = [], feedbackButtons = [];
let loading = false;
const candidates = photo => photo.variants.filter(v => v.role === 'candidate');
const candidate = photo => photo.variants.find(v => v.id === photo.selectedVariantId) || candidates(photo).at(-1) || photo.variants.at(-1);
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
    const chosen = candidate(photo), decision = store.review(photo.id, chosen.id).decision, disabled = !!photo.disabled;
    const row = button('', () => choosePhoto(photo.id), {class: ['photo-row', disabled && 'is-disabled'].filter(Boolean).join(' '), 'data-case': photo.id, 'aria-current': photo.id === ui.photoId ? 'true' : 'false', 'aria-label': `${photo.title || `Photograph ${photo.id}`} · Selected version: ${chosen.label || chosen.id}${disabled ? ' (disabled)' : ''}`});
    const statusDot = el('span', {class: `status-dot ${decision || 'pending'}`, title: pretty(decision || 'pending'), 'aria-label': pretty(decision || 'pending')}, decision === 'accepted' ? '✓' : decision === 'revise' ? '↻' : '');
    row.append(el('img', {src: media(chosen.image), alt: '', loading: 'lazy'}),
      el('span', {class: 'photo-row-copy'}, el('span', {class: 'photo-row-title'}, photo.title || `Photograph ${photo.id}`), (photo.category || photo.format) && el('small', {}, pretty(photo.category || photo.format))), statusDot);
    row.insertBefore(el('span', {class: 'photo-selected-badge', title: `Selected version: ${chosen.label || chosen.id}`, 'aria-label': `Selected version: ${chosen.label || chosen.id}`}, 'Selected'), statusDot);
    if (disabled) row.insertBefore(el('span', {class: 'photo-disabled-badge', title: 'Disabled', 'aria-label': 'Disabled'}, 'Disabled'), statusDot);
    list.append(row);
  }
  if (!photos.length) list.append(el('p', {class: 'empty-list'}, 'No photographs match your filters.'));
}
function updateListStatus() {
  summary.textContent = `${reviewCount()} accepted · ${store.dataset?.cases.length || 0} total`;
  for (const row of list.querySelectorAll('.photo-row')) {
    const photo = store.dataset.cases.find(item => item.id === row.dataset.case);
    if (!photo) continue;
    const disabled = !!photo.disabled;
    row.classList.toggle('is-disabled', disabled);
    const chosen = candidate(photo);
    row.setAttribute('aria-label', `${photo.title || `Photograph ${photo.id}`} · Selected version: ${chosen.label || chosen.id}${disabled ? ' (disabled)' : ''}`);
    const selectedBadge = row.querySelector('.photo-selected-badge');
    if (selectedBadge) { selectedBadge.title = `Selected version: ${chosen.label || chosen.id}`; selectedBadge.setAttribute('aria-label', `Selected version: ${chosen.label || chosen.id}`); }
    const badge = row.querySelector('.photo-disabled-badge');
    if (disabled && !badge) row.insertBefore(el('span', {class: 'photo-disabled-badge', title: 'Disabled', 'aria-label': 'Disabled'}, 'Disabled'), row.querySelector('.status-dot'));
    if (!disabled) badge?.remove();
    const decision = store.review(photo.id, candidate(photo).id).decision || 'pending';
    const dot = row.querySelector('.status-dot');
    dot.className = `status-dot ${decision}`; dot.title = pretty(decision); dot.setAttribute('aria-label', pretty(decision));
    dot.textContent = decision === 'accepted' ? '✓' : decision === 'revise' ? '↻' : '';
  }
}
function applyFilters() { normalizeSelection(); renderList(); renderPanel(); }
function clearFilters() {
  ui.query = ''; ui.category = ''; ui.decision = ''; ui.format = ''; ui.split = '';
  document.querySelector('#search').value = '';
  renderFilters(); applyFilters();
  document.querySelector('#search').focus();
}
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
  tabs.replaceChildren(...panels.map(panel => button(panel.label, () => {ui.panel = panel.id; ui.regionId = ''; renderTabs(); renderPanel();}, {class: 'page-tab', role: 'tab', 'aria-selected': panel.id === ui.panel ? 'true' : 'false', 'aria-controls': 'main', id: `tab-${panel.id}`, tabIndex: panel.id === ui.panel ? '0' : '-1'})));
}
function renderPanel() {
  activePanel?.destroy?.(); activePanel = null; main.replaceChildren(); pairControls.replaceChildren();
  const photo = currentPhoto();
  navigationButtons.forEach(node => {node.disabled = filters().length < 2;});
  feedbackButtons.forEach(node => {node.disabled = !store.dataset;});
  document.querySelector('#search').disabled = !store.dataset;
  if (!photo) {
    const filtered = !!store.dataset?.cases.length;
    main.append(el('div', {class: 'empty-state'},
      el('h2', {}, filtered ? 'No photographs match' : 'Start your first photo review'),
      el('p', {}, filtered ? 'Clear your search and filters to see the collection again.' : 'Compare exports from your editor and leave feedback for the next edit. Ask your agent to add them here, or import a collection JSON file.'),
      button(filtered ? 'Clear filters' : 'Add a collection', filtered ? clearFilters : importCollection, {class: 'primary'})));
    return;
  }
  const left = photo.variants.find(v => v.id === ui.leftId), right = photo.variants.find(v => v.id === ui.rightId);
  const pairFields = ui.panel === 'style' ? [['leftId', 'Reference']] : ui.panel === 'set' ? [['leftId', 'First'], ['rightId', 'Second']] : [['leftId', 'Reference'], ['rightId', 'Reviewing']];
  for (const [key, label] of pairFields) pairControls.append(field(label,
    select(`${label} version`, photo.variants.map((v, index) => ({value: v.id, label: ui.blind ? `Version ${index + 1}` : v.label})), ui[key], value => {ui[key] = value; renderPanel();})));
  const blindButton = button(ui.blind ? 'Reveal names' : 'Hide names', () => {ui.blind = !ui.blind; renderPanel();}, {'aria-label': ui.blind ? 'Reveal names' : 'Hide names', 'aria-pressed': ui.blind ? 'true' : 'false', class: 'blind-button', title: 'Hide version names for a less biased comparison'});
  pairControls.append(blindButton);
  const panel = panels.find(item => item.id === ui.panel) || panels[0]; ui.panel = panel.id;
  main.setAttribute('aria-labelledby', `tab-${panel.id}`);
  const ctx = {dataset: store.dataset, photo, left, right, blind: ui.blind, regionId: ui.regionId, detailTool: ui.detailTool,
    review: () => store.review(photo.id, right.id), update: patch => store.update(photo.id, right.id, patch), flush: () => store.flush(), refreshLibrary,
    selectCandidate: id => {ui.rightId = id; renderPanel();}, inspectRegion: id => {ui.panel = 'detail'; ui.regionId = id; renderTabs(); renderPanel();},
    setPhotoDisabled: disabled => setPhotoDisabled(disabled),
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
  collectionPicker.setLocked(true);
  main.inert = true; main.setAttribute('aria-busy', 'true'); pairControls.inert = true;
  try { await store.load(id); ui.query = ''; ui.category = ''; ui.decision = ''; ui.format = ''; ui.split = ''; document.querySelector('#search').value = ''; renderFilters(); normalizeSelection(); renderList(); renderPanel(); announce(`Opened collection “${store.dataset.title}”.`); }
  catch (error) { catchError(error); }
  finally {loading = false; renderCollectionOptions(); main.inert = false; main.removeAttribute('aria-busy'); pairControls.inert = false;}
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
function chooseJSON(onFile, onError = catchError) {
  const input = el('input', {type: 'file', accept: '.json,application/json'});
  input.addEventListener('change', async () => {
    try { if (input.files[0]) await onFile(JSON.parse(await input.files[0].text())); }
    catch (error) {onError(error);}
  }); input.click();
}
function importCollection() {
  const errorText = el('p', {class: 'notice', role: 'alert', hidden: true});
  const content = el('div', {class: 'setup-content'},
    el('p', {}, 'A collection groups photographs and their rendered versions. Your image files stay on this computer.'),
    el('h3', {}, 'Ask your agent'),
    el('p', {}, 'Tell your agent which base render and edited versions to compare, then ask: “Add these exports to my Lightweft review workspace.” Close this message and keep the viewer open while your agent prepares the collection.'),
    el('h3', {}, 'Already have a collection file?'),
    el('p', {}, 'Choose the collection JSON prepared by your agent or the review setup guide. It lists existing image files; photographs and RAW files cannot be imported directly.'),
    el('details', {}, el('summary', {}, 'Preparing a collection yourself'),
      el('p', {}, 'Follow “Add a review” in review/README.md in your Lightweft checkout. Image paths are relative to the server’s --media-root folder, not the JSON file. Export RAW files as JPEG, PNG, or WebP first.')),
    errorText);
  const modal = dialog('Add a review collection', content, button('Choose collection JSON', () => {
    errorText.hidden = true;
    chooseJSON(async data => {
      const dataset = data?.dataset || data;
      if (!dataset || typeof dataset.id !== 'string' || !Array.isArray(dataset.cases)) throw new Error('Choose a collection JSON with an ID and photographs. A feedback export or editor recipe cannot be used here.');
      await store.flush();
      if (ui.workspace.datasets.some(item => item.id === dataset.id)) throw new Error('That collection already exists. Ask your agent to update it, or use a new collection ID.');
      await api(`/api/datasets/${encodeURIComponent(dataset.id)}`, {method: 'PUT', body: JSON.stringify({dataset, version: 0})});
      await refreshLibrary(); await loadDataset(dataset.id); modal.close();
    }, error => {errorText.textContent = error.message; errorText.hidden = false;});
  }, {class: 'primary'}));
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
function visibleDatasets() {
  return ui.workspace.datasets.filter(item => !item.disabled || ui.showDisabled || (store.dataset && item.id === store.dataset.id));
}
function renderCollectionOptions() {
  if (!collectionPicker) return;
  const visible = visibleDatasets();
  const hiddenCount = ui.workspace.datasets.length - visible.length;
  collectionPicker.render(visible, store.dataset?.id || '', {
    empty: ui.workspace.datasets.length ? 'No enabled collections.' : 'No collections yet.',
    loading,
    canRevealHidden: hiddenCount > 0 && !ui.showDisabled,
  });
  if (showDisabledControl) {
    const input = showDisabledControl.querySelector('input');
    if (input) input.checked = ui.showDisabled;
    const label = showDisabledControl.querySelector('span');
    if (label) label.textContent = hiddenCount && !ui.showDisabled ? `Show disabled (${hiddenCount})` : 'Show disabled';
  }
  updateDisabledButton();
}
function updateDisabledButton() {
  if (!disabledButton) return;
  const disabled = !!store.dataset?.disabled;
  disabledButton.textContent = disabled ? 'Enable' : 'Disable';
  disabledButton.title = disabled ? 'Enable this collection in the selector' : 'Disable this collection in the selector';
  disabledButton.setAttribute('aria-label', disabled ? 'Enable this collection' : 'Disable this collection');
  disabledButton.disabled = !store.dataset;
}
async function setCurrentDisabled(disabled) {
  if (!store.dataset || loading) return;
  loading = true; collectionPicker.setLocked(true); disabledButton.disabled = true;
  try {
    await store.flush();
    const updated = await api(`/api/datasets/${encodeURIComponent(store.dataset.id)}/disabled`, {method: 'PUT', body: JSON.stringify({disabled, version: store.version})});
    store.setRecord(updated); store.emit('loaded');
    await refreshLibrary();
    announce(disabled ? 'Collection disabled. It is hidden unless “Show disabled” is on.' : 'Collection enabled.');
  } catch (error) { catchError(error); }
  finally { loading = false; renderCollectionOptions(); }
}
async function setPhotoDisabled(disabled) {
  if (!store.dataset || !currentPhoto() || loading) return;
  const photo = currentPhoto();
  loading = true; collectionPicker.setLocked(true);
  try {
    await store.flush();
    const updated = await api(`/api/datasets/${encodeURIComponent(store.dataset.id)}/cases/${encodeURIComponent(photo.id)}/disabled`, {method: 'PUT', body: JSON.stringify({disabled, version: store.version})});
    store.setRecord(updated); store.emit('loaded');
    announce(disabled ? 'Photograph disabled. It remains visible in grey.' : 'Photograph enabled.');
  } catch (error) { catchError(error); }
  finally { loading = false; renderCollectionOptions(); }
}
async function refreshLibrary() {
  ui.workspace = await api('/api/workspace');
  renderCollectionOptions();
  if (libraryButton) libraryButton.textContent = `Style library${ui.workspace.profiles.length ? ` · ${ui.workspace.profiles.length}` : ''}`;
}
async function showLibrary() {
  try { await refreshLibrary(); } catch (error) {catchError(error); return;}
  const content = el('div', {class: 'library-grid'});
  if (!ui.workspace.profiles.length) content.append(el('div', {class: 'empty-inline'}, el('h3', {}, 'Keep the looks you want to use again'), el('p', {}, 'Choose a look and leave feedback in Style builder. Then ask your agent to save your reviewed preferences as an edit profile, or a supported editor recipe as a preset. Saved styles appear here.')));
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
    [['← / →', 'Previous / next photograph'], ['Space (hold)', 'Temporarily show the other version'], ['B', 'Swap the comparison sides'], ['1 / 2 / 3 / 4', 'Reviewer / Style builder / Detail lab / 360 review'], ['Scroll / pinch', 'Zoom around the pointer'], ['Drag', 'Pan both images together at any numeric zoom']].map(([key, description]) => el('p', {}, el('kbd', {}, key), el('span', {}, description)))));
}
function buildShell() {
  saveStatus = el('span', {class: 'save-status', role: 'status'}, 'Connecting…');
  libraryButton = button('Style library', showLibrary, {class: 'library-button', 'aria-label': 'Style library'});
  collectionPicker = createCollectionPicker({
    onSelect: loadDataset,
    onShowDisabled: () => {
      ui.showDisabled = true;
      try { localStorage.setItem('lightweft-show-disabled', '1'); } catch {}
      renderCollectionOptions();
      announce('Disabled collections are now shown.');
    },
  });
  disabledButton = button('Disable', () => setCurrentDisabled(!store.dataset?.disabled), {class: 'collection-action-button', title: 'Disable this collection in the selector'});
  showDisabledControl = el('label', {class: 'live-control'}, el('input', {type: 'checkbox', checked: ui.showDisabled, onChange: e => { ui.showDisabled = e.target.checked; try { localStorage.setItem('lightweft-show-disabled', ui.showDisabled ? '1' : '0'); } catch {} renderCollectionOptions(); }}), el('span', {}, 'Show disabled'));
  const top = el('header', {class: 'topbar'}, el('a', {class: 'brand', href: '/'}, el('img', {src: '/icon.svg', alt: '', width: 30, height: 30}), el('span', {}, 'lightweft')),
    el('div', {class: 'workspace-switch'}, el('span', {class: 'eyebrow'}, 'Workspace collection'), el('div', {class: 'workspace-collection-row'}, collectionPicker.element, disabledButton), showDisabledControl),
    el('div', {class: 'top-actions'}, saveStatus, libraryButton, button('?', shortcuts, {class: 'icon-button', 'aria-label': 'Keyboard shortcuts'})));
  count = el('span', {}); summary = el('small', {});
  list = el('nav', {class: 'photo-list', 'aria-label': 'Photographs'});
  rail = el('aside', {class: 'collection-rail'}, el('div', {class: 'rail-heading'}, el('span', {class: 'eyebrow'}, 'The collection'), button('Import', importCollection, {class: 'import-button', 'aria-label': 'Import collection'})),
    el('input', {id: 'search', type: 'search', placeholder: 'Find a photograph…', 'aria-label': 'Search photographs', onInput: e => {ui.query = e.target.value; applyFilters();}}),
    el('div', {id: 'facets', class: 'filter-grid'}), el('div', {class: 'collection-count'}, count, summary), list,
    el('footer', {class: 'rail-footer'}, el('div', {class: 'rail-footer-actions'}, button('Import', importCollection, {class: 'mobile-import', 'aria-label': 'Import collection'}), feedbackButtons = [button('Export feedback', exportFeedback), button('Import feedback', importFeedback)]),
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
  const work = el('div', {class: 'work-area'}, el('div', {class: 'work-toolbar'}, tabs, el('div', {class: 'navigation'}, navigationButtons = [button('←', () => navigate(-1), {'aria-label': 'Previous photograph', class: 'icon-button'}), button('→', () => navigate(1), {'aria-label': 'Next photograph', class: 'icon-button'})])), warning, pairControls, main);
  document.querySelector('#app').replaceChildren(top, el('div', {class: 'studio'}, rail, work)); renderTabs();
}
store.addEventListener('status', status);
store.addEventListener('loaded', () => {
  renderCollectionOptions();
  normalizeSelection(); if (store.dataset) renderFilters(); renderList(); renderPanel();
  if (store.recovered) { warning.replaceChildren(el('span', {}, 'An earlier browser draft is available for recovery.'), button('Export older draft', () => exportJSON(`${store.dataset.id}-older-draft.json`, {schemaVersion: 1, workspaceId: store.workspaceId, datasetId: store.dataset.id, ...store.recovered}))); warning.hidden = false; }
});
document.addEventListener('keydown', event => {
  if (document.querySelector('dialog[open]') || event.altKey || event.ctrlKey || event.metaKey || event.target.closest('input,textarea,select,[role="slider"],[contenteditable="true"],.collection-picker')) return;
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
  const requested = params.get('dataset');
  const enabled = ui.workspace.datasets.filter(item => !item.disabled);
  const fallback = (enabled[0] || ui.workspace.datasets[0])?.id;
  const id = ui.workspace.datasets.some(item => item.id === requested) ? requested : fallback;
  if (id) await loadDataset(id); else {renderPanel(); saveStatus.textContent = 'Local workspace';}
} catch (error) {catchError(error); renderPanel();}
setInterval(async () => {
  if (!ui.live || loading || document.hidden || document.querySelector('dialog[open]') || store.dirty || store.saving) return;
  try {
    await refreshLibrary();
    if (!store.dataset) {
      const enabled = ui.workspace.datasets.filter(item => !item.disabled);
      const next = (enabled[0] || visibleDatasets()[0])?.id;
      if (next) await loadDataset(next);
    }
    else if (await store.refresh()) announce('The collection was updated.');
  } catch { /* Preserve the current review while disconnected. */ }
}, 10000);
