# AI photo editing workflow

## Project boundaries

Lightweft is the central workspace for artistic direction, personal style, and rendered photo review. RapidRAW and Insta360 AI Toolkit are independent, optional companion projects with their own setup, licenses, and verification records. Keep their application-specific instructions in their respective repositories; link to them from Lightweft. Changes in a companion checkout belong to that repository, not the root Git history. Describe available capabilities separately from the ecosystem's future direction.

## Editing integration

You are authorized to make any changes to RapidRAW and its MCP integration that you judge necessary to improve the AI photo editing workflow. This includes changes to the RapidRAW application, MCP tools, and supporting workflow code. Proceed with these improvements without asking for separate permission for each change.

## Image generation and photographic cleanup

- Ask for explicit permission before generating or recreating a whole image with ChatGPT ImageGen, or generating a separate image asset such as a sticker. This rule is separate from the editor's discretion to remove distractions through inpainting.
- Distraction removal is a core editing responsibility. Decide what to remove, subdue, crop out, or retain to make the strongest photograph; do not wait for the user to name distractions or approve cleanup separately. Respect explicit keep instructions and preserve context that strengthens the subject or story. Prefer generative inpainting through the established RapidRAW/ComfyUI connector whenever suitable and available.
- Fall back to local inpainting when the connector is unavailable, unsuitable, or produces an inferior repair. Inspect the complete repair and retained subject boundaries at native resolution for seams, residual shapes, smeared texture, and damage to feathers, fur, or perches. Restore the better reference if the repair fails; a plausible small preview is insufficient.
- Preserve original photographs and sidecars, retained scene content, and source resolution. Keep reconstruction confined to the intended cleanup and record its method in the saved edit.

## Shared review workspace

- Use the [shared review application](review/README.md) for ongoing photo, style, denoise, and detail reviews. Publish rendered candidates through its manifest/API/CLI contract; extend its panel registry when a new inspection needs a specialised view.
- Choose `defaultView` for each review case: `single` for mask visualisations, or `side` / `wipe` for adjustment comparisons according to the inspection. Use variant overrides when mask renders and photo edits share a case.
- Keep review state, photographs, and personal style artifacts in the user's ignored workspace. Preserve historical review evidence, but do not create new standalone helper websites for workflows the shared app can handle.
- The master editing skill supplies an image-specific foundation. Use [photo-style-builder](skills/photo-style-builder/SKILL.md) for collaborative personal style exploration, with profiles and actual editor recipes kept separate from shared philosophy.

## Storage discipline

- Measure physical free space on the output volume before and after large batches. Reserve at least 20 GiB before starting benchmark or bulk-render runs; estimate unique output sizes as well as input sizes.
- Reuse verified model assets through the companion editor's model cache, on the same volume as the workspaces for clone savings. Keep isolated workspaces, but use independent filesystem clones for large local fixture and source copies where supported. Do not use hard links for editable photographs or replace review assets with symlinks.
- Reuse a build target for the same toolchain and configuration. Prefer non-incremental builds without debug symbols for validation; opt into larger development caches only when needed.
- Keep accepted edits, recipes, original sources, review decisions, and reproducibility manifests. Prune only known rebuildable caches after confirming no active writer; completed experiments should be archived with checksum verification before local removal.
- Put archive and retention records in the ignored workspace. Keep current review references usable and verify them after any storage migration.

## Product manager review of public-facing material

- Before finalizing or publishing any public-facing material, have a separate agent acting as a product manager review it. This applies to product naming, websites, demos, README files, documentation, social posts, release notes, and promotional images or videos.
- Review for the intended audience: a clear value proposition, natural and compelling headlines, understandable messaging, professional presentation, and marketability appropriate to the material's purpose. Keep claims accurate and supported, and protect private information.
- Review rendered pages and media when visual presentation matters. Address material findings before delivery or publication.
- This is an internal agent review; it does not require an additional round of user permission.

## Public repository files

- Write every public-facing file for its intended users and contributors. Never use README files, documentation, changelogs, examples, code comments, or other public files as an agent notepad: exclude internal work notes, conversation history, task progress, and temporary repository housekeeping.
- Do not include commentary about the repository currently being private, plans to make it public, or temporary Git-credential caveats tied to its publication status. Document the supported installation and usage steps directly.
- Public documentation must use repository-relative links to files included in the repository or publicly accessible URLs. Do not reference private workspace paths, parent-workspace files, private photo filenames, or ignored local evidence/run artifacts.
- Summarize private verification results without exposing their local locations, and link to repository test scripts and reproducible instructions instead. Clearly labeled placeholder paths in setup examples are allowed.
- Before finishing changes to public-facing files, check for internal commentary and temporary housekeeping notes as well as private paths and inaccessible local evidence references. Check that repository-relative links resolve.

## Before committing

- Review the repository's `CHANGELOG.md` and `README.md` against the changes being committed. Update the changelog for relevant fork additions, fixes, or behavior changes, and keep the README's summary, setup instructions, and capability claims consistent. Do not add unrelated entries or imply an unreleased change has been released.
- Run the affected checks locally before committing and do not commit on red: `cargo fmt --check` plus `cargo clippy --all-targets --all-features -- -D warnings` and `cargo test` for Rust changes; `npm run format:check`, typecheck/lint/test for frontend and MCP changes (`npm test --prefix mcp` covers the MCP suite); the relevant `packaging/test-*.py` or other repo test scripts for packaging/workflow changes. Mirror every gate the PR CI runs for the touched areas. If a check cannot run locally (missing system dependency or platform), say so explicitly instead of assuming it passes.
