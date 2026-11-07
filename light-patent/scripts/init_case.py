#!/usr/bin/env python3
"""Create a patent drafting workspace without copying source material."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys


def init_case(out, title, patent_type="invention", stage="pre-filing"):
    out = Path(out).resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError(f"输出位置已存在且非空：{out}")
    if not title.strip():
        raise ValueError("案件名称不能为空")
    data = {
        "schema_version": "1.0", "title": title.strip(), "jurisdiction": "CN",
        "patent_type": patent_type, "stage": stage,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sources": [], "features": [], "claims": [],
        "documents": {"disclosure": [], "specification": [], "abstract": []},
        "figures": [], "abstract_figure_id": None,
        "search": {"status": "pending", "queries": [], "limitations": []},
        "prior_art": [], "questions": [],
    }
    out.mkdir(parents=True, exist_ok=True)
    for folder in ("work", "drafts", "figures"):
        (out / folder).mkdir(exist_ok=True)
    with (out / "case.json").open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return out / "case.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--patent-type", choices=["invention", "utility-model"], default="invention")
    parser.add_argument("--stage", choices=["pre-filing", "filed"], default="pre-filing")
    args = parser.parse_args()
    try:
        print(init_case(args.out, args.title, args.patent_type, args.stage))
    except (OSError, ValueError) as exc:
        print(f"初始化失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
