"""Drawing controls must expose dense observations without moving any vertex."""
import sys
import unittest
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/light-chart/scripts'))
from computational_plots import plot_budget_sweep,ordered_sweep
from impedance_plots import prepare_impedance,plot_nyquist,plot_bode

class DenseCurveDrawing(unittest.TestCase):
    def tearDown(self):plt.close('all')
    def test_repeat_style_changes_marks_without_subsampling_or_mean_change(self):
        data=pd.DataFrame([dict(group=s,seed=r,budget=x,score=s+r+x/100)
             for s in [1,2] for r in [11,29,47] for x in [5,15,40,100,240]])
        enc={1:dict(color='navy',marker='o',linestyle='-'),2:dict(color='sienna',marker='s',linestyle='--')}
        fig,ax=plt.subplots()
        result=plot_budget_sweep(ax,data,x='budget',y='score',series='group',repeat='seed',series_order=[1,2],encodings=enc,
             run_style=dict(alpha=.9,linewidth=.7,zorder=2),mean_style=dict(markersize=4.8,markerfacecolor='white',zorder=4))
        expected=ordered_sweep(data,x='budget',y='score',series='group',repeat='seed',series_order=[1,2])
        for name in [1,2]:
            self.assertEqual(len(result['run_artists'][name]),3)
            for i,line in enumerate(result['run_artists'][name]):
                np.testing.assert_array_equal(line.get_xdata(),expected['x'])
                np.testing.assert_array_equal(line.get_ydata(),expected['values'][name][i])
                self.assertEqual(line.get_alpha(),.9)
            np.testing.assert_array_equal(result['artists'][name].get_ydata(),expected['values'][name].mean(0))
            self.assertGreater(result['artists'][name].get_zorder(),result['run_artists'][name][0].get_zorder())
        self.assertEqual(result['repeat_ids'],[11,29,47])

    def test_run_style_cannot_introduce_coordinate_transform_or_hide_all_runs(self):
        data=pd.DataFrame(dict(group=['a','a'],seed=[1,1],budget=[1,2],score=[.2,.3]))
        for style in [dict(markevery=2),dict(transform='axes'),dict(alpha=0),dict(markersize=True),dict(linewidth=float('nan'))]:
            with self.subTest(style=style),self.assertRaises(ValueError):
                plot_budget_sweep(plt.subplots()[1],data,x='budget',y='score',series='group',repeat='seed',series_order=['a'],
                     encodings={'a':dict(color='navy',marker='o',linestyle='-')},run_style=style)

    def test_coincident_spectra_remain_exact_with_distinct_marker_footprints(self):
        data=pd.DataFrame(dict(s=['A']*3+['B']*3,f=[1,10,100]*2,re=[3,2,1]*2,im=[-4,-2,.2]*2))
        result=prepare_impedance(data,spectrum='s',frequency='f',real='re',imag='im',unit='ohm')
        before=result.rows.copy(deep=True)
        enc={'A':dict(color='navy',marker='o',linestyle='-',markersize=3.1,markerfacecolor='none',zorder=3),
             'B':dict(color='sienna',marker='s',linestyle='--',markersize=1.6,markerfacecolor='sienna',zorder=4)}
        fig,axes=plt.subplots(1,3)
        ny=plot_nyquist(axes[0],result,encodings=enc)
        bode=plot_bode(axes[1],axes[2],result,encodings=enc)
        for mapping in [ny['lines'],{n:p[0] for n,p in bode['lines'].items()},{n:p[1] for n,p in bode['lines'].items()}]:
            np.testing.assert_array_equal(mapping['A'].get_xydata(),mapping['B'].get_xydata())
            self.assertEqual(len(mapping['A'].get_xydata()),3)
            self.assertGreater(mapping['A'].get_markersize(),mapping['B'].get_markersize())
        pd.testing.assert_frame_equal(result.rows,before)

    def test_impedance_style_rejects_invisible_or_nonreal_marks(self):
        data=pd.DataFrame(dict(s=['A','A'],f=[1,10],re=[1,2],im=[-1,-2]))
        result=prepare_impedance(data,spectrum='s',frequency='f',real='re',imag='im',unit='ohm')
        for style in [dict(markersize=0),dict(alpha=0),dict(linewidth=True),dict(markeredgewidth=-1),dict(zorder=1j)]:
            with self.subTest(style=style),self.assertRaises(ValueError):
                plot_nyquist(plt.subplots()[1],result,encodings={'A':dict(color='navy',marker='o',linestyle='-',**style)})

if __name__=='__main__':unittest.main()
