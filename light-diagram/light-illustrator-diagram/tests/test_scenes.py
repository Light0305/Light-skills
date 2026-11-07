import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('scene_backend',ROOT/'scripts/illustrator.py')
backend=importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)

class SceneTests(unittest.TestCase):
    def setUp(self):
        self.scene={'schema_version':'1.1','font':'ArialMT','font_bold':'Arial-BoldMT','points_per_pixel':.75,
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
    def test_infinite_scale(self):self.reject(lambda s:s.update(points_per_pixel=float('inf')) if 'AI'=='AI' else s['canvas'].update(pixels_per_inch=float('inf')))
    def test_boolean_scale(self):self.reject(lambda s:s.update(points_per_pixel=True) if 'AI'=='AI' else s['canvas'].update(pixels_per_inch=True))
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
    def test_text_run_outside_native_text(self):self.reject(lambda s:s['pages'][0]['nodes'][0].update(native_text='X',text_runs=[dict(start=1,length=1)]))
    def test_invalid_gradient(self):self.reject(lambda s:s['pages'][0]['nodes'][0]['style'].update(gradient_type='magic'))
    def test_bridge_failure_keeps_diagnostic_not_audit(self):
        import sys,tempfile
        from types import SimpleNamespace
        from unittest.mock import patch
        def fail(_):raise RuntimeError('synthetic server failure')
        app=SimpleNamespace(DoJavaScript=fail)
        client=SimpleNamespace(Dispatch=lambda _:app)
        modules={'win32com':SimpleNamespace(client=client),'win32com.client':client,
                 'pythoncom':SimpleNamespace(CoInitialize=lambda:None,CoUninitialize=lambda:None)}
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);scene=folder/'scene.json';scene.write_text(json.dumps(self.scene))
            args=['illustrator.py','render',str(scene),str(folder/'fixture.ai'),'--stem',str(folder/'run')]
            with patch.dict(sys.modules,modules),patch.object(sys,'argv',args),patch.object(backend,'foreground',lambda:None):
                with self.assertRaises(RuntimeError):backend.main()
            report=json.loads((folder/'run.failure.json').read_text('utf-8'))
            self.assertFalse(report['passed']);self.assertEqual(report['phase'],'execute')
            self.assertFalse((folder/'run.render.json').exists())
    def test_invalid_under_optimized_python(self):
        import subprocess,sys,tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.json';s=copy.deepcopy(self.scene);s['pages'][0]['nodes'][0]['bbox']=[1,1,-3,4];p.write_text(json.dumps(s))
            result=subprocess.run([sys.executable,'-O','-B',str(ROOT/'scripts/illustrator.py'),'validate',str(p)],capture_output=True)
            self.assertNotEqual(result.returncode,0)

if __name__=='__main__':unittest.main()
