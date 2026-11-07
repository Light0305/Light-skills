"""Shared routing/preparation must honor the real narrow domain contracts."""
from pathlib import Path
import sys
import tempfile
import unittest
import warnings
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skills/light-chart/scripts'))
import library
from chart_plan import data_digest
from figure_job import prepare_job
from evidence_tools import plan_evidence


class DomainIntegration(unittest.TestCase):
    def setUp(self):
        self.counts = pd.DataFrame({'gene':['g1','g2','g3'], 's1':[2,9,3],
                                    's2':[8,1,4], 's3':[4,6,9]})
        self.metadata = pd.DataFrame({'sample':['s3','s1','s2'], 'condition':['b','a','a']})
        self.count_chart = dict(intent='count_structure', unit='gene', values=['s1','s2','s3'],
            value_semantics='gene_counts', normalization='library_total_cpm', transform='log2_1plus_cpm',
            min_cpm=1, min_samples=2, heatmap_n=2, metadata_source='samples', sample_id='sample', annotations=['condition'])
        self.risks = pd.DataFrame({'id':['a','b'], 'name':['Study A','Study B'],
            'ae':[0,4], 'an':[10,16], 'be':[2,8], 'bn':[8,12]})
        self.risk_chart = dict(intent='two_arm_risk_evidence', unit='id', label='name',
            numerator_events='ae', numerator_non_events='an', comparator_events='be', comparator_non_events='bn',
            independent_binomial_working_model_explicit=True, confidence=.95, effect='RR', effect_scale='ratio',
            reference=1, risk_scale='linear', zero_event_policy='unavailable_no_correction')

    def count_job(self, metadata=None, chart=None, **options):
        tables={'counts':self.counts}
        if metadata is not False:
            tables['samples']=self.metadata if metadata is None else metadata
        return prepare_job(tables, dict(question='What descriptive structure do the supplied counts show?', source='counts',
            chart=self.count_chart if chart is None else chart, **options))

    def risk_job(self, data=None, **overrides):
        return prepare_job(self.risks if data is None else data, {'question':'What relative and absolute risks do the observed arms support?',
            'chart':{**self.risk_chart, **overrides}})

    def test_count_handoff_uses_exact_metadata_profile_and_source_digests(self):
        result=self.count_job()
        self.assertEqual((result['status'],result['backend']),('prepared','python'))
        diag=result['decisions']['main']['diagnostics']
        self.assertEqual(diag['metadata_ids_in_count_order'],['s1','s2','s3'])
        self.assertTrue(diag['profile_supplied'])
        self.assertEqual(diag['metadata_sha256'],data_digest(self.metadata))
        self.assertEqual(result['sources']['counts']['sha256'],data_digest(self.counts))
        self.assertEqual(result['field_mapping']['main']['metadata_source'],'samples')
        self.assertEqual(result['profiles']['samples']['columns']['sample']['type'],'identifier')
        self.assertFalse(result['implementation_adaptations'])

    def test_absent_or_misaligned_metadata_never_prepares(self):
        for meta in [False, self.metadata.iloc[:-1], self.metadata.assign(sample=['s3','s1','foreign']),
                     pd.concat([self.metadata,self.metadata.iloc[:1]])]:
            with self.subTest(meta=str(meta)):
                result=self.count_job(metadata=meta)
                self.assertEqual(result['status'],'needs_resolution')
                self.assertIsNone(result['decisions']['main']['recommended'])

    def test_duplicate_features_and_unknown_annotation_block(self):
        self.counts.loc[1,'gene']='g1'
        self.assertEqual(self.count_job()['status'],'needs_resolution')
        self.counts.loc[1,'gene']='g2'
        self.assertEqual(self.count_job(chart={**self.count_chart,'annotations':['guessed_batch']})['status'],'needs_resolution')

    def test_public_metadata_aware_evidence_and_job_keep_graph_blockers(self):
        panel=dict(id='a', source='counts', claim='c', role='primary', question='What varies?', chart=self.count_chart)
        spec=dict(question='What varies across samples?', claims={'c':{'boundary':'descriptive'}}, panels=[panel])
        direct=plan_evidence({'counts':self.counts,'samples':self.metadata},spec)
        self.assertEqual(direct['status'],'ready')
        self.assertEqual(direct['panels']['a']['decision']['diagnostics']['metadata_join'],'exact_one_to_one')
        missing=plan_evidence({'counts':self.counts},spec)
        self.assertEqual(missing['status'],'needs_resolution')
        self.assertTrue(any('metadata_source' in b for b in missing['blockers']))
        result=prepare_job({'counts':self.counts,'samples':self.metadata},spec)
        self.assertEqual(result['status'],'prepared')
        self.assertEqual(result['evidence']['status'],'ready')
        spec['claims']['c']['required_roles']=['boundary']
        result=prepare_job({'counts':self.counts,'samples':self.metadata},spec)
        self.assertEqual(result['status'],'needs_resolution')
        self.assertTrue(any('required evidence role' in b for b in result['blockers']))

    def test_clinical_zero_event_is_explicit_unavailable_with_preserved_arm_risks(self):
        result=self.risk_job()
        self.assertEqual((result['status'],result['backend']),('prepared','python'))
        diag=result['decisions']['main']['diagnostics']
        self.assertEqual(diag['study_ids'],['a','b'])
        self.assertEqual(diag['unavailable_rr_ids'],['a'])
        self.assertEqual(diag['recommended_risk_scale'],'linear')
        self.assertEqual(diag['observed_risk_evidence'][0]['risk_numerator'],0)
        self.assertEqual(diag['observed_risk_evidence'][0]['rr_status'],'unavailable_zero_events')
        self.assertEqual(diag['observed_risk_evidence'][1]['rr'],.5)
        self.assertEqual(diag['methods']['confidence'],.95)
        self.assertIn('Wilson',diag['methods']['risk_interval'])

    def test_selected_panel_digest_and_original_record_mapping_survive_reordered_indices(self):
        original=pd.DataFrame({'id':['a','b','c','d','e'], 'value':[1.,2.,3.,4.,5.]}, index=[91,5,91,0,77])
        panel=dict(id='p',source='measurements',claim='c',role='primary',question='What values are in the declared subset?',
                   select={'id':['e','a','c']},chart={'intent':'distribution','unit':'id','y':'value'})
        spec=dict(question='What is the observed subset distribution?',claims={'c':{'boundary':'descriptive'}},panels=[panel])
        for permutation in [[0,1,2,3,4],[4,1,0,3,2]]:
            with self.subTest(permutation=permutation):
                source=original.iloc[permutation].copy(deep=True)
                before=source.copy(deep=True)
                positions=[i for i,unit in enumerate(source['id']) if unit in {'a','c','e'}]
                expected=source.iloc[positions].reset_index(drop=True)
                result=prepare_job({'measurements':source},spec)
                self.assertEqual(result['status'],'prepared')
                evidence=result['evidence']['panels']['p']
                diagnostic=result['decisions']['p']['diagnostics']
                self.assertEqual(evidence['source_positions'],positions)
                self.assertEqual(evidence['selected_data_sha256'],data_digest(expected))
                self.assertEqual(diagnostic['source_sha256'],data_digest(expected))
                self.assertEqual(diagnostic['row_positions'],[0,1,2])
                source_digest=data_digest(source)
                self.assertEqual(evidence['selection_provenance']['source_sha256'],source_digest)
                self.assertEqual(set(evidence['origin_records']),{f'{source_digest}:{i}' for i in positions})
                self.assertEqual(result['field_mapping']['p']['selection']['source_positions'],positions)
                direct=plan_evidence({'measurements':source},spec)
                self.assertEqual(direct['panels']['p']['selected_data_sha256'],diagnostic['source_sha256'])
                single=prepare_job(source,dict(question='What are all original values?',chart=panel['chart']))
                self.assertEqual(single['decisions']['main']['diagnostics']['source_sha256'],source_digest)
                pd.testing.assert_frame_equal(source,before)

    def test_invalid_clinical_cells_reference_and_log_zero_block(self):
        for value in [-1, .5, float('nan'), 1+2j]:
            bad=self.risks.astype(object).copy();bad.loc[0,'ae']=value
            self.assertEqual(self.risk_job(bad)['status'],'needs_resolution')
        bad=self.risks.copy();bad.loc[0,['ae','an']]=0
        self.assertEqual(self.risk_job(bad)['status'],'needs_resolution')
        for override in [dict(reference=0),dict(risk_scale='log'),dict(effect='OR'),dict(pooled=True),
                         dict(independent_binomial_working_model_explicit=False),dict(effect_limits=[.8,1.2])]:
            self.assertEqual(self.risk_job(**override)['status'],'needs_resolution')

    def test_prediction_ids_validate_and_declared_mapping_survives_shuffle(self):
        data=pd.DataFrame({'case':[8,3,7], 'observed':['A','B','A'], 'forecast':['A','A','B']})
        chart=dict(intent='confusion-counts',unit='case',true='observed',predicted='forecast',
                   class_order=['B','A','C'],evaluation_split='test')
        spec=dict(question='Where do observed predictions fail?',chart=chart)
        a=prepare_job(data,spec);b=prepare_job(data.iloc[::-1],spec)
        self.assertEqual(a['status'],'prepared')
        self.assertEqual(a['decisions']['main']['diagnostics']['counts'],b['decisions']['main']['diagnostics']['counts'])
        self.assertEqual(a['field_mapping']['main']['roles']['predicted'],'forecast')
        data.loc[1,'case']=8
        self.assertEqual(prepare_job(data,spec)['status'],'needs_resolution')

    def test_declared_individual_symbols_and_legacy_multi_symbol_resolve(self):
        for symbol in ['analyze_count_structure','align_sample_metadata','expression_heatmap','pca_scores',
                       'analyze_2x2','forest_panel','arm_risk_panel','confusion_counts','prepare_count_matrix',
                       'ordered_sweep','plot_budget_sweep','plot_signal_window','compare_revisions']:
            result=library.route(symbol,backend='python',limit=1)
            self.assertEqual(result['status'],'implementation_found',symbol)
            self.assertIn(symbol,result['symbol_coverage'])
        self.assertFalse(library.route('unrelated_analyze_2x2_suffix',backend='python')['entrypoints'])

    def test_fulltext_function_mention_never_certifies_a_callable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'helper.py').write_text('def real_function():\n    """analyze_2x2 and unrelated_construct"""\n',encoding='utf8')
            row=dict(id='real',title='Example',kind='implementation',path='helper.py',status='callable',
                     symbol='real_function',backend='python',concepts=['real'])
            with patch.object(library,'ROOT',root),patch.object(library,'_index',return_value=[row]),\
                 patch.object(library,'_vocabulary',return_value={'unrelated_construct':[]}):
                self.assertFalse(library.route('analyze_2x2')['entrypoints'])
                self.assertIn('unrelated_construct',library.route('unrelated_construct')['unimplemented_concepts'])

    def test_narrow_modules_do_not_certify_unrelated_generic_constructs(self):
        for query in ['signed float heatmap','trend','adjusted hazard ratio forest','pooled odds ratio forest']:
            result=library.route(query,backend='python')
            self.assertFalse(any(r['path'].endswith(('omics_plots.py','effect_plots.py','computational_plots.py'))
                                 for r in result['entrypoints']),query)
        pca = library.route('PCA',backend='python')
        self.assertEqual(pca['status'],'implementation_found')
        self.assertEqual([r['symbol'] for r in pca['entrypoints']],['pca_scores'])

    def test_count_parameterized_transform_and_count_threshold_are_prepared(self):
        chart = {k:v for k,v in self.count_chart.items() if k != 'min_cpm'}
        chart.update(transform='log2_cpm',pseudocount=.5,min_count=3)
        result = self.count_job(chart=chart)
        self.assertEqual(result['status'],'prepared')
        parameters = result['decisions']['main']['diagnostics']['parameters']
        self.assertEqual(parameters['pseudocount'],.5)
        self.assertEqual(parameters['eligibility_basis'],'count')
        self.assertEqual(parameters['min_count'],3)
        for override in [dict(min_cpm=1),dict(transform='log2_1plus_cpm'),dict(pseudocount=0),dict(min_count=None)]:
            with self.subTest(override=override):
                self.assertEqual(self.count_job(chart={**chart,**override})['status'],'needs_resolution')

    def test_mixed_concepts_and_symbols_ignore_small_display_limit(self):
        result=library.route('computational-sweep confusion-counts count-structure two-arm-counts',backend='python',limit=1)
        self.assertEqual(result['status'],'implementation_found')
        self.assertFalse(result['unimplemented_concepts'])
        self.assertTrue(result['limit_exceeded_for_coverage'])
        result=library.route('analyze_2x2 expression_heatmap plot_budget_sweep',backend='python',limit=1)
        self.assertEqual(len(result['symbol_coverage']),3)
        self.assertEqual(len(result['entrypoints']),3)

    def test_explicit_backend_never_silently_switches_to_new_python_helpers(self):
        result=self.count_job(backend='r')
        self.assertEqual(result['backend'],'r')
        self.assertEqual(result['status'],'adaptation_required')
        self.assertTrue(result['implementation_adaptations'])
        result=library.route('analyze_2x2 confusion-counts',backend='r')
        self.assertFalse(result['entrypoints'])
        self.assertIn('confusion-counts',result['unimplemented_concepts'])
        self.assertIn('analyze_2x2',result['unimplemented_symbols'])

    def test_raw_and_supplied_interval_trajectories_use_their_real_callables(self):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        sys.path.insert(0, str(ROOT/'skills/light-chart/assets'))
        from paper_patterns import trend_lines
        from editorial import interval_trajectory
        data=pd.DataFrame({'x':[7.,1.,3.],'y':[9.,2.,5.]})
        chart=dict(intent='trend',x='x',y='y',ordered=True)
        result=prepare_job(data,dict(question='How do the observations change?',chart=chart))
        self.assertEqual(result['status'],'prepared')
        chosen=result['decisions']['main']['recommended']['resources']['entrypoints']
        self.assertEqual([r['symbol'] for r in chosen],['trend_lines'])
        fig,ax=trend_lines(data.x,[data.y],['Observed'])
        np.testing.assert_array_equal(ax.lines[0].get_xdata(),[1.,3.,7.])
        np.testing.assert_array_equal(ax.lines[0].get_ydata(),[2.,5.,9.])
        self.assertFalse(ax.collections,'Raw values must not acquire invented interval fills')
        plt.close(fig)
        data=data.assign(lo=[8.,1.,4.],hi=[10.,3.,6.])
        result=prepare_job(data,dict(question='How do supplied estimates change?',chart={**chart,'lower':'lo','upper':'hi'}))
        self.assertEqual(result['status'],'prepared')
        self.assertEqual(result['decisions']['main']['diagnostics']['constructor_symbol'],'interval_trajectory')
        fig,ax=plt.subplots()
        line=interval_trajectory(ax,data.x,data.y,data.lo,data.hi,color='blue')
        np.testing.assert_array_equal(line.get_xdata(),[1.,3.,7.])
        self.assertEqual(len(ax.collections),1)
        plt.close(fig)

    def test_trajectory_duplicate_categorical_complex_and_partial_bounds_do_not_prepare(self):
        chart=dict(intent='trend',x='x',y='y',ordered=True)
        valid=pd.DataFrame({'x':[1.,3.,7.],'y':[2.,5.,9.]})
        for data in [valid.assign(x=[1.,1.,7.]),valid.assign(x=['pre','during','post']),
                     valid.assign(x=[1+2j,3,7]),valid.assign(y=[True,False,True])]:
            with self.subTest(data=str(data)):
                result=prepare_job(data,dict(question='Measured ordered observations?',chart=chart))
                self.assertEqual(result['status'],'needs_resolution')
                self.assertIsNone(result['decisions']['main']['recommended'])
        result=prepare_job(valid.assign(lo=[1.,4.,8.]),dict(question='Supplied bounds?',chart={**chart,'lower':'lo'}))
        self.assertEqual(result['status'],'needs_resolution')

    def test_repeated_unit_trajectory_preserves_keys_and_declares_unequal_raw_grid_gap(self):
        data=pd.DataFrame({'unit':['b','a','b','a'],'x':[4.,1.,1.,4.],'y':[8.,2.,3.,7.]})
        chart=dict(intent='trend',unit='unit',x='x',y='y',ordered=True)
        result=prepare_job(data,dict(question='Within-unit observed paths?',chart=chart))
        self.assertEqual(result['status'],'prepared')
        traces=result['decisions']['main']['diagnostics']['trajectory_traces']
        self.assertEqual({t['identity']:t['positions_in_used_rows'] for t in traces},{'b':[2,0],'a':[1,3]})
        np.testing.assert_array_equal(data.y,[8.,2.,3.,7.])
        unequal=data.copy();unequal.loc[0,'x']=5
        blocked=prepare_job(unequal,dict(question='Within-unit observed paths?',chart=chart))
        self.assertEqual(blocked['status'],'needs_resolution')
        self.assertTrue(any('shared x grid' in b for b in blocked['blockers']))
        interval=unequal.assign(lo=unequal.y-1,hi=unequal.y+1)
        self.assertEqual(prepare_job(interval,dict(question='Supplied per-unit estimates?',chart={**chart,'lower':'lo','upper':'hi'}))['status'],'prepared')

    def test_strict_duplicate_domain_evidence_cannot_be_laundered_by_prose(self):
        pred=pd.DataFrame({'id':['a','b','c'],'actual':['A','B','A'],'forecast':['A','A','B']})
        confusion=dict(intent='confusion-counts',unit='id',true='actual',predicted='forecast',class_order=['A','B'],evaluation_split='test')
        for data,chart,fields in [(self.risks,self.risk_chart,{'ae','an','be','bn'}),
                                  (pred,confusion,{'actual','forecast'})]:
            for prose in [False,True]:
                panels=[dict(id=k,source='data',role=role,question=role,claim='c',chart=dict(chart))
                        for k,role in [('a','primary'),('b','boundary')]]
                if prose:
                    panels[0]['unique_inference']='Describes one interpretation'
                    panels[1]['unique_inference']='Describes another interpretation'
                    panels[1]['chart']['view']='Ignored arbitrary description must not change the construction'
                result=prepare_job(data,dict(question='Which evidence supports the claim?',claims={'c':{'boundary':'Descriptive'}},
                    panels=panels,require_complementarity=True))
                self.assertEqual(result['status'],'needs_resolution')
                pair=result['evidence']['complementarity'][0]
                self.assertEqual(set(pair['shared_measurements']),fields)
                self.assertTrue(pair['same_declared_encoding'])

    def impedance_inputs(self):
        data=pd.DataFrame({'spectrum':['A','B','A','B','B'],'hz':[10.,1.,1.,20.,5.],
                           're':[1.,3.,2.,1.,2.],'im':[.1,-2.,-1.,.2,-1.], 'row_id':['a','b','c','d','e']})
        chart=dict(intent='impedance',spectrum='spectrum',frequency='hz',real='re',imaginary='im',
                   frequency_unit='Hz',impedance_unit='ohm',imaginary_convention='physical_signed',order=['B','A'])
        return data,chart

    def test_impedance_actual_mapping_profiles_sort_and_signed_rows_are_preserved(self):
        data,chart=self.impedance_inputs();original=data.copy(deep=True)
        result=prepare_job(data,dict(question='Where do measured spectra differ?',chart=chart))
        self.assertEqual((result['status'],result['backend']),('prepared','python'))
        diag=result['decisions']['main']['diagnostics']
        self.assertEqual(diag['source_positions_in_frequency_order'],[1,4,3,2,0])
        self.assertEqual(diag['spectrum_rows'],{'B':3,'A':2})
        self.assertEqual(diag['positive_physical_imaginary_points'],{'B':1,'A':1})
        self.assertEqual(result['field_mapping']['main']['roles']['imaginary'],'im')
        self.assertEqual(result['profiles']['data']['columns']['spectrum']['type'],'identifier')
        self.assertEqual(set(result['decisions']['main']['profile_context']['measurement_profiles']),{'hz','re','im'})
        pd.testing.assert_frame_equal(data,original)

    def test_impedance_invalid_semantics_values_bounds_and_native_backend(self):
        data,chart=self.impedance_inputs()
        for override in [dict(frequency_unit='kHz'),dict(impedance_unit='ohm cm2'),dict(imaginary_convention='negative_imag'),
                         dict(spectrum=None),dict(view='unrecognized'),dict(fit='Randles'),dict(frequency_limits=[2,30]),
                         dict(nyquist_limits=[0,2,-1,1]),dict(phase_limits=[-10,10])]:
            with self.subTest(override=override):
                self.assertEqual(prepare_job(data,dict(question='Measured impedance?',chart={**chart,**override}))['status'],'needs_resolution')
        for changed in [data.assign(hz=[1,1,1,20,5]),data.assign(im=[1+2j,-2,-1,.2,-1]),data.assign(re=[True]*5)]:
            self.assertEqual(prepare_job(changed,dict(question='Measured impedance?',chart=chart))['status'],'needs_resolution')
        zero=data.copy();zero.loc[0,['re','im']]=0
        self.assertEqual(prepare_job(zero,dict(question='Measured impedance?',chart=chart))['status'],'needs_resolution')
        self.assertEqual(prepare_job(zero,dict(question='Measured geometry?',chart={**chart,'view':'nyquist'}))['status'],'prepared')
        native=prepare_job(data,dict(question='Measured impedance?',chart=chart,backend='r'))
        self.assertEqual((native['status'],native['backend']),('adaptation_required','r'))
        self.assertTrue(native['implementation_adaptations'])

    def test_distinct_validated_impedance_views_can_be_complementary(self):
        data,chart=self.impedance_inputs()
        panels=[dict(id=k,source='data',role=role,question=gain,claim='c',chart={**chart,'view':view},unique_inference=gain)
                for k,role,view,gain in [('a','primary','nyquist','Complex-plane geometry'),('b','boundary','bode','Frequency localization')]]
        result=prepare_job(data,dict(question='Where do the spectra differ?',claims={'c':{'boundary':'Measured observations only'}},panels=panels,require_complementarity=True))
        self.assertEqual(result['status'],'prepared')
        self.assertFalse(result['evidence']['complementarity'][0]['same_declared_encoding'])
        self.assertTrue(result['evidence']['complementarity'][0]['review_required'])
        for symbol in ['prepare_impedance','plot_nyquist','plot_bode','trend_lines']:
            self.assertEqual(library.route(symbol,backend='python')['status'],'implementation_found')

    def test_text_language_selection_does_not_confuse_statistical_r_or_style(self):
        for query in ['Python ggplot style heatmap','Python scatter plot of Pearson r','Python heatmap of Pearson r']:
            self.assertEqual(library.route(query)['backend'],'python')
        self.assertIsNone(library.route('scatter plot of Pearson r')['backend'])
        for query in ['R heatmap','R','请用R绘图','using R for heatmap','R语言热图']:
            self.assertEqual(library.route(query)['backend'],'r',query)
        self.assertEqual(library.route('Python heatmap',backend='r')['backend'],'r')

    def test_direct_trajectory_constructors_reject_complex_and_boolean_before_cast(self):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        sys.path.insert(0,str(ROOT/'skills/light-chart/assets'))
        from paper_patterns import trend_lines
        from editorial import interval_trajectory
        x=np.array([0.,1.,2.]);y=np.array([2.,3.,4.]);lo=y-1;hi=y+1
        cases=[dict(x=x+5j),dict(y=y+5j),dict(lo=lo+5j),dict(hi=hi+5j),
               dict(x=np.array([False,True,False])),dict(y=np.array([True,False,True])),
               dict(x=np.array([0,1+2j,2],dtype=object))]
        for changes in cases:
            inputs=dict(x=x,y=y,lo=lo,hi=hi);inputs.update(changes)
            with self.subTest(changes=str(changes)),warnings.catch_warnings(record=True) as emitted:
                warnings.simplefilter('always')
                with self.assertRaisesRegex(ValueError,'real numeric'):
                    trend_lines(inputs['x'],[inputs['y']],['Observed'],[inputs['lo']],[inputs['hi']])
                fig,ax=plt.subplots()
                try:
                    with self.assertRaisesRegex(ValueError,'real numeric'):
                        interval_trajectory(ax,inputs['x'],inputs['y'],inputs['lo'],inputs['hi'],color='blue')
                    self.assertFalse(ax.lines)
                finally:
                    plt.close(fig)
                self.assertFalse(emitted,'Rejected inputs must not first emit a lossy-cast warning')

    def test_preparation_retains_complex_inputs_without_lossy_profile_statistics(self):
        data,chart=self.impedance_inputs()
        data['im']=data['im'].astype(complex)+2j
        source=data.copy(deep=True)
        with warnings.catch_warnings(record=True) as emitted:
            warnings.simplefilter('always')
            result=prepare_job(data,dict(question='Explicit components are required?',chart=chart))
        self.assertEqual(result['status'],'needs_resolution')
        self.assertEqual(result['profiles']['data']['unsupported_complex_columns'],['im'])
        self.assertNotIn('mean',result['profiles']['data']['columns']['im'])
        self.assertFalse(any('Casting complex' in str(w.message) for w in emitted))
        pd.testing.assert_frame_equal(data,source)

    def test_direct_trajectory_constructors_reject_mixed_boolean_float_lists(self):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        sys.path.insert(0,str(ROOT/'skills/light-chart/assets'))
        from paper_patterns import trend_lines
        from editorial import interval_trajectory
        for changes in [dict(x=[True,2.]),dict(y=[True,20.])]:
            inputs=dict(x=[1.,2.],y=[10.,20.],lo=[0.,0.],hi=[30.,40.]);inputs.update(changes)
            with self.subTest(changes=changes),warnings.catch_warnings(record=True) as emitted:
                warnings.simplefilter('always')
                with self.assertRaisesRegex(ValueError,'real numeric'):
                    trend_lines(inputs['x'],[inputs['y']],['Observed'],[inputs['lo']],[inputs['hi']])
                fig,ax=plt.subplots()
                try:
                    with self.assertRaisesRegex(ValueError,'real numeric'):
                        interval_trajectory(ax,inputs['x'],inputs['y'],inputs['lo'],inputs['hi'],color='blue')
                    self.assertFalse(ax.lines)
                finally:
                    plt.close(fig)
                self.assertFalse(emitted)

    def test_arbitrary_unique_ids_do_not_establish_sampling_independence(self):
        data=pd.DataFrame({'id':['technical-a','technical-b','technical-c'],'x':[1.,2.,4.],'y':[2.,3.,6.]})
        result=prepare_job(data,dict(question='What is the recorded path?',chart=dict(intent='trend',unit='id',x='x',y='y',ordered=True)))
        self.assertEqual(result['status'],'prepared')
        diag=result['decisions']['main']['diagnostics']
        self.assertEqual(diag['units'],3)
        self.assertFalse(diag['repeated_units'])
        self.assertTrue(diag['rows_have_unique_unit_ids'])
        self.assertIsNone(diag['rows_are_independent_units'])
        self.assertEqual(diag['sampling_independence'],'not_established_by_identity')
        self.assertTrue(any('sampling independence' in w for w in result['warnings']))

    def test_backend_is_selected_from_real_callables_and_mixed_native_figure_blocks(self):
        data=pd.DataFrame({'id':['a','b','c'],'x':[1.,2.,4.],'y':[2.,3.,6.],'event':[1,0,1]})
        trend=dict(intent='trend',x='x',y='y',ordered=True)
        survival=dict(intent='survival',unit='id',time='x',event='event')
        one=prepare_job(data,dict(question='Observed path?',chart=trend))
        self.assertEqual((one['status'],one['backend']),('prepared','python'))
        native=prepare_job(data,dict(question='Unadjusted survival?',chart=survival))
        self.assertEqual((native['status'],native['backend']),('prepared','r'))
        self.assertEqual(native['decisions']['main']['recommended']['resources']['backend'],'r')
        panels=[dict(id='a',source='data',role='primary',claim='c',question='Observed ordered values?',chart=trend),
                dict(id='b',source='data',role='boundary',claim='c',question='Event and censoring?',chart=survival)]
        graph=dict(question='What do these records show?',claims={'c':{'boundary':'Descriptive only'}},panels=panels)
        mixed=prepare_job(data,graph)
        self.assertEqual(mixed['status'],'needs_resolution')
        self.assertTrue(any('mixed Python/R' in b for b in mixed['blockers']))
        explicit=prepare_job(data,{**graph,'backend':'python'})
        self.assertEqual(explicit['backend'],'python')
        self.assertEqual(explicit['status'],'adaptation_required')
        self.assertTrue(any(a['panel']=='b' for a in explicit['implementation_adaptations']))


if __name__=='__main__':
    unittest.main()
