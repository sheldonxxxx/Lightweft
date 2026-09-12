import {el, button, field, media, announce} from '../dom.js';
import {api} from '../store.js';
import {comparison, feedback, heading} from './shared.js';

export function styleBuilder(ctx) {
  const viewer = comparison(ctx);
  const preferences = ['direction', 'keep', 'avoid', 'scope'];
  const labels = {direction: 'The feeling to pursue', keep: 'Qualities to keep', avoid: 'What to avoid', scope: 'Where this style belongs'};
  const placeholders = {direction: 'Quiet warmth, deep greens, soft light…', keep: 'Natural skin, atmospheric distance…', avoid: 'Crushed shadows, brittle texture…', scope: 'Woodland scenes in soft daylight…'};
  const form = el('div', {class: 'style-form'});
  for (const key of preferences) {
    const input = el('textarea', {rows: 2, placeholder: placeholders[key], onInput: e => ctx.update({style: {...ctx.review().style, [key]: e.target.value}})});
    input.value = ctx.review().style?.[key] || '';
    form.append(field(labels[key], input));
  }
  const name = el('input', {type: 'text', placeholder: 'Give this style a name', maxlength: 120, 'aria-label': 'Style name', onInput: e => ctx.update({style: {...ctx.review().style, name: e.target.value}})});
  name.value = ctx.review().style?.name || '';
  const status = el('p', {class: 'form-status', role: 'status'});
  const profileButton = button('Save edit profile', () => save('profile'), {class: 'primary'});
  const presetButton = button('Save editor preset', () => save('preset'), {disabled: !ctx.right.recipe || !ctx.right.recipeFormat});
  async function save(kind) {
    if (!name.value.trim()) { status.textContent = 'Give your style a name first.'; name.focus(); return; }
    profileButton.disabled = true; presetButton.disabled = true; status.textContent = 'Saving your style…';
    try {
      await ctx.flush();
      await api('/api/profiles', {method: 'POST', body: JSON.stringify({name: name.value.trim(), kind, datasetId: ctx.dataset.id, caseId: ctx.photo.id, variantId: ctx.right.id, assetRevision: ctx.right.assetRevision,
        description: ctx.review().style?.direction || '', preferences: Object.fromEntries(preferences.map(key => [key, ctx.review().style?.[key] || '']))})});
      status.textContent = `${kind === 'preset' ? 'Preset' : 'Edit profile'} saved to your workspace library.`;
      announce(status.textContent); await ctx.refreshLibrary();
    } catch (error) { status.textContent = error.message; }
    finally { profileButton.disabled = false; presetButton.disabled = !ctx.right.recipe || !ctx.right.recipeFormat; }
  }
  const variants = el('div', {class: 'variant-grid'}, ctx.photo.variants.map((variant, index) => el('button', {type: 'button', class: 'variant-card', 'aria-pressed': variant.id === ctx.right.id ? 'true' : 'false', onClick: () => ctx.selectCandidate(variant.id)},
    el('div', {class: 'variant-image'}, el('img', {src: media(variant.image), alt: '', loading: 'lazy'}), variant.id === ctx.right.id && el('span', {class: 'selected-dot'}, '✓')),
    el('strong', {}, ctx.blind ? `Version ${index + 1}` : variant.label), el('small', {}, ctx.blind ? 'Explore this direction' : variant.role === 'baseline' ? 'Foundation' : variant.description || (variant.role === 'reference' ? 'Reference' : 'Style candidate')))));
  const element = el('div', {class: 'panel-layout'},
    el('div', {class: 'view-column'}, heading(ctx, 'Style builder', 'A good foundation. A direction of your own.'), viewer.root,
      el('section', {class: 'below-view'}, el('div', {class: 'section-heading'}, el('h3', {}, 'Explore the directions'), el('span', {class: 'muted'}, `${ctx.photo.variants.length} versions`)), variants)),
    el('aside', {class: 'inspector', 'aria-label': 'Style preferences'}, el('section', {class: 'inspector-section'}, el('span', {class: 'eyebrow'}, 'Your visual language'), el('h3', {}, 'Shape the next iteration'), el('p', {class: 'muted'}, 'Describe what you respond to. Your agent can use these notes to make the next candidates.'), form),
      el('section', {class: 'inspector-section'}, el('h3', {}, 'Make it yours'), field('Style name', name), el('div', {class: 'save-style-actions'}, profileButton, presetButton),
        el('p', {class: 'field-hint'}, 'An edit profile carries your visual preferences between photographs. A preset preserves this version’s editor recipe; check its reuse limits in your editor.'),
        (!ctx.right.recipe || !ctx.right.recipeFormat) && el('p', {class: 'field-hint'}, 'An editor recipe and its format are needed to save a preset.'), status), feedback(ctx)));
  return {element, viewer, destroy: () => viewer.destroy()};
}
