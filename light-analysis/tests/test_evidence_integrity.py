'''Synthetic sealed-record regressions, not research observations.'''
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from test_analysis import bridge, paired, put, complete_plan, complete_analysis
from test_native_intake import native_fixture


def assessment(root, qc='passed', name='001', previous=None, run_id='R001'):
    value = {'run_id': run_id, 'qc_status': qc, 'outcome': 'not_evaluated'}
    sha = hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
    path = root / f'runs/{run_id}/assessments/{name}.json'
    put(path, {'assessment': value, 'sha256': sha, 'supersedes': previous})
    put(root / f'events/{run_id}-{name}.json', {'event_type': 'run_assessed', 'payload': {'run_id': run_id, 'assessment_id': name}})
    return path


def seal(root, run_id='R001'):
    folder = root / 'runs' / run_id
    records = [{'path': p.relative_to(folder).as_posix(), **bridge.fingerprint(p)}
               for p in sorted(folder.rglob('*')) if p.is_file() and 'assessments' not in p.relative_to(folder).parts and p.name != 'manifest.json']
    put(folder / 'manifest.json', {'schema_version': '1.0', 'records': records, 'unarchived_links_or_special_files': []})


class EvidenceIntegrityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='light-analysis-evidence-')
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.execution, self.work = self.base / 'execution', self.base / 'analysis'
        self.raw = native_fixture(self.execution)
        assessment(self.execution)
        seal(self.execution)

    def finish(self):
        bridge.ingest([self.execution], [self.raw], self.work)
        complete_plan(self.work)
        context = bridge.read(self.work / 'context.json')
        input_id = next(row['input_id'] for row in context['inputs'] if row['path'] == str(self.raw))
        value = complete_analysis(self.work, input_id)
        value['findings'][0].update(run_refs=['EX01/R001'], claim_refs=['EX01/C01'])
        put(self.work / 'analysis.json', value)
        return value

    def test_failed_qc_cannot_support_a_claim_despite_successful_exit(self):
        assessment(self.execution, 'failed', '002', '001.json')
        self.finish()
        self.assertFalse(bridge.verify(self.work)['ok'])

    def test_task_failure_rationale_cannot_excuse_successful_but_drifting_run(self):
        path = self.execution / 'runs/R001/result.json'
        result = bridge.read(path)
        result['input_drift_after'] = [{'path': 'evaluator.py'}]
        put(path, result)
        seal(self.execution)
        value = self.finish()
        value['findings'][0]['failure_outcome_basis'] = 'Timeout counts as an unsolved task'
        put(self.work / 'analysis.json', value)
        self.assertFalse(bridge.verify(self.work)['ok'])

    def test_selected_raw_must_match_the_original_seal_before_intake(self):
        put(self.raw, {'value': 999})
        with self.assertRaises(ValueError):
            bridge.ingest([self.execution], [self.raw], self.work)
        self.assertFalse(self.work.exists())

    def test_assessment_content_drift_cannot_be_imported_as_new_evidence(self):
        path = self.execution / 'runs/R001/assessments/001.json'
        value = bridge.read(path)
        value['assessment']['qc_status'] = 'failed'
        put(path, value)
        with self.assertRaises(ValueError):
            bridge.ingest([self.execution], [self.raw], self.work)
        self.assertFalse(self.work.exists())

    def test_broken_assessment_correction_chain_rejected(self):
        assessment(self.execution, 'passed', '002', None)
        with self.assertRaises(ValueError):
            bridge.ingest([self.execution], [self.raw], self.work)

    def test_deleted_latest_assessment_cannot_fall_back_to_old_pass(self):
        path = assessment(self.execution, 'failed', '002', '001.json')
        path.unlink()
        with self.assertRaises(ValueError):
            bridge.ingest([self.execution], [self.raw], self.work)

    def test_current_qc_revocation_invalidates_dependent_conclusion(self):
        self.finish()
        self.assertTrue(bridge.verify(self.work)['ok'])
        assessment(self.execution, 'failed', '002', '001.json')
        self.assertFalse(bridge.verify(self.work)['ok'])

    def test_raw_evidence_is_required_not_only_campaign_configuration(self):
        value = self.finish()
        context = bridge.read(self.work / 'context.json')
        metadata = next(row['input_id'] for row in context['inputs'] if row['role'] == 'campaign')
        value['findings'][0]['evidence'] = [{'input_id': metadata, 'locator': 'budget'}]
        put(self.work / 'analysis.json', value)
        self.assertFalse(bridge.verify(self.work)['ok'])

    def test_referenced_claim_must_belong_to_the_used_run_experiment(self):
        path = self.execution / 'inputs/design/design.json'
        design = bridge.read(path)
        design['claims'].append({'claim_id': 'C02', 'statement': 'Another experiment claim'})
        put(path, design)
        value = self.finish()
        value['findings'][0]['claim_refs'] = ['EX01/C02']
        put(self.work / 'analysis.json', value)
        self.assertFalse(bridge.verify(self.work)['ok'])

    def test_both_evidence_reference_fields_are_not_an_exclusive_choice(self):
        value = self.finish()
        value['findings'][0]['evidence'][0]['artifact_id'] = 'not_registered'
        put(self.work / 'analysis.json', value)
        self.assertFalse(bridge.verify(self.work)['ok'])

    def test_export_becomes_stale_when_report_is_rewritten(self):
        self.finish()
        bridge.export_handoff(self.work)
        (self.work / 'analysis-report.md').write_text('A changed interpretation', encoding='utf-8')
        self.assertFalse(bridge.verify(self.work)['ok'])

    def test_export_binds_provenance_records_not_only_derived_bytes(self):
        self.finish()
        code = self.work / 'code/analyze.py'
        code.parent.mkdir()
        code.write_text('print(14)', encoding='utf-8')
        put(self.work / 'derived/value.json', {'value': 14})
        context = bridge.read(self.work / 'context.json')
        raw_id = next(r['input_id'] for r in context['inputs'] if r['path'] == str(self.raw))
        bridge.register_artifact(self.work, 'T01', 'derived/value.json', [raw_id], ['code/analyze.py'], 'python code/analyze.py', 'synthetic fixture')
        bridge.export_handoff(self.work)
        path = self.work / 'artifacts/T01.json'
        record = bridge.read(path)
        record['command'] = 'a different claimed command'
        put(path, record)
        self.assertFalse(bridge.verify(self.work)['ok'])

    def test_constant_finite_large_effect_does_not_overflow_its_mean(self):
        path = self.base / 'large.csv'
        path.write_text('unit_id,a,b\nu1,1e308,0\nu2,1e308,0\n', encoding='utf-8')
        result = paired.compare(path, 'higher', .95, 100, 0, 'synthetic pairs', 'synthetic only', 'synthetic_validation')
        self.assertEqual(result['mean_improvement'], 1e308)
        self.assertEqual(result['sd_differences'], 0)

    def test_unselected_raw_files_are_not_required_for_bounded_intake(self):
        unused = self.execution / 'runs/R001/outputs/large-unused.json'
        put(unused, {'value': 'not selected'})
        seal(self.execution)
        unused.unlink()
        self.finish()
        result = bridge.verify(self.work)
        self.assertTrue(result['ok'], result)
        self.assertTrue(any('Bounded intake' in w for w in result['warnings']))

    def test_sealed_metadata_drift_is_rejected_before_creation(self):
        path = self.execution / 'runs/R001/result.json'
        value = bridge.read(path)
        value['returncode'] = 19
        put(path, value)
        with self.assertRaises(ValueError):
            bridge.ingest([self.execution], [self.raw], self.work)
        self.assertFalse(self.work.exists())

    def test_pending_or_unknown_qc_cannot_become_decisive(self):
        for qc in ('pending', 'unknown'):
            with self.subTest(qc=qc):
                assessment(self.execution, qc, '001')
                target = self.base / qc
                original = self.work
                self.work = target
                self.finish()
                self.assertFalse(bridge.verify(target)['ok'])
                self.work = original

    def test_incomplete_process_is_not_a_task_failure_even_with_rationale(self):
        path = self.execution / 'runs/R001/result.json'
        path.unlink()
        put(self.execution / 'runs/R001/started.json', {'run_id': 'R001'})
        seal(self.execution)
        value = self.finish()
        value['findings'][0]['failure_outcome_basis'] = 'Timeout counts as an unsolved task'
        put(self.work / 'analysis.json', value)
        self.assertFalse(bridge.verify(self.work)['ok'])

    def test_transitive_prerequisite_revocation_blocks_only_its_dependents(self):
        for run_id, dependency in [('R002', 'R001'), ('R003', 'R002')]:
            native_fixture(self.execution, run_id=run_id)
            path = self.execution / f'runs/{run_id}/spec.json'
            spec = bridge.read(path)
            spec['depends_on_runs'] = [dependency]
            put(path, spec)
            assessment(self.execution, run_id=run_id)
            seal(self.execution, run_id)
        self.raw = self.execution / 'runs/R003/outputs/raw.json'
        value = self.finish()
        value['findings'][0]['run_refs'] = ['EX01/R003']
        put(self.work / 'analysis.json', value)
        self.assertTrue(bridge.verify(self.work)['ok'])
        assessment(self.execution, 'failed', '002', '001.json')
        self.assertFalse(bridge.verify(self.work)['ok'])

    def test_derived_finding_uses_registered_raw_lineage_and_keeps_export_valid(self):
        value = self.finish()
        code = self.work / 'code/analyze.py'
        code.parent.mkdir()
        code.write_text('print(14)', encoding='utf-8')
        put(self.work / 'derived/value.json', {'value': 14})
        raw_id = value['findings'][0]['evidence'][0]['input_id']
        bridge.register_artifact(self.work, 'T01', 'derived/value.json', [raw_id], ['code/analyze.py'], 'python code/analyze.py', 'synthetic fixture')
        value['findings'][0]['evidence'] = [{'artifact_id': 'T01', 'locator': 'value'}]
        put(self.work / 'analysis.json', value)
        bridge.export_handoff(self.work)
        result = bridge.verify(self.work)
        self.assertTrue(result['ok'], result)
        self.assertEqual(len(bridge.read(self.work / 'handoff.json')['sources']), 7)

    def test_journal_selection_handoff_does_not_require_new_experiment_predictions(self):
        value = self.finish()
        value['loop_decision'].update(route='light-journal-select', next_action='Match this bounded contribution and author constraints to candidate venues')
        put(self.work / 'analysis.json', value)
        result = bridge.verify(self.work)
        self.assertTrue(result['ok'], result)
        self.assertEqual(bridge.export_handoff(self.work)['route'], 'light-journal-select')

    def test_duplicate_native_claim_ids_are_rejected_before_creation(self):
        path = self.execution / 'inputs/design/design.json'
        design = bridge.read(path)
        design['claims'].append(dict(design['claims'][0]))
        put(path, design)
        with self.assertRaises(ValueError):
            bridge.ingest([self.execution], [self.raw], self.work)
        self.assertFalse(self.work.exists())

    def test_current_passed_reassessment_requires_review_but_preserves_raw_history(self):
        self.finish()
        before = self.raw.read_bytes()
        assessment(self.execution, 'passed', '002', '001.json')
        result = bridge.verify(self.work)
        self.assertTrue(result['ok'], result)
        self.assertTrue(any('differs from frozen receipt' in w for w in result['warnings']))
        self.assertEqual(before, self.raw.read_bytes())

    def test_finite_opposite_extreme_quantiles_do_not_overflow_interpolation(self):
        result = paired.quantile([-1e308, 1e308], .5)
        self.assertEqual(result, 0)
