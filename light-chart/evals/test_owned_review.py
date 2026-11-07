"""Integrity/diagnostic fixtures; none are actual scientific or visual reviews."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'skills/light-chart/scripts'))
import review_cycle as cycle
import review_engine as engine
import raster_diagnostics as raster


class OwnedReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root/'image.png'
        Image.new('RGB', (120, 80), '#587e93').save(self.image)
        self.work = self.root/'cycle'
        cycle.stage_review(self.work, self.image, briefing='SYNTHETIC TEST ONLY.', size_mm=(120, 80))
        self.review = {'iter': 0,
            'reference_inventory': {'chart_type': 'fixture', 'signature_element': 'fixture', 'motifs': ['fixture']},
            'anchor': {'what_is_right': ['Fixture only.'], 'measurements': {}},
            'quality_floor': {'passed': True, 'violation_kinds': [], 'summary': None},
            'fidelity': {'verdict': 'ship', 'paragraph': 'SYNTHETIC TEST, NOT A REVIEW.'},
            'focus_themes': [], 'boxes': []}

    def submit(self, payload=None, session='fixture-a'):
        path = self.root/'incoming.json'
        path.write_text(json.dumps(self.review if payload is None else payload), encoding='utf-8')
        return cycle.accept_review(self.work, path, iteration=0, reviewer_session=session)

    def test_ledger_detects_event_edits_and_tail_deletion(self):
        self.submit()
        event = next((self.work/'review_attempts').glob('attempt_*.json'))
        original = event.read_bytes()
        packet = json.loads(original); packet['valid_review_count'] = 20
        event.write_text(json.dumps(packet), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'integrity'):
            engine.review_history(self.work)
        event.write_bytes(original)
        self.submit(session='fixture-b')
        latest = sorted((self.work/'review_attempts').glob('attempt_*.json'))[-1]
        latest.unlink()
        with self.assertRaisesRegex(ValueError, 'head'):
            engine.review_history(self.work)

    def test_recorded_raw_payload_changes_are_detected(self):
        self.submit()
        event = engine.review_history(self.work)[0]
        (self.work/event['payload_file']).write_bytes(b'changed bytes')
        with self.assertRaisesRegex(ValueError, 'input changed'):
            engine.review_history(self.work)

    def test_foreign_reference_box_is_recorded_as_invalid(self):
        payload = copy.deepcopy(self.review)
        payload.update(focus_themes=['Fixture repair.'], boxes=[{'x0': 3, 'y0': 60, 'x1': 25, 'y1': 80, 'note': 'Fixture.'}])
        payload['fidelity']['verdict'] = 'close'
        result = self.submit(payload)
        self.assertEqual(result['classification'], 'invalid')
        self.assertIn('outside', result['reason'])
        self.assertFalse((self.work/'review_feedback_0').exists())

    def test_contradictory_acceptance_is_not_counted(self):
        payload = copy.deepcopy(self.review)
        payload['focus_themes'] = ['Fixture unresolved repair.']
        result = self.submit(payload)
        self.assertEqual((result['classification'], result['valid_review_count']), ('invalid', 0))

    def test_nonfinite_json_is_preserved_and_invalid(self):
        payload = copy.deepcopy(self.review)
        payload['anchor']['measurements']['bad'] = float('nan')
        result = self.submit(payload)
        self.assertEqual(result['classification'], 'invalid')
        self.assertIn(b'NaN', (self.work/result['payload_file']).read_bytes())

    def test_existing_lock_refuses_parallel_writer_without_new_record(self):
        (self.work/'.review-engine.lock').write_text('fixture lock', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'busy'):
            self.submit()
        self.assertFalse((self.work/'review_attempts').exists())

    def test_terminal_replay_is_idempotent_but_new_review_rejected(self):
        self.submit()
        terminal = self.submit(session='fixture-b')
        replay = self.submit(session='fixture-b')
        self.assertEqual(terminal['result_id'], replay['result_id'])
        self.assertTrue(replay['replayed'])
        with self.assertRaisesRegex(ValueError, 'terminal'):
            self.submit(session='fixture-c')
        self.assertEqual(len(engine.review_history(self.work)), 2)

    def test_boolean_and_out_of_range_scores_are_invalid(self):
        card = {key: 90 for key in engine.SCORE_FIELDS}; card['summary'] = 'Fixture.'
        for value in (True, -1, 101, 82.5):
            with self.subTest(value=value):
                card['topology'] = value
                self.assertIsNotNone(engine.scorecard_error({'three_d_scorecard': card}))

    def test_blank_and_transparent_rasters_have_no_content_bounds(self):
        for mode, color in [('RGB', 'white'), ('RGBA', (10, 20, 30, 0))]:
            path = self.root/f'{mode}.png'; Image.new(mode, (5, 6), color).save(path)
            report = raster.describe(path)
            self.assertEqual(report['nonwhite_fraction'], 0)
            self.assertIsNone(report['nonwhite_bounds_xyxy'])
            self.assertNotIn('score', report)

    def test_pixel_comparison_does_not_resize_or_rank(self):
        same = raster.compare(self.image, self.image)
        self.assertEqual(same['mean_absolute_channel_difference'], 0)
        other = self.root/'other.png'; Image.new('RGB', (60, 40), 'white').save(other)
        different = raster.compare(self.image, other)
        self.assertFalse(different['same_pixel_grid'])
        self.assertNotIn('mean_absolute_channel_difference', different)

    def test_no_original_figmirror_import_in_runtime_adapter(self):
        path = Path(cycle.__file__)
        self.assertNotIn('import figannot', path.read_text(encoding='utf-8'))
        self.assertTrue(cycle.LIBRARY.name == 'visual-review')


if __name__ == '__main__':
    unittest.main()
