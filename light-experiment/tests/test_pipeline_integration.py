"""Executable synthetic numerical study, optionally checked by real light-design.

Set LIGHT_DESIGN_ROOT to a local light-design checkout to check its handoff validator.
No dependency on that checkout is needed for ordinary runtime or numerical testing.
"""
import copy
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_experiment import make_design, tool, write


SOLVER = '''import json, math, os, pathlib, sys
config = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
out = pathlib.Path(os.environ["LIGHT_EXPERIMENT_OUT"])
records = []
for method in config["methods"]:
    for n in config["steps"]:
        dt = 1.0 / n
        y = 1.0
        trajectory = [y]
        for i in range(n):
            if method == "euler":
                y = y - dt*y
            elif method == "rk4":
                k1 = -y
                k2 = -(y+dt*k1/2)
                k3 = -(y+dt*k2/2)
                k4 = -(y+dt*k3)
                y += dt*(k1+2*k2+2*k3+k4)/6
            else:
                raise ValueError("unknown method")
            trajectory.append(y)
        records.append({"method":method, "steps":n, "dt":dt, "solution":y,
                        "exact":math.exp(-1.0), "abs_error":abs(y-math.exp(-1.0)),
                        "trajectory":trajectory})
(out/"raw.json").write_text(json.dumps({"synthetic":True,"problem":"dy/dt=-y, y(0)=1",
    "records":records},indent=2,allow_nan=False),encoding="utf-8")
print("Completed deterministic analytic ODE validation; not a research discovery.")
'''


def numerical_validation(base, upstream_root=None):
    base = Path(base)
    source, design, execution = base / "source", base / "design", base / "execution"
    source.mkdir(parents=True)
    solver, config, environment = source / "solver.py", source / "config.json", source / "environment.txt"
    solver.write_text(SOLVER, encoding="utf-8")
    write(config, {"methods": ["euler", "rk4"], "steps": [20, 40, 80]})
    environment.write_text("Synthetic validation runtime: " + sys.version + "\n" + sys.executable,
                           encoding="utf-8")
    plan = make_design(design)
    plan["objective"] = "Validate actual execution and evidence retention on a known analytical ODE"
    plan["claims"][0].update(statement="Euler and RK4 show expected convergence on this exact ODE",
                              prediction="Approximate orders one and four over 20,40,80 steps",
                              rival="Broken implementation does not match known convergence",
                              scope="One manufactured deterministic test problem; no new scientific finding")
    experiment = plan["experiments"][0]
    experiment.update(name="Analytic ODE convergence", purpose="Validate a computational execution pipeline",
                      design="Deterministic grid-refinement comparison on dy/dt=-y",
                      conditions=["Euler", "RK4"],
                      units={"allocation": "No random allocation", "independent": "One manufactured ODE",
                             "observation": "Six method/resolution trajectories; not six independent samples"},
                      allocation="Pre-specified method and resolution matrix",
                      procedure="Execute source/solver.py with frozen config.json and preserve complete trajectories",
                      measurement={"primary": "Absolute terminal error and empirical convergence order",
                                   "operationalization": "Error to exp(-1); order log2(e(h)/e(h/2))",
                                   "timepoint": "At t=1 and end of deterministic run",
                                   "qc": "Finite trajectories of n+1 values; Euler order 0.9-1.2, RK4 order 3.8-4.2"},
                      sample_size={"n": 1, "n_definition": "One manufactured problem, not an independent sample study",
                                   "method": "Known analytical validation", "basis": "Exact solution exp(-t)",
                                   "status": "justified"},
                      analysis="Compute error and refinement order; no statistical efficacy inference",
                      decisions={"support": "Expected orders and preserved evidence validate this small pipeline",
                                 "falsify": "Incorrect errors/order reject this implementation on the test",
                                 "inconclusive": "Missing data or execution failure needs repair",
                                 "stop": "Two short CPU attempts at most"})
    plan["tasks"][0].update(inputs=[str(config)], action="Execute the local deterministic solver",
                             outputs=["raw.json with six complete trajectories"],
                             acceptance="Finite solutions and expected convergence; repeatable raw bytes")
    plan["resources"][0].update(locator=str(solver), specification="Local pure-Python Euler/RK4 implementation",
                                basis="File generated in this isolated validation directory")
    write(design / "design.json", plan)
    (design / "plan.md").write_text(
        "Synthetic pipeline validation only. Integrate y'=-y from y(0)=1 to t=1.\n"
        "Euler/RK4 at 20/40/80 steps; preserve trajectories and compare to exp(-1).\n"
        "Expected orders: Euler 0.9-1.2; RK4 3.8-4.2. Run twice without changes.\n"
        "These resolution points and reruns are not independent study replicates.\n", encoding="utf-8")
    (design / "protocols/check.txt").write_text("Exact solution exp(-t); fixed convergence QC before results",
                                                encoding="utf-8")
    upstream_check = {"status": "not_requested"}
    if upstream_root is not None:
        bridge = Path(upstream_root) / "scripts/design_bridge.py"
        if not bridge.is_file():
            raise ValueError("Provided light-design validator was not found")
        process = subprocess.run([sys.executable, "-X", "utf8", str(bridge), "verify", "--workspace", str(design)],
                                 capture_output=True, encoding="utf-8", timeout=20)
        if process.returncode != 0:
            raise AssertionError("Real upstream validator rejected handoff: " + process.stdout + process.stderr)
        upstream_check = {"status": "passed", "validator": str(bridge), "result": json.loads(process.stdout)}
    source_hash = tool.digest(design / "design.json")
    tool.init(design, execution, 2, 20, "Two deterministic local validation processes; no external services")
    spec = {"schema_version": "1.0", "run_id": "R001", "experiment_id": "X01", "task_id": "T01",
            "kind": "pilot", "purpose": "Execute frozen known-answer ODE convergence check",
            "parent_run_id": None, "unit": {"unit_id": "ODE1", "reexecution": 1},
            "parameters": tool.read(config), "argv": [sys.executable, str(solver), str(config)],
            "cwd": str(source), "timeout_seconds": 10, "environment": {},
            "provenance": {"environment": str(environment), "hardware": "Local CPU, no accelerators requested",
                           "determinism": "Deterministic serial double-precision arithmetic; no RNG"},
            "inputs": [{"path": str(path), "role": role, "snapshot": True}
                       for path, role in [(solver, "code"), (config, "config"), (environment, "environment")]],
            "expected_outputs": [{"path": "raw.json", "role": "raw", "required": True, "min_bytes": 1}]}
    errors, orders, signatures, results = {}, {}, [], []
    for index, run_id in enumerate(("R001", "R002"), 1):
        run_spec = copy.deepcopy(spec)
        run_spec.update(run_id=run_id, parent_run_id="R001" if index == 2 else None)
        run_spec["unit"]["reexecution"] = index
        spec_path = base / (run_id + ".json"); write(spec_path, run_spec)
        tool.prepare(execution, spec_path)
        result = tool.run(execution, run_id)
        if not result["ok"]:
            raise AssertionError(result)
        raw_path = execution / "runs" / run_id / "outputs/raw.json"
        raw = tool.read(raw_path)
        if len(raw["records"]) != 6:
            raise AssertionError("The complete method/resolution matrix was not produced")
        for row in raw["records"]:
            if len(row["trajectory"]) != row["steps"] + 1 or not all(math.isfinite(v) for v in row["trajectory"]):
                raise AssertionError("Invalid raw trajectory")
        for method, low, high in [("euler", 0.9, 1.2), ("rk4", 3.8, 4.2)]:
            values = [row["abs_error"] for row in raw["records"] if row["method"] == method]
            measured = [math.log2(a / b) for a, b in zip(values, values[1:])]
            if not all(low <= value <= high for value in measured):
                raise AssertionError(f"Incorrect {method} convergence: {measured}")
            errors[method], orders[method] = values, measured
        assessment = {"schema_version": "1.0", "run_id": run_id, "assessor": "Executable known-answer validation",
                      "qc_status": "passed", "qc_basis": "Six finite trajectories with specified convergence orders",
                      "outcome": "support", "claim_ids": ["C01"],
                      "metrics": [{"name": "rk4_terminal_error_80", "value": errors["rk4"][-1],
                                   "unit": "dimensionless", "artifact": "outputs/raw.json",
                                   "locator": "JSON $.records[5].abs_error"}],
                      "deviations": [], "limitations": ["One synthetic deterministic analytic problem only"],
                      "next_action": "Stop this validation; no efficacy or real-HPC inference"}
        assessment_path = base / (run_id + "-assessment.json"); write(assessment_path, assessment)
        tool.assess(execution, run_id, assessment_path)
        signatures.append(tool.digest(raw_path)["sha256"])
        results.append({k: result[k] for k in ("run_id", "process_status", "returncode", "wall_seconds", "artifacts_ok")})
    integrity = tool.verify(execution)
    if not integrity["ok"] or signatures[0] != signatures[1] or tool.digest(design / "design.json") != source_hash:
        raise AssertionError("Repeatability, integrity or upstream preservation failed")
    return {"synthetic": True, "execution_directory": str(execution), "upstream_validation": upstream_check,
            "problem": "dy/dt=-y, y(0)=1; exact y(1)=exp(-1)", "steps": [20, 40, 80],
            "errors": errors, "orders": orders, "raw_sha256": signatures,
            "reexecutions_byte_identical": True, "runs": results, "integrity": integrity}


class PipelineIntegrationTests(unittest.TestCase):
    def test_actual_numerical_convergence_and_repeatability(self):
        with tempfile.TemporaryDirectory(prefix="light-experiment-numerics-") as directory:
            result = numerical_validation(directory, os.environ.get("LIGHT_DESIGN_ROOT"))
            self.assertTrue(result["reexecutions_byte_identical"])
            self.assertEqual(result["integrity"]["counts"]["attempted"], 2)
            self.assertTrue(result["integrity"]["ok"])


if __name__ == "__main__":
    unittest.main()
