#!/usr/bin/env python3
"""Build the portable RAW catalogue and coverage report from the current manifest."""
import argparse
import shutil
from urllib.parse import urlsplit
from collections import Counter
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def e(value):
    return escape(str(value if value is not None else 'Unknown'), quote=True)


def build(root):
    root = Path(root).resolve()
    m = json.loads((root / 'manifest.json').read_text())
    assets = m['assets']; n = len(assets)
    formats = Counter(a['original']['format'] for a in assets)
    origins = Counter(a['origin'] for a in assets)
    categories = Counter(a['category'] for a in assets)
    cameras = Counter(a['metadata'].get('camera', {}).get('model') or 'Unknown' for a in assets)
    tags = Counter(t for a in assets for t in set(a['tags']))
    groups = len({a['group_id'] for a in assets})
    total_bytes = sum(a['original']['byte_size'] for a in assets)
    smoke_ids = [a['id'] for a in assets if a.get('smoke_subset')]
    cards = []
    for a in assets:
        original = a['original']; md = a['metadata']; preview = a['preview']
        source = a.get('source_url') or original['path']
        if a.get('source_url') and urlsplit(source).scheme not in {'https', 'http'}:
            raise ValueError('Source URL must use HTTP or HTTPS')
        source_label = 'Open in Immich ↗' if a.get('source_url') else 'Open local RAW ↗'
        origin_label = 'Immich' if a['origin'] == 'v2' else 'Local'
        details = ' · '.join(str(v) for v in [md.get('camera', {}).get('model'), original['format'], f"ISO {md['iso']}" if md.get('iso') else None] if v)
        search = ' '.join(str(v) for v in [a['id'], original['filename'], a['reason'], a.get('capture_date'), details, *a['tags']]).lower()
        chips = ''.join(f'<span class="tag">{e(t.replace("_", " "))}</span>' for t in a['tags'])
        smoke = '<span class="smoke">SMOKE</span>' if a.get('smoke_subset') else ''
        previous = f'<dt>Historical split</dt><dd>{e(a["previous_split"])}; now exposed regression material</dd>' if a.get('previous_split') else ''
        limits = ''.join(f'<p class="source-note">{e(note)}</p>' for note in a.get('input_limitations', []))
        cards.append(f'''<article class="card" data-id="{e(a['id'])}" data-origin="{e(a['origin'])}" data-tags="{e('|'.join(a['tags']))}" data-search="{e(search)}" data-smoke="{str(bool(a.get('smoke_subset'))).lower()}" data-format="{e(original['format'])}">
<a class="photo" href="{e(source)}" target="_blank" rel="noopener"><img src="{e(preview['path'])}" alt="{e(a['reason'])}" loading="lazy"><span class="open">{source_label}</span></a>
<div class="body"><div class="identity"><h2>{e(a['id'])}</h2><span class="split development">{origin_label}</span>{smoke}</div><p class="reason">{e(a['reason'])}</p><div class="tags">{chips}</div><p class="original-link"><a href="{e(original['path'])}" download>Original {original['format']} ↓</a><span>{e(details)}</span></p>
<details><summary>Source &amp; provenance</summary><dl><dt>Filename</dt><dd>{e(original['filename'])}</dd><dt>Capture date</dt><dd>{e(a.get('capture_date'))}</dd><dt>Capture group</dt><dd>{e(a['group_id'])}</dd><dt>Dimensions</dt><dd>{e(md.get('width'))} × {e(md.get('height'))}</dd><dt>Original size</dt><dd>{original['byte_size']:,} bytes</dd><dt>SHA-256</dt><dd class="mono">{original['sha256']}</dd><dt>Source verification</dt><dd>{e(original['verification'])}</dd>{previous}</dl>{limits}<p class="source-note">{e(preview['kind'])}. Preview only; use the linked RAW for editing. This case has prior development or review exposure.</p></details></div></article>''')
    options = lambda values: ''.join(f'<option value="{e(v)}">{e(v.replace("_", " "))} · {c}</option>' for v,c in sorted(values.items()))
    css = (ROOT / 'catalogue.css').read_text()
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Photo Edit Test Suite · RAW</title><style>{css}
.original-link{{display:flex;flex-direction:column;gap:5px;font-size:12px}}.original-link a{{font-weight:700}}.original-link span{{color:var(--muted)}}.stats{{grid-template-columns:repeat(4,1fr)}}@media(max-width:630px){{.stats{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><div class="shell"><header><div class="topline"><div class="eyebrow">Local RAW regression suite</div></div><div class="intro"><div><h1>One collection.<br>RAW inputs.</h1><p class="subtitle">{n} photographs for developing and checking photo edits. Bring your own originals and previews; keep this catalogue private.</p><div class="stats"><div class="stat"><b>{n}</b><span>RAW photographs</span></div><div class="stat"><b>{formats['CR3']}</b><span>Canon CR3</span></div><div class="stat"><b>{formats['DNG']}</b><span>DNG inputs</span></div><div class="stat"><b>0</b><span>fresh holdouts</span></div></div></div><div><aside class="notice"><strong>All original inputs verified.</strong><p>{total_bytes / 1_000_000_000:.2f} GB of source files, checked by size and SHA-256. These {n} cases have prior development or review exposure. JPEG images on the cards are browsing previews of RAW inputs.</p></aside><nav class="resources" aria-label="Suite resources"><a href="coverage.md">Coverage &amp; gaps</a><a href="manifest.json">Manifest JSON</a><a href="evaluation-template.json">Evaluation template</a></nav></div></div></header><main><noscript>All {n} photographs are visible. Enable JavaScript to filter.</noscript><form class="controls" id="filters"><label class="search">Search cases<input id="search" type="search" placeholder="Subject, filename or case ID" autocomplete="off"></label><label>Origin<select id="origin"><option value="">All cases</option>{options(origins)}</select></label><label>Coverage<select id="tag"><option value="">All labels</option>{options(tags)}</select></label><label>Format<select id="format"><option value="">All RAW formats</option>{options(formats)}</select></label><label class="checkbox"><input type="checkbox" id="smoke">Smoke subset · {len(smoke_ids)}</label><button type="reset">Reset</button></form><p class="results" id="results" aria-live="polite">Showing all {n} photographs</p><section class="grid" id="grid" aria-label="Selected photographs">{''.join(cards)}</section><div class="empty" id="empty">No cases match. Try fewer filters.</div></main><footer><p>All cases are development/regression material. Select new, unexposed capture groups for an independent evaluation.</p><p>Recorded review exposure does not establish a fresh benchmark or user acceptance.</p><p>Portable local catalogue · source files preserved byte-for-byte · no remote library changes</p></footer></div>
<script>const form=document.querySelector('#filters'),cards=[...document.querySelectorAll('.card')];function filter(){{const q=document.querySelector('#search').value.trim().toLowerCase(),origin=document.querySelector('#origin').value,tag=document.querySelector('#tag').value,format=document.querySelector('#format').value,smoke=document.querySelector('#smoke').checked;let n=0;for(const card of cards){{const show=(!q||q.split(/\\s+/).every(word=>card.dataset.search.includes(word)))&&(!origin||card.dataset.origin===origin)&&(!tag||card.dataset.tags.split('|').includes(tag))&&(!format||card.dataset.format===format)&&(!smoke||card.dataset.smoke==='true');card.hidden=!show;if(show)n++}}document.querySelector('#results').textContent=`Showing ${{n}} of ${{cards.length}} photographs`;document.querySelector('#empty').style.display=n?'none':'block'}}form.addEventListener('input',filter);form.addEventListener('change',filter);form.addEventListener('submit',e=>e.preventDefault());form.addEventListener('reset',()=>setTimeout(filter,0));</script></body></html>'''
    template = root / 'evaluation-template.json'
    if not template.exists():
        shutil.copyfile(ROOT / 'evaluation-template.json', template)
    (root / 'catalogue.html').write_text(html)
    table = lambda title,values: title + '\n\n| Value | Cases |\n|---|---:|\n' + '\n'.join(f'| {key} | {count} |' for key,count in sorted(values.items()))
    coverage = f'''# RAW regression coverage

**{n} originals: {formats['CR3']} CR3 and {formats['DNG']} DNG.**
All cases are exposed development/regression material. There are no fresh holdouts.

There are {groups} recorded capture groups. File counts do not establish independent scenes.

{table('## Subject categories', categories)}

{table('## Cameras', cameras)}

{table('## Formats', formats)}

{table('## Overlapping coverage labels', tags)}

## Limits

- Source files total **{total_bytes:,} bytes**. Run the verifier after building the catalogue.
- Smoke subset: **{', '.join(smoke_ids) or 'None selected'}**.
- Labels and capture groups are supplied by the collection author, not inferred by these tools.
- DNG can contain computational processing; the extension does not establish capture history.
- Hash checks, container signatures and catalogue links do not measure image quality or RAW decodability.
- Review rendered edits separately; record findings in the evaluation template.
'''
    (root / 'coverage.md').write_text(coverage)
    print(f'Built {n} catalogue cards; {dict(origins)}; RAW smoke subset {smoke_ids}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite-dir', type=Path, required=True)
    args = parser.parse_args()
    build(args.suite_dir)
