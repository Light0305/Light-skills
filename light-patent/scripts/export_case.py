#!/usr/bin/env python3
"""Export supported CN drafting records to separate review documents."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

from audit_case import claim_text, nonblank, read_case, report_for, valid_omml


def compose_documents(data, kind):
    def named(blocks):
        if any(b.get("text") == data["title"] for b in blocks):
            return blocks
        return [{"type": "heading", "level": 1, "text": data["title"]}] + blocks

    docs = []
    if kind == "disclosure":
        return [("01_技术交底书", named(data["documents"]["disclosure"]))]
    claims = [{"type": "paragraph", "text": claim_text(c)} for c in data["claims"]]
    docs.append(("02_权利要求书", claims))
    if kind == "application":
        docs.append(("03_说明书", named([b for b in data["documents"]["specification"] if b["type"] != "image"])))
        docs.append(("04_说明书摘要", data["documents"]["abstract"]))
        if data.get("figures"):
            docs.append(("05_说明书附图", [{"type": "image", "figure_id": f["id"]} for f in data["figures"]]))
            docs.append(("06_摘要附图", [{"type": "image", "figure_id": data["abstract_figure_id"]}]))
    return docs


def blocks_to_markdown(title, blocks, figures):
    lines = ["# " + title, ""]
    for b in blocks:
        t = b["type"]
        if t == "heading":
            lines += ["#" * (b.get("level", 1) + 1) + " " + b["text"], ""]
        elif t == "paragraph":
            lines += [b["text"], ""]
        elif t == "image":
            f = figures[b["figure_id"]]
            lines += [f"![{f['title']}]({f['path']})", "", f["title"], ""]
        elif t == "equation":
            if nonblank(b.get("latex")):
                lines += ["$$", b["latex"], "$$", ""]
            else:
                lines += ["```xml", b["omml"], "```", ""]
        elif t == "table":
            def cell(s):
                return s.replace("|", "\\|").replace("\n", "<br>")
            lines.append("| " + " | ".join(cell(s) for s in b["headers"]) + " |")
            lines.append("| " + " | ".join("---" for _ in b["headers"]) + " |")
            lines += ["| " + " | ".join(cell(s) for s in row) + " |" for row in b["rows"]]
            lines.append("")
    return "\n".join(lines)


def write_docx(path, title, blocks, figures, base):
    # Optional dependency is imported only for Word export.
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import parse_xml
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = Cm(2.5)
    for name in ("Normal", "Title", "Heading 1", "Heading 2", "Heading 3"):
        style = doc.styles[name]
        style.font.name = "Times New Roman"
        style._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.size = Pt(12 if name == "Normal" else 14)
    normal = doc.styles["Normal"].paragraph_format
    normal.line_spacing = 1.5
    normal.space_after = Pt(6)
    doc.core_properties.author = ""
    doc.core_properties.last_modified_by = ""
    doc.core_properties.title = title
    doc.add_paragraph(title, "Title")
    for b in blocks:
        t = b["type"]
        if t == "heading":
            doc.add_paragraph(b["text"], f"Heading {b.get('level', 1)}")
        elif t == "paragraph":
            doc.add_paragraph(b["text"])
        elif t == "equation":
            if not valid_omml(b.get("omml")):
                raise ValueError("Word 公式需要有效 OMML；不能以 LaTeX 字符串替代")
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p._p.append(parse_xml(b["omml"]))
        elif t == "image":
            f = figures[b["figure_id"]]
            # Fit tall and wide figures without changing aspect ratio.
            from docx.image.image import Image
            img = Image.from_file(str(base / f["path"]))
            aspect = img.px_width / img.px_height
            width_cm = min(16, 21 * aspect)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next = True
            p.add_run().add_picture(str(base / f["path"]), width=Cm(width_cm))
            caption = doc.add_paragraph(f["title"])
            caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif t == "table":
            table = doc.add_table(rows=1, cols=len(b["headers"]))
            table.style = "Table Grid"
            table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
            for c, text in zip(table.rows[0].cells, b["headers"]):
                c.text = text
            for row in b["rows"]:
                for c, text in zip(table.add_row().cells, row):
                    c.text = text
            doc.add_paragraph()
    doc.save(path)


def support_markdown(data):
    features = {f["id"]: f for f in data.get("features", [])}
    lines = ["# 逐限定支持记录", "", "本表是已记录的支持链，仍需逐项检查实质支持及范围。", ""]
    for c in data.get("claims", []):
        lines += [f"## 权利要求{c['number']}", ""]
        for lim in c["limitations"]:
            lines += [lim["text"], "", "说明书块：" + ", ".join(lim["spec_ids"]), ""]
            for fid in lim["feature_ids"]:
                f = features[fid]
                refs = "；".join(f"{r['source_id']} / {r['locator']}" for r in f["source_refs"])
                lines.append(f"- {fid} [{f['support']}] {refs}")
                if f.get("rationale"):
                    lines.append("  推导：" + f["rationale"])
                if f.get("original_refs"):
                    lines.append("  原申请：" + "；".join(f"{r['source_id']} / {r['locator']}" for r in f["original_refs"]))
            lines.append("")
    return "\n".join(lines)


def recorded_inputs(data, base):
    """Only explicitly declared local sources and figures, never a project crawl."""
    rows = []
    for item in data.get("sources", []):
        if nonblank(item.get("path")):
            rows.append(("source:"+item["id"], base / item["path"]))
    for item in data.get("figures", []):
        for key in ("path", "source_path"):
            if nonblank(item.get(key)) and (base/item[key]).is_file():
                rows.append(("figure:"+item["id"]+":"+key, base/item[key]))
    return [{"id":name, "path":str(path.resolve()),
             "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
             "bytes":path.stat().st_size} for name,path in rows]


def verify_export(case_path, out):
    case_path, out = Path(case_path).resolve(), Path(out).resolve()
    manifest = read_case(out/"交付清单.json")
    errors = []
    def check(ok, message):
        if not ok: errors.append(message)
    check(hashlib.sha256(case_path.read_bytes()).hexdigest()==manifest.get("source_case_sha256"),"Case record changed")
    seen=set()
    files=manifest.get("files")
    if not isinstance(files,list) or not files:
        raise ValueError("Delivery manifest needs a nonempty files list")
    for item in files:
        name=item["path"]; path=(out/name).resolve()
        if Path(name).is_absolute() or not path.is_relative_to(out) or path==out or path in seen:
            raise ValueError("Unsafe or duplicate delivery file path")
        seen.add(path)
        check(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==item["sha256"],"Delivery changed or missing: "+name)
    if "source_inputs" in manifest:
        try:
            current={r["id"]:r for r in recorded_inputs(read_case(case_path),case_path.parent)}
        except OSError as exc:
            errors.append("Recorded source unavailable: " + str(exc))
            current={}
        recorded=manifest["source_inputs"]
        if not isinstance(recorded,list) or len({r["id"] for r in recorded})!=len(recorded):
            raise ValueError("Invalid or duplicate recorded source input")
        check({r["id"] for r in recorded}==set(current),"Declared source set changed")
        for item in recorded:
            check(current.get(item["id"])==item,"Recorded source changed: "+item["id"])
    return {"ok":not errors,"errors":errors,"scope":"recorded_case_sources_and_exports" if "source_inputs" in manifest else "recorded_case_and_exports_only",
            "visual_review":manifest.get("visual_review","not-recorded"),
            "meaning":"Recorded bytes only; no technical, legal, novelty, visual or filing certification."}


def export_case(case_path, out, kind="application", fmt="both"):
    case_path, out = Path(case_path).resolve(), Path(out).resolve()
    if out.exists():
        raise ValueError(f"输出位置已存在，请使用新的交付目录：{out}")
    if fmt not in {"md", "docx", "both"} or kind not in {"application", "claims", "disclosure"}:
        raise ValueError("不支持的交付种类或格式")
    case_sha = hashlib.sha256(case_path.read_bytes()).hexdigest()
    data = read_case(case_path)
    report = report_for(data, case_path.parent, kind)
    if report["errors"]:
        first = next(f for f in report["findings"] if f["severity"] == "ERROR")
        raise ValueError(f"结构检查存在{report['errors']}项错误；{first['code']} {first['location']}：{first['message']}。请先运行 audit_case.py 查看完整报告")
    source_inputs = recorded_inputs(data, case_path.parent)
    docs = compose_documents(data, kind)
    if fmt in {"docx", "both"}:
        try:
            import docx  # noqa: F401
        except ImportError as exc:
            raise ValueError("Word 导出需要 python-docx；可安装 requirements-docx.txt 或使用 --format md") from exc
        for _, blocks in docs:
            for b in blocks:
                if b["type"] == "equation" and not valid_omml(b.get("omml")):
                    raise ValueError(f"公式 {b.get('id', '')} 缺少有效 OMML，尚不能导出可编辑 Word 公式")
    out.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="." + out.name + ".building-", dir=out.parent))
    try:
        # Copy only figures actually included in this delivery; source paths stay local.
        used_ids = {b["figure_id"] for _, blocks in docs for b in blocks if b["type"] == "image"}
        figures = {}
        for i, f in enumerate(data.get("figures", []), 1):
            if f["id"] not in used_ids:
                continue
            item = deepcopy(f)
            src = case_path.parent / f["path"]
            rel = Path("figures") / f"figure-{i}{src.suffix.lower()}"
            (staging / rel).parent.mkdir(exist_ok=True)
            shutil.copyfile(src, staging / rel)
            item["path"] = rel.as_posix()
            figures[f["id"]] = item
        for name, blocks in docs:
            title = name.split("_", 1)[1]
            if fmt in {"md", "both"}:
                (staging / (name + ".md")).write_text(blocks_to_markdown(title, blocks, figures), encoding="utf-8")
            if fmt in {"docx", "both"}:
                write_docx(staging / (name + ".docx"), title, blocks, figures, staging)
        (staging / "检查报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        if kind in {"claims", "application"}:
            (staging / "支持表.md").write_text(support_markdown(data), encoding="utf-8")
        notes = {"questions": data.get("questions", []), "search": data.get("search", {}), "prior_art": data.get("prior_art", [])}
        (staging / "复核事项.json").write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest = {
            "schema_version": "1.1",
            "title": data["title"], "kind": kind, "format": fmt,
            "status": "供发明人及专利专业人员复核的撰写草稿",
            "semantic_review": "not-certified-by-tool", "visual_review": "not-performed",
            "filing_status": "未进行电子提交或官方格式合规验证",
            "source_case_sha256": case_sha, "source_inputs": source_inputs,
            "files": [{"path": p.relative_to(staging).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in sorted(staging.rglob("*")) if p.is_file()],
        }
        if hashlib.sha256(case_path.read_bytes()).hexdigest()!=case_sha or recorded_inputs(data,case_path.parent)!=source_inputs:
            raise ValueError("Case or declared inputs changed during export; re-read and review before retrying")
        (staging / "交付清单.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        staging.rename(out)
    except Exception as exc:
        raise ValueError(f"导出未完成；诊断暂存目录 {staging}；原因：{exc}") from exc
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case")
    parser.add_argument("--kind", choices=["application", "claims", "disclosure"], default="application")
    parser.add_argument("--format", choices=["md", "docx", "both"], default="both")
    parser.add_argument("--out", required=True)
    parser.add_argument("--verify", action="store_true", help="Read-only comparison of an existing delivery and its recorded inputs")
    args = parser.parse_args()
    try:
        if args.verify:
            result=verify_export(args.case,args.out)
            print(json.dumps(result,ensure_ascii=False))
            return 0 if result["ok"] else 2
        print(export_case(args.case, args.out, args.kind, args.format))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"导出失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
