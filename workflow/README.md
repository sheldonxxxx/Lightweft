# Lightweft collection tools

Build a repeatable local collection for checking changes to an editor, editing agent, or workflow. These tools record the identity of your original files, produce a browsable catalogue, and check that your inputs still match their recorded hashes and provenance.

This is an optional part of [Lightweft](../README.md). Start with the [editing and review guide](../docs/getting-started.md) for a first photo; use a regression collection when you need to revisit the same inputs across changes. The [Review application](../review/README.md) handles rendered comparisons and feedback. Collection tools work independently of RapidRAW, Insta360, and any photo library service.

Use Python 3.10+ and the standard library. Supported inputs are existing CR3/DNG originals and JPEG/WebP previews. Supply your own photographs and rendered previews; these tools check and catalogue files without decoding RAW, rendering edits, downloading photographs, or contacting a server.

## Set up your own collection

Keep data in an ignored directory, separate from public source:

```text
.local/
  originals/
    example.dng
  suite/
    selection.json
    previews/
      example.jpg
```

```sh
mkdir -p .local/originals .local/suite/previews
cp workflow/selection.example.json .local/suite/selection.json
```

Supply your own RAW and an existing preview at the example paths, or change the paths in `selection.json`. The [example selection](selection.example.json) contains invented labels and placeholder hashes; replace them before building.

For each file, obtain its size and SHA-256 without changing it:

```sh
python3 -c 'import hashlib,pathlib,sys; p=pathlib.Path(sys.argv[1]); print(p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())' .local/originals/example.dng
```

Repeat for the preview. Fill both `original.sha256` and `source_checksum_sha256` with the original's hash; set each `byte_size` and the preview's hash. Copy the case object for additional images and assign unique IDs, original paths, and source hashes.

Describe the actual challenge, source limitations, and how the preview was rendered. Keep the example's structural fields and leave unknown metadata empty. Preserve capture relationships with `group_id` and `related_case_ids`; every related ID must exist in the collection. Cases sharing a date in `capture_date_candidates` must belong to one group. A date alone does not establish an independent shoot.

Local originals use `origin: "local"`, `asset_id: null`, and `original.server_sha1_base64: null`. Existing Immich selections may use `origin: "immich"` or `"v2"` with their recorded asset ID and base64 server SHA-1 checksum. That checksum is verified against the local file only; it does not confirm current library membership or access.

## Build and verify

Run from the repository root:

```sh
python3 workflow/build_suite.py --suite-dir .local/suite
python3 workflow/build_catalogue.py --suite-dir .local/suite
python3 workflow/verify_collection.py --suite-dir .local/suite --require-clean
```

Open `.local/suite/catalogue.html` in a browser after verification succeeds. Each command writes only into the selected suite directory:

| Command | Output |
| --- | --- |
| `build_suite.py` | `manifest.json` with the selected cases and computed collection summary |
| `build_catalogue.py` | `catalogue.html`, `coverage.md`, and a blank `evaluation-template.json` if one is absent |
| `verify_collection.py` | `validation-report.json` and a nonzero exit status when a check fails |

Keep `suite/` beside `originals/`; the builder requires originals beneath that sibling directory. Previews must be inside `suite/previews/`. Nested original and preview directories are supported, and their manifest paths must resolve from the suite directory.

The builder checks hashes, sizes, source containment, unique source identities, and the regression-only policy before writing `manifest.json`. The catalogue writes HTML and a coverage report, and copies the blank evaluation template if no local copy exists. The verifier checks signatures, hashes, sizes, recorded provenance, grouping, and catalogue links. `--require-clean` also requires exact correspondence between the manifest and original/preview folders. It reports stray files without deleting them.

## Evaluate edits separately

This workflow accepts **exposed development/regression cases only**: photographs already available to the person or agent developing the edit. Use `split: "development"` and `evaluation_status: "exposed_regression"`. Do not describe improvements on these familiar inputs as performance on an unseen benchmark. A previous holdout label does not erase later exposure.

Preserve original bytes. Put editing sessions, recipes, and rendered results in a separate ignored run directory. Record the application revision, RAW interpretation, rendering settings, intended result, and viewing conditions in a copy of the [evaluation template](evaluation-template.json). Leave unassessed fields empty and explain observed improvements and regressions with visual evidence.

Review source and candidate at the intended viewing size and matched native detail. Record gains, losses, artifacts, and unresolved limitations. A successful integrity check or export does not establish aesthetic quality or user acceptance. Container-signature checks also do not prove that a RAW decoder can open the file.

Use the [unified review application](../review/README.md) for ongoing edit, style, denoise, and detail review. Publish rendered exports and their provenance into a review session, then read saved user feedback before revising. The catalogue remains an inventory and integrity aid; new review capabilities belong in the shared application's panels. The [style builder skill](../skills/photo-style-builder/SKILL.md) keeps personal preferences and validated editor presets in the user's workspace, separately from the general editing philosophy.

Never publish generated catalogues, manifests, or populated evaluations from a personal library. They can contain paths, identifiers, capture metadata, and photographs.

## Verify changes to these tools

From the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_workflow.py' -v
python3 scripts/check_public_repo.py --working-tree
```

The tests use invented records and synthetic container bytes. They exercise collection integrity, catalogue links, input boundaries, and error handling; actual RAW decoding and photographic review require your editor and images. See [contributing](../CONTRIBUTING.md) for the complete repository checks.
