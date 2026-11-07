"""Contract-validator failure paths, not writing quality evaluations."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('write_validate', ROOT / 'scripts/validate.py')
validator = importlib.util.module_from_spec(spec); spec.loader.exec_module(validator)


class ValidationTests(unittest.TestCase):
    def test_package_structure_and_links(self):
        validator.validate(ROOT)  # Raises on a broken package; does not return a score.

    def test_nonobject_case_or_run_has_a_contract_error(self):
        for value in (None, [], 'text'):
            for which in ('case', 'run'):
                with self.subTest(value=value, which=which), self.assertRaises(validator.ValidationError):
                    if which == 'case': validator.check_case(value, {}, set())
                    else: validator.check_run(value, {}, set(), ROOT)

    def test_duplicate_keys_and_constants_rejected_for_json_and_jsonl(self):
        for raw in ('{"id":"a","id":"b"}', '{"x":NaN}', '{"x":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(validator.ValidationError):
                validator.parse_json(raw, 'case.jsonl:1')
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'record.json'; path.write_text(raw, encoding='utf-8')
                with self.assertRaises(validator.ValidationError): validator.read_json(path)

    def test_overflow_number_is_not_a_valid_finite_metric(self):
        value = validator.parse_json('1e999', 'score')
        with self.assertRaises(validator.ValidationError):
            validator.check_schema(value, {'type': 'number'})


if __name__ == '__main__':
    unittest.main()
