"""State/integrity fixtures only. These tests are not visual-review evidence."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/light-chart/scripts'))
from review_cycle import stage_review, accept_review, select_iteration, verify_stage


class ReviewCycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.work=self.root/'review'
        self.first=self.image('first.png',10)
        self.next=self.image('next.png',30)
        self.brief='UNIT TEST FIXTURE. Question: are paired values readable? Units: test units.'

    def tearDown(self):
        self.temp.cleanup()

    def image(self,name,shift):
        path=self.root/name
        image=Image.new('RGB',(600,400),'white')
        draw=ImageDraw.Draw(image)
        draw.line([(40,350),(560,350)],fill='black',width=2)
        draw.line([(40,40),(40,350)],fill='black',width=2)
        draw.ellipse((150+shift,120,175+shift,145),fill='navy')
        image.save(path)
        return path

    def stage(self,iteration=0,draft=None,**kwargs):
        return stage_review(self.work,draft or self.first,iteration=iteration,
            briefing=self.brief,size_mm=(150,100),**kwargs)

    def payload(self,iteration=0,actionable=False,floor=True):
        return {'iter':iteration,
            'reference_inventory':{'chart_type':'fixture point plot','signature_element':'fixture axis',
                                   'motifs':['fixture point']},
            'anchor':{'what_is_right':['FIXTURE only: input has a point.'],'measurements':{}},
            'quality_floor':{'passed':floor,'violation_kinds':[] if floor else ['label_clipped'],
                             'summary':None if floor else 'FIXTURE clipped label.'},
            'fidelity':{'verdict':'close' if actionable else 'ship',
                        'paragraph':'STATE TEST FIXTURE. Not an actual image review.'},
            'focus_themes':['FIXTURE change point.'] if actionable else [],
            'boxes':[]}

    def submit(self,payload,session,iteration=0):
        path=self.root/f'incoming{len(list(self.root.glob("incoming*")))}.json'
        path.write_text(payload if isinstance(payload,str) else json.dumps(payload),encoding='utf-8')
        return accept_review(self.work,path,iteration=iteration,reviewer_session=session)

    def test_stages_final_pdf_and_print_preview_and_idempotent_hashes(self):
        import fitz
        path=self.root/'figure.pdf'
        doc=fitz.open();doc.new_page(width=150/25.4*72,height=100/25.4*72)
        doc.save(path);doc.close()
        manifest=self.stage(pdf=path)
        self.assertEqual(manifest['reference_role'],'brief_only')
        self.assertEqual(manifest['mode'],'data-first')
        self.assertIn('pdf_preview.png',manifest['required_images'])
        with Image.open(self.work/'audit_view_0/print_preview.png') as image:
            self.assertEqual(image.size,(567,378))
        self.assertEqual(self.stage(pdf=path)['sha256'],manifest['sha256'])
        self.assertEqual(verify_stage(self.work,0)['draft_sha256'],manifest['draft_sha256'])

    def test_stale_draft_refused_before_review_is_committed(self):
        self.stage()
        (self.work/'img_iter0.png').write_bytes(self.next.read_bytes())
        with self.assertRaisesRegex(ValueError,'Stale'):
            self.submit(self.payload(),'real-session-A')
        self.assertFalse((self.work/'review_attempts').exists())

    def test_stale_prompt_refused(self):
        self.stage()
        with (self.work/'audit_view_0/review_prompt.txt').open('a',encoding='utf-8') as handle:
            handle.write('CHANGED')
        with self.assertRaisesRegex(ValueError,'Stale'):
            self.submit(self.payload(),'real-session-A')

    def test_invalid_does_not_count_then_clean_same_draft_confirmation(self):
        self.stage()
        invalid=self.submit('not JSON','real-session-A')
        self.assertEqual((invalid['action'],invalid['valid_review_count']),('retry_reviewer',0))
        clean=self.submit(self.payload(),'real-session-B')
        self.assertEqual((clean['action'],clean['valid_review_count']),('review_same_draft',1))
        done=self.submit(self.payload(),'real-session-C')
        self.assertEqual((done['action'],done['valid_review_count']),('ship',2))
        chosen=select_iteration(self.work,iteration=0,reason='Fixture clean confirmation.')
        self.assertEqual(chosen['status'],'ship')

    def test_reused_session_is_invalid_not_an_extra_independent_review(self):
        self.stage()
        first=self.submit(self.payload(),'real-session-A')
        replay=self.submit(self.payload(),'real-session-A')
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['valid_review_count'],1)
        changed=self.payload();changed['fidelity']['paragraph']='Different fixture payload.'
        invalid=self.submit(changed,'real-session-A')
        self.assertEqual((invalid['classification'],invalid['valid_review_count']),('invalid',1))
        done=self.submit(self.payload(),'real-session-B')
        self.assertEqual(done['action'],'ship')

    def test_valid_feedback_draws_and_authorizes_changed_next_iteration_only(self):
        self.stage()
        first=self.submit(self.payload(actionable=True),'real-session-A')
        self.assertEqual(first['action'],'draw')
        self.assertTrue((self.work/'review_feedback_0/annotated.png').is_file())
        with self.assertRaisesRegex(ValueError,'changed draft'):
            self.stage(1,self.first)
        self.stage(1,self.next,reference=self.first,reference_role='previous_draft')
        done=self.submit(self.payload(1),'real-session-B',iteration=1)
        self.assertEqual(done['action'],'ship')
        self.assertEqual(select_iteration(self.work,iteration=1,reason='Fixture repair confirmed.')['status'],'ship')

    def test_data_first_repair_handoff_preserves_actual_review_and_not_card_matching(self):
        import hashlib
        self.stage()
        payload=self.payload(actionable=True,floor=False)
        payload['focus_themes']=['FIXTURE theme one.','FIXTURE theme two.']
        payload['boxes']=[{'x0':900,'y0':100,'x1':930,'y1':130,'note':'FIXTURE first box.'},
                          {'x0':1000,'y0':200,'x1':1040,'y1':230,'note':'FIXTURE second box.'}]
        result=self.submit(payload,'/fixture/fresh-session')
        path=Path(result['repair_instructions']);text=path.read_text(encoding='utf-8')
        self.assertEqual(path.name,'repair_instructions.md')
        self.assertIn('Do not copy the briefing card',text)
        self.assertIn('Preserve the review\'s positive anchors',text)
        self.assertIn(self.brief,text)
        embedded=text.split('```json\n',1)[1].split('\n```',1)[0]
        self.assertEqual(json.loads(embedded),payload)
        feedback=path.parent
        binding=json.loads((feedback/'repair_handoff.json').read_text(encoding='utf-8'))
        self.assertEqual(binding['result_id'],result['result_id'])
        self.assertEqual(binding['draft_sha256'],result['draft_sha256'])
        self.assertEqual(binding['repair_instructions_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
        original=(feedback/'notes.md').read_bytes()
        replay=self.submit(payload,'/fixture/fresh-session')
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['valid_review_count'],1)
        self.assertEqual(original,(feedback/'notes.md').read_bytes())
        self.assertEqual(Path(replay['repair_instructions']).read_bytes(),path.read_bytes())

    def test_reference_fit_keeps_original_repair_handoff(self):
        self.stage(mode='reference-fit',reference=self.next)
        result=self.submit(self.payload(actionable=True),'real-session-A')
        self.assertEqual(Path(result['repair_instructions']).name,'notes.md')
        self.assertFalse((self.work/'review_feedback_0/repair_instructions.md').exists())

    def test_next_iteration_without_draw_refused_and_limits_fixed(self):
        self.stage()
        with self.assertRaisesRegex(ValueError,'valid draw'):
            self.stage(1,self.next)
        self.submit(self.payload(),'real-session-A')
        with self.assertRaisesRegex(ValueError,'valid draw'):
            self.stage(1,self.next)
        with self.assertRaisesRegex(ValueError,'immutable'):
            self.stage(min_reviews=1)

    def test_cap_requires_explicit_floor_passing_choice_and_unresolved_issues(self):
        self.stage(max_iters=2)
        self.submit(self.payload(actionable=True),'real-session-A')
        self.stage(1,self.next,max_iters=2)
        capped=self.submit(self.payload(1,actionable=True),'real-session-B',iteration=1)
        self.assertEqual(capped['action'],'stop_at_cap')
        with self.assertRaisesRegex(ValueError,'unresolved'):
            select_iteration(self.work,iteration=0,reason='Fixture previous version chosen.')
        chosen=select_iteration(self.work,iteration=0,reason='Fixture reviewer found first version clearer.',
                                unresolved=['FIXTURE remaining label issue.'])
        self.assertEqual(chosen['selected_iteration'],0)
        self.assertEqual(chosen['status'],'selected_with_unresolved_issues')

    def test_floor_failure_cannot_be_promoted_at_cap(self):
        self.stage(max_iters=1)
        self.submit(self.payload(actionable=True,floor=False),'real-session-A')
        with self.assertRaisesRegex(ValueError,'floor-passing'):
            select_iteration(self.work,iteration=0,reason='Fixture selection.',unresolved=['Fixture clipped text.'])

    def test_self_comparison_refused_and_reference_fit_requires_reference(self):
        with self.assertRaisesRegex(ValueError,'Self-comparison'):
            self.stage(reference=self.first)
        with self.assertRaisesRegex(ValueError,'actual external reference'):
            self.stage(mode='reference-fit')

    def test_second_malformed_review_fails_closed(self):
        self.stage()
        self.submit('{invalid','real-session-A')
        with self.assertRaisesRegex(ValueError,'second invalid'):
            self.submit('[]','real-session-B')
        attempts=list((self.work/'review_attempts').glob('attempt_*.json'))
        self.assertEqual(len(attempts),2)
        self.assertEqual(json.loads(attempts[-1].read_text())['valid_review_count'],0)
        with self.assertRaisesRegex(ValueError,'exhausted'):
            self.submit(self.payload(),'real-session-C')

    def test_missing_review_is_a_recorded_invalid_attempt(self):
        self.stage()
        result=accept_review(self.work,self.root/'never-returned.json',iteration=0,
                             reviewer_session='real-session-A')
        self.assertEqual((result['classification'],result['valid_review_count']),('invalid',0))

    def test_reference_fit_stages_original_review_prompt(self):
        self.stage(mode='reference-fit',reference=self.next)
        self.assertTrue((self.work/'audit_view_0/reviewer.md').is_file())
        self.assertIn('reference-fit',(self.work/'audit_view_0/review_prompt.txt').read_text(encoding='utf-8'))


if __name__=='__main__':
    unittest.main()
