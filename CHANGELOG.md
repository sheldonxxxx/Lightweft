# Changelog

## Unreleased

### Workspace and documentation

- Present Lightweft as the central AI photo editing workspace, with independent optional RapidRAW and Insta360 AI Toolkit companions, current compatibility boundaries, and links to each project's setup.
- Add a getting-started guide for skills, the disposable review demo, and a first persistent comparison; document the ecosystem and project responsibilities.
- Refresh the repository banner and documentation navigation, and align contribution checks with the complete browser test suite.

### Photo review

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

### Editing guidance

- Add the photo-style-builder skill for collaborative look exploration, qualitative workspace profiles, and validated editor preset provenance.
- Separate personal style development from the master skill's image-specific editing foundation, and route ongoing review through the shared application.
- Add conditional film-emulation recommendations, a six-look selection guide with sample observations and primary sources, and optional film suggestions during image-specific edit planning.
- Require explicit permission before using generative image services; preserve the original scene and resolution for ordinary photo edits and local compositing.

### Collection tools

- Present RAW regression catalogues as one collection without source-cohort badges or filters, and support explicit Immich provenance in verification.
