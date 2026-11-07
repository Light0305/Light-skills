"""Integration checks with labelled synthetic fixtures. Run: python -m unittest discover -s evals -v.

These exercise helpers and generated artifacts; they do not constitute an
independent agent evaluation of skill routing or scientific judgment.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/light-chart"
OUT = Path(os.environ["LIGHT_CHART_TEST_OUTPUT"]) if os.environ.get("LIGHT_CHART_TEST_OUTPUT") else None
sys.path[:0] = [str(SKILL / "scripts"), str(SKILL / "assets")]
os.environ["MPLBACKEND"] = "Agg"
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
import fitz

from profile_data import profile_data
from setup_style import setup_style
from publication import save_figure, write_json
from paper_patterns import trend_lines, annotated_heatmap, comparison_bars
from figure_safety import interp_monotone
import figannot


class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global OUT
        if OUT is None:
            temporary = tempfile.TemporaryDirectory(prefix="light-chart-acceptance-")
            cls.addClassCleanup(temporary.cleanup)
            OUT = Path(temporary.name)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "SYNTHETIC_DATA.txt").write_text(
            "All fixture values are synthetic. Tests validate software behavior, not experimental claims.\n",
            encoding="utf-8")

    def setUp(self):
        plt.rcdefaults()
        setup_style(use_sciplots=False)

    def tearDown(self):
        plt.close("all")

    def save(self, fig, name, **options):
        report = save_figure(fig, str(OUT / name), **options)
        self.assertNotEqual(report["automated_status"], "FAIL", report["failures"])
        self.assertNotEqual(report["automated_status"], "NOT_AUDITABLE", report["unavailable_checks"])
        self.assertEqual(report["visual_review"]["status"], "pending")
        return report

    def test_A01_small_samples_and_identifiers(self):
        data = pd.DataFrame({"sample_id": range(101, 111), "condition": ["Control"]*5+["Treatment"]*5,
                             "value": [1, 2, 3, 2, 4, 4, 5, 6, 5, 7], "empty": [None]*10})
        profile = profile_data(data, ["condition"])
        self.assertEqual(profile["columns"]["sample_id"]["type"], "identifier")
        self.assertEqual(profile["columns"]["value"]["type"], "continuous")
        self.assertEqual(profile["columns"]["empty"]["type"], "unknown")
        self.assertEqual(profile["group_summary"]["min_n_per_group"], 5)
        self.assertIsNone(profile["correlation"])
        data.to_csv(OUT / "A01_input.csv", index=False)
        write_json(OUT / "A01_profile.json", profile)
        fig, ax = plt.subplots(figsize=(5, 3.5), layout="constrained")
        for index, (group, subset) in enumerate(data.groupby("condition", sort=False)):
            ax.scatter(index + np.linspace(-.08, .08, len(subset)), subset.value,
                       color=["#0072B2", "#D55E00"][index], s=25)
        ax.set(xticks=[0,1], xticklabels=["Control", "Treatment"], ylabel="Observed response (a.u.)")
        self.assertEqual(sum(len(c.get_offsets()) for c in ax.collections), len(data))
        self.save(fig, "A01_groups", size_mm=(125, 90))

    def test_A02_incomplete_pairs_require_explicit_exclusion(self):
        data = pd.DataFrame({"subject_id": [1,1,2,2,3,3,4,4,5],
                             "condition": ["Before", "After"]*4+["Before"],
                             "value": [1.1,1.8,1.5,2.0,1.4,1.9,1.8,2.2,1.2]})
        profile = profile_data(data, pair_col="subject_id", condition_col="condition")
        self.assertEqual(profile["pair_summary"]["incomplete_ids"], ["5"])
        self.assertEqual(profile["pair_summary"]["rows_excluded"], 0)
        path = OUT / "A02_input.csv"
        data.to_csv(path, index=False)
        command = [sys.executable, str(SKILL / "scripts/plot_templates.py"), "paired", "--input", str(path),
                   "--id-col", "subject_id", "--condition-col", "condition", "--value-col", "value",
                   "--condition-order", "Before,After", "--width-mm", "120", "--height-mm", "85",
                   "--output", str(OUT / "A02_paired")]
        rejected = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("incomplete", rejected.stderr.lower())
        accepted = subprocess.run(command + ["--drop-incomplete"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        qa = json.loads((OUT / "A02_paired.qa.json").read_text(encoding="utf-8"))
        self.assertEqual(qa["data"]["rows_plotted"], 8)
        self.assertEqual(qa["data"]["excluded_rows"], 1)
        self.assertEqual(qa["data"]["excluded_entities"], 1)
        self.assertEqual(qa["data"]["rows_input"], 9)
        from source_binding import verify_sources
        self.assertEqual(verify_sources(qa), [])
        self.assertEqual(Path(qa["source_manifest"]["input"]["path"]), path)
        self.assertIn("A02_paired.svg", qa["review_artifacts"])
        self.assertIn("A02_paired.tiff", qa["review_artifacts"])

    def test_A03_nonuniform_coordinates_and_intervals(self):
        x = np.array([0,1,4,10])
        values = np.array([[1.2,1.5,1.9,2.0],[1.1,1.7,2.5,2.8]])
        lower, upper = values-.15, values+.15
        fig, ax = trend_lines(x, values, ["Baseline", "Treatment"], lower, upper)
        ax.set(xlabel="Time (h)", ylabel="Response (a.u.)")
        ax.legend(frameon=False, loc="upper left")
        np.testing.assert_array_equal(ax.lines[0].get_xdata(), x)
        np.testing.assert_array_equal(ax.lines[1].get_ydata(), values[1])
        np.testing.assert_allclose(interp_monotone([.5,1.5],[2,1,0],[20,10,0]), [5,15])
        with self.assertRaises(ValueError):
            interp_monotone([1],[0,1,1],[2,3,4])
        self.save(fig, "A03_trends", size_mm=(150, 100))
        pd.DataFrame({"time_h":x,"baseline":values[0],"treatment":values[1],
                      "baseline_lower":lower[0],"baseline_upper":upper[0],
                      "treatment_lower":lower[1],"treatment_upper":upper[1]}).to_csv(OUT/"A03_input.csv",index=False)

    def test_A04_heatmap_missing_values_and_labels(self):
        values = np.array([[1,3,4],[2,np.nan,5],[3,4,8],[2,5,7]],float)
        rows, columns = ["Group A", "Group B", "Group C", "Group D"], ["Early", "Middle", "Late"]
        original_rows, original_columns = list(rows), list(columns)
        fig, ax = annotated_heatmap(values,rows,columns,label="Count")
        self.assertEqual(rows,original_rows)
        self.assertEqual(columns,original_columns)
        self.assertEqual(int(np.ma.getmaskarray(ax.images[0].get_array()).sum()),1)
        self.assertEqual(len(ax.texts),values.size)
        self.save(fig,"A04_heatmap",size_mm=(150,100),axes=[ax])

    def test_A05_grid_and_spanning_panels_in_both_languages(self):
        for spanning in (False,True):
            fig=plt.figure(figsize=(7.1,4.9),layout="constrained")
            axes=fig.subplot_mosaic([["a","c"],["b","c"]] if spanning else [["a","b"],["c","d"]])
            for index,ax in enumerate(axes.values()):
                x=np.array([0,1,4,10])
                ax.plot(x, np.array([1,2,2.4,3])+index*.3, marker="o",color=["#0072B2","#D55E00","#009E73","#CC79A7"][index])
                ax.set(xlabel="Time (h)",ylabel="Response (a.u.)")
            report=self.save(fig,"A05_spanning" if spanning else "A05_grid",size_mm=(180,130),
                             axes=list(axes.values()),label_panels=True)
            self.assertEqual(report["alignment"]["verdict"],"PASS")
        rscript=shutil.which("Rscript")
        self.assertIsNotNone(rscript,"R route is required by this acceptance run")
        from r_runtime import child_environment
        env,_=child_environment()
        env['PYTHONUTF8']='1'
        result=subprocess.run([rscript,"--vanilla",str(ROOT/"evals/acceptance_r.R"),
                               str(SKILL/"scripts/publication.R"),str(OUT/"r")],
                              env=env,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=120)
        (OUT/"r_execution.log").write_text(result.stdout+"\n"+result.stderr,encoding="utf-8")
        self.assertIn("R_ACCEPTANCE_COMPLETE",result.stdout)
        baseline = subprocess.run([rscript,"--vanilla","-e",'library(ggplot2);cat("BASELINE_COMPLETE\\n")'],
                                  env=env,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30)
        self.assertIn("BASELINE_COMPLETE",baseline.stdout)
        runtime = {"render_exit_code":result.returncode,"package_load_only_exit_code":baseline.returncode,
                   "completion_marker_seen":True,"status":"normal" if result.returncode == 0 else "shutdown_error_reproduced_without_chart_code"}
        write_json(OUT/"r_runtime.json",runtime)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(baseline.returncode,0,baseline.stderr)
        for name in ["A01_groups","A02_paired","A05_grid","A05_spanning","A08_chinese"]:
            report=json.loads((OUT/"r"/(name+".qa.json")).read_text(encoding="utf-8"))
            self.assertNotIn(report["automated_status"],["FAIL","NOT_AUDITABLE"],report)
        with fitz.open(OUT/"r/A08_chinese.pdf") as pdf:
            self.assertIn("时间",pdf[0].get_text(),"R source encoding must preserve Chinese text")

    def test_comparison_pattern_and_template_exports(self):
        fig, axes = comparison_bars(["Baseline","Method A","Method B"],["Metric 1","Metric 2"],
                                    [[.5,.6],[.7,.75],[.8,.9]],errors=[[.03,.02],[.02,.04],[.03,.02]])
        self.assertEqual(len(axes),2)
        self.assertEqual(sum(len(ax.patches) for ax in axes),6)
        self.save(fig,"comparison_bars",size_mm=(180,85),axes=axes,label_panels=True)
        directory=OUT/"templates"
        directory.mkdir(exist_ok=True)
        for kind in ["volcano","roc","dotplot","marginal"]:
            result=subprocess.run([sys.executable,str(SKILL/"scripts/plot_templates.py"),kind,"--demo",
                                   "--width-mm","145","--height-mm","110","--output",str(directory/kind)],
                                  capture_output=True,text=True,encoding="utf-8",timeout=60)
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads((directory/(kind+".qa.json")).read_text(encoding="utf-8"))
            self.assertNotIn(report["automated_status"],["FAIL","NOT_AUDITABLE"],report)
            self.assertEqual(report["data"]["excluded_rows"],0)
            self.assertGreater(report["data"]["rows_plotted"],0)

    def test_final_pdf_rejects_real_text_overlap(self):
        from audit_figure_collisions import audit_pdf
        fig, ax=plt.subplots(figsize=(4,3))
        ax.text(.4,.5,"Overlapping words",fontsize=12)
        ax.text(.4,.5,"Conflicting words",fontsize=12)
        path=OUT/"negative_overlap.pdf"
        fig.savefig(path)
        report=audit_pdf(path)
        self.assertTrue(any(item["kind"] == "text-text" and item["severity"] == "FAIL" for item in report["findings"]))
        write_json(OUT/"negative_overlap.qa.json",report)

    def test_A06_reference_style_new_data_and_review_ledger(self):
        work=OUT/"reference"
        work.mkdir(exist_ok=True)
        reference=ROOT/"Reference  Repositories/figures4papers-main/figure_VIGIL/figures/comparison_posttraining.png"
        fig,ax=trend_lines([0,2,5,10],[[22,30,34,36],[22,35,42,44],[22,41,54,60]],
                           ["Baseline","Alternative","Treatment"],colors=["#D88F8A","#8BCF8B","#0F4D92"],size_mm=(130,115))
        ax.set(xlabel="Training budget (h)",ylabel="Validation performance (%)")
        ax.legend(loc="lower right",ncols=2,frameon=False,fontsize=7)
        ax.axhline(22,color="black",alpha=.25,linestyle="--",linewidth=.7)
        self.save(fig,"A06_reference_adapted",size_mm=(130,115))
        shutil.copy2(OUT/"A06_reference_adapted.png",work/"img_iter0.png")
        with contextlib.redirect_stdout(io.StringIO()):
            figannot.cmd_compose(argparse.Namespace(ref=str(reference),draft=str(work/"img_iter0.png"),
                                 out_dir=str(work/"audit_view_0"),height=650,gutter=24,reviewer_md=""))
        self.assertTrue((work/"audit_view_0/composite.png").is_file())
        # This is a protocol fixture, not the evaluator's visual verdict.
        review={"iter":0,"reference_inventory":{"chart_type":"line chart","signature_element":"three colored curves", "motifs":["thin axes","compact legend"]},
                "anchor":{"what_is_right":["[L1] Three series remain visible."],"measurements":{}},
                "quality_floor":{"passed":True,"violation_kinds":[],"summary":None},
                "fidelity":{"verdict":"ship","paragraph":"Protocol fixture for state validation only."},
                "focus_themes":[],"boxes":[]}
        write_json(work/"protocol_fixture_review.json",review)
        args=argparse.Namespace(workdir=str(work),review=str(work/"protocol_fixture_review.json"),
                                draft=str(work/"img_iter0.png"),iter="0",min_reviews=1,max_iters=2,
                                strict_3d=False,reviewer_session="protocol-fixture-0")
        # Remove only our prior test ledger files to make this case repeatable.
        for path in (work/"review_attempts").glob("attempt_*.json") if (work/"review_attempts").exists() else []:
            path.unlink()
        with contextlib.redirect_stdout(io.StringIO()) as capture:
            figannot.cmd_review_decision(args)
        first=json.loads(capture.getvalue())
        self.assertEqual(first["action"],"ship")
        with contextlib.redirect_stdout(io.StringIO()) as capture:
            figannot.cmd_review_decision(args)
        self.assertTrue(json.loads(capture.getvalue())["replayed"])
        self.assertEqual(len(list((work/"review_attempts").glob("attempt_*.json"))),1)
        args.iter="2"
        with self.assertRaises(ValueError):
            figannot.cmd_review_decision(args)

    def test_A07_incompatible_reference_preserves_observations(self):
        categories=["Assay A","Assay B","Assay C"]
        values=[[2,3,2.5,3.2,2.7],[4.1,3.9,4.4,4.0,4.5],[1.1,1.4,1.5,1.7,1.3]]
        fig,ax=plt.subplots(figsize=(5,3.5),layout="constrained")
        for index,group in enumerate(values):
            ax.scatter(index+np.linspace(-.08,.08,5),group,color=["#D88F8A","#8BCF8B","#0F4D92"][index],s=25)
        ax.set(xticks=range(3),xticklabels=categories,ylabel="Observed response (a.u.)")
        self.assertEqual(len(ax.lines),0,"unordered assays must not acquire a fabricated trajectory")
        self.assertEqual(sum(len(c.get_offsets()) for c in ax.collections),15)
        self.save(fig,"A07_style_only",size_mm=(130,90))
        write_json(OUT/"A07_adaptation.json",{"mode":"style_only","reason":"unordered assay groups do not supply a continuous x coordinate",
                                                "rows_input":15,"rows_plotted":15,"excluded_rows":0})

    def test_A08_cjk_symbols_exact_size_and_non_destructive_grayscale(self):
        setup_style(lang="zh",use_sciplots=False)
        for width,height in [(125,90),(180,115)]:
            fig,ax=plt.subplots(figsize=(width/25.4,height/25.4),layout="constrained")
            ax.plot([0,1,4,10],[-.5,.1,.8,1.2],marker="o",color="#0072B2",label="处理组")
            ax.set(xlabel="时间（小时）",ylabel="响应强度 Δ（任意单位）",title="合成数据：中文与长标签验证")
            ax.legend(frameon=False,loc="upper left")
            name=f"A08_chinese_{width}"
            self.save(fig,name,size_mm=(width,height))
            with Image.open(OUT/(name+".png")) as color, Image.open(OUT/(name+"_grayscale.png")) as gray:
                self.assertEqual(color.size,gray.size)
                self.assertEqual(gray.mode,"L")
                self.assertLessEqual(abs(color.width-width/25.4*300),1)
                rgb=np.asarray(color.convert("RGB"))
                self.assertTrue(np.any(rgb[:,:,0] != rgb[:,:,2]),"color PNG was overwritten")
            with fitz.open(OUT/(name+".pdf")) as pdf:
                self.assertAlmostEqual(pdf[0].rect.width,width/25.4*72,places=3)
                self.assertIn("时间",pdf[0].get_text())
            self.assertIn("<text",(OUT/(name+".svg")).read_text(encoding="utf-8"))

    def test_windows_lock_serializes_competing_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            script=("import sys,time;from pathlib import Path;sys.path.insert(0,sys.argv[1]);"
                    "from figannot import _review_transaction_lock;"
                    "p=Path(sys.argv[2]);\n"
                    "with _review_transaction_lock(p):\n"
                    " p.joinpath(sys.argv[3]+'.start').write_text(str(time.time()));time.sleep(.5);"
                    "p.joinpath(sys.argv[3]+'.end').write_text(str(time.time()))\n")
            one=subprocess.Popen([sys.executable,"-c",script,str(SKILL/"scripts"),directory,"one"])
            two=subprocess.Popen([sys.executable,"-c",script,str(SKILL/"scripts"),directory,"two"])
            self.assertEqual(one.wait(timeout=30),0)
            self.assertEqual(two.wait(timeout=30),0)
            directory=Path(directory)
            spans=sorted((float((directory/(name+".start")).read_text()),float((directory/(name+".end")).read_text())) for name in ["one","two"])
            self.assertLessEqual(spans[0][1],spans[1][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
