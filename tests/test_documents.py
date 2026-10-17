"""Local generated-PDF checks; these make no claim about a Spark installation."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import fitz

from probe.documents import create_vision_cases, prepare_source


class DocumentPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pdf = self.root / "two-pages.pdf"
        with fitz.open() as doc:
            first = doc.new_page(width=300, height=400)
            first.insert_text((30, 50), "FIRST PAGE: x - 1 = 0", fontsize=12)
            second = doc.new_page(width=300, height=400)
            second.insert_text((30, 50), "SECOND PAGE: table a=1 b=2", fontsize=12)
            second.set_rotation(90)
            doc.set_page_labels([{"startpage": 0, "style": "r", "firstpagenum": 4}])
            doc.set_metadata({"title": "Synthetic plumbing fixture, not OCR gold"})
            doc.save(self.pdf)

    def tearDown(self):
        self.temp.cleanup()

    def test_selected_page_identity_labels_text_and_hashes(self):
        before = hashlib.sha256(self.pdf.read_bytes()).hexdigest()
        result = prepare_source(self.pdf, self.root / "chapter", 2, 2, "book-chapter")
        manifest = result["manifest"]
        self.assertEqual(manifest["original"]["sha256"], before)
        self.assertEqual(manifest["original"]["physical_page_count"], 2)
        self.assertFalse(manifest["selection"]["whole_original_selected"])
        self.assertEqual([p["scope"] for p in manifest["page_ledger"]], ["outside_selected_scope", "selected"])
        record = manifest["pages"][0]
        self.assertEqual(record["original_physical_page_1based"], 2)
        self.assertEqual(record["selected_page_1based"], 1)
        self.assertEqual(record["pdf_catalogue_label"], "v")
        self.assertIsNone(record["printed_page_label"])
        self.assertEqual(record["geometry"]["rotation_degrees"], 90)
        root = Path(result["output_dir"])
        text = json.loads((root / record["native_evidence"]["path"]).read_text())
        self.assertIn("SECOND PAGE", text["text"])
        self.assertNotIn("FIRST PAGE", text["text"])
        self.assertTrue(text["characters"]["blocks"])
        for artifact in (record["native_evidence"], record["preview"], manifest["metadata"], manifest["selected_pdf"]):
            self.assertEqual(hashlib.sha256((root / artifact["path"]).read_bytes()).hexdigest(), artifact["sha256"])
        with fitz.open(result["source_pdf_path"]) as selected:
            self.assertEqual(selected.page_count, 1)
            self.assertEqual(selected[0].get_label(), "v")
            self.assertEqual(selected[0].rotation, 90)
        self.assertEqual(hashlib.sha256(self.pdf.read_bytes()).hexdigest(), before)

    def test_complete_selection(self):
        manifest = prepare_source(self.pdf, self.root / "paper")["manifest"]
        self.assertTrue(manifest["selection"]["whole_original_selected"])
        self.assertEqual(len(manifest["pages"]), 2)

    def test_full_page_image_and_hidden_text_do_not_imply_native_quality(self):
        image_pdf = self.root / "image-backed.pdf"
        pixels = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 10, 10), False)
        pixels.clear_with(255)
        with fitz.open() as doc:
            page = doc.new_page(width=300, height=400)
            page.insert_image(page.rect, stream=pixels.tobytes("png"), keep_proportion=False)
            page.insert_text((30, 50), "corrupted hidden OCR x plus instead of minus", render_mode=3)
            page.set_rotation(90)
            doc.save(image_pdf)
        manifest = prepare_source(image_pdf, self.root / "image-run")["manifest"]
        classification = manifest["pages"][0]["classification"]
        self.assertTrue(classification["image_backed"])
        self.assertTrue(classification["native_text_present"])
        self.assertTrue(classification["ocr_recommended"])
        self.assertFalse(classification["native_text_is_verified_ground_truth"])
        self.assertAlmostEqual(classification["largest_single_image_page_fraction"], 1.0)

    def test_rejects_bounds_without_creating_output(self):
        for index, (first, last) in enumerate([(0, 1), (1, 3), (2, 1), (-1, None), (True, 1), (1, 1.5)]):
            target = self.root / f"bad-{index}"
            with self.assertRaises(ValueError):
                prepare_source(self.pdf, target, first, last)
            self.assertFalse(target.exists())

    def test_no_overwrite_existing_directory_or_source(self):
        target = self.root / "existing"
        target.mkdir()
        marker = target / "keep"
        marker.write_text("do not overwrite")
        with self.assertRaises(FileExistsError):
            prepare_source(self.pdf, target)
        self.assertEqual(marker.read_text(), "do not overwrite")
        before = self.pdf.read_bytes()
        with self.assertRaises(FileExistsError):
            prepare_source(self.pdf, self.pdf)
        self.assertEqual(self.pdf.read_bytes(), before)

    def test_refuses_output_symlink(self):
        real = self.root / "real"
        real.mkdir()
        link = self.root / "link"
        link.symlink_to(real, target_is_directory=True)
        with self.assertRaises(FileExistsError):
            prepare_source(self.pdf, link)
        self.assertTrue(link.is_symlink())
        self.assertEqual(list(real.iterdir()), [])

    def test_rotated_review_crop_has_explicit_frame(self):
        result = prepare_source(self.pdf, self.root / "crop-run", 2, 2,
                                review_crops=[{"physical_page_1based": 2, "bbox": [0, 0, 200, 100], "id": "chosen"}])
        crop = result["manifest"]["review_crops"][0]
        self.assertEqual(crop["coordinate_frame"], "displayed page points")
        self.assertEqual((crop["width"], crop["height"]), (500, 250))
        self.assertTrue((Path(result["output_dir"]) / crop["path"]).is_file())

    def test_invalid_crop_ids_and_regions(self):
        bad = [
            {"physical_page_1based": 1, "bbox": [0, 0, 20, 20], "id": "../bad"},
            {"physical_page_1based": 2, "bbox": [0, 0, 20, 20]},
            {"physical_page_1based": 1, "bbox": [0, 0, 9999, 20]},
            {"physical_page_1based": 1, "bbox": [0, 0, float("nan"), 20]},
        ]
        for index, spec in enumerate(bad):
            with self.assertRaises(ValueError):
                prepare_source(self.pdf, self.root / f"bad-crop-{index}", 1, 1, review_crops=[spec])

    def test_encryption_rejected_without_output(self):
        encrypted = self.root / "encrypted.pdf"
        with fitz.open(self.pdf) as doc:
            doc.save(encrypted, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="reader")
        target = self.root / "encrypted-run"
        with self.assertRaisesRegex(ValueError, "Encrypted"):
            prepare_source(encrypted, target)
        self.assertFalse(target.exists())

    def test_vision_cases_distinct_random_readings_and_blank(self):
        cases = create_vision_cases(self.root / "vision")
        readings = [case["expected"] for case in cases if case["kind"] == "digits"]
        self.assertEqual(len(readings), 3)
        self.assertEqual(len(set(readings)), 3)
        self.assertTrue(all(len(value) == 6 and value.isdigit() for value in readings))
        blank = [case for case in cases if case["kind"] == "blank"]
        self.assertEqual(len(blank), 1)
        self.assertEqual(blank[0]["expected"], "")
        for case in cases:
            image = Path(case["image_path"])
            self.assertTrue(image.is_file())
            self.assertNotIn(case["expected"], image.name) if case["expected"] else None
        with self.assertRaises(FileExistsError):
            create_vision_cases(self.root / "vision")


if __name__ == "__main__":
    unittest.main()
