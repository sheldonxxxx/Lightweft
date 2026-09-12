"""Source-faithful adapters for historical photo review material."""

import base64
import json
import tempfile
import unittest
from pathlib import Path

from review.import_legacy import load_legacy


class LegacyImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.media = self.root / "media"
        self.media.mkdir()
        for name in ("base.jpg", "first.jpg", "current.jpg", "base-detail.png", "first-detail.png", "current-detail.png"):
            (self.media / name).write_bytes(b"fixture image bytes")

    def write(self, name, value):
        target = self.media / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value), encoding="utf-8")
        return target

    def gallery(self, prefix=""):
        region = {"x": 10, "y": 20, "width": 640, "height": 480}
        return {"cases": [{"id": "one", "title": "One photo", "variants": [
            {"id": "base", "status": "baseline", "views": {
                "overview": {"path": prefix + "base.jpg", "width": 2400, "height": 1600},
                "sky": {"path": prefix + "base-detail.png", "region": region}}},
            {"id": "edit", "status": "accepted", "views": {
                "overview": {"path": prefix + "current.jpg", "width": 2400, "height": 1600},
                "sky": {"path": prefix + "current-detail.png", "region": region}}}]}]}

    def test_explicit_mapping_and_historical_status_do_not_create_approval(self):
        source = self.write("gallery.json", self.gallery("/previous-workspace/"))
        result = load_legacy(source, self.media, "test", path_maps=[("/previous-workspace", str(self.media))])
        case = result["cases"][0]
        self.assertEqual(case["variants"][1]["image"], "current.jpg")
        self.assertEqual(case["metadata"]["historicalVariantStatuses"]["edit"], "accepted")
        self.assertNotIn("feedback", result)
        self.assertNotIn("decision", case["variants"][1])
        self.assertFalse(case["aligned"])
        self.assertFalse(case["regions"][0]["aligned"])
        self.assertEqual({entry["variantId"] for entry in case["regions"][0]["images"]}, {"base", "edit"})

    def test_missing_path_mapping_rejects_unmapped_absolute_media(self):
        source = self.write("gallery.json", self.gallery("/previous-workspace/"))
        with self.assertRaisesRegex(ValueError, "outside --media-root"):
            load_legacy(source, self.media, "test")
        with self.assertRaisesRegex(ValueError, "destination must be an absolute path"):
            load_legacy(source, self.media, "test", path_maps=[("/previous-workspace", ".")])

    def test_historical_reference_does_not_become_current_candidate(self):
        data = self.gallery()
        data['cases'][0]['variants'].append({'id': 'earlier', 'status': 'tested', 'views': {'overview': {'path': 'base.jpg'}}})
        result = load_legacy(self.write('gallery.json', data), self.media, 'test')
        self.assertEqual([v['id'] for v in result['cases'][0]['variants'] if v['role'] == 'candidate'], ['edit'])
        self.assertEqual(result['cases'][0]['variants'][-1]['role'], 'reference')
        self.assertNotIn('feedback', result)

    def test_matching_current_export_gets_its_own_latest_crop(self):
        absolute = lambda name: str(self.media / name)
        region = {"x": 100, "y": 200, "width": 640, "height": 640}
        source = self.write("cases/01.json", {"id": "01", "category": "wildlife", "baseline": absolute("base.jpg"),
            "candidate": absolute("current.jpg"), "revision_round": "r2",
            "user_review": {"decision": "Accept", "note": "Earlier edit", "reviewed_candidate_sha256": "old-bytes"},
            "events": [
                {"stage": "apply", "label": "first", "export": absolute("first.jpg")},
                {"stage": "review", "label": "first", "region": region,
                 "images": [absolute("base-detail.png"), absolute("first-detail.png")]},
                {"stage": "apply", "label": "revised", "export": absolute("current.jpg")},
                {"stage": "review", "label": "revised", "region": region,
                 "images": [absolute("base-detail.png"), absolute("current-detail.png")]},
            ]})
        result = load_legacy(source.parent, self.media, "test")
        case = result["cases"][0]
        images = {item["variantId"]: item["image"] for item in case["regions"][0]["images"]}
        self.assertEqual(images["candidate"], "current-detail.png")
        self.assertEqual(images["earlier-1"], "first-detail.png")
        self.assertEqual(case["metadata"]["historicalReview"]["decision"], "Accept")
        self.assertEqual(case["metadata"]["revisionRound"], "r2")
        self.assertNotIn("feedback", result)

    def test_symlink_alias_is_rejected_even_when_target_is_inside_media_root(self):
        (self.media / "alias.jpg").symlink_to(self.media / "current.jpg")
        gallery = self.gallery()
        gallery["cases"][0]["variants"][1]["views"]["overview"]["path"] = "alias.jpg"
        source = self.write("gallery.json", gallery)
        with self.assertRaisesRegex(ValueError, "must not use symlinks"):
            load_legacy(source, self.media, "test")

    def test_symlink_escape_is_rejected(self):
        (self.root / "outside.jpg").write_bytes(b"outside")
        (self.media / "alias.jpg").symlink_to(self.root / "outside.jpg")
        gallery = self.gallery()
        gallery["cases"][0]["variants"][1]["views"]["overview"]["path"] = "alias.jpg"
        source = self.write("gallery.json", gallery)
        with self.assertRaisesRegex(ValueError, "outside --media-root"):
            load_legacy(source, self.media, "test")

    def test_source_suite_is_reference_only(self):
        source = self.write("suite.json", {"suite_id": "private-collection", "assets": [
            {"id": "one", "category": "landscape", "original": {"format": "DNG"},
             "preview": {"path": "base.jpg", "kind": "Remote browsing preview"}}
        ]})
        case = load_legacy(source, self.media, "test")["cases"][0]
        self.assertEqual(case["variants"][0]["role"], "reference")
        self.assertEqual(case["variants"][0]["label"], "Remote browsing preview")
        self.assertEqual(case["regions"], [])

    def test_native_regions_require_recorded_crop_size_to_equal_encoded_pixels(self):
        png = lambda w, h: b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + w.to_bytes(4, "big") + h.to_bytes(4, "big")
        (self.media / "base-detail.png").write_bytes(png(640, 480))
        (self.media / "current-detail.png").write_bytes(png(640, 480))
        source = self.write("gallery.json", self.gallery())
        region = load_legacy(source, self.media, "test")["cases"][0]["regions"][0]
        self.assertTrue(region["native"])
        self.assertFalse(region["aligned"])
        self.assertEqual(region["nativeDomain"], "recorded-render-region")
        (self.media / "current-detail.png").write_bytes(png(320, 240))
        region = load_legacy(source, self.media, "test")["cases"][0]["regions"][0]
        self.assertFalse(region["native"])

    def test_embedded_review_reuses_exact_existing_bytes_and_preserves_crop_context(self):
        embedded = lambda name: "data:image/jpeg;base64," + base64.b64encode(name).decode("ascii")
        (self.media / "baselines").mkdir()
        (self.media / "baselines/one.jpg").write_bytes(b"baseline bytes")
        (self.media / "exports").mkdir()
        (self.media / "exports/edit.jpg").write_bytes(b"edited bytes")
        data = {"assets": {
            "before": {"src": embedded(b"baseline bytes"), "width": 100, "height": 100},
            "final": {"src": embedded(b"edited bytes"), "width": 50, "height": 50}},
            "cases": [{"id": "one", "title": "Historical crop", "before": "before", "sourceWidth": 100, "sourceHeight": 100,
                       "variants": [{"key": "final", "label": "Selected", "sliderAvailable": True,
                                     "crop": {"x": 25, "y": 25, "width": 50, "height": 50}, "geometryChanged": []}]}]}
        source = self.media / "old.html"
        source.write_text('<script>throw new Error("must not execute")</script><script type="application/json" id="galleryData">' + json.dumps(data) + '</script>')
        before = {p.relative_to(self.media): p.read_bytes() for p in self.media.rglob("*") if p.is_file()}
        result = load_legacy(source, self.media, "test")
        case = result["cases"][0]
        self.assertEqual(case["variants"][0]["image"], "baselines/one.jpg")
        self.assertEqual(case["variants"][1]["image"], "exports/edit.jpg")
        self.assertFalse(case["aligned"])
        self.assertEqual(case["metadata"]["historicalVariantGeometry"]["final"]["crop"]["x"], 25)
        self.assertEqual(before, {p.relative_to(self.media): p.read_bytes() for p in self.media.rglob("*") if p.is_file()})
        (self.media / "exports/edit.jpg").write_bytes(b"changed export")
        with self.assertRaisesRegex(ValueError, "no byte-identical existing export"):
            load_legacy(source, self.media, "test")

    def test_embedded_review_does_not_evaluate_javascript_payload(self):
        source = self.media / "old.html"
        source.write_text('<script id="galleryData">JSON.parse("{}")</script>')
        with self.assertRaises(json.JSONDecodeError):
            load_legacy(source, self.media, "test")


if __name__ == "__main__":
    unittest.main()
