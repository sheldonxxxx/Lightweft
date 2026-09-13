# AI photo editing workflow

You are authorized to make any changes to RapidRAW and its MCP integration that you judge necessary to improve the AI photo editing workflow. This includes changes to the RapidRAW application, MCP tools, and supporting workflow code. Proceed with these improvements without asking for separate permission for each change.

## Image generation requires permission

- This is a photo-editing project. Ask for explicit permission before using imagegen or any other generative image service, including to create a separate sticker or other asset.
- A request to edit a photograph does not itself authorize image generation. Use photographic editing and local compositing for ordinary edits, preserving the original scene and resolution.

## Shared review workspace

- Use the [shared review application](review/README.md) for ongoing photo, style, denoise, and detail reviews. Publish rendered candidates through its manifest/API/CLI contract; extend its panel registry when a new inspection needs a specialised view.
- Choose `defaultView` for each review case: `single` for mask visualisations, or `side` / `wipe` for adjustment comparisons according to the inspection. Use variant overrides when mask renders and photo edits share a case.
- Keep review state, photographs, and personal style artifacts in the user's ignored workspace. Preserve historical review evidence, but do not create new standalone helper websites for workflows the shared app can handle.
- The master editing skill supplies an image-specific foundation. Use [photo-style-builder](skills/photo-style-builder/SKILL.md) for collaborative personal style exploration, with profiles and actual editor recipes kept separate from shared philosophy.

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
