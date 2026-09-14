# Contributing to Lightweft

Lightweft brings editing judgment, review, and personal style feedback into one workspace. Contributions should help photographers and their agents make intentional edits, compare real results, and carry useful feedback into the next photograph.

Read the [project overview](README.md), [getting started guide](docs/getting-started.md), and [ecosystem guide](docs/ecosystem.md) before choosing where a change belongs.

## Choose the right project and layer

| Contribution | Location |
| --- | --- |
| Image-specific judgment and critique | [Master editing skill](skills/photo-edit-master/SKILL.md) and its genre references |
| Collaborative style exploration | [Style builder skill](skills/photo-style-builder/SKILL.md) |
| Comparisons, feedback, saved style artifacts, and specialised review panels | [Review application](review/README.md#extend-and-verify) |
| Repeatable local input collections and integrity checks | [Collection tools](workflow/README.md) |
| RapidRAW editor or MCP changes | [Independent RapidRAW repository](https://github.com/sheldonxxxx/RapidRAW) |
| Insta360 processing and integration changes | [Independent Insta360 repository](https://github.com/sheldonxxxx/insta360-ai-toolkit) |

Keep artistic reasoning in the planning skill and application procedures in the relevant tool integration. Preserve source attribution and evidence limits in research references. Keep personal profiles, presets, and accepted examples in the user's workspace so taste can evolve independently of shared philosophy.

Extend the shared Review application when a new inspection needs a specialised panel. Reuse its media registration, versioned feedback, and selection model so users can continue the same review across views. Companion integrations should remain optional: users must be able to use Lightweft's skills and Review without installing an editor or camera toolkit.

## Develop and test

Use Python 3.10+ on macOS or Linux and Node.js 22+ for browser-module tests. Review and collection tools use the Python standard library; the browser modules need no package installation or build step. Run a [disposable review demo](review/README.md#try-the-demo) for interface work.

From the repository root:

```sh
python3 -m unittest discover -s tests -v
node --test review/tests/*.test.mjs
python3 scripts/check_public_repo.py --working-tree
git diff --check
```

CI runs the Python and browser-module tests. They check collection integrity, review data, comparison behavior, sphere geometry, and sequence grouping using synthetic inputs. They do not establish RAW decoder compatibility, aesthetic quality, or photographer acceptance. For interface changes, use the [browser verification guide](review/README.md#extend-and-verify) to check the affected flow with a keyboard and a narrow viewport.

## Prepare a pull request

Describe the user-facing problem, resulting behavior, and validation that actually ran. Include a concrete example when it helps a reviewer understand the change. Keep scope focused, preserve existing manifest and feedback contracts, and explain any required migration. Use screenshots from synthetic fixtures or photographs you have permission to publish.

Review [README.md](README.md) and [CHANGELOG.md](CHANGELOG.md) against the change. Update affected instructions and capability claims, and add relevant behavior changes under **Unreleased**. Do not describe an unreleased change as shipped.

Before committing, stage only the reviewed source files, then check the exact staged content:

```sh
git add <reviewed-source-files>
python3 scripts/check_public_repo.py
git diff --cached --check
git diff --cached
```

`<reviewed-source-files>` is a placeholder for the paths you intend to commit. The default publication check reads the Git index, so stage the final versions before running it. The working-tree check is useful while editing but does not replace reviewing the staged diff.

## Publication boundary

`.gitignore` uses a source allowlist because this workspace may also contain private photo libraries and editing runs. New public files require a deliberate allowlist change in both `.gitignore` and [the publication checker](scripts/check_public_repo.py). Keep those boundaries consistent so files visible to Git also pass publication validation. Never force-add originals, personal rendered photos, EXIF dumps, library manifests, session/recipe data, credentials, local database configuration, or independent companion checkouts. Use invented identifiers and synthetic test bytes in examples.

Keep private inputs and outputs under `.local/` or another ignored directory. Write documentation for users and contributors, using links to included repository files or public URLs. Exclude private paths, personal photo names, local run evidence, conversation history, and temporary maintenance notes. Read the complete staged diff before publishing; pattern checks cannot prove that every secret or personal detail is absent. Do not paste private manifests or authentication data into issues.

RapidRAW and the Insta360 toolkit have their own source, installation instructions, licenses, and release processes. Review, commit, and publish changes to each in its own repository.
