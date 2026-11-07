import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from light_crawl.site import _count_items, run_site_pack
from light_crawl.utils import write_json


class SiteOutputTests(unittest.TestCase):
    def test_csv_multiline_field_is_one_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'data.csv'
            path.write_text('id,note\n1,"two\nlines"\n2,plain\n', encoding='utf-8')
            self.assertEqual(_count_items(path), 2)

    def test_invalid_jsonl_is_not_an_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'data.jsonl'
            path.write_text('not json\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                _count_items(path)

    def test_success_exit_without_output_is_not_a_successful_crawl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / 'pack'
            (pack / 'spider').mkdir(parents=True)
            write_json(pack / 'site.json', {})
            write_json(pack / 'spider/site.json', {})
            (pack / 'spider/spider.py').write_text('pass', encoding='utf-8')
            self.assertFalse(run_site_pack(pack, output=root / 'missing.jsonl', verify=False).passed)

    def test_invalid_output_returns_failed_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / 'pack'
            (pack / 'spider').mkdir(parents=True)
            write_json(pack / 'site.json', {'run': {'expected_items': 1}})
            write_json(pack / 'spider/site.json', {})
            code = 'import sys\nfrom pathlib import Path\nPath(sys.argv[sys.argv.index("--out") + 1]).write_text("not json")\n'
            (pack / 'spider/spider.py').write_text(code, encoding='utf-8')
            self.assertFalse(run_site_pack(pack, output=root / 'invalid.jsonl', verify=False).passed)
