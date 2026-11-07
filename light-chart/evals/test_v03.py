"""Meaningful data-integrity regressions for new domain capabilities."""
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/light-chart/scripts'))
from field_tools import grid_field,scalar_field
from table_tools import Column,best_cells,scientific_table,require_table_fit,to_latex
from preflight import preflight
from library import search


class DataIntegrity(unittest.TestCase):
    def test_native_latex_escapes_text_and_ranks_original_values(self):
        rows=[{'name':'A&B_50%','v':.771,'display':'0.77 ± 0.04'},
              {'name':'B','v':.771,'display':'0.77 ± 0.02'},
              {'name':'C','v':.7709,'display':'0.77 ± 0.01'},
              {'name':'Not reported','v':None,'display':'not a value'}]
        cols=[Column('name','Method',.4,align='left'),
              Column('v','Score ↑',.6,better='max',display_key='display')]
        tex=to_latex(rows,cols,rank=True,spanners=[('Results & metrics',1,2)])
        self.assertIn(r'A\&B\_50\%',tex)
        self.assertIn(r'Results \& metrics',tex)
        self.assertEqual(tex.count(r'\textbf{'),2)
        self.assertIn(r'0.77 \(\pm\) 0.01',tex)
        self.assertIn(r'Not reported & \textemdash{}',tex)
        self.assertNotIn('not a value',tex)
        self.assertNotIn(r'\begin{figure}',tex)
        self.assertNotIn(r'\resizebox',tex)
        with self.assertRaises(ValueError):
            to_latex([{'name':'Infinite','v':float('inf'),'display':'1.0'}],cols)

    def test_grid_reorders_coordinates_and_values_together_without_filling(self):
        z=np.array([[1,np.nan,3],[4,5,6.]])
        f=grid_field([8,2,0],[5,-1],z,limits=[0,6])
        np.testing.assert_array_equal(f.x,[0,2,8])
        np.testing.assert_array_equal(f.y,[-1,5])
        np.testing.assert_equal(f.z,[[6,5,4],[3,np.nan,1]])
        np.testing.assert_equal(z,[[1,np.nan,3],[4,5,6]])
        fig,ax=plt.subplots();m=scalar_field(ax,f)
        # Nonuniform centers produce nonuniform cells, not equal-width pixels.
        np.testing.assert_allclose(np.diff(m.get_coordinates()[0,:,0]),[2,4,6])
        self.assertEqual(np.ma.count_masked(m.get_array()),1)
        plt.close(fig)

    def test_invalid_grids_and_clipping_fail(self):
        for x,z,limits in [([0,0,1],np.ones((2,3)),[0,2]),
                           ([0,2,1],np.ones((2,3)),[0,2]),
                           ([0,1,2],np.ones((3,2)),[0,2]),
                           ([0,1,2],np.ones((2,3)),[0,.9])]:
            with self.assertRaises(ValueError):grid_field(x,[0,1],z,limits=limits)

    def test_rank_raw_values_ties_and_na_separately_from_display(self):
        rows=[{'name':'A','mean':.771,'display':'0.77 ± 0.04','loss':None},
              {'name':'B','mean':.771,'display':'0.77 ± 0.02','loss':2},
              {'name':'C','mean':.7709,'display':'0.77 ± 0.01','loss':1}]
        cols=[Column('name','Method',.3,align='left'),
              Column('mean','Score ↑',.4,better='max',display_key='display'),
              Column('loss','Loss ↓',.3,better='min')]
        self.assertEqual(best_cells(rows,cols),{(0,1),(1,1),(2,2)})
        fig,ax=plt.subplots(figsize=(6,3))
        cells=scientific_table(ax,rows,cols,rank=True)
        self.assertEqual(cells[2]['text'],'—')
        self.assertFalse(cells[7]['best']) # Rounded display tie does not create raw tie.
        require_table_fit(ax,cells)
        plt.close(fig)

    def test_crowded_table_is_rejected_in_actual_renderer(self):
        fig,ax=plt.subplots(figsize=(2,1))
        cols=[Column('name','Method',.5),Column('v','Value',.5)]
        cells=scientific_table(ax,[{'name':'A very long unbreakable method name','v':1}],cols)
        with self.assertRaises(ValueError):require_table_fit(ax,cells)
        plt.close(fig)

    def test_preflight_does_not_execute_declared_helpers(self):
        with tempfile.TemporaryDirectory(prefix='light chart 中文 ') as d:
            p=Path(d);marker=p/'must-not-exist.txt'
            script=p/'plot.py';support=p/'support.py'
            script.write_text('from support import style\n',encoding='utf-8')
            support.write_text(f'from pathlib import Path\nPath({str(marker)!r}).write_text("bad")\n',encoding='utf-8')
            r=preflight(script,support=[support],formats=['png'])
            self.assertFalse(marker.exists())
            self.assertEqual(len(r['scope']),2)
            self.assertFalse(any(x['level']=='FAIL' and x['check_id']=='EXPORT-VECTOR' for x in r['findings']))
            script.write_text('from matplotlib.colors import Normalize\nx=Normalize(vmin=2,vmax=0)\n',encoding='utf-8')
            r=preflight(script,formats=['png'])
            self.assertFalse(r['ready_to_render'])
            self.assertTrue(any(x['check_id']=='COLOR-LIMIT-ORDER' for x in r['findings']))

    def test_domain_search_finds_shipped_workflows_and_external_data_boundary(self):
        hits=search('生存',backend='r')
        self.assertTrue(any('domain-workflows' in h['path'] for h in hits))
        hits=search('freq_prior',kind='source-pattern')
        self.assertEqual(len(hits),1)
        self.assertEqual(hits[0]['availability'],'external_file_required')

if __name__=='__main__':unittest.main()
