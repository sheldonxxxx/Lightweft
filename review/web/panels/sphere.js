import {el} from '../dom.js';
import {SphereViewer} from '../sphere.js';
import {isSphere} from '../sphere-geometry.js';
import {feedback, contextCard, artifacts, heading, checkboxes} from './shared.js';

const views = new Map();
export function sphereReview(ctx) {
  const key = `${ctx.dataset.id}:${ctx.photo.id}`;
  const hasSphere = isSphere(ctx.left) && isSphere(ctx.right);
  const viewer = hasSphere ? new SphereViewer({left:ctx.left, right:ctx.right, aligned:ctx.photo.aligned === true,
    defaultView:ctx.right.defaultView ?? ctx.photo.defaultView, blind:ctx.blind,
    initialView:views.get(key) ?? ctx.right.metadata?.sphereView ?? ctx.photo.metadata?.sphereView,
    onView:view => views.set(key, {...view})}) : null;
  const element = el('div', {class:'panel-layout'},
    el('div', {class:'view-column'}, heading(ctx),
      viewer ? viewer.root : el('p', {class:'empty-panel'}, 'Choose panorama variants marked as equirectangular. A flat reframe belongs in Photo reviewer; a 2:1 ratio alone does not establish a full sphere.')),
    el('aside', {class:'inspector','aria-label':'360 photo review'}, contextCard(ctx),
      hasSphere && el('section', {class:'inspector-section'}, el('h3', {}, 'Sphere inspection'), checkboxes(ctx, [['sphereSeam','Longitude seam'],['sphereHorizon','Horizon around the sphere'],['sphereZenith','Zenith'],['sphereNadir','Nadir'],['sphereNearObjects','Near objects and stitching']])), feedback(ctx), artifacts(ctx)));
  return {element, viewer:viewer || undefined, destroy:() => viewer?.destroy()};
}
