"""Calibrated coordinates and raw-image conservation beyond any worked dataset."""
from pathlib import Path
import sys
import unittest

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/light-chart/scripts'))
from field_tools import volume_isosurface
from image_layout import image_plate, link_roi, orthogonal_slice
from research_panels import image_panel


class ImageCalibration(unittest.TestCase):
    def tearDown(self):
        plt.close('all')

    def test_legacy_scalar_keeps_crop_local_edges_and_pixels(self):
        pixels = np.arange(600).reshape(20,30)
        original = pixels.copy()
        fig, ax = plt.subplots()
        record = image_panel(ax,pixels,pixel_size=.5,unit='um',limits=(0,600),scale_bar=3,crop=(2,18,4,28))
        np.testing.assert_array_equal(ax.images[0].get_array(),pixels[2:18,4:28])
        np.testing.assert_array_equal(ax.images[0].get_extent(),[0,12,8,0])
        np.testing.assert_array_equal(pixels,original)
        self.assertEqual(record['pixel_size'],.5)
        self.assertIsNone(record['center_origin'])
        self.assertAlmostEqual(np.ptp(ax.lines[0].get_xdata()),3)

    def test_rectangular_pixels_keep_source_centres_and_physical_scale(self):
        fig,ax=plt.subplots(figsize=(4,4))
        pixels=np.arange(14*9).reshape(14,9)
        record=image_panel(ax,pixels,pixel_size=(2,.5),unit='um',center_origin=(10,-3),
                           limits=(0,126),scale_bar=1,crop=(2,11,3,8))
        np.testing.assert_allclose(ax.images[0].get_extent(),[-1.75,.75,31,13])
        np.testing.assert_array_equal(ax.images[0].get_array(),pixels[2:11,3:8])
        fig.canvas.draw()
        p=ax.transData.transform([[0,20],[1,20],[0,21]])
        self.assertAlmostEqual(np.linalg.norm(p[1]-p[0]),np.linalg.norm(p[2]-p[0]),places=10)
        self.assertEqual(record['pixel_spacing'],[2,.5])
        self.assertAlmostEqual(np.ptp(ax.lines[0].get_xdata()),1)

    def test_anisotropic_nested_roi_uses_parent_absolute_coordinate_system(self):
        pixels=np.arange(20*22).reshape(20,22)
        common=dict(pixels=pixels,pixel_size=(2,.5),unit='um',limits=(0,440),scale_bar=1,center_origin=(10,-3))
        c,records=image_plate((140,120),[['parent','child']],{
            'parent':{**common,'crop':(1,14,2,16)},'child':{**common,'crop':(4,10,6,12)}})
        roi=link_roi(c,records,'parent','child',label='I')
        np.testing.assert_allclose([*roi.get_xy(),roi.get_width(),roi.get_height()],[-.25,17,3,12])
        records['child']['center_origin']=[11,-3]
        with self.assertRaises(ValueError):link_roi(c,records,'parent','child',label='changed origin')

    def test_legacy_nested_roi_keeps_parent_crop_local_frame(self):
        pixels=np.zeros((20,30))
        common=dict(pixels=pixels,pixel_size=.5,unit='um',limits=(0,1),scale_bar=1)
        c,r=image_plate((140,90),[['parent','child']],{
            'parent':{**common,'crop':(2,18,4,28)},'child':{**common,'crop':(5,13,9,19)}})
        roi=link_roi(c,r,'parent','child',label='I')
        np.testing.assert_allclose([*roi.get_xy(),roi.get_width(),roi.get_height()],[2.5,1.5,5,4])

    def test_different_plane_sampling_shares_physical_magnification(self):
        a=np.zeros((20,40));b=np.zeros((40,40))
        c,r=image_plate((140,120),[['a','b']],{
            'a':dict(pixels=a,pixel_size=(2,.5),unit='um',limits=(0,1),scale_bar=3,equal_unit_group='um'),
            'b':dict(pixels=b,pixel_size=.5,unit='um',limits=(0,1),scale_bar=3,equal_unit_group='um')},
            panels={'a':{'min_plot_mm':[10,10]},'b':{'min_plot_mm':[10,10]}})
        c.fit()
        scales=[]
        for key in ['a','b']:
            ax=c.axes[key]
            p=ax.transData.transform([[0,0],[1,0],[0,1]])
            scales.extend([np.linalg.norm(p[1]-p[0]),np.linalg.norm(p[2]-p[0])])
        np.testing.assert_allclose(scales,np.repeat(scales[0],4),atol=1e-10)
        self.assertEqual(c.panels['a']['plot_aspect'],.5)
        self.assertEqual(c.panels['b']['plot_aspect'],1)

    def test_pixel_groups_and_mixed_length_units_cannot_hide_unequal_scale(self):
        common=dict(pixels=np.zeros((20,30)),pixel_size=(2,.5),unit='um',limits=(0,1),scale_bar=1)
        with self.assertRaisesRegex(ValueError,'equal_unit_group'):
            image_plate((140,90),[['a']],{'a':{**common,'equal_pixel_group':'p'}})
        with self.assertRaisesRegex(ValueError,'identical declared units'):
            image_plate((140,90),[['a','b']],{
                'a':{**common,'equal_unit_group':'g'},'b':{**common,'unit':'mm','equal_unit_group':'g'}})

    def test_plane_extraction_preserves_axes_indices_and_voxel_centre_origin(self):
        zi,yi,xi=np.indices((5,7,11));volume=10000*zi+100*yi+xi;copy=volume.copy()
        cases=[('xy',2,volume[2,:,:],[.5,2],[-2,10],10),
               ('xz',3,volume[:,3,:],[3,2],[4,10],-.5),
               ('yz',5,volume[:,:,5],[3,.5],[4,-2],20)]
        for plane,index,expected,spacing,origin,fixed in cases:
            result=orthogonal_slice(volume,plane=plane,index=index,spacing=(3,.5,2),origin=(4,-2,10))
            np.testing.assert_array_equal(result['pixels'],expected)
            self.assertEqual(result['pixel_size'],spacing)
            self.assertEqual(result['center_origin'],origin)
            self.assertEqual(result['coordinate'],fixed)
            self.assertFalse(result['pixels'].flags.writeable)
        np.testing.assert_array_equal(volume,copy)

    def test_scientific_channels_require_explicit_selection(self):
        raw=np.ones((5,7,11,3),dtype=np.uint16)
        with self.assertRaisesRegex(ValueError,'select any channel first'):
            orthogonal_slice(raw,plane='xy',index=2,spacing=(1,1,1))
        fig,ax=plt.subplots()
        with self.assertRaisesRegex(ValueError,'RGB must'):
            image_panel(ax,raw[0],pixel_size=1,unit='px',limits=None,scale_bar=1)
        rgb=np.zeros((10,12,3),dtype=np.uint8);rgb[:,:,1]=127
        image_panel(ax,rgb,pixel_size=1,unit='px',limits=None,scale_bar=2)
        np.testing.assert_array_equal(ax.images[0].get_array(),rgb)

    def test_invalid_slice_indices_or_masks_are_not_silently_repaired(self):
        a=np.zeros((4,5,6))
        for index in [-1,4,1.5,True]:
            with self.assertRaises(ValueError):orthogonal_slice(a,plane='xy',index=index,spacing=(1,1,1))
        mask=np.ma.array(a,mask=False);mask.mask[1,1,1]=True
        with self.assertRaisesRegex(ValueError,'Masked voxels'):
            orthogonal_slice(mask,plane='xy',index=2,spacing=(1,1,1))

    def test_large_world_origin_keeps_fractional_isovalue_coordinates(self):
        a=np.broadcast_to(np.arange(4,dtype=np.float32)[:,None,None],(4,5,6)).copy()
        fig=plt.figure();ax=fig.add_subplot(projection='3d')
        _,report,xyz,_=volume_isosurface(ax,a,spacing=(1,1,1),origin=(1e7,0,0),level=1.5)
        np.testing.assert_array_equal(xyz[:,2],np.repeat(1e7+1.5,len(xyz)))
        self.assertTrue(report['touches_crop_boundary'])

    def test_boundary_flag_is_independent_of_origin_and_length_unit(self):
        z,y,x=np.indices((11,13,15),dtype=float)
        a=1-((z-5)/3)**2-((y-6)/4)**2-((x-7)/5)**2
        for scale in [1e-6,1,1e6]:
            for origin in [(0,0,0),(1e7,-1e7,2e7)]:
                fig=plt.figure();ax=fig.add_subplot(projection='3d')
                _,report,xyz,faces=volume_isosurface(ax,a,spacing=np.array([2,.7,.3])*scale,origin=origin,level=0)
                self.assertFalse(report['touches_crop_boundary'])
                plt.close(fig)


if __name__=='__main__':
    unittest.main(verbosity=2)
