# Local RAW regression workflow

These tools are a portable extraction of the local suite builder, catalogue, and verifier. They use Python 3.10+ and the standard library. They accept existing CR3/DNG originals and JPEG/WebP previews; they do not download photographs, decode RAW files, render edits, or contact Immich.

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

Supply your own RAW and an existing preview at the example paths, or change the paths in `selection.json`. The example contains invented labels and placeholder hashes; it is not a downloadable test case.

For each file, obtain its size and SHA-256 without changing it:

```sh
python3 -c 'import hashlib,pathlib,sys; p=pathlib.Path(sys.argv[1]); print(p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())' .local/originals/example.dng
```

Repeat for the preview. Fill both `original.sha256` and `source_checksum_sha256` with the original's hash; set each `byte_size` and the preview's hash. Copy the case object for additional images and assign unique IDs, original paths, and source hashes.

Describe the actual challenge, source limitations, and preview provenance. Preserve existing capture relationships with `group_id` and `related_case_ids`. All cases sharing a recorded capture date must be in one group. Dates alone do not prove independent shoots. Metadata fields are optional descriptions; do not invent measurements or server identities.

Local originals use `origin: "local"`, `asset_id: null`, and `server_sha1_base64: null`. For compatibility with a private historical Immich selection, `origin: "v2"` requires its existing asset ID and base64 server SHA-1 checksum. Verification is offline; it does not confirm current server membership or permissions.

## Build and verify

Run from the repository root:

```sh
python3 workflow/build_suite.py --suite-dir .local/suite
python3 workflow/build_catalogue.py --suite-dir .local/suite
python3 workflow/verify_collection.py --suite-dir .local/suite --require-clean
```

Open `.local/suite/catalogue.html` in a browser. Build outputs remain in the selected suite directory. Keep `suite/` beside `originals/` to retain working relative links. Previews must be inside `suite/previews/`; nested preview directories are supported.

The builder checks hashes, sizes, source containment, unique source identities, and the regression-only policy before writing `manifest.json`. The catalogue writes HTML and a coverage report, and copies the blank evaluation template if no local copy exists. The verifier checks signatures, hashes, sizes, recorded provenance, grouping, and catalogue links. `--require-clean` also requires exact correspondence between the manifest and original/preview folders. It reports stray files without deleting them.

## Evaluate edits separately

This workflow deliberately accepts **exposed development/regression cases only**. Use `split: "development"` and `evaluation_status: "exposed_regression"`. It is not a fresh-holdout benchmark tool, and a previous holdout label does not erase later exposure.

Preserve original bytes. Put editing sessions, recipes, and rendered results in a separate ignored run directory. Record the application revision, RAW interpretation, rendering settings, intended result, and viewing conditions in a copy of `evaluation-template.json`.

Review source and candidate at the intended viewing size and matched native detail. Record gains, losses, artifacts, and unresolved limitations. A successful integrity check or export does not establish aesthetic quality or user acceptance. Container-signature checks also do not prove that a RAW decoder can open the file.

Never publish generated catalogues, manifests, or populated evaluations from a personal library. They can contain paths, identifiers, capture metadata, and photographs.
