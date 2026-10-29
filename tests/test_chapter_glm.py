"""Offline chapter contracts; mocks do not establish live model/TeX quality."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from probe import chapter_inputs as ci, chapter_protocol as cp, chapter_glm as cg, tex_compile
from probe.common import atomic_json, read_json, fingerprint
from probe.local_model import LocalClient, ProbeError
from probe.saved_pages import page_blocks


def inventory(ids=('s-p0001:b0','s-p0001:b1')):
    return {'key':'test','target_ids':list(ids),'split':{'groups':[[ids[0]],[ids[-1]]]},'assets':[]}


def blocks(ids=('s-p0001:b0','s-p0001:b1')):
    return [{'id':x,'kind':'text','tex':'Complete paragraph with conditions.',
             'native':{'type':'text','content':[{'type':'text','content':'Whole paragraph.'}]},'assets':[]} for x in ids]


def answer(inv,tag='whole',assigned=None):
    return '\n'.join('% SRC '+x+'\nComplete paragraph including \\(x\\).'
                     for x in (inv['target_ids'] if assigned is None else assigned))+'\n% END CONVERT '+inv['key']+' '+tag


class ChapterInputsTests(unittest.TestCase):
    def test_schema_default_is_only_admitted_for_verified_blank(self):
        self.assertEqual(page_blocks({'page_idx':0},verified_blank=True),[])
        for pg in ({'page_idx':0},{'page_idx':0,'blocks':None}):
            with self.assertRaises(ValueError):page_blocks(pg)
        with self.assertRaises(ValueError):page_blocks({'blocks':None},verified_blank=True)
        with self.assertRaises(ValueError):page_blocks({'blocks':[{}]},verified_blank=True)

    def test_actual_manifest_all_210_pages_once(self):
        pages=[{'page':{'selected_page':i,'owner':True}} for i in range(1,211)]
        result=ci.select_parts(pages,ci.PARTS)
        self.assertEqual([p['page']['selected_page'] for _,_,group in result for p in group],list(range(1,211)))
        chapter2=next(p for k,_,p in result if k=='02')
        self.assertEqual([p['page']['selected_page'] for p in chapter2],list(range(46,56)))
        self.assertEqual(ci.BLANKS,(3,9,15,21,23,31,199))

    def test_klebaner_boundary_no_chapter5(self):
        pages=[{'page':{'selected_page':i,'original_physical_page':105+i,'owner':True}} for i in range(1,121)]
        selected=ci.select_parts(pages,[('04','Chapter 4',1,31)])[0][2]
        self.assertEqual([p['page']['original_physical_page'] for p in selected],list(range(106,137)))

    def test_duplicate_context_and_overlap_rejected(self):
        pages=[{'page':{'selected_page':i,'owner':True}} for i in (1,2)]
        with self.assertRaises(ValueError):ci.select_parts(pages+pages,[('x','X',1,2)])
        with self.assertRaises(ValueError):ci.select_parts(pages,[('x','X',1,2),('y','Y',2,2)])
        pages[1]['page']['owner']=False
        with self.assertRaises(ValueError):ci.select_parts(pages,[('x','X',1,2)])

    def test_native_strings_not_portable_grammar(self):
        raw=r'\left.\frac{\partial^2 C}{\partial K^2}\right|_{K=0}\quad\text{if }K\ge0'
        self.assertIn(('equation',raw),list(ci.strings({'type':'equation','content':raw})))
        self.assertEqual(list(ci.strings({'type':'text','content':[{'type':'equation_inline','content':r'\tau<t'}]})),[('equation_inline',r'\tau<t')])

    def test_split_refuses_an_unclosed_proof(self):
        bs=[{'id':str(i),'kind':'text','tex':'x'*100,'bbox':[.1,.2,.9,.3],
             'native':{'type':'text','content':[{'type':'text','content':'Proof' if i==0 else 'argument'}]}} for i in range(10)]
        bs[5].update(kind='paragraph_title',native={'level':2,'content':[{'type':'text','content':'Intermediate calculation'}]})
        self.assertEqual(ci.split_plan(bs)['groups'],[])
        bs[5]['native']['content']=[{'type':'text','content':'2.3 Next major section'}]
        self.assertTrue(ci.split_plan(bs)['groups'])
        bs[5]['native']['content']=[{'type':'text','content':'Intermediate calculation'}]
        bs[4]['native']['content']=[{'type':'equation_inline','content':r'\square'}]
        self.assertTrue(ci.split_plan(bs)['groups'])

    def test_coherent_split_preserves_blocks_not_arbitrary_text(self):
        bs=[]
        for i in range(10):
            bs.append({'id':str(i),'kind':'text','tex':'x'*100,'bbox':[.1,.2,.9,.3],
                       'native':{'type':'text','content':[{'type':'text','content':'paragraph'}]}})
        bs[4].update(kind='paragraph_title',native={'type':'paragraph_title','level':2,'content':[{'type':'text','content':'Proof'}]})
        bs[5]['native']['content']=[{'type':'equation_inline','content':r'\square'}]
        bs[6].update(kind='paragraph_title',native={'type':'paragraph_title','level':2,'content':[{'type':'text','content':'Next section'}]})
        plan=ci.split_plan(bs)
        self.assertEqual(plan['boundary_block'],'6')
        self.assertEqual([x for g in plan['groups'] for x in g],[str(i) for i in range(10)])
        bs[6]['bbox'][1]=.02
        self.assertEqual(ci.split_plan(bs)['groups'],[])


class ChapterProtocolTests(unittest.TestCase):
    def test_long_context_no_clipping_or_sampling_override(self):
        source='full source '+('native \\beta and prose\n'*7000)+'TAIL'
        body=cp.request(source,inventory())
        self.assertIn(source,body['messages'][1]['content'])
        self.assertEqual(body['max_tokens'],32768)
        self.assertEqual(set(body),{'model','messages','max_tokens','stream'})
        bound=cp.budget(body)
        with self.assertRaises(ValueError):cp.budget(body,bound['combined_upper_estimate']-1)
        cp.budget(body,bound['combined_upper_estimate'])
        with self.assertRaises(ValueError):cp.request('x'*(2*1024*1024+1),inventory())

    def test_health_requires_idle_workload_and_actual_context(self):
        h={'context_length':1048576,'streams':{'max':4,'decoding':0,'filling':0,'paused':0}}
        self.assertEqual(cp.health_capacity(h),1048576)
        h['streams']['paused']=1
        with self.assertRaises(ValueError):cp.health_capacity(h)
        for h in ({},{'context_length':1048576},{'context_length':False,'streams':{}}):
            with self.assertRaises(ValueError):cp.health_capacity(h)

    def test_raw_tex_and_outer_fence_are_preserved(self):
        inv=inventory();a=answer(inv).replace('\\(x\\)',r'\(\operatorname{Var}(X)\mid\mathcal F_t\)')
        valid,evidence=cp.validate_output('```latex\n'+a+'\n```',inv,phase='convert',blocks=blocks())
        self.assertEqual(valid,a+'\n');self.assertTrue(evidence['outer_fence_stripped'])
        self.assertEqual(evidence['semantic_fidelity'],'not established')

    def test_missing_tail_block_and_duplicate_are_not_complete(self):
        inv=inventory();a=answer(inv)
        for bad in (a[:-10],a.replace('% SRC s-p0001:b1','% SRC s-p0001:b0'),
                    a.replace('% SRC s-p0001:b1','% SRC other'),
                    a.replace('Complete paragraph including \\(x\\).','',1)):
            with self.assertRaises(ValueError):cp.validate_output(bad,inv,phase='convert',blocks=blocks())

    def test_asset_not_silently_dropped(self):
        inv=inventory(('b1',));bs=[{'id':'b1','kind':'table','assets':['assets/abc.png']}]
        with self.assertRaises(ValueError):cp.validate_output(answer(inv),inv,phase='convert',blocks=bs)
        a=answer(inv).replace('Complete paragraph',r'\includegraphics[width=.9\linewidth]{assets/abc.png} Complete paragraph')
        cp.validate_output(a,inv,phase='convert',blocks=bs)

    def test_image_only_formula_must_remain_an_image(self):
        inv=inventory(('b1',));bs=[{'id':'b1','kind':'equation','assets':['assets/formula.png'],
                                  'tex':r'\includegraphics{assets/formula.png}'}]
        with self.assertRaises(ValueError):cp.validate_output(answer(inv),inv,phase='convert',blocks=bs)
        self.assertEqual(cp.required_assets(bs[0]),['assets/formula.png'])
        bs[0]['tex']=r'\[x^2\]'
        self.assertEqual(cp.required_assets(bs[0]),[])

    def test_fresh_review_contains_exact_source_and_generated_only(self):
        inv=inventory();draft=answer(inv);source='Complete original chapter'
        review=cp.request(source,inv,phase='review',generated=draft,context='Exact local reference')
        self.assertEqual([m['role'] for m in review['messages']],['system','user'])
        self.assertIn(source,review['messages'][1]['content']);self.assertIn(draft,review['messages'][1]['content'])
        self.assertNotIn(cp.SYSTEM,review['messages'][0]['content'])
        with self.assertRaises(ValueError):cp.request(source,inv,phase='review')

    def test_split_requests_keep_full_context_and_assembly_order(self):
        inv=inventory();groups=inv['split']['groups'];parts=[]
        for i,g in enumerate(groups):
            req=cp.request('full chapter unchanged',inv,assigned=g,tag=f'section-{i+1}')
            self.assertIn('full chapter unchanged',req['messages'][1]['content'])
            parts.append(answer(inv,f'section-{i+1}',g))
        joined=cp.assemble_sections(parts,groups,inv,blocks())
        self.assertLess(joined.index(groups[0][0]),joined.index(groups[1][0]))
        with self.assertRaises(ValueError):cp.assemble_sections(parts[::-1],groups,inv,blocks())
        with self.assertRaises(ValueError):cp.assemble_sections(parts[:1],groups,inv,blocks())

    def test_chapter_transport_limits_do_not_weaken_legacy(self):
        LocalClient(cp.BASE_URL,cp.MODEL,purpose='chapter',timeout=2700,max_tokens=32768)
        for purpose,timeout in [('text_critic',901),('page_review',601),('capability_probe',601)]:
            with self.assertRaises(ValueError):LocalClient(cp.BASE_URL,purpose=purpose,timeout=timeout)
        with self.assertRaises(ValueError):LocalClient(cp.BASE_URL,purpose='chapter',timeout=2701)
        with self.assertRaises(ValueError):LocalClient(cp.BASE_URL).chapter_health(Path('/unused'))

    def test_health_transport_uses_root_and_retains_evidence(self):
        from urllib.parse import urlsplit
        class Response:
            status=200
            def __init__(self):self.data=b'{"context_length":1048576}'
            def getheaders(self):return []
            def getheader(self,x):return None
            def read1(self,n):data=self.data;self.data=b'';return data
        class Connection:
            sock=None
            def connect(self):pass
            def close(self):pass
            def request(self,method,path,**kwargs):self.path=path
            def getresponse(self):return Response()
        with tempfile.TemporaryDirectory() as td:
            c=LocalClient(cp.BASE_URL,cp.MODEL,purpose='chapter');conn=Connection()
            with patch.object(c,'_connection',return_value=(conn,urlsplit(cp.BASE_URL))):data,ev=c.chapter_health(Path(td))
            self.assertEqual(conn.path,'/health')
            self.assertEqual(read_json(Path(ev['attempt_dir'])/'request.json')['url'],'http://192.168.1.100:8888/health')


class ChapterBudgetTests(unittest.TestCase):
    def state(self):return {'first_dispatch':None,'calls':[]}

    def test_idle_time_counts_and_no_reset_on_resume(self):
        s=self.state();cg.reserve(s,'t','a',wall=100)
        restored=json.loads(json.dumps(s))
        cg.reserve(restored,'readiness','b',wall=200)
        self.assertEqual(restored['first_dispatch'],100)
        with self.assertRaises(cg.StopRun):cg.reserve(restored,'t','c',wall=100+8*3600)
        self.assertEqual(len(restored['calls']),2)

    def test_shared_extra_and_global_limits_include_uncertain(self):
        s=self.state()
        for i in range(3):cg.reserve(s,'t',str(i),wall=100)
        with self.assertRaises(cg.StopRun):cg.reserve(s,'t','four',wall=101)
        for i in range(77):cg.reserve(s,'readiness',str(i),wall=101)
        with self.assertRaises(cg.StopRun):cg.reserve(s,'readiness','81',wall=102)

    def test_truncation_even_with_reasoning_and_partial_content(self):
        r={'finish_reason':'length','actual_model':cp.MODEL,'usage':{'completion_tokens':32768,'completion_tokens_details':{'reasoning_tokens':30000}}}
        self.assertEqual(cg.classify_failure(r,'partial final'),'truncation')
        r.pop('usage');self.assertEqual(cg.classify_failure(r,'partial'),'truncation')
        r['actual_model']='wrong';self.assertEqual(cg.classify_failure(r,'partial'),'identity')


class ChapterExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.run=self.root/'run';self.run.mkdir();self.preview=self.root/'preview'
        self.inv=inventory();folder=self.preview/'chapters/test';folder.mkdir(parents=True)
        atomic_json(folder/'inventory.json',self.inv);atomic_json(folder/'source.json',{'blocks':blocks()})
        (folder/'source.tex').write_text('Complete chapter source')
        prepared=self.run/'prepared/test';prepared.mkdir(parents=True);(prepared/'review-context.txt').write_text('')
        self.task={'id':'test/convert','key':'test','phase':'convert','status':'pending'}
        self.state={'first_dispatch':None,'calls':[],'connection_failures':0,'compile_unavailable':'mocked offline', 'tasks':[self.task]}

    def fake_invoke(self,outputs):
        def invoke(run,state,parent,body,**kw):
            c=cg.reserve(state,parent,fingerprint(body));out=outputs.pop(0)
            c.update(status='completed_response' if out is not None else 'failed',failure_kind='truncation',error='length')
            return out,c
        return invoke

    def test_length_adapts_to_two_sections_with_same_context(self):
        groups=self.inv['split']['groups']
        outputs=[None]+[answer(self.inv,f'section-{i+1}',g) for i,g in enumerate(groups)]
        with patch.object(cg,'invoke',side_effect=self.fake_invoke(outputs)),patch.object(cg,'compile_chapter') as comp:
            cg.execute_task(self.run,self.state,self.task,self.preview)
        self.assertEqual(self.task['status'],'completed');self.assertEqual(len(self.state['calls']),3)
        self.assertEqual(len(self.task['sections']),2);comp.assert_called_once()
        text=(self.run/self.task['output']).read_text()
        self.assertIn('s-p0001:b0',text);self.assertIn('s-p0001:b1',text)

    def test_invalid_repairs_exhaust_without_completion(self):
        outputs=['bad answer']*3
        self.inv['split']['groups']=[];atomic_json(self.preview/'chapters/test/inventory.json',self.inv)
        with patch.object(cg,'invoke',side_effect=self.fake_invoke(outputs)):
            cg.execute_task(self.run,self.state,self.task,self.preview)
        self.assertEqual(len(self.state['calls']),3);self.assertEqual(self.task['status'],'failed')
        self.assertFalse((self.run/'chapters/test/draft.tex').exists())

    def test_uncertain_interruption_is_not_replayed(self):
        cg.reserve(self.state,'test/convert','a')
        with patch.object(cg,'invoke') as call:cg.execute_task(self.run,self.state,self.task,self.preview)
        call.assert_not_called();self.assertEqual(self.task['status'],'unresolved_interruption')
        self.assertEqual(len(self.state['calls']),1)

    def test_complete_but_unfinalized_response_is_not_replayed(self):
        c=cg.reserve(self.state,'test/convert','a');c['status']='completed_response'
        with patch.object(cg,'invoke') as call:cg.execute_task(self.run,self.state,self.task,self.preview)
        call.assert_not_called();self.assertEqual(self.task['status'],'unresolved_interruption')

    def test_readiness_rejects_empty_and_wrong_output(self):
        for result in ('','something',None):
            with patch.object(cg,'invoke',return_value=(result,{'id':'x'})):
                with self.assertRaises(cg.StopRun):cg.readiness(self.run,self.state)
        self.assertFalse((self.run/'latest-readiness.json').exists())

    def test_successful_invoke_serialization_and_identity(self):
        class Fake:
            response_model=cp.MODEL
            def __init__(self,*a,**kw):self.kw=kw
            def discover_model(self,out):return {'selected_model':cp.MODEL}
            def chapter_health(self,out):return {'context_length':1048576,'streams':{'decoding':0,'filling':0}},{}
            def chat(self,messages,dest,label):return {'content':'Complete answer','actual_model':self.response_model,'usage':{'completion_tokens':123},'finish_reason':'stop'}
        body=cp.request('source',self.inv)
        content,call=cg.invoke(self.run,self.state,'test/convert',body,client_factory=Fake)
        self.assertEqual(content,'Complete answer');self.assertEqual(len(self.state['calls']),1)
        self.assertEqual(read_json(self.run/'calls'/call['id']/'request.json'),body)
        Fake.response_model='wrong'
        with self.assertRaises(cg.Fatal):cg.invoke(self.run,self.state,'other',body,client_factory=Fake)
        self.assertEqual(self.state['calls'][-1]['failure_kind'],'identity')


class ChapterAssetTests(unittest.TestCase):
    def test_staging_relative_assets_and_escape_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'body.tex';src.write_text('Relative body.');dst=root/'dst';dst.mkdir()
            records=tex_compile.stage_assets({'parts/body.tex':src},dst)
            self.assertEqual((dst/'parts/body.tex').read_text(),'Relative body.')
            self.assertEqual(records[0]['path'],'parts/body.tex')
            for path in ('../escape.tex','/parts/body.tex','assets/../x.tex','parts/./x.tex','parts/a.sh','document.tex'):
                with self.assertRaises(ValueError):tex_compile.stage_assets({path:src})
            link=root/'link.tex';link.symlink_to(src)
            with self.assertRaises(ValueError):tex_compile.stage_assets({'parts/body.tex':link})

    def test_mock_compiler_receives_allowlisted_include_and_isolation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'body.tex';src.write_text('Relative include: \\(x\\).')
            def runner(cmd,**kw):
                mount=next(x for x in cmd if x.startswith('type=bind,src=') and 'dst=/source' in x)
                source=Path(mount.split('src=')[1].split(',')[0])
                self.assertEqual((source/'parts/body.tex').read_text(),src.read_text())
                self.assertIn('--network=none',cmd);self.assertIn('openin_any=p',cmd);self.assertIn('-no-shell-escape',cmd)
                self.assertEqual(cmd[-1],'document.tex')
                return subprocess.CompletedProcess(cmd,0,b'fake TeX execution, not real compilation')
            with patch('probe.tex_compile.shutil.which',return_value='/usr/bin/docker'):
                result=tex_compile.compile_document(cp.document(r'\input{parts/body.tex}'),root/'out',image=cp.IMAGE,
                    runner=runner,assets={'parts/body.tex':src})
            self.assertEqual(result['assets'][0]['path'],'parts/body.tex')

    @unittest.skipUnless(os.environ.get('PDF2TEX_COMPILER_IMAGE'),'Opt-in real Docker compiler unavailable/offline')
    def test_real_allowlisted_relative_include_when_operator_enabled(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'body.tex';src.write_text('Relative include: \\(x^2\\).')
            result=tex_compile.compile_document(cp.document(r'\input{parts/body.tex}'),root/'out',
                image=os.environ['PDF2TEX_COMPILER_IMAGE'],assets={'parts/body.tex':src})
            self.assertTrue(result['compilation_claim'],result)
            self.assertTrue((root/'out/document.pdf').is_file())


class ChapterControllerIntegrationTests(unittest.TestCase):
    def test_workload_check_reads_both_nodes_and_refuses_alternative(self):
        with tempfile.TemporaryDirectory() as td,patch.object(cg,'converter_idle'),\
             patch.object(cg.shutil,'which',return_value='/existing/tool'),\
             patch.object(cg.subprocess,'run',side_effect=[
                 subprocess.CompletedProcess([],0,'regular-glm-head\n',''),
                 subprocess.CompletedProcess([],0,'qwen-peer\n','')]) as run:
            with self.assertRaisesRegex(cg.StopRun,'peer'):cg.check_other_jobs(Path(td))
            self.assertEqual(run.call_args_list[0].args[0],['docker','ps','--format','{{.Names}}'])
            self.assertEqual(run.call_args_list[1].args[0][0],'ssh')
            self.assertIn('BatchMode=yes',run.call_args_list[1].args[0])

    def test_serial_plan_and_resume_preserve_completed_work(self):
        from probe.common import files_manifest,sha
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);preview=root/'preview';preview.mkdir();(preview/'assets').mkdir()
            parts=[]
            keys=['klebaner-04']+['gatheral-'+k for k,_,_,_ in ci.PARTS]
            for key in keys:
                inv=inventory((key+':b0',key+':b1'));inv.update(key=key,title=key,
                    source='gatheral' if key.startswith('gatheral') else 'klebaner-ch4-7',
                    pages=[1],original_pages=[1],block_count=2,native_math_strings=0,
                    source_characters=20,all_native_math_present=True)
                bs=blocks(tuple(inv['target_ids']));folder=preview/'chapters'/key;folder.mkdir(parents=True)
                atomic_json(folder/'inventory.json',inv)
                atomic_json(folder/'source.json',{'blocks':bs,'fallback':[]})
                (folder/'source.tex').write_text('Complete chapter source '+key)
                parts.append(inv)
            atomic_json(preview/'inputs.json',{'parts':parts,'consumed':{}})
            atomic_json(preview/'manifest.json',files_manifest(preview))
            class Fake:
                dispatched=[]
                def __init__(self,*a,**kw):pass
                def discover_model(self,out):return {'selected_model':cp.MODEL}
                def chapter_health(self,out):return {'context_length':1048576,'streams':{'decoding':0,'filling':0}},{}
                def chat(self,messages,dest,label):
                    self.dispatched.append(copy.deepcopy(messages))
                    if len(messages)==1:content='CHAPTER_READY'
                    else:
                        text=messages[1]['content']
                        assigned=json.loads(text.split('ASSIGNED BLOCKS:\n')[1].split('\nFULL EXTRACTED CHAPTER:')[0])
                        end=text.split('standalone line: ')[1].split('\n')[0]
                        if end.startswith('% END CONVERT'):
                            content='\n'.join('% SRC '+x+'\nComplete unchanged paragraph.' for x in assigned)+'\n'+end
                        else:content='No material issue detected in supplied text; this is not proof. Reviewed: '+str(assigned)+'\n'+end
                    return {'content':content,'actual_model':cp.MODEL,'finish_reason':'stop','usage':{'completion_tokens':20}}
            with patch.object(cg,'ROOT',root),patch.object(cg,'POINTER',root/'results/current.json'),\
                 patch.object(ci,'new_path',return_value=root/'run'),patch.object(cg,'code_hashes',return_value={}),\
                 patch.object(cg,'check_other_jobs'),patch.object(cg,'compile_chapter'),\
                 patch.object(cg.tex_compile,'compile_document',return_value={'status':'unavailable'}):
                run=cg.initialize(preview)
                self.assertEqual(cg.execute(run,client_factory=Fake),0)
                state=read_json(run/'state.json');first=state['first_dispatch']
                self.assertEqual(len(state['calls']),29)
                self.assertTrue(all(t['status']=='completed' for t in state['tasks']))
                order=[c['parent'] for c in state['calls']]
                self.assertEqual(order[:3],['readiness','klebaner-04/convert','klebaner-04/review'])
                self.assertEqual(order[3:14],[f'gatheral-{i:02d}/convert' for i in range(1,12)])
                # Avoid intentionally colliding timestamped ZIP names in this fast mock.
                with patch.object(cg,'bundle',return_value=root/'mock-resume.zip'):
                    self.assertEqual(cg.execute(run,resume=True,client_factory=Fake),0)
                resumed=read_json(run/'state.json')
                self.assertEqual(len(resumed['calls']),30)
                self.assertEqual(resumed['first_dispatch'],first)
                self.assertEqual(resumed['calls'][-1]['parent'],'readiness')
                self.assertEqual(len(Fake.dispatched),30)


if __name__=='__main__':unittest.main()
