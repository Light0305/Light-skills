import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ppt_verify',ROOT/'scripts/verify_powerpoint.py')
verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)
class PreservationTests(unittest.TestCase):
    def test_saved_allowed(self):verify.ensure_saved(SimpleNamespace(Saved=-1))
    def test_unsaved_rejected(self):
        with self.assertRaises(ValueError):verify.ensure_saved(SimpleNamespace(Saved=0))
    def test_all_derived_exports_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=verify.export_paths(Path(tmp)/'preview',{'pages':[{'slug':'one'},{'slug':'two'}]})
            self.assertEqual({p.name for p in paths},{'preview-one.png','preview-two.png','preview.pdf','preview.audit.json'})
if __name__=='__main__':unittest.main()
