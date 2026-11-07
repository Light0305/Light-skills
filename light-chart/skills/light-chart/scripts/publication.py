"""Compose the migrated export, geometry and PDF checks into one callable workflow."""
from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from pathlib import Path


def write_json(path, value):
    def clean(item):
        if isinstance(item, dict):
            return {str(k): clean(v) for k, v in item.items()}
        if isinstance(item, (tuple, list)):
            return [clean(v) for v in item]
        if isinstance(item, float) and not math.isfinite(item):
            return None
        if hasattr(item, "item"):
            return clean(item.item())
        return item
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def normalize_cairo_page(pdf, target_inches):
    """Correct Cairo's sub-point page rounding without rescaling any plotted content.

    Refuse changes larger than one point: this is a device rounding correction,
    not a general crop/resize operation. Preserve the top-left content position.
    """
    from pypdf import PdfReader, PdfWriter, Transformation
    from pypdf.generic import RectangleObject
    pdf = Path(pdf)
    reader = PdfReader(str(pdf))
    if len(reader.pages) != 1:
        raise ValueError("Cairo page normalization requires a one-page figure")
    page = reader.pages[0]
    before = [float(page.mediabox.width), float(page.mediabox.height)]
    target = [float(value) * 72 for value in target_inches]
    if any(not math.isfinite(value) or value <= 0 for value in target):
        raise ValueError("Target page dimensions must be finite and positive")
    if any(abs(a-b) > 1.01 for a,b in zip(before,target)):
        raise ValueError("Page differs by more than Cairo's one-point rounding; refusing correction")
    page.add_transformation(Transformation().translate(ty=target[1]-before[1]))
    page.mediabox = RectangleObject([0, 0, *target])
    page.cropbox = RectangleObject([0, 0, *target])
    writer = PdfWriter()
    writer.add_page(page)
    descriptor, temporary = tempfile.mkstemp(prefix=".page-", suffix=".pdf", dir=pdf.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            writer.write(handle)
        os.replace(temporary, pdf)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return {"method": "Cairo sub-point MediaBox correction; no content scaling",
            "before_pt": before, "after_pt": target}


def audit_exported(pdf, *, raster=None, target_inches=None, min_font_pt=None, additional_exports=()):
    from project_style import current_project
    if min_font_pt is None:
        min_font_pt = current_project()['typography']['minimum_pt']
    from check_figure import check_figure
    from audit_pdf_text import audit_pdf
    from audit_figure_collisions import audit_pdf as collision_audit
    pdf = Path(pdf)
    files = {}
    failed, warnings, unavailable = [], [], []
    for path in [pdf, *([Path(raster)] if raster else [])]:
        issues, metadata = check_figure(str(path), target_inches=target_inches)
        files[path.name] = {"metadata": metadata, "issues": issues}
        failed.extend(message for level, message in issues if level == "FAIL")
        warnings.extend(message for level, message in issues if level == "WARN")
        unavailable.extend(message for level, message in issues if level == "INFO")
    try:
        text = audit_pdf(pdf.read_bytes(), minimum_pt=min_font_pt)
        if not text["auditable"]:
            unavailable.append("PDF font sizes were not auditable")
        if text["below_minimum_count"]:
            failed.append("PDF contains text smaller than the requested minimum")
        warnings.extend(text["warnings"])
    except (OSError, RuntimeError, ValueError) as exc:
        text = {"auditable": False, "error": str(exc)}
        unavailable.append(str(exc))
    try:
        collision = collision_audit(pdf)
        if not collision["auditable"]:
            unavailable.append("PDF collisions were not auditable")
        if collision["summary"]["fail"]:
            failed.append("PDF contains blocking geometric collisions")
        if collision["summary"]["warn"]:
            warnings.append("PDF contains overlays requiring visual review")
    except (OSError, RuntimeError, ValueError) as exc:
        collision = {"auditable": False, "error": str(exc)}
        unavailable.append(str(exc))
    report = {
        "automated_status": "FAIL" if failed else "NOT_AUDITABLE" if unavailable else "REVIEW_REQUIRED" if warnings else "PASS",
        "files": files, "pdf_text": text, "collisions": collision,
        "failures": failed, "warnings": warnings, "unavailable_checks": unavailable,
        "visual_review": {"status": "pending", "notes": []},
        "design_review": {"status": "pending", "notes": [],
                          "scope": "Automated checks do not assess evidence architecture or editorial quality."},
    }
    from review_tools import bind_exports
    return bind_exports(report, pdf=pdf, png=raster, additional_exports=additional_exports)


def save_figure(fig, basename, *, size_mm=None, formats=("pdf", "svg", "png"),
                dpi=300, axes=None, label_panels=False, min_font_pt=None,
                grayscale=True, alignment_options=None, source_data=None, source_files=None):
    """Export one physical-size figure and record checks. Human/agent visual review remains pending.

    For comparable panels pass their axes explicitly; alignment_options accepts the
    migrated auditor's groups/exemptions. This function does not perform statistics.
    """
    from export_figure import export_figure
    from visual_qa import audit_layout
    from layout_tools import _data_axes, add_panel_labels
    from audit_panel_alignment import require_matplotlib_panel_alignment
    from project_style import current_project, snapshot
    from review_tools import audit_marks, figure_snapshot
    from source_binding import capture_sources, verify_sources
    sources = capture_sources(source_files, source_data=source_data)
    source_digest = None
    if source_data is not None:
        from chart_plan import read_data, data_digest
        source_digest = data_digest(read_data(source_data))
    if min_font_pt is None:
        min_font_pt = current_project()['typography']['minimum_pt']
    basename = str(basename)
    Path(basename).parent.mkdir(parents=True, exist_ok=True)
    if "pdf" not in formats:
        raise ValueError("save_figure needs PDF output for final-file checks")
    if size_mm is not None:
        if len(size_mm) != 2 or any(not math.isfinite(float(value)) or float(value) <= 0 for value in size_mm):
            raise ValueError("size_mm must contain positive finite width and height")
        fig.set_size_inches(*(float(value) / 25.4 for value in size_mm))
    if not math.isfinite(min_font_pt) or min_font_pt <= 0:
        raise ValueError("min_font_pt must be positive and finite")
    write_json(basename + ".qa.json", {"automated_status": "IN_PROGRESS",
               "visual_review": {"status": "pending", "notes": []}})
    selected = list(axes) if axes is not None else _data_axes(fig)
    if label_panels:
        add_panel_labels(fig, axes=selected, x_offset_pt=0, y_offset_pt=5, ha="left")
    findings = audit_layout(fig)
    mark_findings = audit_marks(fig, axes=selected)
    if any(level == "FAIL" for level, _ in findings):
        write_json(basename + ".qa.json", {"automated_status": "FAIL", "layout_issues": findings})
        raise ValueError("missing glyphs detected; correct fonts before exporting")
    alignment = None
    if len(selected) > 1:
        try:
            alignment = require_matplotlib_panel_alignment(
                fig, axes=selected, json_out=basename + ".alignment.json",
                **(alignment_options or {}))
        except (ValueError, RuntimeError) as exc:
            write_json(basename + ".qa.json", {"automated_status": "FAIL", "stage": "alignment", "error": str(exc)})
            raise
    size = tuple(float(value) for value in fig.get_size_inches())
    paths = export_figure(fig, basename, formats=formats, dpi=dpi,
                          size_inches=size, grayscale_preview=grayscale)
    report = audit_exported(basename + ".pdf",
                            raster=basename + ".png" if "png" in formats else None,
                            target_inches=size, min_font_pt=min_font_pt, additional_exports=paths)
    report.update({"layout_issues": findings, "alignment": alignment,
                   "outputs": paths, "size_inches": size, "project_style": snapshot(),
                   "minimum_font_pt": min_font_pt, "mark_issues": mark_findings,
                   "figure_snapshot": figure_snapshot(fig)})
    from color_tools import audit_rendered_mapping
    report['color_mapping_audit']=audit_rendered_mapping(report['figure_snapshot'],report['project_style'])
    if report['color_mapping_audit']['status']=='FAIL':
        report['automated_status']='FAIL'
        report['failures'].append('Rendered group colors differ from project identity mapping')
    if source_digest is not None:
        report['source_data_sha256'] = source_digest
    if sources:
        report['source_manifest'] = sources
        source_errors = verify_sources(report)
        if source_errors:
            report['automated_status'] = 'FAIL'
            report['failures'].extend(source_errors)
    if hasattr(fig, '_light_chart_composition'):
        report['composition'] = fig._light_chart_composition
    if hasattr(fig, '_light_chart_images'):
        report['image_manifest'] = fig._light_chart_images
    if (mark_findings or any(level == "WARN" for level, _ in findings)) and report["automated_status"] == "PASS":
        report["automated_status"] = "REVIEW_REQUIRED"
    write_json(basename + ".qa.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description="Audit the final PDF from Python or R without redrawing it")
    parser.add_argument("pdf")
    parser.add_argument("--png")
    parser.add_argument("--width-mm", type=float)
    parser.add_argument("--height-mm", type=float)
    parser.add_argument("--min-font-pt", type=float, default=None)
    parser.add_argument("--normalize-cairo-page", action="store_true")
    parser.add_argument("--extra-export", action="append", default=[])
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()
    if (args.width_mm is None) != (args.height_mm is None):
        parser.error("supply both --width-mm and --height-mm")
    if any(not math.isfinite(value) or value <= 0 for value in [*([args.min_font_pt] if args.min_font_pt is not None else []), *([args.width_mm, args.height_mm] if args.width_mm is not None else [])]):
        parser.error("dimensions and minimum font size must be finite and positive")
    size = (args.width_mm / 25.4, args.height_mm / 25.4) if args.width_mm is not None else None
    correction = None
    if args.normalize_cairo_page:
        if size is None:
            parser.error("Cairo normalization needs target dimensions")
        correction = normalize_cairo_page(args.pdf, size)
    result = audit_exported(args.pdf, raster=args.png, target_inches=size, min_font_pt=args.min_font_pt,
                            additional_exports=args.extra_export)
    if correction:
        result["page_geometry_correction"] = correction
    write_json(args.json_out, result)
    print(result["automated_status"])
    return 1 if result["automated_status"] == "FAIL" else 2 if result["automated_status"] == "NOT_AUDITABLE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
