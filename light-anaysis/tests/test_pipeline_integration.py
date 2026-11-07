"""Optional real light-experiment -> actual analysis -> feedback integration.

Set LIGHT_EXPERIMENT_ROOT (and optionally LIGHT_DESIGN_ROOT) to local source.
All raw synthetic data and processes stay in an isolated temporary workspace.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import importlib.util

from test_analysis import bridge, put, complete_plan, complete_analysis


ANALYZE = '''import json,math,pathlib,sys
raw=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
result={"synthetic_validation":True,"problem":raw["problem"],"independent_problems":1,
        "solutions":len(raw["records"]),"orders":{}}
for method in ["euler","rk4"]:
 values=[r["abs_error"] for r in raw["records"] if r["method"]==method]
 result["orders"][method]=[math.log2(a/b) for a,b in zip(values,values[1:])]
pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf-8")
'''


def integration(root, design_root=None):
    root = Path(root)
    # Load the upstream's actual synthetic numerical validation without copying it.
    sys.path.insert(0, str(root / "tests"))
    spec = importlib.util.spec_from_file_location("upstream_numerics", root / "tests/test_pipeline_integration.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="light-anaysis-pipeline-") as directory:
        base = Path(directory)
        upstream = module.numerical_validation(base / "native", design_root)
        execution = Path(upstream["execution_directory"])
        before = {str(p.relative_to(execution)): bridge.fingerprint(p) for p in execution.rglob("*") if p.is_file()}
        raw1 = execution / "runs/R001/outputs/raw.json"
        raw2 = execution / "runs/R002/outputs/raw.json"
        work = base / "analysis"
        bridge.ingest([execution], [raw1, raw2], work)
        context = bridge.read(work / "context.json")
        e = context["executions"][0]
        if (e["design_id"], e["design_version"], e["selection"]) != ("D01", 3, {"idea_id": "I01", "idea_version": 2}):
            raise AssertionError("Identity lost in actual native handoff")
        complete_plan(work)
        code = work / "code/analyze.py"
        code.parent.mkdir()
        code.write_text(ANALYZE, encoding="utf-8")
        derived = work / "derived/convergence.json"
        derived.parent.mkdir()
        argv = [sys.executable, "-X", "utf8", str(code), str(raw1), str(derived)]
        process = subprocess.run(argv, capture_output=True, encoding="utf-8", timeout=20)
        if process.returncode:
            raise AssertionError(process.stdout + process.stderr)
        calculated = bridge.read(derived)
        for method, low, high in [("euler", .9, 1.2), ("rk4", 3.8, 4.2)]:
            if not all(low <= x <= high for x in calculated["orders"][method]):
                raise AssertionError("Incorrect computed convergence")
        raw_ids = [i["input_id"] for i in context["inputs"] if i["path"] in {str(raw1), str(raw2)}]
        bridge.register_artifact(work, "T01", "derived/convergence.json", raw_ids, ["code/analyze.py"],
                                 json.dumps(argv, ensure_ascii=False), "Actual interpreter: " + sys.version)
        analysis = complete_analysis(work, raw_ids[0])
        f = analysis["findings"][0]
        f.update(claim_refs=["EX01/C01"], run_refs=["EX01/R001", "EX01/R002"],
                 statement="Euler/RK4 expected orders on one analytic ODE; reruns are not independent efficacy samples",
                 validity_basis="Compared exact solution, finite trajectories and expected orders; two repeated outputs byte-identical",
                 evidence=[{"input_id": raw_ids[0], "locator": "JSON $.records[*].abs_error"},
                           {"artifact_id": "T01", "locator": "JSON $.orders"}],
                 estimates=[{"name": "RK4 final refinement order", "value": calculated["orders"]["rk4"][-1],
                             "unit": "order", "n_independent": 1, "n_observations": 6, "interval": None}],
                 limitations=["One manufactured deterministic ODE, not a new scientific result", "Two executions do not double independent N"])
        put(work / "analysis.json", analysis)
        verification = bridge.verify(work)
        if not verification["ok"]:
            raise AssertionError(verification)
        bridge.export_handoff(work)
        handoff = bridge.read(work / "handoff.json")
        after = {str(p.relative_to(execution)): bridge.fingerprint(p) for p in execution.rglob("*") if p.is_file()}
        if before != after:
            raise AssertionError("Analysis changed upstream data")
        if handoff["data_kind"] != "synthetic_validation" or handoff["executions"][0]["campaign_id"] != e["campaign_id"]:
            raise AssertionError("Feedback identity/origin lost")
        # Deliberately mutate selected raw data after successful handoff; verify must reject it.
        raw2.write_text("deliberate integrity regression", encoding="utf-8")
        if bridge.verify(work)["ok"]:
            raise AssertionError("Raw drift was not detected")
        return {"synthetic_validation": True, "upstream_runs": len(upstream["runs"]),
                "native_upstream_integrity_before_deliberate_mutation": upstream["integrity"]["ok"],
                "design_validation": upstream["upstream_validation"]["status"],
                "design_id": e["design_id"], "design_version": e["design_version"], "selection": e["selection"],
                "independent_problems": calculated["independent_problems"], "solutions": calculated["solutions"],
                "computed_orders": calculated["orders"], "analysis_verified": verification["ok"],
                "handoff_route": handoff["decision"]["route"], "upstream_preserved": before == after,
                "raw_drift_rejected": True, "boundary": "Synthetic known-answer integration only; no domain research or independent model behavior evaluation"}


class PipelineTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("LIGHT_EXPERIMENT_ROOT"), "Set LIGHT_EXPERIMENT_ROOT for real local upstream integration")
    def test_actual_upstream_execution_analysis_feedback_and_integrity(self):
        result = integration(os.environ["LIGHT_EXPERIMENT_ROOT"], os.environ.get("LIGHT_DESIGN_ROOT"))
        self.assertTrue(result["analysis_verified"])
        self.assertEqual(result["independent_problems"], 1)
        self.assertTrue(result["upstream_preserved"])
        if os.environ.get("LIGHT_ANALYSIS_VALIDATION_REPORT"):
            put(Path(os.environ["LIGHT_ANALYSIS_VALIDATION_REPORT"]), result)


if __name__ == "__main__":
    unittest.main()
