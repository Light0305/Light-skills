"""Real failure modes: denominators, stale ancestry, false validation and routing."""
import sys
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/light-chart/scripts'))
from study_data import combine_cohorts,binomial_estimates,missingness_summary,lineage,save_study_table,grouped_lineage
from chart_plan import plan_chart,read_data
from evidence_tools import plan_evidence
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from review_tools import figure_snapshot,compare_revisions
from color_tools import audit_rendered_mapping,contrast_text,palette_project


class StudyTests(unittest.TestCase):
    def source(self):
        return pd.DataFrame({'id':range(5),'event':[1,0,1,np.nan,0],'kind':['a','a','b','b','b']})

    def summary(self,d=None,**kwargs):
        return binomial_estimates(self.source() if d is None else d,event='event',unit='id',groups=['kind'],
            levels={'kind':['a','b','empty']},interval='wilson',**kwargs)

    def test_missing_outcomes_do_not_become_negative(self):
        with self.assertRaisesRegex(ValueError,'missing'): self.summary()
        a,r=self.summary(missing='exclude')
        self.assertEqual(a.denominator.tolist(),[2,2,0]);self.assertEqual(a.numerator.tolist(),[1,1,0])
        self.assertEqual(r['excluded_positions'],[3]);self.assertTrue(np.isnan(a.estimate.iloc[2]))
        self.assertEqual(sum(a.denominator),4)

    def test_wilson_boundary_known_result(self):
        d=pd.DataFrame({'id':range(10),'event':0,'kind':'a'})
        a,_=self.summary(d)
        self.assertAlmostEqual(a.lower.iloc[0],0);self.assertAlmostEqual(a.upper.iloc[0],.27753279986,places=9)
        self.assertTrue(np.isnan(a.upper.iloc[1]))

    def test_undeclared_group_cannot_be_dropped(self):
        d=self.source();d.loc[0,'kind']='unexpected'
        with self.assertRaisesRegex(ValueError,'omit'):self.summary(d,missing='exclude')

    def test_invalid_event_cannot_be_silently_excluded(self):
        d=self.source();d.loc[0,'event']=2
        with self.assertRaisesRegex(ValueError,'binary'):self.summary(d,missing='exclude')

    def test_repeated_units_need_another_estimator(self):
        d=self.source();d.loc[1,'id']=0
        with self.assertRaisesRegex(ValueError,'record per'):self.summary(d,missing='exclude')

    def test_original_positions_survive_summary(self):
        a,_=self.summary(missing='exclude');origins=lineage(a)['row_origins']
        self.assertEqual([len(x) for x in origins],[2,2,0]);self.assertEqual(len(set(sum(origins,[]))),4)

    def test_stale_provenance_rejected(self):
        a,_=self.summary(missing='exclude');a.loc[0,'estimate']=.99
        with self.assertRaisesRegex(ValueError,'Stale'):lineage(a)

    def test_persisted_lineage_and_text_codes_survive_reload(self):
        d=self.source();d['code']=['001','NA','003','004','005']
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'records.csv';save_study_table(d,p);restored=read_data(p)
            self.assertEqual(restored.code.tolist(),d.code.tolist())
            self.assertEqual(lineage(restored)['row_origins'],lineage(d)['row_origins'])
            p.write_text(p.read_text().replace('001','999'))
            with self.assertRaisesRegex(ValueError,'CSV bytes'):read_data(p)

    def test_grouped_view_has_correct_record_ancestry(self):
        d=self.source();r=d.groupby('kind',as_index=False).event.count()
        bound=grouped_lineage(d,r,by=['kind'],operation='count observed events by kind')
        self.assertEqual([len(v) for v in lineage(bound)['row_origins']],[2,3])

    def test_same_file_under_two_names_cannot_double_sample_size(self):
        with self.assertRaisesRegex(ValueError,'reused across cohorts'):
            combine_cohorts({'one':self.source(),'renamed copy':self.source()})

    def test_grouped_binary_rows_are_not_individual_trials(self):
        d=self.source();r=pd.DataFrame({'kind':['a','b'],'id':[0,1],'event':[1,0]})
        r=grouped_lineage(d,r,by=['kind'],operation='caller grouped summary')
        with self.assertRaisesRegex(ValueError,'individual records'):self.summary(r)

    def test_cohort_schema_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,'schemas differ'):
            combine_cohorts({'one':self.source(),'two':self.source().drop(columns='event')})

    def test_records_preserved_without_cross_cohort_patient_claim(self):
        a=combine_cohorts({'one':self.source(),'two':self.source().assign(event=0)})
        self.assertEqual(len(a),10);self.assertEqual(a.record_id.nunique(),10)
        self.assertEqual(len(lineage(a)['sources']),2)

    def test_zero_is_reported_separately_from_na(self):
        a,r=missingness_summary({'one':self.source()},['event'])
        self.assertEqual(a.missing.iloc[0],1);self.assertEqual(a.recorded_zero.iloc[0],2)
        self.assertEqual(r['cohorts'][0]['complete_positions'],[0,1,2,4])

    def test_proportion_route_counts_and_alternative(self):
        d=self.source().dropna();p=plan_chart(d,{'intent':'proportion','event':'event','group':'kind','unit':'id'})
        self.assertEqual(p['status'],'ready');self.assertEqual(p['recommended']['construction'],'proportion-interval')
        self.assertEqual(sum(x['denominator'] for x in p['diagnostics']['binomial_cells']),4)
        self.assertTrue(any(x['construction']=='pooled-proportion-only' for x in p['rejected']))

    def test_derived_summary_cannot_claim_independent_validation(self):
        d=combine_cohorts({'one':self.source().dropna(),'two':self.source().dropna().assign(event=0)})
        a,_=binomial_estimates(d,event='event',unit='record_id',groups=['cohort'],levels={'cohort':['one','two']},interval='wilson')
        spec={'question':'Does pattern vary?','claims':{'c':{'boundary':'description','required_roles':['main','boundary']}},'panels':[
            {'id':'raw','source':'raw','claim':'c','role':'main','question':'Observed fractions?',
             'chart':{'intent':'proportion','event':'event','group':'cohort','unit':'record_id'}},
            {'id':'summary','source':'summary','claim':'c','role':'boundary','question':'Independent validation?',
             'independence':{'from':'raw'},'chart':{'intent':'estimates','data_level':'summary','y':'estimate','group':'cohort'}}]}
        p=plan_evidence({'raw':d,'summary':a},spec)
        self.assertEqual(p['status'],'needs_resolution');self.assertTrue(any('original records' in x for x in p['blockers']))
        del spec['panels'][1]['independence']
        self.assertEqual(plan_evidence({'raw':d,'summary':a},spec)['status'],'ready')


class EncodingRevisionTests(unittest.TestCase):
    def test_final_pdf_rotated_seven_point_font_is_not_smaller_from_roundoff(self):
        from audit_pdf_text import audit_pdf
        fig=plt.figure(figsize=(2,2));fig.text(.4,.5,'Rotated',fontsize=7,rotation=29.9)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'rotated.pdf';fig.savefig(path)
            self.assertEqual(audit_pdf(path.read_bytes(),minimum_pt=7)['below_minimum_count'],0)
            self.assertGreater(audit_pdf(path.read_bytes(),minimum_pt=7.01)['below_minimum_count'],0)
        plt.close(fig)
    def test_text_contrast_uses_rendered_colour_including_alpha(self):
        for color in ['#EAF3EC','#405D54','#D7905A',(.8,.2,.2,.4)]:
            ink,report=contrast_text(color)
            self.assertGreaterEqual(report['contrast'],4.5)

    def test_palette_identity_does_not_depend_on_plot_order(self):
        p=palette_project('ocean',['A','B','C'])
        self.assertNotEqual(p['groups']['A']['color'],p['groups']['B']['color'])
        with self.assertRaises(ValueError):palette_project('ocean',['same','same'])
    def compare(self,before,after):
        # Export hash verification is exercised elsewhere; this unit isolates
        # actual Matplotlib encoding changes while data coordinates stay fixed.
        with patch('review_tools.verify_exports',return_value=[]):
            return compare_revisions({'source_data_sha256':'same-input','figure_snapshot':before},
                {'source_data_sha256':'same-input','figure_snapshot':after})['changes_requiring_justification']

    def test_expanding_axes_is_still_an_encoding_change(self):
        fig,ax=plt.subplots();ax.set_label('panel');ax.plot([0,1],[0,1]);a=figure_snapshot(fig)
        ax.set_xlim(-5,5);b=figure_snapshot(fig)
        self.assertEqual(a['panels']['panel']['marks'],b['panels']['panel']['marks'])
        self.assertIn('View limits changed: panel',self.compare(a,b));plt.close(fig)

    def test_legacy_missing_metadata_is_not_claimed_as_a_real_scale_change(self):
        import copy
        fig,ax=plt.subplots();ax.set_label('panel');ax.plot([0,1],[0,1]);current=figure_snapshot(fig)
        legacy=copy.deepcopy(current);del legacy['panels']['panel']['view_limits']
        changes=self.compare(legacy,current)
        self.assertIn('Encoding metadata availability changed: panel/view_limits',changes)
        self.assertNotIn('View limits changed: panel',changes);plt.close(fig)

    def test_unit_labels_cannot_drift_without_a_decision(self):
        fig,ax=plt.subplots();ax.set_label('panel');ax.plot([0,1],[0,1]);ax.set_xlabel('Length (µm)');a=figure_snapshot(fig)
        ax.set_xlabel('Length (mm)');b=figure_snapshot(fig)
        self.assertIn('Axis labels/units changed: panel',self.compare(a,b));plt.close(fig)

    def test_named_errorbar_colour_is_checked_on_actual_container_data(self):
        fig,ax=plt.subplots();ax.errorbar([.5],[0],xerr=[.1],fmt='o',color='orange',label='expected blue')
        audit=audit_rendered_mapping(figure_snapshot(fig),{'groups':{'expected blue':{'color':'blue'}}})
        self.assertEqual(audit['status'],'FAIL');plt.close(fig)

    def test_same_mesh_values_with_changed_colour_scale_are_flagged(self):
        fig,ax=plt.subplots();ax.set_label('panel');m=ax.pcolormesh([[0,1],[2,3]],vmin=0,vmax=3);a=figure_snapshot(fig)
        m.set_clim(0,10);b=figure_snapshot(fig)
        self.assertEqual(a['panels']['panel']['marks'],b['panels']['panel']['marks'])
        self.assertIn('Scalar color encoding changed: panel',self.compare(a,b));plt.close(fig)


if __name__=='__main__':unittest.main()
