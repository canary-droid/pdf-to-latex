"""Finite suite protocol, real threaded coordinator with fake transport; no sockets."""
import copy
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from probe import speed_suite as q, chapter_concurrency as scheduler, chapter_glm as runtime
from probe.common import atomic_json, read_json, sha, fingerprint, files_manifest
from scripts import speed_suite as ctrl

BODY={'model':'glm53-regular','messages':[{'role':'user','content':'Complete source.'}],
      'stream':True,'max_tokens':131072,'reasoning_effort':'high'}
DOC=r'\documentclass{article}\begin{document}Complete $x^2$ and conditions.\end{document}'


def fixture():
    tasks=[]
    for stage,units in ((1,4),(2,2),(3,3),(4,2),(5,2)):
        for n in range(units):
            key=f's{stage}-bergomi-{n}'
            for phase in (('critic',) if stage==3 else ('convert','critic')):
                tasks.append({'id':key+'/'+phase,'key':key,'stage':stage,'arm':str(n),'phase':phase,
                    'source_key':'bergomi-01','section':{'blocks':[str(n)],'text':'Full formula and conditions.'},
                    'context':'','reasoning_effort':'high' if stage==3 else 'max' if phase=='critic' else 'low' if stage==5 else 'high',
                    'depends_on':key+'/convert' if phase=='critic' and stage!=3 else None,
                    'expected_draft_sha256':'saved' if stage==3 else None,'draft_label':'saved' if stage==3 else None,
                    'request_recipe':'production','baseline':key,'status':'pending'})
    manifest={'protocol':q.VERSION,'tasks':[q.frozen_task(t) for t in tasks],
        'reference_concurrency':2,'attempts_per_work_request':1,'estimates':{str(n):{'hours_range':[.1,2]} for n in range(1,6)}}
    return {'suite_protocol':q.VERSION,'suite_manifest':manifest,'tasks':tasks,'calls':[],'first_dispatch':None,
        'status':'running','chapter_contract':'annotated-chapter-v1','timing_policy':'manual_only',
        'execution_limits':{'calls':None,'attempts_per_unit':1},'production_stage':{'task_ids':[t['id'] for t in tasks]},
        'current_versions':{},'versions':{},'connection_failures':0,'concurrency_policy':copy.deepcopy(scheduler.POLICY),
        'active_stage':1,'reference_concurrency':None,'stages':{str(n):{'status':'pending','sessions':[]} for n in range(1,6)}}


def health(active=0,slots=4,pool=2015232):
    return {'health':{'context_length':1048576,'pool_tokens':pool,'streams':{'decoding':active,'prefilling':0,'paused':0,'max':slots},
                     'requests_running':active,'busy':bool(active)},
            'memory_available_bytes':{'head':10*1024**3,'peer':12*1024**3},'evidence':{},'at':'test'}


class FrozenProtocolTests(unittest.TestCase):
    def test_exact_23_and_stage_caps(self):
        s=fixture();q.validate_manifest(s['suite_manifest']);self.assertEqual(len(s['tasks']),23)
        for stage in range(1,6):self.assertEqual(len(q.stage_tasks(s,stage)),q.CAPS[stage])
        m=copy.deepcopy(s['suite_manifest']);m['tasks'].append(dict(m['tasks'][0],id='extra'))
        with self.assertRaises(runtime.Fatal):q.validate_manifest(m)
    def test_foreign_stage_and_changed_settings_rejected_before_reserve(self):
        s=fixture();t=s['tasks'][0];q.reservation_guard(s,t,BODY)
        for mutation in ({'id':'production-next'}, {'stage':2}, {'reasoning_effort':'low'}):
            with self.assertRaises(runtime.Fatal):q.reservation_guard(s,dict(t,**mutation),BODY)
        for mutation in ({'temperature':.1},{'model':'other'},{'max_tokens':32768},{'stream':False}):
            with self.assertRaises(runtime.Fatal):q.reservation_guard(s,t,dict(BODY,**mutation))
        s['active_stage']=2
        with self.assertRaises(runtime.Fatal):q.reservation_guard(s,t,BODY)
    def test_consumed_attempt_not_reset_by_failure_or_resume(self):
        s=fixture();t=s['tasks'][0]
        q.reservation_guard(s,t,BODY);c=runtime.reserve(s,t['id'],fingerprint(BODY));c.update(status='failed',failure_kind='truncation')
        resumed=copy.deepcopy(s)
        with self.assertRaisesRegex(runtime.Fatal,'consumed'):q.reservation_guard(resumed,t,BODY)
        self.assertEqual(resumed['calls'],s['calls'])
    def test_extra_and_duplicate_consumed_calls_rejected(self):
        s=fixture();s['calls']=[{'parent':'outside','status':'failed'}]
        with self.assertRaises(runtime.Fatal):q.reservation_guard(s,s['tasks'][0],BODY)
    def test_cross_stage_active_call_stops_new_dispatch(self):
        s=fixture();s['calls']=[{'parent':s['tasks'][0]['id'],'status':'in_progress'}];s['active_stage']=2;t=q.stage_tasks(s,2)[0]
        with self.assertRaisesRegex(runtime.Fatal,'still owns'):q.reservation_guard(s,t,BODY)
    def test_critic_exact_version_and_own_dependency(self):
        s=fixture();c,t=s['tasks'][:2];s['current_versions'][t['key']]='draft';s['versions'][t['key']]={'draft':{'sha256':'abc'}}
        body=dict(BODY,reasoning_effort='max');t['dispatch_draft_sha256']='abc'
        with self.assertRaisesRegex(runtime.Fatal,'dependency'):q.reservation_guard(s,t,body)
        c['status']='conversion_completed';q.reservation_guard(s,t,body)
        t['dispatch_draft_sha256']='wrong'
        with self.assertRaisesRegex(runtime.Fatal,'bound'):q.reservation_guard(s,t,body)
    def test_missing_or_changed_draft_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);p=r/'draft.tex';p.write_text(DOC);s=fixture();t=s['tasks'][1]
            s['current_versions'][t['key']]='d';s['versions'][t['key']]={'d':{'path':'draft.tex','sha256':sha(p)}}
            self.assertEqual(q.verify_draft(r,s,t),DOC);p.write_text('other document')
            with self.assertRaises(runtime.Fatal):q.verify_draft(r,s,t)
    def test_effort_only_variants_keep_exact_payload(self):
        b=dict(BODY,messages=[{'role':'user','content':'Long formula and all sources '+('x'*200000)}])
        for effort in ('low','max'):
            v=q.effort_variant(b,effort);self.assertEqual(set(q.difference(b,v)),{'reasoning_effort'});self.assertEqual(v['messages'],b['messages'])
        self.assertEqual(b['reasoning_effort'],'high')
    def test_simple_arms_only_declared_sources_and_same_assets(self):
        a=q.chapter_request('MINERU_ONLY','NATIVE_COMPLETE',['assets/f.png'],arm='dual')
        b=q.chapter_request('MINERU_ONLY','NATIVE_COMPLETE',['assets/f.png'],arm='native')
        self.assertIn('MINERU_ONLY',a['messages'][0]['content']);self.assertNotIn('MINERU_ONLY',b['messages'][0]['content'])
        for arm in ('dual','native'):
            r=q.chapter_request('MINERU_ONLY','NATIVE_COMPLETE',['assets/f.png'],arm=arm,draft=DOC,notes='An unresolved reference.')
            self.assertIn(DOC,r['messages'][0]['content']);self.assertIn('assets/f.png',r['messages'][0]['content']);self.assertEqual(r['reasoning_effort'],'max')
            self.assertEqual('MINERU_ONLY' in r['messages'][0]['content'],arm=='dual')
    def test_grouping_conserves_adjacent_content_and_repeated_headings(self):
        native={'blocks':[{'id':str(i),'kind':'text','page':{'original_physical_page':i//2+1}} for i in range(4)]}
        sections=[{'title':'Repeated heading','blocks':['0','1'],'text':'First theorem. x<y.'},{'title':'Repeated heading','blocks':['2','3'],'text':'Second condition. x=y.'}]
        g=q.grouped_section(sections,native);self.assertEqual(g['blocks'],['0','1','2','3']);self.assertEqual(g['text'],'First theorem. x<y.\n\nSecond condition. x=y.')
        for bad in ([sections[1],sections[0]],[sections[0],sections[0]], [sections[0],dict(sections[1],blocks=['3'])]):
            with self.assertRaises(ValueError):q.grouped_section(bad,native)


class StageLoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def run_loop(self,state,**kw):
        with patch.object(ctrl,'report'),patch.object(ctrl,'body_for',return_value=BODY):
            return ctrl.run_stages(self.root,state,sample=kw.pop('sample',lambda n:health()),verify_inputs=lambda:None,**kw)
    def test_five_stages_stop_no_book_continuation_or_winner_propagation(self):
        state=fixture();levels=[];visited=[]
        def coord(r,s,ts,**opts):
            visited.append(s['active_stage']);levels.append(opts['fixed_level'])
            for t in ts:t['status']='conversion_completed' if t['phase']=='convert' else 'critic_unchanged'
        self.run_loop(state,coordinator=coord)
        self.assertEqual(visited,[1,2,3,4,5]);self.assertEqual(levels,[4,2,2,2,2]);self.assertEqual(state['status'],q.TERMINAL)
        self.run_loop(state,coordinator=Mock(side_effect=AssertionError('No second pass')))
    def test_unsupported_four_and_low_skip_independent_stages_without_refill(self):
        s=fixture();visited=[]
        def c(r,s,ts,**kw):
            visited.append(s['active_stage'])
            for t in ts:t['status']='local_failure'
        self.run_loop(s,coordinator=c,sample=lambda n:health(slots=2),low_supported=False)
        self.assertEqual(visited,[2,3,4]);self.assertEqual(s['stages']['1']['status'],'skipped');self.assertEqual(s['stages']['5']['status'],'skipped')
        self.assertEqual(len(s['tasks']),23);self.assertEqual(s['status'],q.TERMINAL)
    def test_common_serial_reference_when_only_one_slot_exists(self):
        s=fixture();levels=[]
        def c(r,s,ts,**kw):
            levels.append(kw['fixed_level'])
            for t in ts:t['status']='local_failure'
        self.run_loop(s,coordinator=c,sample=lambda n:health(slots=1))
        self.assertEqual(levels,[1,1,1,1]);self.assertEqual(s['reference_concurrency'],1)
    def test_global_shared_failure_stops_after_current_stage(self):
        s=fixture();c=Mock(side_effect=runtime.Fatal('Changed response identity'))
        with self.assertRaises(runtime.Fatal):self.run_loop(s,coordinator=c)
        c.assert_called_once();self.assertEqual(s['stages']['2']['status'],'pending')
    def test_running_finalization_prevents_stage_advance(self):
        s=fixture()
        def c(r,s,ts,**kw):ts[0]['status']='running'
        with self.assertRaisesRegex(runtime.Fatal,'owns'):self.run_loop(s,coordinator=c)
        self.assertEqual(s['stages']['2']['status'],'pending')
    def test_pause_between_stages_then_resume_skips_finished_stage(self):
        s=fixture();seen=[]
        def c(r,s,ts,**kw):
            seen.append(s['active_stage'])
            for t in ts:t['status']='local_failure'
            atomic_json(r/'pause.json',{})
        with self.assertRaises(runtime.StopRun):self.run_loop(s,coordinator=c)
        self.assertEqual(seen,[1]);(self.root/'pause.json').unlink()
        def resumed(r,s,ts,**kw):
            seen.append(s['active_stage'])
            for t in ts:t['status']='local_failure'
        self.run_loop(s,coordinator=resumed);self.assertEqual(seen,[1,2,3,4,5])
    def test_terminal_launch_is_zero_tests_services_and_readiness(self):
        with patch.object(ctrl,'verify',return_value={'status':q.TERMINAL}),patch.object(ctrl.subprocess,'run',side_effect=AssertionError('must not execute')),patch.object(ctrl.runtime,'readiness',side_effect=AssertionError('no readiness')):
            ctrl.launch(self.root)
    def test_terminal_worker_has_no_readiness_or_service_probe(self):
        with patch.object(ctrl,'verify',return_value={'status':q.TERMINAL}),patch.object(ctrl.os,'dup2'),patch.object(ctrl.runtime,'readiness',side_effect=AssertionError('no readiness')),patch.object(ctrl,'module',side_effect=AssertionError('no service probe')):
            ctrl.worker(self.root)
    def test_unsafe_memory_stops_whole_suite_not_only_stage1(self):
        s=fixture();obs=health();obs['memory_available_bytes']['peer']=1024
        with self.assertRaises(runtime.Fatal):self.run_loop(s,sample=lambda _:obs,coordinator=Mock(side_effect=AssertionError('no dispatch')))


class ThreadedSuiteTests(unittest.TestCase):
    def test_four_unique_outputs_dependencies_and_pause_drains(self):
        for pause in (False,True):
            with self.subTest(pause=pause),tempfile.TemporaryDirectory() as td:
                root=Path(td);s=fixture();ts=q.stage_tasks(s,1);seen=[];lock=threading.Lock();active=0;peak=0
                def body(r,s,t):
                    b=copy.deepcopy(BODY);b['reasoning_effort']=t['reasoning_effort'];b['messages'][0]['content']=t['id']
                    if t['phase']=='critic':t['dispatch_draft_sha256']=s['versions'][t['key']]['draft']['sha256']
                    return b
                def transport(r,c,b,**kwargs):
                    nonlocal active,peak
                    with lock:active+=1;peak=max(peak,active);seen.append(c['parent'])
                    time.sleep(.025)
                    if pause:atomic_json(r/'pause.json',{})
                    c.update(status='completed_response',metadata={'finish_reason':'stop'},elapsed_seconds=.025)
                    d=r/'calls'/c['id'];atomic_json(d/'request.json',b);atomic_json(d/'manifest.json',files_manifest(d));c['seal']=sha(d/'manifest.json')
                    with lock:active-=1
                    return DOC,c
                def finish(r,s,t,a,c):
                    self.assertEqual(c['parent'],t['id']);t['status']='conversion_completed' if t['phase']=='convert' else 'critic_unchanged'
                    s['versions'][t['key']]={'draft':{'sha256':t['key']}};s['current_versions'][t['key']]='draft'
                    if pause:self.assertEqual(s['status'],'draining')
                def go():
                    scheduler.coordinate(root,s,ts,body_for=body,finish=finish,verify=lambda:None,changed=lambda:None,
                        sample=lambda owned:health(owned),transport=transport,poll_seconds=.01,fixed_level=4,before_reserve=q.reservation_guard)
                if pause:
                    with self.assertRaises(runtime.StopRun):go()
                    self.assertEqual(s['status'],'draining');self.assertEqual(len(seen),4)
                else:go();self.assertEqual(len(seen),8)
                self.assertEqual(len(seen),len(set(seen)));self.assertEqual(peak,4);self.assertEqual(active,0)
                for t in ts:
                    if t['phase']=='critic' and t['id'] in seen:self.assertLess(seen.index(t['depends_on']),seen.index(t['id']))
    def test_external_request_is_still_fatal_in_suite_mode(self):
        with tempfile.TemporaryDirectory() as td:
            s=fixture()
            with self.assertRaisesRegex(runtime.Fatal,'Unowned'):
                scheduler.coordinate(Path(td),s,q.stage_tasks(s,1),body_for=lambda *args:BODY,finish=Mock(),verify=lambda:None,
                    changed=lambda:None,sample=lambda owned:health(owned+1),fixed_level=4,transport=Mock(side_effect=AssertionError('no dispatch')))
            self.assertFalse(s['calls'])
    def test_no_experiment_override_for_production_controller(self):
        s=fixture();s.pop('suite_protocol')
        with self.assertRaises(runtime.Fatal):scheduler.coordinate(Path('/unused'),s,[],body_for=Mock(),finish=Mock(),verify=Mock(),changed=Mock(),sample=Mock(),fixed_level=4)
    def test_shared_http_failure_stops_other_work_without_retry(self):
        with tempfile.TemporaryDirectory() as td:
            s=fixture();root=Path(td);seen=[]
            def transport(r,c,b,**kw):
                seen.append(c['parent']);c.update(status='failed',failure_kind='content_or_format',error='Unauthorized local service',metadata={'http_status':401})
                d=r/'calls'/c['id'];atomic_json(d/'request.json',b);atomic_json(d/'manifest.json',files_manifest(d));c['seal']=sha(d/'manifest.json')
                return None,c
            with self.assertRaisesRegex(runtime.Fatal,'infrastructure'):
                scheduler.coordinate(root,s,q.stage_tasks(s,1),body_for=lambda *args:BODY,finish=Mock(side_effect=AssertionError('not a content repair')),
                    verify=lambda:None,changed=lambda:None,sample=lambda n:health(n),transport=transport,fixed_level=1,poll_seconds=.01,before_reserve=q.reservation_guard)
            self.assertEqual(len(seen),1);self.assertEqual(s['stages']['2']['status'],'pending')


if __name__=='__main__':unittest.main()
