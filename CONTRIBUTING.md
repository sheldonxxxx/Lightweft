# Contributing

Keep the planning skill focused on artistic judgment. Put application procedures in the execution integration, and preserve source attribution and evidence limits in the references. Personal style exploration belongs in the style builder, with reusable preferences saved in the user's workspace.

The public collection tools are maintained under [workflow/](workflow/README.md), and the shared review application under [review/](review/README.md). Add specialised review panels to the shared application. Copies under local historical suite or run directories are private records and are not the public source of truth.

## Validate a change

```sh
python3 -m unittest discover -s tests -v
node --test review/tests/store.test.mjs
git add <reviewed-source-files>
python3 scripts/check_public_repo.py
git diff --cached --check
git diff --cached
```

The publication check reads staged blobs, so stage the final versions before running it. Use `python3 scripts/check_public_repo.py --working-tree` to check source before staging. CI runs the Python and browser-state tests. Tests use synthetic inputs to check collection integrity, review data, and application contracts; they do not claim RAW decoding or edit-quality validation. The [review guide](review/README.md#extend-and-verify) includes a disposable browser fixture.

## Publication boundary

`.gitignore` uses a source allowlist because this workspace may also contain private photo libraries and editing runs. New public files require a deliberate allowlist change in both `.gitignore` and `scripts/check_public_repo.py`. Keep those boundaries consistent so files visible to Git also pass publication validation. Never force-add originals, rendered photos, EXIF dumps, library manifests, session/recipe data, credentials, local database configuration, or the nested `RapidRAW/` checkout. Use invented identifiers and generated test bytes in examples.

Keep private inputs and outputs under `.local/` or another ignored directory. Read an actual staged diff before publishing; pattern checks cannot prove that every possible secret or personal detail is absent. Do not paste private manifests or authentication data into issues.

Changes to a separate RapidRAW checkout must be reviewed, committed, and published in that repository. Its existing license remains in force.
