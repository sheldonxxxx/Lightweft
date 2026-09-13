# Add a demo group

The gallery reads [data.json](data.json). Append a group to its `groups` array; keep existing group and photo IDs stable so links continue to work. The frontend renders every group through the same comparison controls.

[Explore the gallery](https://sheldonxxxx.github.io/Lightweft/).

## Preview locally

Run these commands from the repository root with Python 3.10 or later:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install Pillow==12.2.0
.venv/bin/python -m unittest discover -s tests -p test_showcase.py -v
.venv/bin/python scripts/check_public_repo.py --working-tree
.venv/bin/python scripts/build_showcase.py
.venv/bin/python -m http.server 8000 --directory _site
```

Open `http://localhost:8000`. Each build recreates `_site` from the gallery's explicit runtime files and referenced JPEGs.

## Prepare a fair comparison

Use the same photograph, framing, orientation, aspect ratio, and export dimensions for both sides. Label the before image accurately: an unadjusted RAW render shows an editor's starting interpretation, which can differ from an embedded camera preview. It is not a benchmark against a skilled human edit.

Describe the visible edit and any material cost, such as faint detail softened by denoising. Identify human direction or later refinements when discussing autonomous editing. Do not imply that AI generated the photographed scene when the workflow used ordinary photographic adjustments.

Export JPEGs in sRGB at matching responsive widths, such as 960, 1600, and 2400 pixels. Strip EXIF, GPS, XMP, IPTC, comments, and embedded thumbnails. A generic sRGB ICC profile may remain. Each JPEG must be at most 2 MiB. Inspect the actual exports, including sky detail and foreground edges, before adding them.

## Add the images and data

Place only approved demo JPEGs in `assets/<collection-name>/`. Use generic lowercase names with hyphens, such as `ridge-before-1600.jpg`; avoid camera filenames, dates, and library identifiers.

Each group contains `id`, `number`, `title`, `subtitle`, and `photos`. Each photo contains `id`, `title`, `description`, `alt`, `width`, `height`, `before`, and `after`. Set `width` and `height` to the positive integer dimensions of the final export, for example 2400 and 1600. The gallery uses their aspect ratio, so portrait, square, and panoramic photographs keep their framing. Every responsive image must match that ratio, allowing one pixel of resize rounding. Each side has a default `src` and a `srcset` array:

```json
{
  "src": "assets/nightscapes/ridge-before-1600.jpg",
  "srcset": [
    { "src": "assets/nightscapes/ridge-before-960.jpg", "width": 960 },
    { "src": "assets/nightscapes/ridge-before-1600.jpg", "width": 1600 },
    { "src": "assets/nightscapes/ridge-before-2400.jpg", "width": 2400 }
  ]
}
```

Each side also accepts optional `label` and `description` strings. When omitted, `before` uses **Before** / **Unadjusted RAW rendering**, and `after` uses **After** / **Edited photograph**. These names appear throughout the comparison controls, image descriptions and direct links.

For a preset comparison, set the before side to `"label": "Base rendering"` and `"description": "RapidRAW base rendering, before the preset"`. Set the after label to the preset name, such as `"label": "Quiet Story"`, with `"description": "The same base rendering with the Quiet Story preset"`. A base may retain the editor's defaults or include photo-specific corrections. Both images must share the same corrections and finishing; a denoised after image needs a correspondingly denoised base. Labels and descriptions must be nonempty strings when supplied; unsupported fields are rejected.

Image paths are relative to this directory. External image URLs, absolute paths, traversal, unsupported fields, and mismatched before/after dimensions are rejected. `assets/share-card.jpg` is the site's social preview; keep its content consistent with the gallery.

## Check and publish

Follow the [preview and validation commands](#preview-locally), then inspect the gallery at desktop and phone widths. Check both comparison sides, keyboard operation, captions, and image loading. After staging the reviewed files, run `.venv/bin/python scripts/check_public_repo.py` from the repository root to check the exact publication content.

The build copies only `index.html`, `styles.css`, `app.js`, `data.json`, the referenced JPEGs, and the social preview to `_site`. All photographs remain outside the code's MIT license; see the [photo terms](LICENSE). Only add images whose public display you are authorized to approve.

In repository Settings → Pages, choose **GitHub Actions** as the build source. Pushes and pull requests that change the showcase run validation and build checks. To publish, open Actions → **Publish photo showcase** → **Run workflow** and select `main`. Only a manual run on `main` uploads `_site` and deploys the gallery through the [Pages workflow](../.github/workflows/pages.yml).
