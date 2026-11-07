"""Scientific invariants for new domain components, not style-string checks."""
import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/light-chart/scripts'))
from signal_plots import minmax_envelope,validate_signal,signal_spectra
from domain_decisions import plan_domain_chart


class SignalSemantics(unittest.TestCase):
    def test_bins_cover_all_records_and_keep_true_extrema(self):
        t=np.arange(103)/10;y=np.sin(t);y[51]=30;y[-1]=-40
        b=minmax_envelope(t,y,max_bins=12)
        self.assertEqual(b['count'].sum(),len(y));self.assertEqual(b.source_start.iloc[0],0)
        self.assertEqual(b.source_stop.iloc[-1],103)
        np.testing.assert_array_equal(b.source_start.to_numpy()[1:],b.source_stop.to_numpy()[:-1])
        self.assertEqual(b.maximum.max(),30);self.assertEqual(b.minimum.min(),-40)
        for r in b.itertuples():
            self.assertEqual(y[r.minimum_position],r.minimum)
            self.assertEqual(y[r.maximum_position],r.maximum)
    def test_wrong_hz_and_irregular_sampling_cannot_be_fft(self):
        with self.assertRaisesRegex(ValueError,'disagrees'):validate_signal([0,.1,.25],[1,2,3],sampling_hz=10)
        with self.assertRaisesRegex(ValueError,'time_unit'):validate_signal([0,1,2],[1,2,3],sampling_hz=1,time_unit='ms')
        with self.assertRaisesRegex(ValueError,'strictly'):validate_signal([0,1,1],[1,2,3])
        with self.assertRaisesRegex(ValueError,'Real samples'):validate_signal([0,1,2],[1,2+3j,4])
    def test_known_tone_peak_and_density_integral(self):
        t=np.arange(4096)/256;y=np.sin(2*np.pi*32*t)
        r=signal_spectra(t,y,sampling_hz=256,signal_unit='V',nperseg=256,noverlap=128)
        self.assertEqual(r['frequency_hz'][np.argmax(r['psd'])],32)
        self.assertAlmostEqual(np.trapz(r['psd'],r['frequency_hz']),.5,places=8)
        self.assertEqual(r['parameters']['density_unit'],'V^2/Hz')
        self.assertFalse(r['parameters']['edge_padding'])
    def test_signal_router_uses_actual_sampling(self):
        d=pd.DataFrame({'t':[0,.1,.23],'y':[1,3,2]})
        r=plan_domain_chart(d,{'intent':'signal','time':'t','y':'y','time_unit':'s','signal_unit':'V'})
        self.assertEqual(r['status'],'ready')
        self.assertFalse(any(c['construction']=='signal-time-frequency' for c in r['candidates']))
        r=plan_domain_chart(d,{'intent':'signal','time':'t','y':'y','time_unit':'s','signal_unit':'V','sampling_hz':10})
        self.assertEqual(r['status'],'needs_resolution')
    def test_ordination_zero_sites_and_duplicate_id_blocked(self):
        d=pd.DataFrame({'id':['a','a','c'],'x':[1,2,0],'y':[2,1,0]})
        r=plan_domain_chart(d,{'intent':'ordination','unit':'id','values':['x','y'],
          'transform':'hellinger','method':'pca','value_semantics':'cover_class'})
        self.assertEqual(r['status'],'needs_resolution')
        self.assertTrue(any('Zero-total' in s for s in r['blockers']))
        self.assertTrue(any('Unique' in s for s in r['blockers']))
    def test_old_intents_do_not_enter_domain_logic(self):
        self.assertIsNone(plan_domain_chart(pd.DataFrame(),{'intent':'trend'}))
    def test_complex_ordination_is_blocked_before_float_conversion(self):
        d=pd.DataFrame({'id':['a','b','c'],'x':[1+2j,2,3],'y':[3,2,1]})
        r=plan_domain_chart(d,{'intent':'ordination','unit':'id','values':['x','y'],
          'transform':'hellinger','method':'pca','value_semantics':'cover_class'})
        self.assertEqual(r['status'],'needs_resolution')
        self.assertTrue(any('real' in s for s in r['blockers']))
    def test_impedance_not_falsely_ready(self):
        d=pd.DataFrame({'f':[1,2],'r':[2,3],'i':[-1,-2]})
        r=plan_domain_chart(d,{'intent':'impedance','frequency':'f','real':'r','imaginary':'i'})
        self.assertEqual(r['status'],'needs_resolution');self.assertIsNone(r['recommended'])
    def test_spectral_display_extension_is_explicit_and_keeps_values(self):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from signal_plots import plot_spectrogram
        a={'frequency_hz':np.array([0.,1.]),'time_s':np.array([1.,2.]),
           'spectrogram':np.array([[1e-10,1.],[.1,10.]])}
        before=a['spectrogram'].copy();fig,ax=plt.subplots()
        with self.assertRaisesRegex(ValueError,'explicit extend'):
            plot_spectrogram(ax,a,limits=(.001,1.))
        _,view=plot_spectrogram(ax,a,limits=(.001,1.),out_of_range='extend')
        self.assertEqual(view['below_display_limits'],1);self.assertEqual(view['above_display_limits'],1)
        np.testing.assert_array_equal(a['spectrogram'],before);plt.close(fig)
    def test_uncomputed_endpoint_display_uses_actual_mesh_edges(self):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from signal_plots import plot_spectrogram,plot_spectral_coverage
        spectra={'frequency_hz':np.array([0.,1.]),'time_s':np.array([1.,2.,3.]),
                 'spectrogram':np.ones((2,3))}
        fig,ax=plt.subplots()
        mark,_=plot_spectrogram(ax,spectra,limits=(.1,10.))
        before=np.asarray(mark.get_array()).copy()
        coverage=plot_spectral_coverage(ax,mark,measured_time_range=(0,4))
        self.assertEqual(coverage['uncomputed_display_intervals_s'],[[0,.5],[3.5,4]])
        np.testing.assert_array_equal(mark.get_array(),before)
        plt.close(fig)

if __name__=='__main__':unittest.main()
