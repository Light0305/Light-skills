"""Synthetic CLI exercise; does not benchmark an independent scientific reviewer."""
import argparse
import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / "light-review/scripts/review_packet.py"
WRITE = ROOT / "light-write/scripts/audit_manuscript.py"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as f:
        f.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    project = out / "synthetic-project"
    events = []

    def run(name, command, expected=0):
        result = subprocess.run([sys.executable, "-X", "utf8", "-B", *map(str, command)],
                                capture_output=True, text=True, encoding="utf-8")
        event = {"name": name, "exit": result.returncode, "expected": expected,
                 "stdout": result.stdout, "stderr": result.stderr}
        events.append(event)
        save(out / "logs" / (name + ".json"), event)
        if result.returncode != expected:
            raise RuntimeError(f"{name}: expected {expected}, got {result.returncode}: {result.stderr}")
        return json.loads(result.stdout) if result.stdout.strip() else None

    data = project / "Experiment/Data/sites.csv"
    save(data, "site,A,B\nX,0.72,0.70\nY,0.68,0.65\nZ,0.53,0.55\n")
    code = project / "Analysis/AN-0001_descriptive/calculate.py"
    save(code, '''import csv, json, statistics, sys
from pathlib import Path
rows = list(csv.DictReader(Path(sys.argv[1]).open(encoding="utf-8")))
a, b = ([float(row[k]) for row in rows] for k in ("A", "B"))
print(json.dumps({"basis":"synthetic descriptive data; no inferential test",
 "mean_A":statistics.mean(a), "mean_B":statistics.mean(b),
 "A_below_B":[r["site"] for r in rows if float(r["A"]) < float(r["B"])]}))
''')
    calculated = run("calculate", [code, data])
    assert calculated["A_below_B"] == ["Z"]
    assert calculated["mean_A"] > calculated["mean_B"]
    result_path = code.parent / "results.json"
    save(result_path, calculated)
    original_data_hash = sha(data)
    strong = "A is better than B at every site."
    bounded = "A has a higher macro-average across these three synthetic sites, but is lower at site Z."
    previous_review = previous_packet = previous_write = None
    round_results = []
    for number, (abstract, conclusion, state) in enumerate([
        (strong, strong, "open"), (bounded, strong, "addressed"), (bounded, bounded, "verified")
    ], 1):
        draft_dir = project / f"Write/Paper-01_synthetic/drafts/v{number:02d}"
        manuscript = draft_dir / "manuscript.md"
        save(manuscript, f"# Synthetic local manuscript v{number:02d}\n\n"
             f"## Abstract\n{abstract}\n\n## Results\n"
             "Higher is better. X: A=0.72, B=0.70; Y: A=0.68, B=0.65; Z: A=0.53, B=0.55.\n"
             "These are three illustrative sites, not a population inference.\n\n"
             f"## Conclusion\n{conclusion}\n")
        write_packet = draft_dir / "manuscript-packet.json"

        def rel(path):
            return Path(os.path.relpath(path, draft_dir)).as_posix()

        wp = {"schema_version":"1.0", "basis":"Synthetic local revision exercise; actual CSV and code computed; no independent review.",
              "manuscript":{"paper_id":"Paper-01", "revision":f"v{number:02d}", "path":rel(manuscript), "sha256":sha(manuscript)},
              "sources":[{"id":key, "role":role, "path":rel(path), "sha256":sha(path)} for key, role, path in [
                  ("data","data",data), ("results","analysis",result_path), ("code","code",code)]],
              "claims":[{"id":"C1", "anchor":conclusion, "status":"supported" if number == 3 else "needs_evidence",
                         "boundary":"Synthetic descriptive sample only; no causal, significance or population claim.",
                         "evidence":[{"source_id":"results","locator":"mean_A, mean_B and A_below_B"}]}],
              "protected_literals":[{"source_id":"data","text":"0.53"}],
              "parent":None if previous_write is None else {"path":rel(previous_write),"sha256":sha(previous_write)}}
        save(write_packet, wp)
        audit = run(f"write-audit-{number}", [WRITE, write_packet])
        review_dir = project / f"Review/REV-{number:04d}_synthetic"
        packet = review_dir / "packet"
        run(f"freeze-{number}", [REVIEW,"freeze","--out",packet,
            "--file",f"manuscript={manuscript}","--file",f"data={data}",
            "--file",f"context={result_path}","--file",f"code={code}"])
        manifest = json.loads((packet/"packet.json").read_text(encoding="utf-8"))
        record = json.loads((packet/"review.stub.json").read_text(encoding="utf-8"))
        ptr = lambda mid, anchor: {"material_id":mid, "anchor":anchor}
        record.update(review_status="final", scope="focused" if number == 1 else "recheck",
            assessment_complete=False,
            summary="Synthetic text/numerical review only; abstract-only repair is insufficient." if number < 3 else "Targeted issue closed after rereading abstract, results and conclusion; full review still not assessed.",
            strengths=["The displayed Z values preserve the counterexample."],
            limitations=["Synthetic exercise by this executor; no independent model or expert.", "No figures, complete methods, ethics, citations or venue checks."])
        for item in record["coverage"]:
            item.update(status="inspected", notes="Actual text/CSV/result/script read for this local synthetic exercise.")
        for check in record["checks"]:
            check.update(notes="Outside this focused synthetic audit.", status="not_assessable")
            if check["check"] in {"claims","numerical"}:
                check.update(status="issue" if check["check"] == "claims" and number < 3 else "passed",
                    notes="Read actual abstract, results, conclusion and computed descriptive results.",
                    evidence=[ptr("M001","Abstract / Results / Conclusion"),ptr("M003","A_below_B / mean_A / mean_B")])
        record["claims"] = [{"id":"C1","text":conclusion,"central":True,
            "location":ptr("M001","Conclusion"),"assessment":"contradicted" if number < 3 else "supported",
            "evidence":[ptr("M002","site Z"),ptr("M003","mean_A / mean_B / A_below_B")]}]
        issue = {"id":"LR-001","severity":"major","category":"claim","basis":"audit",
            "evidence_status":"confirmed","confidence":"high","blocking":True,"required":True,
            "status":state,"claim_ids":["C1"],"source_ids":[],"owner":"light-write",
            "location":ptr("M001","Conclusion"),
            "evidence":[ptr("M002","site Z: A=0.53, B=0.55")],
            "observation":"The initial all-site superiority claim conflicts with site Z.",
            "impact":"Universal superiority cannot be retained on these descriptive data.",
            "suggested_fix":"Narrow the claim in the abstract and conclusion, retaining the site-Z exception.",
            "closure_test":"Read abstract, results and conclusion; no all-site superiority remains.",
            "resolution_evidence":[]}
        if number == 3:
            issue.update(resolution_evidence=[ptr("M001","Abstract / Results / Conclusion"),ptr("M003","A_below_B")],
                         closure_check={"packet_id":manifest["packet_id"],"method":"rechecked",
                           "notes":"Actual reread and literal check found no universal statement; site Z retained. This closes only LR-001."})
            assert strong not in manuscript.read_text(encoding="utf-8")
        if number == 2:
            assert strong in manuscript.read_text(encoding="utf-8").split("## Conclusion\n")[1]
        record["issues"] = [issue]
        record["readiness"] = {"scientific":"hold" if number < 3 else "not_assessable",
            "submission":"not_requested","rationale":"Only a targeted synthetic text/number audit; closure does not establish full scientific readiness."}
        args = [REVIEW,"validate","--packet",packet]
        parent_args = []
        if previous_review is not None:
            record["previous_review"] = {"packet_id":json.loads((previous_packet/"packet.json").read_text(encoding="utf-8"))["packet_id"],
                                         "record_sha256":sha(previous_review)}
            parent_args = ["--previous-packet",previous_packet,"--previous-record",previous_review]
        record_path = review_dir / "review.json"
        save(record_path,record)
        validated = run(f"review-validate-{number}", args + ["--record",record_path] + parent_args)
        if number == 3:
            dropped = copy.deepcopy(record); dropped["issues"] = []
            invalid = review_dir / "attempts/dropped-issue.json"
            save(invalid,dropped)
            run("reject-dropped-issue",args+["--record",invalid]+parent_args, expected=2)
            stale = copy.deepcopy(record)
            stale["issues"][0]["closure_check"]["packet_id"] = record["previous_review"]["packet_id"]
            invalid = review_dir / "attempts/old-closure-stamp.json"
            save(invalid,stale)
            run("reject-old-closure-stamp",args+["--record",invalid]+parent_args, expected=2)
        save(review_dir/"review.md",f"# Synthetic revision review {number}\n\n"
             f"LR-001: {state}. Scientific: {record['readiness']['scientific']}; submission: not_requested.\n\n"
             f"{record['summary']}\n\nNo visual, independent model, expert or full-manuscript validation was performed.\n")
        round_results.append({"round":number,"issue_state":state,"scientific":record["readiness"]["scientific"],
                              "packet_id":manifest["packet_id"],"lineage":validated["lineage"],
                              "write_audit_checks_passed":audit.get("checks_passed")})
        previous_review, previous_packet, previous_write = record_path, packet, write_packet
    assert sha(data) == original_data_hash
    result = {"basis":"Actual local CSV computation, Write auditor and Review CLI; synthetic material, executor-authored judgments.",
              "rounds":round_results,"data_unchanged":True,"events":len(events),
              "not_done":["independent model review","real-project scientific evaluation","visual review","full scientific or submission readiness","Memory/Workflow runtime integration"]}
    save(out/"result.json",result)
    print(json.dumps(result,ensure_ascii=False))


if __name__ == "__main__":
    main()
