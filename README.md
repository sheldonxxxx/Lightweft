# Photo Edit Test

Skills and local workflow tools for planning, reviewing, and checking AI-assisted photo edits.

The [Photo Edit Master skill](skills/photo-edit-master/SKILL.md) develops an image-specific artistic direction from attention, light, colour, atmosphere, and truthful representation. Its references cover landscape, wildlife, nightscapes, people, and still life. It supplies reasoning to a separate editing tool; it contains no software settings or presets.

The [RAW regression workflow](workflow/README.md) builds a local catalogue and checks original files, previews, hashes, capture groups, and recorded provenance. It supports CR3 and DNG inputs. These checks establish input integrity; rendered-image review is still needed to judge edit quality.

## Contents

| Path | Purpose |
| --- | --- |
| `skills/photo-edit-master/` | Portable skill and attributed research references |
| `workflow/` | Suite builder, catalogue, verifier, and blank templates |
| `tests/` | Synthetic integrity and portability checks; no photographs |
| `scripts/check_public_repo.py` | Checks the Git index for unexpected files, large blobs, and common private-data patterns |

Personal photographs, library metadata, editing sessions, recipes, generated galleries, historical run reports, and local research drafts are excluded. Bring your own images and keep them under an ignored local directory. No photograph or third-party dataset is distributed here.

## Use the skill

Read [SKILL.md](skills/photo-edit-master/SKILL.md) and the reference appropriate to the photograph. An agent that supports filesystem skills can load the complete `skills/photo-edit-master/` folder. Installation and registration depend on the agent you use.

Example request:

> Inspect this photograph and propose a clear edit direction. Explain the visible priorities, the relationships to protect, and how to recognize excessive processing. After editing, compare the rendered result with the source at viewing size and matched detail.

## Run the workflow checks

Python 3.10 or newer is required. The public tools and tests use the standard library; no application, database, credentials, or network connection is needed.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_public_repo.py
```

Follow the [workflow setup guide](workflow/README.md) to build a catalogue from your own RAW files and existing JPEG/WebP previews. The tools do not decode RAW files or generate previews.

## RapidRAW integration

[RapidRAW](https://github.com/CyberTimon/RapidRAW) is a separate photo editor. The [MCP-enabled fork](https://github.com/sheldonxxxx/RapidRAW) contains its integration and execution skill. Consult that checkout's documentation and capabilities for setup and supported operations.

This repository does not vendor RapidRAW, register it as a submodule, or publish changes in a local `RapidRAW/` checkout. A clone of this repository includes the planning skill and input-verification workflow; it does not include an editing engine. The integrity tests do not exercise RapidRAW or prove aesthetic quality.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md) for validation and publication boundaries. Original code and documentation in this repository are available under the [MIT License](LICENSE). Referenced research, linked photographs, and third-party projects retain their own terms. RapidRAW has its own AGPL-3.0 license, which this repository does not replace.
