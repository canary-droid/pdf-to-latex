"""Local book stage admission/adoption; no sockets, Docker or model calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from probe import chapter_glm as rt, chapter_editorial as edit
from probe.common import read_json,atomic_json,sha
from scripts import editorial_chapters as ctrl

class StageTests(unittest.TestCase):
    def state(self):
        return {'chapter_contract':edit.VERSION,'timing_policy':'manual_only','first_dispatch':1,
                'execution_limits':{'calls':None,'attempts_per_unit':1},
                'calls':[{'id':f'call-{i:03d}','parent':f'old-{i}','status':'completed_response'} for i in range(1,99)],
                'production_stage':{'task_ids':['new-convert','new-critic']}}
    def test_unlimited_local_stage_crosses_old_ceiling_keeps_history_and_blocks_other_tasks(self):
        s=self.state();history=copy.deepcopy(s['calls'])
        self.assertEqual(rt.reserve(s,'new-convert','x',wall=10**12)['id'],'call-099')
        rt.reserve(s,'readiness','r',wall=10**12)
        resumed=json.loads(json.dumps(s));rt.reserve(resumed,'new-critic','c',wall=10**12)
        self.assertEqual(resumed['calls'][:98],history)
        self.assertIsNone(resumed['execution_limits']['calls'])
        with self.assertRaises(rt.StopRun):rt.reserve(resumed,'new-convert','same')
        with self.assertRaisesRegex(rt.StopRun,'outside'):rt.reserve(resumed,'dormant-bergomi','other')
        for _ in range(5):rt.reserve(resumed,'readiness','resume')
        legacy=self.state();legacy.pop('production_stage');legacy['execution_limits']['calls']=98
        with self.assertRaisesRegex(rt.StopRun,'ceiling'):rt.reserve(legacy,'x','y')
    def test_resume_skips_success_and_uncertain_calls_without_dispatch(self):
        with tempfile.TemporaryDirectory() as td:
            s=self.state();task={'id':'done','status':'conversion_completed'}
            def forbidden(*a,**k):raise AssertionError('Repeated inference')
            ctrl.task_once(Path(td),s,task,invoke=forbidden)
            task={'id':'old-1','status':'running'};ctrl.task_once(Path(td),s,task,invoke=forbidden)
            self.assertEqual(task['status'],'interrupted_unresolved')
    def test_worker_continues_after_content_gap_stops_after_first_bergomi_pair(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/'run';run.mkdir()
            s=self.state();s.update(current_versions={},versions={},historical_calls=[],historical_request_seconds=0,
                scope='stage',accuracy={},bergomi_status='prepared',tasks=[])
            for i,book in enumerate(['gatheral','gatheral','bergomi','bergomi','bergomi']):
                s['tasks'].append({'id':str(i),'key':book+'-01','source_key':book+'-01','phase':'convert' if i%2==0 else 'critic','status':'pending'})
            s['production_stage']['task_ids']=['0','1','2','3'];seen=[]
            def once(run,state,t):
                seen.append(t['id']);t['status']='no_final_answer' if t['id']=='0' else 'critic_unchanged'
            with patch.object(ctrl,'ROOT',root),patch.object(ctrl,'verify',return_value=s),patch.object(ctrl.os,'dup2'),\
                 patch.object(ctrl,'converter_idle'),patch.object(ctrl.runtime,'check_other_jobs'),\
                 patch.object(ctrl.runtime,'readiness'),patch.object(ctrl,'compile_version'),patch.object(ctrl,'assemble'),\
                 patch.object(ctrl,'report'),patch.object(ctrl,'finalize'),patch.object(ctrl,'task_once',side_effect=once):
                ctrl.worker(run)
            self.assertEqual(seen,['0','1','2','3']);self.assertEqual(s['tasks'][4]['status'],'pending')
            self.assertEqual(s['status'],'stage_finished_for_inspection')
    def test_stage_order_is_sealed_ids_not_all_pending_tasks(self):
        s={'production_stage':{'task_ids':['a','b']},'tasks':[{'id':'dormant'},{'id':'b'},{'id':'a'}]}
        self.assertEqual([t['id'] for t in ctrl.scheduled_tasks(s)],['a','b'])
        s['production_stage']['task_ids'].append('a')
        with self.assertRaises(rt.Fatal):ctrl.scheduled_tasks(s)

class NotesTests(unittest.TestCase):
    def test_explicit_note_link_avoids_markdown_duplicate_but_unmatched_open_issue_survives(self):
        doc=r'\documentclass{article}\begin{document}\textbf{GLM unresolved issue (coefficient).} Printed sign needs evidence.\end{document}'
        entries=edit.notes_record('c','1. **Unresolved** → TeX note “GLM unresolved issue (coefficient).”\n\n2. **Verified, no change** — first-order result correct.\n\n3. **Unresolved** — Different missing condition.')['items']
        result=edit.annotate(doc,entries)
        self.assertEqual(result.count('GLM unresolved issue (coefficient).'),1)
        self.assertIn('Different missing condition',result)
        self.assertNotIn('editorial correction',result)
        self.assertNotIn('Verified, no change',result)
        mixed=edit.notes_record('c','1. **Unresolved** — second-order sign is open.\nThe first-order consistency check; no change, does not settle it.')
        self.assertEqual(mixed['items'][0]['category'],'material')
        self.assertEqual(mixed['items'][0]['status'],'open')
    def test_explicit_prior_issue_reference_reconciles_once_without_claiming_independent_check(self):
        old=edit.notes_record('chapter','1. **Unresolved** — Evidence required.',phase='convert-call-036')
        id=old['items'][0]['id']
        new=edit.notes_record('chapter',f'1. **Unresolved** (`{id}`, open) → TeX note “GLM unresolved issue (sign).” Source still needed.')
        merged=edit.reconcile_notes(old,new)
        self.assertEqual(len(merged['items']),1);self.assertEqual(len(merged['history']),1)
        self.assertEqual(merged['items'][0]['status'],'open');self.assertFalse(merged['items'][0]['independent_verification'])

class SavedAdoptionTests(unittest.TestCase):
    def test_hash_bound_adoption_preserves_formulas_and_tilde_path_not_added_caption_accents(self):
        plan=read_json(ctrl.ROOT/'docs/gatheral-pilot-adoption-20261028.json');p=Path(plan['parent'])
        if not p.exists():self.skipTest('Optional saved pilot evidence absent')
        for row in plan['rows']:
            src=p/'versions'/row['source_key']/row['source_label']/'document.tex';before=src.read_text()
            after=edit.apply_edits(before,row);self.assertEqual(sha(src),row['source_sha256'])
            with self.assertRaises(ValueError):edit.apply_edits(before+'stale',row)
            if row['key']=='gatheral-07-s01':
                self.assertNotIn(r'\tilde{\sigma}',after);self.assertNotIn(r'\tilde{\nu}',after)
                self.assertIn(r'\tilde{x}',after);self.assertIn(r'\rho\eta\,\beta(\nu_0)',after)
                self.assertNotIn('Impossible self-reference',after);self.assertIn('PDF 66 / printed 35',after)
            else:
                # Every displayed source equation survives the note-only qualification.
                import re
                equations=lambda s:re.findall(r'\\begin\{equation\*\}(.*?)\\end\{equation\*\}',s,re.S)
                self.assertEqual(equations(before),equations(after));self.assertIn('cancellation there',after)
                self.assertIn('not merely an OCR discrepancy',after);self.assertNotIn('[U+',after)
                self.assertEqual(after.count('[G7-Lewis]'),1)

if __name__=='__main__':unittest.main()

class ReplacementCoverageTests(unittest.TestCase):
    def test_parent_gap_is_replaced_by_actual_subsection_gaps_not_claimed_complete(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);state={'tasks':[],'versions':{},'current_versions':{},'scope':'test',
                'production_stage':{'section_replacements':{'gatheral-07-s02':['gatheral-07-s02-part01','gatheral-07-s02-part02']}}}
            for n in range(1,12):
                folder=r/'inputs'/f'gatheral-{n:02d}';folder.mkdir(parents=True)
                atomic_json(folder/'native.json',{'pages':[{'page':{'original_physical_page':p}} for p in (120,121)],
                    'blocks':[{'id':str(p),'kind':'equation','page':{'original_physical_page':p}} for p in (120,121)]})
                atomic_json(folder/'assets.json',[])
            for key,ids in [('gatheral-07-s02',['120','121']),('gatheral-07-s02-part01',['120']),('gatheral-07-s02-part02',['121'])]:
                state['tasks'].append({'key':key,'source_key':'gatheral-07','phase':'convert','status':'pending','section':{'blocks':ids,'title':key}})
            key='gatheral-07-s02-part01';ctrl.remember(r,state,key,'saved',r'\documentclass{article}\begin{document}Unchanged content\end{document}',{})
            state['current_versions'][key]='saved'
            (r/'source-supplement').mkdir();(r/'source-supplement/gatheral-front-blank-index.pdf').write_bytes(b'preserved')
            out=ctrl.assemble(r,state);coverage=read_json(out/'coverage.json')['delivered_parts']
            self.assertNotIn('gatheral-07-s02',[x['key'] for x in coverage])
            gap=next(x for x in coverage if x['key']=='gatheral-07-s02-part02')
            self.assertEqual(gap['target_physical_pages'],[121]);self.assertEqual(gap['status'],'missing_output')
            self.assertIn('Unchanged content',(out/'chapters'/key/'document.tex').read_text())
