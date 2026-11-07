"""Scientific invariants of CF decoding and the ordinary mixed evidence path."""
from pathlib import Path
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/light-chart/scripts'))
from field_data import prepare_netcdf_field, field_from_table, FieldPreparationError
from figure_job import prepare_job
from chart_plan import plan_chart, read_data
import library


class NetCDFPreparation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='netcdf test with spaces ')
        self.folder = Path(self.tmp.name)
        self.path = self.folder / 'packed field.nc'
        self.raw = np.arange(3 * 2 * 2 * 3, dtype=np.int16).reshape(3, 2, 2, 3)
        self.raw[1, 0, 0, 0] = -32767
        a = xr.DataArray(self.raw.transpose(3, 0, 1, 2), dims=('column', 'time', 'level', 'row'),
            attrs={'units': 'K', 'scale_factor': .5, 'add_offset': 100., '_FillValue': np.int16(-32767)})
        ds = xr.Dataset({'temperature': a}, coords={
            'lon': ('column', [8., 2., -1.], {'units': 'degrees_east'}),
            'lat': ('row', [50., 20.], {'units': 'degrees_north'}),
            'time': pd.date_range('2000-01-01', periods=3), 'level': [1000, 850]})
        ds.to_netcdf(self.path, engine='scipy')
        self.chart = dict(intent='scalar_field', variable='temperature', x='lon', y='lat', time='time',
            isel={'level': 0}, reduce={'operation': 'mean', 'dimension': 'time',
                'ranges': [['2000-01-01', '2000-01-03']], 'weighting': 'equal_samples', 'missing': 'skip'},
            limits=[90., 130.])
        values = self.raw.astype(float) * .5 + 100
        values[self.raw == -32767] = np.nan
        self.values = values

    def tearDown(self):
        self.tmp.cleanup()

    def job(self, chart=None, **extra):
        return prepare_job(self.path, {'question': 'What does the declared temperature field show?',
            'chart': self.chart if chart is None else chart, **extra})

    def test_packed_decode_transpose_descending_pairs_counts_and_real_mesh(self):
        p = prepare_netcdf_field(self.path, self.chart)
        expected = np.nanmean(self.values[:, 0], axis=0)[::-1, ::-1]
        np.testing.assert_array_equal(p.field.z, expected)
        np.testing.assert_array_equal(p.field.x, [-1., 2., 8.])
        np.testing.assert_array_equal(p.field.y, [20., 50.])
        np.testing.assert_array_equal(p.report['valid_counts_yx'][0], np.isfinite(self.values[:, 0]).sum(0)[::-1, ::-1])
        self.assertEqual(p.report['engine'], 'scipy')
        self.assertEqual(p.report['source_variable']['encoding']['scale_factor'], .5)
        self.assertFalse(p.field.z.flags.writeable)
        import matplotlib.pyplot as plt
        from field_tools import scalar_field
        fig, ax = plt.subplots()
        artist = scalar_field(ax, p.field)
        np.testing.assert_array_equal(np.asarray(artist.get_array()), expected)
        # Nonuniform x cell widths survive the actual QuadMesh geometry.
        np.testing.assert_array_equal(artist.get_coordinates()[0, :, 0], [-2.5, .5, 5., 11.])
        plt.close(fig)

    def test_integer_axes_keep_each_valid_count_paired_with_its_rendered_cell(self):
        # Native unsigned coordinates use HDF5 when its optional reader is
        # available. The base SciPy environment exercises the same decoded
        # uint contract through the CF _Unsigned storage convention.
        engine = 'h5netcdf' if 'h5netcdf' in xr.backends.list_engines() else 'scipy'
        for name, xx, yy in [('unsigned', np.array([9, 5, 1], dtype='uint16'), np.array([4, 2], dtype='uint8')),
                             ('signed-overflow', np.array([30000, -30000], dtype='int16'), np.array([100, -100], dtype='int8'))]:
            with self.subTest(coordinate_type=name, engine=engine):
                values = np.arange(3 * len(yy) * len(xx), dtype=float).reshape(3, len(yy), len(xx))
                values[1:, 0, 0] = np.nan
                values[2, 1, 0] = np.nan
                values[0, 0, -1] = np.nan
                coords = {}
                for key, axis in [('x', xx), ('y', yy)]:
                    attrs = {'units': 'm'}
                    if engine == 'scipy' and axis.dtype.kind == 'u':
                        attrs['_Unsigned'] = 'true'
                        axis = axis.astype('int' + str(axis.dtype.itemsize * 8))
                    coords[key] = (key, axis, attrs)
                ds = xr.Dataset({'v': (('time', 'y', 'x'), values, {'units': 'K'})},
                    coords={**coords, 'time': pd.date_range('2000-01-01', periods=3)})
                path = self.folder / (name + '.nc'); ds.to_netcdf(path, engine=engine)
                chart = {'intent': 'scalar_field', 'variable': 'v', 'x': 'x', 'y': 'y', 'time': 'time', 'limits': [-1., 30.],
                    'reduce': copy.deepcopy(self.chart['reduce'])}
                result = prepare_netcdf_field(path, chart)
                expected_counts = np.isfinite(values).sum(axis=0)[::-1, ::-1]
                expected_values = np.nanmean(values, axis=0)[::-1, ::-1]
                np.testing.assert_array_equal(result.field.x, xx[::-1])
                np.testing.assert_array_equal(result.field.y, yy[::-1])
                np.testing.assert_array_equal(result.field.z, expected_values)
                np.testing.assert_array_equal(result.report['valid_counts_yx'][0], expected_counts)
                with xr.open_dataset(path, engine=engine) as reopened:
                    self.assertEqual(reopened['x'].dtype, xx.dtype)
                    self.assertEqual(reopened['y'].dtype, yy.dtype)

    def test_nonmonotonic_integer_coordinates_reject_before_range_subsetting(self):
        from field_data import _coordinate
        for values in [np.array([9, 1, 5], dtype='uint16'), np.array([30000, -30000, 0], dtype='int16')]:
            with self.subTest(dtype=str(values.dtype)):
                ds = xr.Dataset(coords={'x': ('x', values)})
                with self.assertRaises(FieldPreparationError):
                    _coordinate(ds, 'x', 'x', ('x',))

    def test_missing_propagates_and_affine_units_do_not_edit_source(self):
        before = self.path.read_bytes()
        chart = copy.deepcopy(self.chart)
        chart['reduce']['missing'] = 'propagate'
        chart['value_transform'] = {'scale': 1., 'offset': -100., 'unit': 'relative_K'}
        chart['limits'] = [-10., 30.]
        p = prepare_netcdf_field(self.path, chart)
        np.testing.assert_array_equal(p.field.z, (np.mean(self.values[:, 0], axis=0) - 100)[::-1, ::-1])
        self.assertTrue(np.isnan(p.field.z[-1, -1]))
        self.assertEqual(p.report['units']['value'], 'relative_K')
        self.assertEqual(self.path.read_bytes(), before)

    def test_all_missing_cells_remain_na_in_mean_and_difference(self):
        with xr.open_dataset(self.path, engine='scipy') as ds: changed = ds.load()
        changed['temperature'].values[0, :, 0, 0] = np.nan
        other = self.folder / 'all missing cell.nc'
        changed.to_netcdf(other, engine='scipy')
        p = prepare_netcdf_field(other, self.chart)
        self.assertTrue(np.isnan(p.field.z[-1, -1]))
        self.assertEqual(p.report['valid_counts_yx'][0][-1][-1], 0)
        chart = copy.deepcopy(self.chart)
        chart['reduce'].update(operation='difference_of_means', direction='second_minus_first',
            ranges=[['2000-01-01', '2000-01-01'], ['2000-01-02', '2000-01-03']])
        chart.update(limits=[-20., 20.], center=0)
        p = prepare_netcdf_field(other, chart)
        self.assertTrue(np.isnan(p.field.z[-1, -1]))
        self.assertEqual([v[-1][-1] for v in p.report['valid_counts_yx']], [0, 0])

    def test_difference_is_explicit_second_minus_first_and_preserves_missing(self):
        chart = copy.deepcopy(self.chart)
        chart['reduce'].update(operation='difference_of_means',
            ranges=[['2000-01-01', '2000-01-01'], ['2000-01-02', '2000-01-03']], direction='second_minus_first')
        chart.update(limits=[-20., 20.], center=0)
        p = prepare_netcdf_field(self.path, chart)
        expected = (np.nanmean(self.values[1:, 0], 0) - self.values[0, 0])[::-1, ::-1]
        np.testing.assert_array_equal(p.field.z, expected)
        self.assertEqual([r['count'] for r in p.report['selected_time']], [1, 2])
        self.assertEqual(p.field.norm.vcenter, 0)
        self.assertEqual(len(p.report['valid_counts_yx']), 2)
        chart['reduce'].pop('direction')
        self.assertEqual(self.job(chart)['status'], 'needs_resolution')

    def test_scalar_layer_time_and_spatial_subset_are_explicit(self):
        chart = {**self.chart, 'isel': {'level': 1, 'time': 2}, 'coordinate_ranges': {'lon': [-1, 2]},
                 'limits': [100., 140.]}
        chart.pop('reduce')
        p = prepare_netcdf_field(self.path, chart)
        np.testing.assert_array_equal(p.field.z, self.values[2, 1, ::-1, 1:][:, ::-1])
        np.testing.assert_array_equal(p.field.x, [-1., 2.])
        self.assertEqual(p.report['isel'], {'level': 1, 'time': 2})

    def test_same_public_route_profiles_only_reduced_cells(self):
        result = self.job()
        self.assertEqual(result['status'], 'prepared')
        self.assertEqual(result['sources']['data']['rows'], 6)
        self.assertEqual(result['decisions']['main']['recommended']['construction'], 'rectilinear-scalar-field')
        self.assertEqual(result['input_preparation']['main']['report']['source_variable']['shape'], [3, 3, 2, 2])
        self.assertEqual(result['field_mapping']['main']['original_source'], 'data')
        routes = result['decisions']['main']['recommended']['resources']['entrypoints']
        self.assertTrue(any(r['id'] == 'impl-netcdf-field-preparation' for r in routes))
        self.assertTrue(any(r['id'] == 'impl-field' for r in routes))
        self.assertEqual(library.plan(self.path, self.chart)['status'], 'ready')

    def test_two_fields_and_csv_share_evidence_roles_dependencies_and_ancestry(self):
        second = copy.deepcopy(self.chart)
        second['reduce']['ranges'] = [['2000-01-01', '2000-01-02']]
        panels = [dict(id='a', source='cube', chart=self.chart, claim='c', role='primary', question='What is the field?'),
            dict(id='b', source='cube', chart=second, claim='c', role='contrast', question='What is the earlier field?', depends_on=['a']),
            dict(id='c', source='observations', chart={'intent': 'distribution', 'y': 'v'},
                 claim='c', role='support', question='What are the supplied observations?', depends_on=['b'])]
        spec = {'question': 'What complementary patterns are supported?',
                'claims': {'c': {'boundary': 'descriptive only', 'required_roles': ['primary', 'contrast', 'support']}}, 'panels': panels}
        sources = {'cube': self.path, 'observations': pd.DataFrame({'v': [1., 4., 7.]})}
        r = prepare_job(sources, spec)
        self.assertEqual(r['status'], 'prepared')
        self.assertEqual(r['evidence']['reading_order'], ['a', 'b', 'c'])
        self.assertEqual(len(r['profiles']), 3)
        self.assertTrue(any('original records' in w for w in r['warnings']))
        self.assertEqual(spec['panels'][0]['source'], 'cube')
        panels[1]['independence'] = {'from': 'a'}
        bad = prepare_job(sources, spec)
        self.assertEqual(bad['status'], 'needs_resolution')
        self.assertTrue(any('independent evidence' in b for b in bad['blockers']))

    def test_stale_values_or_changed_time_color_contract_cannot_reuse_grid(self):
        p = prepare_netcdf_field(self.path, self.chart)
        changed = p.table.copy()
        changed.iloc[0, 2] += 1
        with self.assertRaises(FieldPreparationError): field_from_table(changed, self.chart)
        other = copy.deepcopy(self.chart)
        other['reduce']['ranges'][0][0] = '2000-01-02'
        with self.assertRaises(FieldPreparationError): field_from_table(p.table, other)
        with self.assertRaises(FieldPreparationError): field_from_table(p.table.iloc[:-1].copy(), self.chart)

    def test_unknown_layer_variable_units_limits_and_weighting_block(self):
        variants = []
        for key in ('isel', 'reduce', 'variable', 'limits'):
            c = copy.deepcopy(self.chart); c.pop(key); variants.append(c)
        c = copy.deepcopy(self.chart); c['reduce'].pop('weighting'); variants.append(c)
        c = copy.deepcopy(self.chart); c['value_unit'] = 'degC'; variants.append(c)
        c = copy.deepcopy(self.chart); c['limits'] = [100, 101]; variants.append(c)
        c = copy.deepcopy(self.chart); c['isel']['level'] = True; variants.append(c)
        for chart in variants:
            with self.subTest(chart=chart):
                r = self.job(chart)
                self.assertEqual(r['status'], 'needs_resolution')
                self.assertTrue(r['blockers'])
        self.assertEqual(self.job(backend='r')['status'], 'adaptation_required')
        self.assertEqual(self.job({**self.chart, 'backend': 'r'})['status'], 'needs_resolution')

    def test_no_unit_guess_curvilinear_or_nonstandard_calendar(self):
        with xr.open_dataset(self.path, engine='scipy') as ds: original = ds.load()
        for kind in ('missing-unit', 'curvilinear', 'calendar'):
            ds = original.copy(deep=True)
            if kind == 'missing-unit': ds['temperature'].attrs.pop('units')
            elif kind == 'curvilinear': ds = ds.drop_vars('lon').assign_coords(lon=(('row', 'column'), [[-1., 2., 8.], [-.5, 2., 8.]]))
            else:
                ds = ds.drop_vars('time').assign_coords(time=('time', [0, 1, 2], {'units': 'days since 2000-01-01', 'calendar': '360_day'}))
            p = self.folder / (kind + '.nc'); ds.to_netcdf(p, engine='scipy')
            r = prepare_job(p, {'question': 'What is the field?', 'chart': self.chart})
            self.assertEqual(r['status'], 'needs_resolution', kind)

    def test_missing_reader_and_unmapped_source_cannot_be_silently_skipped(self):
        with patch('xarray.backends.list_engines', return_value={}):
            r = self.job()
            self.assertEqual(r['status'], 'needs_resolution')
            self.assertTrue(any('engine' in b for b in r['blockers']))
        r = prepare_job({'cube': self.path, 'values': pd.DataFrame({'v': [1., 2., 3.]})},
            {'question': 'What varies?', 'source': 'values', 'chart': {'intent': 'distribution', 'y': 'v'}})
        self.assertEqual(r['status'], 'needs_resolution')
        with self.assertRaisesRegex(ValueError, 'binary data are not CSV'): read_data(self.path)

    def test_cli_with_spaces_and_csv_without_optional_xarray(self):
        spec = self.folder / 'task spec.json'; out = self.folder / 'prepared decision.json'
        spec.write_text(json.dumps({'question': 'What field is observed?', 'chart': self.chart}), encoding='utf-8')
        run = subprocess.run([sys.executable, '-B', str(ROOT / 'skills/light-chart/scripts/figure_job.py'),
            '--data', str(self.path), '--spec', str(spec), '--out', str(out)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(out.read_text(encoding='utf-8'))['status'], 'prepared')
        code = "import sys;sys.modules['xarray']=None;from figure_job import prepare_job;import pandas as pd;r=prepare_job(pd.DataFrame({'v':[1.,2.,3.]}),{'question':'What varies?','chart':{'intent':'distribution','y':'v'}});assert r['status']=='prepared'"
        env = {**os.environ, 'PYTHONPATH': str(ROOT / 'skills/light-chart/scripts')}
        run = subprocess.run([sys.executable, '-B', '-c', code], env=env, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == '__main__': unittest.main()
