"""Rendered plot budgets must hold after Matplotlib applies data aspect."""
from pathlib import Path
import sys
import unittest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/light-chart/scripts'))
from composition import compose, LayoutError
from editorial import figure_style
from omics_plots import pca_scores


class RenderedCompositionGeometry(unittest.TestCase):
    def tearDown(self):
        plt.close('all')

    def draw_pca(self, options, extreme=False):
        layout=compose((140,100),[['scores']],panels={'scores':options})
        scores=pd.DataFrame({'PC1':[-50.,0.,50.] if extreme else [-4.,0.,4.],
                             'PC2':[0.,.5,-.5] if extreme else [0.,1.,-1.]},index=['a','b','c'])
        meta=pd.DataFrame({'sample':['c','a','b'],'condition':['C','C','D']})
        drawn=pca_scores(layout.axes['scores'],scores,meta,sample_id='sample',
            explained_variance_ratio=[.7,.2],color='condition',colors={'C':'#123456','D':'#AB6723'})
        return layout,scores,drawn

    def test_extreme_equal_data_aspect_refuses_explicit_and_default_budgets(self):
        with figure_style():
            for options in ({'min_plot_mm':[30,20]},{}):
                with self.subTest(options=options):
                    layout,scores,drawn=self.draw_pca(options,extreme=True)
                    ax=layout.axes['scores'];font_size=ax.xaxis.label.get_fontsize()
                    with self.assertRaisesRegex(LayoutError,'actual rendered data rectangle'):
                        layout.fit()
                    self.assertLess(ax.get_window_extent().height/layout.figure.dpi*25.4,2)
                    self.assertEqual(ax.xaxis.label.get_fontsize(),font_size)
                    for sid,artist in drawn['artists'].items():
                        np.testing.assert_array_equal(artist.get_offsets()[0],scores.loc[sid,['PC1','PC2']])
                    xy=ax.transData.transform([[0,0],[1,0],[0,1]])
                    self.assertAlmostEqual(np.linalg.norm(xy[1]-xy[0]),np.linalg.norm(xy[2]-xy[0]),places=8)

    def test_ordinary_equal_scores_report_the_measured_box_and_reservation(self):
        with figure_style():
            layout,_,_=self.draw_pca({'min_plot_mm':[30,20]})
            report=layout.fit();ax=layout.axes['scores']
            box=ax.get_window_extent();scale=25.4/layout.figure.dpi
            actual=[box.x0*scale,100-box.y1*scale,box.width*scale,box.height*scale]
            np.testing.assert_allclose(report['plot_rectangles_mm']['scores'],actual,atol=1e-10)
            allocated=report['allocated_plot_rectangles_mm']['scores']
            self.assertGreater(allocated[3],actual[3]+10)
            self.assertGreaterEqual(actual[2],30)
            self.assertGreaterEqual(actual[3],20)

    def test_auto_and_declared_physical_aspect_keep_existing_layout_behavior(self):
        with figure_style():
            for options in ({},{'plot_aspect':1,'min_plot_mm':[30,20]}):
                with self.subTest(options=options):
                    layout=compose((140,100),[['main']],panels={'main':options})
                    layout.axes['main'].plot([0,1],[0,1])
                    report=layout.fit()
                    np.testing.assert_allclose(report['plot_rectangles_mm']['main'],
                        report['allocated_plot_rectangles_mm']['main'],atol=1e-10)
                    if options:
                        rectangle=report['plot_rectangles_mm']['main']
                        self.assertAlmostEqual(rectangle[2],rectangle[3])

    def test_explicit_thin_field_budget_remains_possible_without_distortion(self):
        with figure_style():
            layout=compose((140,100),[['field']],panels={'field':{'min_plot_mm':[30,.5]}})
            ax=layout.axes['field']
            ax.imshow(np.arange(100).reshape(1,100),extent=(0,100,0,1),aspect='equal')
            report=layout.fit();actual=report['plot_rectangles_mm']['field']
            self.assertGreaterEqual(actual[3],.5)
            self.assertLess(actual[3],2)
            self.assertAlmostEqual(actual[2]/actual[3],100,places=7)


if __name__=='__main__':unittest.main()
