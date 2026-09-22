# Changelog

## Unreleased

### Workspace and documentation

- Add prerequisite checks and explicit Codex skill locations, with links to the companion's MCP setup guide and Codex host configuration.
- Present Lightweft as the central AI photo editing workspace, with independent optional RapidRAW and Insta360 AI Toolkit companions, current compatibility boundaries, and links to each project's setup.
- Add a getting-started guide for skills, the disposable review demo, and a first persistent comparison; document the ecosystem and project responsibilities.
- Refresh the repository banner and documentation navigation, and align contribution checks with the complete browser test suite.

### Public showcase and setup

- Clarify the RapidRAW MCP setup needed for agent-driven editing alongside the one-command skill install, and add a prompt for delegating setup to an AI agent.
- Make showcase photo comparisons smaller and centered while preserving the full image and usable controls.
- Refresh the README introduction and banner to explain the roles of Lightweft, RapidRAW MCP, and connected photo libraries.
- Redesign the showcase around AI workflows for studying a photo library, editing selected photos, and creating custom presets, with a growing demo directory and workflow-specific stories.
- Add four Style Builder photo demonstrations with matched base/preset comparisons, responsive images, and a guide to developing a consistent personal palette.
- Support accurate per-side comparison labels and descriptions while preserving existing nightscape comparisons.

- Prevent the showcase hero's photo count from overlapping its comparison link in shorter windows.
- Add a public photo showcase featuring two galaxy photographs selected through targeted Immich searches, with responsive before-and-after comparisons and support for future collections and photo aspect ratios.
- Add a manually triggered GitHub Pages workflow and validate approved demo JPEGs, metadata, comparison dimensions, and the site's explicit runtime files.
- Bring visitors directly to the photo comparisons, clarify Lightweft's role and photographer feedback, and improve social-preview readability.
- Document Pillow setup for contributor checks and require a product manager agent review of public-facing material.
- Present Lightweft's skills and local review app together, with companion setup linked to its owning repository.
- Link the master studies and nightscape guidance to primary artist, museum, interview, and research sources.

### Photo review

- Replace the plain collection menu with a richer selector: descriptions, disabled badges, type-to-filter search when five or more collections are visible, keyboard list navigation, loading state, and a one-click option to reveal hidden disabled collections when none are enabled.
- Remove inspection checkboxes from the standard feedback form while keeping them available in compact review panels.
- Allow review dialogs to close by clicking the background, without dismissing them when interacting with their content.
- Reduce visual clutter around photographs by removing repeated page headings, taglines, thumbnail IDs, and decorative label icons.
- Clarify first-run collection setup and JSON import errors, and open the first agent-added collection automatically when following updates.
- Add empty-search recovery, clearer reference and reviewed-version labels, and visible save status and import controls on narrow screens.
- Add a shared local review application with extensible photo, style, detail, and denoise panels, persisted feedback, and agent-readable review data.
- Add read-only Set review for explicit photo sequences, comparing common variant IDs without substituting missing looks and linking back to individual review.
- Simplify Style builder around choosing rendered looks from a wrapping card grid and leaving feedback; remove style naming and artifact-saving forms, tuck away inspection checks, and retain earlier style notes.
- Add smooth pointer-centred zoom and custom percentages, show the actual Fit scale, and keep image pixel scaling consistent without disrupting matched preview comparisons.
- Let agents choose a default single-image, side-by-side, or before/after view for each photo, with variant overrides for masks and overlays, while preserving review feedback.
- Support dragging the before/after divider over the photograph, with keyboard adjustment and independent image panning when zoomed.
- Add synchronized 360° review with seam and pole inspection, saved viewing coordinates, and guidance for judging full spheres and selected perspective photographs.
- Open confirmed 360° comparison pairs in Photo reviewer's interactive spherical viewer automatically.
- Fix photo loading and panel switching when 360 review contains a flat photograph or mask variant.
- Keep dropdowns and options in the dark theme, improve secondary text and focus visibility, and fit controls and dialogs on narrow screens.
- Allow disabling review collections to shorten the selector, with a “Show disabled” toggle and per-collection Disable/Enable control plus matching CLI commands; disabling preserves feedback and works even while a render is missing.
- Allow the review server to listen on 0.0.0.0 via `--bind` for trusted-LAN viewing from other devices, keeping loopback the default and restricting requests to the address they arrived on.
- Direct the style-builder skill to publish new edits of an already-reviewed photograph into the existing review collection as new candidates, creating a new collection only for a genuinely new study, batch, or grouping.

### Editing guidance

- Apply supported personal preferences from accepted edits and feedback to subsequent photographs, with guidance for checking whether learning transfers.
- Add collection selection and sequencing guidance, and refine wildlife tonal separation and scene lighting judgment.
- Clarify editor discretion for distraction removal and native-detail repair checks; whole-image generation and separate generated assets still require explicit permission.
- Add guidance for compact per-photo checkpoints, selective state retrieval, and continuing rendered reviews after a context reset.

- Add the photo-style-builder skill for collaborative look exploration, qualitative workspace profiles, and validated editor preset provenance.
- Separate personal style development from the master skill's image-specific editing foundation, and route ongoing review through the shared application.
- Add conditional film-emulation recommendations, a six-look selection guide with sample observations and primary sources, and optional film suggestions during image-specific edit planning.
- Preserve original photographs, sidecars, retained scene content, and source resolution during editing and cleanup.

### Collection tools

- Present RAW regression catalogues as one collection without source-cohort badges or filters, and support explicit Immich provenance in verification.
