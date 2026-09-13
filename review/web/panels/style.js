import {el, media} from '../dom.js';
import {comparison, feedback, heading} from './shared.js';

export function styleBuilder(ctx) {
  const viewer = comparison(ctx);
  const variants = el('div', {class: 'variant-grid', role: 'group', 'aria-label': 'Choose a look'}, ctx.photo.variants.map((variant, index) => el('button', {
    type: 'button', class: 'variant-card', 'aria-pressed': variant.id === ctx.right.id ? 'true' : 'false',
    onClick: () => ctx.selectCandidate(variant.id)},
    el('div', {class: 'variant-image'}, el('img', {src: media(variant.image, variant.assetRevision), alt: '', loading: 'lazy'}),
      variant.id === ctx.right.id && el('span', {class: 'selected-dot'}, '✓')),
    el('strong', {}, ctx.blind ? `Version ${index + 1}` : variant.label),
    el('small', {}, ctx.blind ? 'Explore this direction' : variant.role === 'baseline' ? 'Foundation' : variant.description || (variant.role === 'reference' ? 'Reference' : 'Style candidate')))));
  const previous = Object.entries({direction: 'Direction', keep: 'Keep', avoid: 'Avoid', scope: 'Scope'})
    .filter(([key]) => ctx.review().style?.[key]);
  const element = el('div', {class: 'panel-layout style-layout'},
    el('div', {class: 'view-column'}, heading(ctx, 'Style builder', 'Compare looks. Tell me what to refine.'), viewer.root,
      el('section', {class: 'below-view'}, el('div', {class: 'section-heading'}, el('h3', {}, 'Choose a look'),
        el('span', {class: 'muted'}, `${ctx.photo.variants.length} versions`)), variants)),
    el('aside', {class: 'inspector style-inspector', 'aria-label': 'Style feedback'},
      !ctx.blind && ctx.right.description && el('section', {class: 'inspector-section'},
        el('h3', {}, 'About this look'), el('p', {class: 'muted'}, ctx.right.description)),
      feedback(ctx, {title: 'Your feedback', compact: true}),
      previous.length > 0 && el('details', {class: 'style-history'}, el('summary', {}, 'Earlier style notes'),
        el('div', {class: 'inspector-section'}, previous.map(([key, label]) =>
          el('div', {}, el('h3', {}, label), el('p', {class: 'history-text'}, ctx.review().style[key])))))));
  return {element, viewer, destroy: () => viewer.destroy()};
}
