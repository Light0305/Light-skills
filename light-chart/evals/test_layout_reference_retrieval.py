"""Real packaged-reference retrieval, ranking, portability and routing boundaries."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

WORK = Path(__file__).resolve().parents[1]
SKILL = WORK/'skills/light-chart'
sys.path.insert(0, str(SKILL/'scripts'))
import library


class LayoutReferenceRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((SKILL/'assets/library/domain-layouts.json').read_text(encoding='utf-8'))
        cls.rows=cls.catalog['entries']

    def test_six_domains_return_usable_relevant_whole_references(self):
        queries={
          'omics':'omics heatmap sample annotation',
          'clinical':'clinical forest risk evidence',
          'signals':'signals spectrogram time behavior',
          'ecology':'ecology ordination matrix labels',
          'ml':'machine learning benchmark budget repeated runs',
          'materials':'materials impedance frequency origin zoom',
        }
        for domain,query in queries.items():
            with self.subTest(domain=domain):
                hits=library.search(query,kind='visual-reference',limit=3)
                self.assertTrue(hits)
                self.assertEqual(hits[0]['domain'],domain)
                self.assertEqual(hits[0]['reference_role'],'positive')
                self.assertTrue(Path(hits[0]['absolute_path']).is_file())
                self.assertTrue(hits[0]['figure_url'].startswith('https://'))
                if hits[0]['absolute_preview_path']:
                    self.assertTrue(Path(hits[0]['absolute_preview_path']).is_file())

    def test_domain_and_evidence_change_ranking_for_same_chart_concept(self):
        a=library.search('omics distribution residual',kind='visual-reference',limit=2)
        b=library.search('clinical distribution support',kind='visual-reference',limit=2)
        self.assertEqual(a[0]['domain'],'omics')
        self.assertEqual(b[0]['domain'],'clinical')
        self.assertNotEqual(a[0]['id'],b[0]['id'])
        # Both queries include a known vocabulary concept: lexical/domain
        # constraints must still participate rather than being discarded.
        self.assertIn('distribution',library.concepts_for('omics distribution residual'))

    def test_counterexamples_are_separate_and_explicitly_findable(self):
        normal=library.search('ecology ordination matrix labels',kind='visual-reference',limit=1)
        self.assertEqual(normal[0]['reference_role'],'positive')
        counter=library.search('signals counterexample',kind='visual-reference',limit=2)
        self.assertTrue(all(x['reference_role']=='counterexample' for x in counter))
        for d in ('omics','clinical','signals','ecology','ml','materials'):
            positive=[r for r in self.rows if r['domain']==d and r['reference_role']=='positive']
            self.assertGreaterEqual(len(positive),6)
            self.assertGreaterEqual(len({r['paper_id'] for r in positive}),3)
            self.assertTrue(any(r['domain']==d and r['reference_role']=='counterexample' for r in self.rows))

    def test_bundled_previews_are_exact_inspected_whole_figures(self):
        for row in self.rows:
            with self.subTest(ref=row['id']):
                self.assertEqual(row['kind'],'visual-reference')
                self.assertNotEqual(row['status'],'callable')
                self.assertFalse(Path(row['path']).is_absolute())
                self.assertTrue((SKILL/row['path']).is_file())
                self.assertTrue(row['lesson'] and row['boundary'] and row['view_record'])
                if row['preview']:
                    self.assertFalse(Path(row['preview']).is_absolute())
                    data=(SKILL/row['preview']).read_bytes()
                    self.assertEqual(hashlib.sha256(data).hexdigest(),row['inspected_image_sha256'])
                else:
                    self.assertEqual(row['redistribution'],'link-only')
                    self.assertTrue(row['figure_url'].startswith('https://'))
        link_only={r['id']:r for r in self.rows if not r['preview']}
        self.assertIn('visual-calibration-fig2',link_only)
        self.assertIn('BY-NC',link_only['visual-calibration-fig2']['license'])
        self.assertTrue(any('BY-NC-ND' in r['license'] for r in link_only.values()))

    def test_existing_callable_coverage_and_backend_are_unchanged(self):
        all_rows=library._index()
        without=[r for r in all_rows if r['kind']!='visual-reference']
        tasks=[('Python pca ordination',None),('R survival risk table',None),
               ('Python measured-impedance nyquist bode',None),
               ('computational-sweep confusion-counts','python'),
               ('UMAP biplot','r'),('annotated heatmap','r')]
        keys=['backend','concepts','requested_symbols','unimplemented_symbols',
              'unimplemented_concepts','concept_coverage','symbol_coverage','status']
        for task,backend in tasks:
            with self.subTest(task=task):
                current=library.route(task,backend)
                with patch.object(library,'_index',return_value=without):
                    previous=library.route(task,backend)
                self.assertEqual([r['id'] for r in current['entrypoints']],
                                 [r['id'] for r in previous['entrypoints']])
                for key in keys:self.assertEqual(current[key],previous[key],key)
                self.assertTrue(all(r['kind']=='implementation' for r in current['entrypoints']))
        resource=library.route('clinical calibration support',backend='python')
        self.assertFalse(any(r['kind']=='visual-reference' for r in resource['entrypoints']))

    def test_packaged_references_relocate_without_artifact_dependency(self):
        with tempfile.TemporaryDirectory(prefix='light chart reference copy ') as temp:
            copied=Path(temp)/'relocated skill'
            for name in ('assets/library','assets/visual-library/domain-layouts','references/domain-layouts'):
                shutil.copytree(SKILL/name,copied/name)
            with patch.object(library,'ROOT',copied):
                hits=library.search('omics heatmap sample annotation',kind='visual-reference',limit=3)
                self.assertTrue(all(Path(r['absolute_path']).is_relative_to(copied) for r in hits))
                self.assertTrue(all(not r['absolute_preview_path'] or
                    Path(r['absolute_preview_path']).is_relative_to(copied) for r in hits))
                link=library.search('clinical calibration support',kind='visual-reference',limit=1)[0]
                self.assertIsNone(link['absolute_preview_path'])
                self.assertTrue((copied/link['path']).is_file())

    def test_cli_exposes_real_reference_kind(self):
        done=subprocess.run([sys.executable,'-X','utf8',str(SKILL/'scripts/library.py'),
          'search','--kind','visual-reference','--query','clinical forest risk evidence','--limit','1'],
          capture_output=True,text=True,encoding='utf-8',check=False)
        self.assertEqual(done.returncode,0,done.stderr)
        hit=json.loads(done.stdout)[0]
        self.assertEqual(hit['domain'],'clinical')
        self.assertTrue(Path(hit['absolute_path']).is_file())


if __name__=='__main__':unittest.main()
