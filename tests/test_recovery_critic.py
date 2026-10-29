"""Offline recovery/critic contracts; no live servers, installation or TeX claims."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from probe import recovery as r, text_critic as tc, experiment as ex, tex_compile as tex
from probe.common import atomic_json,read_json,sha,fingerprint,files_manifest
from probe.portable_export import accepted_fragment,typed_fragment,render_block,portable_document
from probe.evaluation_export import edits_for,build_candidate,bundle,draft
from probe.recovery_trial import save_unit,finish_preview,CONFIG,prepare_critic
from probe.local_model import LocalClient,ProbeError
from probe.batch_review import IdentityError,IntegrityError
from probe.bibliography import inventory,candidate_bib


def block(n=1,kind='text',content=None):
    return {'id':f'p1:b{n}','kind':kind,'reading_order':n,'bbox':[0,0,1,1],
            'native':{'content':content or [{'type':'text','content':'For '},{'type':'equation_inline','content':r'\alpha>0'},{'type':'text','content':', the bound holds.'}]}}


def data(n=1):
    return {'page_id':'p1','source_id':'synthetic','page':{'original_physical_page':1},'review_scope':'selected_blocks',
        'blocks':[block(n)],'context_blocks':[],'draft_by_block':[],'images':[]}


def valid(d):
    return {'scope':'selected_blocks','page_id':d['page_id'],'complete':True,
        'reviewed_block_ids':[b['id'] for b in d['blocks']],'proposals':[], 'proposal_categories':[], 'observations':[]}


def proposal(target='p1:b1',text='Correct text.',**extra):
    return {'block_ids':[target],'region_bbox':None,'suggested_latex':text,'issue':'Transcription differs',
        'uncertain':False,'fragment_kind':'latex_fragment','change_kind':'ocr_repair','depends_on':[],**extra}


def critic_data():
    spans=[{'block_id':'p1:b1','text':r'Assume \(\alpha>0\). Then \(\int_0^T\frac{f(s)}{1+\beta^2}\,ds\le C\). See \cite{Ref}.',
            'format':'portable_latex','source_location':{'page':1,'source_hash':'abc','edition':'second'}}]
    return {'group_id':'g01','draft_sha256':tc.draft_hash(spans),'spans':spans,'context':{'missing':'none'},'bibliography':{'coverage':'not_in_extract'}}


def critic_valid(d):
    return {'group_id':d['group_id'],'draft_sha256':d['draft_sha256'],'coverage':'complete',
        'reviewed_block_ids':[s['block_id'] for s in d['spans']],'context_needed':[],'findings':[]}


class GrammarTests(unittest.TestCase):
    def test_nested_prose_math_accents_headings_unicode(self):
        for text in [r'\textbf{Theorem \textit{for \(x\ge0\)}}',r'\subsection*{It\^{o} and \emph{\(X\)}}',
                     r'\textsc{It\^o}, Itô’s formula.',r'\(\liminf_{n\to\infty}X_n\wedge Y\le Z\)',
                     r'\[\Bigl(\frac{1}{2}+\ldots\Bigr)\]',r'Price \$1 and \texttt{\textbackslash{}x}.']:
            self.assertEqual(accepted_fragment(text)[0],text)
        self.assertIn('fontenc',accepted_fragment('Itô')[1])
    def test_renderer_commands_round_trip(self):
        b=block(content=[{'type':'text','content':'A & B','styles':['bold','italic']}]);s,p=render_block(b)
        self.assertEqual(accepted_fragment(s)[0],s)
        b['kind']='paragraph_title';self.assertEqual(accepted_fragment(render_block(b)[0])[0],render_block(b)[0])
    def test_malformed_and_dangerous_commands_rejected(self):
        for text in [r'\input{/etc/passwd}',r'\textbf{\write18{touch x}}',r'\def\x{y}',r'\textit{A $x} and}$',
                     '\textit{A \t'+'extstyle x_1}',r'\textbf{x',r'\textit{x}}',r'\frac{a}{b}',r'\textbf x',r'$x$$',r'\[x\input{a}\]']:
            with self.subTest(text=text),self.assertRaises(ValueError):accepted_fragment(text)
    def test_no_wrapper_guess_and_math_body_provenance(self):
        with self.assertRaises(ValueError):typed_fragment(r'x^2')
        value=typed_fragment(r'x^2','math_body');self.assertEqual(value['original'],r'x^2');self.assertEqual(value['transformation'],'add_display_wrappers')
        check=r.compatible_fragment(proposal(text=r'x^2'),block(),True);self.assertNotEqual(check['status'],'wrapper_required')
        check=r.compatible_fragment(proposal(text=r'x^2'),block(kind='equation',content='x'),True);self.assertEqual(check['status'],'wrapper_required')
    def test_linebreak_hyphen_not_joined(self):
        text=r'The dif-\\ferential is given.';self.assertEqual(accepted_fragment(text)[0],text)
    def test_packages_and_template(self):
        _,packages=accepted_fragment(r'\[\mathbb{R}\text{ with }x\ge0\]')
        self.assertEqual(packages,{'amsmath','amssymb'})
        document=portable_document(['Itô'],{'inputenc','fontenc'})
        self.assertIn(r'\usepackage[utf8]{inputenc}',document);self.assertIn(r'\usepackage[T1]{fontenc}',document)
    def test_observed_full_saved_replacements_when_available(self):
        root=Path(__file__).resolve().parents[1]/'runs/qwen-native-trial-20261021T062027Z-a1f40a'
        if not root.exists():self.skipTest('Local book evidence is intentionally not in Git')
        for ordinal in (33,220):
            value=read_json(root/'requests'/f'{ordinal:03d}-A/outcome.json')['answer']
            for p in value['proposals']:
                with self.assertRaises(ValueError):accepted_fragment(p['suggested_latex'])
    def test_all_observed_deepseek_blockers_preserve_bytes(self):
        root=Path(__file__).resolve().parents[1]/'runs/deepseek-arm-a-trial-20261022T180153Z-0ee3cf'
        if not root.exists():self.skipTest('Book evidence remains outside Git')
        count=0;wrappers=0
        preview=Path(read_json(root/'binding.json')['preview'])
        for folder in sorted((root/'requests').iterdir()):
            o=read_json(folder/'outcome.json')
            if o['status']!='completed':continue
            b=read_json(preview/'regions'/folder.name/'input.json')['blocks'][0]
            for p,old in zip(o['answer']['proposals'],o['latex_checks']):
                if old['status']!='unsupported_export_blocked':continue
                check=r.compatible_fragment(p,b,True);self.assertIn(check['status'],('supported','wrapper_required'))
                self.assertEqual(check['original'],p['suggested_latex']);count+=1;wrappers+=check['status']=='wrapper_required'
        self.assertEqual((count,wrappers),(77,6))


class RecoveryTests(unittest.TestCase):
    def test_exact_schema_paths_and_fence(self):
        d=data();v=valid(d);del v['scope']
        with self.assertRaises(r.ValidationError) as cm:r.parse_validate(json.dumps(v),r.VISUAL_SCHEMA,lambda x:r.validate_visual(x,d))
        self.assertEqual(cm.exception.errors,[{'path':'$.scope','message':'required field missing'}])
        good=json.dumps(valid(d));self.assertEqual(r.single_outer_fence('```json\n'+good+'\n```'),good)
        for text in ['prefix '+good,good+' '+good,'```json\n[]\n```','```json\n{}\n```\nmore','```json\n{"x":1,"x":2}\n```']:
            self.assertIsNone(r.single_outer_fence(text))
    def test_recovery_keeps_bad_schema_bad(self):
        d=data();v=valid(d);v['reviewed_block_ids']=[]
        answer={'actual_model':CONFIG['model'],'finish_reason':'stop','content':'```json\n'+json.dumps(v)+'\n```'}
        with self.assertRaises(r.ValidationError):ex.validate_completion(answer,{'kind':'visual'},d,CONFIG['model'])
    def test_identity_and_coverage_not_format_success(self):
        d=data();v=valid(d);a={'actual_model':'wrong','finish_reason':'stop','content':json.dumps(v)}
        with self.assertRaises(IdentityError):ex.validate_completion(a,{'kind':'visual'},d,CONFIG['model'])
        a['actual_model']=CONFIG['model'];v['reviewed_block_ids'].append('p1:b100');a['content']=json.dumps(v)
        with self.assertRaises(r.ValidationError):ex.validate_completion(a,{'kind':'visual'},d,CONFIG['model'])
    def test_finish_reason_requires_usage_and_final_answer(self):
        ev={'http_status':200,'actual_model':'m','finish_reason':'length','content':'','usage':{'completion_tokens':16384,'completion_tokens_details':{'reasoning_tokens':16384}}}
        f=r.diagnose(ValueError('length'),ev,'m');self.assertEqual(f['kind'],'reasoning_exhausted')
        self.assertEqual(r.recovery_method(f,{'lower_reasoning_supported':True}),'lower_reasoning')
        ev['content']='{"proposals":[';self.assertEqual(r.diagnose(ValueError('length'),ev,'m')['kind'],'output_truncated')
        ev['content']='';ev['usage']={'completion_tokens':16384};self.assertEqual(r.diagnose(ValueError('length'),ev,'m')['kind'],'budget_exhausted_unknown')
        self.assertIsNone(r.recovery_method({'kind':'output_truncated'},{}))
    def test_json_feedback_exact_and_no_lower_effort(self):
        body={'model':'m','messages':[{'role':'user','content':'original full context'}],'reasoning_effort':'medium'}
        f={'kind':'schema','errors':[{'path':'$.scope','message':'required field missing'}],'content':'{"proposals":[] }'}
        new=r.feedback_request(body,f,r.VISUAL_SCHEMA,'json_feedback')
        self.assertEqual(new['reasoning_effort'],'medium');self.assertEqual(new['messages'][0],body['messages'][0]);self.assertIn('$.scope',new['messages'][-1]['content']);self.assertIn('DATA INSTANCE',new['messages'][-1]['content'])
        self.assertEqual(len(body['messages']),1)
    def test_shared_two_calls_including_child_and_resume(self):
        state={};limits={'baseline_calls':2,'recovery_calls':80,'per_parent_recovery':2}
        r.reserve_budget(state,'original','baseline',limits);r.reserve_budget(state,'original','json_feedback',limits)
        state=json.loads(json.dumps(state));r.reserve_budget(state,'original','compiler_feedback',limits)
        with self.assertRaises(ValueError):r.reserve_budget(state,'original','lower_reasoning',limits)
        with self.assertRaises(IntegrityError):r.reserve_budget(state,'original','baseline',limits)
    def test_fragment_kind_cannot_wrap_paragraph(self):
        d=data();v=valid(d);v['proposals']=[proposal(text='x',fragment_kind='math_body')];v['proposal_categories']=['content']
        with self.assertRaises(r.ValidationError):r.validate_visual(v,d)
    def test_json_repair_cannot_drop_or_change_existing_proposals(self):
        old={'proposals':[proposal()]};good=copy.deepcopy(old)
        self.assertIn('preserved',r.preserve_substance(json.dumps(old),good,'json_feedback'))
        with self.assertRaises(r.ValidationError):r.preserve_substance(json.dumps(old),{'proposals':[]},'json_feedback')
        good['proposals'][0]['suggested_latex']='Changed substantive text'
        with self.assertRaises(r.ValidationError):r.preserve_substance(json.dumps(old),good,'json_feedback')
        self.assertIn('unparseable',r.preserve_substance('schema {} result {}',good,'json_feedback'))


def assessed_edits_for(blocks,items):
    # Synthetic explicit assessments, not automatic production authorization.
    decisions={p['id']:{'evidence_sha256':fingerprint(p),'disposition':'suitable',
        'whole_block_preserved':True,'reason':'Synthetic source comparison'} for p in items}
    return edits_for(blocks,items,decisions)


class CandidateTests(unittest.TestCase):
    def test_duplicates_conflicts_and_atomic_dependencies(self):
        blocks=[block(1),block(2)]
        def item(i,p):return {'id':str(i),'proposal':p}
        one=item(1,proposal());two=item(2,proposal())
        edits,records=assessed_edits_for(blocks,[one,two]);self.assertEqual(len(edits),1);self.assertEqual(records[1]['status'],'duplicate')
        two=item(2,proposal(text='Different'))
        edits,records=assessed_edits_for(blocks,[one,two]);self.assertFalse(edits);self.assertEqual({x['status'] for x in records},{'conflicted'})
        one=item(1,proposal(depends_on=['p1:b2']));edits,_=assessed_edits_for(blocks,[one]);self.assertFalse(edits)
        edits,_=assessed_edits_for(blocks,[one,item(2,proposal('p1:b2'))]);self.assertEqual(set(edits),{'p1:b1','p1:b2'})
    def test_unsafe_alternative_does_not_let_other_edit_win(self):
        items=[{'id':'1','proposal':proposal()},{'id':'2','proposal':proposal(text=r'\input{x}')}]
        edits,records=assessed_edits_for([block()],items);self.assertFalse(edits)
    def test_uncertainty_and_deletion_not_auto_final_acceptance(self):
        for p in [proposal(uncertain=True),proposal(text='',fragment_kind='delete')]:
            edits,records=assessed_edits_for([block()],[{'id':'1','proposal':p}]);self.assertFalse(edits);self.assertEqual(records[0]['acceptance'],'UNACCEPTED')
    def test_editorial_source_typo_is_eligible_evaluation_only(self):
        edits,records=assessed_edits_for([block(kind='equation',content='e^{x)}')],[{'id':'1','proposal':proposal(text=r'\[e^{x}\]',change_kind='editorial_repair')}])
        self.assertEqual(records[0]['status'],'applied_experimental');self.assertEqual(records[0]['acceptance'],'UNACCEPTED')
    def test_dependent_component_cannot_apply_part_when_first_is_deferred(self):
        items=[{'id':'1','proposal':proposal(uncertain=True,depends_on=['p1:b2'])},
               {'id':'2','proposal':proposal('p1:b2')}]
        edits,_=assessed_edits_for([block(1),block(2)],items);self.assertFalse(edits)
    def test_material_math_cannot_hide_as_editorial(self):
        from probe.evaluation_export import queue_class
        self.assertEqual(queue_class(proposal(text=r'\[x+1\]',change_kind='editorial_repair'),r'\[x-1\]'),'material_or_uncertain')
        self.assertEqual(queue_class(proposal(text=r'\[e^{x}\]',change_kind='editorial_repair'),r'\[e^{x)}\]'),'editorial_or_cosmetic')


class CriticBibliographyTests(unittest.TestCase):
    def test_exact_math_citations_and_text_only_payload(self):
        d=critic_data();p=tc.request(d);content=p['messages'][1]['content']
        supplied=json.loads(content.split('<passage>\n',1)[1].split('\n</passage>',1)[0]);self.assertEqual(supplied,d)
        self.assertTrue(all(isinstance(m['content'],str) for m in p['messages']));self.assertNotIn('image_url',json.dumps(p));self.assertNotIn('strip_latex',json.dumps(p))
    def test_distinct_coverage_states_and_empty_findings(self):
        d=critic_data();v=critic_valid(d);tc.validate(v,d)
        for status in ('incomplete','insufficient_context'):
            v['coverage']=status;v['reviewed_block_ids']=[];v['context_needed']=['Earlier hypothesis needed'];tc.validate(v,d)
        v['coverage']='complete'
        with self.assertRaises(r.ValidationError):tc.validate(v,d)
    def test_quotes_hash_ids_and_no_rewriting(self):
        d=critic_data();v=critic_valid(d);f={'id':'g01:f1','category':'domain_or_assumption','quotes':[{'block_id':'p1:b1','text':r'\alpha>0','occurrence':0}],
            'consequence':'A stated condition needs checking','severity':'medium','uncertain':True,'context_required':[], 'next_action':'source_image_review'}
        v['findings']=[f];self.assertEqual(tc.located_findings(v,d)[0]['quotes'][0]['start'],9)
        for key,value in [('text','invented'),('block_id','p2:b1'),('occurrence',2)]:
            bad=copy.deepcopy(v);bad['findings'][0]['quotes'][0][key]=value
            with self.assertRaises(r.ValidationError):tc.validate(bad,d)
        for key,value in [('group_id','wrong'),('draft_sha256','wrong')]:
            with self.assertRaises(r.ValidationError):tc.validate({**v,key:value},d)
    def test_no_silent_long_context_clipping(self):
        d=critic_data();d['spans'][0]['text']='A'*48001;d['draft_sha256']=tc.draft_hash(d['spans'])
        with self.assertRaises(ValueError):tc.request(d)
    def test_bibliography_unmatched_is_not_fake_and_statuses_separate(self):
        spans=[{'block_id':'b','text':r'See \cite{Smith} and Jones (1990). \eqref{missing}'}]
        inv=inventory(spans,{'edition':'second'},'not_in_extract')
        self.assertEqual(inv['occurrences'][0]['status'],'unresolved');self.assertEqual(inv['occurrences'][1]['status'],'ambiguous')
        self.assertEqual(inv['occurrences'][0]['source_actually_consulted'],'not_consulted');self.assertEqual(inv['cross_references'][0]['status'],'unknown_outside_window')
    def test_bibitem_raw_and_ambiguous_duplicate_entries(self):
        spans=[{'block_id':'b','text':r'\cite{A}\bibitem{A} First.\bibitem{A} Second.'}]
        inv=inventory(spans,{},'present_partial');self.assertEqual(inv['occurrences'][0]['status'],'ambiguous');self.assertEqual(len(inv['entries']),2)
        self.assertEqual(inv['entries'][0]['parsed_fields'],{});self.assertEqual(candidate_bib(inv['entries']),('',[]))
    def test_candidate_bib_only_explicit_fields_and_provenance(self):
        e={'id':'e','raw':'Title, 1990','raw_sha256':fingerprint('Title, 1990'),
           'parsed_fields':{'title':'Title','year':'1990'},'field_provenance':{'title':{'start':0,'end':5},'year':{'start':7,'end':11}}}
        text,prov=candidate_bib([e]);self.assertIn('year = {1990}',text);self.assertEqual(prov[0]['claim_supported'],'not_assessed')
        e['parsed_fields']['doi']='invented'
        with self.assertRaises(ValueError):candidate_bib([e])


class CompilerTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('PDF2TEX_COMPILER_IMAGE'),'No explicit isolated compiler image; real compilation untested')
    def test_real_isolated_compiler_when_operator_enabled(self):
        with tempfile.TemporaryDirectory() as td:
            result=tex.compare(r'Before: \(x\).',r'\textbf{After: \(x\).}',Path(td)/'pair',{'amsmath'},image=os.environ['PDF2TEX_COMPILER_IMAGE'])
            self.assertEqual(result['status'],'both_compiled')
    @unittest.skipUnless(os.environ.get('PDF2TEX_COMPILER_IMAGE'),'No explicit isolated compiler image; relative include compilation untested')
    def test_real_relative_include_when_operator_enabled(self):
        # Exercise the actual adapter command with an explicitly staged include;
        # compile_document deliberately does not follow arbitrary caller files.
        with tempfile.TemporaryDirectory() as td:
            work=Path(td);source=work/'source';build=work/'build'
            (source/'sections').mkdir(parents=True);build.mkdir()
            (source/'document.tex').write_text(portable_document([r'\input{sections/example.tex}'],{'amsmath'}))
            (source/'sections/example.tex').write_text(r'Relative input: \(\frac{1}{2}\).\typeout{RELATIVE-INCLUDE-READ}')
            before=files_manifest(source)
            cmd=tex.command(os.environ['PDF2TEX_COMPILER_IMAGE'],work)
            result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90,check=False,
                env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'HOME':td})
            log=result.stdout.decode('utf-8','replace')
            self.assertEqual(result.returncode,0,log)
            self.assertIn('RELATIVE-INCLUDE-READ',log)
            self.assertTrue((build/'document.pdf').is_file(),log)
            self.assertGreater((build/'document.pdf').stat().st_size,0)
            self.assertTrue((build/'document.log').is_file(),log)
            self.assertTrue((build/'document.aux').is_file(),log)
            self.assertEqual(files_manifest(source),before)
    def test_isolation_command_and_immutable_image_required(self):
        with self.assertRaises(ValueError):tex.command('some:tag','/tmp/build')
        cmd=tex.command('sha256:'+'a'*64,'/tmp/build')
        for option in ('--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges',
                       '--pids-limit=64','--memory=512m','--memory-swap=512m','--cpus=1','-no-shell-escape',
                       'openin_any=p','openout_any=p','TEXMFOUTPUT=/work','-output-directory=/work'):self.assertIn(option,cmd)
        self.assertEqual(cmd[cmd.index('--workdir')+1],'/source')
        self.assertEqual(cmd[cmd.index('--user')+1],f'{os.getuid()}:{os.getgid()}')
        self.assertEqual(cmd[-1],'document.tex');self.assertNotIn('/source/document.tex',cmd)
        self.assertIn('type=bind,src=/tmp/build/source,dst=/source,readonly',cmd)
        self.assertIn('type=bind,src=/tmp/build/build,dst=/work',cmd)
        self.assertNotIn('/var/run/docker.sock',' '.join(cmd));self.assertNotIn(str(Path.home()),' '.join(cmd))
    def test_unavailable_is_never_compiled(self):
        with tempfile.TemporaryDirectory() as td,patch('subprocess.run',side_effect=AssertionError('No compiler')):
            result=tex.compile_document('text',Path(td)/'build');self.assertEqual(result['status'],'unavailable');self.assertFalse(result['compilation_claim'])
    def test_compiler_error_routing_with_equivalent_template(self):
        calls=[]
        def runner(cmd,**kwargs):
            path=Path(next(x.split('src=',1)[1].split(',dst=')[0] for x in cmd if x.startswith('type=bind,')))
            calls.append((path/'document.tex').read_text())
            return subprocess.CompletedProcess(cmd,0 if len(calls)==1 else 1,b'OK' if len(calls)==1 else b'Missing $ inserted')
        with tempfile.TemporaryDirectory() as td,patch('probe.tex_compile.shutil.which',return_value='/usr/bin/docker'):
            with patch('probe.tex_compile.compile_document',side_effect=[{'status':'passed'},{'status':'syntax_failure'}]):
                result=tex.compare('before','after',Path(td)/'pair',{'amsmath'},image='sha256:'+'a'*64)
            self.assertTrue(result['compiler_feedback_eligible'])
        self.assertEqual(tex.classify_log('Undefined control sequence',1),'missing_context_or_macro')
        self.assertEqual(tex.classify_log('LaTeX Error: File x.sty not found',1),'missing_package_or_asset')
        self.assertEqual(tex.classify_log('There were undefined references',0),'passed_with_unresolved_references')
    def test_policy_denial_takes_precedence_over_emergency_stop(self):
        denial='pdflatex: Not reading from /source/document.tex (openin_any = p).'
        emergency="! I can't find file `/source/document.tex'.\n! Emergency stop."
        for log in (denial+'\n'+emergency,emergency+'\n'+denial,
                    'pdflatex: Not writing to /denied/file (openout_any=p).\n! Emergency stop.'):
            with self.subTest(log=log):
                self.assertEqual(tex.classify_log(log,1),'adapter_configuration_failure')
        self.assertEqual(tex.classify_log('! Missing $ inserted.\n! Emergency stop.',1),'syntax_failure')
    def test_policy_denial_is_never_model_repair_eligible(self):
        from probe.evaluation_export import compiler_checks
        for statuses in [('passed','adapter_configuration_failure'),('adapter_configuration_failure','syntax_failure'),
                         ('adapter_configuration_failure','adapter_configuration_failure')]:
            with self.subTest(statuses=statuses),tempfile.TemporaryDirectory() as td:
                with patch('probe.tex_compile.compile_document',side_effect=[{'status':s} for s in statuses]):
                    result=tex.compare('before','after',Path(td)/'pair',image='sha256:'+'a'*64)
                self.assertEqual(result['status'],'adapter_configuration_failure')
                self.assertFalse(result['compiler_feedback_eligible'])
                with self.assertRaises(ValueError):tex.feedback(result,'before','after',Path(td)/'pair')
                outcome={'answer':{'proposals':[proposal()]},'export_checks':[{'latex':'Correct text.','packages':[]}]}
                with patch('probe.tex_compile.compare',return_value=result):
                    self.assertIsNone(compiler_checks(outcome,data(),Path(td)/'checks','sha256:'+'a'*64))
                self.assertEqual(outcome['compilation'],[result])
    def test_texput_log_preserved_and_used_for_failure_classification(self):
        denial=b'pdflatex: Not reading from /source/document.tex (openin_any = p).\n! Emergency stop.\n'
        def runner(cmd,**kwargs):
            mount=next(s for s in cmd if s.startswith('type=bind,') and s.endswith('dst=/work'))
            build=Path(mount.split('src=')[1].split(',dst=')[0]);(build/'texput.log').write_bytes(denial)
            return subprocess.CompletedProcess(cmd,returncode,b'! Emergency stop.\nTranscript written on texput.log.\n')
        for returncode in (1,0):
            with self.subTest(returncode=returncode),tempfile.TemporaryDirectory() as td,patch('probe.tex_compile.shutil.which',return_value='/usr/bin/docker'):
                out=Path(td)/'build';result=tex.compile_document('exact document',out,image='sha256:'+'a'*64,runner=runner)
                self.assertEqual(result['status'],'adapter_configuration_failure');self.assertFalse(result['compilation_claim'])
                self.assertEqual((out/'texput.log').read_bytes(),denial)
                saved=next(e for e in result['outputs'] if e['path']=='texput.log')
                self.assertEqual(saved['sha256'],sha(out/'texput.log'))
                self.assertIn('Transcript written on texput.log.',(out/'console.log').read_text())
    def test_adapter_executes_only_isolated_inputs_and_records_output(self):
        def runner(cmd,**kwargs):
            self.assertEqual(kwargs['timeout'],90);self.assertNotIn('shell',kwargs)
            self.assertEqual(cmd[cmd.index('--workdir')+1],'/source');self.assertEqual(cmd[-1],'document.tex')
            self.assertIn('TEXMFOUTPUT=/work',cmd);self.assertIn('-output-directory=/work',cmd)
            mounts=[s for s in cmd if s.startswith('type=bind,')];self.assertEqual(len(mounts),2)
            self.assertTrue(mounts[0].endswith('readonly'))
            source=Path(mounts[0].split('src=')[1].split(',dst=')[0]);self.assertEqual((source/'document.tex').read_text(),'exact document')
            build=Path(mounts[1].split('src=')[1].split(',dst=')[0]);(build/'document.pdf').write_bytes(b'fake compiler PDF')
            return subprocess.CompletedProcess(cmd,0,b'This is pdfTeX synthetic\nNo errors')
        with tempfile.TemporaryDirectory() as td,patch('probe.tex_compile.shutil.which',return_value='/usr/bin/docker'):
            result=tex.compile_document('exact document',Path(td)/'build',image='sha256:'+'a'*64,runner=runner)
            self.assertEqual(result['status'],'passed');self.assertEqual(result['compiler_banner'],'This is pdfTeX synthetic')
            self.assertTrue((Path(td)/'build/document.pdf').exists())


class FakeClient(LocalClient):
    actions=[];sent=[];counter=0;tick=None
    def _request(self,method,endpoint,payload,output_dir,label):
        folder=Path(output_dir)/'attempts'/str(FakeClient.counter);FakeClient.counter+=1;folder.mkdir(parents=True)
        atomic_json(folder/'request.json',{'body':payload});atomic_json(folder/'record.json',{'http_status':200,'latency_seconds':1})
        evidence={'attempt_dir':str(folder),'http_status':200,'latency_seconds':1}
        if method=='GET':return {'data':[{'id':self.requested_model}]},evidence
        FakeClient.sent.append(payload)
        if FakeClient.tick:FakeClient.tick()
        action=FakeClient.actions.pop(0) if FakeClient.actions else 'ok'
        if action=='crash':
            atomic_json(folder/'record.json',{'http_status':None,'latency_seconds':1})
            raise KeyboardInterrupt()
        if action in ('timeout','transport','wrong400','option'):
            status=400 if action in ('wrong400','option') else None
            atomic_json(folder/'record.json',{'http_status':status,'latency_seconds':1})
            if action=='wrong400':atomic_json(folder/'response.raw',{'model':'wrong','error':'bad option'})
            raise ProbeError('timed out' if action=='timeout' else 'connection failed',attempt_dir=folder,status=status)
        d=json.loads(payload['messages'][0]['content']);v=valid(d)
        if action=='schema':del v['scope']
        if action=='coverage':v['reviewed_block_ids']=[]
        content=json.dumps(v)
        if action=='fence':content='```json\n'+content+'\n```'
        if action=='length':content=''
        if action=='tex':v['proposals']=[proposal(d['blocks'][0]['id'])];v['proposal_categories']=['content'];content=json.dumps(v)
        obj={'model':'wrong' if action=='identity' else self.requested_model,
             'choices':[{'finish_reason':'length' if action=='length' else 'stop','message':{'content':content}}],
             'usage':{'completion_tokens':16384 if action=='length' else 100,'completion_tokens_details':{'reasoning_tokens':16384 if action=='length' else 50}}}
        atomic_json(folder/'response.raw',obj);return obj,evidence


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);self.preview=self.root/'preview';self.preview.mkdir();self.out=self.root/'run'
        self.source=self.root/'source';self.source.write_text('immutable')
        units=[]
        for n in range(1,4):
            d=data(n);body={'model':CONFIG['model'],'messages':[{'role':'user','content':json.dumps(d)}], 'max_tokens':16384,'stream':False,'reasoning_effort':'medium'}
            units.append(save_unit(self.preview,str(n),d,body,kind='visual',gate=n<=2))
        finish_preview(self.preview,units,'visual',CONFIG,{str(self.source):sha(self.source)},
            {'baseline_calls':3,'recovery_calls':4,'per_parent_recovery':2,'admission_seconds':21600},
            {'minimum_first':0,'minimum_final':2,'minimum_coverage':2},{})
        ex.initialize(self.preview,self.out);self.ready=self.root/'ready';self.ready.mkdir();atomic_json(self.ready/'readiness.json',{'config':CONFIG,'text':'passed','vision':'qualified','finished_at':ex.now()});ex.seal(self.ready)
        FakeClient.actions=[];FakeClient.sent=[];FakeClient.counter=0;FakeClient.tick=None
        idle=patch('probe.experiment.converter_idle',return_value={'owned_converter_pids':[]});idle.start();self.addCleanup(idle.stop)
    def run_stage(self,stage='gate',**kw):return ex.execute(self.root,self.out,stage=stage,readiness=self.ready,client_factory=FakeClient,**kw)
    def state(self):return read_json(self.out/'state.json')
    def test_gate_then_continue_no_repeat_and_serialization(self):
        self.run_stage();self.assertEqual(len(FakeClient.sent),2);self.assertTrue(self.state()['gate']['passed'])
        self.run_stage('continue',resume=True);self.assertEqual(len(FakeClient.sent),3);self.assertEqual(self.state()['status'],'completed');self.assertEqual(self.source.read_text(),'immutable')
        for c in self.state()['calls']:
            folder=self.out/'calls'/c['id'];self.assertEqual(read_json(folder/'request.json'),read_json(next(folder.glob('attempts/*/request.json')))['body'])
    def test_schema_feedback_then_valid_and_fence_no_model_retry(self):
        FakeClient.actions=['schema','ok','fence'];self.run_stage();s=self.state();self.assertEqual(len(FakeClient.sent),3)
        self.assertEqual([c['method'] for c in s['calls']],['baseline','json_feedback','baseline']);self.assertIn('$.scope',FakeClient.sent[1]['messages'][-1]['content'])
        self.assertTrue(read_json(self.out/'calls/0003/outcome.json')['mechanical_recovery'])
    def test_two_recovery_cap_across_resume(self):
        FakeClient.actions=['schema','coverage','schema','ok'];self.run_stage();self.assertEqual(len(FakeClient.sent),4);self.assertEqual(self.state()['status'],'gate_failed')
        self.run_stage(resume=True);self.assertEqual(len(FakeClient.sent),4)
    def test_identical_failed_response_not_blindly_retried(self):
        FakeClient.actions=['schema','schema','ok'];self.run_stage();self.assertEqual(len(FakeClient.sent),3)
        self.assertIn('retry_deferred',self.state()['units']['1'])
    def test_reasoning_retry_only_supported_with_no_final_tokens(self):
        FakeClient.actions=['length','ok','ok'];self.run_stage();self.assertEqual(FakeClient.sent[1]['reasoning_effort'],'low');self.assertEqual(FakeClient.sent[0]['messages'],FakeClient.sent[1]['messages'])
    def test_wrong_model_in_error_and_success_stops(self):
        for action in ('wrong400','identity'):
            if self.state()['calls']:break
            FakeClient.actions=[action];self.run_stage();self.assertEqual(self.state()['status'],'stopped_identity');self.assertEqual(len(FakeClient.sent),1)
    def test_two_transport_failures_pause(self):
        FakeClient.actions=['transport','timeout'];self.run_stage();self.assertEqual(self.state()['status'],'paused_connection');self.assertEqual(len(FakeClient.sent),2)
    def test_changed_sources_resume_refused_before_client(self):
        self.source.write_text('changed')
        with self.assertRaises(IntegrityError):self.run_stage()
        self.assertFalse(FakeClient.sent)
    def test_changed_attempt_refused(self):
        self.run_stage();(self.out/'calls/0001/outcome.json').write_text('{}')
        with self.assertRaises(IntegrityError):self.run_stage('continue',resume=True)
        self.assertEqual(len(FakeClient.sent),2)
    def test_crash_reservation_consumed(self):
        FakeClient.actions=['crash'];self.run_stage();self.assertEqual(self.state()['calls'][0]['status'],'in_flight_unknown')
        self.run_stage(resume=True);self.assertEqual(len(FakeClient.sent),2);self.assertEqual(self.state()['units']['1']['status'],'interrupted')
    def test_budget_including_resume_time(self):
        state=self.state();state.update(elapsed_seconds=21599);atomic_json(self.out/'state.json',state);tick=[0];FakeClient.tick=lambda:tick.__setitem__(0,tick[0]+600)
        self.run_stage(clock=lambda:tick[0]);self.assertEqual(len(FakeClient.sent),1);self.assertEqual(self.state()['status'],'budget_exhausted')
    def test_pause_file_stops_without_review_call(self):
        (self.out/'PAUSE').touch();self.run_stage();self.assertFalse(FakeClient.sent);self.assertEqual(self.state()['status'],'paused_operator')
    def test_candidate_preserves_unaffected_content_and_original_evidence(self):
        self.run_stage();self.run_stage('continue',resume=True);before=files_manifest(self.out)
        cand=self.root/'candidate';build_candidate(self.preview,self.out,cand)
        self.assertEqual(files_manifest(self.out),before);self.assertFalse(read_json(cand/'provenance.json')['final_acceptance'])
        self.assertEqual([r['block_id'] for r in read_json(cand/'inventory.json')],['p1:b1','p1:b2','p1:b3'])
        self.assertTrue(all(r['before']['text']==r['after'] for r in read_json(cand/'inventory.json')))
        self.assertEqual(read_json(cand/'build/result.json')['status'],'unavailable')
    def test_critic_recipe_binds_actual_candidate_without_rationales_or_images(self):
        FakeClient.actions=['tex','ok'];self.run_stage();self.run_stage('continue',resume=True)
        from probe.evaluation_export import disposition_template
        review=disposition_template(self.out)
        for decision in review['decisions']:
            decision.update(disposition='suitable',whole_block_preserved=True,reason='Synthetic assessment')
        path=self.root/'dispositions.json';atomic_json(path,review)
        cand=self.root/'candidate';build_candidate(self.preview,self.out,cand,dispositions=path)
        original=read_json(cand/'inventory.json')[0];d=critic_data()
        d['spans']=[{'block_id':'p1:b1','text':original['before']['text'],'format':'portable_latex',
            'source_location':{**original['source_location'],'source_block_sha256':original['source_block_sha256']}}]
        d['draft_sha256']=tc.draft_hash(d['spans']);recipe=self.root/'recipe';recipe.mkdir()
        atomic_json(recipe/'input.json',d)
        atomic_json(recipe/'recipe.json',{'code_sha256':ex.code_hashes(),'system_prompt_sha256':fingerprint(tc.SYSTEM),
            'source_hashes':{str(self.source):sha(self.source)},'groups':[{'id':'g01','split':'development',
                'original_physical_page':1,'block_ids':['p1:b1'],'baseline_input':'input.json','gate':True}],
            'limits':{'baseline_calls':2,'recovery_calls':2,'per_parent_recovery':2,'admission_seconds':14400},
            'gate':{'minimum_first':1,'minimum_final':2,'minimum_coverage':1}})
        ex.seal(recipe);prepared=self.root/'critic';prepare_critic(recipe,cand,prepared)
        units=read_json(prepared/'units.json');self.assertEqual(len(units),2)
        texts=[]
        for u in units:
            payload=read_json(prepared/u['request']);self.assertTrue(all(isinstance(m['content'],str) for m in payload['messages']))
            self.assertNotIn('Transcription differs',json.dumps(payload));texts.append(read_json(prepared/u['data'])['spans'][0]['text'])
        self.assertIn('Correct text.',texts);self.assertIn(original['before']['text'],texts)
    def test_diagnostic_unsupported_does_not_fallback_or_block_feedback(self):
        # Reuse synthetic units under the legacy contract. The one actual-schema
        # gate is unsupported; the separate feedback baseline still executes.
        units=read_json(self.preview/'units.json')
        units=units[:2]
        for i,u in enumerate(units):
            u.update(kind='diagnostic',condition='constrained' if i==0 else 'feedback',gate=i==0)
            body=read_json(self.preview/u['request'])
            if i==0:body['response_format']={'type':'json_schema','json_schema':{'name':'actual','strict':True,'schema':r.LEGACY_SCHEMA}}
            atomic_json(self.preview/u['request'],body)
        (self.preview/'manifest.json').unlink()
        finish_preview(self.preview,units,'diagnostic',CONFIG,{str(self.source):sha(self.source)},
            {'baseline_calls':2,'recovery_calls':0,'per_parent_recovery':2,'admission_seconds':7200},
            {'minimum_first':1,'minimum_final':1,'minimum_coverage':1},{})
        self.out=self.root/'diagnostic';ex.initialize(self.preview,self.out)
        FakeClient.actions=['option','ok'];self.run_stage('continue')
        self.assertEqual(self.state()['schema_support'],'unsupported');self.assertEqual(len(FakeClient.sent),2)
        self.assertIn('response_format',FakeClient.sent[0]);self.assertNotIn('response_format',FakeClient.sent[1])

if __name__=='__main__':unittest.main()
