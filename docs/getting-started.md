# Start with Lightweft

[Lightweft](../README.md) connects an editing intention, the tools you choose, and visual feedback. Start with either the skills or the review app; neither requires RapidRAW or Insta360 AI Toolkit.

## Choose your starting point

| Goal | What you need | Next step |
|---|---|---|
| Plan or critique a photograph | An agent that can inspect images and read skills | [Install the skills](#install-the-skills) |
| Try the review controls | Python 3.10+, macOS or Linux, a modern browser | [Run the demo](#run-the-review-demo) |
| Review your own edit | The review app and browser-readable exports from an editor | [Register a comparison](#review-your-own-photographs) |
| Let an agent operate a RAW editor | A compatible agent and a separately configured execution tool | [Choose an editor](#add-an-optional-execution-tool) |
| Prepare an Insta360 original | The toolkit's Studio or SDK prerequisites | [Choose a 360° route](#add-an-optional-execution-tool) |

The skills are Markdown instructions and have no editing engine. The local review server uses Python's standard library and POSIX file handling; native Windows is not supported by that server. Node.js 22+ is used for browser-module development tests, not to run the review app.

## Install the skills

With Node.js/npm available, run these commands from the project where you work with your agent:

```sh
npx skills add sheldonxxxx/lightweft --skill photo-edit-master
npx skills add sheldonxxxx/lightweft --skill photo-style-builder
```

Select your agent when prompted. The [Skills CLI](https://github.com/vercel-labs/skills#readme) installs to the project by default; add `--global` for user-level installation. Reconnect or start a new agent session if your host loads skills only at startup.

For a manual install, download or clone this repository and copy the complete [photo-edit-master](../skills/photo-edit-master/SKILL.md) and [photo-style-builder](../skills/photo-style-builder/SKILL.md) directories, including their `references/` folders, into your agent's supported skill location. Hosts without skill discovery can read those files directly. Installing skills alone does not install the review app or either companion.

**Start with one photograph:**

> Use photo-edit-master to inspect this photograph and choose a clear artistic direction. Explain the visible priorities and the qualities to protect. Use my available editor to produce a candidate, then compare it with the source at viewing size and native detail. Preserve the original.

**Explore personal style after a convincing base:**

> Use photo-style-builder to explore a few distinct looks from this base edit. Render each with my available editor and publish them to the Lightweft review workspace. Keep the base for comparison, let me choose and leave feedback, then refine the selected direction.

Tell the agent where the photograph and Lightweft checkout are and which editing tools it can use. If no editing tool is connected, the agent can still supply a plan or critique; you can make the edit yourself and bring its exports back for review.

## Run the review demo

```sh
git clone https://github.com/sheldonxxxx/lightweft.git
cd lightweft
python3 review/tests/fixture.py --port 8766
```

Open [localhost:8766](http://127.0.0.1:8766). The synthetic fixture includes aligned versions, changed framing, a detail region, a sequence, and full spheres. Try Photo reviewer, Style builder, Set review, Detail lab, and 360 review. Save a note and reload to see feedback persist during the session.

This is a controls demo, not evidence of photo-editing quality. **Ctrl+C** stops the server and removes its temporary workspace. Use the persistent setup below for real work. If the port is in use, choose another with `--port` and use that port in your browser.

## Review your own photographs

Run the following from your Lightweft checkout. `.local/` is an ignored workspace for your images, manifests, and feedback.

### 1. Prepare a pair of exports

```sh
mkdir -p .local/media .local/manifests
```

Put a baseline render at `.local/media/baseline.jpg` and your edited render at `.local/media/candidate.jpg`. These are example filenames: copy or export your own photographs into those locations. Use JPEG, PNG, or WebP for broad browser compatibility. RAW files need development first; browser support for TIFF varies.

Use the same dimensions and framing for an aligned comparison. If the crop or geometry changed, set `aligned` to `false` in the example below. Matched framing matters more than matching the filenames.

### 2. Register the pair

Save this JSON as `.local/manifests/first-edit.json`:

```json
{
  "schemaVersion": 1,
  "id": "first-edit",
  "title": "My first edit",
  "cases": [
    {
      "id": "photo-01",
      "title": "Light and atmosphere",
      "intent": "Keep the scene's depth while making the subject clearer.",
      "aligned": true,
      "defaultView": "side",
      "variants": [
        {"id": "base", "label": "Baseline", "role": "baseline", "image": "baseline.jpg"},
        {"id": "edit", "label": "Candidate", "role": "candidate", "image": "candidate.jpg"}
      ]
    }
  ]
}
```

Image paths are relative to `--media-root`, not to the manifest file. Import the manifest and start the server using the same roots:

```sh
python3 review/cli.py import .local/manifests/first-edit.json \
  --id first-edit --workspace .local/review --media-root .local/media
python3 review/server.py \
  --workspace .local/review --media-root .local/media --port 8765
```

Open [localhost:8765](http://127.0.0.1:8765). Compare the versions and save your decision and note. This workspace persists after the server stops. For ongoing agent work, use the [review manifest and API contract](../review/README.md) to register candidates while retaining stable identities and feedback.

### 3. Feed the decision back into the edit

In another terminal, from the same checkout:

```sh
python3 review/cli.py feedback-export first-edit \
  --workspace .local/review --media-root .local/media \
  --output .local/manifests/first-edit-feedback.json
```

Give that feedback to the agent and ask it to refine the selected candidate. Have it keep the accepted version as a reference when publishing the next render. A review decision records what you prefer; exporting the final photograph or an editor preset remains a separate operation.

For 360° images, masks, native crops, full-resolution variants, or photo sets, continue with the [review guide](../review/README.md). Qualitative style profiles and reusable editor presets follow the [style-builder guidance](../skills/photo-style-builder/SKILL.md); a preset requires a real editor recipe.

## Add an optional execution tool

**RapidRAW** is an independent RAW editor. Its [MCP guide](https://github.com/sheldonxxxx/RapidRAW/blob/main/mcp/README.md) explains how to build and connect this fork's optional bridge, verify capabilities, and make a first edit. The [execution skill](https://github.com/sheldonxxxx/RapidRAW/tree/main/skills/rapidraw-mcp) translates a Lightweft intention into native edits. Install the application, bridge, and skill according to that repository; none is installed by the Lightweft commands above.

**Insta360 AI Toolkit** is an independent preparation toolkit for saved camera photos. Its [README](https://github.com/sheldonxxxx/insta360-ai-toolkit#readme) separates the native Studio DNG route, licensed SDK processing, and the SDK-free Local 360 viewer. Bring a prepared image into your editor, then send review exports to Lightweft. The toolkit's [handoff guide](https://github.com/sheldonxxxx/insta360-ai-toolkit/blob/main/skills/insta360-sdk/references/photo-edit-handoff.md) covers sphere preservation and selected perspective views.

You can also use another editor manually or through its available automation. Lightweft accepts suitable exports through its documented manifest/API; it does not add application integrations by itself. See [the ecosystem guide](ecosystem.md) for responsibilities, tested environments, and complete workflow examples.
