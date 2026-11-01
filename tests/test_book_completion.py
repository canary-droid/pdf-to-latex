"""Finite completion scope, reconciliation and saved technical repairs; offline."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from probe import book_completion as core, chapter_concurrency as concurrent, chapter_glm as runtime
from probe.common import atomic_json, read_json, files_manifest, sha, fingerprint
from scripts import book_completion as ctrl
from test_speed_suite import BODY, DOC, health


def block(number, text, kind='text', *, page=1, assets=None):
    return {'id': f'bergomi-p{page:04d}:b{number}', 'kind': kind, 'tex': text, 'assets': assets or [],
            'native': {'type': kind}, 'page': {'original_physical_page': page}}


def native(blocks):
    return {'key': 'bergomi-05', 'title': 'Example', 'blocks': blocks, 'pages': []}


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.native = native([block(1, r'\section{5.9 Weighted swaps}', 'paragraph_title'),
                              block(2, r'Body $x^2$.'),
                              block(3, r'\section{Appendix A -- timer options}', 'paragraph_title'),
                              block(4, r'Appendix body $\int_0^T X_t\,dt$.')])
        self.ids = [b['id'] for b in self.native['blocks']]

    def test_complete_target_scope_for_both_requests_not_first_title(self):
        section = core.target(self.native, self.ids, title='5.9 Weighted swaps')
        for phase, draft in [('convert', None), ('critic', DOC)]:
            body = core.request(self.native, section, 'Boundary page context', phase=phase, draft=draft)
            text = body['messages'][0]['content']
            self.assertIn('Appendix A -- timer options', text)
            self.assertIn('Every block of PRIMARY EXTRACTION below is output', text)
            self.assertIn(self.native['blocks'][-1]['tex'], text)
            self.assertEqual(body['reasoning_effort'], core.EFFORTS[phase])
            self.assertEqual(body['max_tokens'], 131072)
            self.assertTrue(body['stream'])
        changed = copy.deepcopy(section); changed['headings'] = changed['headings'][:1]
        with self.assertRaisesRegex(ValueError, 'scope'):core.validate_target(self.native, changed)
        changed = copy.deepcopy(section); changed['title'] = 'Only section 5.9; exclude appendix'
        with self.assertRaisesRegex(ValueError, 'scope'):core.validate_target(self.native, changed)

    def test_missing_appendix_body_and_chart_not_satisfied_by_critic_claim(self):
        n = copy.deepcopy(self.native)
        n['blocks'].append(block(5, 'Figure 5.1', 'chart', assets=['assets/chart.jpg']))
        n['blocks'].append(block(6, r'\tag{5.1}x=2', 'equation', assets=['assets/formula.jpg']))
        ids = [b['id'] for b in n['blocks']]
        text = r'''\documentclass{article}\begin{document}
\section{5.9 Weighted swaps}Body.
\section{Appendix A -- timer options}
\section{Editorial notes}Verified all appendices and all charts.
\includegraphics{assets/chart.jpg}
\end{document}'''
        check = core.coverage_check(text, n, ids)
        self.assertTrue(check['empty_appendix_body_candidates'])
        self.assertEqual(check['missing_required_charts'][0]['assets'], ['assets/chart.jpg'])
        self.assertNotIn('assets/formula.jpg', str(check['missing_required_charts']))
        self.assertEqual(check['semantic_completeness'], 'not established')

    def test_automatic_math_is_not_tag_count_failure(self):
        n = native([block(1, r'\tag{1.1}x=1', 'equation')])
        result = core.coverage_check(r'\begin{equation}x=1\end{equation}', n, [n['blocks'][0]['id']])
        self.assertFalse(result['missing_explicit_equation_numbers'])
        self.assertIn('automatic', result['equation_sequence_status'])
        self.assertEqual(result['source_numbered_equations'], ['1.1'])

    def test_chart_argument_after_comment_and_detokenize(self):
        text = '\\includegraphics[width=\\linewidth]%\n{assets/a.jpg}\n' + r'\includegraphics{\detokenize{assets/b.jpg}}'
        self.assertEqual(core.image_references(text), ['assets/a.jpg', 'assets/b.jpg'])

    def test_generated_annotation_escapes_observed_failure_tokens(self):
        entry={'id':'fixture', 'status':'unresolved', 'category':'material',
               'text':r'Original \textcompss, {braces}, 100%, $x_1$ and ❧; preserve this quoted reading.'}
        result=ctrl.edit.annotate(DOC,[entry])
        self.assertIn(r'\textbackslash{}textcompss',result)
        self.assertNotIn(r'Original \textcompss',result)
        self.assertIn(r'100\%',result);self.assertNotIn('❧',result)
        self.assertEqual(ctrl.edit.annotate(result,[entry]),result)

    def test_appendix_boundaries_and_digest_are_distinct_blocks(self):
        n = native([block(1, r'\section{Appendix A -- timers}', 'paragraph_title', page=197),
                    block(2, 'A body', page=205), block(3, r'\section{Appendix B -- density}', 'paragraph_title', page=205),
                    block(4, 'B body', page=211), block(5, r'\section{Chapter digest}', 'paragraph_title', page=212),
                    block(6, r'\section{Appendix A -- timers}', 'paragraph_title', page=215), block(7, 'Recap', page=215)])
        spans = core.appendix_spans(n)
        self.assertEqual([s['recap'] for s in spans], [False, False, True])
        self.assertEqual(spans[0]['last'], 'bergomi-p0205:b2')
        self.assertEqual(spans[1]['first'], 'bergomi-p0205:b3')
        self.assertNotIn('bergomi-p0212:b5', spans[1]['blocks'])

    def test_grouped_output_once_partial_adoption_and_safe_capacity_split(self):
        ledger = [{'unit': 'group', 'blocks': self.ids[:2]}, {'unit': 'appendix', 'blocks': self.ids[2:]}]
        self.assertEqual(len(core.unique_coverage(ledger)), 4)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):core.unique_coverage(ledger + [ledger[0]])
        with self.assertRaisesRegex(ValueError, 'Overlapping'):core.unique_coverage([ledger[0], {'unit': 'other', 'blocks': self.ids[:1]}])
        sections = core.split_meaningfully(self.native, self.ids, fits=lambda s: len(s['blocks']) <= 2)
        self.assertEqual([b for s in sections for b in s['blocks']], self.ids)
        with self.assertRaises(core.chapter_protocol.ContextBudgetGap):
            core.split_meaningfully(native([block(1, 'Indivisible proof')]), ['bergomi-p0001:b1'], fits=lambda s: False)


class SavedRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parents = {}
        for name, filename in ctrl.PARENTS.items():
            pointer = ctrl.ROOT / 'results' / filename
            if not pointer.exists():raise unittest.SkipTest('Local saved book evidence unavailable')
            cls.parents[name] = Path(read_json(pointer)['run'])
        cls.states = {name: read_json(path / 'state.json') for name, path in cls.parents.items()}

    def test_actual_saved_repairs_exact_diff_no_original_mutation(self):
        for row in ctrl.choose_candidates(self.parents, self.states):
            if row['key'] not in ctrl.REPAIR_KEYS:continue
            path = Path(row['parent']) / row['record']['path']; before_hash = sha(path); text = path.read_text()
            with self.subTest(unit=row['key']):
                repaired, changes = core.repair_known(row['key'], text)
                self.assertTrue(changes)
                expected = text
                for change in changes:expected = core.replace_exact(expected, change['old'], change['new'])
                self.assertEqual(repaired, expected); self.assertEqual(sha(path), before_hash)
                with self.assertRaises(ValueError):core.repair_known(row['key'], repaired)
                if row['key'].endswith('s01') or row['key'].endswith('s08'):
                    self.assertNotIn(r'\textcolor{blue', repaired)
                if row['key'] == 'd-large-09-bergomi-09':
                    self.assertNotIn(r'\end{align*}\tag', repaired)

    def test_figure_109_restored_from_saved_source_counter_and_claim(self):
        parent = self.parents['overnight']; s = self.states['overnight']; key = 'd-large-10-bergomi-10'
        v = s['versions'][key][s['current_versions'][key]]; source = parent / v['path']; original = source.read_text()
        n = read_json(ctrl.folder(parent, 'bergomi-10') / 'native.json')
        repaired, changes = ctrl.restore_figure_109(original, n)
        self.assertEqual(sha(source), v['sha256']); self.assertEqual(len(changes), 3)
        self.assertIn('assets/d6bde87360b133c396f7d878.jpg', core.image_references(repaired))
        import re
        numbered = []
        for figure in re.findall(r'\\begin\{figure\}(.*?)\\end\{figure\}', repaired, re.S):
            if r'\caption{' in figure:
                numbered.extend(re.findall(r'\\label\{fig:([^}]+)\}', figure))
        self.assertEqual(numbered, ['10'+str(i) for i in range(1,11)])
        self.assertIn('claims reproduced in the historical notes are contradicted', repaired)
        with self.assertRaises(ValueError):ctrl.restore_figure_109(repaired, n)

    def test_real_selection_no_replay_four_partial_appendices_and_17_units(self):
        rows = ctrl.choose_candidates(self.parents, self.states); parent = self.parents['production']
        omitted = ctrl.exclude_omitted_bodies(rows, parent); ctrl.reconcile_digest_headings(rows, parent)
        self.assertEqual(len(omitted), 4)
        ledger = [{'unit': r['key'], 'source_key': r['source_key'], 'blocks': r['blocks']} for r in rows]
        canonical = ctrl.canonical_plan(parent, self.states['production'])
        units = ctrl.plan_missing(parent, canonical, ledger, omitted)
        owned = core.unique_coverage(ledger); pending = [b for u in units for b in u['section']['blocks']]
        self.assertFalse(set(pending) & set(owned))
        self.assertEqual(len(pending), len(set(pending)))
        self.assertEqual(set(pending) | (set(owned) & {b for p in canonical for b in p['blocks']}), {b for p in canonical for b in p['blocks']})
        self.assertEqual(len(units), 17)
        self.assertEqual(sum(r['source_key'].startswith('gatheral') for r in rows), 34)
        for span in omitted:self.assertTrue(set(span['blocks']) <= set(pending))
        self.assertTrue(all(len(u['section']['blocks']) > 1 for u in units))

    def test_existing_lewis_selection_already_has_qualified_uncertainty(self):
        rows = ctrl.choose_candidates(self.parents, self.states); row = next(r for r in rows if r['key']=='gatheral-07-s05')
        text = (Path(row['parent']) / row['record']['path']).read_text()
        self.assertIn(r'\rho\ne0', text); self.assertIn('not independently\nestablished', text); self.assertIn(r'J^{(2)}', text)


def base_state(keys=('one','two')):
    tasks = [{'id': key+'/'+phase, 'key': key, 'source_key': 'bergomi-05', 'phase': phase,
              'status': 'pending', 'reasoning_effort': core.EFFORTS[phase], 'draft_label': None}
             for key in keys for phase in ('convert','critic')]
    return {'suite_protocol': core.PROTOCOL, 'chapter_contract': ctrl.edit.VERSION, 'timing_policy': 'manual_only',
            'first_dispatch': None, 'execution_limits': {'calls':None,'attempts_per_unit':1},
            'production_stage': {'task_ids':[t['id'] for t in tasks]}, 'tasks':tasks, 'calls':[],
            'concurrency_policy':copy.deepcopy(concurrent.POLICY),'active_stage':1,'stages':{'1':{}},
            'current_versions':{},'versions':{},'accuracy':{},'accuracy_records':{},'selection_ledger':[],
            'source_units':{},'connection_failures':0,'status':'running'}


class ControllerTests(unittest.TestCase):
    def test_pause_prevents_new_admission_and_obsolete_generation_refused(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td)/'run';run.mkdir();atomic_json(run/'pause.json',{'operator':True})
            with self.assertRaises(runtime.StopRun):ctrl.check_pause(run)
            pointer=Path(td)/'pointer.json';atomic_json(pointer,{'run':str(Path(td)/'different')})
            with patch.object(ctrl,'POINTER',pointer):
                with self.assertRaisesRegex(runtime.Fatal,'obsolete'):ctrl.require_current(run)

    def test_pause_drains_then_resume_dispatches_only_unsettled_dependencies(self):
        state=base_state();seen=[];paused=[False]
        def body(run,s,t):return dict(BODY,reasoning_effort=core.EFFORTS[t['phase']])
        def transport(run,c,b,**kw):
            seen.append(c['parent']);c.update(status='completed_response',metadata={},elapsed_seconds=.001)
            d=run/'calls'/c['id'];atomic_json(d/'request.json',b);atomic_json(d/'manifest.json',files_manifest(d));c['seal']=sha(d/'manifest.json')
            return DOC,c
        def finish(run,s,t,a,c):
            t.update(status='conversion_completed' if t['phase']=='convert' else 'critic_unchanged',settled_call=c['id'])
            s['current_versions'][t['key']]='draft';s['versions'][t['key']]={'draft':{'sha256':t['key']}}
            if not paused[0]:atomic_json(run/'pause.json',{'operator':True});paused[0]=True
        def coordinator(*args,**kwargs):concurrent.coordinate(*args,**kwargs,transport=transport,poll_seconds=.001)
        with tempfile.TemporaryDirectory() as td,patch.object(ctrl,'request_for',side_effect=body),patch.object(ctrl,'before_reserve'),patch.object(ctrl,'report'):
            run=Path(td)
            with self.assertRaises(runtime.StopRun):ctrl.execute_queue(run,state,sample=lambda n:health(n),verify_inputs=Mock(),coordinator=coordinator,finish_fn=finish)
            self.assertTrue(all(c['status']=='completed_response' for c in state['calls']))
            self.assertTrue(all(t['status']!='running' for t in state['tasks']))
            saved=copy.deepcopy(state['calls']);(run/'pause.json').unlink()
            ctrl.execute_queue(run,state,sample=lambda n:health(n),verify_inputs=Mock(),coordinator=coordinator,finish_fn=finish)
            self.assertEqual(len(seen),4);self.assertEqual(len(set(seen)),4)
            self.assertEqual(state['calls'][:len(saved)],saved)

    def test_real_scheduler_failed_unit_isolated_dependency_terminal_zero_dispatch(self):
        state = base_state(); seen=[]
        def body(run, s, t):
            if t['phase']=='critic':self.assertIn(t['key'],s['current_versions'])
            return dict(BODY, reasoning_effort=core.EFFORTS[t['phase']])
        def transport(run,c,b,**kw):
            seen.append(c['parent']);c.update(status='completed_response',metadata={'finish_reason':'stop'},elapsed_seconds=.001)
            d=run/'calls'/c['id'];atomic_json(d/'request.json',b);atomic_json(d/'manifest.json',files_manifest(d));c['seal']=sha(d/'manifest.json')
            return ('not a document' if c['parent']=='one/convert' else DOC),c
        def finish(run,s,t,a,c):
            t['settled_call']=c['id']
            if t['id']=='one/convert':t['status']='complete_answer_without_document';return
            t['status']='conversion_completed' if t['phase']=='convert' else 'critic_unchanged'
            s['current_versions'][t['key']]='draft';s['versions'][t['key']]={'draft':{'sha256':t['key']}}
        def coordinator(*args,**kwargs):concurrent.coordinate(*args,**kwargs,transport=transport,poll_seconds=.001)
        with tempfile.TemporaryDirectory() as td,patch.object(ctrl,'request_for',side_effect=body),patch.object(ctrl,'before_reserve'),patch.object(ctrl,'report'):
            run=Path(td);ctrl.execute_queue(run,state,sample=lambda n:health(n),verify_inputs=Mock(),coordinator=coordinator,finish_fn=finish)
            self.assertEqual(set(seen),{'one/convert','two/convert','two/critic'})
            self.assertLess(seen.index('two/convert'),seen.index('two/critic'))
            self.assertEqual(next(t for t in state['tasks'] if t['id']=='one/critic')['status'],'unavailable')
            compiler=Mock();assembler=Mock();ctrl.finalize(run,state,compiler=compiler,assembler=assembler)
            self.assertEqual(state['status'],core.TERMINAL);self.assertEqual(assembler.call_count,2)
            before=copy.deepcopy(state['calls']);ctrl.execute_queue(run,state,sample=Mock(side_effect=AssertionError('no readiness')),verify_inputs=Mock(),coordinator=Mock(side_effect=AssertionError('no dispatch')))
            with patch.object(ctrl.subprocess,'run',side_effect=AssertionError('terminal must not call tools')):ctrl.launch(run)
            self.assertEqual(state['calls'],before)

    def test_reconcile_sealed_response_idempotently_and_refuse_uncertainty(self):
        state=base_state(('one',));task=state['tasks'][0]
        call={'id':'call-001','parent':task['id'],'status':'in_progress','request_sha256':fingerprint(BODY)};state['calls']=[call]
        with tempfile.TemporaryDirectory() as td:
            run=Path(td)
            with self.assertRaisesRegex(runtime.Fatal,'Uncertain'):ctrl.reconcile_unfinished(run,state)
            d=run/'calls/call-001';atomic_json(d/'request.json',BODY);atomic_json(d/'outcome.json',dict(call,status='completed_response'))
            (d/'answer.txt').write_text(DOC);atomic_json(d/'manifest.json',files_manifest(d))
            def finish(run,s,t,a,c):self.assertEqual(a,DOC);t.update(status='conversion_completed',settled_call=c['id'])
            callback=Mock(side_effect=finish)
            ctrl.reconcile_unfinished(run,state,finish_fn=callback);snapshot=files_manifest(d)
            ctrl.reconcile_unfinished(run,state,finish_fn=callback)
            self.assertEqual(callback.call_count,1);self.assertEqual(files_manifest(d),snapshot)
            (d/'answer.txt').write_text('tamper')
            with self.assertRaises(Exception):ctrl.verify_seal(d,call['seal'])

    def test_findings_only_retains_real_draft_and_handles_build_failure(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);state=base_state(('one',));task=state['tasks'][1]
            n=native([block(1,'Content')]);section=core.target(n,[n['blocks'][0]['id']]);task['section']=section
            state['source_units']['one']={'source_key':'bergomi-05','section':section,'kind':'new'}
            f=ctrl.folder(run,'bergomi-05');f.mkdir(parents=True);atomic_json(f/'native.json',n);atomic_json(f/'assets.json',[])
            v=ctrl.remember(run,state,'one','conversion',DOC,{'source':'fixture'});state['current_versions']['one']='conversion'
            task.update(dispatched_draft_label='conversion',dispatched_draft_sha256=v['sha256'])
            call={'id':'call-002','status':'completed_response'}
            compile_mock=Mock(side_effect=ValueError('isolated build syntax failure'))
            ctrl.finish(run,state,task,'## Accuracy notes\nNo changes required.',call,compiler=compile_mock)
            self.assertEqual(task['status'],'critic_unchanged');self.assertNotIn('critic-call-002',state['versions']['one'])
            self.assertEqual((run/v['path']).read_text(),DOC)
            self.assertEqual(state['versions']['one'][state['current_versions']['one']]['compilation']['status'],'build_failure_unresolved')
            ctrl.finish(run,state,task,'## Accuracy notes\nNo changes required.',call,compiler=compile_mock)
            self.assertEqual(compile_mock.call_count,1)

    def test_status_is_read_only(self):
        state=base_state();state['historical_calls']={}
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);atomic_json(run/'state.json',state);before=files_manifest(run)
            with patch('builtins.print'):ctrl.status(run)
            self.assertEqual(files_manifest(run),before)


if __name__ == '__main__':unittest.main()
