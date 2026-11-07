"""Scientific invariants for the descriptive count-matrix component."""
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/light-chart/scripts'))
from omics_plots import analyze_count_structure, align_sample_metadata, expression_heatmap, pca_scores


class OmicsSemantics(unittest.TestCase):
    def setUp(self):
        self.counts = pd.DataFrame([[0,0,0,0], [4,12,4,8], [12,4,8,4],
                                   [8,8,16,20], [1,3,2,1]],
                                  index=['zero','gB','gA','gC','gD'], columns=['s1','s2','s3','s4'])
        self.meta = pd.DataFrame({'sample':['s3','s1','s4','s2'],
                                  'condition':['a','a','b','b']})

    def run_analysis(self, counts=None, meta=None, **options):
        return analyze_count_structure(self.counts if counts is None else counts,
            self.meta if meta is None else meta, sample_id='sample', min_cpm=1,
            min_samples=2, heatmap_n=3, **options)

    def test_exact_counts_cpm_and_transform_preserve_all_zero_rows(self):
        a = self.run_analysis()
        pd.testing.assert_frame_equal(a.counts, self.counts)
        np.testing.assert_allclose(a.cpm, self.counts.to_numpy() / self.counts.sum().to_numpy() * 1e6)
        np.testing.assert_allclose(a.cpm.sum(), 1e6)
        np.testing.assert_allclose(a.log_cpm, np.log2(1 + a.cpm))
        np.testing.assert_array_equal(a.log_cpm.loc['zero'].to_numpy(), 0)
        self.assertFalse(a.gene_summary.loc['zero','pca_eligible'])
        np.testing.assert_array_equal(a.sample_qc.sum_gene_counts.to_numpy(), self.counts.sum().to_numpy())

    def test_metadata_and_gene_shuffle_do_not_break_identity(self):
        a = self.run_analysis()
        b = self.run_analysis(self.counts.sample(frac=1, random_state=8), self.meta.iloc[::-1])
        pd.testing.assert_frame_equal(a.scores, b.scores)
        pd.testing.assert_frame_equal(a.loadings, b.loadings)
        self.assertEqual(a.heatmap_gene_order, b.heatmap_gene_order)
        self.assertEqual(a.metadata['sample'].tolist(), list(self.counts.columns))

    def test_sample_shuffle_pca_distances_and_annotation_identity(self):
        from scipy.spatial.distance import pdist, squareform
        a = self.run_analysis()
        perm = ['s4','s2','s1','s3']
        b = self.run_analysis(self.counts[perm])
        da = squareform(pdist(a.scores))
        db = squareform(pdist(b.scores.loc[a.scores.index]))
        np.testing.assert_allclose(da, db, atol=1e-9)
        self.assertEqual(b.metadata['sample'].tolist(), perm)

    def test_covariance_pca_and_sample_sd_zscores(self):
        a = self.run_analysis()
        x = a.log_cpm.loc[a.loadings.index].T
        centered = x - x.mean()
        np.testing.assert_allclose(a.scores, centered @ a.loadings, atol=1e-9)
        np.testing.assert_allclose(a.scores.to_numpy() @ a.loadings.to_numpy().T, centered, atol=1e-9)
        np.testing.assert_allclose(a.heatmap_z.mean(axis=1), 0, atol=1e-12)
        np.testing.assert_allclose(a.heatmap_z.std(axis=1, ddof=1), 1)
        self.assertAlmostEqual(sum(a.explained_variance_ratio), 1)

    def test_library_scaling_leaves_cpm_and_pca_invariant(self):
        a = self.run_analysis()
        b = self.run_analysis(self.counts.mul([2,3,4,5], axis=1))
        np.testing.assert_allclose(a.cpm, b.cpm)
        np.testing.assert_allclose(a.scores, b.scores, atol=1e-9)

    def test_bad_counts_zero_libraries_and_empty_eligibility_fail(self):
        for value in [-1, np.nan, np.inf, 1.5]:
            bad = self.counts.astype(float)
            bad.iloc[1,0] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_analysis(bad)
        bad = self.counts.copy(); bad['s1'] = 0
        with self.assertRaises(ValueError): self.run_analysis(bad)
        bad = self.counts.copy(); bad.index = ['same'] * len(bad)
        with self.assertRaises(ValueError): self.run_analysis(bad)
        with self.assertRaises(ValueError):
            analyze_count_structure(self.counts, self.meta, sample_id='sample', min_cpm=1e7)
        with self.assertRaises(ValueError): self.run_analysis(self.counts.astype(str))
        with self.assertRaises(ValueError): self.run_analysis(self.counts.astype(complex)+1j)

    def test_missing_extra_duplicate_ids_fail(self):
        for bad in [self.meta.iloc[:-1], pd.concat([self.meta, self.meta.iloc[:1]]),
                    self.meta.assign(sample=['extra','s1','s4','s2'])]:
            with self.assertRaises(ValueError): self.run_analysis(meta=bad)

    def test_threshold_selection_is_explicit_and_ties_deterministic(self):
        a = self.run_analysis()
        eligible = (a.cpm.ge(1).sum(axis=1) >= 2) & a.log_cpm.var(axis=1,ddof=1).gt(0)
        np.testing.assert_array_equal(a.gene_summary.pca_eligible.to_numpy(), eligible.to_numpy())
        expected = sorted(a.loadings.index, key=lambda g: (-a.log_cpm.loc[g].var(ddof=1), g))[:3]
        self.assertEqual(list(a.heatmap_z.index), expected)

    def test_default_threshold_and_pseudocount_preserve_previous_numeric_path(self):
        implicit = analyze_count_structure(self.counts, self.meta, sample_id='sample', min_samples=2, heatmap_n=3)
        explicit = self.run_analysis()
        for field in ('counts','cpm','log_cpm','gene_summary','sample_qc','scores','loadings','heatmap_z'):
            pd.testing.assert_frame_equal(getattr(implicit, field), getattr(explicit, field), check_exact=True)
        np.testing.assert_array_equal(implicit.explained_variance_ratio, explicit.explained_variance_ratio)

    def test_count_eligibility_and_half_pseudocount_follow_declared_formula(self):
        a = analyze_count_structure(self.counts, self.meta, sample_id='sample',
            min_count=10, min_samples=1, heatmap_n=3, pseudocount=.5)
        transformed = np.log2(self.counts.div(self.counts.sum(), axis=1) * 1e6 + .5)
        pd.testing.assert_frame_equal(a.log_cpm, transformed)
        eligible = self.counts.ge(10).sum(axis=1).ge(1) & transformed.var(axis=1,ddof=1).gt(0)
        np.testing.assert_array_equal(a.gene_summary.pca_eligible, eligible)
        np.testing.assert_array_equal(a.log_cpm.loc['zero'], -np.ones(4))
        self.assertEqual(a.parameters['eligibility_basis'], 'count')
        self.assertEqual(a.parameters['eligibility_threshold'], 10)
        self.assertEqual(a.parameters['pseudocount'], .5)
        self.assertIsNone(a.parameters['min_cpm'])
        self.assertEqual(a.parameters['all_zero_transformed_value'], -1)
        centered = transformed.loc[a.loadings.index].T
        centered = centered - centered.mean()
        np.testing.assert_allclose(a.scores, centered @ a.loadings, atol=1e-9)
        for options in [dict(min_count=10,min_cpm=1), dict(pseudocount=0), dict(pseudocount=True),
                        dict(pseudocount=np.inf), dict(min_count=-1), dict(min_count='10'),dict(min_cpm=True)]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                analyze_count_structure(self.counts,self.meta,sample_id='sample',**options)

    def test_pca_artists_identity_and_physical_equal_units_survive_layout(self):
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from editorial import canvas, axes_mm
        from composition import compose
        scores = pd.DataFrame({'PC1':[-4,0,2,4], 'PC2':[0,1,-1,0]},index=self.counts.columns)
        meta = self.meta.assign(pair=['p2','p1','p2','p1'])
        layout = compose((140,100),[['scores']],panels={'scores':{'min_plot_mm':[30,20]}})
        plain = canvas((140,100)); axis = axes_mm(plain,20,10,95,50)
        for fig, ax in [(plain,axis),(layout.figure,layout.axes['scores'])]:
            drawn = pca_scores(ax,scores,meta,sample_id='sample',explained_variance_ratio=[.7,.2],
                color='condition',colors={'a':'#123456','b':'#AB6723'},shape='pair',markers={'p1':'o','p2':'s'})
            if fig is layout.figure: layout.fit()
            fig.canvas.draw()
            xy = ax.transData.transform([[0,0],[1,0],[0,1]])
            self.assertAlmostEqual(np.linalg.norm(xy[1]-xy[0]), np.linalg.norm(xy[2]-xy[0]), places=8)
            pd.testing.assert_frame_equal(drawn['scores'],scores)
            self.assertEqual(drawn['metadata']['sample'].tolist(),list(scores.index))
            self.assertEqual(set(drawn['artists']),set(scores.index))
            for sid,artist in drawn['artists'].items():
                np.testing.assert_array_equal(artist.get_offsets()[0],scores.loc[sid,['PC1','PC2']])
                self.assertEqual(artist.get_gid(),sid)
            self.assertEqual(len(drawn['shape_handles']),2)
            plt.close(fig)
        fig, ax = plt.subplots()
        args = dict(sample_id='sample',explained_variance_ratio=[.7,.2],color='condition',colors={'a':'black'})
        with self.assertRaises(ValueError): pca_scores(ax,scores,meta,**args)
        with self.assertRaises(ValueError): pca_scores(ax,scores,meta.iloc[:-1],**{**args,'colors':{'a':'black','b':'red'}})
        ax.set_xscale('log')
        with self.assertRaises(ValueError): pca_scores(ax,scores,meta,**{**args,'colors':{'a':'black','b':'red'}})
        plt.close(fig)

    def test_display_reordering_and_strict_annotation_limits(self):
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        a = self.run_analysis()
        fig, axes = plt.subplots(2)
        args = dict(sample_id='sample', annotation_axes={'condition':axes[1]},
            annotation_colors={'condition':{'a':'#123456','b':'#DD9955'}},
            row_order=a.heatmap_gene_order, sample_order=a.heatmap_sample_order,
            limits=(-3,3), cmap='RdBu_r', negative_ticks=True)
        result = expression_heatmap(axes[0], a.heatmap_z, self.meta, **args)
        np.testing.assert_equal(result['image'].get_array(), a.heatmap_z.loc[a.heatmap_gene_order,a.heatmap_sample_order])
        self.assertEqual(result['annotations']['condition'], a.metadata.loc[a.heatmap_sample_order,'condition'].tolist())
        self.assertEqual(result['negative_tick_count'], int((a.heatmap_z.to_numpy()<0).sum()))
        with self.assertRaises(ValueError):
            expression_heatmap(axes[0], a.heatmap_z, self.meta, **{**args,'limits':(-.1,.1)})
        with self.assertRaises(ValueError):
            expression_heatmap(axes[0], a.heatmap_z, self.meta, **{**args,'annotation_colors':{'condition':{'a':'black'}}})
        with self.assertRaises(ValueError):
            expression_heatmap(axes[0], a.heatmap_z, self.meta, **{**args,'sample_order':['s1']*4})
        plt.close(fig)


if __name__ == '__main__': unittest.main()
