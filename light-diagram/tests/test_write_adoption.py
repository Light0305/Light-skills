"""Synthetic FIG-to-Write file adoption only; no semantic certification."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
WRITER=ROOT.parent/'light-write/scripts/audit_manuscript.py'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
h=module('figure_handoff',ROOT/'scripts/validate_handoff.py')

@unittest.skipUnless(WRITER.is_file(),'Adjacent Write source not installed')
class WriteAdoptionTests(unittest.TestCase):
    def setUp(self):
        self.writer=module('figure_writer',WRITER)
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.base=Path(tmp.name)
        self.prompt=self.base/'Figure/Methods/FIG-0001/prompt-v1.txt';self.prompt.parent.mkdir(parents=True)
        self.prompt.write_text('Synthetic plan: a labelled A-to-B schematic. This is a concept, not a research result.',encoding='utf-8')
        self.draft=self.base/'manuscript.md'
        body='Figure 1 is a conceptual A-to-B schematic.'
        self.draft.write_text(body,encoding='utf-8')
        def ref(p):return {'path':str(p),'sha256':h.file_hash(p)}
        self.packet={'schema_version':'1.0','basis':'Synthetic declared figure-version adoption only',
            'manuscript':{'paper_id':'PAPER-0001','revision':'v01',**ref(self.draft)},
            'sources':[{'id':'FIG1','role':'figure_prompt',**ref(self.prompt)}],
            'claims':[{'id':'C1','anchor':body,'status':'supported','boundary':'Concept only, no causal evidence',
                       'evidence':[{'source_id':'FIG1','locator':'FIG-0001 prompt-v1.txt'}]}],
            'protected_literals':[],'parent':None}
    def test_current_figure_adoption_is_read_only(self):
        before={str(p):p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        self.assertTrue(self.writer.audit(self.packet,self.base)['checks_passed'])
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.base.rglob('*') if p.is_file()})
    def test_figure_revision_invalidates_adoption_without_rewriting_old_draft(self):
        old=self.draft.read_bytes();self.prompt.write_text('Revised concept: A does not have an established link to B.',encoding='utf-8')
        self.assertFalse(self.writer.audit(self.packet,self.base)['checks_passed'])
        self.assertEqual(self.draft.read_bytes(),old)
if __name__=='__main__':unittest.main()
