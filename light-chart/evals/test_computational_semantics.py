"""Scientific invariants of reusable computational constructors (no model fixtures)."""
import sys
from pathlib import Path
import unittest
import warnings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/light-chart/scripts'))
from computational_plots import ordered_sweep, plot_budget_sweep, prepare_count_matrix, confusion_counts, plot_count_matrix, plan_computational_chart


class ComputationalSemantics(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame([{'s': s, 'r': r, 'x': x, 'y': 100*s+10*r+x}
                                  for s in [2, 1] for r in [8, 3] for x in [100, 5, 17]])

    def test_irregular_x_joint_order_and_identity(self):
        d = ordered_sweep(self.data, x='x', y='y', series='s', repeat='r', series_order=[1, 2])
        np.testing.assert_array_equal(d['x'], [5, 17, 100])
        np.testing.assert_array_equal(d['values'][1], [[185,197,280],[135,147,230]])
        self.assertEqual(d['repeat_ids'], [8,3])

    def test_sweep_no_silent_missing_or_duplicate_runs(self):
        for frame in [self.data.iloc[:-1], pd.concat([self.data,self.data.iloc[:1]])]:
            with self.assertRaises(ValueError):
                ordered_sweep(frame, x='x', y='y', series='s', repeat='r', series_order=[1,2])
        with self.assertRaises(ValueError):
            ordered_sweep(self.data, x='x', y='y', series='s', repeat='r', series_order=[1])

    def test_sweep_rejects_integer_budget_precision_loss_before_alignment(self):
        cases = [
            [2**53, 2**53+1], [-2**53, -2**53-1],
            [str(2**53), str(2**53+1)],
            pd.Series([2**53+1, .5], dtype=object),
            [str(2**53+1), '.5'],
        ]
        for budgets in cases:
            with self.subTest(budgets=budgets):
                data = pd.DataFrame({'budget':budgets, 'score':[.1,.9], 'method':['A','A'], 'run':[0,0]})
                with self.assertRaisesRegex(ValueError, 'exactly representable'):
                    ordered_sweep(data, x='budget', y='score', series='method', repeat='run', series_order=['A'])
        data['budget'] = [2**53+2, 2**53]
        actual = ordered_sweep(data, x='budget', y='score', series='method', repeat='run', series_order=['A'])
        np.testing.assert_array_equal(actual['x'], [2**53, 2**53+2])
        np.testing.assert_array_equal(actual['values']['A'], [[.9,.1]])

    def test_sweep_rejects_distinct_source_budgets_that_collapse_during_numeric_parsing(self):
        data = pd.DataFrame({'x':['0.100000000000000001', '0.100000000000000002'],
                             'y':[.1,.9], 's':['A','A'], 'r':[0,0]})
        with self.assertRaisesRegex(ValueError, 'cannot collapse'):
            ordered_sweep(data, x='x', y='y', series='s', repeat='r', series_order=['A'])

    def test_close_fractional_budget_labels_remain_distinct_at_original_coordinates(self):
        for budgets in [[.1000001,.1000002], [.1,np.nextafter(.1,1)], [1e20,np.nextafter(1e20,np.inf)]]:
            with self.subTest(budgets=budgets):
                data = pd.DataFrame({'x':budgets[::-1], 'y':[.9,.1], 's':['A','A'], 'r':[0,0]})
                fig, ax = plt.subplots()
                try:
                    result = plot_budget_sweep(ax, data, x='x', y='y', series='s', repeat='r', series_order=['A'],
                                               encodings={'A':dict(color='navy',marker='o',linestyle='-')})
                    np.testing.assert_array_equal(result['x'], budgets)
                    np.testing.assert_array_equal(result['artists']['A'].get_xdata(), budgets)
                    np.testing.assert_array_equal(result['values']['A'], [[.1,.9]])
                    tick_labels = [tick.get_text() for tick in ax.get_xticklabels()]
                    self.assertEqual(len(set(tick_labels)), len(budgets))
                    np.testing.assert_array_equal([float(label) for label in tick_labels], budgets)
                finally:
                    plt.close(fig)

    def test_sweep_rejects_complex_boolean_and_nonfinite_measurements(self):
        for field in ['x', 'y']:
            for dtype in [complex, object]:
                for value in [1+2j, np.complex128(1+0j)]:
                    with self.subTest(field=field, dtype=dtype, value=value), warnings.catch_warnings():
                        warnings.simplefilter('error')
                        bad = self.data.copy()
                        values = self.data[field].tolist()
                        values[0] = value
                        bad[field] = pd.Series(values, dtype=dtype)
                        with self.assertRaisesRegex(ValueError, 'real numeric'):
                            ordered_sweep(bad, x='x', y='y', series='s', repeat='r', series_order=[1,2])
            for value in [True, np.bool_(False), np.inf, -np.inf, np.nan]:
                with self.subTest(field=field, value=value):
                    bad = self.data.astype(object)
                    bad.loc[0, field] = value
                    with self.assertRaises(ValueError):
                        ordered_sweep(bad, x='x', y='y', series='s', repeat='r', series_order=[1,2])

    def test_sweep_real_numeric_inputs_and_field_mapping_preserve_exact_values(self):
        expected = ordered_sweep(self.data, x='x', y='y', series='s', repeat='r', series_order=[1,2])
        mapped = self.data.rename(columns={'x':'budget', 'y':'score', 's':'method', 'r':'run'})
        for dtype in [float, object, str]:
            with self.subTest(dtype=dtype):
                real = mapped.astype({'budget':dtype, 'score':dtype})
                actual = ordered_sweep(real, x='budget', y='score', series='method', repeat='run', series_order=[1,2])
                np.testing.assert_array_equal(actual['x'], expected['x'])
                self.assertEqual(actual['repeat_ids'], expected['repeat_ids'])
                self.assertEqual(actual['series_order'], expected['series_order'])
                for name in expected['series_order']:
                    np.testing.assert_array_equal(actual['values'][name], expected['values'][name])

    def test_count_matrix_rejects_complex_and_boolean_including_object_mixtures(self):
        for values in [np.array([[1+2j, 2]]), np.array([[1+0j, 2]], dtype=object),
                       np.array([[1, 2+3j]], dtype=object), np.array([[True, False]]),
                       np.array([[1, True]], dtype=object)]:
            with self.subTest(values=values), warnings.catch_warnings():
                warnings.simplefilter('error')
                with self.assertRaisesRegex(ValueError, 'finite nonnegative integers'):
                    prepare_count_matrix(values, row_ids=['a'], column_ids=['b','c'])
        fig, ax = plt.subplots()
        try:
            for value in [1+2j, np.complex128(1+0j), True, np.inf, np.nan]:
                with self.subTest(vmax=value), self.assertRaises(ValueError):
                    plot_count_matrix(ax, [[1]], row_ids=['a'], column_ids=['b'], vmax=value)
        finally:
            plt.close(fig)

    def test_mixed_nested_count_lists_reject_boolean_before_numpy_coercion(self):
        cases = [[[4,True]], [[False,4]], [[4.,np.bool_(True)]],
                 [[True,4],[5,6]], [[4,2+0j]]]
        for values in cases:
            with self.subTest(values=values), warnings.catch_warnings():
                warnings.simplefilter('error')
                with self.assertRaisesRegex(ValueError, 'never complex or Boolean'):
                    prepare_count_matrix(values,row_ids=list(range(len(values))),column_ids=['a','b'])
        # Real lists retain their exact counts, including integers above float precision.
        valid = [[2**53+1,4],[0,7]]
        result = prepare_count_matrix(valid,row_ids=['a','b'],column_ids=['x','y'],
                                      row_order=['b','a'],column_order=['y','x'])
        np.testing.assert_array_equal(result['counts'],[[7,0],[4,2**53+1]])
        self.assertEqual(result['total'],2**53+12)

    def test_measured_mean_artist_has_true_numeric_x(self):
        fig, ax = plt.subplots()
        d = plot_budget_sweep(ax, self.data, x='x', y='y', series='s', repeat='r', series_order=[1,2],
                              encodings={1:dict(color='navy',marker='o',linestyle='-'),2:dict(color='brown',marker='s',linestyle='--')})
        np.testing.assert_array_equal(d['artists'][1].get_xdata(), [5,17,100])
        np.testing.assert_allclose(d['artists'][1].get_ydata(), [160,172,255])
        plt.close(fig)

    def test_exact_joint_matrix_reorder_and_marginals(self):
        d = prepare_count_matrix([[1,2,3],[4,5,9]], row_ids=['a','b'], column_ids=['x','y','z'],
                                 row_order=['b','a'], column_order=['z','x','y'])
        np.testing.assert_array_equal(d['counts'], [[9,4,5],[3,1,2]])
        np.testing.assert_array_equal(d['row_totals'], [18,6])
        np.testing.assert_array_equal(d['column_totals'], [12,5,7])
        self.assertEqual(d['total'], 24)

    def test_invalid_counts_and_identity_orders_rejected(self):
        for values in [[[-1]], [[.2]], [[np.nan]], [[np.inf]], [['1']], [[float(2**63)]]]:
            with self.assertRaises(ValueError):
                prepare_count_matrix(values,row_ids=['a'],column_ids=['b'])
        with self.assertRaises(ValueError):
            prepare_count_matrix([[1,2]],row_ids=['a'],column_ids=['b','b'])
        with self.assertRaises(ValueError):
            prepare_count_matrix([[1,2]],row_ids=['a'],column_ids=['b','c'],column_order=['b'])

    def test_confusion_preserves_zeros_class_order_and_record_ids(self):
        d = confusion_counts(['a','b','a'],['a','a','a'],class_order=['c','b','a'],record_ids=[9,2,7])
        np.testing.assert_array_equal(d['counts'], [[0,0,0],[0,0,1],[0,0,2]])
        self.assertEqual(d['record_ids'], [9,2,7])
        self.assertEqual(d['correct'],2)
        with self.assertRaises(ValueError):
            confusion_counts(['a','a'],['a','a'],class_order=['a'],record_ids=[1,1])

    def test_full_count_range_and_zero_origin_no_clipping(self):
        fig, ax = plt.subplots()
        d = plot_count_matrix(ax,[[0,400],[2,1]],row_ids=['b','a'],column_ids=['b','a'])
        self.assertEqual(d['norm'].vmin,0)
        self.assertEqual(d['norm'].vmax,400)
        self.assertEqual([t.get_text() for t in ax.get_yticklabels()], ['b\nn=400','a\nn=3'])
        with self.assertRaises(ValueError):
            plot_count_matrix(ax,[[21]],row_ids=['a'],column_ids=['a'],vmax=20)
        plt.close(fig)

    def test_value_aware_decision_requires_repeat_and_split_semantics(self):
        spec = dict(intent='computational-sweep',x='x',y='y',series='s',repeat='r',series_order=[1,2],
                    evaluation_split='validation',repeat_semantics='algorithmic seeds on one split',objective_direction='max')
        self.assertEqual(plan_computational_chart(self.data,spec)['status'],'ready')
        self.assertEqual(plan_computational_chart(self.data.iloc[:-1],spec)['status'],'needs_resolution')
        self.assertEqual(plan_computational_chart(self.data,{**spec,'objective_direction':None})['status'],'needs_resolution')

    def test_column_display_alias_preserves_counts_and_ids(self):
        fig, ax = plt.subplots()
        d=plot_count_matrix(ax,[[2,3],[5,7]],row_ids=['a','b'],column_ids=['a','b'],
                            labels={'a':'Full A','b':'Full B'},column_labels={'a':'A','b':'B'},rotation=0)
        self.assertEqual(d['column_ids'],['a','b'])
        self.assertEqual(ax.get_xticklabels()[0].get_text(),'A\nn=7')
        self.assertEqual(ax.get_yticklabels()[0].get_text(),'Full A\nn=5')
        plt.close(fig)

if __name__ == '__main__':
    unittest.main()
