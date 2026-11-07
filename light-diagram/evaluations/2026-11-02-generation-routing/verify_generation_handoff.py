"""Synthetic declaration checks using historical files, not new image generation."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("handoff_validator", ROOT / "scripts/validate_handoff.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def main():
    old_dir = ROOT / "evaluations/2026-10-31-integration"
    historical = json.loads((old_dir / "handoff-illustrator.json").read_text("utf-8"))
    for ref in historical["artifacts"].values():
        ref["path"] = str((old_dir / ref["path"]).resolve())
    cases = []

    def check(name, document, expected=True, fragment=None):
        result = validator.validate(document, HERE)
        passed = result["passed"] == expected
        if fragment:
            passed = passed and any(fragment in error for error in result["errors"])
        cases.append({"case": name, "passed": passed, "expected_valid": expected,
                      "observed_valid": result["passed"], "findings": result["errors"]})
        if not passed:
            raise AssertionError(cases[-1])

    fallback = copy.deepcopy(historical)
    fallback.update(output_mode="prompt_only", requested_output_mode="editable", input_kind="concept")
    fallback["artifacts"] = {k: v for k, v in fallback["artifacts"].items() if k in ("prompt", "report")}
    fallback["generation"] = {"status": "not_run", "calls_this_run": 0, "executed_prompt": None,
                              "selection": "prompt_only"}
    fallback["prompt_delivery"] = {"artifact": "prompt", "channel": "file_link", "before_call": True}
    fallback["routing"].update(requested_tool=None, selected_tool=None)
    fallback["reference_review"] = {"status": "not_run", "issues": []}
    for name in ("file", "science"):
        fallback["checks"][name] = {"status": "passed", "scope": "Synthetic prompt-delivery declaration fixture only.",
                                    "evidence": ["prompt", "report"]}
    for name in ("native", "visual"):
        fallback["checks"][name] = {"status": "not_applicable", "scope": "Prompt delivery only.", "evidence": []}
    check("prompt-fallback-retains-original-editable-goal", fallback)
    d = copy.deepcopy(fallback)
    d["generation"]["executed_prompt"] = "prompt"
    check("uncalled-prompt-cannot-be-marked-executed", d, False, "not_run cannot")

    # Only the index declarations are synthetic here; referenced native files
    # remain historical and are never opened or claimed to be newly generated.
    generated = copy.deepcopy(historical)
    generated["generation"] = {"status": "generated", "calls_this_run": 1, "executed_prompt": "prompt",
                               "selection": "builtin"}
    generated["prompt_delivery"] = {"artifact": "prompt", "channel": "inline", "before_call": True}
    check("new-generation-index-with-delivered-prompt", generated)
    d = copy.deepcopy(generated)
    del d["prompt_delivery"]
    check("new-generation-missing-prompt-delivery-rejected", d, False, "requires prompt_delivery")
    d = copy.deepcopy(generated)
    d["prompt_delivery"]["before_call"] = False
    check("post-call-prompt-delivery-rejected", d, False, "before call")
    d = copy.deepcopy(generated)
    d["generation"]["executed_prompt"] = "report"
    check("executed-version-differs-from-delivered-version", d, False, "differs from delivered")
    d = copy.deepcopy(generated)
    d["generation"]["selection"] = "prompt_only"
    check("prompt-only-route-cannot-claim-actual-calls", d, False, "builtin/custom selection")

    with tempfile.TemporaryDirectory() as temporary:
        failure_file = Path(temporary) / "synthetic-failure.json"
        failure_file.write_text(json.dumps({"status": "failed", "calls_this_run": 1,
                                             "scope": "Synthetic failure fixture; no service called."}), encoding="utf-8")
        failed = copy.deepcopy(fallback)
        failed["artifacts"]["failure_record"] = {"path": str(failure_file),
                                                   "sha256": hashlib.sha256(failure_file.read_bytes()).hexdigest()}
        failed["generation"].update(status="failed", calls_this_run=1, executed_prompt="prompt",
                                    selection="custom", failure_record="failure_record")
        check("failed-attempt-can-still-deliver-prompt", failed)
        d = copy.deepcopy(failed)
        d["generation"]["calls_this_run"] = 0
        check("failed-attempt-needs-call-record", d, False, "failed requires actual calls")
        d = copy.deepcopy(failed)
        del d["generation"]["failure_record"]
        check("failed-attempt-needs-failure-evidence", d, False, "requires failure_record")
        d = copy.deepcopy(failed)
        d["output_mode"] = "image"
        check("failed-attempt-cannot-deliver-an-image", d, False, "reference must have generation or reuse")
    result = {"passed": all(c["passed"] for c in cases), "count": len(cases), "cases": cases,
              "scope": "Synthetic handoff declaration checks using historical artifacts; no external image service or native app invoked."}
    (HERE / "handoff-verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
