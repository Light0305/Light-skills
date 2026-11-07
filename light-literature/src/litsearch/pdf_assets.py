from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


def estimate_pages(pdf_path: str | Path) -> int:
    """Count pages locally; return a best-effort estimate if no reader succeeds."""
    path = Path(pdf_path)
    try:
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(path))
        try:
            return len(doc)
        finally:
            doc.close()
    except Exception:  # noqa: BLE001
        pass
    try:
        return len(re.findall(rb"/Type\s*/Page\b", path.read_bytes()))
    except OSError:
        return 0


def _write_manifest(article_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest["status"] == "ok" and any(isinstance(p, dict) for p in manifest["pages"]):
        manifest["status"] = "partial"
    (article_dir / "pdf_assets.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def _base_manifest(dpi: int) -> dict[str, Any]:
    return {
        "status": "ok",
        "dpi": dpi,
        "pages": [],
        "images": [],
    }


def _close_quietly(obj: Any) -> None:
    close = getattr(obj, "close", None)
    if close is None:
        return
    try:
        close()
    except Exception:  # noqa: BLE001
        pass


def _render_with_pdfium(
    pdf_path: Path,
    article_dir: Path,
    pages_dir: Path,
    images_dir: Path,
    dpi: int,
) -> dict[str, Any]:
    """Render pages and extract image objects with pypdfium2 (BSD/Apache-licensed).

    pypdfium2 sees image objects nested in Form XObjects, so it often returns a
    complete figure where PyMuPDF's page.get_images() returns only fragments.
    """
    import pypdfium2 as pdfium

    manifest = _base_manifest(dpi)
    version = getattr(getattr(pdfium, "version", None), "PYPDFIUM_INFO", "")
    manifest["renderer"] = f"pypdfium2 {version}".strip()
    doc = pdfium.PdfDocument(str(pdf_path))
    seen_hashes: set[str] = set()
    scale = dpi / 72.0
    try:
        for index in range(1, len(doc) + 1):
            page = doc[index - 1]
            try:
                page_png = pages_dir / f"page_{index:03d}.png"
                try:
                    bitmap = page.render(scale=scale)
                    try:
                        image = bitmap.to_pil()
                        try:
                            image.save(page_png, format="PNG")
                        finally:
                            _close_quietly(image)
                    finally:
                        _close_quietly(bitmap)
                    manifest["pages"].append(str(page_png.relative_to(article_dir)))
                except Exception as exc:  # noqa: BLE001
                    manifest["pages"].append({"page": index, "error": str(exc)})

                image_index = 0
                try:
                    objects = page.get_objects(filter=[pdfium.raw.FPDF_PAGEOBJ_IMAGE])
                    for obj in objects:
                        if not isinstance(obj, pdfium.PdfImage):
                            _close_quietly(obj)
                            continue
                        image_index += 1
                        try:
                            bitmap = obj.get_bitmap(render=True)
                            try:
                                image = bitmap.to_pil()
                                try:
                                    digest = hashlib.sha256(
                                        f"{image.mode}:{image.size}:".encode("utf-8")
                                        + image.tobytes()
                                    ).hexdigest()
                                    if digest in seen_hashes:
                                        continue
                                    seen_hashes.add(digest)
                                    target = images_dir / f"page_{index:03d}_img_{image_index}.png"
                                    image.save(target, format="PNG")
                                    manifest["images"].append(
                                        str(target.relative_to(article_dir))
                                    )
                                finally:
                                    _close_quietly(image)
                            finally:
                                _close_quietly(bitmap)
                        except Exception as exc:  # noqa: BLE001
                            manifest["images"].append(
                                {
                                    "page": index,
                                    "image": image_index,
                                    "error": str(exc),
                                }
                            )
                        finally:
                            _close_quietly(obj)
                except Exception as exc:  # noqa: BLE001
                    manifest["images"].append({"page": index, "error": str(exc)})
            finally:
                _close_quietly(page)
    finally:
        _close_quietly(doc)
    return _write_manifest(article_dir, manifest)


def _render_with_pymupdf(
    pdf_path: Path,
    article_dir: Path,
    pages_dir: Path,
    images_dir: Path,
    dpi: int,
) -> dict[str, Any]:
    """Fallback renderer using PyMuPDF (AGPL-3.0/commercial; optional extra)."""
    import fitz  # PyMuPDF

    manifest = _base_manifest(dpi)
    version = getattr(fitz, "VersionBind", "") or getattr(fitz, "__version__", "")
    manifest["renderer"] = f"PyMuPDF {version}".strip()
    doc = fitz.open(str(pdf_path))
    seen_xrefs: set[int] = set()
    try:
        for index, page in enumerate(doc, start=1):
            page_png = pages_dir / f"page_{index:03d}.png"
            try:
                pix = page.get_pixmap(dpi=dpi)
                pix.save(str(page_png))
                manifest["pages"].append(str(page_png.relative_to(article_dir)))
            except Exception as exc:  # noqa: BLE001
                manifest["pages"].append({"page": index, "error": str(exc)})
            try:
                for image_index, image in enumerate(page.get_images(full=True), start=1):
                    xref = int(image[0])
                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)
                    extracted = doc.extract_image(xref)
                    ext = str(extracted.get("ext") or "png").lower()
                    if ext not in {"png", "jpg", "jpeg", "webp"}:
                        ext = "png"
                    target = images_dir / f"page_{index:03d}_img_{image_index}.{ext}"
                    target.write_bytes(extracted["image"])
                    manifest["images"].append(str(target.relative_to(article_dir)))
            except Exception as exc:  # noqa: BLE001
                manifest["images"].append({"page": index, "error": str(exc)})
    finally:
        doc.close()
    return _write_manifest(article_dir, manifest)


def render_pdf_assets(
    pdf_path: str | Path,
    article_dir: str | Path,
    *,
    dpi: int = 150,
) -> dict[str, Any]:
    """Render each PDF page to PNG and extract embedded images.

    Used by the host-model reading workflow so the multimodal model can read page
    images directly. pypdfium2 is the default renderer and is installed with the
    package; PyMuPDF is an optional fallback. Returns a small manifest and never
    raises on a single bad image.
    """
    pdf_path = Path(pdf_path)
    article_dir = Path(article_dir)
    pages_dir = article_dir / "pages"
    images_dir = article_dir / "images"
    pages_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    pdfium_error = "not installed"
    try:
        return _render_with_pdfium(pdf_path, article_dir, pages_dir, images_dir, dpi)
    except ImportError:
        pass
    except Exception as exc:  # noqa: BLE001
        pdfium_error = str(exc)
    else:
        pdfium_error = ""

    try:
        return _render_with_pymupdf(pdf_path, article_dir, pages_dir, images_dir, dpi)
    except ImportError:
        pymupdf_error = "PyMuPDF is not installed"
    except Exception as exc:  # noqa: BLE001
        pymupdf_error = str(exc)
    else:
        pymupdf_error = ""

    manifest = _base_manifest(dpi)
    manifest.update(
        {
            "status": "unavailable",
            "reason": (
                f"pypdfium2: {pdfium_error or 'not installed'}; "
                f"PyMuPDF: {pymupdf_error or 'not installed'}. "
                "Install with `pip install pypdfium2 Pillow` (default) or "
                '`pip install "litsearch[pdf]"` (PyMuPDF fallback).'
            ),
        }
    )
    return _write_manifest(article_dir, manifest)
