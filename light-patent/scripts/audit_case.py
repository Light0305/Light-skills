#!/usr/bin/env python3
"""Check recorded support and document structure, not legal/technical sufficiency."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

PROFILES = ("evidence", "disclosure", "claims", "application")
MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
PLACEHOLDER = re.compile(r"待补充|待填写|待确认|需发明人确认|\bTODO\b|TO CONFIRM|\{\{.+?\}\}|\[占位\]", re.I)
CATEGORIES = {"method", "product", "apparatus", "system", "device", "medium", "program-product", "use"}
SUPPORT = {"explicit", "entailed", "needs-confirmation", "unsupported"}


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def oneof(value, choices):
    return isinstance(value, str) and value in choices


def read_case(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def valid_omml(value):
    if not nonblank(value) or re.search(r"<!DOCTYPE|<!ENTITY", value, re.I):
        return False
    try:
        root = ET.fromstring(value)
        return root.tag in {f"{{{MATH_NS}}}oMath", f"{{{MATH_NS}}}oMathPara"} and any(
            el.tag == f"{{{MATH_NS}}}t" and nonblank(el.text) for el in root.iter())
    except (ET.ParseError, ValueError):
        return False


def claim_text(claim):
    """Compose only the supported subset of ordinary Chinese claim syntax."""
    if claim["kind"] == "independent":
        opening = f"{claim['subject']}，其特征在于，包括："
    else:
        refs = "或".join(str(x) for x in claim["depends_on"])
        opening = f"根据权利要求{refs}所述的{claim['subject']}，其特征在于，"
    body = "；".join(x["text"].strip().rstrip("；;。") for x in claim["limitations"])
    return f"{claim['number']}. {opening}{body}。"


def audit_case(data, base, profile="application"):
    if profile not in PROFILES:
        raise ValueError(f"未知检查档位：{profile}")
    base = Path(base)
    findings = []

    def add(severity, code, location, message):
        findings.append(dict(severity=severity, code=code, location=location, message=message))

    def err(code, location, message):
        add("ERROR", code, location, message)

    def warn(code, location, message):
        add("WARNING", code, location, message)

    def records(value, location):
        if not isinstance(value, list):
            err("TYPE", location, "应为数组")
            return []
        good = []
        for i, item in enumerate(value):
            if isinstance(item, dict):
                good.append(item)
            else:
                err("TYPE", f"{location}[{i}]", "数组成员应为对象")
        return good

    def index(items, location):
        result = {}
        for i, item in enumerate(items):
            key = item.get("id")
            if not nonblank(key):
                err("ID", f"{location}[{i}]", "缺少非空字符串 id")
            elif key in result:
                err("DUPLICATE_ID", location, f"重复 id：{key}")
            else:
                result[key] = item
        return result

    if not isinstance(data, dict):
        err("TYPE", "$", "案件文件顶层必须为对象")
        return findings
    if data.get("schema_version") != "1.0":
        err("VERSION", "schema_version", "本工具支持 schema_version 1.0")
    if not nonblank(data.get("title")):
        err("TITLE", "title", "缺少发明名称")
    if not oneof(data.get("patent_type"), {"invention", "utility-model"}):
        err("PATENT_TYPE", "patent_type", "应为 invention 或 utility-model")
    if not oneof(data.get("stage"), {"pre-filing", "filed"}):
        err("STAGE", "stage", "应为 pre-filing 或 filed")
    if data.get("jurisdiction") != "CN":
        err("JURISDICTION", "jurisdiction", "内置规则/拼接器只适用 CN；其他法域请单独撰写核验")

    sources = index(records(data.get("sources", []), "sources"), "sources")
    features = index(records(data.get("features", []), "features"), "features")
    figures = index(records(data.get("figures", []), "figures"), "figures")
    if not sources:
        warn("NO_SOURCES", "sources", "尚未记录材料；不能确认技术事实")
    for sid, src in sources.items():
        if src.get("role", "technical") not in ("technical", "original-application", "context", "prior-art"):
            err("SOURCE_ROLE", sid, "未知材料角色；背景/对比文献与本发明事实须分开")
        if src.get("sha256") is not None and not (
                isinstance(src["sha256"], str) and re.fullmatch(r"[0-9a-fA-F]{64}", src["sha256"])):
            err("SOURCE_HASH", sid, "sha256 若提供须为真实64位十六进制摘要")
        if not nonblank(src.get("path")) and not nonblank(src.get("url")):
            err("SOURCE_LOCATION", sid, "材料需有本地 path 或可核验 url")
        if nonblank(src.get("path")) and not (base / src["path"]).is_file():
            err("SOURCE_FILE", sid, f"材料文件不存在：{src['path']}")
        elif nonblank(src.get("path")) and nonblank(src.get("sha256")):
            digest = hashlib.sha256()
            with (base / src["path"]).open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != src["sha256"].lower():
                err("SOURCE_CHANGED", sid, "材料内容与记录的SHA-256不一致，需复核定位与支持")
        if src.get("reviewed") is not True:
            warn("SOURCE_UNREAD", sid, "材料尚未标记已阅读，不能支持正式限定")

    def check_refs(refs, location, required=False, original=False, formal=False):
        rows = records(refs, location)
        if required and not rows:
            err("MISSING_SUPPORT", location, "缺少可定位的支持依据")
        for ref in rows:
            sid = ref.get("source_id")
            src = sources.get(sid) if isinstance(sid, str) else None
            if src is None:
                err("SOURCE_REF", location, f"材料引用不存在：{sid}")
            else:
                if formal and src.get("reviewed") is not True:
                    err("UNREAD_SUPPORT", location, f"正式限定依赖未读材料：{sid}")
                if formal and src.get("role") in ("context", "prior-art"):
                    err("BACKGROUND_AS_DISCLOSURE", location, f"{sid} 是背景/对比材料，不能作为本发明正式限定的事实披露")
                if original and src.get("role") != "original-application":
                    err("ORIGINAL_BASIS", location, f"{sid} 未标记为原始申请文件")
                if original:
                    part = ref.get("document_part", src.get("document_kind"))
                    if part in ("abstract", "receipt", "later-supplement"):
                        err("ORIGINAL_PART", location, f"{sid} 所指材料不能单独作为新增技术限定的原始申请依据")
                    elif part not in ("specification", "claims", "drawings"):
                        warn("ORIGINAL_PART_UNRESOLVED", location, f"{sid} 尚需人工核对实际原说明书/权要/附图部位，角色标签不能证明修改有原始支持")
            if not nonblank(ref.get("locator")):
                err("LOCATOR", location, "依据缺少具体页/段/行/图式定位")

    for fid, feature in features.items():
        status = feature.get("support")
        if not oneof(status, SUPPORT):
            err("SUPPORT_STATUS", fid, "支持状态必须为四种约定值之一")
        if not nonblank(feature.get("text")):
            err("FEATURE_TEXT", fid, "缺少具体技术特征")
        check_refs(feature.get("source_refs", []), fid, required=oneof(status, {"explicit", "entailed"}))
        if status == "entailed" and not nonblank(feature.get("rationale")):
            err("ENTAILMENT", fid, "必然推导需说明推导及必要性")

    documents = data.get("documents", {})
    if not isinstance(documents, dict):
        err("TYPE", "documents", "应为文档对象")
        documents = {}
    docnames = {"evidence": [], "disclosure": ["disclosure"],
                "claims": ["specification"], "application": ["specification", "abstract"]}[profile]
    blocks = {}
    parsed_docs = {}
    spec_ids = set()
    used_figures = set()
    for name in docnames:
        rows = records(documents.get(name, []), f"documents.{name}")
        parsed_docs[name] = rows
        if not rows:
            err("EMPTY_DOCUMENT", name, "缺少当前任务必需的正文")
        for bid, block in index(rows, name).items():
            if bid in blocks:
                err("DUPLICATE_ID", bid, "文档块 id 必须跨当前文档唯一")
            blocks[bid] = block
            btype = block.get("type")
            if not oneof(btype, {"heading", "paragraph", "table", "equation", "image"}):
                err("BLOCK_TYPE", bid, "不支持的文档块类型")
            if oneof(btype, {"paragraph", "heading"}) and not nonblank(block.get("text")):
                err("EMPTY_BLOCK", bid, "标题或段落不能为空")
            if btype == "heading" and (type(block.get("level", 1)) is not int or not 1 <= block.get("level", 1) <= 3):
                err("HEADING", bid, "标题 level 应为1至3的整数")
            if btype == "table":
                headers, rows_t = block.get("headers"), block.get("rows")
                if (not isinstance(headers, list) or not headers or not all(isinstance(x, str) for x in headers)
                        or not isinstance(rows_t, list) or not rows_t
                        or any(not isinstance(row, list) or len(row) != len(headers)
                               or not all(isinstance(cell, str) for cell in row) for row in rows_t)):
                    err("TABLE", bid, "表格需非空字符串 headers 和等宽字符串 rows")
            if btype == "equation":
                if not nonblank(block.get("latex")) and not valid_omml(block.get("omml")):
                    err("EQUATION", bid, "公式缺少 LaTeX 或有效 OMML")
                if block.get("omml") and not valid_omml(block["omml"]):
                    err("OMML", bid, "OMML 不是有效的 Office Math 结构")
            if btype == "image":
                gid = block.get("figure_id")
                if not isinstance(gid, str) or gid not in figures:
                    err("FIGURE_REF", bid, f"图件不存在：{gid}")
                else:
                    used_figures.add(gid)
            if name == "specification" and oneof(btype, {"paragraph", "equation", "table"}):
                spec_ids.add(bid)
            if PLACEHOLDER.search(json.dumps(block, ensure_ascii=False)):
                (warn if name == "disclosure" else err)("PLACEHOLDER", bid, "正文含待补/确认占位，需判断并处理")

    claim_rows = records(data.get("claims", []), "claims") if profile in {"claims", "application"} else []
    claims = {}
    if profile in {"claims", "application"} and not claim_rows:
        err("NO_CLAIMS", "claims", "缺少权利要求")
    for pos, claim in enumerate(claim_rows, 1):
        n = claim.get("number")
        loc = f"claim:{n}"
        if type(n) is not int or n != pos:
            err("CLAIM_NUMBER", loc, "权要需从1起按数组顺序连续编号")
        if type(n) is int:
            claims[n] = claim
        kind = claim.get("kind")
        if not oneof(kind, {"independent", "dependent"}):
            err("CLAIM_KIND", loc, "kind 应为 independent 或 dependent")
        if not oneof(claim.get("category"), CATEGORIES):
            err("CATEGORY", loc, "不支持的权要类别")
        if data.get("patent_type") == "utility-model" and not oneof(claim.get("category"), {"product", "apparatus", "system", "device"}):
            err("UTILITY_SUBJECT", loc, "实用新型不能使用该权要类别")
        if not nonblank(claim.get("subject")):
            err("SUBJECT", loc, "缺少主题名称")
        deps = claim.get("depends_on", [])
        if not isinstance(deps, list) or any(type(x) is not int for x in deps):
            err("DEPENDENCY_TYPE", loc, "depends_on 应为整数数组")
            deps = []
        if len(set(deps)) != len(deps):
            err("DEPENDENCY_DUPLICATE", loc, "引用编号重复")
        if kind == "independent" and deps:
            err("DEPENDENCY", loc, "独立权要不应作为从属引用其他权要")
        if kind == "dependent" and not deps:
            err("DEPENDENCY", loc, "从属权要需引用在前权要")
        for dep in deps:
            if type(n) is not int or dep >= n or dep not in claims:
                err("DEPENDENCY", loc, f"引用不存在或不在前：{dep}")
        if len(deps) > 1:
            if claim.get("dependency_mode") != "any":
                err("MULTIPLE_MODE", loc, "多项从属须择一引用")
            for dep in deps:
                parent_deps = claims.get(dep, {}).get("depends_on", [])
                if isinstance(parent_deps, list) and len(parent_deps) > 1:
                    err("MULTIPLE_BASE", loc, "多项从属不能引用另一多项从属作为基础")
        limitations = records(claim.get("limitations", []), loc + ".limitations")
        if not limitations:
            err("LIMITATIONS", loc, "权要需有具体且可映射的限定")
        for i, limitation in enumerate(limitations, 1):
            lloc = f"{loc}.limitation:{i}"
            if not nonblank(limitation.get("text")):
                err("LIMITATION_TEXT", lloc, "限定文本不能为空")
            if PLACEHOLDER.search(str(limitation.get("text", ""))):
                err("PLACEHOLDER", lloc, "正式权要不能包含待补占位")
            for key in ("feature_ids", "spec_ids"):
                ids = limitation.get(key)
                if not isinstance(ids, list) or not ids or not all(nonblank(x) for x in ids):
                    err("LIMITATION_MAP", lloc, f"{key} 需非空字符串数组")
                    continue
                for item_id in ids:
                    if key == "spec_ids":
                        if item_id not in spec_ids:
                            err("SPEC_SUPPORT", lloc, f"说明书实质内容块不存在：{item_id}")
                    else:
                        feature = features.get(item_id)
                        if feature is None:
                            err("FEATURE_REF", lloc, f"特征不存在：{item_id}")
                            continue
                        if not oneof(feature.get("support"), {"explicit", "entailed"}):
                            err("UNSUPPORTED_CLAIM", lloc, f"{item_id} 尚无正式限定支持")
                        check_refs(feature.get("source_refs", []), lloc, required=True, formal=True)
                        if data.get("stage") == "filed":
                            check_refs(feature.get("original_refs", []), lloc, required=True, original=True, formal=True)
        if PLACEHOLDER.search(str(claim.get("subject", ""))):
            err("PLACEHOLDER", loc, "权要主题含占位")
    if claim_rows and not any(c.get("kind") == "independent" for c in claim_rows):
        err("NO_INDEPENDENT", "claims", "缺少独立权利要求")

    if profile == "application":
        abstract = "".join(b.get("text", "") for b in parsed_docs.get("abstract", [])
                           if isinstance(b, dict) and b.get("type") == "paragraph" and isinstance(b.get("text"), str))
        if len(re.sub(r"\s", "", abstract)) > 300:
            warn("ABSTRACT_LENGTH", "abstract", "摘要超过300个非空白字符，需按当前要求复核")
        if not abstract.strip():
            err("ABSTRACT_TEXT", "abstract", "摘要缺少实质段落")
        abstract_id = data.get("abstract_figure_id")
        if figures and (not isinstance(abstract_id, str) or abstract_id not in figures):
            err("ABSTRACT_FIGURE", "abstract_figure_id", "有图申请需指定说明书中的摘要附图")
        if not figures and abstract_id is not None:
            err("ABSTRACT_FIGURE", "abstract_figure_id", "无图案件的摘要附图应为 null")
        if data.get("patent_type") == "utility-model" and not figures:
            err("UTILITY_FIGURES", "figures", "实用新型缺少产品结构附图")
        for gid in figures:
            if gid not in used_figures:
                err("FIGURE_UNUSED", gid, "图件未在说明书中以 image 块登记")
        used_figures.update(figures)
    for gid in used_figures:
        fig = figures[gid]
        if not nonblank(fig.get("title")):
            err("FIGURE_TITLE", gid, "缺少图件标题")
        path = fig.get("path")
        if not nonblank(path) or not (base / path).is_file():
            err("FIGURE_FILE", gid, f"入文图件不存在：{path}")
        elif Path(path).suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            err("FIGURE_FORMAT", gid, "入文图件需 PNG/JPEG，矢量源另外保留")

    for question in records(data.get("questions", []), "questions"):
        if question.get("severity") == "blocking":
            (err if profile in {"claims", "application"} else warn)(
                "OPEN_BLOCKER", str(question.get("id", "questions")), str(question.get("text", "存在阻断问题")))
    search = data.get("search", {})
    if not isinstance(search, dict):
        err("TYPE", "search", "search 应为对象")
    elif profile in {"claims", "application"}:
        if search.get("status") != "completed":
            warn("SEARCH_LIMIT", "search", f"检索状态 {search.get('status')}；不得给出确定的查新/授权结论")
        elif not isinstance(search.get("queries"), list) or not search["queries"]:
            warn("SEARCH_LOG", "search", "声称完成检索但未保留实际检索记录")
    for ref in records(data.get("prior_art", []), "prior_art"):
        if ref.get("verified") is not True:
            warn("UNVERIFIED_PRIOR_ART", str(ref.get("id", "prior_art")), "该对比文献尚未核验，不能作为确定论据")
    return findings


def report_for(data, base, profile):
    findings = audit_case(data, base, profile)
    return {
        "profile": profile, "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": "结构与已记录的支持链；未判断技术实质、法律结论或版式",
        "errors": sum(x["severity"] == "ERROR" for x in findings),
        "warnings": sum(x["severity"] == "WARNING" for x in findings), "findings": findings,
    }


def report_markdown(report):
    lines = ["# 案件结构检查", "", report["scope"], "",
             f"错误 {report['errors']} 项；警告 {report['warnings']} 项。", ""]
    for item in report["findings"]:
        lines.append(f"- {item['severity']} [{item['code']}] {item['location']}：{item['message']}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case")
    parser.add_argument("--profile", choices=PROFILES, default="application")
    parser.add_argument("--out")
    parser.add_argument("--format", choices=["json", "md"], default="json")
    args = parser.parse_args()
    try:
        path = Path(args.case).resolve()
        report = report_for(read_case(path), path.parent, args.profile)
        result = report_markdown(report) if args.format == "md" else json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            dest = Path(args.out)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(result, encoding="utf-8")
        else:
            print(result, end="")
        return 2 if report["errors"] else 0
    except (OSError, ValueError) as exc:
        print(f"检查失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
