"""Decision, measured layout and non-regression behavior on actual figure objects."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skills/light-chart/scripts'))
from chart_plan import plan_chart, data_digest
from library import plan
from composition import compose, label_line_ends, LayoutError
from review_tools import audit_marks, figure_snapshot, compare_revisions, bind_exports, record_review
from visual_qa import audit_layout
from editorial import figure_style


class DecisionAndRevision(unittest.TestCase):
    def tearDown(self):
        plt.close('all')

    def test_same_columns_different_questions_and_summary_boundary(self):
        d = pd.DataFrame({'id':['a','b','a','b'], 'phase':['pre','pre','post','post'], 'v':[2,4,3,8]})
        p = plan(d, {'intent':'change','unit':'id','condition':'phase','y':'v','order':['pre','post']})
        self.assertEqual(p['recommended']['construction'], 'paired-change')
        self.assertEqual(p['diagnostics']['used_units'],2)
        self.assertTrue(p['candidates'][0]['resources']['entrypoints'])
        self.assertEqual(p['rejected'][0]['construction'],'independent-mean-bars')
        p = plan_chart(d, {'intent':'compare','group':'phase','y':'v','data_level':'summary'})
        self.assertEqual(p['recommended']['construction'],'estimate-interval')
        self.assertTrue(any('distributions' in x['reason'] for x in p['rejected']))
        p = plan_chart(d, {'intent':'compare','group':'phase','y':'v','unit':'id'})
        self.assertIsNone(p['recommended'])
        self.assertTrue(p['blockers'])

    def test_missing_pair_policy_and_technical_repeats_are_not_silently_fixed(self):
        d = pd.DataFrame({'id':['a','b','a'], 'phase':['pre','pre','post'], 'v':[2,4,3]})
        spec = {'intent':'change','unit':'id','condition':'phase','y':'v','order':['pre','post']}
        self.assertIsNone(plan_chart(d,spec)['recommended'])
        p = plan_chart(d,{**spec,'missing':'complete_cases'})
        self.assertEqual(p['diagnostics']['excluded_rows'],[1])
        self.assertEqual(p['diagnostics']['used_units'],1)
        self.assertEqual(len(d),3)
        dup = pd.concat([d,d.iloc[[0]]], ignore_index=True)
        self.assertTrue(any('Duplicate' in b for b in plan_chart(dup,spec)['blockers']))

    def test_reference_signature_and_true_order(self):
        d = pd.DataFrame({'x':np.arange(20), 'y':np.arange(20)**2})
        spec = {'intent':'association','x':'x','y':'y','reference':{'required_elements':['marginals']}}
        self.assertEqual(plan_chart(d,spec)['recommended']['construction'],'joint-density-marginals')
        self.assertIsNone(plan_chart(d,{'intent':'trend','x':'x','y':'y'})['recommended'])
        self.assertEqual(plan_chart(d,{'intent':'trend','x':'x','y':'y','ordered':True})['status'],'ready')

    def test_numeric_condition_codes_do_not_prove_a_continuous_trajectory(self):
        d=pd.DataFrame({'id':['a','a','a','b','b','b'],'code':[1,2,3,1,2,3],'value':[2,1,3,4,2,5]})
        spec={'intent':'change','unit':'id','condition':'code','y':'value','order':[1,2,3]}
        self.assertIsNone(plan_chart(d,spec)['recommended'])
        self.assertEqual(plan_chart(d,{**spec,'ordered':True})['recommended']['construction'],'within-unit-trajectories')

    def test_survival_design_must_match_implementation(self):
        d = pd.DataFrame({'id':[1,2], 'time':[10,20], 'status':[0,1]})
        spec = {'intent':'survival','unit':'id','time':'time','event':'status','backend':'r'}
        p = plan(d,spec)
        self.assertEqual(p['candidates'][0]['resources']['entrypoints'][0]['symbol'],'survival_panel_r')
        self.assertIsNone(plan_chart(d,{**spec,'design':'competing-risk'})['recommended'])
        self.assertIsNone(plan_chart(d.assign(status=[1,2]),spec)['recommended'])

    def test_matrix_missingness_keeps_cells_and_never_treats_ID_as_value(self):
        d=pd.DataFrame({'id':[101,102], 'a':[1,np.nan], 'b':[3,4]})
        p=plan_chart(d,{'intent':'matrix','unit':'id','values':['a','b'],'missing':'display'})
        self.assertEqual(p['status'],'ready')
        self.assertEqual(p['diagnostics']['matrix_shape'],[2,2])
        self.assertEqual(p['diagnostics']['row_positions'],[0,1])
        self.assertEqual(p['diagnostics']['excluded_rows'],[])
        self.assertIsNone(plan_chart(d,{'intent':'matrix','values':['a','b']})['recommended'])

    def test_different_quantities_get_separate_scales_without_saturation(self):
        d=pd.DataFrame({'effect':[-2,1],'percent':[40,95]})
        spec={'intent':'matrix','values':['effect','percent'],'value_groups':{
            'effect':{'columns':['effect'],'limits':[-3,3]},
            'fraction':{'columns':['percent'],'limits':[0,100]}}}
        self.assertEqual(plan_chart(d,spec)['recommended']['construction'],'multi-scale-heatmaps')
        spec['value_groups']['fraction']['limits']=[0,90]
        self.assertIsNone(plan_chart(d,spec)['recommended'])

    def test_balanced_columns_budget_long_names_before_equal_data_widths(self):
        with figure_style():
            c=compose((170,90),[['left','right']],balance_columns=True)
            for key,ax in c.axes.items():
                ax.plot([0,1],[0,1]);ax.set_yticks([0,1],
                    ['long experimental condition','another experimental condition'] if key=='left' else ['0','1'])
            r=c.fit()['plot_rectangles_mm']
            self.assertAlmostEqual(r['left'][2],r['right'][2],places=5)
            self.assertGreater(c.slots['left'][2]-c.slots['left'][0],c.slots['right'][2]-c.slots['right'][0])

    def test_direct_labels_keep_endpoints_and_physical_separation_after_fit(self):
        with figure_style():
            c=compose((110,75),[['main']]);ax=c.axes['main']
            lines=[ax.plot([0,1],[0,1+i*.01],label='Series '+str(i))[0] for i in range(4)]
            before=[line.get_xydata().copy() for line in lines]
            notes=label_line_ends(ax,minimum_gap_pt=11)
            c.fit();c.figure.canvas.draw()
            boxes=sorted([n.get_window_extent(c.figure.canvas.get_renderer()) for n in notes],key=lambda b:b.y0)
            # Annotation boxes include leaders, so inspect text positions directly.
            ypos=sorted(n.get_position()[1]*ax.get_window_extent().height for n in notes)
            self.assertTrue(np.all(np.diff(ypos)>=11*c.figure.dpi/72-1e-6))
            for line,values in zip(lines,before):np.testing.assert_array_equal(line.get_xydata(),values)

    def test_hexbin_offsets_are_not_misread_as_data_near_origin(self):
        fig,ax=plt.subplots();x=np.linspace(10,20,100)
        ax.hexbin(x,x**2,gridsize=10,mincnt=1)
        self.assertFalse(any(r['code']=='data_clipped' for r in audit_marks(fig)))

    def test_measured_labels_spans_and_panel_local_aspect(self):
        with figure_style():
            c = compose((180,110), [['hero','hero','control'],['hero','hero','boundary']],
                width_ratios=[1,1,1.2], panels={'hero':{'plot_aspect':1,'min_plot_mm':[50,50]}})
            for key, ax in c.axes.items():
                ax.plot([0,1],[0,1]);ax.set(xlabel='Follow-up (days)',ylabel='Observed response (a.u.)',title=key)
            report = c.fit()
            r = report['plot_rectangles_mm']['hero']
            self.assertAlmostEqual(r[2]/r[3],1)
            self.assertGreater(r[2]*r[3],np.prod(report['plot_rectangles_mm']['control'][2:]))
            self.assertTrue(report['converged'])
            self.assertEqual(tuple(c.figure.get_size_inches()*25.4),(180,110))
            self.assertFalse(any('裁切' in m for _,m in audit_layout(c.figure)))

    def test_layout_refuses_unreadable_page_without_shrinking_text(self):
        c = compose((30,25),[['a']],panels={'a':{'min_plot_mm':[25,20]}})
        ax = c.axes['a'];ax.set_ylabel('Very long label at the original font size')
        old = ax.yaxis.label.get_fontsize()
        with self.assertRaises(LayoutError):c.fit()
        self.assertEqual(ax.yaxis.label.get_fontsize(),old)

    def test_real_marks_interval_clipping_and_legend_crossing(self):
        fig, ax = plt.subplots()
        ax.set_label('result')
        ax.plot([0,10],[.5,.5],label='A')
        ax.errorbar([5],[.8],yerr=[.5],fmt='o')
        ax.set(xlim=(0,10),ylim=(0,1))
        ax.legend(loc='center')
        found = audit_marks(fig)
        self.assertTrue(any(x['code']=='legend_over_data' for x in found))
        self.assertTrue(any(x['code']=='data_clipped' and x['mark'].startswith('interval') for x in found))
        ax.get_legend().remove();ax.set_ylim(-.1,1.5)
        self.assertEqual(audit_marks(fig),[])

    def test_fixed_axes_tick_collisions_are_checked(self):
        fig = plt.figure(figsize=(2,2));ax=fig.add_axes([.2,.2,.7,.7])
        ax.set_xticks([0,1,2],['long condition one','long condition two','long condition three'])
        self.assertTrue(any('刻度标签重叠' in m for _,m in audit_layout(fig)))

    def test_revision_refuses_data_loss_signature_loss_and_stale_review(self):
        with tempfile.TemporaryDirectory() as tmp, figure_style():
            root=Path(tmp);fig,ax=plt.subplots(figsize=(3,2));ax.set_label('joint')
            line,=ax.plot([0,1],[0,1],label='A',color='#226D8D')
            def export(name):
                base=root/name;fig.savefig(base.with_suffix('.pdf'));fig.savefig(base.with_suffix('.png'))
                report={'automated_status':'PASS','figure_snapshot':figure_snapshot(fig),
                        'source_data_sha256':data_digest(pd.DataFrame({'x':[0,1],'y':[0,1]}))}
                bind_exports(report,pdf=base.with_suffix('.pdf'),png=base.with_suffix('.png'))
                q=base.with_suffix('.qa.json');q.write_text(json.dumps(report),encoding='utf8')
                return report,q
            before,_=export('before')
            ax.set_position([.2,.2,.7,.6]);after,path=export('after')
            self.assertEqual(compare_revisions(before,after)['status'],'no_evidence_regression')
            self.assertEqual(compare_revisions(before,after,required_panels=['marginal'])['status'],'regression')
            line.set_ydata([0,.4]);bad,_=export('bad')
            self.assertEqual(compare_revisions(before,bad)['status'],'regression')
            line.set_ydata([0,1]);line.set_color('#CA7259');bad,_=export('color')
            self.assertEqual(compare_revisions(before,bad)['status'],'regression')
            inspected=[x['path'] for x in after['review_artifacts'].values() if x['path'].endswith('.png')]
            reviewed=record_review(path,inspected=inspected,observations=['Test inspection metadata only; no visual quality claim.'])
            self.assertEqual(reviewed['visual_review']['reviewer'],'executor')
            Path(inspected[0]).write_bytes(b'changed')
            with self.assertRaises(ValueError):record_review(path,inspected=inspected,observations=['Stale artifact'])


if __name__ == '__main__':unittest.main()
