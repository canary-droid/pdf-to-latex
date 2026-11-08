"""Saved-shape lifecycle regressions; only transport/resource/compiler are mocked."""
import copy,json,shutil,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from probe import followup_lifecycle as c,chapter_concurrency as scheduler
from probe.common import read_json,atomic_json,files_manifest,sha,fingerprint
from scripts import extraction_followup as f
ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'runs/extraction-followup-20261105T204630Z'
DOC=r'\documentclass{article}\usepackage{amsmath}\begin{document}A retained mathematical passage with its required assumptions.\begin{equation}x^2=1\tag{1}\end{equation}\end{document}'

def current():
    fixture=ROOT/'results/followup-lifecycle-development/fixture'
    if not fixture.exists():raise unittest.SkipTest('Local saved-source lifecycle fixture unavailable')
    return fixture

class Contracts(unittest.TestCase):
    def test_actual_empty_pvalues_detects_tables_equations_and_figures(self):
        run=current();key=f.PV+'-whole-1';native=read_json(run/'inputs'/key/'native.json');ids=[b['id'] for b in native['blocks']]
        result=c.coverage(r'\documentclass{article}\begin{document}\end{document}',native,ids)
        self.assertGreater(result['source_tables'],0);self.assertGreater(result['source_equation_blocks'],0)
        self.assertTrue(result['table_count_warning']);self.assertTrue(result['missing_expected_assets']);self.assertTrue(result['empty_or_insubstantial_output'])
    def test_actual_nine_unit_ownership_and_context(self):
        run=current();s=read_json(run/'state.json');p=read_json(run/'plan.json');c.verify_sources(run,s,p)
        ownership=read_json(run/'region-ownership.json');self.assertEqual(ownership['unit_count'],9)
        later=s['source_units'][f.SP+'-whole-5'];earlier=s['source_units'][f.SP+'-whole-4']
        self.assertTrue(set(earlier['section']['blocks'])<=set(later['context_blocks']))
        s['source_units'][f.SP+'-whole-5']['context']+='stale'
        with self.assertRaises(ValueError):c.verify_sources(run,s,p)
    def test_migration_did_not_expand_tasks_or_consumption(self):
        run=current();s=read_json(run/'state.json');p=read_json(run/'plan.json');old=read_json(PARENT/'state.json')
        self.assertEqual([f.focused.definition(t) for t in old['tasks']],[f.focused.definition(t) for t in s['tasks']]);self.assertEqual(len(old['calls']),0)
        self.assertEqual(c.allowance(p,s)['eligible_new'],24)
        bad=copy.deepcopy(p);bad['maximum_model_requests']=100
        with self.assertRaises(ValueError):c.allowance(bad,s)
        t=next(t for t in s['tasks'] if t['id'].startswith('matched-'));t['status']='pending'
        with self.assertRaises(ValueError):c.allowance(p,s)
    def test_tag_whitespace_auto_numbering_is_not_proof(self):
        b={'id':'a','kind':'equation','tex':r'\[x=1\tag { 33 }\]','page':{'original_physical_page':1}}
        n={'blocks':[b]}
        result=c.coverage(r'\begin{document}\begin{equation}x=1\tag{33}\end{equation}\end{document}',n,['a'])
        self.assertEqual(result['source_numbered_equations'],['33']);self.assertFalse(result['automatic_numbering_unverified'])
        result=c.coverage(r'\begin{document}\begin{equation}x=1\end{equation}\end{document}',n,['a'])
        self.assertEqual(result['automatic_numbering_unverified'],['33']);self.assertNotEqual(result['coverage_status'],'complete')
    def test_missing_dependency_cannot_download_in_this_workflow(self):
        from probe import compiler_environment as env
        name=next(n for n,p in env.PACKAGES.items() if p=='texlive-plain-generic')
        def compile_stub(document,folder,**kwargs):
            folder.mkdir(parents=True);(folder/'console.log').write_text("! LaTeX Error: File `"+name+"' not found.")
            return {'status':'missing_package_or_asset'}
        with tempfile.TemporaryDirectory() as tmp, patch.object(env,'verify_seal'):
            root=Path(tmp);state={'disable_dependency_downloads':True,'compiler_environment':{'image':'sha256:fixture','path':'env','seal':'sealed','packages':[]}}
            result=env.compile_saved(root,state,root,'document',root/'build',{},compiler=compile_stub,provision=lambda *a,**k:self.fail('Download attempted'))
            self.assertIn('forbids dependency downloads',result['attempts'][0]['dependency_recovery'])

    def test_assembly_namespaces_bibliography_macros_and_refs(self):
        a=r'\documentclass{article}\usepackage{amsmath}\newcommand{\word}{A}\begin{document}\label{dup}\label{cross}\cite{k}\begin{thebibliography}{9}\bibitem{k}Alpha\end{thebibliography}\end{document}'
        b=a.replace('Alpha','Beta').replace(r'\label{cross}',r'\eqref{cross}')
        master,parts,log=c.assemble_documents([('one',a),('two',b)])
        self.assertEqual(master.count(r'\usepackage{amsmath}'),1);self.assertIn(r'\eqref{one--cross}',parts['two']);self.assertIn(r'\bibitem{two--k}',parts['two']);self.assertFalse(log['unresolved_references'])
        with self.assertRaises(ValueError):c.assemble_documents([('one',a),('two',b.replace('{amsmath}','[bad]{amsmath}'))])

class SavedLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.run=Path(self.tmp.name)
        src=current();self.s=copy.deepcopy(read_json(src/'state.json'));self.plan=read_json(src/'plan.json');self.s['calls']=[];self.s['status']='running'
        for name in ('inputs','quality','region-manifests','versions'):shutil.copytree(src/name,self.run/name)
        atomic_json(self.run/'plan.json',self.plan)
        # Exact saved task set/plan remains; this test dispatches one real pair.
        self.key=f.CF+'-whole-1';self.seen=[];self.pause=False;self.fail_syntax=False
        for t in self.s['tasks']:
            if not t['id'].startswith('matched-'):t['status']='pending' if t['key']==self.key and t['phase']!='syntax' else 'dormant' if t['phase']=='syntax' else 'test_deferred'
        self.compiler=patch.object(f.focused,'compile_version',side_effect=self.compile)
        self.compiler.start();self.addCleanup(self.compiler.stop)
    def compile(self,run,s,key,label):
        v=s['versions'][key][label];v['compilation']={'status':'syntax_failure' if self.fail_syntax else 'passed','attempts':[]}
        return v['compilation']
    def sample(self,owned):
        return {'health':{'context_length':1048576,'pool_tokens':2015232,'pool_free_tokens':1000,'kept_mix':{'rows':1900000},'streams':{'decoding':owned,'prefilling':0,'paused':0,'max':2},'requests_running':owned,'busy':bool(owned)},'memory_available_bytes':{'head':8*1024**3,'peer':12*1024**3},'evidence':{}}
    def transport(self,run,call,body,**kwargs):
        persisted=read_json(run/'state.json');self.assertIn(call['id'],[x['id'] for x in persisted['calls']]);self.seen.append(call['parent'])
        task=next(t for t in self.s['tasks'] if t['id']==call['parent'])
        if task['phase']=='critic':
            draft=(run/self.s['versions'][self.key][task['base_label']]['path']).read_text()
            payload=json.loads(body['messages'][0]['content'].split('\n',1)[1]);self.assertEqual(payload['draft'],draft);self.assertEqual(payload['base_sha256'],f.focused.core.digest(draft))
            answer=json.dumps({'base_sha256':payload['base_sha256'],'findings':[]})
        elif task['phase']=='syntax':answer='{"edits":[]}'
        else:answer='```tex\n'+DOC+'\n```'
        call.update(status='completed_response',elapsed_seconds=.01,metadata={'actual_model':'glm53-regular','finish_reason':'stop','usage':{'completion_tokens':100,'prompt_tokens':30}})
        dest=run/'calls'/call['id'];dest.mkdir(parents=True);atomic_json(dest/'request.json',body);atomic_json(dest/'attempts/one/request.json',{'body':body});atomic_json(dest/'outcome.json',call);(dest/'content.txt').write_text(answer);(dest/'answer.txt').write_text(answer);atomic_json(dest/'manifest.json',files_manifest(dest));call['seal']=sha(dest/'manifest.json')
        if self.pause:atomic_json(run/'pause.json',{'operator':True})
        return answer,call
    def coordinate(self):
        active=[]
        def changed():
            # Do NOT mock away adjust -> progress: this is the original crash.
            f.focused.adjust(self.run,self.s);f.save(self.run,self.s);active[:]=[t for t in self.s['tasks'] if t['status'] not in ('dormant','not_needed')]
        changed();scheduler.coordinate(self.run,self.s,active,body_for=f.focused.body_for,finish=f.finish,verify=lambda:c.allowance(self.plan,self.s),sample=self.sample,changed=changed,fixed_level=2,before_reserve=lambda s,t,b:f.before(self.run,s,t,b),transport=self.transport,poll_seconds=.001)
    def test_real_helper_boundary_reservation_settlement_and_finished_queue(self):
        self.coordinate();self.assertEqual(len(self.s['calls']),2);self.assertEqual(self.seen,[self.key+'/convert',self.key+'/critic']);self.coordinate();self.assertEqual(len(self.seen),2)
        self.assertFalse(any(x.startswith('matched-') for x in self.seen))
    def test_pause_drains_and_sealed_response_is_settled_without_replay(self):
        self.pause=True
        with self.assertRaises(f.runtime.StopRun):self.coordinate()
        self.assertEqual(len(self.seen),1);t=next(t for t in self.s['tasks'] if t['id']==self.key+'/convert');call=self.s['calls'][0]
        # Idempotent settlement of an already sealed exact response.
        f.finish(self.run,self.s,t,(self.run/'calls'/call['id']/'content.txt').read_text(),call)
        self.pause=False;(self.run/'pause.json').unlink();self.coordinate();self.assertEqual(len(self.seen),2)
    def test_stale_critic_draft_refused(self):
        self.pause=True
        with self.assertRaises(f.runtime.StopRun):self.coordinate()
        t=next(t for t in self.s['tasks'] if t['id']==self.key+'/critic');body=f.focused.body_for(self.run,self.s,t);f.before(self.run,self.s,t,body)
        v=self.s['versions'][self.key][t['base_label']];p=self.run/v['path'];p.write_text(p.read_text()+'changed')
        with self.assertRaises(f.runtime.Fatal):f.focused.finish(self.run,self.s,t,'{}',{'id':'fake'})

    def test_syntax_eligibility_consumption_survives_resume(self):
        self.fail_syntax=True
        with patch.object(f.focused.repair,'first_error',return_value={'line':1,'message':'Undefined control sequence'}):
            self.coordinate()
            t=next(t for t in self.s['tasks'] if t['id']==self.key+'/syntax')
            self.assertEqual(t['status'],'syntax_patch_rejected')
            self.assertEqual(len(self.s['calls']),3)
            lineages=copy.deepcopy(self.s['syntax_lineages']);self.coordinate()
            self.assertEqual(self.s['syntax_lineages'],lineages);self.assertEqual(len(self.seen),3)

    def test_restart_after_sealed_response_before_settlement(self):
        task=next(t for t in self.s['tasks'] if t['id']==self.key+'/convert')
        body=f.focused.body_for(self.run,self.s,task);f.before(self.run,self.s,task,body)
        call=f.runtime.reserve(self.s,task['id'],fingerprint(body));task.update(status='running',call=call['id']);f.save(self.run,self.s)
        answer,result=self.transport(self.run,copy.deepcopy(call),body)
        # Exact worker recovery: validate persisted seal, load outcome, settle;
        # no transport is invoked for this already answered reservation.
        folder=self.run/'calls'/call['id'];f.verify_seal(folder);call.update(read_json(folder/'outcome.json'));call['seal']=sha(folder/'manifest.json')
        f.finish(self.run,self.s,task,(folder/'content.txt').read_text(),call)
        self.coordinate();self.assertEqual(self.seen,[self.key+'/convert',self.key+'/critic'])
