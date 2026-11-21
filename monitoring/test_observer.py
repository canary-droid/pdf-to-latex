import importlib.util, json, os, tempfile, threading, time, unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('observer',Path(__file__).with_name('observer.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.base=self.root/'monitor';self.run=self.root/'runs/example';self.run.mkdir(parents=True)
        self.rootpatch=patch.object(m,'ROOT',self.root);self.rootpatch.start()
        self.proc={'pid':123,'start_ticks':'100','boot_id':'boot1','argv':['python',str(self.root/'scripts/library_pipeline.py'),'worker','--run',str(self.run)]}
        self.wp=patch.object(m,'workers',return_value=[self.proc]);self.wp.start()
        self.lp=patch.object(m,'lock_owners',return_value=[123]);self.lp.start()
        m.atom(self.run/'plan.json',{'workflow':'library-first-v1'})
        m.atom(self.run/'binding.json',{'plan_sha256':m.sha(self.run/'plan.json')})
        self.s={'status':'running','stage':'conversion','launches':[{'pid':123}], 'tasks':[{'id':'unit/convert','status':'pending'}],'calls':[]}
        self.p={'status':'running','run':str(self.run),'at':'2026-11-09T00:00:00Z','documents':{'src':{'filename':'paper.pdf','status':'partial','outstanding_scopes':[{'pages':[1,2],'reason':'missing'}]}}}
        self.save();self.target=m.pin(self.run);self.target['worker']=m.worker_identity(self.proc)
        s=m.initial();s.update(target=self.target,enabled=True);m.atom(self.base/'state.json',s)
        self.fake=self.root/'fake-codex'
        self.fake.write_text("#!/usr/bin/python3\nimport json,sys,pathlib\np=pathlib.Path.cwd()/'invocations'\np.write_text(p.read_text()+'x' if p.exists() else 'x')\nassert '--ignore-user-config' in sys.argv and '--ephemeral' in sys.argv\nassert 'resume' not in sys.argv\nassert len(sys.stdin.read())<16000\nprint(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'healthy: disposable fixture only'}}))\nprint(json.dumps({'type':'turn.completed','usage':{'input_tokens':40,'output_tokens':8}}))\n")
        self.fake.chmod(0o700)
        self.cp=patch.object(m,'codex_path',return_value=str(self.fake));self.cp.start()
        saved=m.state(self.base);saved['qualification']={'passed':True,'monitor_sha256':m.code_identity(),'codex_sha256':m.sha(self.fake)};m.atom(self.base/'state.json',saved)
    def tearDown(self):self.cp.stop();self.lp.stop();self.wp.stop();self.rootpatch.stop();self.tmp.cleanup()
    def save(self):m.atom(self.run/'state.json',self.s);m.atom(self.run/'progress.json',self.p)
    def execute(self,b,e,s):return m.dispatch(b,e,s,str(self.fake))
    def tick(self,now=10000):return m.tick(self.base,self.execute,now)
    def state(self):return m.state(self.base)
    def test_unchanged_and_advancing(self):
        a=m.observe(self.target,now=10000);b=m.observe(self.target,a,10300)
        self.assertFalse(b['progress_changed']);self.assertEqual(b['progress_epoch'],10000)
        self.s['tasks'][0]['status']='conversion_completed';self.save();c=m.observe(self.target,b,10600)
        self.assertTrue(c['progress_changed']);self.assertEqual(c['changes']['finished_tasks'],1)
    def test_slow_stream_is_not_stall_or_success(self):
        a=m.observe(self.target,now=time.time()-3600)
        self.s['calls']=[{'id':'call-001','status':'running'}];self.save()
        f=self.run/'calls/call-001/attempts/a/stream-events.jsonl';f.parent.mkdir(parents=True);f.write_text('private')
        b=m.observe(self.target,a,time.time());self.assertEqual(b['health'],'healthy');self.assertTrue(b['long_request_active']);self.assertEqual(b['progress_epoch'],a['progress_epoch']);self.assertNotIn('private',json.dumps(b))
    def test_stall_does_not_mutate_worker(self):
        a=m.observe(self.target,now=1);b=m.observe(self.target,a,1900)
        self.assertEqual(b['incident'],'no_progress_without_recent_stream')
    def test_missing_worker(self):
        with patch.object(m,'workers',return_value=[]):b=m.observe(self.target,now=1)
        self.assertEqual(b['incident'],'worker_missing_or_ownership_uncertain')
    def test_pid_reuse(self):
        self.proc['start_ticks']='200';b=m.observe(self.target,now=1)
        self.assertEqual(b['incident'],'pid_identity_reused')
    def test_process_start_and_boot_real(self):
        p=m.process(os.getpid());self.assertTrue(p['start_ticks']);self.assertTrue(p['boot_id']);self.assertFalse(m.owns(p,self.run))
    def test_legitimate_handoff(self):
        self.proc.update(pid=124,start_ticks='201');self.s['launches'].append({'pid':124});self.save()
        with patch.object(m,'lock_owners',return_value=[124]):b=m.observe(self.target,now=1)
        self.assertEqual(b['health'],'healthy')
    def test_unreadable_and_partial_are_unknown(self):
        (self.run/'state.json').write_text('{');self.assertEqual(m.observe(self.target)['health'],'unknown')
        self.save();self.p['status']='prepared';self.save();self.assertEqual(m.observe(self.target)['health'],'unknown')
    def test_changed_identity(self):
        m.atom(self.run/'plan.json',{'workflow':'changed'});self.tick();s=self.state()
        self.assertFalse(s['events']);self.assertIn('identity',s['dispatch_blocker'])
    def test_duplicate_ticks_and_restart_do_not_replay(self):
        self.tick();self.tick(10001);self.tick(10002);self.assertEqual(len(self.state()['events']),1)
        self.assertEqual(self.state()['events'][0]['usage'][0]['input_tokens'],40)
    def test_concurrent_ticks(self):
        entered=threading.Event();leave=threading.Event()
        def slow(*args):entered.set();leave.wait(5);return {'outcome':'success'}
        thread=threading.Thread(target=lambda:m.tick(self.base,slow,10000));thread.start();entered.wait(2)
        with self.assertRaises(BlockingIOError):self.tick()
        leave.set();thread.join();self.assertEqual(len(self.state()['events']),1)
    def test_stable_incident(self):
        with patch.object(m,'workers',return_value=[]):
            self.tick();self.tick(10300);self.tick(10600)
        self.assertEqual(len(self.state()['events']),1)
    def test_incident_can_return_only_twice(self):
        for now in (10000,10300,10600):
            with patch.object(m,'workers',return_value=[]):self.tick(now)
            self.tick(now+1)
        self.assertEqual(sum(e['reason']=='incident' for e in self.state()['events']),2)
    def test_dispatch_exception_reserves_and_blocks(self):
        def fail(*a):raise OSError('disconnect')
        m.tick(self.base,fail,10000);self.tick(20000)
        self.assertEqual(len(self.state()['events']),1);self.assertEqual(self.state()['events'][0]['outcome'],'uncertain')
    def test_crash_after_reservation_does_not_replay(self):
        s=self.state();m.reserve(self.base,s,'routine','x',1);self.tick(20000)
        self.assertEqual(len(self.state()['events']),1);self.assertIn('Unsettled',self.state()['dispatch_blocker'])
    def test_failed_exec_blocks(self):
        self.fake.write_text('#!/usr/bin/python3\nraise SystemExit(2)\n');s=self.state();s['qualification']['codex_sha256']=m.sha(self.fake);m.atom(self.base/'state.json',s);self.tick();self.tick(20000)
        self.assertEqual(len(self.state()['events']),1);self.assertEqual(self.state()['events'][0]['outcome'],'blocked')
    def test_rolling_caps_and_no_catchup(self):
        s=self.state();s['events']=[{'id':str(n),'reason':'routine','reserved_epoch':10000-n,'outcome':'success'} for n in range(12)];m.atom(self.base/'state.json',s)
        self.tick(20000);self.assertEqual(len(self.state()['events']),12)
        self.tick(100000);self.tick(100001);self.assertEqual(len(self.state()['events']),13)
    def test_incident_cap(self):
        s=self.state();s['events']=[{'reason':'incident','key':str(n),'reserved_epoch':10000-n,'outcome':'success'} for n in range(4)];m.atom(self.base/'state.json',s)
        with patch.object(m,'workers',return_value=[]):self.tick(10001)
        self.assertEqual(len(self.state()['events']),4)
    def test_pause_disable_durable(self):
        for action in ('pause','disable'):
            m.control(self.base,action);self.tick();self.assertFalse(self.state()['events'])
    def test_pause_while_checkpoint_does_not_wait(self):
        with m.lock(self.base):m.control(self.base,'pause')
        self.tick();self.assertFalse(self.state()['events'])
    def test_terminal_partial_once(self):
        self.s['status']=self.p['status']=m.TERMINAL;self.save()
        with patch.object(m,'workers',return_value=[]),patch.object(m,'lock_owners',return_value=[]):
            result=self.tick();self.tick(20000)
        self.assertEqual(result['health'],'finished');self.assertEqual(result['counts']['partial_sources'],1)
        self.assertEqual(len(self.state()['events']),1);self.assertFalse(self.state()['enabled'])
    def test_terminal_live_request_unknown(self):
        self.s['status']=self.p['status']=m.TERMINAL;self.s['calls']=[{'id':'call-1','status':'reserved'}];self.save()
        self.assertEqual(m.observe(self.target)['health'],'unknown')
    def test_failed_final_no_retry(self):
        self.s['status']=self.p['status']=m.TERMINAL;self.save()
        with patch.object(m,'workers',return_value=[]),patch.object(m,'lock_owners',return_value=[]):
            m.tick(self.base,lambda *a:{'outcome':'blocked'},10000);self.tick(20000)
        self.assertTrue(self.state()['pending_final_report']);self.assertEqual(len(self.state()['events']),1)
    def test_no_protected_mutations(self):
        before={str(p):m.sha(p) for p in self.run.rglob('*') if p.is_file()};self.tick()
        self.assertEqual(before,{str(p):m.sha(p) for p in self.run.rglob('*') if p.is_file()})
    def test_snapshot_bound_and_redaction(self):
        self.s['diagnostic']='api_key=private-secret bearer abcdef password=secret';self.save()
        a=m.observe(self.target);self.assertNotIn('private-secret',json.dumps(a));self.assertNotIn('abcdef',json.dumps(a))
        a['outstanding']=['x'*1000]*100;self.assertLessEqual(len(json.dumps(m.compact(a)).encode()),12000)
    def test_permissions_and_no_host_bridge(self):
        cfg=m.settings(self.base);self.assertEqual(cfg['permissions']['observer']['filesystem'][':root'],'deny')
        self.assertFalse(cfg['permissions']['observer']['network']['enabled']);self.assertFalse(cfg['features']['shell_tool'])
        self.assertFalse(any(x=='write' for x in cfg['permissions']['observer']['filesystem'].values()))
        cmd=m.build_command(str(self.fake),self.base);self.assertNotIn('--ignore-rules',cmd);self.assertNotIn('resume',cmd)
    def test_attach_finished_never(self):
        self.s['status']=self.p['status']=m.TERMINAL;self.save()
        s=self.state();s['qualification']={'passed':True,'monitor_sha256':m.code_identity(),'codex_sha256':m.sha(self.fake)};m.atom(self.base/'state.json',s)
        with patch.object(m,'codex_path',return_value=str(self.fake)),self.assertRaisesRegex(ValueError,'Finished'):m.attach(self.base,self.run)
    def test_no_qualification_no_model_call(self):
        saved=self.state();saved.pop('qualification');m.atom(self.base/'state.json',saved)
        self.tick();self.assertFalse(self.state()['events']);self.assertIn('not qualified',self.state()['dispatch_blocker'])
    def test_active_attach_preserves_allowances(self):
        self.tick();before=self.state()['events']
        m.control(self.base,'pause');m.attach(self.base,self.run)
        self.assertEqual(self.state()['events'],before);self.tick(10001);self.assertEqual(len(self.state()['events']),1)
    def test_wrong_run_progress_unknown(self):
        self.p['run']='/other';self.save();self.assertEqual(m.observe(self.target)['health'],'unknown')
    def test_terminal_reservation_crash_marker(self):
        saved=self.state();m.reserve(self.base,saved,'terminal','one',1)
        self.tick();self.assertTrue(self.state()['pending_final_report']);self.assertFalse(self.state()['enabled'])
    def test_tool_activity_blocks_future_calls(self):
        self.fake.write_text('#!/usr/bin/python3\nimport json\nprint(json.dumps({"type":"item.completed","item":{"type":"command_execution","command":"forbidden"}}))\n')
        saved=self.state();saved['qualification']['codex_sha256']=m.sha(self.fake);m.atom(self.base/'state.json',saved)
        self.tick();self.assertEqual(self.state()['events'][0]['forbidden_items'],['command_execution']);self.tick(20000);self.assertEqual(len(self.state()['events']),1)
    def test_exact_nonfatal_notice_reclassification(self):
        event={'id':'saved','reason':'qualification'};self.execute(self.base,event,{'safe':'fixture'})
        job=self.base/'checks/saved';path=job/'events.jsonl';original=path.read_text()
        message=('Under-development features enabled: skip_host_skill_discovery. '
          'Under-development features are incomplete and may behave unpredictably. '
          'To suppress this warning, set `suppress_unstable_features_warning = true` in '+str(m.HOME/'.codex/config.toml')+'.')
        path.write_text(json.dumps({'type':'item.completed','item':{'type':'error','message':message}})+'\n'+original)
        self.assertEqual(m.collect_result(job,0)['outcome'],'success')
        path.write_text(json.dumps({'type':'item.completed','item':{'type':'error','message':'authentication failed'}})+'\n'+original)
        self.assertEqual(m.collect_result(job,0)['outcome'],'blocked')
    def test_qualification_cannot_repeat(self):
        s=self.state();m.reserve(self.base,s,'qualification','one',1)
        with self.assertRaisesRegex(ValueError,'already reserved'):m.qualify(self.base)

if __name__=='__main__':unittest.main()
