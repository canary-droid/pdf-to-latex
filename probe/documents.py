"""Local PDF evidence preparation; this module performs no OCR or model calls.

PyMuPDF is imported lazily so controller-only commands need not load it. Output
directories must be new. A selected PDF is a derivative snapshot, not a claim to
preserve document-level signatures, attachments or links outside the selection.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
from datetime import datetime, timezone
from typing import Any


def _fitz():
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF preparation requires PyMuPDF in this isolated environment") from exc
    return fitz


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    # Exclusive creation also protects individual files against accidental reuse.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _new_directory(path: str | Path) -> Path:
    raw = Path(path).expanduser()
    if raw.exists() or raw.is_symlink():
        raise FileExistsError(f"Output already exists; use a fresh run directory: {raw}")
    parent = raw.parent.resolve(strict=True)
    target = parent / raw.name
    # exist_ok=False provides the atomic reservation; never replace a directory.
    target.mkdir(mode=0o700)
    return target


def _artifact(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
    }


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _classify_page(page, native_text: str) -> dict[str, Any]:
    """Cheap routing evidence, deliberately not a mathematical-quality score."""
    fitz = _fitz()
    unrotated = page.rect * page.derotation_matrix
    area = unrotated.width * unrotated.height
    images = page.get_image_info(hashes=False, xrefs=False)
    largest = 0.0
    for item in images:
        overlap = fitz.Rect(item["bbox"]) & unrotated
        if not overlap.is_empty and area > 0:
            largest = max(largest, overlap.width * overlap.height / area)
    image_backed = largest >= 0.8
    native_present = bool(native_text.strip())
    return {
        "image_backed": image_backed,
        "image_count": len(images),
        "largest_single_image_page_fraction": largest,
        "image_backed_threshold": 0.8,
        "native_text_present": native_present,
        "native_character_count": len(native_text),
        "ocr_recommended": image_backed or not native_present,
        "native_text_is_verified_ground_truth": False,
        "note": "Routing heuristic only. Full-page imagery can coexist with damaged hidden OCR; selectable text is not mathematical ground truth. Tiled scans may evade the single-image heuristic.",
    }


def _crop_specs(doc, items, first: int, last: int) -> list[dict[str, Any]]:
    result = []
    ids = set()
    for index, item in enumerate(items or []):
        if not isinstance(item, dict):
            raise ValueError("Each review crop must be an object")
        page_no = _integer(item.get("physical_page_1based"), "crop physical_page_1based")
        if not first <= page_no <= last:
            raise ValueError("Review crop page is outside the selected original page range")
        crop_id = item.get("id", f"crop-{index + 1:04d}")
        if not isinstance(crop_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", crop_id):
            raise ValueError("Crop IDs must be safe short alphanumeric names")
        if crop_id in ids:
            raise ValueError("Duplicate review crop ID")
        ids.add(crop_id)
        bounds = item.get("bbox")
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 4:
            raise ValueError("Crop bbox must contain four displayed-page PDF-point coordinates")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in bounds):
            raise ValueError("Crop bbox coordinates must be finite numbers")
        x0, y0, x1, y1 = bounds
        page_rect = doc[page_no - 1].rect
        if not (page_rect.x0 <= x0 < x1 <= page_rect.x1 and page_rect.y0 <= y0 < y1 <= page_rect.y1):
            raise ValueError("Crop bbox must lie inside the displayed page")
        result.append({"id": crop_id, "physical_page_1based": page_no, "bbox": list(bounds)})
    return result


def prepare_source(
    pdf_path: str | Path,
    output_dir: str | Path,
    page_start: int = 1,
    page_end: int | None = None,
    label: str = "paper",
    *,
    review_crops: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Prepare exact page selection and local evidence without overwriting outputs.

    Bounds are original physical PDF pages, one-based and inclusive. No OCR,
    mathematical validation, chapter inference or external access is performed.
    ``review_crops`` use displayed-page PDF points (the frame shown by previews),
    not native extraction coordinates. Recorded matrices connect the two frames.
    Catalogue labels are retained, but visually printed page numbers are unknown.
    """
    fitz = _fitz()
    source = Path(pdf_path).expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError("Input must be a PDF file")
    if not isinstance(label, str) or not label.strip():
        raise ValueError("label must be a non-empty string")
    first = _integer(page_start, "page_start")
    original_stat = source.stat()
    original_hash = _sha256(source)
    root = None
    try:
        with fitz.open(source) as doc:
            if not doc.is_pdf:
                raise ValueError("Input is not a PDF document")
            if doc.needs_pass or doc.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported by this probe; supply an authorised unencrypted copy")
            count = doc.page_count
            last = count if page_end is None else _integer(page_end, "page_end")
            if not (1 <= first <= last <= count):
                raise ValueError(f"Page range must satisfy 1 <= start <= end <= {count}")
            crop_specs = _crop_specs(doc, review_crops, first, last)
            page_labels = [doc[i].get_label() or None for i in range(count)]
            metadata = {
                "source_sha256": original_hash,
                "pdf_metadata": doc.metadata,
                "pdf_page_label_rules": doc.get_page_labels(),
                "physical_page_count": count,
                "label_note": "Catalogue labels are not verified visually printed page numbers.",
            }
            root = _new_directory(output_dir)
            (root / "native").mkdir()
            (root / "previews").mkdir()
            (root / "crops").mkdir()
            _write_json(root / "metadata.json", metadata)
            selected_path = root / "source.pdf"
            with fitz.open() as selected:
                selected.insert_pdf(doc, from_page=first - 1, to_page=last - 1)
                # Store explicit source catalogue labels, not renumbered labels.
                label_rules = [
                    {"startpage": i, "prefix": page_labels[original - 1] or "", "style": ""}
                    for i, original in enumerate(range(first, last + 1))
                ]
                selected.set_page_labels(label_rules)
                selected.set_metadata(doc.metadata)
                selected.save(selected_path, garbage=4, deflate=True)
            pages = []
            raw_flags = fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES
            for selected_index, original_page in enumerate(range(first, last + 1)):
                page = doc[original_page - 1]
                native_text = page.get_text("text", sort=False)
                classification = _classify_page(page, native_text)
                stem = f"page-{original_page:06d}"
                evidence_path = root / "native" / f"{stem}.json"
                preview_path = root / "previews" / f"{stem}.png"
                geometry = {
                    "rotation_degrees": page.rotation,
                    "displayed_rect_points": list(page.rect),
                    "cropbox_points": list(page.cropbox),
                    "mediabox_points": list(page.mediabox),
                    "rotation_matrix": list(page.rotation_matrix),
                    "derotation_matrix": list(page.derotation_matrix),
                    "native_coordinate_frame": "PyMuPDF unrotated page coordinates in points",
                    "preview_coordinate_frame": "displayed (rotated) page coordinates in points",
                }
                evidence = {
                    "source_sha256": original_hash,
                    "original_physical_page_1based": original_page,
                    "original_page_index0": original_page - 1,
                    "selected_page_1based": selected_index + 1,
                    "pdf_catalogue_label": page_labels[original_page - 1],
                    "printed_page_label": None,
                    "geometry": geometry,
                    "classification": classification,
                    "extraction_status": "native_evidence_only_not_verified_transcription",
                    "text": native_text,
                    "words": page.get_text("words", sort=False),
                    "characters": page.get_text("rawdict", flags=raw_flags, sort=False),
                }
                _write_json(evidence_path, evidence)
                preview = page.get_pixmap(dpi=120, colorspace=fitz.csRGB, alpha=False, annots=True)
                preview.save(preview_path)
                pages.append({
                    "original_physical_page_1based": original_page,
                    "selected_page_1based": selected_index + 1,
                    "pdf_catalogue_label": page_labels[original_page - 1],
                    "printed_page_label": None,
                    "geometry": geometry,
                    "classification": classification,
                    "native_evidence": _artifact(evidence_path, root),
                    "preview": {**_artifact(preview_path, root), "dpi": 120, "width": preview.width, "height": preview.height},
                })
            crops = []
            for spec in crop_specs:
                page = doc[spec["physical_page_1based"] - 1]
                path = root / "crops" / f"{spec['id']}.png"
                crop = page.get_pixmap(dpi=180, clip=fitz.Rect(spec["bbox"]), colorspace=fitz.csRGB, alpha=False, annots=True)
                crop.save(path)
                crops.append({**spec, "coordinate_frame": "displayed page points", "dpi": 180,
                              "width": crop.width, "height": crop.height, **_artifact(path, root)})
            current = source.stat()
            if ((current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns)
                    != (original_stat.st_dev, original_stat.st_ino, original_stat.st_size, original_stat.st_mtime_ns)
                    or _sha256(source) != original_hash):
                raise RuntimeError("Source changed during preparation; no completed preparation was published")
            manifest = {
                "schema_version": 1,
                "kind": "source_preparation",
                "label": label,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "prepared_not_converted_or_verified",
                "pymupdf_version": fitz.VersionBind,
                "original": {"path": str(source), "sha256": original_hash,
                             "size_bytes": original_stat.st_size, "physical_page_count": count,
                             "original_file_copied": False},
                "selection": {"page_start_1based": first, "page_end_1based": last,
                              "selected_page_count": last - first + 1, "whole_original_selected": first == 1 and last == count},
                "selected_pdf": {**_artifact(selected_path, root),
                                 "note": "Selected-page derivative; original full-file hash remains authoritative. Document-level signatures/attachments and out-of-range links are not promised."},
                "metadata": _artifact(root / "metadata.json", root),
                "page_ledger": [
                    {"original_physical_page_1based": i, "original_page_index0": i - 1,
                     "pdf_catalogue_label": page_labels[i - 1], "printed_page_label": None,
                     "scope": "selected" if first <= i <= last else "outside_selected_scope",
                     "selected_page_1based": i - first + 1 if first <= i <= last else None}
                    for i in range(1, count + 1)
                ],
                "pages": pages,
                "review_crops": crops,
            }
            _write_json(root / "manifest.json", manifest)
        return {"output_dir": str(root), "manifest_path": str(root / "manifest.json"),
                "source_pdf_path": str(selected_path), "manifest": manifest}
    except Exception:
        if root is not None:
            # This directory was exclusively created by this invocation.
            shutil.rmtree(root)
        raise


def create_vision_cases(out_dir: str | Path) -> list[dict[str, Any]]:
    """Create three randomized six-digit images and a blank control, all local.

    Expected values are returned for the local scorer only; do not put them in
    prompts. These test image transport/basic reading, not mathematical OCR quality.
    """
    fitz = _fitz()
    root = _new_directory(out_dir)
    cases = []
    seen = set()
    try:
        for index in range(4):
            expected = ""
            if index < 3:
                while not expected or expected in seen:
                    expected = "".join(secrets.choice("0123456789") for _ in range(6))
                seen.add(expected)
            case_id = f"case-{index + 1:02d}"
            image_path = root / f"{case_id}.png"
            with fitz.open() as doc:
                page = doc.new_page(width=480, height=160)
                if expected:
                    page.insert_text((75, 105), expected, fontsize=72, fontname="cour", color=(0, 0, 0))
                page.get_pixmap(dpi=120, colorspace=fitz.csRGB, alpha=False).save(image_path)
            cases.append({"case_id": case_id, "image_path": str(image_path),
                          "expected": expected, "kind": "digits" if expected else "blank",
                          "sha256": _sha256(image_path)})
        _write_json(root / "manifest.json", {"schema_version": 1,
                    "purpose": "image_transport_and_basic_reading_not_mathematical_OCR_gold", "cases": cases})
        return cases
    except Exception:
        shutil.rmtree(root)
        raise
