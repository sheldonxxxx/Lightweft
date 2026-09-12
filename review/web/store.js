export async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(typeof data.error === 'string' ? data.error : data.error?.message || data.message || `Request failed (${response.status})`);
    error.status = response.status; throw error;
  }
  return data;
}

export class ReviewStore extends EventTarget {
  dataset = null;
  feedback = {};
  version = 0;
  workspaceId = '';
  dirty = false;
  saving = false;
  error = null;
  recovered = null;
  timer = null;
  pending = null;
  changeNumber = 0;
  emit(type = 'status') { this.dispatchEvent(new Event(type)); }
  key() { return `lightweft-review-draft:${this.workspaceId}:${this.dataset.id}`; }
  backup() {
    try { localStorage.setItem(this.key(), JSON.stringify({ version: this.version, feedback: this.feedback })); } catch { /* Server saving remains available. */ }
  }
  preserveRecovery() {
    const recovery = this.export();
    try { localStorage.setItem(`${this.key()}:recovery`, JSON.stringify(recovery)); } catch { /* The export dialog still holds an in-memory copy. */ }
    return recovery;
  }
  async load(id) {
    if (this.dataset && this.dirty) await this.flush();
    const record = await api(`/api/datasets/${encodeURIComponent(id)}`);
    // Keep edits made while a collection request was in flight.
    if (this.dataset && this.dirty) await this.flush();
    this.setRecord(record);
    try {
      const draft = JSON.parse(localStorage.getItem(this.key()));
      if (draft?.version === this.version) { this.feedback = draft.feedback; this.dirty = true; this.emit(); this.schedule(); }
      else if (draft) this.recovered = draft;
      if (!this.recovered) this.recovered = JSON.parse(localStorage.getItem(`${this.key()}:recovery`));
    } catch { /* A malformed browser backup never replaces workspace data. */ }
    this.emit('loaded'); return record;
  }
  setRecord(record) {
    this.dataset = record.dataset; this.feedback = record.feedback || {}; this.version = record.version;
    this.workspaceId = record.workspaceId;
    this.dirty = false; this.error = null; this.recovered = null; this.changeNumber++; this.emit();
  }
  review(caseId, variantId) { return this.feedback[caseId]?.[variantId] || {}; }
  update(caseId, variantId, patch) {
    const old = this.review(caseId, variantId);
    const variant = this.dataset.cases.find(photo => photo.id === caseId)?.variants.find(item => item.id === variantId);
    this.feedback = { ...this.feedback, [caseId]: { ...this.feedback[caseId], [variantId]: { ...old, ...patch, assetRevision: variant?.assetRevision, updatedAt: new Date().toISOString() } } };
    this.changeNumber++; this.dirty = true; this.backup(); this.emit(); this.schedule();
  }
  schedule() { clearTimeout(this.timer); this.timer = setTimeout(() => this.flush().catch(() => {}), 550); }
  async flush() {
    clearTimeout(this.timer);
    if (this.pending) { await this.pending; if (this.dirty) return this.flush(); return; }
    if (!this.dirty || !this.dataset) return;
    const sequence = this.changeNumber, id = this.dataset.id;
    const feedback = structuredClone(this.feedback);
    this.saving = true; this.error = null; this.emit();
    this.pending = api(`/api/datasets/${encodeURIComponent(id)}/feedback`, {
      method: 'PUT', body: JSON.stringify({ version: this.version, feedback }),
    }).then(record => {
      this.version = record.version;
      if (sequence === this.changeNumber) {
        this.feedback = record.feedback;
        this.dataset = record.dataset;
        this.dirty = false;
        try { localStorage.removeItem(this.key()); } catch { /* Optional backup. */ }
      } else this.backup();
    }).catch(error => { this.error = error; this.backup(); throw error; })
      .finally(() => { this.saving = false; this.pending = null; this.emit(); });
    await this.pending;
    if (this.dirty) return this.flush();
  }
  async refresh() {
    if (!this.dataset || this.dirty || this.saving) return false;
    const record = await api(`/api/datasets/${encodeURIComponent(this.dataset.id)}`);
    if (this.dirty || this.saving || record.dataset.id !== this.dataset.id) return false;
    if (record.version !== this.version) { this.setRecord(record); this.emit('loaded'); return true; }
    return false;
  }
  export() { return {schemaVersion: 1, workspaceId: this.workspaceId, datasetId: this.dataset.id, version: this.version, feedback: this.feedback}; }
}
