"""Synthetic records test declarations, not scientific/native correctness."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('diagram_handoff', ROOT/'scripts/validate_handoff.py')
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.data = {
            'schema_version':'1.1','task_id':'FIG-0001','revision':1,
            'input_kind':'concept','output_mode':'prompt_only','stage':'planned',
            'brief':dict(visual_claim='Hypothesis schematic',evidence_boundary='Not experimental evidence',source_scope='User concept only'),
            'artifacts':{},'generation':dict(status='not_run',calls_this_run=0,executed_prompt=None),
            'reference_review':dict(status='not_run',issues=[]),
            'reconstruction':dict(mode='faithful',corrections=[]),
            'routing':dict(requested_tool=None,selected_tool=None,visible_process=False),
            'checks':{k:dict(status='not_run',scope='Not executed',evidence=[]) for k in ('file','native','visual','science')}
        }
    def artifact(self,key,content='fixture'):
        p=self.base/key;p.write_text(content,encoding='utf-8')
        self.data['artifacts'][key]=dict(path=key,sha256=handoff.file_hash(p))
    def delivered_prompt(self):
        self.artifact('prompt');self.artifact('report')
        self.data['stage']='delivered'
        for name in ('file','science'):
            self.data['checks'][name]=dict(status='passed',scope='Synthetic declaration only',evidence=['report'],
                subjects={'prompt':self.data['artifacts']['prompt']['sha256']})
    def result(self):
        return handoff.validate(self.data,self.base)
    def test_planned(self):
        self.assertTrue(self.result()['passed'])
    def test_root_array(self):
        self.assertFalse(handoff.validate([],self.base)['passed'])
    def test_nested_array(self):
        self.data['brief']=[];self.assertFalse(self.result()['passed'])
    def test_numeric_file_reference(self):
        self.data['artifacts']={'x':dict(path=1,sha256=1)}
        self.assertFalse(self.result()['passed'])
    def test_unhashable_status(self):
        self.data['generation']['status']=[];self.assertFalse(self.result()['passed'])
    def test_boolean_call_count(self):
        self.data['generation']['calls_this_run']=True;self.assertFalse(self.result()['passed'])
    def test_boolean_revision(self):
        self.data['revision']=True;self.assertFalse(self.result()['passed'])
    def test_missing_artifact(self):
        self.artifact('prompt');(self.base/'prompt').unlink();self.assertFalse(self.result()['passed'])
    def test_duplicate_json(self):
        with self.assertRaises(ValueError):handoff.strict_json('{"x":1,"x":2}')
    def test_nan_json(self):
        with self.assertRaises(ValueError):handoff.strict_json('{"x":NaN}')
    def test_numeric_overflow_json(self):
        with self.assertRaises(ValueError):handoff.strict_json('{"x":1e999}')
    def test_legacy_parent_need_not_be_rewritten(self):
        previous=dict(self.data,schema_version='1.0');previous.pop('revision')
        self.artifact('previous',json.dumps(previous))
        self.data['parent']=self.data['artifacts'].pop('previous')
        self.assertTrue(self.result()['passed'])
    def test_delivered_prompt(self):
        self.delivered_prompt();self.assertTrue(self.result()['passed'])
    def test_changed_file_with_refreshed_artifact_invalidates_check(self):
        self.delivered_prompt();self.artifact('prompt','revised')
        self.assertFalse(self.result()['passed'])
    def test_missing_subject(self):
        self.delivered_prompt();del self.data['checks']['science']['subjects']
        self.assertFalse(self.result()['passed'])
    def test_missing_scientific_subject(self):
        self.delivered_prompt();self.artifact('methods')
        self.data['science_sources']=[dict(artifact='methods',locator='Methods section 2',scope='Mechanism only')]
        self.assertFalse(self.result()['passed'])
    def test_bound_scientific_subject(self):
        self.delivered_prompt();self.artifact('methods')
        self.data['science_sources']=[dict(artifact='methods',locator='Methods section 2',scope='Mechanism only')]
        self.data['checks']['science']['subjects']['methods']=self.data['artifacts']['methods']['sha256']
        self.assertTrue(self.result()['passed'])
    def test_fallback_cannot_claim_requested_output(self):
        self.delivered_prompt();self.data['requested_output_mode']='editable'
        self.assertFalse(self.result()['passed'])
        self.data['requested_output_fulfilled']=False
        self.assertTrue(self.result()['passed'])
    def test_parent_hash_and_identity(self):
        self.artifact('previous',json.dumps(dict(self.data)))
        self.data['revision']=2;self.data['parent']=self.data['artifacts'].pop('previous')
        self.assertTrue(self.result()['passed'])
        (self.base/'previous').write_text('{}')
        self.assertFalse(self.result()['passed'])
    def test_legacy_illustrator(self):
        self.legacy('illustrator')
    def test_legacy_powerpoint(self):
        self.legacy('powerpoint')
    def test_legacy_visio(self):
        self.legacy('visio')
    def legacy(self,tool):
        p=ROOT/'evaluations/2026-10-31-integration'/f'handoff-{tool}.json'
        result=handoff.validate(handoff.strict_json(p.read_text('utf-8-sig')),p.parent)
        self.assertTrue(result['passed'],result)
        self.assertTrue(result['warnings'])
    def test_native_audit_requires_scene_binding(self):
        p=ROOT/'evaluations/2026-10-31-integration/handoff-powerpoint.json'
        self.data=handoff.strict_json(p.read_text('utf-8-sig'))
        self.data.update(schema_version='1.1',revision=1)
        for ref in self.data['artifacts'].values():
            ref['path']=str((p.parent/ref['path']).resolve())
        for name in ('file','native','visual','science'):
            self.data['checks'][name]['subjects']={k:v['sha256'] for k,v in self.data['artifacts'].items()}
        self.assertFalse(self.result()['passed'])
        self.assertTrue(any('scene hash' in x for x in self.result()['errors']))
    def test_cli_error_is_json(self):
        p=self.base/'bad.json';p.write_text('{"x":NaN}')
        r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/validate_handoff.py'),str(p)],capture_output=True,text=True)
        self.assertEqual(r.returncode,1);self.assertFalse(json.loads(r.stdout)['passed'])
        self.assertNotIn('Traceback',r.stderr)
    def test_check_is_read_only(self):
        self.delivered_prompt()
        before={p.name:p.read_bytes() for p in self.base.iterdir()}
        self.assertTrue(self.result()['passed'])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.base.iterdir()})
    def test_parent_task_mismatch(self):
        previous=dict(self.data,task_id='OTHER')
        self.artifact('previous',json.dumps(previous))
        self.data.update(revision=2,parent=self.data['artifacts'].pop('previous'))
        self.assertFalse(self.result()['passed'])
    def test_generated_reference_is_not_its_own_science(self):
        self.delivered_prompt();self.artifact('reference');self.data['output_mode']='image'
        self.data['generation']=dict(status='generated',calls_this_run=1,executed_prompt='prompt',selection='builtin')
        self.data['prompt_delivery']=dict(artifact='prompt',channel='inline',before_call=True)
        self.data['reference_review']['status']='passed'
        self.data['checks']['visual']=copy.deepcopy(self.data['checks']['science'])
        self.data['science_sources']=[dict(artifact='reference',locator='Whole image',scope='Invented self-support')]
        for name in ('file','visual','science'):
            self.data['checks'][name]['subjects']={'reference':self.data['artifacts']['reference']['sha256']}
        result=self.result()
        self.assertFalse(result['passed'])
        self.assertTrue(any('own scientific source' in e for e in result['errors']))
    def test_v11_native_declarations_bind_final_and_scene(self):
        p=ROOT/'evaluations/2026-10-31-integration/handoff-powerpoint.json'
        self.data=handoff.strict_json(p.read_text('utf-8-sig'))
        self.data.update(schema_version='1.1',revision=1)
        for ref in self.data['artifacts'].values():ref['path']=str((p.parent/ref['path']).resolve())
        report={'passed':True,'sha256':self.data['artifacts']['final_native']['sha256'],
                'scene_sha256':self.data['artifacts']['scene']['sha256'],
                'scope':'Synthetic declaration binding test, NOT a new desktop check'}
        self.artifact('native_audit',json.dumps(report))
        for name in ('file','native','visual','science'):
            self.data['checks'][name]['subjects']={k:v['sha256'] for k,v in self.data['artifacts'].items()}
        self.assertTrue(self.result()['passed'],self.result())
        report['scene_sha256']='0'*64;self.artifact('native_audit',json.dumps(report))
        for check in self.data['checks'].values():check['subjects']['native_audit']=self.data['artifacts']['native_audit']['sha256']
        self.assertFalse(self.result()['passed'])

if __name__=='__main__':
    unittest.main()
