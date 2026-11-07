"""Actually executable synthetic software; no applicant or reference business facts."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import copyright_case as cc
import render_materials as renderer

PROGRAM = '''"""Validate measurement CSV and export grouped descriptive statistics."""
import argparse
import csv
import json
import math
from pathlib import Path


def read_measurements(path):
    records = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"group", "value"} <= set(reader.fieldnames or []):
            raise ValueError("CSV must contain group and value columns")
        for line, row in enumerate(reader, 2):
            group = row["group"].strip()
            if not group:
                raise ValueError(f"Missing group at line {line}")
            try:
                value = float(row["value"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid value at line {line}") from exc
            if not math.isfinite(value):
                raise ValueError(f"Non-finite value at line {line}")
            records.append((group, value))
    if not records:
        raise ValueError("CSV contains no measurements")
    return records


def summarize(records):
    groups = {}
    for group, value in records:
        groups.setdefault(group, []).append(value)
    results = []
    for group, values in sorted(groups.items()):
        total = math.fsum(values)
        results.append({
            "group": group,
            "count": len(values),
            "sum": total,
            "mean": total / len(values),
            "minimum": min(values),
            "maximum": max(values),
        })
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        records = read_measurements(args.input)
        result = {"record_count": len(records), "groups": summarize(records)}
    except (OSError, ValueError) as exc:
        parser.exit(2, str(exc) + "\\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\\n",
        encoding="utf-8",
    )
    print(f"Validated {len(records)} records; wrote {args.output.name}")


if __name__ == "__main__":
    main()
'''


def p(text):
    return {"type":"paragraph","text":text}


def sec(heading, *blocks):
    return {"heading":heading,"level":1,"blocks":list(blocks)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    out=Path(args.out).resolve()
    if out.exists():
        raise ValueError("Use a new isolated output directory")
    project=out/"project"; project.mkdir(parents=True)
    (project/"measure.py").write_text(PROGRAM,encoding="utf-8")
    (project/"sample.csv").write_text("group,value\nA,2\nA,4\nB,10\nB,14\n",encoding="utf-8")
    (project/"bad.csv").write_text("group,value\nA,nan\n",encoding="utf-8")
    runs=[]
    for name,expected in (("sample",0),("bad",2)):
        cmd=[sys.executable,"-B",str(project/"measure.py"),str(project/(name+".csv")),
             "--output",str(project/"results"/(name+".json"))]
        r=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8")
        runs.append({"name":name,"command":cmd,"exit_code":r.returncode,"stdout":r.stdout,"stderr":r.stderr})
        assert r.returncode==expected, r.stderr
    result=cc.read_json(project/"results/sample.json")
    assert [g["mean"] for g in result["groups"]]==[3.0,12.0]
    assert not (project/"results/bad.json").exists()
    case=out/"SoftwareCopyright/SWC-0001_合成测量汇总V0.1"
    cc.init_case(project,case); cc.scan_case(case)
    sel=cc.read_json(case/"selection.json")
    sel.update(scope_reviewed=True,scope_note="Read the entire self-contained measure.py CLI",
               skipped_review="CSV and results JSON are synthetic data/output, not code")
    for item in sel["files"]:
        item.update(decision="include" if item["path"]=="measure.py" else "exclude",
                    reason="Synthetic original CLI" if item["path"]=="measure.py" else "Data/output, not program")
    cc.write_json(case/"selection.json",sel)
    facts=cc.read_json(case/"case.json")
    facts.update(software_name="合成测量汇总工具",version="V0.1",languages=["Python"],
                 purpose="对合成测量记录做校验和描述性分组汇总。")
    facts["reviews"].update(third_party_review="合成程序仅用Python标准库，无外部实现复制。",
                            source_ending_review="已读完整文件，末尾为main入口。",visual_review=None)
    lines=PROGRAM.splitlines()
    facts["features"]=[]
    for fid,fh,mh,func,next_func in [
        ("F1","数据读入与校验","输入数据校验","read_measurements","def summarize"),
        ("F2","分组汇总","汇总与导出","summarize","def main"),
        ("F3","结果导出","汇总与导出","main",None)]:
        start=next(i for i,l in enumerate(lines,1) if l.startswith("def "+func+"("))
        end=next((i-1 for i,l in enumerate(lines,1) if next_func and l.startswith(next_func)),len(lines))
        facts["features"].append({"id":fid,"name":fh,"status":"implemented","function_heading":fh,"manual_heading":mh,
             "evidence":[{"path":"measure.py","lines":[start,end],"sha256":cc.file_hash(project/"measure.py")}]})
    cc.write_json(case/"case.json",facts)
    cc.write_json(case/"functions.json",{"document_type":"功能说明","sections":[
        sec("软件概述",p("本工具校验CSV测量记录，生成按组统计的JSON结果。这是材料工具升级的合成验证样例，不对应真实申请人；无界面、账号、训练或云服务。")),
        sec("数据读入与校验",p("输入为UTF-8或带BOM的CSV，必须含group和value列。程序检查非空组名和有限数值。缺列、空组、非法或非有限值会中止，返回码2，不生成该次统计结果。"),
            {"type":"steps","items":["准备含表头的CSV。","运行程序并指定输出路径。","若报错，按行号修正后重新运行。"]}),
        sec("分组汇总",p("全部输入通过校验后，按组名排序，计算条数、合计、均值、最小值和最大值。输出仅描述输入记录，不含显著性检验或因果结论。")),
        sec("结果导出",p("保存JSON并打印条数。实际样例为A组2和4、B组10和14，得到均值3和12。输出路径存在时会覆盖，使用者应另存旧结果。"))]})
    cc.write_json(case/"manual.json",{"document_type":"使用说明书","sections":[
        sec("运行条件",p("本次在本地Python解释器验证，仅用标准库。输入需可读，输出位置需可写。未验证其他操作系统、生产数据或大量记录性能。本合成软件不代表真实登记项目。")),
        sec("输入数据校验",p("read_measurements逐行检查。group去首尾空白后不得为空，value通过浮点转换和有限性检查。第一处错误即退出，不补零、不跳过错误行。"),
            {"type":"table","headers":["字段","约束","示例"],"rows":[["group","非空组名","A"],["value","有限浮点数","2"]]}),
        sec("操作步骤",{"type":"steps","items":["进入measure.py所在目录。","准备sample.csv并检查表头和编码。","执行命令，查看JSON结果。"]},
            {"type":"code","text":"python measure.py sample.csv --output results/sample.json"},
            p("本次实际打印“Validated 4 records; wrote sample.json”。A、B各2条，该日志只对应本次合成样例。")),
        sec("汇总与导出",p("summarize分组后用math.fsum求和。顶层record_count为记录总数，groups按组名排序；每组含count、sum、mean、minimum、maximum。"),
            {"type":"table","headers":["组名","条数","合计","均值","最小","最大"],"rows":[["A","2","6","3","2","4"],["B","2","24","12","10","14"]]},
            p("结果以UTF-8写出，自动创建父目录并覆盖同名结果；写出失败由解释器报告，不保证旧结果事务性保留。")),
        sec("错误与限制",p("以value=nan实际运行返回2，提示“Non-finite value at line 2”，未产生bad.json。不可读文件、缺列、无记录同样返回2。无GUI、登录、在线同步、数据库或预测模型。"))]})
    cc.extract_case(case)
    paths=renderer.render(case,"bundle",["docx"])
    audit=cc.audit_case(case)
    assert any("visual_review" in e for e in audit["errors"])
    cc.write_json(out/"exercise-result.json",{"synthetic":True,"software_runs":runs,"results":result,
        "case":str(case),"paths":[str(p) for p in paths],"source_pages":cc.verify_pages(case)["submitted_pages"],
        "audit_before_visual":audit,"scope":"Synthetic tool exercise; not a real registration project."})
    print(json.dumps({"out":str(out),"case":str(case),"documents":[str(p) for p in paths]},ensure_ascii=False))


if __name__=="__main__":
    main()
