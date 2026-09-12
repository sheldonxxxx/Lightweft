import {el, select, field} from '../dom.js';
import {comparison, feedback, checkboxes, heading} from './shared.js';

const tools = {
  zoom: {label: 'Zoom & detail', description: 'Check the details that carry the photograph.', checks: [['texture', 'Material texture holds up'], ['halos', 'Edges are free of distracting halos'], ['color', 'Fine colour detail stays coherent']]},
  denoise: {label: 'Denoise review', description: 'Balance quieter noise with living texture.', checks: [['noise', 'Noise is less distracting'], ['texture', 'Fine texture and faint detail survive'], ['halos', 'No smearing, ringing, or edge halos'], ['color', 'Colour remains consistent']]},
};
export function detailLab(ctx) {
  const regions = (ctx.photo.regions || []).filter(region => [ctx.left, ctx.right].every(variant => region.images?.some(image => image.variantId === variant.id)));
  let region = regions.find(item => item.id === ctx.regionId) || null;
  let tool = tools[ctx.detailTool] ? ctx.detailTool : 'zoom';
  let viewer = comparison(ctx, region);
  const mount = el('div', {}, viewer.root);
  const checklist = el('div');
  const note = el('p', {class: 'detail-explanation'});
  function updateChecks() { checklist.replaceChildren(checkboxes(ctx, tools[tool].checks)); }
  function updateNote() {
    note.textContent = region ? `${region.label}${region.width && region.height ? ` · ${region.width} × ${region.height} source region` : ''}${Number.isFinite(region.x) && Number.isFinite(region.y) ? ` · origin ${region.x}, ${region.y}` : ''}. ${region.aligned ? 'Recorded as aligned.' : 'Alignment unconfirmed; compare side by side.'}` :
      'Choose 100% to inspect available full-resolution exports. Preview-only images are labelled. Use a matched region to compare the same detail.';
  }
  const regionSelect = select('Detail region', [{value: '', label: 'Whole image'}, ...regions.map(item => ({value: item.id, label: item.label}))], region?.id || '', value => {
    region = regions.find(item => item.id === value) || null; ctx.setRegion(value); viewer.destroy(); viewer = comparison(ctx, region); mount.replaceChildren(viewer.root); updateNote();
  });
  const toolSelect = select('Inspection panel', Object.entries(tools).map(([value, spec]) => ({value, label: spec.label})), tool, value => { tool = value; ctx.setDetailTool(value); updateChecks(); });
  updateChecks(); updateNote();
  const element = el('div', {class: 'panel-layout'}, el('div', {class: 'view-column'}, heading(ctx, 'Detail lab', 'A closer look, with the whole image in mind.'),
    el('div', {class: 'detail-controls'}, field('Inspection', toolSelect), field('Matched region', regionSelect)), mount, note,
    !regions.length && el('div', {class: 'empty-inline'}, el('h3', {}, 'No matched crops for this pair yet'), el('p', {}, 'Your agent can add named regions for eyes, texture, sky, or any area that needs a closer look. Full-image zoom is available above.'))),
    el('aside', {class: 'inspector', 'aria-label': 'Detail inspection'}, el('section', {class: 'inspector-section'}, el('span', {class: 'eyebrow'}, 'Inspect & preserve'), el('h3', {}, 'Detail observations'), el('p', {class: 'muted'}, 'Record only what you have inspected. These checks stay with the selected version.'), checklist), feedback(ctx)));
  return {element, get viewer() {return viewer;}, destroy: () => viewer.destroy()};
}
