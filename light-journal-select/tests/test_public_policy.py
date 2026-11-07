'''Offline use of manually read public facts plus explicitly synthetic constraints.'''
import json
from pathlib import Path
import unittest
from test_packet_v11 import MODULE, packet


class PublicPolicySmokeTests(unittest.TestCase):
    def example(self):
        facts = json.loads((Path(__file__).resolve().parents[1] / 'evaluations/2026-11-06-public-facts.json').read_text(encoding='utf-8'))
        value = packet()
        value['research']['basis'] = 'Synthetic budget only; no real manuscript or actual recommendation.'
        source = next(r for r in facts['records'] if r['id'] == 'PLOS-FEES')
        source['applies_to'] = value['sources'][0]['applies_to']
        value['sources'] = [source]
        value['constraints'][0]['requirement'] = 'Synthetic USD1000 budget; author eligibility not known'
        row = value['candidates'][0]
        row.update(name='PLOS One', recommended=False, comparables=[])
        row['target'].update(publisher='PLOS', homepage='https://journals.plos.org/plosone/')
        row['checks'][0].update(status='unknown', basis=source['observation'], source_ids=['PLOS-FEES'])
        for facet in MODULE.FACET_KINDS:
            row[facet].update(status='unknown', basis='No actual manuscript/identity comparison performed', source_ids=[])
        row['fit'].update(band='unknown', rationale='No real manuscript supplied')
        return value

    def test_official_waiver_page_does_not_establish_zero_cost(self):
        value = self.example(); report = MODULE.audit(value)
        self.assertTrue(report['valid'])
        self.assertEqual(report['candidates'][0]['eligibility'], 'conditional')
        self.assertFalse(report['handoff']['evidence_ready'])
        value['candidates'][0]['recommended'] = True
        self.assertFalse(MODULE.audit(value)['valid'])

    def test_public_source_is_not_reusable_for_an_unchecked_route(self):
        value = self.example(); value['candidates'][0]['target']['publication_route'] = 'subscription'
        with self.assertRaisesRegex(MODULE.PacketError, 'applicability'): MODULE.audit(value)
