import {reviewer} from './reviewer.js';
import {styleBuilder} from './style.js';
import {detailLab} from './detail.js';
import {sphereReview} from './sphere.js';
import {setReview} from './set.js';

// New pages share one context, persistence layer, and comparison surface.
// render(context) returns { element, viewer?, destroy? }.
export const panels = [
  {id: 'review', label: 'Photo reviewer', icon: '◫', render: reviewer},
  {id: 'style', label: 'Style builder', icon: '◈', render: styleBuilder},
  {id: 'detail', label: 'Detail lab', icon: '⌕', render: detailLab},
  {id: 'sphere', label: '360 review', icon: '◎', render: sphereReview},
  {id: 'set', label: 'Set review', icon: '▦', render: setReview},
];
