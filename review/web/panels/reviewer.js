import {el} from '../dom.js';
import {isSphere} from '../sphere-geometry.js';
import {sphereReview} from './sphere.js';
import {comparison, feedback, contextCard, artifacts, heading, regionCards} from './shared.js';

export function reviewer(ctx) {
  if (isSphere(ctx.left) && isSphere(ctx.right)) return sphereReview(ctx);
  const viewer = comparison(ctx);
  const element = el('div', {class: 'panel-layout'},
    el('div', {class: 'view-column'}, heading(ctx, 'Photo reviewer', 'See the whole. Decide what matters.'), viewer.root,
      (ctx.photo.regions?.length > 0) && el('section', {class: 'below-view'}, el('div', {class: 'section-heading'}, el('h3', {}, 'Closer looks'), el('span', {class: 'muted'}, `${ctx.photo.regions.length} detail regions`)), regionCards(ctx, ctx.inspectRegion))),
    el('aside', {class: 'inspector', 'aria-label': 'Photo review'}, contextCard(ctx), feedback(ctx), artifacts(ctx)));
  return {element, viewer, destroy: () => viewer.destroy()};
}
