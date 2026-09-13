# Lightweft Review

A shared local workspace for reviewing AI photo edits, developing personal style, and checking detail. It displays existing renders and gives the photographer and agent a common record of candidates, feedback, and decisions. Python serves the application and stores the workspace; browser modules provide extensible review panels. No package installation or frontend build is required.

## Run locally

Use Python 3.10+ on macOS or Linux, from the repository root:

```sh
python3 review/server.py --workspace .local/review --media-root . --port 8765
```

Open `http://127.0.0.1:8765`. Keep the server running during review. `--workspace` holds local review state; `--media-root` is the directory against which image and recipe paths resolve. The server exposes only registered media and rejects paths that traverse directories or symlinks. The listener is restricted to loopback; this is a local application, not a hosted multi-user service.

The application reads browser-compatible renders. Export RAW photographs through your editor first and retain their originals and editable state. Browser display depends on the display, browser, and exported colour profile; use native exports and matched detail when judging texture or processing artifacts.

## Add a review

Create a JSON manifest with a stable dataset ID, case IDs, and variant IDs. Paths are relative to the selected media root. The paths below are placeholders for your own rendered exports:

```json
{
  "schemaVersion": 1,
  "id": "style-study",
  "title": "Personal style study",
  "description": "Explore colour while preserving the established base.",
  "cases": [
    {
      "id": "example",
      "title": "Example photograph",
      "category": "landscape",
      "intent": "Preserve depth while exploring warmer light.",
      "limits": "Fine detail must be checked in the full export.",
      "aligned": true,
      "defaultView": "wipe",
      "variants": [
        {
          "id": "base",
          "label": "Established base",
          "role": "baseline",
          "image": ".local/renders/example-base.jpg",
          "full": ".local/renders/example-base-full.jpg"
        },
        {
          "id": "warm-v1",
          "label": "Warm light",
          "role": "candidate",
          "image": ".local/renders/example-warm-v1.jpg",
          "full": ".local/renders/example-warm-v1-full.jpg",
          "description": "Warmer illuminated areas with restrained shadow colour.",
          "metadata": {
            "parentVariantId": "base",
            "editor": "Your editor",
            "editorVersion": "Your installed version"
          }
        }
      ],
      "regions": []
    }
  ]
}
```

Save your manifest in the local workspace and import it:

```sh
python3 review/cli.py import .local/style-study.json \
  --workspace .local/review --media-root . --id style-study
```

The import registers paths and metadata; it does not move, edit, or delete source photographs. Keep rendered versions at distinct paths so old decisions continue to refer to the images actually reviewed. Preserve the base and any accepted rendition when adding a new candidate.

## Review and build a style

| Page | Use it for |
| --- | --- |
| Photo reviewer | Whole-image comparisons with automatic spherical viewing for 360° pairs, edit intention and limits, user decisions, and links to available exports and recipes |
| Style builder | Choose a rendered look, compare it with the base, and leave feedback for the next iteration |
| Detail lab | Zoom and matched crop inspection, with separate detail and denoise observation checklists |
| 360 review | Synchronized spherical viewpoints, longitude seams, horizon and pole inspection |
| Set review | Read-only comparison of the same looks across an explicitly grouped sequence, with links back to individual photographs |

All pages share the same collection, selected comparison pair, and candidate feedback. Search the collection, filter by genre, format, group, or decision, and use the collection selector to move between studies. The page URL retains the collection, photograph, and review page.

The shared comparison surface includes side-by-side and single-image views, an aligned before/after divider dragged directly over the photograph, side swapping, full screen, and hidden version names. Scroll or pinch a trackpad over the photograph to zoom smoothly around the pointer, or enter a percentage from 0.1% to 1600%. Fit returns to the whole photograph and displays its actual magnification; a numeric zoom stays fixed when the viewer resizes. At 100%, one image pixel occupies one CSS pixel. Comparisons use full exports when both versions provide them; otherwise they use the review images to retain a matched comparison. Single-image mode uses the selected full export when available. Sources stay consistent across zoom levels, so leaving Fit preserves the same pixel scale; a magnified preview does not establish native detail. Drag the divider line or its centre handle to compare; at any numeric zoom, drag elsewhere on the image to pan both versions together. Focus the divider and use arrow keys for fine adjustment, Shift + arrow keys for larger steps, or Home / End to reveal either side. The divider is disabled when alignment is unconfirmed or image dimensions differ.

| Shortcut | Action |
| --- | --- |
| Left / Right arrow | Previous / next photograph |
| Hold Space | Temporarily show the other version |
| B | Swap comparison sides |
| 1 / 2 / 3 / 4 | Open Photo reviewer / Style builder / Detail lab / 360 review |
| Scroll / trackpad pinch over the photograph | Zoom around the pointer |
| Drag at any numeric zoom | Pan the compared images together |

Feedback saves automatically to the workspace, with a browser draft available if saving fails. The save status shows whether the workspace has received it. On a concurrent update, loading the newer version retains a separate recovery draft and opens the earlier feedback as JSON for reconciliation. Exports provide copy, select, and download controls so in-app browsers need not rely on downloads. “Follow agent updates” refreshes published candidates while there are no unsaved edits. Feedback can also be imported as JSON.

Use the edit reviewer to compare source or base against candidates, inspect the whole photograph, and record the gain, cost, and requested revision. Fine-detail checks belong to the same decision: a successful export or an agent's preferred candidate does not establish user acceptance.

In Style builder, select a look from the wrapping card grid below the photograph, compare it with the chosen base, and use Accept, Refine, or Pass with one feedback note. Selecting a thumbnail only changes the viewed look; it does not record acceptance. Feedback saves automatically for each version. Inspection checks are tucked into a disclosure, and any earlier structured style notes remain readable. Naming styles and saving reusable artifacts are separate from this comparison flow. Keep personal style separate from the shared [master editing philosophy](../skills/photo-edit-master/SKILL.md). Use the [style builder skill](../skills/photo-style-builder/SKILL.md) for the collaborative workflow.

When the photographer asks to retain a reusable style, the agent can save the appropriate artifact through the profile API below. Saved artifacts remain available in the Style library:

| Artifact | Meaning | Reuse |
| --- | --- | --- |
| Edit profile | Qualitative preferences tied to reviewed examples | Guides image-specific judgment across photographs |
| Editor preset | An actual recipe exported by the editor | Requires that editor's supported format and a suitable scope of adjustments |

A profile is not a set of invented slider values. A preset is not a prose description. To enable preset export, a variant needs a `recipe` path and `recipeFormat`, and should identify editor/version and validation provenance in `metadata`. The server checks that the recipe exists and snapshots its exact bytes with a SHA-256 hash. It cannot establish whether an arbitrary editor recipe is reusable: the editing agent must verify the recipe against the candidate and document its limits. Scene-specific crop, masks, retouching, and adaptive settings require a supported and validated reuse method before inclusion in a general preset. Saving a style does not itself mark the candidate accepted; keep drafts and confirmed preferences clearly described.

## Review a sequence

Set review displays the selected comparison versions across related photographs in the same collection. Each column keeps one exact variant ID throughout the set; a missing version is shown as a gap, never replaced by a different look. Images retain their full framing and load as review previews. Open an individual photograph for full-resolution comparison, detail inspection or feedback. Viewing a set does not save acceptance or change any photo decisions.

Declare each member's group and optional order and display label in case metadata:

```json
"metadata": {
  "sequenceGroup": "evening-walk",
  "sequenceOrder": 1,
  "sequenceLabel": "An evening walk"
}
```

Use a group to describe a real episode or an intentional editorial relationship. Genre and split labels do not create a sequence. Finite numeric `sequenceOrder` values sort first; ties and unspecified orders retain manifest order. The first labelled member in that order supplies the set label. Keep the same label across members and use common variant IDs such as `base`, `style-a` and `style-b`. The version selectors use the current photograph's IDs, and hidden names remain hidden in the set columns. Ungrouped photographs display a prompt to prepare a sequence.

The panel is available at `?dataset=your-collection&case=your-photo&panel=set`. It is registered alongside the existing four pages; their numeric shortcuts remain unchanged. Set conclusions can be retained in separate agent evidence while individual decisions continue through the established feedback contract.

## Review full-sphere photographs

Register each confirmed full-sphere variant with `metadata.projection: "equirectangular"`. Photo reviewer automatically opens the spherical viewer when both selected variants carry this declaration, including on direct links and when moving between photographs. Flat photographs, masks, and mixed-projection pairs use the ordinary image viewer. The dedicated 360 review page offers the same spherical controls. The spherical viewer loads the registered `full` export when present, otherwise `image`, and requires exact 2:1 decoded dimensions. A matching ratio alone does not establish a spherical projection; unstitched fisheyes and flat reframes must not carry this declaration. No image upload or separate viewer is required.

An optional `metadata.sphereView` on the case or selected candidate sets the opening `{ "yaw": 0, "pitch": 0, "hfov": 75 }`. Angles are in degrees: yaw zero points at the panorama centre, positive yaw turns right, positive pitch looks up, and `hfov` is horizontal field of view. These are image-relative coordinates, not a compass bearing. The view stays synchronized across both versions while dragging, zooming, swapping, or changing candidates. The View coordinates button exports the current angle for a reproducible rectilinear reframe.

The panel honors `defaultView` and offers single, side, and aligned divider comparisons. Differing dimensions or unconfirmed alignment disable the divider. Use the named seam, zenith, nadir, and cardinal viewpoints alongside a full horizon sweep. Inspect the seam in single-image mode or move the divider away from it; a centred divider can obscure a discontinuity. Inspection checkboxes share the selected candidate's normal feedback record. When the panorama surface has keyboard focus, arrow keys look around, Shift increases the step, plus/minus zoom, and zero returns to the opening view. Outside that surface, the normal collection shortcuts apply.

WebGL sphere viewing interpolates pixels and may reduce large exports to the browser's graphics limits. It is useful for geometry, orientation, seams, and photographic intent; native texture judgments still belong in Detail lab. The panel reads the declared projection; it does not author or validate GPano delivery metadata.

## Session and agent contract

The manifest uses `schemaVersion: 1`. Each case contains variants; each variant points to a render rather than embedding image bytes. Useful optional case fields include `category`, `split`, `format`, `intent`, `limits`, `metadata`, and `qa`. Variant roles are `baseline`, `candidate`, or `reference`; optional fields include `full`, `recipe`, `recipeFormat`, `width`, `height`, `description`, and `metadata`.

Set a case's optional `defaultView` to `single` (single image), `side` (side by side), or `wipe` (before/after divider). The agent chooses the opening view for each review: use `single` for a mask or overlay inspection, `side` for seeing both versions in full, and `wipe` for comparing aligned adjustments directly. A variant may also set `defaultView`; the selected right-hand variant takes precedence over the case default. This lets mask variants open alone within an adjustment comparison. Single-image mode displays the selected right-hand version.

These defaults apply in Photo reviewer, Style builder, and Detail lab, including matched crops. The viewer's mode selector remains available for manual changes. Defaults are applied again when opening a photo, changing the selected versions, or reopening a panel. Without a default, a single selected variant opens alone; otherwise aligned pairs open with the divider and other pairs open side by side. A requested `wipe` still falls back to `side` when alignment is unconfirmed or loaded dimensions differ. Default-view changes are presentation settings and preserve existing feedback and image revisions. Publish them through the same manifest import or versioned dataset API as other case fields.

Set `aligned: true` only when the compared images represent the same framing and registration. Equal output dimensions alone do not prove alignment. Use separate regions for pre-rendered matched crops. Each region has an `id`, `label`, source location and size (`x`, `y`, `width`, `height`), an `aligned` flag, and `images: [{"variantId": "candidate-id", "image": "relative/crop.jpg"}]`. Set `native: true` only when the crop preserves one pixel per pixel of the recorded source region. Record the source domain and any prior resizing in metadata; a one-to-one crop from a reduced render does not establish full RAW resolution.

| Endpoint | Contract |
| --- | --- |
| `GET /api/workspace` | Dataset summaries and saved profiles/presets |
| `GET /api/datasets/:id` | Current dataset, feedback, and version |
| `PUT /api/datasets/:id` | Replace a manifest with `{ "version": currentVersion, "dataset": manifest }` |
| `PUT /api/datasets/:id/feedback` | Save feedback with `{ "version": currentVersion, "feedback": feedback }` |
| `GET /api/datasets/:id/feedback/export` | Download agent-readable feedback |
| `POST /api/profiles` | Save `{ name, kind, datasetId, caseId, variantId, description, preferences, assetRevision? }`; `kind` is `profile` or `preset`; include the selected variant's revision to guard against a stale selection |
| `GET /api/profiles/:id/export` | Download a qualitative profile or the preserved recipe bytes |

Feedback is keyed by case ID and then variant ID. Entries include `decision` (`accepted`, `revise`, `rejected`, or empty), `note`, `checks`, `style`, and asset revision metadata. Style notes contain `direction`, `keep`, `avoid`, and `scope`. The decision and technical check status are independent: checks record what was inspected, not an automatic image-quality assessment. When an asset or its review context changes, earlier feedback becomes stale and its decision and checks are cleared while notes remain available.

Agents should read the current version and saved feedback before editing a manifest or preparing the next candidate. Publish a new variant for a revision, preserve accepted versions, and supply truthful provenance. On a version conflict, reread and reconcile with the latest feedback; do not blindly overwrite it. An internal agent ranking must remain distinct from the photographer's saved decision.

The CLI can read the same state while the server is running:

```sh
python3 review/cli.py list --workspace .local/review --media-root .
python3 review/cli.py show style-study --workspace .local/review --media-root .
python3 review/cli.py feedback-export style-study \
  --workspace .local/review --media-root . --output .local/feedback.json
```

`feedback-import DATASET FILE --version N` imports an exported feedback file using the current destination version returned by `show`; add the same workspace and media-root arguments. The file must name the same dataset, and stale versions are rejected. Browser collection import accepts a native manifest; use the CLI to migrate legacy formats.

Workspace data lives in `state.json`, recipe snapshots in `presets/`, and the process lock in `.lock`. Writes are atomic and dataset updates are versioned to guard against concurrent overwrites. Keep the workspace and its associated media together in your private backup process; public source contains no populated review data.

## Migrate existing helper reviews

Import existing review manifests into a named dataset and use the shared app for subsequent iterations. The importer normalises supported legacy layouts into the same case/variant/region contract. Keep historical helpers and evidence until the imported images and crops have been checked in the new application.

Supported inputs include the native schema above, a gallery manifest with case/variant `views`, a run's case-state JSON or `cases` directory, a source suite manifest with `assets`, and older HTML reviews containing an inert `galleryData` JSON payload. The HTML importer parses that payload without executing page scripts. Embedded images require byte-identical original exports in the gallery's directory tree; it does not extract new image files, and missing or changed exports stop import. Historical crop metadata remains context, with alignment unconfirmed.

Run imports retain available earlier renders and denoise experiments as additional references. Suite previews remain labelled browsing references; they are not native unedited baselines. For imported detail crops, `native: true` means the encoded image dimensions match the recorded region dimensions. `nativeDomain` and crop metadata identify that recorded-render basis; full RAW resolution is not verified. Historical review decisions remain context and do not become current approval.

If a collection moved, remap the recorded prefix explicitly. The prefixes below are placeholders, not repository locations:

```sh
python3 review/cli.py import .local/legacy-review.json \
  --workspace .local/review --media-root /absolute/path/to/current/media \
  --id migrated-study \
  --path-map /old/media/root=/absolute/path/to/current/media
```

Repeat `--path-map` for additional roots. Relative legacy paths resolve against their source manifest or run directory; use an absolute replacement when relocating a root. Required missing images stop import; optional unavailable exports and recipes are omitted and reported in the imported description. Check the imported images and crops before retiring a helper; import alone does not prove that every image is correctly matched. The inventory [workflow](../workflow/README.md) remains useful for original-file integrity and collection coverage.

## Extend and verify

Keep new specialised review views in the shared application's panel layer. Reuse dataset selection, variant identity, media access, versioned feedback, and profile export instead of building another independent helper server. Extend the schema deliberately when a new view needs persistent data, and make old manifests continue to load or provide a migration.

Register a page in the [panel registry](web/panels/index.js) with `{ id, label, icon, render }`. Its `render(context)` returns `{ element, viewer?, destroy? }`. The shell mounts `element`, routes comparison shortcuts to `viewer`, and calls `destroy` when changing pages. The [existing panels](web/panels/reviewer.js) show the pattern.

The context contains `dataset`, `photo`, `left`, `right`, and view state. `review()` reads the selected candidate's feedback; `update(patch)` queues its next save; `flush()` waits for persistence. `selectCandidate`, `inspectRegion`, `setRegion`, and `setDetailTool` connect specialised views to shared navigation. Reuse the [shared comparison and feedback helpers](web/panels/shared.js) and [comparison surface](web/compare.js) for image viewing. Keep stored inspection flags in `checks` and qualitative preferences in `style`; use a schema change for new data with different semantics.

The [server](server.py) uses the Python standard library. The [browser store](web/store.js) owns autosave, conflict state, and draft recovery. Browser code is served directly from `web/`. Review data and image paths are local state, not source fixtures. Use generated images and invented identities in tests.

Run the repository checks from its root:

```sh
python3 -m unittest discover -s tests -v
node --test review/tests/*.test.mjs
python3 scripts/check_public_repo.py --working-tree
python3 scripts/check_public_repo.py
```

The browser-state tests use Node.js 22+ and need no packages. They cover queued saves, collection-switch timing, conflicts, canonical server revisions, and workspace-isolated draft recovery. The default publication check reads the Git index; `--working-tree` checks tracked and unignored source before staging. See [contributing](../CONTRIBUTING.md) for staging and review.

For repeatable browser checks without changing photo feedback, start the [disposable fixture](tests/fixture.py):

```sh
python3 review/tests/fixture.py --port 8766
```

Open `http://127.0.0.1:8766`. It contains generated images with aligned versions, a changed frame, full exports, a detail region, an earlier reference, a sample recipe, and generated full spheres. In 360 review, inspect the seam and both poles, compare synchronized views, and export angle coordinates. Check comparison modes, native zoom and pan, disabled wipe for changed framing, and notes/decisions after reload. In Style builder, switch looks, save a decision and note, and reload to check that feedback stays with the selected version. Confirm that inspection checks expand and that the duplicate candidate selector and style-saving form are absent. In Set review, check that the changed frame precedes the landscape, missing versions leave visible gaps, hidden names stay hidden, and photo links return to Photo reviewer. The sphere is deliberately ungrouped. Profile and preset creation are covered by the server tests. Check Detail lab and a narrow viewport. Closing the fixture server removes its temporary workspace. These checks exercise the application; they do not establish the aesthetic success of a private edit or validate a RAW decoder.
