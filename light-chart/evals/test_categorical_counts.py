"""Count conservation and actual statistical mosaic/alluvial geometry."""
from itertools import product
from pathlib import Path
import copy
import hashlib
import json
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skills/light-chart/scripts'))
from count_tables import prepare_count_table, conditional_proportions, plot_mosaic, plot_alluvial
from repeated_measures import prepare_repeated_trajectory
from figure_job import prepare_job
from review_tools import figure_snapshot, compare_revisions
import library


class CategoricalCounts(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame([(a,b,n) for (a,b),n in zip(product(['A','B','Zero'],['No','Yes']),[3,1,2,2,0,0])],
                                 columns=['group','outcome','n'])
        self.order = {'group':['B','A','Zero'], 'outcome':['Yes','No']}
        self.chart = dict(intent='count_table', dimensions=['group','outcome'], count='n',
                          order=self.order, count_semantics='observed_counts', view='mosaic')
        self.colors = {'Yes':'#286B8A','No':'#CF6B45'}

    def prepared(self, data=None, **kwargs):
        return prepare_count_table(self.data if data is None else data, dimensions=['group','outcome'], count='n',
            order=self.order, count_semantics='observed_counts', **kwargs)

    def test_joint_and_conditional_denominators_keep_zero_cells_and_exact_integer_totals(self):
        t = self.prepared()
        self.assertEqual(t.total,8)
        self.assertEqual(t.marginals,{'group':{'B':4,'A':4,'Zero':0}, 'outcome':{'Yes':3,'No':5}})
        p = conditional_proportions(t,given=['group'])
        self.assertEqual([r['denominator'] for r in p],[4,4,4,4,0,0])
        self.assertEqual([r['proportion'] for r in p],[.5,.5,.25,.75,None,None])
        self.assertEqual(len({c['cell_id'] for c in t.cells}),6)
        self.assertTrue(all(isinstance(c['count'],int) for c in t.cells))

    def test_actual_mosaic_rectangles_encode_count_without_gaps_or_fake_zero_widths(self):
        fig,ax=plt.subplots()
        t=self.prepared(); r=plot_mosaic(ax,t,colors=self.colors,color_dimension='outcome')
        for c in r['geometry']:
            patch=r['artists'][c['cell_id']]
            self.assertAlmostEqual(patch.get_width()*patch.get_height(),c['count']/8,places=15)
            self.assertEqual(patch.get_xy(),(c['x'],c['y']))
            self.assertEqual(patch.get_gid(),'cell:'+c['cell_id'])
            if not c['count']:self.assertEqual(patch.get_width()*patch.get_height(),0)
        self.assertAlmostEqual(sum(c['area'] for c in r['geometry']),1)
        self.assertEqual([v.get_text() for v in ax.get_xticklabels()],['B','A'])
        self.assertEqual(r['zero_width_categories_for_caption_or_companion'],['Zero'])
        plt.close(fig)

    def test_shuffle_does_not_reorder_geometry_or_category_identity(self):
        t=self.prepared(); u=self.prepared(self.data.sample(frac=1,random_state=4).reset_index(drop=True))
        self.assertEqual([(c['cell_id'],c['count']) for c in t.cells],[(c['cell_id'],c['count']) for c in u.cells])
        fig,(a,b)=plt.subplots(1,2)
        r=plot_mosaic(a,t,colors=self.colors,color_dimension='outcome')
        s=plot_mosaic(b,u,colors=self.colors,color_dimension='outcome')
        fields=('cell_id','count','x','y','width','height','area')
        self.assertEqual([{k:c[k] for k in fields} for c in r['geometry']], [{k:c[k] for k in fields} for c in s['geometry']])
        plt.close(fig)

    def test_all_zero_total_is_unavailable_not_nan_or_pseudocount_geometry(self):
        t=self.prepared(self.data.assign(n=0))
        self.assertTrue(all(p['proportion'] is None for p in conditional_proportions(t,given=['group'])))
        fig,ax=plt.subplots();r=plot_mosaic(ax,t,colors=self.colors,color_dimension='outcome')
        self.assertEqual(r['status'],'empty_total')
        self.assertEqual(len(r['geometry']),6)
        self.assertTrue(all(g['area']==0 for g in r['geometry']))
        self.assertFalse(ax.get_xticklabels())
        plt.close(fig)

    def test_invalid_cells_and_inexact_integer_counts_never_prepare(self):
        variants=[self.data.iloc[:-1],pd.concat([self.data,self.data.iloc[:1]]),self.data.assign(n=-1),
                  self.data.assign(n=.5),self.data.assign(n=True),self.data.assign(n=np.nan),
                  self.data.assign(n=2**53),self.data.assign(n=complex(2,1)),
                  self.data.assign(group=['A','A','B','B','Zero',None])]
        for frame in variants:
            with self.subTest(frame=str(frame)):
                with self.assertRaises(ValueError):self.prepared(frame)
        for order in [{'group':['A','B'],'outcome':['No','Yes']}, {'group':['A','B','Zero'],'outcome':['No','No']}]:
            with self.assertRaises(ValueError):prepare_count_table(self.data,dimensions=['group','outcome'],count='n',order=order,count_semantics='observed_counts')
        with self.assertRaises(ValueError):prepare_count_table(self.data,dimensions=['group','outcome'],count='n',order=self.order,count_semantics='survey_weights')
        large=self.data.assign(n=pd.Series([2**53,0,0,0,0,0],dtype=object))
        self.assertEqual(self.prepared(large).total,2**53)

    def test_alluvial_each_joint_identity_is_conserved_at_both_ends_and_all_nodes(self):
        frame=pd.DataFrame([(*key,n) for key,n in zip(product(['a','b'],['x','y'],['off','on']),[3,1,0,2,4,0,1,1])],columns=['one','two','three','n'])
        order={'one':['b','a'],'two':['y','x'],'three':['on','off']}
        t=prepare_count_table(frame,dimensions=['one','two','three'],count='n',order=order,count_semantics='observed_counts')
        fig,ax=plt.subplots()
        r=plot_alluvial(ax,t,colors={'a':'#2C728E','b':'#B45B39'},color_dimension='one',relationship_semantics='joint_categories')
        self.assertEqual(len(r['ribbons']),16)
        for g in r['ribbons']:
            self.assertAlmostEqual(g['left_interval'][1]-g['left_interval'][0],g['count']*r['count_to_height'])
            self.assertAlmostEqual(g['right_interval'][1]-g['right_interval'][0],g['count']*r['count_to_height'])
            actual=r['ribbon_artists'][(g['cell_id'],g['left_axis'])].get_path().vertices
            np.testing.assert_array_equal(actual,np.array(g['vertices']))
            self.assertAlmostEqual(actual[7,1]-actual[0,1],g['count']*r['count_to_height'])
            self.assertAlmostEqual(actual[4,1]-actual[3,1],g['count']*r['count_to_height'])
        for node in r['nodes']:
            actual=r['node_artists'][node['node_id']]
            self.assertAlmostEqual(actual.get_height(),node['count']*r['count_to_height'])
            for segment,side in [(node['axis']-1,'right'),(node['axis'],'left')]:
                if segment not in (0,1):continue
                ribbons=[g for g in r['ribbons'] if g['left_axis']==segment and g['levels'][node['axis']]==node['level']]
                self.assertEqual(sum(g['count'] for g in ribbons),node['count'])
                endpoints=sorted([g[side+'_interval'] for g in ribbons])
                self.assertAlmostEqual(endpoints[0][0],node['y0'])
                self.assertAlmostEqual(endpoints[-1][1],node['y1'])
        with self.assertRaises(ValueError):plot_alluvial(ax,t,colors={'a':'#2C728E','b':'#B45B39'},color_dimension='one',relationship_semantics='temporal_flow')
        # Revision snapshots must retain ribbons as well as the node rectangles.
        before=figure_snapshot(fig)
        first=r['ribbon_artists'][(r['ribbons'][0]['cell_id'],0)]
        first.get_path().vertices[3,1]+=.01
        after=figure_snapshot(fig)
        self.assertNotEqual(before['panels'],after['panels'])
        plt.close(fig)

    def test_long_labels_more_categories_and_zero_nodes_keep_original_identities(self):
        levels=['A category with a complete long scientific label '+str(i) for i in range(9)]
        frame=pd.DataFrame([(*key,0 if key[0]==levels[-1] else 1) for key in product(levels,['No','Yes'],['Left','Right'])],columns=['a','b','c','n'])
        t=prepare_count_table(frame,dimensions=['a','b','c'],count='n',order={'a':levels,'b':['No','Yes'],'c':['Left','Right']},count_semantics='observed_counts')
        fig,ax=plt.subplots();r=plot_alluvial(ax,t,colors={'No':'#174B75','Yes':'#BD6745'},color_dimension='b',relationship_semantics='joint_categories')
        self.assertEqual(len(r['ribbons']),len(frame)*2)
        self.assertEqual([n['level'] for n in r['nodes'] if n['dimension']=='a'],levels)
        zero=[n for n in r['nodes'] if n['dimension']=='a' and n['level']==levels[-1]][0]
        self.assertEqual(r['node_artists'][zero['node_id']].get_height(),0)
        with self.assertRaises(ValueError):plot_alluvial(ax,t,colors={'No':'#174B75','Yes':'#BD6745'},color_dimension='b',relationship_semantics='joint_categories',node_gap=.2)
        plt.close(fig)

    def test_real_prepare_route_is_summary_aware_and_mosaic_no_longer_means_layout(self):
        r=prepare_job(self.data,{'question':'How is aggregate support distributed?','chart':self.chart})
        self.assertEqual(r['status'],'prepared')
        self.assertEqual(r['decisions']['main']['recommended']['construction'],'statistical-mosaic')
        self.assertEqual(r['profiles']['data']['observation_structure']['data_level'],'aggregate_count_cells')
        self.assertEqual(r['decisions']['main']['diagnostics']['total_count'],8)
        self.assertEqual(r['field_mapping']['main']['dimensions'],['group','outcome'])
        route=library.route('mosaic',backend='python')
        self.assertEqual(route['status'],'implementation_found')
        self.assertTrue(any(e['id']=='impl-statistical-mosaic' for e in route['entrypoints']))
        self.assertTrue(any(e['id']=='impl-static-alluvial' for e in library.route('alluvial',backend='python')['entrypoints']))
        self.assertEqual(prepare_job(self.data,{'question':'What support?','chart':{**self.chart,'count_semantics':'weights'}})['status'],'needs_resolution')


class CategoricalRevisionIdentity(unittest.TestCase):
    """Exercise actual unlabeled cell artists through revision-bound exports."""
    def make(self, view):
        dims = ['site','status'] if view == 'mosaic' else ['site','status','assay']
        order = {d:['L','R'] for d in dims}
        data = pd.DataFrame([dict(zip(dims,key),n=i+1)
            for i,key in enumerate(product(*order.values()))])
        table = prepare_count_table(data,dimensions=dims,count='n',order=order,
                                    count_semantics='observed_counts')
        fig,ax = plt.subplots(figsize=(3,2))
        kwargs = dict(colors={'L':'#24648A','R':'#B34B3D'},color_dimension='status')
        if view == 'mosaic':plot_mosaic(ax,table,**kwargs)
        else:plot_alluvial(ax,table,relationship_semantics='joint_categories',**kwargs)
        self.addCleanup(plt.close,fig)
        return fig,ax,table.source_sha256

    def report(self, fig, folder, name, digest):
        path = folder/(name+'.png')
        fig.savefig(path,dpi=80)
        return {'source_data_sha256':digest,'figure_snapshot':figure_snapshot(fig),
                'review_artifacts':{path.name:{'path':str(path),
                    'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}}

    def test_swapped_actual_category_facecolors_and_overwritten_gids_require_revision_decisions(self):
        from matplotlib.colors import to_rgba
        for view in ['mosaic','alluvial']:
            with self.subTest(view=view), tempfile.TemporaryDirectory() as tmp:
                fig,ax,digest = self.make(view); folder=Path(tmp)
                self.assertTrue(all(not p.get_label() or p.get_label().startswith('_') for p in ax.patches))
                before = self.report(fig,folder,'before',digest)
                originals = [p.get_facecolor() for p in ax.patches]
                for patch in ax.patches:
                    color=patch.get_facecolor()
                    if color == to_rgba('#24648A'):patch.set_facecolor('#B34B3D')
                    elif color == to_rgba('#B34B3D'):patch.set_facecolor('#24648A')
                swapped = self.report(fig,folder,'swapped',digest)
                for patch,color in zip(ax.patches,originals):
                    patch.set_facecolor(color);patch.set_gid('wrong-source-cell')
                wrong_identity = self.report(fig,folder,'wrong-identity',digest)
                for changed in [swapped,wrong_identity]:
                    result=compare_revisions(before,changed)
                    self.assertEqual(result['errors'],[])
                    self.assertEqual(result['status'],'regression')
                    self.assertIn('Identified data-artist encoding changed: axes-0',
                                  result['changes_requiring_justification'])

    def test_every_actual_node_cell_and_ribbon_keeps_identity_including_gid_removal(self):
        for view in ['mosaic','alluvial']:
            fig,ax,_ = self.make(view); before=figure_snapshot(fig)
            for index,patch in enumerate(ax.patches):
                gid=patch.get_gid()
                for changed in ['wrong-source-cell',None]:
                    with self.subTest(view=view,patch=index,gid=changed):
                        patch.set_gid(changed)
                        self.assertNotEqual(before,figure_snapshot(fig))
                patch.set_gid(gid)
            self.assertEqual(before,figure_snapshot(fig))

    def test_count_linewidth_edge_decoration_and_layout_changes_preserve_evidence(self):
        for view in ['mosaic','alluvial']:
            with self.subTest(view=view), tempfile.TemporaryDirectory() as tmp:
                fig,ax,digest = self.make(view);folder=Path(tmp)
                before=self.report(fig,folder,'before',digest)
                for patch in ax.patches:
                    patch.set_linewidth(1.2);patch.set_edgecolor('#222222')
                ax.set_position([.2,.2,.6,.6])
                after=self.report(fig,folder,'after',digest)
                result=compare_revisions(before,after)
                self.assertEqual(result['status'],'no_evidence_regression',result)

    def test_unidentified_ordinary_patch_decoration_does_not_become_category_identity(self):
        from matplotlib.patches import Rectangle
        with tempfile.TemporaryDirectory() as tmp:
            fig,ax=plt.subplots();self.addCleanup(plt.close,fig)
            patch=Rectangle((.1,.2),.3,.4,facecolor='blue');ax.add_patch(patch)
            folder=Path(tmp);before=self.report(fig,folder,'before','same-source')
            patch.set_facecolor('red');patch.set_linewidth(3)
            after=self.report(fig,folder,'after','same-source')
            result=compare_revisions(before,after)
            self.assertEqual(result['status'],'no_evidence_regression',result)


class EvidenceConstructorViews(unittest.TestCase):
    """Only constructor-consumed choices can distinguish duplicate evidence."""
    def pair(self, data, first, second):
        panels=[dict(id=key,source='data',role=role,question=role,claim='c',
                     chart=chart,unique_inference='Declared interpretation '+key)
                for key,role,chart in [('a','primary',first),('b','boundary',second)]]
        return prepare_job(data,dict(question='Which supplied evidence supports the comparison?',
            claims={'c':{'boundary':'Descriptive views of the same records'}},
            panels=panels,require_complementarity=True))

    def count_fixture(self):
        data=pd.DataFrame([(*key,'Assay',i+1) for i,key in
            enumerate(product(['A','B'],['No','Yes']))],columns=['site','status','assay','n'])
        chart=dict(intent='count_table',dimensions=['site','status'],count='n',
            order={'site':['A','B'],'status':['No','Yes']},count_semantics='observed_counts',view='mosaic')
        return data,chart

    def test_ignored_new_keys_and_alias_count_roles_cannot_launder_non_count_duplicates(self):
        data=pd.DataFrame({'id':['a','b','c'],'actual':['A','B','A'],
            'forecast':['A','A','B'],'unused_one':[1,2,3],'unused_two':[4,5,6]})
        chart=dict(intent='confusion-counts',unit='id',true='actual',predicted='forecast',
                   class_order=['A','B'],evaluation_split='test')
        extras=[({'view':'one ignored description'},{'view':'another ignored description'}),
            ({'dimensions':['actual']},{'dimensions':['forecast']}),
            ({'count_semantics':'one ignored description'},{'count_semantics':'another'}),
            ({'relationship_semantics':'one ignored description'},{'relationship_semantics':'another'}),
            ({'count':'unused_one'},{'count':'unused_two'}),
            # Filtering an ignored count key must preserve the real true/predicted
            # roles when their field names happen to be used as that key's value.
            ({'count':'actual'},{'count':'forecast'})]
        for first,second in extras:
            with self.subTest(first=first,second=second):
                result=self.pair(data,{**chart,**first},{**chart,**second})
                self.assertEqual(result['status'],'needs_resolution')
                pair=result['evidence']['complementarity'][0]
                self.assertTrue(pair['same_declared_encoding'])
                self.assertEqual(pair['shared_measurements'],['actual','forecast'])

    def test_mosaic_ignored_relationship_prose_remains_duplicate(self):
        data,chart=self.count_fixture()
        result=self.pair(data,{**chart,'relationship_semantics':'ignored prose A'},
                              {**chart,'relationship_semantics':'ignored prose B'})
        self.assertEqual(result['status'],'needs_resolution')
        self.assertTrue(result['evidence']['complementarity'][0]['same_declared_encoding'])

    def test_actual_count_dimensions_and_constructor_choices_remain_distinct(self):
        data,chart=self.count_fixture()
        alternatives=[{**chart,'dimensions':['status','site']},
            {**chart,'dimensions':['site','status','assay'],
             'order':{**chart['order'],'assay':['Assay']},'view':'alluvial',
             'relationship_semantics':'joint_categories'}]
        for other in alternatives:
            with self.subTest(dimensions=other['dimensions']):
                result=self.pair(data,chart,other)
                self.assertEqual(result['status'],'prepared',result['blockers'])
                pair=result['evidence']['complementarity'][0]
                self.assertFalse(pair['same_declared_encoding'])
                self.assertEqual(pair['shared_measurements'],['n'])
                self.assertTrue(any('not independent validation' in w for w in result['warnings']))
        constructors=[result['decisions'][key]['recommended']['construction'] for key in ['a','b']]
        self.assertEqual(constructors,['statistical-mosaic','static-joint-alluvial'])

    def test_unsupported_count_view_cannot_prepare_as_another_evidence_view(self):
        data,chart=self.count_fixture()
        result=self.pair(data,chart,{**chart,'view':'arbitrary prose'})
        self.assertEqual(result['status'],'needs_resolution')
        self.assertTrue(any('view=mosaic or alluvial' in b for b in result['blockers']))

    def test_impedance_canonical_default_is_duplicate_and_real_views_are_distinct(self):
        data=pd.DataFrame({'spectrum':['S','S'],'hz':[1.,10.],'re':[3.,2.],'im':[-1.,-.5]})
        chart=dict(intent='impedance',spectrum='spectrum',frequency='hz',real='re',imaginary='im',
            frequency_unit='Hz',impedance_unit='ohm',imaginary_convention='physical_signed',order=['S'])
        duplicate=self.pair(data,chart,{**chart,'view':'nyquist_bode'})
        self.assertEqual(duplicate['status'],'needs_resolution')
        self.assertTrue(duplicate['evidence']['complementarity'][0]['same_declared_encoding'])
        distinct=self.pair(data,{**chart,'view':'nyquist'},{**chart,'view':'bode'})
        self.assertEqual(distinct['status'],'prepared',distinct['blockers'])
        self.assertFalse(distinct['evidence']['complementarity'][0]['same_declared_encoding'])
        self.assertEqual([distinct['decisions'][key]['recommended']['construction'] for key in ['a','b']],
                         ['measured-impedance-nyquist','measured-impedance-bode'])


class RepeatedTrajectories(unittest.TestCase):
    def setUp(self):
        self.frame=pd.DataFrame([(i,day,200+10*i+day*(i+1)) for i in range(8) for day in [0,2,5]],columns=['subject','day','reaction'])
        self.chart=dict(intent='repeated_trajectory',unit='subject',x='day',y='reaction',order=list(range(8)),
                        x_unit='day',y_unit='ms',view='small_multiples')

    def test_repeated_preparation_preserves_unit_ids_and_every_actual_coordinate(self):
        r=prepare_job(self.frame.sample(frac=1,random_state=3),{'question':'How do raw trajectories differ between units?','chart':self.chart})
        self.assertEqual((r['status'],r['backend']),('prepared','r'))
        diag=r['decisions']['main']['diagnostics']
        self.assertEqual(diag['unit_count'],8)
        self.assertEqual(diag['rows'],24)
        self.assertFalse(diag['rows_are_independent_units'])
        self.assertFalse(diag['baseline_inferred'])
        for i,t in enumerate(diag['traces']):
            self.assertEqual(t['unit_id'],str(i));self.assertEqual(t['x'],[0,2,5])
            self.assertEqual(t['y'],[200+10*i+d*(i+1) for d in [0,2,5]])
        self.assertTrue(any(e['id']=='impl-repeated-native-r' for e in r['decisions']['main']['recommended']['resources']['entrypoints']))

    def test_missing_duplicate_baseline_and_wrong_order_are_scientific_blockers(self):
        frames=[self.frame.assign(reaction=np.nan),pd.concat([self.frame,self.frame.iloc[:1]]),self.frame.assign(day=True)]
        for frame in frames:
            self.assertEqual(prepare_job(frame,{'question':'How vary?','chart':self.chart})['status'],'needs_resolution')
        for extra in [{'baseline':0},{'order':[0,1]},{'view':'all_in_one'}]:
            self.assertEqual(prepare_job(self.frame,{'question':'How vary?','chart':{**self.chart,**extra}})['status'],'needs_resolution')

    def test_native_r_actual_points_fixed_axes_and_unit_facets(self):
        from r_runtime import run_r
        with tempfile.TemporaryDirectory(prefix='repeated-native-r-') as tmp:
            folder=Path(tmp);script=folder/'check.R';helper=(ROOT/'skills/light-chart/scripts/repeated_measures.R').as_posix()
            pdf=(folder/'native-small-multiples.pdf').as_posix()
            script.write_text(f'''source({json.dumps(helper)})
d<-expand.grid(day=c(0,2,5),subject=0:7);d$reaction<-200+10*d$subject+d$day*(d$subject+1)
r<-repeated_trajectory_r(d,'subject','day','reaction',0:7,'day','ms',ncol=4)
b<-ggplot2::ggplot_build(r$plot)
stopifnot(nrow(b$data[[1]])==24L,nrow(b$data[[2]])==24L,length(b$layout$panel_params)==8L)
stopifnot(length(unique(vapply(b$layout$panel_params,function(p)paste(p$x.range,collapse=','),'')))==1L)
stopifnot(length(unique(vapply(b$layout$panel_params,function(p)paste(p$y.range,collapse=','),'')))==1L)
stopifnot(identical(as.character(b$layout$layout$.lc_unit),as.character(0:7)))
for(i in seq_len(8)){{a<-b$data[[2]][as.integer(b$data[[2]]$PANEL)==i,];stopifnot(identical(a$x,c(0,2,5)),identical(a$y,200+10*(i-1)+c(0,2,5)*i))}}
grDevices::cairo_pdf({json.dumps(pdf)},width=180/25.4,height=100/25.4);print(r$plot);dev.off()
stopifnot(file.info({json.dumps(pdf)})$size>1000)
cat('NATIVE_REPEATED_PASS\\n')
''',encoding='utf-8')
            result=run_r(script,timeout=60)
            self.assertEqual(result['returncode'],0,result['stderr'])
            self.assertIn('NATIVE_REPEATED_PASS',result['stdout'])


if __name__=='__main__':unittest.main()
