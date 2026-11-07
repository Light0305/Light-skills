#!/usr/bin/env python3
"""Distribute self-contained layout references; --check detects drift without writes."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def sync(check=False):
    common = (ROOT / "assets/common-contract.md").read_text(encoding="utf-8").rstrip()
    profiles = json.loads((ROOT / "assets/skill-layouts.json").read_text(encoding="utf-8"))
    changed = []
    for profile in profiles:
        skill = ROOT.parent / profile["skill"]
        if not (skill / "SKILL.md").is_file():
            raise ValueError(f"找不到实际 skill 入口：{skill}")
        content = ("<!-- Generated from project-layout/assets; update the source then sync. -->\n"
                   + common + "\n\n## 本技能的归档与交接\n\n默认工作区：`"
                   + profile["workspace"] + "`\n\n" + profile["detail"] + "\n")
        path = skill / "references/project-layout.md"
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            changed.append(str(path))
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
    return changed


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    changed = sync(args.check)
    print(json.dumps({"ok": not changed if args.check else True, "changed": changed}, ensure_ascii=False, indent=2))
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
