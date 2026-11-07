"""Reusable layout distilled from user references; no reference business content."""
import io
import json
from pathlib import Path

from copyright_case import CaseError, contained, title_for

PROFILE = Path(__file__).resolve().parents[1] / "assets/three-document-layout.json"


def set_font(style, name, size, color="000000", latin=None, bold=None):
    from docx.shared import Pt, RGBColor
    from docx.oxml.ns import qn
    style.font.name = latin or name
    style.font.size = Pt(size)
    style.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        style.font.bold = bold
    fonts = style.element.get_or_add_rPr().get_or_add_rFonts()
    for key in ("ascii", "hAnsi", "cs"):
        fonts.set(qn("w:"+key), latin or name)
    fonts.set(qn("w:eastAsia"), name)
    fonts.set(qn("w:hint"), "default")


def configure(document, facts, code=False):
    from docx.shared import Mm, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    s = document.sections[0]
    s.page_width, s.page_height = map(Mm, profile["page_mm"])
    s.top_margin, s.bottom_margin, s.left_margin, s.right_margin = map(Mm, profile["code_margins_mm"] if code else profile["document_margins_mm"])
    s.header_distance = s.footer_distance = Mm(profile["header_footer_mm"])
    body = profile["body"]
    normal = document.styles["Normal"]
    set_font(normal, body["font"], body["size_pt"])
    f = normal.paragraph_format
    f.line_spacing = body["line_spacing"]
    f.space_before = f.space_after = Pt(0)
    f.first_line_indent = Pt(body["first_line_pt"])
    f.widow_control = True
    for i in (1, 2, 3):
        h = profile["headings"]
        style = document.styles[f"Heading {i}"]
        set_font(style, h["font"], h["sizes_pt"][i-1], h["color"], bold=True)
        style.paragraph_format.first_line_indent = Pt(0)
        style.paragraph_format.space_before = Pt(h["before_pt"])
        style.paragraph_format.space_after = Pt(h["after_pt"])
        style.paragraph_format.keep_with_next = True
    set_font(document.styles["Title"], "黑体", profile["function_title_pt"], bold=True)
    document.styles["Title"].paragraph_format.first_line_indent = Pt(0)
    document.styles["Title"].paragraph_format.space_after = Pt(12)
    # The references use this thin title rule; do not rely on a local template.
    title_pr = document.styles["Title"].element.get_or_add_pPr()
    old_border = title_pr.find(qn("w:pBdr"))
    if old_border is not None:
        title_pr.remove(old_border)
    border = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for key, value in (("val","single"),("sz","8"),("space","4"),("color","4F81BD")):
        bottom.set(qn("w:"+key), value)
    border.append(bottom); title_pr.append(border)
    caption = document.styles["Caption"]
    c = profile["caption"]
    set_font(caption, c["font"], c["size_pt"], bold=c["bold"])
    caption.font.italic = False
    caption.paragraph_format.first_line_indent = Pt(0)
    caption.paragraph_format.space_before = Pt(c["before_pt"])
    caption.paragraph_format.space_after = Pt(c["after_pt"])
    caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    header = s.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    header.paragraph_format.first_line_indent = Pt(0)
    header.paragraph_format.space_after = Pt(0)
    set_font(document.styles["Header"], "宋体", 8)
    header.add_run(title_for(facts))
    if code:
        header.add_run(" 第 ")
        field = OxmlElement("w:fldSimple")
        field.set(qn("w:instr"), "PAGE")
        header._p.append(field)
        header.add_run(" 页")
    document.core_properties.author = ""
    document.core_properties.last_modified_by = ""
    document.core_properties.title = title_for(facts)
    return profile


def numbered_steps(document, items):
    """Create one real ordered list per steps block."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt
    numbering = document.part.numbering_part.element
    ids = [int(x.get(qn("w:numId"))) for x in numbering.findall(qn("w:num"))]
    abstract_ids = [int(x.get(qn("w:abstractNumId"))) for x in numbering.findall(qn("w:abstractNum"))]
    num_id, abstract_id = max(ids, default=0)+1, max(abstract_ids, default=0)+1
    abstract = OxmlElement("w:abstractNum"); abstract.set(qn("w:abstractNumId"), str(abstract_id))
    level = OxmlElement("w:lvl"); level.set(qn("w:ilvl"), "0")
    for tag, value in (("start","1"),("numFmt","decimal"),("lvlText","%1.")):
        el=OxmlElement("w:"+tag); el.set(qn("w:val"),value); level.append(el)
    abstract.append(level); numbering.insert(0,abstract)
    num=OxmlElement("w:num"); num.set(qn("w:numId"),str(num_id))
    ref=OxmlElement("w:abstractNumId"); ref.set(qn("w:val"),str(abstract_id)); num.append(ref); numbering.append(num)
    for text in items:
        p=document.add_paragraph(text)
        p.paragraph_format.first_line_indent = Pt(-18)
        p.paragraph_format.left_indent = Pt(18)
        pr=p._p.get_or_add_pPr(); props=OxmlElement("w:numPr")
        for tag, value in (("ilvl","0"),("numId",str(num_id))):
            el=OxmlElement("w:"+tag); el.set(qn("w:val"),value); props.append(el)
        pr.append(props)


def render_document(case, facts, content, kind):
    from docx import Document
    from docx.shared import Mm, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from PIL import Image
    doc = Document(); profile = configure(doc, facts)
    if kind == "functions":
        p=doc.add_paragraph(title_for(facts)+" 功能说明", "Title")
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    else:
        for text, size, before, after in (
            (facts["software_name"],26,72,20), (facts["version"],20,0,40),
            (content["document_type"],22,0,60)):
            p=doc.add_paragraph(text,"Title"); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before=Pt(before); p.paragraph_format.space_after=Pt(after)
            for r in p.runs: r.font.size=Pt(size)
        if facts.get("owners"):
            p=doc.add_paragraph("、".join(facts["owners"])+" 版权所有")
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.first_line_indent=Pt(0)
            p.paragraph_format.space_before=Pt(60)
        # A native page-break property avoids an empty cover paragraph.
    first = True
    for section in content["sections"]:
        heading=doc.add_heading(section["heading"],section.get("level",1))
        if kind != "functions" and first:
            heading.paragraph_format.page_break_before=True
        first=False
        for block in section["blocks"]:
            t=block["type"]
            if t=="paragraph":
                doc.add_paragraph(block["text"])
            elif t=="steps":
                numbered_steps(doc,block["items"])
            elif t=="code":
                for line in block["text"].splitlines():
                    p=doc.add_paragraph(); p.paragraph_format.first_line_indent=Pt(0)
                    p.paragraph_format.line_spacing=1
                    r=p.add_run(line); r.font.name="Consolas"; r.font.size=Pt(9)
            elif t=="table":
                table=doc.add_table(rows=1,cols=len(block["headers"])); table.style="Table Grid"
                repeat=OxmlElement("w:tblHeader"); table.rows[0]._tr.get_or_add_trPr().append(repeat)
                for row, values in [(table.rows[0],block["headers"])]+[(table.add_row(),x) for x in block["rows"]]:
                    for cell,text in zip(row.cells,values):
                        cell.text=str(text)
                        for p in cell.paragraphs: p.paragraph_format.first_line_indent=Pt(0)
            elif t=="image":
                asset=contained(case,block["path"])
                with Image.open(asset) as im: width,height=im.size
                p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.first_line_indent=Pt(0); p.paragraph_format.keep_with_next=True
                p.add_run().add_picture(str(asset),width=Mm(min(160,195*width/height)))
                doc.add_paragraph(block["caption"],"Caption")
    stream=io.BytesIO(); doc.save(stream)
    return stream.getvalue()


def render_code(facts, pages, pdf_font):
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_LINE_SPACING
    if pdf_font:
        from reportlab.pdfbase import pdfmetrics
    doc=Document(); profile=configure(doc,facts,code=True); c=profile["code"]
    for index,page in enumerate(pages["pages"]):
        lines=[r["text"].expandtabs(4) for r in page["lines"]]
        if pdf_font:
            # Consolas Latin is wider than proportional Latin in a CJK font.
            units=max((max(pdfmetrics.stringWidth(s,pdf_font,1),len(s)*0.61) for s in lines),default=1)
            size=min(c["size_pt"],480*.96/max(units,1))
            if size<c["minimum_pt"]: raise CaseError("Source line cannot fit reference code layout without truncation")
        else:
            import unicodedata
            units=max((sum(1 if unicodedata.east_asian_width(ch) in {"W","F"} else .61 for ch in s) for s in lines),default=0)
            if units*c["size_pt"] > 480*.96:
                raise CaseError("Code width needs an actual measured font")
            size=c["size_pt"]
        for j,line in enumerate(lines):
            p=doc.add_paragraph()
            f=p.paragraph_format; f.first_line_indent=Pt(0); f.space_before=f.space_after=Pt(0)
            f.line_spacing_rule=WD_LINE_SPACING.EXACTLY; f.line_spacing=Pt(c["line_pt"])
            f.keep_together=True; f.widow_control=False
            if index and j==0: f.page_break_before=True
            r=p.add_run(line); set_font(r,c["east_asia_font"],size,latin=c["latin_font"])
    stream=io.BytesIO(); doc.save(stream)
    return stream.getvalue()
