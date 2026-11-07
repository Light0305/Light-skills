"""Behavioral failures beyond the worked datasets, not image-style snapshots."""
from pathlib import Path
import sys
import json
import tempfile
import unittest
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/light-chart/scripts'))
from evidence_tools import plan_evidence,audit_evidence_layout
from color_tools import audit_palette,continuous_scale,simulate_colors,audit_rendered_mapping
from composition import compose,LayoutError
from image_layout import image_plate,link_roi
from field_tools import grid_field,field_surface,volume_isosurface
from research_panels import image_panel
from review_tools import figure_snapshot,bind_exports,compare_revisions
from project_style import project_context,encodings_for


class AdvancedBehavior(unittest.TestCase):
    def tearDown(self):plt.close('all')
    def contract(self):
        d=pd.DataFrame({'unit':['x','y','z'],'v':[2.,5.,3.],'group':['a','a','b']})
        spec={'question':'What is observed?','claims':{'c':{'required_roles':['primary','boundary'],'boundary':'descriptive'}},
          'panels':[{'id':'main','source':'one','role':'primary','claim':'c','question':'Which values?',
              'chart':{'intent':'compare','unit':'unit','y':'v','group':'group'}},
            {'id':'limit','source':'two','role':'boundary','claim':'c','question':'Where does it fail?',
              'chart':{'intent':'distribution','unit':'unit','y':'v'},'depends_on':['main']}]}
        return {'one':d,'two':d.copy()},spec

    def test_missing_evidence_role_blocks_claim(self):
        tables,s=self.contract();s['panels']=s['panels'][:1]
        p=plan_evidence(tables,s);self.assertEqual(p['status'],'needs_resolution')
        self.assertIn('boundary',p['blockers'][0])

    def test_false_independence_and_source_mutation_are_detected(self):
        tables,s=self.contract();p=plan_evidence(tables,s)
        s['panels'][1]['independence']={'from':'main','key':'unit'}
        self.assertEqual(plan_evidence(tables,s)['status'],'needs_resolution')
        tables['two'].loc[0,'v']=99
        self.assertNotEqual(p['source_data_sha256'],plan_evidence(tables,s)['source_data_sha256'])

    def test_dependency_cycle_and_exact_selection(self):
        tables,s=self.contract();s['panels'][0]['select']={'group':['a']}
        self.assertEqual(plan_evidence(tables,s)['panels']['main']['source_positions'],[0,1])
        s['panels'][0]['depends_on']=['limit']
        with self.assertRaisesRegex(ValueError,'cycle'):plan_evidence(tables,s)

    def test_renaming_same_table_does_not_make_new_evidence(self):
        tables,s=self.contract();s['panels'][1]['chart']=dict(s['panels'][0]['chart'])
        p=plan_evidence(tables,s)
        self.assertTrue(any('not independent validation' in w for w in p['warnings']))

    def test_layout_cannot_drop_a_required_boundary(self):
        tables,s=self.contract();p=plan_evidence(tables,s)
        check=audit_evidence_layout(p,{'plot_rectangles_mm':{'main':[0,0,60,40]}})
        self.assertEqual(check['status'],'FAIL')

    def test_diverging_requires_real_center_and_no_value_clipping(self):
        with self.assertRaises(ValueError):continuous_scale([-1,0,2],mode='diverging')
        norm,_,_=continuous_scale([-1,0,2],mode='diverging',center=0)
        np.testing.assert_allclose(norm([-1,0,2]),[0,.5,1])
        with self.assertRaises(ValueError):continuous_scale([0,10],limits=(0,5))
        self.assertEqual(continuous_scale(np.arange(5),cmap='jet')[2]['status'],'REVIEW_REQUIRED')

    def test_alpha_and_duplicate_color_redundancy_stay_visible(self):
        enc={'x':{'color':'#0072B2','marker':'o'},'y':{'color':'#0072B2','marker':'s'}}
        r=audit_palette(enc)
        self.assertTrue(all(p['redundant_channel'] for p in r['modes']['normal']['pairs']))
        self.assertTrue(r['findings'])
        self.assertTrue(any(f['code']=='low_mark_contrast' for f in audit_palette(enc,alpha=.1)['findings']))
        np.testing.assert_allclose(simulate_colors(['white','black'],'deutan'),[[1,1,1],[0,0,0]],atol=1e-5)

    def test_named_encodings_do_not_follow_request_order(self):
        path=Path(__file__).resolve().parents[1]/'skills/light-chart/assets/project-style.json'
        d=json.loads(path.read_text());d['groups']={'a':{'color':'#0072B2','marker':'o'},'b':{'color':'#B65022','marker':'^'}}
        with project_context(d):
            self.assertEqual(encodings_for(['b','a'])['a'],d['groups']['a'])
            with self.assertRaises(ValueError):encodings_for(['unknown'])

    def test_equal_pixel_layout_and_source_roi_link(self):
        a=np.arange(120*200).reshape(120,200)
        common=dict(pixels=a,pixel_size=1,unit='px',limits=[0,24000],scale_bar=15,equal_pixel_group='acquisition')
        c,records=image_plate((140,85),[['full','crop']],{'full':common,'crop':{**common,'crop':(20,100,20,120)}})
        link_roi(c,records,'full','crop',label='I')
        r=c.fit()['plot_rectangles_mm']
        self.assertAlmostEqual(r['full'][2]/200,r['crop'][2]/100,places=5)
        np.testing.assert_array_equal(c.axes['crop'].images[0].get_array(),a[20:100,20:120])
        records['crop']['source_sha256']='different'
        with self.assertRaises(ValueError):link_roi(c,records,'full','crop',label='wrong')

    def test_rgb_stays_native_and_invalid_range_is_not_clipped(self):
        _,ax=plt.subplots();a=np.zeros((20,30,3),dtype='uint8');a[:,:,0]=120
        image_panel(ax,a,pixel_size=1,unit='px',limits=None,scale_bar=5)
        np.testing.assert_array_equal(ax.images[0].get_array(),a)
        with self.assertRaises(ValueError):image_panel(ax,a.astype(float),pixel_size=1,unit='px',limits=None,scale_bar=5)

    def test_3d_snapshot_ignores_camera_but_catches_mesh_changes(self):
        c=compose((110,100),[['surface']],panels={'surface':{'projection':'3d','min_plot_mm':[35,35]}})
        z=np.array([[1.,2.,1.],[2.,4.,2.],[1.,2.,1.]])
        field=grid_field([0,1,2],[0,1,2],z,limits=(0,5))
        surface=field_surface(c.axes['surface'],field);c.figure.canvas.draw()
        a=figure_snapshot(c.figure);c.axes['surface'].view_init(elev=43,azim=100);c.figure.canvas.draw()
        self.assertEqual(a['panels'],figure_snapshot(c.figure)['panels'])
        if hasattr(surface,'_faces'):surface._faces[0,0,2]=3.5
        else:surface._vec[2,0]=3.5
        self.assertNotEqual(a['panels'],figure_snapshot(c.figure)['panels'])

    def test_helper_colorbar_has_no_panel_letter(self):
        c=compose((120,80),[['data','bar']],panels={'bar':{'panel_label':False}})
        self.assertEqual(len(c.labels()),1)

    def test_anisotropic_sections_use_common_physical_magnification(self):
        c=compose((150,90),[['xy','xz']],width_ratios=[1.3,1],panels={
            'xy':{'plot_aspect':1,'equal_unit_group':'um','data_span':[30,30]},
            'xz':{'plot_aspect':2,'equal_unit_group':'um','data_span':[15,30]}})
        r=c.fit()['plot_rectangles_mm']
        self.assertAlmostEqual(r['xy'][2],r['xz'][2],places=5)
        self.assertAlmostEqual(r['xy'][3]/30,r['xz'][3]/15,places=5)

    def test_unbound_source_cannot_claim_revision_equivalence(self):
        with tempfile.TemporaryDirectory() as tmp:
            fig,ax=plt.subplots();ax.plot([0,1],[0,1]);pdf=Path(tmp)/'a.pdf';fig.savefig(pdf)
            r=bind_exports({'figure_snapshot':figure_snapshot(fig)},pdf=pdf)
            self.assertTrue(compare_revisions(r,r)['errors'])

    def test_actual_artist_identity_drift_is_not_hidden_by_correct_config(self):
        fig,ax=plt.subplots();ax.plot([0,1],[0,1],label='a',color='#B65022')
        project={'groups':{'a':{'color':'#0072B2'}}}
        self.assertEqual(audit_rendered_mapping(figure_snapshot(fig),project)['status'],'FAIL')

    def test_true_volume_mesh_keeps_spacing_and_open_boundary(self):
        z,y,x=np.indices((5,6,7));a=((z-2)**2+(y-3)**2+(x-3)**2).astype(float)
        fig=plt.figure();ax=fig.add_subplot(projection='3d')
        _,report,vertices,faces=volume_isosurface(ax,a,spacing=(2,1,.5),origin=(10,20,30),level=5.)
        self.assertTrue(report['material_lighting'])
        self.assertGreater(len(faces),0)
        self.assertGreaterEqual(vertices[:,0].min(),30)
        self.assertGreaterEqual(vertices[:,2].min(),10)
        self.assertTrue(report['touches_crop_boundary'])
        self.assertEqual(report['spacing'],[2.,1.,.5])
        with self.assertRaises(ValueError):volume_isosurface(ax,a,spacing=(2,0,.5),level=5)


if __name__=='__main__':unittest.main()
