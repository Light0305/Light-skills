"""Behavioral coverage of task preparation, retrieval completeness and evidence."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/light-chart/scripts'))
import library
from figure_job import prepare_job
from evidence_tools import plan_evidence


class BackboneBehavior(unittest.TestCase):
    def test_display_limit_cannot_hide_implemented_parts_of_a_mixed_task(self):
        result=library.route('volcano heatmap',backend='python',limit=1)
        self.assertEqual(result['status'],'implementation_found')
        self.assertFalse(result['unimplemented_concepts'])
        self.assertTrue(result['limit_exceeded_for_coverage'])
        covered=set().union(*(set(r['concepts']) for r in result['entrypoints']))
        self.assertTrue({'volcano','heatmap'} <= covered)

    def test_body_mention_does_not_certify_an_implementation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);(path/'heatmap.py').write_text('def draw_heatmap():\n    """phantom"""\n',encoding='utf-8')
            row={'id':'heatmap','title':'Matrix','kind':'implementation','path':'heatmap.py',
                 'symbol':'draw_heatmap','backend':'python','concepts':['heatmap']}
            with patch.object(library,'ROOT',path),patch.object(library,'_index',return_value=[row]),\
                 patch.object(library,'_vocabulary',return_value={'phantom':[],'heatmap':[]}):
                result=library.route('phantom',backend='python')
        self.assertFalse(result['entrypoints'])
        self.assertIn('phantom',result['unimplemented_concepts'])
        self.assertNotEqual(result['status'],'implementation_found')

    def test_blank_or_unknown_task_does_not_select_arbitrary_implementations(self):
        self.assertEqual(library.route('')['status'],'no_match')
        self.assertFalse(library.route('draw completely_unknown_squiggle')['entrypoints'])

    def test_gallery_example_is_not_an_arbitrary_data_adapter(self):
        result=library.route('ECDF',backend='python')
        self.assertNotEqual(result['status'],'implementation_found')
        self.assertIn('ecdf',result['unimplemented_concepts'])
        self.assertTrue(any(r.get('status')=='runnable_example' for r in result['related']))

    def test_pca_does_not_claim_umap_or_loading_arrow_biplot(self):
        result=library.route('PCA UMAP biplot',backend='r',limit=1)
        self.assertEqual(result['status'],'partial_implementation')
        self.assertNotIn('pca',result['unimplemented_concepts'])
        self.assertIn('umap',result['unimplemented_concepts'])
        self.assertIn('biplot',result['unimplemented_concepts'])

    def test_job_runs_actual_profile_and_keeps_rows_and_question(self):
        data=pd.DataFrame({'subject':['a','b','a','b'],'phase':['pre','pre','post','post'],'v':[2.,4.,3.,8.]})
        before=data.copy(deep=True)
        result=prepare_job(data,{'question':'How does each subject change?', 'backend':'python',
            'chart':{'intent':'change','unit':'subject','condition':'phase','y':'v','order':['pre','post']}})
        self.assertEqual(result['status'],'prepared')
        self.assertEqual(result['decisions']['main']['recommended']['construction'],'paired-change')
        self.assertEqual(result['profiles']['data']['pair_summary']['n_entities'],2)
        self.assertEqual(result['field_mapping']['main']['roles']['unit'],'subject')
        self.assertTrue(any(r['source']=='SciPilot' and r['operation']=='executed' for r in result['source_use']))
        self.assertFalse(any(r['source']=='FigMirror' and r['operation'].startswith('executed') for r in result['source_use']))
        pd.testing.assert_frame_equal(data,before)

    def test_blank_question_blocks_before_recommendation(self):
        result=prepare_job(pd.DataFrame({'v':[1.,2.,3.]}),{'chart':{'intent':'distribution','y':'v'}})
        self.assertEqual(result['status'],'needs_resolution')
        self.assertFalse(result['decisions'])
        self.assertFalse(any(r['source']=='nature-figure' for r in result['source_use']))

    def test_declared_numeric_identifier_cannot_enter_measurement_matrix(self):
        data=pd.DataFrame({'id':[101,102],'v':[3.,4.]})
        result=prepare_job(data,{'question':'What varies?',
            'chart':{'intent':'matrix','values':['id','v']},
            'profiles':{'data':{'id_cols':['id']}}})
        self.assertEqual(result['status'],'needs_resolution')
        self.assertTrue(any('identifiers' in b for b in result['blockers']))

    def test_nested_backend_conflict_is_not_silently_overridden(self):
        result=prepare_job(pd.DataFrame({'v':[1.,2.]}),{'question':'What varies?','backend':'r',
            'chart':{'intent':'distribution','y':'v','backend':'python'}})
        self.assertEqual(result['status'],'needs_resolution')
        self.assertTrue(any('backend' in b for b in result['blockers']))

    def test_domain_candidate_routes_to_required_backend_without_overriding_choice(self):
        data=pd.DataFrame({'id':['a','b','c'],'u':[1.,3.,2.],'v':[2.,1.,3.]})
        chart={'intent':'ordination','unit':'id','values':['u','v'],
               'transform':'hellinger','method':'pca','value_semantics':'cover_class'}
        automatic=prepare_job(data,{'question':'How do communities differ?','chart':chart})
        self.assertEqual(automatic['backend'],'r')
        self.assertEqual(automatic['status'],'prepared')
        explicit=prepare_job(data,{'question':'How do communities differ?','backend':'python','chart':chart})
        self.assertEqual(explicit['backend'],'python')
        self.assertEqual(explicit['status'],'adaptation_required')
        self.assertTrue(explicit['implementation_adaptations'])

    def test_contained_matrix_companion_requires_actual_inference_explanation(self):
        data=pd.DataFrame({'id':['a','b','c'],'x':[1.,2.,3.],'y':[3.,2.,1.]})
        spec={'question':'How do the variables differ?', 'claims':{'c':{'boundary':'descriptive'}},
            'panels':[{'id':'matrix','source':'one','role':'primary','question':'What are the patterns?',
                'claim':'c','chart':{'intent':'matrix','unit':'id','values':['x','y']}},
                {'id':'raw','source':'one','role':'support','question':'What are the x values?',
                 'claim':'c','chart':{'intent':'distribution','unit':'id','y':'x'}}]}
        result=plan_evidence({'one':data},spec)
        self.assertEqual(result['status'],'ready')
        self.assertEqual(result['complementarity'][0]['relationship'],'contained_measurements')
        self.assertTrue(result['complementarity'][0]['review_required'])
        strict=plan_evidence({'one':data},{**spec,'require_complementarity':True})
        self.assertEqual(strict['status'],'needs_resolution')
        for panel in spec['panels']:
            panel['unique_inference']='Pattern across variables' if panel['id']=='matrix' else 'Absolute x magnitude absent from normalized matrix'
        self.assertEqual(plan_evidence({'one':data},{**spec,'require_complementarity':True})['status'],'ready')


if __name__=='__main__':unittest.main()
