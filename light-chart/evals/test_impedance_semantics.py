"""Scientific invariants for explicitly mapped, measured EIS constructors."""
import sys
import unittest
import warnings
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/light-chart/scripts'))
from impedance_plots import prepare_impedance, plot_nyquist, plot_bode


class ImpedanceSemantics(unittest.TestCase):
    def setUp(self):
        self.data=pd.DataFrame({'sid':['A']*3+['B']*3,'f':[100,1,10]*2,
            're':[1,3,2,1.5,4,2.5],'im':[.2,-4,-2,.3,-3,-1],
            'source_row':[8,10,9,18,20,19]})
        self.kw=dict(spectrum='sid',frequency='f',real='re',imag='im',unit='ohm',spectrum_order=['A','B'])
        self.enc={'A':dict(color='#306A9C',marker='o',linestyle='-'),
                  'B':dict(color='#B65A3C',marker='s',linestyle='--')}

    def tearDown(self): plt.close('all')
    def prep(self, data=None): return prepare_impedance(self.data if data is None else data,**self.kw)

    def test_joint_sort_and_signed_values_survive_shuffled_rows(self):
        original=self.data.copy(deep=True)
        r=self.prep(self.data.sample(frac=1,random_state=17)).rows
        self.assertEqual(r.source_row.tolist(),[10,9,8,20,19,18])
        np.testing.assert_array_equal(r.negative_imag_ohm,[4,2,-.2,3,1,-.3])
        np.testing.assert_allclose(r.magnitude_ohm,np.sqrt(r.real_ohm**2+r.imag_ohm**2))
        self.assertTrue(self.data.equals(original))

    def test_extra_rank_and_other_metadata_are_preserved_by_positional_sort(self):
        source = self.data.assign(_rank=['a0','a1','a2','b0','b1','b2'],
                                  magnitude_note=[40,41,42,43,44,45]).sample(frac=1,random_state=6)
        before = source.copy(deep=True)
        result = self.prep(source).rows
        expected = source.iloc[result.source_position].reset_index(drop=True)
        pd.testing.assert_frame_equal(result[source.columns],expected)
        pd.testing.assert_frame_equal(source,before)
        self.assertEqual(result.spectrum.tolist(),['A']*3+['B']*3)
        self.assertEqual(result.frequency_hz.tolist(),[1,10,100]*2)

    def test_cross_role_canonical_names_cannot_overwrite_source_observations(self):
        for role, source_field in [('spectrum','sid'),('frequency','f'),('real','re'),('imag','im')]:
            for reserved in ['spectrum','frequency_hz','real_ohm','imag_ohm',
                             'negative_imag_ohm','magnitude_ohm','phase_deg','source_position']:
                canonical = dict(spectrum='spectrum',frequency='frequency_hz',real='real_ohm',imag='imag_ohm')[role]
                if reserved == canonical:
                    continue
                source = self.data.rename(columns={source_field:reserved})
                before = source.copy(deep=True)
                with self.subTest(role=role,reserved=reserved), warnings.catch_warnings():
                    warnings.simplefilter('error')
                    with self.assertRaisesRegex(ValueError,'reserved derived-column names'):
                        prepare_impedance(source,**{**self.kw,role:reserved})
                    pd.testing.assert_frame_equal(source,before)

    def test_matching_canonical_mappings_keep_physical_data_and_ids(self):
        source = self.data.rename(columns={'sid':'spectrum','f':'frequency_hz',
                                          're':'real_ohm','im':'imag_ohm'})
        result = prepare_impedance(source,spectrum='spectrum',frequency='frequency_hz',
            real='real_ohm',imag='imag_ohm',unit='ohm',spectrum_order=['B','A']).rows
        for field in source:
            np.testing.assert_array_equal(result[field],source.iloc[result.source_position][field])
        self.assertEqual(result.spectrum.tolist(),['B']*3+['A']*3)

    def test_phase_uses_signed_atan2_all_quadrants(self):
        d=self.data.copy();d['re']=[-1,-1,1,1,-1,-1];d['im']=[1,-1,1,-1,1,-1]
        r=self.prep(d).rows
        np.testing.assert_allclose(r.phase_deg,np.degrees(np.angle(r.real_ohm+1j*r.imag_ohm)))

    def test_complex_object_and_bool_rejected_before_cast(self):
        for field in ['f','re','im']:
            for value in [1+2j,True]:
                d=self.data.astype({field:object});d.loc[0,field]=value
                with self.subTest(field=field,value=value),self.assertRaises(ValueError): self.prep(d)

    def test_frequencies_positive_unique_finite(self):
        for value in [0,-1,np.nan,np.inf,10]:
            d=self.data.copy();d.loc[0,'f']=value
            with self.subTest(value=value),self.assertRaises(ValueError): self.prep(d)

    def test_identity_and_explicit_units(self):
        for value in [None,1,'']:
            d=self.data.copy();d.loc[0,'sid']=value
            with self.assertRaises(ValueError): self.prep(d)
        for order in [['A'],['A','A'],['A','C']]:
            with self.assertRaises(ValueError): prepare_impedance(self.data,**{**self.kw,'spectrum_order':order})
        with self.assertRaises(ValueError): prepare_impedance(self.data,**{**self.kw,'unit':'ohm cm2'})

    def test_no_silent_rows_removed_or_imaginary_quadrant_lost(self):
        r=self.prep();fig,ax=plt.subplots()
        out=plot_nyquist(ax,r,encodings=self.enc)
        self.assertEqual(sum(len(v.get_xdata()) for v in out['lines'].values()),6)
        self.assertTrue(any((v.get_ydata()<0).any() for v in out['lines'].values()))
        self.assertEqual(ax.get_aspect(),1)
        self.assertFalse(out['requires_overview'])

    def test_overview_cannot_hide_points_and_zoom_declared(self):
        r=self.prep();fig,ax=plt.subplots()
        with self.assertRaises(ValueError): plot_nyquist(ax,r,encodings=self.enc,limits=(0,2,-1,2))
        z=plot_nyquist(ax,r,encodings=self.enc,limits=(0,2,-1,2),detail=True)
        self.assertTrue(z['requires_overview']);self.assertEqual(z['coverage']['A']['total'],3)
        with self.assertRaises(ValueError): plot_nyquist(ax,r,encodings=self.enc,detail=True)

    def test_bode_shared_actual_frequency_and_exact_sign(self):
        r=self.prep();fig,(a,b)=plt.subplots(2)
        out=plot_bode(a,b,r,encodings=self.enc)
        self.assertEqual(a.get_xlim(),b.get_xlim())
        for name,lines in out['lines'].items():
            p=r.rows.loc[r.rows.spectrum==name]
            np.testing.assert_array_equal(lines[0].get_xdata(),[1,10,100])
            np.testing.assert_array_equal(lines[1].get_ydata(),p.phase_deg)
        self.assertEqual(a.get_yscale(),'log');self.assertEqual(b.get_yscale(),'linear')

    def test_bode_zero_or_clipped_or_dual_axis_rejected(self):
        r=self.prep();fig,(a,b)=plt.subplots(2)
        for kw in [dict(frequency_limits=(2,100)),dict(magnitude_limits=(1,3)),dict(phase_limits=(-20,20))]:
            with self.assertRaises(ValueError): plot_bode(a,b,r,encodings=self.enc,**kw)
        with self.assertRaises(ValueError): plot_bode(a,a,r,encodings=self.enc)
        d=self.data.copy();d.loc[0,['re','im']]=0
        with self.assertRaises(ValueError): plot_bode(a,b,self.prep(d),encodings=self.enc)

    def test_mixed_boolean_limits_rejected_before_artists_or_float_conversion(self):
        result = self.prep()
        for field, limits in [('frequency_limits',[True,100.]),
                              ('magnitude_limits',[False,10.]),
                              ('phase_limits',[-90.,True])]:
            fig,(a,b)=plt.subplots(2)
            with self.subTest(field=field), warnings.catch_warnings():
                warnings.simplefilter('error')
                with self.assertRaisesRegex(ValueError,'not complex or Boolean'):
                    plot_bode(a,b,result,encodings=self.enc,**{field:limits})
                self.assertEqual(len(a.lines)+len(b.lines),0)
        fig, ax = plt.subplots()
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            with self.assertRaisesRegex(ValueError,'not complex or Boolean'):
                plot_nyquist(ax,result,encodings=self.enc,limits=[False,5.,-1.,5.])
        self.assertEqual(len(ax.lines),0)

    def test_different_frequency_grids_retained(self):
        d=self.data.copy();d.loc[3:,'f']=[200,2,20]
        r=self.prep(d)
        self.assertEqual(r.rows.frequency_hz.tolist(),[1,10,100,2,20,200])

    def test_invalid_encodings_do_not_guess_identity(self):
        r=self.prep();fig,ax=plt.subplots()
        with self.assertRaises(ValueError): plot_nyquist(ax,r,encodings={'A':self.enc['A']})


if __name__=='__main__': unittest.main()
