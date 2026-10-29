"""Saved-output regressions and remaining-book admission; no inference/Docker."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from types import SimpleNamespace
from probe import chapter_editorial as edit, editorial_delivery as delivery
from probe.common import read_json,atomic_json,sha
from scripts import editorial_chapters as ctrl


class SavedRepairTests(unittest.TestCase):
    def test_actual_saved_repairs_preserve_main_mathematics_and_originals(self):
        plan=read_json(ctrl.ROOT/'docs/editorial-saved-repairs-20261029.json')
        parent=Path(plan['parent'])
        if not parent.exists():self.skipTest('Optional saved development evidence absent')
        for row in plan['rows']:
            source=parent/'versions'/row['key']/row['source_label']/'document.tex'
            before=source.read_text();after=edit.apply_edits(before,row)
            self.assertEqual(sha(source),row['source_sha256'])
            with self.assertRaises(ValueError):edit.apply_edits(before+'changed',row)
            if row['key'].startswith('bergomi'):
                self.assertEqual(after.count('gives variance $2\\hsig^4/N^3$'),2)
                self.assertNotIn('an averaged sum would give variance',after)
                original=r'\overline{\sigma}^2 \;\simeq\; \frac{\hsig^2}{N}\,{\sum_i z_i^2}'
                self.assertIn(original,before);self.assertIn(original,after)
                self.assertIn('footnote 6, printed p.~9',after)
                items=delivery.notes_from_visible_dispositions(row['key'],after)
                self.assertTrue(any(i['status']=='open' and 'gamma' in i['text'] for i in items))
                self.assertFalse(any(i['independent_verification'] for i in items))
                self.assertFalse(any('empty finding' in i['text'] for i in items))
            else:
                self.assertIn(r'\usepackage{amsfonts}',after)
                self.assertNotIn(r'\(\mathbb{E}[\Sigma_{T}]$$',after)
                self.assertIn(r'\(\mathbb{E}[\Sigma_{T}]\)',after)
                self.assertEqual(after.count('assets/930db0571b28d7aad2386511.jpg'),before.count('assets/930db0571b28d7aad2386511.jpg'))
                self.assertIn('Codex technical repair',after)


class NoteRegressionTests(unittest.TestCase):
    def test_headings_separator_and_applied_status_are_not_open_math(self):
        raw='---\n\n## Accuracy log (Chapter 1, Introduction)\n\n**Applied corrections (linked to notes):**\n\n1. **Eq. (1.5)** — quadratic term restored using the definition.\n\n**Unresolved (preserved as printed):**\n\n- **Footnote 6** — gamma convention needs evidence.'
        r=edit.notes_record('b',raw)
        self.assertEqual(len(r['items']),2)
        self.assertEqual(r['items'][0]['status'],'applied_claim_unverified')
        self.assertEqual(r['items'][1]['status'],'open')
        self.assertFalse(any(x['independent_verification'] for x in r['items']))
    def test_abbreviated_explicit_reference_deduplicates_without_independent_verification(self):
        old=edit.notes_record('c','1. Missing factor\nStatus: open',phase='convert-call-049')
        suffix=old['items'][0]['id'].split('-')[-1]
        new=edit.notes_record('c',f'**Accuracy notes (section)**\n\n- **`…-{suffix}` — applied.** Factor restored by the supplied definition. Not left unresolved, since the fix follows from explicit definitions.\n- **No unresolved issues** in this section.')
        result=edit.reconcile_notes(old,new)
        material=[x for x in result['items'] if x['category']=='material']
        self.assertEqual(len(material),1);self.assertEqual(material[0]['status'],'applied_claim_unverified')
        self.assertFalse(material[0]['independent_verification']);self.assertEqual(len(result['history']),1)
    def test_compact_critic_fields_keep_open_math_apart_from_cosmetics(self):
        raw='**Critic dispositions.** Applied and verified: (1.5) factor restored. Unresolved (open, preserved as printed): gamma definition needs context. Contextual: empty header. Cosmetic: punctuation retained.'
        items=edit.notes_record('c',raw)['items']
        self.assertEqual(len(items),4)
        self.assertEqual(items[0]['status'],'applied_claim_unverified')
        self.assertEqual(items[1]['status'],'open');self.assertEqual(items[-1]['category'],'cosmetic')


class RemainingBookTests(unittest.TestCase):
    def fixture(self,root):
        tasks=[];calls=[]
        for ident,key,phase,status in [('old-c','b01','convert','pending'),('old-r','b01','critic','pending'),
                ('new-c','b02','convert','pending'),('new-r','b02','critic','pending'),
                ('done-c','b01','convert','conversion_completed'),('done-r','b01','critic','critic_revised')]:
            task={'id':ident,'key':key,'source_key':'bergomi-'+key,'phase':phase,'status':status,
                  'context':'unaltered complete context','draft_label':None,'section':{'blocks':[key],'text':'formula and prose'}}
            if ident.startswith('done'):
                task['call']=ident;calls.append({'id':ident,'parent':ident})
                atomic_json(root/'calls'/ident/'request.json',{'model':'glm53-regular','max_tokens':131072,
                    'stream':True,'reasoning_effort':'high' if phase=='convert' else 'max'})
            tasks.append(task)
        return {'tasks':tasks,'calls':calls}
    def test_identical_completed_chapter_adopted_and_only_remaining_pair_queued(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);s=self.fixture(root);history=copy.deepcopy(s['calls'])
            canonical,queued,record=delivery.remaining_bergomi(s,root)
            self.assertEqual([x['id'] for x in queued],['new-c','new-r'])
            self.assertEqual(len(canonical),4);self.assertEqual(len(record),2)
            self.assertEqual(s['tasks'][0]['status'],'adopted_completed');self.assertEqual(s['calls'],history)
            with patch.object(ctrl.runtime,'invoke',side_effect=AssertionError('Must not replay')):
                ctrl.task_once(root,s,s['tasks'][0],invoke=ctrl.runtime.invoke)
    def test_changed_targets_wrong_model_and_uncertain_attempt_are_not_adopted(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);s=self.fixture(root);s['tasks'][-2]['section']={'blocks':['other']}
            with self.assertRaisesRegex(ValueError,'Conflicting'):delivery.remaining_bergomi(s,root)
            s=self.fixture(root);s['calls'].append({'id':'uncertain','parent':'new-c'})
            with self.assertRaisesRegex(ValueError,'attempt disposition'):delivery.remaining_bergomi(s,root)
            s=self.fixture(root);p=root/'calls/done-c/request.json';body=read_json(p);body['model']='other';atomic_json(p,body)
            with self.assertRaisesRegex(ValueError,'configuration'):delivery.remaining_bergomi(s,root)

    def test_remaining_stage_passes_old_first_chapter_stop_and_keeps_immediate_critics(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);s=self.fixture(root)
            # A second new chapter tests that the previous first-pair stop does
            # not survive as an implicit dispatch boundary.
            for phase in ('convert','critic'):
                s['tasks'].append({'id':'last-'+phase,'key':'b03','source_key':'bergomi-b03',
                    'phase':phase,'status':'pending','section':None,'context':'','draft_label':None})
            _,queue,_=delivery.remaining_bergomi(s,root)
            run=root/'run';run.mkdir()
            s.update(current_versions={},production_stage={'task_ids':[t['id'] for t in queue],
                     'finish_stage':'remaining_bergomi_schedule_finished','checkpoint':'chapter_boundary'})
            seen=[]
            def once(r,state,t):
                seen.append(t['id']);t['status']='conversion_completed' if t['phase']=='convert' else 'critic_unchanged'
            with patch.object(ctrl,'ROOT',root),patch.object(ctrl,'verify',return_value=s),patch.object(ctrl.os,'dup2'),\
                 patch.object(ctrl,'converter_idle'),patch.object(ctrl.runtime,'check_other_jobs'),\
                 patch.object(ctrl.runtime,'readiness'),patch.object(ctrl.runtime,'save'),\
                 patch.object(ctrl,'report'),patch.object(ctrl,'finalize'),patch.object(ctrl,'assemble') as assembly,\
                 patch.object(ctrl,'task_once',side_effect=once):
                ctrl.worker(run)
            self.assertEqual(seen,['new-c','new-r','last-convert','last-critic'])
            self.assertEqual(s['stage'],'remaining_bergomi_schedule_finished')
            self.assertGreaterEqual(assembly.call_count,3)


class MetadataAndCoverageTests(unittest.TestCase):
    def test_metadata_control_character_is_visible_and_source_is_not_sanitized(self):
        original='2.8 payo\x1d-dependent σ $x$';source=original
        rendered=edit.metadata_tex(original)
        self.assertNotIn('\x1d',rendered);self.assertIn('[control U+001D]',rendered)
        self.assertIn(r'\ensuremath{\sigma}',rendered);self.assertEqual(source,original)
    def test_compiled_master_placeholders_are_not_delivered_content(self):
        rows=[{'key':'a','version':'complete','pdf_included':True},
              {'key':'b','version':'tex-only','pdf_included':False},
              {'key':'c','status':'missing_output','pdf_included':False}]
        summary=delivery.edition_summary(rows)
        self.assertEqual(summary['retained_content_parts'],2);self.assertEqual(summary['compiled_pdf_parts'],1)
        self.assertFalse(summary['complete_part_delivery']);self.assertEqual(summary['missing_content'],['c'])
        self.assertEqual(summary['pdf_gaps'],['b','c'])
    def test_reference_inventory_flags_missing_binding_and_retains_literal_uncertainty(self):
        doc=r'\label{a} See \eqref{a}, \ref{missing}, Figure 7.1. \includegraphics{assets/a.png}'
        r=delivery.reference_inventory(doc,{},ctrl.simple.image_references)
        self.assertEqual(r['undefined_labels'],['missing']);self.assertEqual(r['missing_assets'],['assets/a.png'])
        self.assertIn('Figure 7.1',r['literal_locators'])


class ResidentWorkloadTests(unittest.TestCase):
    def test_container_identity_not_python_name_allows_resident_glm_but_rejects_unknown(self):
        module=SimpleNamespace(CONTAINER='glm53-flash-tf',checked=Mock(return_value='PID\n100\n'),peer=lambda x:['ssh',x])
        def snap(node,unknown=False):
            return {'node':node,'memory_bytes':{'MemAvailable':1234},'processes':[
                {'pid':100,'reported_name':'python','classification':'conflicting_or_unknown'},
                {'pid':200,'classification':'conflicting_or_unknown' if unknown else 'verified_desktop'}]}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with patch.object(ctrl,'gpu_workload_snapshot',side_effect=lambda m,n:snap(n)):
                ctrl.guard_gpu_workloads(root,module,resident_glm=True)
            with patch.object(ctrl,'gpu_workload_snapshot',side_effect=lambda m,n:snap(n,True)):
                with self.assertRaisesRegex(RuntimeError,'GPU work'):ctrl.guard_gpu_workloads(root,module,resident_glm=True)


if __name__=='__main__':unittest.main()
