"""Synthetic transport/gate fixtures, NOT independent reviews or scientific evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import fitz
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'skills/light-chart/scripts'))
import review_cycle as cycle


class Strict3DTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.work = self.root/'review'
        self.images = []
        for index in range(4):
            path = self.root/f'fixture-{index}.png'
            image = Image.new('RGB', (600, 400), 'white')
            ImageDraw.Draw(image).rectangle((50+index*25, 70, 120+index*25, 160), fill='navy')
            image.save(path); self.images.append(path)
        self.pdf = self.root/'fixture.pdf'
        doc = fitz.open(); doc.new_page(width=150/25.4*72, height=100/25.4*72)
        doc.save(self.pdf); doc.close()
        self.asset = self.root/'SYNTHETIC-NOT-A-VOLUME.bin'
        self.asset.write_bytes(b'SYNTHETIC byte-binding fixture; no scientific geometry')
        self.evidence = self.root/'geometry.json'
        self.evidence.write_text(json.dumps({'representation': 'SYNTHETIC fixture',
            'coordinate_units': 'test units', 'checks': {'test_only': True},
            'limitations': ['Not scientific data or a geometry audit.'],
            'assets': [{'role': 'test-bytes', 'path': self.asset.name,
                'sha256': hashlib.sha256(self.asset.read_bytes()).hexdigest()}]}), encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def stage(self, iteration=0, **overrides):
        args = dict(iteration=iteration, briefing='SYNTHETIC COMPONENT FIXTURE ONLY.',
            size_mm=(150, 100), strict_3d=True, three_d_mode='candidate-comparison',
            three_d_subtypes=['volumetric-surfaces', 'material-lighting', 'marks-and-panels'],
            geometry_evidence=self.evidence, reference=self.images[0],
            reference_role='previous_draft', control=self.images[0], pdf=self.pdf)
        args.update(overrides)
        return cycle.stage_review(self.work, self.images[1+iteration], **args)

    def payload(self, iteration=0, repair=False):
        # Scores deliberately test thresholds; they are never visual judgments.
        card = {key: 90 for key in cycle.review_engine.SCORE_FIELDS}
        card['summary'] = 'SYNTHETIC SCORECARD FIXTURE, NOT A REVIEW.'
        return {'iter': iteration,
            'reference_inventory': {'chart_type': 'synthetic fixture', 'signature_element': 'fixture', 'motifs': ['fixture']},
            'anchor': {'what_is_right': ['Fixture only.'], 'measurements': {}},
            'quality_floor': {'passed': True, 'violation_kinds': [], 'summary': None},
            'fidelity': {'verdict': 'close' if repair else 'ship', 'paragraph': 'Synthetic gate fixture only.'},
            'focus_themes': ['Fixture shift.'] if repair else [], 'boxes': [],
            'three_d_scorecard': card, 'target_dimension': 'composition_occupancy',
            'movement_delta': 'too_small' if repair else 'accepted',
            'must_preserve': ['Fixture geometry.'], 'candidate_regressions': [],
            'remaining_gaps': ['Fixture shift.'] if repair else [],
            'next_single_change': 'Fixture shift.' if repair else None,
            'accept_over_control': not repair, 'comparison_scorecards': {'control': copy.deepcopy(card)}}

    def submit(self, payload, session='fixture-session-1', iteration=0):
        path = self.root/f'incoming-{len(list(self.root.glob("incoming-*")))}.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        return cycle.accept_review(self.work, path, iteration=iteration, reviewer_session=session)

    def test_owned_inserts_schema_control_and_geometry_are_really_staged(self):
        manifest = self.stage(baseline=self.images[3], three_d_views={'other_camera': self.images[2]})
        view = self.work/'audit_view_0'
        for module in cycle.THREE_D_BASE_MODULES + ['three-d/volumes.md', 'three-d/light-and-material.md', 'three-d/marks-and-panels.md']:
            self.assertEqual((view/'visual-review-3d'/module).read_bytes(), (cycle.LIBRARY/module).read_bytes())
        schema = json.loads((view/'review_schema.json').read_text(encoding='utf-8'))
        self.assertIn('three_d_scorecard', schema['required'])
        self.assertIn('accept_over_control', schema['required'])
        self.assertIn('three_d_control.png', manifest['required_images'])
        self.assertIn('three_d_baseline.png', manifest['required_images'])
        self.assertIn('three_d_other_camera.png', manifest['required_images'])
        self.assertIn('pdf_preview.png', manifest['required_images'])
        self.assertTrue((self.work/'geometry_sources_0/asset_000.bin').is_file())
        self.assertFalse((view/'SYNTHETIC-NOT-A-VOLUME.bin').exists())
        self.assertEqual(cycle.verify_stage(self.work, 0)['strict_3d'], True)

    def test_routes_and_geometry_fail_closed(self):
        for override, match in [({'three_d_mode': None}, 'explicit three_d_mode'),
                ({'control': None}, 'actual rendered control'), ({'pdf': None}, 'actual final PDF'),
                ({'three_d_subtypes': []}, 'three_d_subtypes'),
                ({'geometry_evidence': None}, 'geometry_evidence'),
                ({'three_d_mode': 'strict-reproduction'}, 'genuine design reference')]:
            with self.subTest(override=override), self.assertRaisesRegex(ValueError, match):
                self.stage(**override)
        self.asset.write_bytes(b'CHANGED SOURCE')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.stage()

    def test_routed_module_missing_is_not_silently_downgraded(self):
        from unittest.mock import patch
        with patch.object(cycle, 'LIBRARY', self.root/'no-library'):
            with self.assertRaisesRegex(ValueError, 'Missing routed'):
                self.stage()

    def test_missing_scorecard_uses_recorded_invalid_attempt_gate(self):
        self.stage(); payload = self.payload(); del payload['three_d_scorecard']
        result = self.submit(payload)
        self.assertEqual((result['action'], result['valid_review_count']), ('retry_reviewer', 0))

    def test_low_scorecard_cannot_ship(self):
        self.stage(); payload = self.payload(); payload['three_d_scorecard']['topology'] = 81
        result = self.submit(payload)
        self.assertEqual((result['action'], result['classification']), ('retry_reviewer', 'invalid'))

    def test_missing_delta_and_rejected_control_cannot_be_clean_acceptance(self):
        self.stage(); payload = self.payload(); del payload['movement_delta']
        with self.assertRaisesRegex(ValueError, 'routed-field preflight'):
            self.submit(payload)
        payload = self.payload(); payload['accept_over_control'] = False
        with self.assertRaisesRegex(ValueError, 'control acceptance'):
            self.submit(payload)
        self.assertFalse((self.work/'review_attempts').exists())

    def test_each_primary_drop_blocks_acceptance_despite_better_text_and_baseline(self):
        self.stage(baseline=self.images[3], min_reviews=1)
        for field in cycle.review_engine.PRIMARY_MINIMUMS:
            with self.subTest(field=field):
                payload = self.payload()
                payload['comparison_scorecards']['baseline'] = copy.deepcopy(payload['three_d_scorecard'])
                payload['comparison_scorecards']['baseline'].update({key: 80
                    for key in cycle.review_engine.SCORE_FIELDS})
                payload['three_d_scorecard'][field] = 85
                payload['three_d_scorecard']['text_export_floor'] = 96
                payload['target_dimension'] = 'text_export_floor'
                with self.assertRaisesRegex(ValueError, 'primary score regressions: ' + field):
                    self.submit(payload, 'fixture-drop-' + field)
                self.assertEqual(cycle._attempts(self.work), [])
                stored = list(self.work.glob('.review_incoming_*'))
                incoming = sorted(self.root.glob('incoming-*'), key=lambda path: path.stat().st_mtime_ns)[-1]
                self.assertTrue(any(path.read_bytes() == incoming.read_bytes() for path in stored))

    def test_previously_committed_primary_regression_cannot_be_selected(self):
        self.stage(min_reviews=1)
        payload = self.payload()
        payload['three_d_scorecard'].update({field: 85
            for field in cycle.review_engine.PRIMARY_MINIMUMS})
        payload['three_d_scorecard']['overall'] = 85
        payload['three_d_scorecard']['text_export_floor'] = 96
        payload['comparison_scorecards']['control'].update({field: 95
            for field in cycle.review_engine.SCORE_FIELDS})
        incoming = self.root/'historical-synthetic-review.json'
        incoming.write_text(json.dumps(payload), encoding='utf-8')
        # Simulate an old adapter's committed false acceptance with the
        # base engine, bypassing the routed adapter preflight. This is never an actual reviewer payload.
        result = json.loads(cycle._capture(cycle.review_engine.record_decision,
            workdir=str(self.work), review=str(incoming), draft=str(self.work/'img_iter0.png'),
            iter=0, reviewer_session='synthetic-old-adapter', min_reviews=1,
            max_iters=3, strict_3d=True))
        self.assertEqual(result['action'], 'ship')
        with self.assertRaisesRegex(ValueError, 'non-regressing control acceptance'):
            cycle.select_iteration(self.work, iteration=0, reason='Synthetic old-ledger rejection.')
        self.assertFalse((self.work/'selection.json').exists())

    def test_nonregressing_control_can_ship_with_improved_active_text_record(self):
        self.stage(min_reviews=1)
        payload = self.payload()
        payload['three_d_scorecard']['text_export_floor'] = 96
        payload['target_dimension'] = 'text_export_floor'
        result = self.submit(payload)
        self.assertEqual(result['action'], 'ship')
        selected = cycle.select_iteration(self.work, iteration=0, reason='Synthetic nonregressing fixture.')
        self.assertEqual(selected['status'], 'ship')

    def test_existing_anchor_rejects_coordinated_metadata_version_downgrade(self):
        self.stage()
        config_path = self.work/'review_cycle.json'
        manifest_path = self.work/'audit_view_0/stage_manifest.json'
        anchor = self.work/'audit_view_0/stage_manifest.sha256'
        original_anchor = anchor.read_bytes()
        config = json.loads(config_path.read_text(encoding='utf-8'))
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        for packet in (config, manifest):
            packet['strict_3d'] = False
            packet['stage_binding_version'] = 1
        config_path.write_text(json.dumps(config), encoding='utf-8')
        manifest['sha256']['review_cycle.json'] = hashlib.sha256(config_path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Stale or missing review stage manifest binding'):
            cycle.verify_stage(self.work, 0)
        self.assertEqual(anchor.read_bytes(), original_anchor)

    def test_unanchored_legacy_ordinary_packet_still_verifies(self):
        cycle.stage_review(self.work, self.images[1], briefing='SYNTHETIC legacy packet.', size_mm=(150, 100))
        config_path = self.work/'review_cycle.json'
        manifest_path = self.work/'audit_view_0/stage_manifest.json'
        config = json.loads(config_path.read_text(encoding='utf-8'))
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        config.pop('stage_binding_version')
        manifest.pop('stage_binding_version')
        config_path.write_text(json.dumps(config), encoding='utf-8')
        manifest['sha256']['review_cycle.json'] = hashlib.sha256(config_path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        (self.work/'audit_view_0/stage_manifest.sha256').unlink()
        self.assertIs(cycle.verify_stage(self.work, 0)['strict_3d'], False)

    def test_packet_source_and_manifest_tampering_are_rejected(self):
        self.stage()
        for relative in ['geometry_sources_0/asset_000.bin', 'audit_view_0/visual-review-3d/three-d/evidence.md',
                'audit_view_0/review_schema.json', 'audit_view_0/stage_manifest.json']:
            path = self.work/relative; original = path.read_bytes()
            try:
                if path.name == 'stage_manifest.json':
                    manifest = json.loads(original); manifest['strict_3d'] = False
                    path.write_text(json.dumps(manifest), encoding='utf-8')
                else:
                    path.write_bytes(original+b'CHANGED')
                with self.subTest(relative=relative), self.assertRaisesRegex(ValueError, 'Stale'):
                    self.submit(self.payload())
            finally:
                path.write_bytes(original)
        self.assertFalse((self.work/'review_attempts').exists())

    def test_owned_draw_feedback_changed_revision_and_fresh_confirmation(self):
        self.stage(); payload = self.payload(repair=True)
        result = self.submit(payload)
        self.assertEqual(result['action'], 'draw')
        handoff = Path(result['repair_instructions'])
        self.assertEqual(handoff.name, 'strict_3d_repair_instructions.md')
        self.assertIn('Start from the accepted rendered control', handoff.read_text(encoding='utf-8'))
        embedded = handoff.read_text(encoding='utf-8').split('```json\n', 1)[1].split('\n```', 1)[0]
        self.assertEqual(json.loads(embedded), payload)
        self.assertTrue((handoff.parent/'annotated.png').is_file())
        self.stage(1)
        result = self.submit(self.payload(1), 'fixture-session-2', 1)
        self.assertEqual(result['action'], 'ship')
        self.assertEqual(cycle.select_iteration(self.work, iteration=1, reason='SYNTHETIC fixture only.')['status'], 'ship')

    def test_low_score_close_at_cap_cannot_bypass_strict_selection(self):
        self.stage(max_iters=1); payload = self.payload(repair=True)
        payload['accept_over_control'] = True
        payload['three_d_scorecard']['overall'] = 84
        result = self.submit(payload)
        self.assertEqual(result['action'], 'stop_at_cap')
        with self.assertRaisesRegex(ValueError, 'passing declared rubric scores'):
            cycle.select_iteration(self.work, iteration=0, reason='Fixture only.', unresolved=['Fixture gap.'])


if __name__ == '__main__':
    unittest.main()
