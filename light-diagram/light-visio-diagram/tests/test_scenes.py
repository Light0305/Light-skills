import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('scene_backend',ROOT/'scripts/render_scene.py')
backend=importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)

class SceneTests(unittest.TestCase):
    def setUp(self):
        self.scene={'schema_version':'1.0','font':'Arial','font_bold':'Arial-BoldMT','points_per_pixel':.75,
            'canvas':dict(width_px=400,height_px=200,pixels_per_inch=96),
            'layers':[dict(id='main',name='Main')],'groups':[dict(id='group',layer='main')],
            'pages':[dict(name='Fixture',slug='fixture',nodes=[
                dict(id='A',group='group',type='rect',bbox=[20,60,100,50],text='A',style=dict(font_px=18)),
                dict(id='B',group='group',type='ellipse',bbox=[280,60,100,50],text='B')],
                paths=[],edges=[dict(id='edge',group='group',points=[[120,85],[280,85]],
                    source=dict(node='A',anchor=[1,.5]),target=dict(node='B',anchor=[0,.5]))],
                draw_order=['A','B','edge'])]}
    def reject(self,change):
        change(self.scene)
        with self.assertRaises(ValueError):backend.validate(self.scene)
    def test_valid(self):backend.validate(self.scene)
    def test_root_array(self):
        with self.assertRaises(ValueError):backend.validate([])
    def test_missing_bbox(self):self.reject(lambda s:s['pages'][0]['nodes'][0].pop('bbox'))
    def test_boolean_canvas(self):self.reject(lambda s:s['canvas'].update(width_px=True))
    def test_infinite_scale(self):self.reject(lambda s:s.update(points_per_pixel=float('inf')) if 'AI'=='VISIO' else s['canvas'].update(pixels_per_inch=float('inf')))
    def test_boolean_scale(self):self.reject(lambda s:s.update(points_per_pixel=True) if 'AI'=='VISIO' else s['canvas'].update(pixels_per_inch=True))
    def test_empty_path(self):self.reject(lambda s:s['pages'][0]['paths'].append(dict(id='path',group='group',points=[])))
    def test_short_polygon(self):self.reject(lambda s:s['pages'][0]['nodes'][0].update(type='polygon',points=[[20,60],[20,60]]))
    def test_unknown_curve(self):self.reject(lambda s:s['pages'][0]['edges'][0].update(curve='magic'))
    def test_boolean_point(self):self.reject(lambda s:s['pages'][0]['edges'][0]['points'][0].__setitem__(0,True))
    def test_missing_endpoint(self):self.reject(lambda s:s['pages'][0]['edges'][0]['target'].update(node='missing'))
    def test_negative_font(self):self.reject(lambda s:s['pages'][0]['nodes'][0]['style'].update(font_px=-1))
    def test_bad_color(self):self.reject(lambda s:s['pages'][0]['nodes'][0]['style'].update(stroke='#xx0000'))
    def test_bad_anchor(self):self.reject(lambda s:s['pages'][0]['edges'][0]['source'].update(anchor=[True,.5]))
    def test_duplicate_id(self):self.reject(lambda s:s['pages'][0]['nodes'][1].update(id='A'))
    def test_historical_scenes(self):
        for path in (ROOT/'evaluations').glob('*/scene.json'):
            with self.subTest(path=path.name):backend.validate(json.loads(path.read_text('utf-8-sig')))
    def test_path_only_empty(self):self.reject(lambda s:s['pages'][0].update(nodes=[],edges=[],paths=[dict(id='p',points=[])]))
    def test_wrong_text_type(self):self.reject(lambda s:s['pages'][0]['nodes'][0].update(text=[]))

if __name__=='__main__':unittest.main()
