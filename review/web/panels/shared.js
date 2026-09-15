import {el, button, field, media} from '../dom.js';
import {CompareViewer} from '../compare.js';

export function source(variant, region) {
  const detail = region?.images?.find(image => image.variantId === variant.id);
  return detail ? {...variant, image: detail.image, full: null, native: region.native === true, nativeDomain: region.nativeDomain} : variant;
}
export function comparison(ctx, region) {
  return new CompareViewer({left: source(ctx.left, region), right: source(ctx.right, region),
    defaultView: ctx.right.defaultView ?? ctx.photo.defaultView,
    aligned: region ? region.aligned === true : ctx.photo.aligned === true, blind: ctx.blind, native: !!region});
}
export function checkboxes(ctx, definitions = [['overview', 'Overall photograph'], ['detail', 'Native detail']]) {
  const checks = el('div', {class: 'check-list'});
  for (const [key, label] of definitions) {
    const input = el('input', {type: 'checkbox', checked: ctx.review().checks?.[key], onChange: e => ctx.update({checks: {...ctx.review().checks, [key]: e.target.checked}})});
    checks.append(el('label', {}, input, label));
  }
  return checks;
}
export function feedback(ctx, {title = 'Your review', compact = false} = {}) {
  const current = ctx.review();
  const options = [['accepted', 'Accept'], ['revise', 'Refine'], ['rejected', 'Pass']];
  const decisions = el('div', {class: 'decision-group', role: 'group', 'aria-label': 'Your decision'});
  for (const [value, label] of options) {
    const b = button(label, () => {
      const decision = ctx.review().decision === value ? '' : value;
      ctx.update({decision});
      decisions.querySelectorAll('button').forEach(node => node.setAttribute('aria-pressed', node.dataset.value === decision ? 'true' : 'false'));
    }, {'aria-pressed': current.decision === value ? 'true' : 'false', 'data-value': value, class: value});
    decisions.append(b);
  }
  const note = el('textarea', {rows: 4, placeholder: 'What works? What should the next edit change?', 'aria-label': 'Review note', onInput: e => ctx.update({note: e.target.value})}); note.value = current.note || '';
  return el('section', {class: 'inspector-section'}, el('div', {class: 'section-heading feedback-heading'}, el('h3', {}, title), el('span', {class: 'eyebrow'}, ctx.blind ? 'Selected version' : ctx.right.label)),
    current.stale && el('p', {class: 'notice'}, 'This version changed. Review the new image before carrying forward your decision.'),
    decisions, field('Notes for the next edit', note),
    el('p', {class: 'field-hint'}, 'Your decision and notes save automatically for this version.'),
    compact && el('details', {class: 'style-checks'}, el('summary', {}, 'Inspection checks'), checkboxes(ctx)));
}
export function contextCard(ctx) {
  const qa = typeof ctx.photo.qa === 'string' ? ctx.photo.qa : ctx.photo.qa?.summary;
  const previous = ctx.photo.metadata?.historicalReview;
  const reviews = ctx.photo.metadata?.historicalReviews;
  const history = (previous || reviews?.length) && el('details', {class: 'history-details'}, el('summary', {}, 'Earlier review history'),
    el('p', {class: 'field-hint'}, 'Historical feedback. The current version has its own decision.'),
    previous && el('p', {}, [previous.decision, previous.reviewed_at && new Date(previous.reviewed_at).toLocaleDateString()].filter(Boolean).join(' · '), previous.note && el('span', {class: 'history-text'}, previous.note)),
    Array.isArray(reviews) && reviews.map(item => el('div', {class: 'history-entry'}, item.name && el('strong', {}, item.name), el('p', {class: 'history-text'}, typeof item === 'string' ? item : item.text || ''))));
  return el('section', {class: 'inspector-section context-section'}, el('span', {class: 'eyebrow'}, 'Edit intention'), el('p', {class: 'intention'}, ctx.photo.intent || 'Review the photograph’s light, colour, and sense of presence.'),
    ctx.photo.limits && el('details', {}, el('summary', {}, 'Source & edit limits'), el('p', {}, ctx.photo.limits)),
    qa && el('details', {}, el('summary', {}, 'Agent’s assessment'), el('p', {}, qa)),
    !ctx.blind && ctx.right.description && el('p', {class: 'muted'}, ctx.right.description), !ctx.blind && history);
}
export function artifacts(ctx) {
  const items = [['image', 'Review image'], ['full', 'Full resolution'], ['recipe', 'Editor recipe']];
  return el('section', {class: 'inspector-section'}, el('h3', {}, 'Files'), el('div', {class: 'artifact-links'}, items.filter(([key]) => ctx.right[key]).map(([key, label]) =>
    el('a', {href: media(ctx.right[key]), target: '_blank', rel: 'noopener'}, label, el('span', {}, '↗')))));
}
export function regionCards(ctx, onSelect) {
  const regions = ctx.photo.regions || [];
  return el('div', {class: 'region-strip'}, regions.map(region => {
    const crop = region.images?.find(item => item.variantId === ctx.right.id);
    return el('button', {type: 'button', class: 'region-card', 'aria-label': `Inspect ${region.label}`, onClick: () => onSelect(region.id)},
      crop && el('img', {src: media(crop.image), alt: '', loading: 'lazy'}), el('span', {}, region.label),
      el('small', {}, region.width && region.height ? `${region.width} × ${region.height}` : 'Detail view'));
  }));
}
export function heading(ctx) {
  return el('div', {class: 'panel-heading'}, el('h2', {}, ctx.photo.title || `Photograph ${ctx.photo.id}`));
}
