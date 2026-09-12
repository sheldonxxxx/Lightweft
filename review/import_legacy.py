"""Read existing review manifests into the shared review format without editing media.

Historical decisions are carried as context, never promoted to current approval.
Path relocation requires an explicit caller-supplied prefix mapping.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from pathlib import Path


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _slug(value, fallback="item"):
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value)).strip("-") or fallback


def _text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return "" if value is None else str(value)


class _Paths:
    def __init__(self, root, maps):
        self.root = Path(root).resolve()
        self.maps = sorted(maps or [], key=lambda pair: len(pair[0]), reverse=True)
        if any(not Path(str(new)).is_absolute() for _, new in self.maps):
            raise ValueError("A --path-map destination must be an absolute path")
        self.warnings = []

    def media(self, value, base, optional=False):
        if not value:
            if optional:
                return None
            raise ValueError("A required legacy image path is missing")
        value = str(value)
        for old, new in self.maps:
            old = str(old).rstrip("/")
            if value == old or value.startswith(old + "/"):
                value = str(new).rstrip("/") + value[len(old):]
                break
        path = Path(value)
        if not path.is_absolute():
            path = Path(base) / path
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(self.root)
        except ValueError as error:
            raise ValueError("Legacy media is outside --media-root; provide an explicit --path-map when relocating a collection") from error
        for component in (path, *path.parents):
            if component.is_symlink() and component.resolve().is_relative_to(self.root):
                raise ValueError("Legacy media paths must not use symlinks inside --media-root")
        if not resolved.is_file():
            if optional:
                self.warnings.append(f"Missing optional artifact: {relative.as_posix()}")
                return None
            raise ValueError(f"Required legacy media is missing: {relative.as_posix()}")
        return relative.as_posix()


def _region(value, label, index):
    if not isinstance(value, dict) or not all(key in value for key in ("x", "y", "width", "height")):
        return None
    return {"id": _slug(label, f"region-{index}"), "label": label,
            **{key: value[key] for key in ("x", "y", "width", "height")},
            "aligned": False, "images": []}


def _encoded_dimensions(path):
    """Read JPEG/PNG dimensions; unknown encodings cannot establish native scale."""
    with Path(path).open("rb") as stream:
        header = stream.read(24)
        if header.startswith(b"\x89PNG\r\n\x1a\n") and header[12:16] == b"IHDR" and len(header) == 24:
            return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")
        if not header.startswith(b"\xff\xd8"):
            return None
        stream.seek(2)
        while stream.tell() < 2 * 1024 * 1024:
            marker = stream.read(1)
            if marker != b"\xff":
                return None
            while marker == b"\xff":
                marker = stream.read(1)
            if not marker or marker in (b"\xd9", b"\xda"):
                return None
            if marker == b"\x01" or 0xD0 <= marker[0] <= 0xD8:
                continue
            size_bytes = stream.read(2)
            if len(size_bytes) != 2:
                return None
            size = int.from_bytes(size_bytes, "big")
            if size < 2:
                return None
            if marker[0] in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                body = stream.read(5)
                if len(body) == 5:
                    return int.from_bytes(body[3:5], "big"), int.from_bytes(body[1:3], "big")
                return None
            stream.seek(size - 2, 1)
    return None


def _mark_native_regions(cases, paths):
    for case in cases:
        for region in case.get("regions", []):
            expected = (region["width"], region["height"])
            region["native"] = bool(region["images"]) and all(
                _encoded_dimensions(paths.root / image["image"]) == expected for image in region["images"])
            region["nativeDomain"] = "recorded-render-region"
            region["metadata"] = {"pixelScaleBasis": "Recorded crop dimensions compared with encoded JPEG/PNG dimensions. This establishes the recorded render domain only; full RAW resolution is not verified."}


def _embedded_data(source):
    # Parse only the inert JSON payload. Never evaluate the page's JavaScript.
    html = source.read_text(encoding="utf-8")
    payloads = re.findall(r"<script\b[^>]*\bid\s*=\s*['\"]galleryData['\"][^>]*>(.*?)</script\s*>", html, re.I | re.S)
    if len(payloads) != 1:
        raise ValueError("Embedded review needs exactly one galleryData JSON script")
    data = json.loads(payloads[0])
    if not isinstance(data, dict) or not isinstance(data.get("assets"), dict) or not isinstance(data.get("cases"), list):
        raise ValueError("Unsupported embedded review JSON format")
    return data


def _embedded_gallery(data, source, paths):
    """Locate existing byte-identical images without extracting or changing media."""
    located, file_sizes = {}, None

    def locate(key, preferred=None):
        nonlocal file_sizes
        if key in located:
            return located[key]
        asset = data["assets"].get(key)
        if not isinstance(asset, dict):
            raise ValueError("Embedded review references an unknown image asset")
        match = re.fullmatch(r"data:image/(?:jpeg|png|webp);base64,([A-Za-z0-9+/=\r\n]+)", asset.get("src", ""))
        if not match:
            raise ValueError("Embedded review image must contain a supported base64 image")
        try:
            raw = base64.b64decode(re.sub(r"\s+", "", match[1]), validate=True)
        except ValueError as error:
            raise ValueError("Embedded review image is invalid base64") from error
        digest = hashlib.sha256(raw).hexdigest()

        def matches(candidate):
            if not candidate.is_file() or candidate.is_symlink() or candidate.stat().st_size != len(raw):
                return False
            with candidate.open("rb") as stream:
                hasher = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    hasher.update(chunk)
                return hasher.hexdigest() == digest

        candidate = source.parent / preferred if preferred else None
        if not candidate or not matches(candidate):
            if file_sizes is None:
                file_sizes = {}
                for directory, subdirs, names in os.walk(source.parent, followlinks=False):
                    subdirs[:] = [name for name in subdirs if not (Path(directory) / name).is_symlink()]
                    for name in names:
                        path = Path(directory) / name
                        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} and not path.is_symlink():
                            file_sizes.setdefault(path.stat().st_size, []).append(path)
            candidate = next((path for path in sorted(file_sizes.get(len(raw), [])) if matches(path)), None)
        if candidate is None:
            raise ValueError(f"Embedded asset {key} has no byte-identical existing export beside the gallery; restore its original export before importing")
        located[key] = paths.media(candidate, source.parent)
        return located[key]

    cases = []
    for entry in data["cases"]:
        case_id = _slug(entry["id"])
        baseline = {"id": "baseline", "label": "Original native render", "role": "baseline",
                    "image": locate(entry["before"], f"baselines/{entry['id']}.jpg")}
        variants = [baseline]
        original_asset = data["assets"][entry["before"]]
        for key in ("width", "height"):
            if original_asset.get(key):
                baseline[key] = original_asset[key]
        metadata_variants = {}
        for index, old in enumerate(entry.get("variants", [])):
            key = old["key"]
            preferred = f"edits/exports/case-{entry['id']}-v1.jpg" if key.endswith("-final") else None
            variant_id = _slug(key, f"variant-{index + 1}")
            variant = {"id": variant_id, "label": old.get("label", variant_id),
                       "role": "reference" if old.get("rejected") else "candidate", "image": locate(key, preferred),
                       "description": "Historical rejected attempt." if old.get("rejected") else "Historical selected export; current user approval is recorded separately."}
            for size in ("width", "height"):
                if data["assets"][key].get(size):
                    variant[size] = data["assets"][key][size]
            recipe_path = source.parent / f"edits/recipes/case-{entry['id']}-v1.json"
            if key.endswith("-final") and recipe_path.is_file():
                variant.update(recipe=paths.media(recipe_path, source.parent), recipeFormat="rapidraw")
            variants.append(variant)
            metadata_variants[variant_id] = {key: old[key] for key in ("crop", "sliderAvailable", "geometryChanged", "rejected") if key in old}
        cases.append({"id": case_id, "title": entry.get("title", case_id), "category": "photo", "split": "development",
                      "format": Path(entry.get("filename", "")).suffix.lstrip(".").upper(), "intent": _text(entry.get("note")),
                      "limits": "Historical source framing and edited crops may differ. Compare complete frames side by side; cropped wipe alignment is not imported.",
                      "aligned": False, "variants": variants, "regions": [],
                      "metadata": {"importedFrom": "embedded-review", "sourceWidth": entry.get("sourceWidth"),
                                   "sourceHeight": entry.get("sourceHeight"), "historicalPhase": entry.get("phase"),
                                   "historicalKeptAsPhotographed": entry.get("faithful"),
                                   "historicalVariantGeometry": metadata_variants,
                                   "historicalReviews": entry.get("reviews", [])}})
    return cases


def _gallery(data, source, paths):
    cases = []
    for entry in data["cases"]:
        variants, regions = [], {}
        used_ids = set()
        for index, old in enumerate(entry.get("variants", [])):
            overview = old.get("views", {}).get("overview")
            if not overview:
                raise ValueError("Each legacy gallery variant needs an overview view")
            variant_id = _slug(old.get("id", f"variant-{index + 1}"))
            if variant_id in used_ids:
                raise ValueError("A legacy case has duplicate variant IDs")
            used_ids.add(variant_id)
            variant = {"id": variant_id, "label": old.get("label", variant_id),
                       "role": "baseline" if old.get("status") == "baseline" else "reference" if old.get("status") in ("tested", "rejected", "reference") else "candidate",
                       "image": paths.media(overview.get("path"), source.parent),
                       "description": _text(old.get("note"))}
            if old.get("status"):
                variant["description"] += f"\nHistorical status: {old['status']}. Current user approval is recorded separately."
            for key in ("width", "height"):
                if overview.get(key):
                    variant[key] = overview[key]
            recipe = paths.media(old.get("recipe_path"), source.parent, optional=True)
            if recipe:
                variant.update(recipe=recipe, recipeFormat="rapidraw")
            full = paths.media(old.get("export", {}).get("path") if isinstance(old.get("export"), dict) else None,
                               source.parent, optional=True)
            if full and full != variant["image"]:
                variant["full"] = full
            variants.append(variant)
            for name, view in old.get("views", {}).items():
                if name == "overview":
                    continue
                roi = _region(view.get("region"), name.replace("_", " "), len(regions) + 1)
                if roi is None:
                    continue
                key = (name, *(roi[k] for k in ("x", "y", "width", "height")))
                if key not in regions:
                    roi["id"] = _slug(f"{name}-{len(regions) + 1}")
                    regions[key] = roi
                image = paths.media(view.get("path"), source.parent, optional=True)
                if image:
                    regions[key]["images"].append({"variantId": variant_id, "image": image})
        if not variants:
            continue
        case = {"id": _slug(entry["id"]), "title": entry.get("title", str(entry["id"])),
                "category": entry.get("category", "study"), "split": entry.get("split", "development"),
                "format": entry.get("format", ""), "intent": _text(entry.get("note")),
                "limits": "Legacy alignment has not been independently verified. Historical status is context, not current user approval.",
                "aligned": entry.get("aligned") is True, "variants": variants,
                "regions": [region for region in regions.values() if region["images"]],
                "metadata": {"importedFrom": "gallery-manifest", "historicalVariantStatuses": {
                    str(v.get("id", i)): v.get("status") for i, v in enumerate(entry.get("variants", []))}}}
        cases.append(case)
    return cases


def _state_cases(files, paths):
    cases = []
    for file in files:
        entry = _read(file)
        if not entry.get("candidate") or entry.get("suite_status") == "retired-jpeg":
            continue
        # These state files live under a run's cases directory. Their original
        # paths were absolute; run-relative paths are also accepted for portability.
        base = file.parent.parent if file.parent.name == "cases" else file.parent
        baseline = paths.media(entry.get("baseline"), base)
        candidate = paths.media(entry["candidate"], base)
        variants = [{"id": "baseline", "label": "Untouched native baseline", "role": "baseline", "image": baseline},
                    {"id": "candidate", "label": "Current candidate", "role": "candidate", "image": candidate}]
        current = variants[1]
        for name, legacy_key in (("full", "final_full"), ("recipe", "recipe")):
            artifact = paths.media(entry.get(legacy_key), base, optional=True)
            if artifact:
                current[name] = artifact
        if current.get("recipe"):
            current["recipeFormat"] = "rapidraw"
        by_image = {baseline: "baseline", candidate: "candidate"}
        by_label = {}
        for event in entry.get("events", []):
            if event.get("stage") not in {"apply", "denoise-selected"} or not event.get("export"):
                continue
            image = paths.media(event["export"], base, optional=True)
            if not image:
                continue
            if image not in by_image:
                variant_id = f"earlier-{len(variants) - 1}"
                variants.append({"id": variant_id, "label": event.get("label", "Earlier candidate"),
                                 "role": "reference", "image": image})
                by_image[image] = variant_id
            if event.get("label"):
                by_label[event["label"]] = by_image[image]
        experiments = []
        for experiment in sorted(base.glob(f"denoise-{entry['id']}*.json")):
            experiment_data = _read(experiment)
            if not experiment_data.get("export"):
                continue
            image = paths.media(experiment_data["export"], base, optional=True)
            if not image:
                continue
            if image not in by_image:
                variant_id = f"denoise-{len(variants) - 1}"
                variants.append({"id": variant_id, "label": experiment_data.get("label", "Denoise experiment"),
                                 "role": "reference", "image": image,
                                 "description": f"{experiment_data.get('method', 'Denoise')} · intensity {experiment_data.get('intensity', 'unrecorded')}. Captured revision {experiment_data.get('captured_revision', 'unrecorded')}."})
                by_image[image] = variant_id
            by_label[experiment_data.get("label", "")] = by_image[image]
            experiments.append((experiment_data, by_image[image]))
        regions = {}

        def attach(region_data, variant_id, image_value):
            roi = _region(region_data, "Detail", len(regions) + 1)
            if roi is None or not variant_id:
                return
            key = tuple(roi[k] for k in ("x", "y", "width", "height"))
            image = paths.media(image_value, base, optional=True)
            if not image:
                return
            if key not in regions:
                roi.update(id=f"detail-{len(regions) + 1}", label=f"Detail {len(regions) + 1}")
                regions[key] = roi
            # Retain the latest crop for each specific variant and region.
            regions[key]["images"] = [im for im in regions[key]["images"] if im["variantId"] != variant_id]
            regions[key]["images"].append({"variantId": variant_id, "image": image})

        reviews = [e for e in entry.get("events", []) if e.get("stage") == "review"]
        selected_label = reviews[-1].get("label") if reviews else None
        for event in entry.get("events", []):
            images = event.get("images", [])
            if event.get("stage") == "inspect" and images:
                attach(event.get("region"), "baseline", images[0])
            elif event.get("stage") == "review" and len(images) >= 2:
                variant_id = by_label.get(event.get("label"))
                if not variant_id and event.get("label") == selected_label:
                    variant_id = "candidate"
                attach(event.get("region"), "baseline", images[0])
                attach(event.get("region"), variant_id, images[1])
        for experiment_data, variant_id in experiments:
            for detail in experiment_data.get("details", []):
                attach(detail.get("region"), variant_id, detail.get("path"))
        category = _text(entry.get("category", "photo"))
        metadata = {"importedFrom": "run-case-state", "sourceSha256": entry.get("source_sha256"),
                    "sessionId": entry.get("session_id"), "revision": entry.get("revision"),
                    "candidateVersion": entry.get("candidate_version"), "revisionRound": entry.get("revision_round")}
        if entry.get("user_review"):
            review = entry["user_review"]
            metadata["historicalReview"] = {key: review[key] for key in (
                "decision", "note", "reviewed_at", "reviewed_candidate_sha256") if key in review}
        cases.append({"id": _slug(entry["id"]), "title": entry.get("title", f"{entry['id']} · {category.replace('_', ' ')}"),
                      "category": category, "split": entry.get("split", "development"),
                      "format": entry.get("format", ""), "intent": _text(entry.get("intent")),
                      "limits": _text(entry.get("limits")), "qa": entry.get("qa", {}), "aligned": False,
                      "variants": variants, "regions": list(regions.values()), "metadata": metadata})
    return cases


def _suite(data, source, paths):
    cases = []
    for entry in data["assets"]:
        original, preview = entry.get("original", {}), entry.get("preview", {})
        if not preview.get("path"):
            continue
        label = preview.get("kind", "Browsing preview")
        metadata = {"importedFrom": "suite-manifest", "sourceSha256": original.get("sha256"),
                    "camera": entry.get("metadata", {}).get("camera"),
                    "iso": entry.get("metadata", {}).get("iso"), "tags": entry.get("tags", []),
                    "smokeSubset": entry.get("smoke_subset", False), "origin": entry.get("origin"),
                    "previewKind": label}
        cases.append({"id": _slug(entry["id"]), "title": f"{entry['id']} · {_text(entry.get('category', 'Photo')).replace('_', ' ')}",
                      "category": entry.get("category", "photo"), "split": entry.get("split", "development"),
                      "format": original.get("format", ""), "intent": _text(entry.get("reason")),
                      "limits": "This is a source catalogue preview. Add native baseline and candidate renders before evaluating an edit.",
                      "aligned": False, "variants": [{"id": "source-preview", "label": label, "role": "reference",
                          "image": paths.media(preview["path"], source.parent),
                          "description": "Browsing reference; it does not establish the unedited native rendering or edit quality."}],
                      "regions": [], "metadata": metadata})
    return cases


def load_legacy(source: Path, media_root: Path, dataset_id: str, title: str | None = None,
                path_maps: list[tuple[str, str]] | None = None) -> dict:
    """Import a gallery manifest, a run cases directory, or a source suite manifest.

    Returns a dataset only. Existing approvals remain historical metadata because
    the importing process is not a new user review of the current rendered bytes.
    """
    source = Path(source).resolve()
    paths = _Paths(media_root, path_maps)
    if source.is_dir():
        case_dir = source / "cases" if (source / "cases").is_dir() else source
        files = sorted(case_dir.glob("*.json"))
        cases = _state_cases(files, paths)
        inferred_title = source.name.replace("-", " ")
    else:
        data = _embedded_data(source) if source.suffix.lower() in {".html", ".htm"} else _read(source)
        if isinstance(data, dict) and isinstance(data.get("assets"), dict) and isinstance(data.get("cases"), list) and all("before" in case for case in data["cases"]):
            cases = _embedded_gallery(data, source, paths)
        elif isinstance(data, dict) and isinstance(data.get("assets"), list):
            cases = _suite(data, source, paths)
        elif isinstance(data, dict) and isinstance(data.get("cases"), list):
            cases = _gallery(data, source, paths)
        elif isinstance(data, dict) and data.get("candidate"):
            cases = _state_cases([source], paths)
        else:
            raise ValueError("Unsupported legacy source; use a gallery manifest, suite manifest, or run cases directory")
        inferred_title = data.get("title") or data.get("suite_id") or source.parent.name.replace("-", " ")
    if not cases:
        raise ValueError("The legacy source contains no available review cases")
    _mark_native_regions(cases, paths)
    description = "Imported review material. Historical decisions are retained as context; record current approvals in this workspace."
    if paths.warnings:
        description += f" {len(paths.warnings)} missing optional artifacts were omitted."
    return {"schemaVersion": 1, "id": dataset_id, "title": title or inferred_title,
            "description": description, "cases": cases}
