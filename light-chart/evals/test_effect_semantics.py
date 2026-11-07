"""Targeted scientific invariants for study 2x2 evidence, no image snapshots."""
import sys
from pathlib import Path
import unittest
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"skills/light-chart/scripts"))
from effect_plots import analyze_2x2, align_studies, wilson_interval, validate_effects, forest_panel, arm_risk_panel


class EffectSemantics(unittest.TestCase):
    def setUp(self):
        self.raw = pd.DataFrame({"study_id":["small", "large"], "label":["Long label β", "Second"],
            "tpos":[10, 40], "tneg":[90, 160], "cpos":[20, 20], "cneg":[80, 180]})

    def tearDown(self):
        plt.close("all")

    def test_risk_ratio_uses_all_participants_not_events_or_odds(self):
        a = analyze_2x2(self.raw)
        np.testing.assert_allclose(a.rr, [.5, 2.])
        np.testing.assert_array_equal(a.n_numerator, [100,200])
        np.testing.assert_array_equal(a.n_comparator, [100,200])
        self.assertAlmostEqual(a.loc[0,"variance_log_rr"], .1-.01+.05-.01)
        np.testing.assert_allclose(a.rr_low*a.rr_high, a.rr**2)
        self.assertAlmostEqual(a.loc[0,"rr_low"], .24664080168294558, places=12)

    def test_joint_shuffle_preserves_identity_labels_denominators_and_intervals(self):
        a = analyze_2x2(self.raw)
        b = analyze_2x2(self.raw.iloc[::-1].reset_index(drop=True))
        pd.testing.assert_frame_equal(a, align_studies(b, ["small","large"]))
        fig, (ax, bx) = plt.subplots(1,2)
        forest = forest_panel(ax,b,effect_scale="ratio",reference=1,order=["small","large"])
        risks = arm_risk_panel(bx,b,risk_scale="linear",order=["small","large"])
        pd.testing.assert_frame_equal(forest,risks)
        self.assertEqual(forest.label.tolist(), ["Long label β","Second"])

    def test_identity_and_order_are_complete_not_positional(self):
        for order in [["small"], ["small","small"], ["small","unknown"]]:
            with self.assertRaises(ValueError): align_studies(self.raw, order)
        for key,value in [("study_id",["a","a"]),("study_id",["", "b"]),("label",[None,"b"])]:
            bad=self.raw.copy();bad[key]=value
            with self.assertRaises(ValueError): analyze_2x2(bad)

    def test_invalid_counts_never_drop_studies_or_correct_counts(self):
        for val in [-1, 1.5, np.nan, np.inf, True, "bad"]:
            bad=self.raw.astype(object).copy();bad.loc[0,"tpos"]=val
            with self.assertRaises(ValueError): analyze_2x2(bad)
        bad=self.raw.copy();bad.loc[0,["tpos","tneg"]]=0
        with self.assertRaises(ValueError): analyze_2x2(bad)

    def test_complex_counts_are_rejected_before_any_lossy_cast(self):
        for column in ["tpos", "tneg", "cpos", "cneg"]:
            for dtype in [complex, object]:
                for value in [1+2j, np.complex128(1+0j)]:
                    with self.subTest(column=column, dtype=dtype, value=value):
                        bad = self.raw.copy()
                        bad[column] = pd.Series([value, self.raw.loc[1, column]], dtype=dtype)
                        with warnings.catch_warnings():
                            warnings.simplefilter("error")
                            with self.assertRaisesRegex(ValueError, "real numeric"):
                                analyze_2x2(bad)

    def test_wilson_rejects_complex_boolean_and_nonfinite_inputs(self):
        for value in [1+2j, np.complex128(1+0j), True, np.bool_(False), np.inf, np.nan]:
            for field in ["events", "total", "confidence"]:
                with self.subTest(field=field, value=value), warnings.catch_warnings():
                    warnings.simplefilter("error")
                    args = dict(events=[1, 2], total=[10, 10], confidence=.95)
                    args[field] = value if field == "confidence" else np.array([value, 2], dtype=object)
                    with self.assertRaises(ValueError):
                        wilson_interval(**args)

    def test_display_values_reject_complex_and_boolean_without_hiding_rows(self):
        analyzed = analyze_2x2(self.raw)
        ax = plt.subplots()[1]
        for field in ["rr", "rr_low", "rr_high", "risk_numerator", "risk_numerator_low",
                      "risk_numerator_high", "risk_comparator", "risk_comparator_low", "risk_comparator_high"]:
            for value in [1+2j, np.complex128(.5+0j), True, np.bool_(False)]:
                with self.subTest(field=field, value=value), warnings.catch_warnings():
                    warnings.simplefilter("error")
                    bad = analyzed.astype(object)
                    bad.loc[0, field] = value
                    with self.assertRaisesRegex(ValueError, "real numeric"):
                        if field.startswith("rr"):
                            validate_effects(bad, effect_scale="ratio", reference=1)
                        else:
                            arm_risk_panel(ax, bad, risk_scale="linear")
        for value in [1+2j, True, np.inf, np.nan]:
            with self.subTest(reference=value), self.assertRaises(ValueError):
                validate_effects(analyzed, effect_scale="ratio", reference=value)
        for limits in [[0, 100+2j], [False, 100], [0, np.inf]]:
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                arm_risk_panel(ax, analyzed, risk_scale="linear", limits=limits)
        for limits in [[.1, 10+2j], [False, 10], [.1, np.inf]]:
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                forest_panel(ax, analyzed, effect_scale="ratio", reference=1, limits=limits)

    def test_real_inputs_and_explicit_field_mapping_keep_exact_results(self):
        expected = analyze_2x2(self.raw)
        mapped = self.raw.rename(columns={"study_id":"sid", "label":"caption", "tpos":"a",
            "tneg":"b", "cpos":"c", "cneg":"d"})
        actual = analyze_2x2(mapped, id_col="sid", label_col="caption", counts=("a", "b", "c", "d"))
        actual = actual.rename(columns={"sid":"study_id", "caption":"label", "a":"tpos",
            "b":"tneg", "c":"cpos", "d":"cneg"})
        pd.testing.assert_frame_equal(actual, expected)
        for dtype in [float, object]:
            with self.subTest(dtype=dtype):
                actual = analyze_2x2(self.raw.astype({name:dtype for name in ["tpos", "tneg", "cpos", "cneg"]}))
                pd.testing.assert_frame_equal(actual[expected.columns[6:]], expected[expected.columns[6:]])
        expected_bounds = wilson_interval([1, 2], [10, 10])
        actual_bounds = wilson_interval(np.array([1., 2.], dtype=object), 10.)
        np.testing.assert_array_equal(actual_bounds, expected_bounds)

    def test_derived_output_names_never_overwrite_source_id_counts_or_metadata(self):
        cases = [
            (self.raw.rename(columns={'study_id':'rr'}), {'id_col':'rr'}),
            (self.raw.rename(columns={'study_id':'risk_numerator'}), {'id_col':'risk_numerator'}),
            (self.raw.rename(columns={'label':'rr_status'}), {'label_col':'rr_status'}),
            (self.raw.rename(columns={'tpos':'n_numerator'}),
             {'counts':('n_numerator','tneg','cpos','cneg')}),
            (self.raw.assign(risk_comparator_low=['original-a','original-b']), {}),
            (self.raw.assign(variance_log_rr=[17,19]), {}),
        ]
        for source, kwargs in cases:
            with self.subTest(columns=source.columns.tolist()), warnings.catch_warnings():
                warnings.simplefilter('error')
                before = source.copy(deep=True)
                with self.assertRaisesRegex(ValueError, 'collide with derived output names'):
                    analyze_2x2(source, **kwargs)
                pd.testing.assert_frame_equal(source, before)

    def test_duplicate_source_columns_rejected_before_ambiguous_identity_or_counts(self):
        for field in ['study_id','tpos','label']:
            duplicate = pd.concat([self.raw,self.raw[[field]]],axis=1)
            with self.subTest(field=field), warnings.catch_warnings():
                warnings.simplefilter('error')
                with self.assertRaisesRegex(ValueError, 'Unique input column names'):
                    analyze_2x2(duplicate)

    def test_noncolliding_extra_source_fields_remain_jointly_aligned(self):
        source = self.raw.assign(author_note=['original-a','original-b'], _rank=[71,42])
        actual = analyze_2x2(source.iloc[::-1])
        ordered = align_studies(actual,['small','large'])
        pd.testing.assert_frame_equal(ordered[source.columns], source)

    def test_preparation_blocks_derived_namespace_collisions_without_changing_ids(self):
        from figure_job import prepare_job
        spec = dict(intent='two_arm_risk_evidence',unit='risk_numerator',label='label',
            numerator_events='tpos',numerator_non_events='tneg',
            comparator_events='cpos',comparator_non_events='cneg',
            independent_binomial_working_model_explicit=True,confidence=.95,
            effect='RR',effect_scale='ratio',reference=1,risk_scale='linear',
            zero_event_policy='unavailable_no_correction')
        source = self.raw.rename(columns={'study_id':'risk_numerator'})
        before = source.copy(deep=True)
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            result = prepare_job({'studies':source},dict(question='Compare recorded study risks',
                source='studies',backend='python',chart=spec))
        self.assertEqual(result['status'],'needs_resolution')
        self.assertTrue(any('collide with derived output names' in b for b in result['blockers']))
        pd.testing.assert_frame_equal(source,before)

    def test_zero_events_retained_explicitly_and_log_risk_rejected(self):
        raw=self.raw.copy();raw.loc[0,"tpos"]=0
        a=analyze_2x2(raw)
        self.assertEqual(len(a),2)
        self.assertEqual(a.loc[0,"rr_status"],"unavailable_zero_events")
        self.assertTrue(np.isnan(a.loc[0,"rr"]))
        self.assertEqual(a.loc[0,"n_numerator"],90)
        self.assertEqual(a.loc[0,"risk_numerator_low"],0)
        ax=plt.subplots()[1]
        arm_risk_panel(ax,a,risk_scale="linear")
        with self.assertRaises(ValueError): arm_risk_panel(ax,a,risk_scale="log")
        forest_panel(ax,a,effect_scale="ratio",reference=1)

    def test_non_event_zero_is_supported_without_continuity_correction(self):
        raw=self.raw.copy();raw.loc[0,"tneg"]=0
        a=analyze_2x2(raw)
        self.assertAlmostEqual(a.loc[0,"rr"],5)
        self.assertEqual(a.loc[0,"n_numerator"],10)
        self.assertEqual(a.loc[0,"risk_numerator_high"],1)

    def test_wilson_bounds_invert_binomial_score_and_handle_boundaries(self):
        x,n = np.array([0,1,13,100]), np.array([100,100,100,100])
        lo,hi=wilson_interval(x,n)
        z=1.959963984540054
        for i in range(4):
            for p in [lo[i],hi[i]]:
                if 0 < p < 1:
                    self.assertAlmostEqual(abs((x[i]/n[i]-p)/np.sqrt(p*(1-p)/n[i])),z,places=9)
        self.assertEqual(lo[0],0);self.assertEqual(hi[-1],1)

    def test_declared_scale_reference_intervals_and_limits_are_scientific_contracts(self):
        a=analyze_2x2(self.raw)
        for scale,ref in [("ratio",0),("log_ratio",1),("linear",1)]:
            with self.assertRaises(ValueError): validate_effects(a,effect_scale=scale,reference=ref)
        for col,val in [("rr_low",.75),("rr_high",.1),("rr_low",np.nan),("rr_low",0)]:
            bad=a.copy();bad.loc[0,col]=val
            with self.assertRaises(ValueError): validate_effects(bad,effect_scale="ratio",reference=1)
        ax=plt.subplots()[1]
        with self.assertRaises(ValueError): forest_panel(ax,a,effect_scale="ratio",reference=1,limits=[.4,2.1])
        with self.assertRaises(ValueError): arm_risk_panel(ax,a,risk_scale="linear",limits=[0,10])
        logged=a.copy();logged[["rr","rr_low","rr_high"]]=np.log(a[["rr","rr_low","rr_high"]])
        forest_panel(ax,logged,effect_scale="log_ratio",reference=0)


if __name__ == "__main__": unittest.main()
