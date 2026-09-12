import {reviewer} from './reviewer.js';
import {styleBuilder} from './style.js';
import {detailLab} from './detail.js';

// New pages share one context, persistence layer, and comparison surface.
// render(context) returns { element, viewer?, destroy? }.
export const panels = [
  {id: 'review', label: 'Photo reviewer', icon: '◫', render: reviewer},
  {id: 'style', label: 'Style builder', icon: '◈', render: styleBuilder},
  {id: 'detail', label: 'Detail lab', icon: '⌕', render: detailLab},
];
