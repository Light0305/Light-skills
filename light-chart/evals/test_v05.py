"""Observable routing, typography, scientific encoding and runtime invariants."""
from pathlib import Path
import json
import os
import sys
import subprocess
import tempfile
import unittest
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import fitz

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/light-chart/scripts'))
from library import search,route
from project_style import load_project,project_context,colors_for,current_project
from research_panels import paired_changes,joint_density,image_panel,network_panel
from setup_style import configure_chinese_fonts
from publication import audit_exported
from r_runtime import child_environment,run_r


class OperationalBehavior(unittest.TestCase):
    def test_routing_CLI_outputs_UTF8_under_English_Windows_encoding(self):
        env=dict(os.environ,PYTHONIOENCODING='cp1252')
        result=subprocess.run([sys.executable,str(ROOT/'skills/light-chart/scripts/library.py'),'route','--query','火山图'],
          capture_output=True,env=env,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8',errors='replace'))
        data=json.loads(result.stdout.decode('utf-8'))
        self.assertEqual(data['entrypoints'][0]['symbol'],'plot_volcano')

    def test_task_queries_find_real_functions_and_respect_language(self):
        for query,symbol in [('火山图','plot_volcano'),('volcano','plot_volcano'),
          ('draw an ROC curve','plot_roc'),('请按受试者做前后变化图','paired_changes'),
          ('联合密度和边缘分布','joint_density'),('显微图像板和比例尺','image_panel'),
          ('气泡图','plot_dotplot')]:
            hits=search(query,limit=3)
            self.assertTrue(any(h.get('symbol')==symbol for h in hits),(query,hits))
        roc=search('ROC',limit=20)
        self.assertFalse(any('preprocessor' in x['path'] for x in roc))
        result=route('请用R画生存曲线并给风险表',backend='r')
        self.assertEqual(result['entrypoints'][0]['symbol'],'survival_panel_r')
        self.assertEqual({r['source'] for r in result['source_routes']},
                         {'nature-figure','SciPilot','Light-Science','figures4papers'})
        self.assertFalse(any(r.get('backend')=='python' for r in search('热图',backend='r')))
        self.assertEqual(route('用 R 画注释热图')['entrypoints'][0]['backend'],'r')
        pca=route('PCA',backend='r')
        self.assertEqual(pca['status'],'implementation_found')
        self.assertTrue(any('hellinger_pca_r' in r.get('symbol','') for r in pca['entrypoints']))
        partial=route('UMAP + 热图')
        self.assertIn('umap',partial['unimplemented_concepts'])
        self.assertEqual(partial['status'],'partial_implementation')

    def test_project_mapping_survives_reordering_and_does_not_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            project=load_project();project.pop('_path');project.pop('_sha256')
            project['groups']={'Control':{'color':'#226D8D'},'Treatment':{'color':'#CA7259'}}
            p=Path(tmp)/'project.json';p.write_text(json.dumps(project),encoding='utf-8')
            old=list(plt.rcParams['font.family'])
            with project_context(p):
                self.assertEqual(colors_for(['Treatment','Control']),['#CA7259','#226D8D'])
                with self.assertRaises(ValueError):colors_for(['Unknown'])
            self.assertEqual(list(plt.rcParams['font.family']),old)
            self.assertEqual(current_project()['groups'],{})

    def test_matched_pairs_are_id_based_and_reject_missing_or_duplicate_records(self):
        d=pd.DataFrame({'id':['b','a','b','a'],'condition':['post','pre','pre','post'],'value':[9,2,5,3]})
        wide=paired_changes(d,id='id',condition='condition',value='value',order=['pre','post'])
        self.assertEqual(wide.loc['a','change'],1);self.assertEqual(wide.loc['b','change'],4)
        for bad in (d.iloc[:-1],pd.concat([d,d.iloc[:1]])):
            with self.assertRaises(ValueError):paired_changes(bad,id='id',condition='condition',value='value',order=['pre','post'])

    def test_custom_roles_reach_actual_benchmark_artists(self):
        import importlib.util
        from editorial import figure_style
        from matplotlib.colors import to_hex
        spec=importlib.util.spec_from_file_location('benchmark_style_probe',ROOT/'skills/light-chart/assets/examples/benchmark.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            data=load_project();data['roles']['primary']='#6B3F8C';data['roles']['baseline']='#5C626A'
            p=Path(tmp)/'style.json';p.write_text(json.dumps(data),encoding='utf-8')
            with figure_style(project=p):
                fig,axes,_=module.method_comparison(module.read('immunostruct.json'))
                colors={to_hex(line.get_color()).lower() for line in axes[0].lines}
                self.assertIn('#6b3f8c',colors);self.assertIn('#5c626a',colors)
                self.assertNotIn('#226d8d',colors)
                plt.close(fig)

    def test_joint_counts_cover_the_same_records(self):
        fig=plt.figure();axes=[fig.add_subplot(2,2,i) for i in (1,2,3)]
        x=np.array([0,0,1,2,3,4,4.]);y=np.array([1,1,3,2,5,7,8.])
        result=joint_density(*axes,x,y)
        self.assertEqual(result['hexbin_total'],7)
        self.assertEqual(result['x_hist_total'],7);self.assertEqual(result['y_hist_total'],7)
        with self.assertRaises(ValueError):joint_density(*axes,x,y,limits=[0,2,0,9])
        plt.close(fig)

    def test_image_pixels_calibration_and_network_topology_are_not_invented(self):
        fig,ax=plt.subplots();a=np.arange(600).reshape(20,30);copy=a.copy()
        meta=image_panel(ax,a,pixel_size=.5,unit='μm',limits=[0,600],scale_bar=3,crop=(2,18,4,28))
        np.testing.assert_array_equal(ax.images[0].get_array(),a[2:18,4:28])
        np.testing.assert_array_equal(a,copy)
        self.assertEqual(meta['display_shape'],[16,24])
        with self.assertRaises(ValueError):image_panel(ax,a,pixel_size=0,unit='μm',limits=[0,600],scale_bar=3)
        with self.assertRaises(ValueError):network_panel(ax,['A','B'],[[0,0],[1,1]],[('A','C',1)])
        plt.close(fig)

    def test_latin_digits_and_chinese_use_distinct_embedded_faces(self):
        with tempfile.TemporaryDirectory() as tmp,matplotlib.rc_context():
            configure_chinese_fonts(serif_for_zh=True)
            fig=plt.figure(figsize=(3,1));fig.text(.1,.5,'图示 12.5 mm',fontsize=9)
            file=Path(tmp)/'mixed.pdf';fig.savefig(file);plt.close(fig)
            with fitz.open(file) as pdf:
                spans=[span for b in pdf[0].get_text('dict')['blocks'] if 'lines' in b for line in b['lines'] for span in line['spans']]
            latin=[s for s in spans if '12.5' in s['text']]
            chinese=[s for s in spans if '图' in s['text'] or '示' in s['text']]
            self.assertTrue(latin);self.assertTrue(chinese)
            self.assertTrue(all('Times' in s['font'] or 'DejaVuSerif' in s['font'] for s in latin),spans)
            self.assertTrue(all(s['font']!=latin[0]['font'] for s in chinese),spans)

    def test_final_file_rejects_text_below_project_minimum(self):
        with tempfile.TemporaryDirectory() as tmp:
            fig=plt.figure(figsize=(3,1));fig.text(.1,.5,'Unreadable small label',fontsize=5.5)
            p=Path(tmp)/'too-small.pdf';fig.savefig(p);plt.close(fig)
            report=audit_exported(p)
            self.assertEqual(report['automated_status'],'FAIL')
            self.assertGreater(report['pdf_text']['below_minimum_count'],0)

    @unittest.skipUnless(os.name=='nt','Windows launcher regression')
    def test_R_child_has_real_architecture_and_errors_remain_errors(self):
        env,changes=child_environment({'PATH':os.environ['PATH'],'LC_ALL':'C.UTF-8'})
        self.assertIn(env['PROCESSOR_ARCHITECTURE'],{'AMD64','ARM64','x86'})
        self.assertNotIn('LC_ALL',env)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.R';p.write_text('stop("intentional failure")\n',encoding='utf-8')
            result=run_r(p,timeout=15)
            self.assertNotEqual(result['returncode'],0)
            self.assertEqual(result['status'],'FAIL')


if __name__=='__main__':unittest.main()
