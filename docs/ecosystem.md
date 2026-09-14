# The Lightweft ecosystem

[Lightweft](../README.md) is the central workspace for an AI photo editing workflow. It brings together artistic direction, personal style, and visual review. Editors and specialist preparation tools remain independent projects that you choose for the photograph in front of you.

## Three independent projects

| | Lightweft | RapidRAW | Insta360 AI Toolkit |
|---|---|---|---|
| Primary role | Direction, style exploration, and review | RAW development and photographic editing | Preparation and inspection of saved Insta360 photos |
| Works on its own | Skills with your agent; review app with existing exports | Desktop editor; optional agent control through this fork's MCP bridge | CLI/agent workflows; standalone Local 360 viewer |
| Connection to the others | Publishes the creative brief and consumes rendered candidates and feedback | Can follow a Lightweft plan and edit prepared Insta360 derivatives | Can prepare a sphere or perspective for an editor and provide previews for Lightweft |
| Required companions | None | None | None |
| Owns | Planning/style skills, review schema and panels, collection toolkit | Editor engine, sidecars, native operations, MCP bridge and execution skill | SDK wrapper, metadata tools, Studio guidance, reprojection helpers and viewer |
| License | [MIT](../LICENSE) | [AGPL-3.0](https://github.com/sheldonxxxx/RapidRAW/blob/main/LICENSE) | [MIT for original code](https://github.com/sheldonxxxx/insta360-ai-toolkit/blob/main/LICENSE); vendor SDK terms apply separately |
| Setup | [Getting started](getting-started.md) | [RapidRAW](https://github.com/sheldonxxxx/RapidRAW#readme) | [Insta360 AI Toolkit](https://github.com/sheldonxxxx/insta360-ai-toolkit#readme) |

RapidRAW is a fork of [CyberTimon/RapidRAW](https://github.com/CyberTimon/RapidRAW) with an optional MCP integration. Insta360 AI Toolkit is an independent community project, unaffiliated with Insta360. Lightweft neither bundles nor relicenses these tools.

Each project owns its installation and technical reference. This keeps application commands close to their implementation and lets any project evolve or be used independently. Other editors can participate through your agent's available controls or a manual workflow and compatible image exports.

## How they work together

The shared boundary is **an intention, rendered files, provenance, and feedback**. Your agent or a human coordinates the handoff. Lightweft does not automatically launch companions, discover their sessions, or convert editor recipes between applications.

1. **Read the photograph.** Photo Edit Master identifies the strongest quality, chooses a direction, and names relationships to protect.
2. **Prepare only when needed.** For native Insta360 input, the toolkit supplies an appropriate Studio or SDK route. Ordinary photographs can go straight to their editor.
3. **Render a candidate.** RapidRAW or another editor performs the edit. Keep the original and the editor's editable state or processing recipe.
4. **Publish a review case.** Register a browser-readable baseline and candidates through the [Lightweft manifest, CLI, or API](../review/README.md). Use stable case and variant IDs; mark changed framing honestly.
5. **Refine from feedback.** The photographer compares results, chooses a direction, and leaves notes. The agent reads that feedback and makes the next edit in its owning tool.
6. **Deliver from the processing tool.** Export the final photograph and verify dimensions, colour, and relevant metadata. Review selections are feedback, not final-image exports.

### One RAW photograph

```text
RAW original → chosen editor → baseline and edited exports
                   ↑                       ↓
             Lightweft plan          Lightweft review
                   ↑                       ↓
                   └──── feedback and refinement ────┘
```

Use RapidRAW's optional bridge for native agent execution, or apply the plan in your preferred editor. Add Photo Style Builder when you want to explore looks or develop reusable preferences. A style profile describes taste; an editor preset contains real settings from that editor. They are separate artifacts.

### One Insta360 photograph

```text
Native original → Insta360 preparation → verified sphere or selected view
                                                    ↓
                                           RapidRAW or another editor
                                                    ↓
                                           Lightweft rendered review
                                                    ↓
                                           editor's verified delivery
```

Choose the intended delivery before editing: an immersive sphere or a conventional perspective photograph. A sphere needs continuous seams, coherent poles, preserved projection, and suitable metadata. A perspective is an intentional crop/reprojection and should be described that way. The toolkit's [photo-editing handoff](https://github.com/sheldonxxxx/insta360-ai-toolkit/blob/main/skills/insta360-sdk/references/photo-edit-handoff.md) owns those processing steps.

The toolkit's **Local 360** viewer is a lightweight way to inspect one prepared panorama without Lightweft. Lightweft's **360 review** compares candidates and records feedback in the wider editing workflow. Both have a useful independent role.

## Compatibility and evidence

Test records describe specific versions, inputs, and environments. They do not establish support for every camera, operating system, GPU, or output route. The companion records below are authoritative for their own setup and known limits.

| Component | Evidence and scope | Boundary to keep in mind |
|---|---|---|
| Lightweft skills | Inspectable Markdown instructions with photographic references | Your host must read skills and inspect images; tool execution depends on your setup |
| Lightweft review | Local Python server for macOS/Linux; [synthetic server tests](../tests/test_review.py), [browser-module tests](../review/tests/store.test.mjs), and a [disposable UI fixture](../review/tests/fixture.py) | POSIX file handling; no native Windows server; browser exports only; tests do not grade photographs or decode RAW |
| RapidRAW MCP on macOS | Source-built MCP-enabled debug binary with Metal; [verification record](https://github.com/sheldonxxxx/RapidRAW/blob/main/mcp/VERIFICATION.md) | Installation of the skill alone does not enable the bridge; packaged MCP releases and Windows workflow remain untested |
| RapidRAW MCP on Linux | Recorded Debian 13 x86-64 LXC/NVIDIA workflow, with SSH and a virtual display; [remote guide](https://github.com/sheldonxxxx/RapidRAW/blob/main/mcp/REMOTE-SSH.md) | A qualified configuration, not blanket Linux/GPU support; optional AI providers and models have their own limits |
| Insta360 SDK processing | Selected INSP workflows in Ubuntu 22.04 amd64 containers on Apple Silicon and x86-64 Linux; [runtime evidence](https://github.com/sheldonxxxx/insta360-ai-toolkit/blob/main/skills/insta360-sdk/references/verification.md) | Licensed SDK downloads required; Mac container emulation is experimental; direct SDK DNG stitching failed acceptance; full NVIDIA graphics is unqualified |
| Insta360 Studio route | Native macOS Studio full-sphere DNG export recorded separately; [Studio guide](https://github.com/sheldonxxxx/insta360-ai-toolkit/blob/main/skills/insta360-sdk/references/runtime.md#studio-full-sphere-dng-export) | Requires installed Studio; export success and later RAW development or edit quality are separate checks |
| Toolkit Local 360 viewer | Browser viewer for existing stitched panoramas; [viewer guide](https://github.com/sheldonxxxx/insta360-ai-toolkit/blob/main/viewer/README.md) | No SDK or Docker needed for viewing; native camera files require preparation first |

A successful API response or source test does not prove that an edit looks right. Verify actual scene pixels and the final output at the viewing scale and detail level that matter to the photograph.

## Local data and model access

The review application serves only registered media beneath an explicit media root and stores feedback in the selected local workspace. Keep originals, personal style profiles, recipes, and rendered work in ignored storage. The [review guide](../review/README.md) explains access and persistence.

Your selected agent may send images or context to its model provider. Local processing tools and a local review server do not determine that provider's policies. Lightweft supplies no model subscription, bundled cloud service, or hosted photo library.

## Where we're going

The vision is an **AI photo editing universe with Lightweft at its center**: a common place to express photographic intent, explore personal taste, and assess results across a growing choice of tools.

The current foundation consists of two skills, a local review application, a regression toolkit, and documented optional companion workflows. Future directions include more independent editing integrations, easier handoffs, broader camera and platform validation, and better review experiences for different kinds of photography. These are directions for contribution, not shipped connectors or delivery commitments.

A useful integration should make its inputs, outputs, editable state, and tested limits clear. It should preserve originals, bring real rendered evidence into review, and let the photographer's feedback shape the next edit. Application procedures belong with the tool that executes them; shared artistic philosophy stays in Lightweft.

Start with the [contribution guide](../CONTRIBUTING.md). For a review panel or manifest change, contribute here. For native editing/MCP behavior, contribute to RapidRAW. For stitching, SDK metadata, Studio preparation, or the standalone panorama viewer, contribute to Insta360 AI Toolkit.
