"""Syntax preservation, finite lineage reservations and exact Low/draft binding."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from probe import tex_syntax_repair as syntax, originals_recovery as rec, originals_review as review
from probe import chapter_glm as runtime, book_completion as scope
from probe import originals_selection as selection, chapter_concurrency as concurrent
from probe.common import atomic_json, sha, fingerprint, read_json
from probe.experiment import seal
from scripts import originals_batch as ctrl
from test_speed_suite import health

DOC=r'\documentclass{article}\begin{document}Assume $x>0$. $a+b=c$.\end{document}'


class SyntaxTests(unittest.TestCase):
    def plan(self,text,line=2,message='Error'):
        return syntax.scope_for(text,{'line':line,'message':message,'excerpt':message})

    def test_three_demonstrated_repairs_preserve_all_content(self):
        cases=[('Header\n'+r'Here \texttt @}: function @x. $a-b$.',2,"Too many }'s."),
               ('Header\\\\[4pt]\n'+r"Quote `H\_\mathrm{Classout}'; restored $H_c$.",2,r'\mathrm allowed only in math mode.'),
               (r'\newcommand{\glmunres}[1]{\par\textcolor{orange}{\small #1}\par}'+'\n'+r'\begin{document}'+'\n'+r'\glmunres{First.\par $x_1=-2$.}',3,r'Paragraph ended before \@textcolor was complete.')]
        for text,line,error in cases:
            new,edits=syntax.deterministic(text,{'line':line,'message':error,'excerpt':error})
            self.assertTrue(edits);self.assertNotEqual(text,new)
            for expression in ('$a-b$','$H_c$','$x_1=-2$'):
                self.assertEqual(text.count(expression),new.count(expression))
        self.assertIn(r'{\color{orange}\small #1}',new)

    def test_unchanged_math_can_be_delimited_in_text(self):
        text='Intro\n'+r'Quoted \hat V_x remains; assume $x>0$.'
        plan=self.plan(text)
        new,record=syntax.apply_response(text,plan,json.dumps({'edits':[{'old':r'\hat V_x','new':r'\(\hat V_x\)'}]}))
        self.assertIn(r'\(\hat V_x\)',new);self.assertIn('$x>0$',new);self.assertEqual(len(record['edits']),1)

    def test_rejects_math_prose_number_asset_and_annotation_changes(self):
        text='Preamble\n'+r'Assume $x>0$. $a-b=c$. Value 0.25. \includegraphics{assets/a.png} GLM unresolved issue.'
        for old,new in [('x>0','x>=0'),('a-b','a+b'),('0.25','0.025'),('Assume','Ignore'),('assets/a.png','assets/b.png'),('GLM unresolved issue.','')]:
            with self.subTest(old=old),self.assertRaises(ValueError):syntax.apply_response(text,self.plan(text),json.dumps({'edits':[{'old':old,'new':new}]}))

    def test_existing_math_grouping_and_verbatim_are_protected(self):
        for text,old,new in [('Header\n'+r'$\hat V_x$',r'\hat V_x',r'\(\hat V_x\)'),
                             ('Header\n'+r'$a+{bc}$',r'a+{bc}',r'{a+b}c'),
                             ('Header\n'+r'\begin{verbatim}\hat V_x\end{verbatim}',r'\hat V_x',r'\(\hat V_x\)')]:
            with self.assertRaises(ValueError):syntax.apply_response(text,self.plan(text),json.dumps({'edits':[{'old':old,'new':new}]}))

    def test_out_of_scope_ambiguous_and_whole_document_rejected(self):
        text='\n'.join(['Header',r'\hat V_x']+['Unchanged.']*20+[r'\texttt @}'])
        for value in [{'edits':[{'old':r'\hat V_x','new':r'\(\hat V_x\)'}]}, {'document':DOC}, {'edits':[{'old':'Unchanged.','new':'Other.'}]}]:
            with self.assertRaises(ValueError):syntax.apply_response(text,self.plan(text,23),json.dumps(value))

    def test_first_substantive_error_and_small_low_request(self):
        error=syntax.first_error('./document.tex:2: Too many }\'s.\nl.2 foo\n./document.tex:2: ==> Fatal error occurred')
        self.assertEqual(error['line'],2)
        text='Header\n'+r'\texttt @}'
        req=syntax.request(text,self.plan(text));self.assertEqual(req['reasoning_effort'],'low');self.assertEqual(req['max_tokens'],8192)
        self.assertNotIn('response_format',req)

    def test_raw_and_single_fenced_json_use_existing_parser(self):
        text='Header\n'+r'\texttt @}';value=json.dumps({'edits':[{'old':r'\texttt @}','new':r'\texttt{@}'}]})
        a,_=syntax.apply_response(text,self.plan(text),value);b,_=syntax.apply_response(text,self.plan(text),'```json\n'+value+'\n```')
        self.assertEqual(a,b)


def low_fixture(root):
    native={'key':rec.SOURCE,'source':rec.SOURCE,'title':'Cases','pages':[],
            'blocks':[{'id':'one','kind':'text','tex':r'Case 1. Density $f(x)$ for $x>0$.','page':{'original_physical_page':1},'assets':[]}]}
    section=scope.target(native,['one']);source=root/'inputs'/rec.SOURCE
    atomic_json(source/'native.json',native);atomic_json(source/'assets.json',[])
    atomic_json(source/'secondary.json',{'pages':[{'physical_pdf_page':1,'printed_page':None,'text':'Whole native source.'}]})
    high=scope.request(native,section,'Whole native source.',phase='convert')
    atomic_json(root/'calls/call-030/request.json',high)
    original={'id':rec.KEY+'/convert','key':rec.KEY,'source_key':rec.SOURCE,'phase':'convert','status':'truncation','section':section,'context':''}
    critic=dict(original,id=rec.KEY+'/critic',phase='critic',status='unavailable')
    s={'tasks':[original,critic],'calls':[{'id':'call-030','parent':original['id'],'status':'failed','failure_kind':'truncation','request_sha256':fingerprint(high)}],
       'documents':{rec.SOURCE:{'status':'queued','source_sha256':'source-hash'}},'deferred_sources':{},'versions':{},'current_versions':{},'accuracy':{},
       'source_units':{rec.KEY:{'source_key':rec.SOURCE}},'selection_ledger':[],
       'production_stage':{'task_ids':[original['id'],critic['id']]},'chapter_contract':'annotated-chapter-v1',
       'execution_limits':{'calls':None,'attempts_per_unit':1},'first_dispatch':1,'timing_policy':'manual_only'}
    return s,high


class LowRecoveryTests(unittest.TestCase):
    def test_shared_controller_runs_low_then_own_critic_without_historical_shadow(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,_=low_fixture(r);low=rec.low_tasks(r,s);s['tasks']+=low
            s['production_stage']['task_ids']=[t['id'] for t in low]
            s.update(recovery_continuation={'fixture':True},low_supported=True,status='running',active_stage=1,suite_protocol='originals-batch-v1',
                     concurrency_policy=copy.deepcopy(concurrent.POLICY),connection_failures=0)
            source=r/'inputs'/rec.SOURCE;seal(source)
            atomic_json(r/'input-plan.json',{'dispatch_input':str(source.relative_to(r)),'dispatch_input_seal':sha(source/'manifest.json'),'assets':{}})
            s['documents'][rec.SOURCE]['plan']='input-plan.json';atomic_json(r/'effort-support-live.json',{'low_supported':True})
            seen=[];real=concurrent.coordinate
            def transport(run,call,body,**kw):
                seen.append((call['parent'],copy.deepcopy(body)))
                out=run/'calls'/call['id'];atomic_json(out/'request.json',body);seal(out)
                call.update(status='completed_response',metadata={'finish_reason':'stop'},elapsed_seconds=.01,seal=sha(out/'manifest.json'))
                return DOC,call
            def finish(run,state,task,answer,call):
                p=run/'new-draft.tex';p.write_text(DOC)
                state['versions'][rec.KEY]={'low-draft':{'path':'new-draft.tex','sha256':sha(p)}};state['current_versions'][rec.KEY]='low-draft'
                task.update(status='conversion_completed' if task['phase']=='convert' else 'critic_unchanged',settled_call=call['id'])
            def coordinate(*args,**kwargs):return real(*args,**kwargs,transport=transport,poll_seconds=.01)
            guard=type('Guard',(),{'check':lambda self:None})()
            with patch.object(ctrl.concurrent,'coordinate',side_effect=coordinate),patch.object(ctrl,'finish',side_effect=finish),patch.object(ctrl,'progress'),patch.object(rec,'extra_ids',return_value=[rec.LOW_CONVERT,rec.LOW_CRITIC]):
                ctrl.dispatch(r,s,s['tasks'],lambda n:health(n),guard)
                ctrl.dispatch(r,s,s['tasks'],lambda n:health(n),guard)
            self.assertEqual([x[0] for x in seen],[rec.LOW_CONVERT,rec.LOW_CRITIC])
            self.assertEqual(seen[0][1]['reasoning_effort'],'low');self.assertEqual(seen[1][1]['reasoning_effort'],'max')
            self.assertIn(DOC,seen[1][1]['messages'][0]['content']);self.assertEqual(s['tasks'][0]['status'],'truncation')

    def test_only_effort_changes_and_original_failed_attempt_stays(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,high=low_fixture(r);before=copy.deepcopy(s['calls']);tasks=rec.low_tasks(r,s);s['tasks']+=tasks
            low=rec.body_for(ctrl,r,s,tasks[0]);self.assertEqual(low,dict(high,reasoning_effort='low'));self.assertEqual(s['calls'],before)
            self.assertEqual(low['max_tokens'],131072);self.assertEqual(tasks[1]['reasoning_effort'],'max')
            self.assertEqual(tasks[0]['section'],s['tasks'][0]['section'])

    def test_critic_uses_exact_new_draft_and_rejects_substitution(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,_=low_fixture(r);tasks=rec.low_tasks(r,s);s['tasks']+=tasks
            p=r/'new-draft.tex';p.write_text(DOC);s['versions'][rec.KEY]={'low-draft':{'path':'new-draft.tex','sha256':sha(p)}};s['current_versions'][rec.KEY]='low-draft'
            body=rec.body_for(ctrl,r,s,tasks[1]);self.assertIn(DOC,body['messages'][0]['content']);self.assertEqual(body['reasoning_effort'],'max')
            with patch.object(rec,'extra_ids',return_value=[rec.LOW_CONVERT,rec.LOW_CRITIC]):rec.before_reserve(ctrl,r,s,tasks[1],body)
            self.assertEqual(tasks[1]['dispatched_draft_sha256'],sha(p))
            body['messages'][0]['content']=body['messages'][0]['content'].replace(DOC,'Other source')
            with patch.object(rec,'extra_ids',return_value=[rec.LOW_CONVERT,rec.LOW_CRITIC]),self.assertRaises(runtime.Fatal):rec.before_reserve(ctrl,r,s,tasks[1],body)

    def test_low_support_and_single_attempt_persist(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,_=low_fixture(r);tasks=rec.low_tasks(r,s);s['tasks']+=tasks;s['production_stage']['task_ids']+=[t['id'] for t in tasks]
            atomic_json(r/'effort-support-live.json',{'low_supported':False});body=rec.body_for(ctrl,r,s,tasks[0])
            with patch.object(rec,'extra_ids',return_value=[rec.LOW_CONVERT,rec.LOW_CRITIC]),self.assertRaises(runtime.Fatal):rec.before_reserve(ctrl,r,s,tasks[0],body)
            runtime.reserve(s,rec.LOW_CONVERT,fingerprint(body))
            resumed=copy.deepcopy(s)
            with self.assertRaises(runtime.StopRun):runtime.reserve(resumed,rec.LOW_CONVERT,fingerprint(body))
            self.assertEqual(s['calls'],resumed['calls'])

    def test_failure_proposal_is_offline_and_covers_scope(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,_=low_fixture(r);tasks=rec.low_tasks(r,s);tasks[0].update(status='truncation',call='call-low');s['tasks']+=tasks
            rec.offline_low_proposal(r,s);proposal=read_json(r/'low-recovery/offline-case-proposal.json')
            self.assertEqual([b for g in proposal['groups'] for b in g['blocks']],['one']);self.assertIn('offline_only',proposal['status'])
            self.assertEqual(len(s['calls']),1)


class LineageAndReviewTests(unittest.TestCase):
    def test_repaired_delivery_creates_revision_and_preserves_old_generation(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,_=low_fixture(r);s['documents'][rec.SOURCE].update(units=[rec.KEY],pages=1)
            for t in s['tasks']:t['status']='conversion_completed' if t['phase']=='convert' else 'critic_revised'
            p=r/'v1.tex';p.write_text(DOC);s['versions'][rec.KEY]={'v1':{'path':'v1.tex','sha256':sha(p),'compilation':{'status':'syntax_failure','attempts':[]}}};s['current_versions'][rec.KEY]='v1'
            document={'source_id':rec.SOURCE,'sha256':'source','page_count':1,'title':'Example'}
            old=ctrl.generation(r,s,document);old_hash=sha(old/'manifest.json')
            p2=r/'v2.tex';p2.write_text(DOC+'\n');s['versions'][rec.KEY]['v2']={'path':'v2.tex','sha256':sha(p2),'compilation':{'status':'syntax_failure','attempts':[]}};s['current_versions'][rec.KEY]='v2'
            new=ctrl.generation(r,s,document);self.assertNotEqual(old,new);self.assertEqual(sha(old/'manifest.json'),old_hash)
            self.assertEqual((new/'parts'/rec.KEY/'document.tex').read_text(),DOC+'\n')

    def test_one_task_per_failed_lineage_and_rejected_patch_does_not_retry(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,_=low_fixture(r);s['recovery_continuation']={'test':True};s['tasks'][0]['status']='conversion_completed';s['tasks'][1]['status']='critic_revised'
            p=r/'base.tex';p.write_text('Header\n\\unknowncommand $a-b$.');log=r/'build/console.log';log.parent.mkdir();log.write_text('./document.tex:2: Undefined control sequence.\nl.2 \\unknowncommand')
            s['versions'][rec.KEY]={'base':{'path':'base.tex','sha256':sha(p),'origin':{},'compilation':{'status':'missing_context_or_macro','attempts':[{'path':'build'}]}}};s['current_versions'][rec.KEY]='base'
            rec.queue_repairs(ctrl,r,s);task=s['tasks'][-1];self.assertEqual(task['phase'],'syntax');count=len(s['tasks'])
            rec.queue_repairs(ctrl,r,s);self.assertEqual(len(s['tasks']),count)
            call={'id':'call-repair','status':'completed_response'}
            rec.finish_syntax(ctrl,r,s,task,json.dumps({'edits':[{'old':'a-b','new':'a+b'}]}),call)
            self.assertEqual(task['status'],'syntax_patch_rejected');self.assertEqual(s['current_versions'][rec.KEY],'base')
            resumed=read_json(r/'state.json');rec.queue_repairs(ctrl,r,resumed);self.assertEqual(len(resumed['tasks']),count)

    def test_linked_policy_preserves_deferrals_and_bounds_dynamic_repair(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,high=low_fixture(r)
            s.update(concurrency_policy=copy.deepcopy(concurrent.POLICY),phase_efforts={'convert':'high','critic':'max'})
            excluded={'excluded':{'source_id':'excluded','decision':'deferred','sha256':'e'*64}}
            s['deferred_sources']=excluded
            # A separate completed document with a saved content-build failure.
            key='other-part';source='other';s['documents'][source]={'status':'delivered_with_gaps'};s['source_units'][key]={'source_key':source}
            for phase in ('convert','critic'):
                t={'id':key+'/'+phase,'key':key,'source_key':source,'phase':phase,'status':'conversion_completed' if phase=='convert' else 'critic_revised'}
                s['tasks'].append(t);s['production_stage']['task_ids'].append(t['id'])
            p=r/'other.tex';p.write_text('Header\n\\unknown $x>0$.');atomic_json(r/'collection.json',{'source':'fixture'})
            (r/'build').mkdir();(r/'build/console.log').write_text('./document.tex:2: Undefined control sequence.')
            s['versions'][key]={'v':{'path':'other.tex','sha256':sha(p),'origin':{},'compilation':{'status':'missing_context_or_macro','attempts':[{'path':'build'}]}}};s['current_versions'][key]='v'
            selected=r/'continuations/selected';atomic_json(selected/'prior-state.json',s);b={'code':{'fixture':'hash'},'frozen':{}}
            atomic_json(selected/'binding.json',b);atomic_json(selected/'selection.json',{'inventory_sha256':sha(r/'collection.json'),'candidates':list(excluded.values())});seal(selected)
            s['selection_continuation']={'path':'continuations/selected','seal':sha(selected/'manifest.json')}
            new=r/'continuations/recovery';atomic_json(new/'prior-state.json',s);atomic_json(new/'prior-binding.json',b);atomic_json(new/'binding.json',{'new':'binding'})
            low=rec.low_tasks(r,s);atomic_json(new/'authorization.json',{'policy':rec.POLICY,'low_tasks':[rec.frozen(t) for t in low]});seal(new)
            s.update(recovery_policy=copy.deepcopy(rec.POLICY),recovery_continuation={'path':'continuations/recovery','seal':sha(new/'manifest.json')},binding_path='continuations/recovery/binding.json')
            s['tasks']+=low;s['production_stage']['task_ids']=[x for x in s['production_stage']['task_ids'] if x not in rec.SUPERSEDED]+[t['id'] for t in low]
            rec.queue_repairs(ctrl,r,s);selection.verify(r,s)
            task=s['tasks'][-1];self.assertEqual(task['phase'],'syntax')
            self.assertIn(task['id'],rec.extra_ids(r,s));runtime.reserve(s,task['id'],task['preview_hash'])
            selection.verify(r,s);resumed=copy.deepcopy(s)
            with self.assertRaises(runtime.StopRun):runtime.reserve(resumed,task['id'],task['preview_hash'])
            changed=copy.deepcopy(s);changed['deferred_sources']={}
            with self.assertRaises(ValueError):selection.verify(r,changed)
            (r/task['plan_path']/'request.json').write_text('{}')
            with self.assertRaises(ValueError):rec.extra_ids(r,s)

    def test_initial_repairs_keep_anfuso_equation_13_bytes(self):
        root=Path('/home/mdi/projects/pdf-to-latex/results/originals-recovery-20261102/saved-repairs')
        if not root.exists():self.skipTest('Saved compilation qualification unavailable')
        folder=root/'original-496de5aa992285e2-part-001';before=(folder/'before.tex').read_text();after=(folder/'document.tex').read_text()
        import re
        marker=re.search(re.escape(r'\frac{\rho\alpha + X}'),before)
        self.assertIsNotNone(marker)
        segment=before[max(0,marker.start()-500):marker.end()+500]
        self.assertIn(segment,after)
        for p in root.glob('*/repair.json'):self.assertTrue(read_json(p)['result']['status'].startswith('passed'))

    def test_sample_is_reproducible_and_skips_flagged_pages(self):
        native={'source':'source','blocks':[{'id':str(i),'kind':'text','tex':'Condition '+('x'*70),'page':{'original_physical_page':i}} for i in range(1,5)]}
        a=review.sampled_blocks(native,[1,3],2);self.assertEqual(a,review.sampled_blocks(native,[1,3],2));self.assertEqual({b['page']['original_physical_page'] for b in a},{2,4})

    def test_model_resolved_claim_is_not_independent_acceptance(self):
        self.assertEqual(review.bucket({'status':'resolved_claim_unverified','text':'Corrected sign','category':'material'}),'applied_changes_claimed')
        self.assertEqual(review.bucket({'status':'open','text':'Unresolved independence assumption','category':'material'}),'uncertain_claims')


if __name__=='__main__':unittest.main()
