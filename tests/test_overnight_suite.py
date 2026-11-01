"""Offline regression checks; no sockets, Docker, generation or credentials."""
import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from probe import speed_suite as q, chapter_glm as runtime, chapter_concurrency as concurrent
from probe.common import atomic_json, read_json
from scripts import speed_suite as ctrl, overnight_suite as prep
from test_speed_suite import fixture, health, BODY


def overnight():
    old=fixture();tasks=[]
    for stage,units,phases in ((1,6,('critic',)),(2,2,('convert','critic')),(3,4,('convert','critic')),(4,13,('convert','critic'))):
        for i in range(units):
            key=f'{stage}-bergomi-{i}'
            for phase in phases:
                t=copy.deepcopy(old['tasks'][0]);t.update(id=key+'/'+phase,key=key,stage=stage,phase=phase,
                    reasoning_effort='high' if stage==1 else 'max' if phase=='critic' else 'low' if stage==2 else 'high',
                    depends_on=key+'/convert' if phase=='critic' and stage!=1 else None,
                    expected_draft_sha256='bound' if stage==1 else None)
                tasks.append(t)
    old.update(suite_protocol=q.OVERNIGHT,tasks=tasks,production_stage={'task_ids':[t['id'] for t in tasks]},
        stages={str(n):{'status':'pending','sessions':[]} for n in range(1,5)})
    old['suite_manifest'].update(protocol=q.OVERNIGHT,tasks=[q.frozen_task(t) for t in tasks],
        estimates={str(n):{'hours_range':[1,4],'basis':[]} for n in range(1,5)})
    return old


class OvernightTests(unittest.TestCase):
    def test_frozen_44_and_no_four_slot_variant(self):
        s=overnight();q.validate_manifest(s['suite_manifest']);self.assertEqual(len(s['tasks']),44)
        with tempfile.TemporaryDirectory() as td:
            r=Path(td)
            with self.assertRaises(runtime.Fatal):
                concurrent.coordinate(r,s,[],body_for=Mock(),finish=Mock(),verify=Mock(),changed=Mock(),sample=Mock(),fixed_level=4)
    def test_four_stages_at_two_terminal_no_replay(self):
        s=overnight();levels=[]
        def dispatch(r,s,ts,**kw):
            levels.append(kw['fixed_level'])
            for t in ts:t['status']='critic_unchanged' if t['phase']=='critic' else 'conversion_completed'
        with tempfile.TemporaryDirectory() as td,patch.object(ctrl,'report'):
            ctrl.run_stages(Path(td),s,sample=lambda n:health(),verify_inputs=Mock(),coordinator=dispatch)
            self.assertEqual(levels,[2,2,2,2]);self.assertEqual(s['status'],q.TERMINAL)
            ctrl.run_stages(Path(td),s,sample=Mock(side_effect=AssertionError('finished')),verify_inputs=Mock(),coordinator=Mock(side_effect=AssertionError('replay')))
    def test_probe_error_only_skips_low_and_independent_stages_continue(self):
        s=overnight();visited=[]
        def dispatch(r,s,ts,**kw):
            visited.append(s['active_stage'])
            for t in ts:t['status']='local_failure'
        with tempfile.TemporaryDirectory() as td,patch.object(ctrl,'report'):
            ctrl.run_stages(Path(td),s,sample=lambda n:health(),verify_inputs=Mock(),coordinator=dispatch,low_supported=False)
        self.assertEqual(visited,[1,3,4]);self.assertEqual(sum(t['status']=='skipped' for t in s['tasks']),4)
    def test_pause_resume_keeps_finished_failed_work_and_frozen_scope(self):
        s=overnight();seen=[]
        def dispatch(r,s,ts,**kw):
            seen.append(s['active_stage'])
            for t in ts:t['status']='failed'
            if len(seen)==1:atomic_json(r/'pause.json',{})
        with tempfile.TemporaryDirectory() as td,patch.object(ctrl,'report'):
            r=Path(td)
            with self.assertRaises(runtime.StopRun):ctrl.run_stages(r,s,sample=lambda n:health(),verify_inputs=Mock(),coordinator=dispatch)
            (r/'pause.json').unlink();s['calls']=[{'id':'call-001','parent':s['tasks'][0]['id'],'status':'failed'}]
            ctrl.run_stages(r,s,sample=lambda n:health(),verify_inputs=Mock(),coordinator=dispatch)
            self.assertEqual(seen,[1,2,3,4]);self.assertEqual(len(s['tasks']),44);self.assertEqual(len(s['calls']),1)
    def test_secondary_target_and_draft_binding_are_immutable(self):
        t=overnight()['tasks'][0];t['secondary_target']='Exact native page text'
        before=q.frozen_task(t);t['secondary_target']='Different';self.assertNotEqual(before,q.frozen_task(t))
    def test_version_compilation_cannot_leak_between_phases_or_failed_critic(self):
        s={'versions':{'x':{'convert-call-001':{'compilation':{'status':'syntax_failure'}},
                           'critic-call-002':{'compilation':{'status':'passed'}}}},'current_versions':{'x':'critic-call-002'}}
        t={'key':'x','phase':'convert','call':'call-001','status':'conversion_completed'}
        self.assertEqual(q.document_result(s,t)['compilation']['status'],'syntax_failure')
        t.update(phase='critic',call='call-003',status='truncation')
        result=q.document_result(s,t);self.assertFalse(result['complete_model_document']);self.assertEqual(result['compilation']['status'],'not_attempted')
    def test_findings_only_annotation_is_not_an_applied_replacement(self):
        t={'key':'x','phase':'critic','call':'call-002','status':'critic_unchanged'}
        s={'versions':{'x':{'critic-call-002-annotated':{'compilation':{'status':'passed'}}}}}
        r=q.document_result(s,t);self.assertFalse(r['complete_model_document']);self.assertIn('NOT applied',r['suggestions']);self.assertEqual(r['compilation']['status'],'not_attempted')
    def test_tag_repair_preserves_equation_content_and_rejects_ambiguous_input(self):
        src='Unchanged prose\n'+r'\begin{equation*}\begin{aligned}a&=b\\c&=d\Bigg).\tag{4.14}'+'\n'+r'\end{aligned}\end{equation*}'
        repaired=prep.repair_tag(src)
        self.assertEqual(src.replace(r'\tag{4.14}',''),repaired.replace(r'\tag{4.14}',''))
        self.assertIn(r'\end{aligned}\tag{4.14}',repaired)
        with self.assertRaises(ValueError):prep.repair_tag(src+src)
    def test_volga_derivation_matches_finite_difference_of_vega(self):
        S,K,tau,sigma=100.,110.,.7,.3
        def vega(x):
            d1=math.log(S/K)/(x*math.sqrt(tau))+x*math.sqrt(tau)/2
            return S*math.sqrt(tau)*math.exp(-d1*d1/2)/math.sqrt(2*math.pi)
        d1=math.log(S/K)/(sigma*math.sqrt(tau))+sigma*math.sqrt(tau)/2;d2=d1-sigma*math.sqrt(tau)
        observed=(vega(sigma+1e-6)-vega(sigma-1e-6))/2e-6
        self.assertAlmostEqual(observed,vega(sigma)*d1*d2/sigma,places=6)
        self.assertGreater(abs(observed-vega(sigma)*d1*d2),1)
    def test_native_page_retention_and_no_guessed_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);atomic_json(r/'secondary.json',{'pages':[{'physical_pdf_page':4,'text':'Chapter 5 locator 5'},{'physical_pdf_page':5,'text':'Condition x > 0'}]})
            text=prep.secondary_span(r,[4,5]);self.assertEqual(text.count('Chapter 5 locator 5'),1);self.assertIn('Condition x > 0',text)
            with self.assertRaises(ValueError):prep.secondary_span(r,[4,4,5])
    def test_effort_probe_failure_is_not_unsupported_low(self):
        with tempfile.TemporaryDirectory() as td:
            helpers=Mock();helpers.CONTAINER='existing';helpers.checked.side_effect=RuntimeError("TemplateSyntaxError: unknown tag 'break'")
            r=ctrl.effort_check(Path(td),helpers);self.assertEqual(r['status'],'probe_error');self.assertFalse(r['low_supported'])
    def test_effort_probe_checks_installed_hashes_and_all_rendered_labels(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);atomic_json(r/'effort-support-offline.json',{'recorded_request_options_sha256':'o','template_sha256':'t'})
            result={'options_sha256':'o','template_sha256':'t','renderer':{'environment_kwargs':{'extensions':['jinja2.ext.loopcontrols']}},
                'results':{e:{'mapped':{'reasoning_effort':e,'enable_thinking':True},'rendered_label':e.capitalize()} for e in ('low','high','max')}}
            h=Mock();h.CONTAINER='existing';h.checked.return_value=json.dumps(result)
            self.assertEqual(ctrl.effort_check(r,h)['status'],'supported')
            result['template_sha256']='changed';h.checked.return_value=json.dumps(result)
            with self.assertRaises(runtime.Fatal):ctrl.effort_check(r,h)
    def test_large_critic_uses_own_draft_and_keeps_all_sources_and_scope(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);f=r/'bergomi/inputs/bergomi-07';f.mkdir(parents=True)
            (f/'source.tex').write_text('FULL PRIMARY '+('x'*120000));(f/'secondary.txt').write_text('FULL NATIVE')
            atomic_json(f/'native.json',{'blocks':[]});atomic_json(f/'assets.json',[])
            task={'source_key':'bergomi-07','section':{'title':'Coherent section','text':'TARGET MATHEMATICS'},'secondary_target':'EXACT TARGET PAGES','context':'Needed definitions'}
            b=ctrl.larger_body(r,task,draft='OWN DRAFT',notes='Open question');text=b['messages'][0]['content']
            for x in ('FULL PRIMARY '+('x'*120000),'FULL NATIVE','TARGET MATHEMATICS','EXACT TARGET PAGES','OWN DRAFT','Open question','Needed definitions'):self.assertIn(x,text)
            self.assertEqual(b['reasoning_effort'],'max');self.assertEqual(b['max_tokens'],131072)
