#!/usr/bin/env python3
"""Render local worksheets, source deposits, and evidence-written manuals.

No software descriptions are inferred here. The agent supplies checked facts and
manual.json; the source content is verified against the actual project snapshot.
"""
from __future__ import annotations

import argparse
from html import escape
import io
import json
from pathlib import Path
import re
import shutil
import sys

from copyright_case import (
    CaseError, audit_case, canonical_inputs, contained, file_hash, fingerprint,
    read_json, title_for, verify_pages, write_json,
)

LABELS = {
    "software_name": "软件全称", "abbreviation": "软件简称", "version": "版本号",
    "owners": "著作权人", "owner_type": "主体类型", "development_mode": "开发方式",
    "rights_acquisition": "权利取得方式", "rights_scope": "权利范围",
    "completed_on": "开发完成日期", "publication_status": "发表状态",
    "first_published_on": "首次发表日期", "first_published_place": "首次发表地点",
    "languages": "编程语言", "purpose": "开发目的", "industry": "面向行业/领域",
    "main_functions": "主要功能", "technical_features": "技术特点",
    "development_hardware": "开发硬件环境", "development_os": "开发操作系统",
    "development_tools": "开发环境/工具", "runtime_hardware": "运行硬件环境",
    "runtime_os": "运行操作系统", "runtime_support": "运行支撑环境",
}


def preserve_write(path, data, case):
    """Preserve existing user edits and previous outputs; never silently destroy."""
    path, case = Path(path), Path(case)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        old = path.read_bytes()
        if old == data:
            return
        history = case / "历史资料" / f"{path.stem}_{file_hash(path)[:12]}{path.suffix}"
        history.parent.mkdir(parents=True, exist_ok=True)
        if not history.exists():
            shutil.copy2(path, history)
    path.write_bytes(data)


def register_artifact(case, path, kind, inputs, details=None):
    case = Path(case).resolve()
    manifest_path = case / "deliverables.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else {"schema_version": 1, "artifacts": []}
    relative = Path(path).resolve().relative_to(case).as_posix()
    # Retire earlier manifests for the same kind/format/location, not user files.
    group = Path(relative).parts[0]
    ext = Path(relative).suffix
    retired = [a for a in manifest["artifacts"] if a["kind"] == kind and Path(a["path"]).suffix == ext and (Path(a["path"]).parts[0] == group or group == "草稿")]
    manifest.setdefault("retired_artifacts", []).extend(retired)
    manifest["artifacts"] = [a for a in manifest["artifacts"] if a not in retired]
    manifest["artifacts"].append({"path": relative, "kind": kind, "sha256": file_hash(path), "inputs": inputs, **(details or {})})
    write_json(manifest_path, manifest)


def safe_stem(value):
    # Filename sanitation only; visible software names are preserved verbatim.
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    if not value or len(value) > 110:
        raise CaseError("Software title too long/empty for a portable output filename; use a shorter explicit output strategy")
    return value


def render_application(case, facts):
    title = title_for(facts)
    source = verify_pages(case) if (case / "source-pages.json").exists() else None
    rows = [title, "申请表填报底稿（不是官方申请表；未核实项见下文）", ""]
    for key in ("software_name", "abbreviation", "version", "owners", "owner_type", "development_mode", "rights_acquisition", "rights_scope", "completed_on", "publication_status", "first_published_on", "first_published_place"):
        value = facts.get(key)
        if key in {"abbreviation", "first_published_on", "first_published_place"} and not value:
            value = "无" if key == "abbreviation" else "不适用" if facts.get("publication_status") == "未发表" else "【待确认】"
        value = "、".join(value) if isinstance(value, list) else value
        rows.append(f"{LABELS[key]}：{value or '【待确认】'}")
    for key, value in facts.get("environments", {}).items():
        rows.append(f"{LABELS.get(key, key)}：{value or '【待确认】'}")
    for key in ("languages", "purpose", "industry", "main_functions", "technical_features"):
        value = facts.get(key)
        value = "、".join(value) if isinstance(value, list) else value
        rows.append(f"{LABELS[key]}：{value or '【待确认】'}")
    if source:
        rows += [f"完整范围原始物理程序行：{source['raw_source_lines']}",
                 f"完整范围非空程序行：{source['nonblank_source_lines']}",
                 f"完整源码底稿页数：{source['complete_pages']}",
                 f"拟提交源程序页数：{source['submitted_pages']}",
                 "源程序量填写依据：以上为完整登记范围统计，非交存节选行数；注释保留，Notebook 只计代码单元。按当前表单要求选择统计口径。"]
    else:
        rows.append("源程序统计：【待确认：尚未抽取】")
    rows += ["", "主要功能字符数（本工具按 Unicode 码点计，供核对页面计数）：" + str(len(facts.get("main_functions") or "")),
             "当前表单/签章要求：" + ("已记录核验来源，提交前仍由申请人复核。" if facts.get("rules", {}).get("official_form_verified") else "未核实，提交前须检查实际页面。")]
    path = case / "草稿" / f"{safe_stem(title)}_申请表信息.txt"
    preserve_write(path, ("\n".join(rows) + "\n").encode("utf-8"), case)
    register_artifact(case, path, "application", {n: h for n, h in canonical_inputs(case).items() if n not in {"manual.json", "functions.json", "layout-profile.json"}})
    return [path]


def load_pdf_font(requested=None):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    candidates = [requested] if requested else [
        "C:/Windows/Fonts/simsun.ttc", "C:/Windows/Fonts/msyh.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
    ]
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        try:
            alias = "LightCN_" + file_hash(candidate)[:10]
            if alias not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(alias, candidate, subfontIndex=0))
            return alias, str(Path(candidate).resolve())
        except Exception:
            if requested:
                raise CaseError("Requested font cannot be embedded as a TrueType font")
    raise CaseError("No embeddable Chinese TrueType font found. Pass --font <local TTF/TTC>; no fonts are downloaded")


def check_glyphs(text, font):
    from reportlab.pdfbase import pdfmetrics
    widths = pdfmetrics.getFont(font).face.charWidths
    missing = sorted({ord(c) for c in text if c not in "\r\n\t" and ord(c) not in widths})
    if missing:
        raise CaseError("Font lacks characters: " + ", ".join(f"U+{c:04X}" for c in missing[:12]))


def fit_size(lines, font, width, maximum=8.5, minimum=7.0):
    from reportlab.pdfbase import pdfmetrics
    longest = max((pdfmetrics.stringWidth(line, font, 1) for line in lines), default=1)
    size = min(maximum, width / max(longest, 1) * .96)
    if size < minimum:
        raise CaseError(f"A line cannot fit at {minimum}pt. Review actual long lines or use a verified alternative layout; source is not truncated")
    return size


def header_size(title, font):
    check_glyphs(title, font)
    return fit_size([title], font, 460, maximum=9, minimum=7)


def render_code_pdf(facts, pages, font):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    title = title_for(facts)
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream, pagesize=A4, invariant=1)
    pdf.setTitle(title + " 源程序")
    hsize = header_size(title, font)
    for page in pages["pages"]:
        lines = [r["text"].expandtabs(4) for r in page["lines"]]
        check_glyphs("\n".join(lines), font)
        size = fit_size(lines, font, A4[0] - 80)
        pdf.setFont(font, hsize)
        pdf.drawString(40, A4[1] - 28, title)
        pdf.drawRightString(A4[0] - 40, A4[1] - 28, str(page["submission_page"]))
        pdf.setFont(font, size)
        for i, line in enumerate(lines):
            pdf.drawString(40, A4[1] - 57 - i * 14, line)
        pdf.showPage()
    pdf.save()
    return stream.getvalue()


def configure_docx(document, facts):
    from docx.shared import Pt, Mm
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    section = document.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.top_margin, section.bottom_margin = Mm(18), Mm(17)
    section.left_margin, section.right_margin = Mm(15), Mm(15)
    section.header_distance = Mm(7)
    for name in ("Normal", "Heading 1", "Heading 2", "Heading 3"):
        style = document.styles[name]
        style.font.name = "SimSun"
        style.font.size = Pt(10.5 if name == "Normal" else 14 if name == "Heading 1" else 12)
        style.font.color.rgb = __import__("docx").shared.RGBColor(0, 0, 0)
        fonts = style.element.get_or_add_rPr().get_or_add_rFonts()
        for key in ("ascii", "hAnsi", "eastAsia", "cs"):
            fonts.set(qn("w:" + key), "SimSun")
        style.paragraph_format.space_after = Pt(6)
    normal = document.styles["Normal"]
    normal.paragraph_format.line_spacing = 1.3
    header = section.header.paragraphs[0]
    header.paragraph_format.tab_stops.add_tab_stop(Mm(177), __import__("docx").enum.text.WD_TAB_ALIGNMENT.RIGHT)
    run = header.add_run(title_for(facts) + "\t")
    run.font.size = Pt(8)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    header._p.append(fld)


def render_code_docx(facts, pages, pdf_font=None):
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_LINE_SPACING
    document = Document()
    configure_docx(document, facts)
    for index, page in enumerate(pages["pages"]):
        if index:
            document.add_page_break()
        lines = [r["text"].expandtabs(4) for r in page["lines"]]
        size = fit_size(lines, pdf_font, 505) if pdf_font else 8.0
        if not pdf_font and any(len(line) > 100 for line in lines):
            raise CaseError("Long source lines need a measured PDF font; supply --font to validate DOCX widths")
        for line in lines:
            p = document.add_paragraph()
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
            p.paragraph_format.line_spacing = Pt(14)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.keep_together = True
            run = p.add_run(line)
            run.font.size = Pt(size)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def load_manual(case):
    return load_document(case, "manual")


def load_document(case, kind):
    name = "functions.json" if kind == "functions" else "manual.json"
    manual = read_json(case / name)
    if not isinstance(manual, dict):
        raise CaseError(f"{name} must be an object")
    types = {"功能说明"} if kind == "functions" else {"操作手册", "用户手册", "设计说明书", "使用说明书"}
    if manual.get("document_type") not in types:
        raise CaseError(f"{name} needs an actual document_type")
    if not isinstance(manual.get("sections"), list) or not manual["sections"]:
        raise CaseError(f"{name} needs nonempty sections")
    assets = {}
    for section in manual["sections"]:
        if not isinstance(section, dict):
            raise CaseError("Document sections must be objects")
        if not isinstance(section.get("heading"), str) or not section["heading"].strip() or section.get("level", 1) not in (1, 2, 3):
            raise CaseError("Manual headings need text and levels 1-3")
        if not isinstance(section.get("blocks"), list) or not section["blocks"]:
            raise CaseError(f"Empty manual section: {section['heading']}")
        for block in section["blocks"]:
            if not isinstance(block, dict):
                raise CaseError("Document blocks must be objects")
            kind = block.get("type")
            if kind in {"paragraph", "code"}:
                if not isinstance(block.get("text"), str) or not block["text"].strip():
                    raise CaseError("Empty paragraph/code block")
            elif kind == "steps":
                if not isinstance(block.get("items"), list) or not block["items"] or not all(isinstance(x, str) and x.strip() for x in block["items"]):
                    raise CaseError("Steps need nonempty text items")
            elif kind == "table":
                headers, rows = block.get("headers", []), block.get("rows", [])
                if not isinstance(headers, list) or not headers or not isinstance(rows, list) or not rows or any(not isinstance(row, list) or len(row) != len(headers) for row in rows):
                    raise CaseError("Table needs headers and rectangular rows")
            elif kind == "image":
                asset = contained(case, block.get("path", ""))
                if not asset.is_file() or not block.get("caption") or not block.get("provenance"):
                    raise CaseError("Image requires actual file, caption and provenance")
                from PIL import Image
                with Image.open(asset) as img:
                    img.verify()
                assets[asset.relative_to(case).as_posix()] = file_hash(asset)
            else:
                raise CaseError(f"Unsupported manual block: {kind}")
    return manual, assets


def render_manual_docx(case, facts, manual):
    from docx import Document
    from docx.shared import Mm, Pt
    document = Document()
    configure_docx(document, facts)
    document.add_heading(title_for(facts), 0)
    document.add_paragraph(manual["document_type"])
    if facts.get("owners"):
        document.add_paragraph("著作权人：" + "、".join(facts["owners"]))
    for section in manual["sections"]:
        document.add_heading(section["heading"], section.get("level", 1))
        for block in section["blocks"]:
            kind = block["type"]
            if kind == "paragraph":
                document.add_paragraph(block["text"])
            elif kind == "steps":
                for index, text in enumerate(block["items"], 1):
                    document.add_paragraph(f"{index}. {text}")
            elif kind == "code":
                p = document.add_paragraph()
                run = p.add_run(block["text"])
                run.font.size = Pt(9)
            elif kind == "table":
                table = document.add_table(rows=1, cols=len(block["headers"]))
                table.style = "Table Grid"
                for i, text in enumerate(block["headers"]):
                    table.rows[0].cells[i].text = str(text)
                for row in block["rows"]:
                    cells = table.add_row().cells
                    for i, text in enumerate(row):
                        cells[i].text = str(text)
            elif kind == "image":
                from PIL import Image
                asset = contained(case, block["path"])
                with Image.open(asset) as img:
                    w, h = img.size
                width = min(174, 210 * w / h)
                document.add_picture(str(asset), width=Mm(width))
                document.add_paragraph(block["caption"])
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def render_manual_pdf(case, facts, manual, font):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Preformatted
    title = title_for(facts)
    hsize = header_size(title, font)
    body = ParagraphStyle("Body", fontName=font, fontSize=10.5, leading=16, spaceAfter=7, wordWrap="CJK", splitLongWords=1)
    headings = {level: ParagraphStyle(f"H{level}", parent=body, fontSize=16 if level == 1 else 13, leading=22 if level == 1 else 18, spaceBefore=12, keepWithNext=True) for level in (1, 2, 3)}
    small = ParagraphStyle("Small", parent=body, fontSize=9, leading=13)
    code_style = ParagraphStyle("Code", parent=body, fontSize=8, leading=12)
    def para(text, style=body):
        text = str(text)
        check_glyphs(text, font)
        return Paragraph(escape(text).replace("\n", "<br/>"), style)
    story = [para(title, headings[1]), para(manual["document_type"], headings[2])]
    if facts.get("owners"):
        story.append(para("著作权人：" + "、".join(facts["owners"])))
    for section in manual["sections"]:
        story.append(para(section["heading"], headings[section.get("level", 1)]))
        for block in section["blocks"]:
            kind = block["type"]
            if kind == "paragraph":
                story.append(para(block["text"]))
            elif kind == "steps":
                story.extend(para(f"{i}. {text}") for i, text in enumerate(block["items"], 1))
            elif kind == "code":
                text = block["text"].expandtabs(4)
                check_glyphs(text, font)
                fit_size(text.splitlines(), font, A4[0] - 84, maximum=8, minimum=8)
                story.append(Preformatted(text, code_style))
            elif kind == "table":
                width = (A4[0] - 84) / len(block["headers"])
                rows = [[para(value, small) for value in row] for row in [block["headers"], *block["rows"]]]
                table = Table(rows, colWidths=[width] * len(block["headers"]), repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")), ("GRID", (0, 0), (-1, -1), .4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
                story.extend([table, Spacer(1, 8)])
            elif kind == "image":
                image = Image(str(contained(case, block["path"])))
                scale = min((A4[0] - 84) / image.imageWidth, 530 / image.imageHeight, 1.0)
                image.drawWidth, image.drawHeight = image.imageWidth * scale, image.imageHeight * scale
                image.hAlign = "LEFT"
                story.extend([image, para(block["caption"], small)])
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, leftMargin=42, rightMargin=42, topMargin=54, bottomMargin=42, title=title + " " + manual["document_type"])
    def header(canvas, doc):
        canvas.setFont(font, hsize)
        canvas.drawString(42, A4[1] - 28, title)
        canvas.drawRightString(A4[0] - 42, A4[1] - 28, str(doc.page))
    doc.build(story, onFirstPage=header, onLaterPages=header)
    return output.getvalue()


def release(case, kind):
    report = audit_case(case, [kind])
    if report["errors"]:
        raise CaseError("Local audit has blockers; see audit.json. Drafts remain available")
    manifest = read_json(case / "deliverables.json")
    artifacts = [a for a in manifest["artifacts"] if a["kind"] == kind and Path(a["path"]).parts[0] == "草稿"]
    if not artifacts:
        raise CaseError("No current draft artifacts for this kind")
    # Prior releases are archived only on explicit local release, not while
    # drafting. Keep any user edits, using their actual hash in the archive name.
    for old in manifest.get("retired_artifacts", []):
        if old.get("kind") != kind or Path(old["path"]).parts[0] != "正式资料":
            continue
        src = contained(case, old["path"])
        if src.is_file():
            sha = file_hash(src)
            history = case / "历史资料" / f"{src.stem}_{sha[:12]}{src.suffix}"
            history.parent.mkdir(parents=True, exist_ok=True)
            if history.exists() and file_hash(history) != sha:
                raise CaseError("History filename collision; existing file preserved")
            src.replace(history)
    paths = []
    for artifact in artifacts:
        src = contained(case, artifact["path"])
        dest = case / "正式资料" / src.name
        preserve_write(dest, src.read_bytes(), case)
        details = {k:v for k,v in artifact.items() if k not in {"path","kind","sha256","inputs"}}
        register_artifact(case, dest, kind, artifact["inputs"], {**details, "release": "local_review_copy", "portal_ready": False})
        paths.append(dest)
    return paths


def build_products(case, kind, formats, font_path=None, reference=False):
    case = Path(case).resolve()
    facts = read_json(case / "case.json")
    title = title_for(facts)
    if not formats or set(formats) - {"docx", "pdf"}:
        raise CaseError("Formats must be docx and/or pdf")
    inputs = canonical_inputs(case)
    layout_input = {}
    if reference:
        from reference_layout import PROFILE
        layout_path = case / "layout-profile.json"
        if layout_path.exists() and layout_path.read_bytes() != PROFILE.read_bytes():
            raise CaseError("Existing layout-profile.json differs; review it before adopting a new profile")
        if not layout_path.exists():
            preserve_write(layout_path, PROFILE.read_bytes(), case)
        layout_input["layout-profile.json"] = file_hash(layout_path)
    if kind == "code":
        pages = verify_pages(case)
        inputs = {k:v for k,v in inputs.items() if k in {"case.json", "inventory.json", "selection.json", "source-pages.json"}}
        descriptor = "软件代码" if reference else "源程序_全部" if pages["mode"] == "all" else "源程序_前后各30页"
    else:
        manual, assets = load_document(case, kind)
        content_name = "functions.json" if kind == "functions" else "manual.json"
        inputs = {"case.json": inputs["case.json"], content_name: inputs[content_name], **assets}
        descriptor = "功能说明" if kind == "functions" else "软件说明书" if reference else manual["document_type"]
    inputs.update(layout_input)
    project_inputs = {}
    if kind in {"manual", "functions"}:
        for feature in facts.get("features", []):
            for e in feature.get("evidence", []):
                source = contained(facts["project_root"], e["path"])
                project_inputs[e["path"]] = file_hash(source)
    font, font_file = (None, None)
    if "pdf" in formats or kind == "code" or font_path:
        try:
            font, font_file = load_pdf_font(font_path)
        except (CaseError, ImportError):
            if "pdf" in formats or font_path:
                raise
    # Build all bytes first: an overflow or missing image cannot publish half a pair.
    products = []
    for fmt in formats:
        if kind == "code":
            if fmt == "docx" and reference:
                from reference_layout import render_code
                data = render_code(facts, pages, font)
            else:
                data = render_code_pdf(facts, pages, font) if fmt == "pdf" else render_code_docx(facts, pages, font)
        else:
            if fmt == "docx" and reference:
                from reference_layout import render_document
                data = render_document(case, facts, manual, kind)
            else:
                data = render_manual_pdf(case, facts, manual, font) if fmt == "pdf" else render_manual_docx(case, facts, manual)
        path = case / "草稿" / f"{safe_stem(title)}_{descriptor}.{fmt}"
        products.append((path, data))
    details = {"font_file": font_file, "font_sha256": file_hash(font_file) if font_file else None,
               "project_inputs": project_inputs, "layout_profile": "three-documents" if reference else "legacy"}
    return [(path, data, kind, inputs, details) for path, data in products]


def publish_products(case, products):
    for _, _, _, inputs, details in products:
        if any(file_hash(contained(case, name)) != sha for name,sha in inputs.items()):
            raise CaseError("Inputs changed while rendering; no new outputs published")
        facts = read_json(Path(case)/"case.json")
        if any(file_hash(contained(facts["project_root"],name)) != sha for name,sha in details.get("project_inputs",{}).items()):
            raise CaseError("Project evidence changed while rendering; no new outputs published")
    for path, data, kind, inputs, details in products:
        preserve_write(path, data, case)
        register_artifact(case, path, kind, inputs, details)
    return [p for p, *_ in products]


def render(case, kind, formats, font_path=None):
    case = Path(case).resolve()
    if kind == "application":
        return render_application(case, read_json(case/"case.json"))
    facts = read_json(case/"case.json")
    reference = facts.get("delivery_profile") == "three-documents" or kind in {"bundle", "functions"}
    kinds = ("functions", "code", "manual") if kind == "bundle" else (kind,)
    products = []
    for current in kinds:
        products.extend(build_products(case,current,formats,font_path,reference))
    return publish_products(case,products)


def release_bundle(case):
    """Publish exactly three DOCX files, keeping internal worksheets outside."""
    import tempfile
    report = audit_case(case, ["functions","code","manual"])
    if report["errors"]:
        raise CaseError("Local three-document audit has blockers; drafts remain available")
    manifest = read_json(case/"deliverables.json")
    artifacts = [a for a in manifest["artifacts"] if a["kind"] in {"functions","code","manual"} and Path(a["path"]).parts[0]=="草稿" and Path(a["path"]).suffix==".docx"]
    if len(artifacts)!=3 or {a["kind"] for a in artifacts}!={"functions","code","manual"}:
        raise CaseError("Bundle release needs exactly one current DOCX per document kind")
    folder=case/"正式资料"/safe_stem(title_for(read_json(case/"case.json")))
    if folder.exists():
        raise CaseError("Bundle delivery directory already exists; preserve it and use a new revision")
    folder.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix="."+folder.name+".building-",dir=folder.parent))
    for artifact in artifacts:
        shutil.copyfile(contained(case,artifact["path"]),staging/Path(artifact["path"]).name)
    staging.rename(folder)
    result=[]
    for artifact in artifacts:
        path=folder/Path(artifact["path"]).name
        details={k:v for k,v in artifact.items() if k not in {"path","kind","sha256","inputs"}}
        register_artifact(case,path,artifact["kind"],artifact["inputs"],{**details,"release":"local_review_copy","portal_ready":False})
        result.append(path)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--kind", default="bundle", choices=["bundle", "functions", "application", "code", "manual"])
    parser.add_argument("--formats", help="Default: docx for bundle; docx,pdf for an individual document")
    parser.add_argument("--font", help="Local embeddable Chinese TrueType TTF/TTC font")
    parser.add_argument("--release", action="store_true", help="Audit existing drafts and copy this kind to 正式资料; does not submit")
    args = parser.parse_args(argv)
    try:
        case = Path(args.case).resolve()
        formats = args.formats or ("docx" if args.kind == "bundle" else "docx,pdf")
        paths = (release_bundle(case) if args.kind == "bundle" else release(case,args.kind)) if args.release else render(case,args.kind,[f.strip() for f in formats.split(",")],args.font)
        print(json.dumps({"status": "local_release_copy" if args.release else "draft_created", "paths": [str(p) for p in paths]}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, ImportError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
