import {el, media} from '../dom.js';
import {sequenceForPhoto, sequenceComparison, photoReviewURL} from '../sequence.js';

function photograph(ctx, row, side, index) {
  const variant = row[side], photo = row.photo;
  const frame = el('div', {class: 'set-photo-image'});
  const missing = () => frame.replaceChildren(el('span', {class: 'set-missing'}, variant ? 'Image unavailable' : 'Version not included'));
  if (!variant || variant.unavailable?.includes(variant.image)) missing();
  else frame.append(el('img', {src: media(variant.image, variant.assetRevision), alt: photo.title,
    loading: 'lazy', decoding: 'async', onError: missing}));
  return el('li', {class: 'set-photo', 'data-case': photo.id},
    el('a', {class: 'set-photo-link', href: photoReviewURL(ctx.dataset.id, photo.id),
      'aria-current': photo.id === ctx.photo.id ? 'true' : null,
      'aria-label': `Review photograph ${index + 1}: ${photo.title}`}, frame,
    el('div', {class: 'set-photo-caption'}, el('span', {class: 'set-photo-number'}, String(index + 1)),
      el('span', {}, photo.title), el('span', {class: 'set-photo-arrow', 'aria-hidden': true}, '↗'))));
}

export function setReview(ctx) {
  const sequence = sequenceForPhoto(ctx.dataset, ctx.photo);
  if (!sequence) return {element: el('section', {class: 'empty-state'},
    el('span', {class: 'eyebrow'}, 'Set review'), el('h2', {}, 'This photograph has no sequence yet.'),
    el('p', {}, 'Group related photographs from a walk, encounter or project to compare a look across them.'),
    el('a', {href: photoReviewURL(ctx.dataset.id, ctx.photo.id)}, 'Open Photo reviewer'))};

  const rows = sequenceComparison(sequence, ctx.left.id, ctx.right.id);
  const columns = ['left', 'right'].map(side => {
    const variant = ctx[side];
    const label = ctx.blind ? `Version ${ctx.photo.variants.findIndex(item => item.id === variant.id) + 1}` : variant.label;
    const missing = rows.filter(row => !row[side] || row[side].unavailable?.includes(row[side].image)).length;
    return el('section', {class: 'set-version', 'aria-label': label},
      el('header', {class: 'set-version-heading'}, el('h3', {}, label),
        el('span', {class: 'muted'}, missing ? `${missing} unavailable · ${rows.length} photographs` : `${rows.length} photographs`)),
      el('ol', {class: 'set-grid'}, rows.map((row, index) => photograph(ctx, row, side, index))));
  });
  const element = el('section', {class: 'set-review'},
    el('div', {class: 'panel-heading set-heading'},
      el('div', {}, el('span', {class: 'eyebrow'}, 'Set review'), el('h2', {}, sequence.label)),
      el('p', {}, 'See how each look carries across the same sequence.')),
    rows.length === 1 && el('p', {class: 'notice'}, 'One photograph is assigned to this set. Add neighbouring frames to assess consistency.'),
    el('div', {class: 'set-comparison'}, columns),
    el('p', {class: 'muted set-guidance'}, 'Compare the rhythm of light, colour and attention across the whole set. Open a photograph to inspect detail or leave feedback.'));
  return {element};
}
