"""Focused saved-output/parser/dependency regressions; no inference or downloads."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from probe import book_completion as scope, chapter_editorial as edit, chapter_accuracy
from probe import compiler_environment as environment, tex_compile
from probe.common import atomic_json, fingerprint, read_json, sha, files_manifest
from scripts import book_completion as completion, book_finalisation as finalisation
from test_book_completion import base_state, block, native


DOC = r'\documentclass{article}\begin{document}Mathematics $x^2$.\end{document}'


class FinalisationTests(unittest.TestCase):
    def test_known_ornament_mapping_preserves_math_and_is_idempotent(self):
        text = DOC.replace(r'\begin{document}', r'\newcommand{\fleurons}{❧ ❧}'+'\n'+r'\begin{document}')
        fixed, edits = scope.supported_ornament(text)
        self.assertEqual(len(edits), 1)
        self.assertIn(r'\DeclareUnicodeCharacter{2767}{\ensuremath{\clubsuit}}', fixed)
        self.assertEqual(fixed.split(r'\begin{document}')[1], text.split(r'\begin{document}')[1])
        self.assertIn(r'\newcommand{\fleurons}{❧ ❧}', fixed)
        self.assertEqual(scope.supported_ornament(fixed), (fixed, []))
        untouched = DOC.replace('Mathematics', 'Unicode σ ∂ and mathematics')
        self.assertEqual(scope.supported_ornament(untouched), (untouched, []))
        commented = '% ❧ decoration mentioned only in a comment\n' + DOC
        self.assertEqual(scope.supported_ornament(commented), (commented, []))

    def test_babel_french_is_a_specific_language_dependency_not_bad_tex(self):
        log = "Package babel Error: Unknown option 'french'. Either you misspelled it\n(babel) or the language definition file french.ldf was not found\n."
        result = environment.missing_dependency(log)
        self.assertEqual(result['filename'], 'french.ldf')
        self.assertEqual(result['kind'], 'language_dependency')
        self.assertEqual(result['approved_debian_package'], 'texlive-lang-french')
        self.assertEqual(tex_compile.classify_log(log,1), 'missing_package_or_asset')
        self.assertIsNone(environment.missing_dependency(log.replace('french','invented-language')))

    def test_french_provisioning_keeps_versioned_image_workflow_and_offline_build(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/'run';run.mkdir();source=root/'scripts/tex-compiler/Dockerfile'
            source.parent.mkdir(parents=True);source.write_text('FROM existing-test-base\n')
            state={};image='sha256:'+'a'*64;commands=[]
            def runner(argv,**kwargs):
                commands.append(argv);Path(argv[argv.index('--iidfile')+1]).write_text(image)
                return Mock(returncode=0)
            def compile_doc(document,out,**kwargs):
                self.assertEqual(kwargs['image'],image)
                self.assertIn('parts/check.tex',kwargs['assets'])
                out.mkdir(parents=True)
                return {'status':'passed','compilation_claim':True}
            with patch.object(environment.tex_compile,'compile_document',side_effect=compile_doc):
                result=environment.ensure(run,state,root,extra=('texlive-lang-french',),runner=runner)
            self.assertEqual(result,image);self.assertIn('texlive-lang-french',state['compiler_environment']['packages'])
            self.assertEqual(commands[0][:2],['docker','build'])
            self.assertIn('--pull=false',commands[0])
            self.assertEqual(list((run/state['compiler_environment']['path']/'context').iterdir())[0].name,'Dockerfile')
            command=tex_compile.command(image,root/'work')
            self.assertIn('--network=none',command);self.assertIn('--read-only',command);self.assertIn('-no-shell-escape',command)
            with self.assertRaises(ValueError):environment.ensure(run,state,root,extra=('unapproved-package',),runner=runner)


class EmbeddedLogTests(unittest.TestCase):
    def test_fenced_tex_accuracy_log_is_captured_without_duplicate_or_mangling(self):
        doc=DOC.replace(r'\end{document}',r'''
\section*{Accuracy log}
\noindent Disposition: correction applied; original reading retained.
\subsection*{Applied editorial corrections (book errors)}
\begin{enumerate}\item Correct $dt$ to $du$ in $\int_0^T f(u)\,du$.\end{enumerate}
\subsection*{Unresolved issues}
None.
\end{document}''')
        answer='```latex\n'+doc+'\n```'
        parsed, info=chapter_accuracy.envelope(answer,completion.book.simple.extract_document)
        notes,status=edit.notes_text(answer,info);self.assertEqual(status,'captured')
        self.assertTrue(notes.startswith(r'\section*{Accuracy log}'))
        record=edit.notes_record('fixture',notes,captured=status)
        self.assertFalse(record['certification']);self.assertTrue(record['items'])
        self.assertTrue(all(not e['independent_verification'] for e in record['items']))
        self.assertTrue(any(e['status']=='applied_claim_unverified' for e in record['items']))
        self.assertEqual(edit.annotate(parsed,record['items']),parsed)
        self.assertEqual(edit.annotate(parsed,record['items']),edit.annotate(parsed,record['items']))

    def test_existing_markdown_and_ambiguous_partial_behavior_remain(self):
        answer='```latex\n'+DOC+'\n```\n\n## Accuracy notes\n- **Unresolved:** source condition unclear.'
        _,info=chapter_accuracy.envelope(answer,completion.book.simple.extract_document)
        notes,status=edit.notes_text(answer,info);self.assertEqual(status,'captured');self.assertIn('source condition unclear',notes)
        partial=DOC.removesuffix(r'\end{document}')+r'\section*{Accuracy log}Claim.'
        self.assertEqual(edit.notes_text(partial,{'status':'unfenced'})[1],'unavailable_unparsed')
        ambiguous='```latex\n'+DOC+'\n```\n```latex\n'+DOC+'\n```'
        _,info=chapter_accuracy.envelope(ambiguous,completion.book.simple.extract_document)
        self.assertEqual(edit.notes_text(ambiguous,info)[1],'unavailable_unparsed')

    @unittest.skipUnless((finalisation.PARENT/'calls/call-004/answer.txt').exists(),'Optional saved timer response unavailable')
    def test_actual_timer_log_recovered_with_original_unchanged(self):
        path=finalisation.PARENT/'calls/call-004/answer.txt';before=sha(path);answer=path.read_text()
        document,info=chapter_accuracy.envelope(answer,completion.book.simple.extract_document)
        notes,status=edit.notes_text(answer,info);record=edit.notes_record('timer',notes,captured=status)
        self.assertEqual(status,'captured');self.assertIn('Footnotes 23 and 25',notes)
        self.assertIn('Unresolved issues',notes);self.assertEqual(edit.annotate(document,record['items']),document)
        self.assertEqual(sha(path),before)


class ComparisonTests(unittest.TestCase):
    def test_finalisation_matches_the_exact_dispatched_document_in_saved_request(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);draft=root/'actual.tex';draft.write_text(DOC)
            request={'model':'glm53-regular','messages':[{'role':'user','content':'CURRENT DRAFT:\n'+DOC}]}
            atomic_json(root/'calls/call-002/request.json',request)
            task={'key':'unit','call':'call-002','dispatched_draft_label':'annotated-input','dispatched_draft_sha256':sha(draft)}
            state={'versions':{'unit':{'annotated-input':{'path':'actual.tex','sha256':sha(draft)}}},
                   'calls':[{'id':'call-002','request_sha256':fingerprint(request)}]}
            result=finalisation.actual_draft(root,state,task);self.assertEqual(result[0],draft)
            draft.write_text(DOC+'changed')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):finalisation.actual_draft(root,state,task)

    def test_future_critic_finalization_records_actual_input_comparison_once(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);state=base_state(('one',));task=state['tasks'][1]
            n=native([block(1,'Mathematics')]);sec=scope.target(n,[n['blocks'][0]['id']]);task['section']=sec
            state['source_units']['one']={'source_key':'bergomi-05','section':sec,'kind':'new'}
            folder=completion.folder(run,'bergomi-05');folder.mkdir(parents=True)
            atomic_json(folder/'native.json',n);atomic_json(folder/'assets.json',[])
            completion.remember(run,state,'one','older-unreviewed',DOC.replace('Mathematics','WRONG INPUT'),{'fixture':True})
            actual=completion.remember(run,state,'one','actual-sent',DOC,{'fixture':True})
            state['current_versions']['one']='actual-sent';task.update(dispatched_draft_label='actual-sent',dispatched_draft_sha256=actual['sha256'])
            selected=DOC.replace('Mathematics','Mathematics and retained explanation')
            completion.finish(run,state,task,'```latex\n'+selected+'\n```',{'id':'call-002','status':'completed_response'},compiler=Mock())
            result=state['selection_ledger'][0]['critic_preservation_comparison']
            self.assertEqual(result['original_sha256'],actual['sha256'])
            self.assertTrue((run/'provenance/one/critic-call-002/critic-change.diff').exists())
            before=files_manifest(run)
            completion.finish(run,state,task,'```latex\n'+selected+'\n```',{'id':'call-002','status':'completed_response'},compiler=Mock())
            self.assertEqual(files_manifest(run),before)


if __name__=='__main__':unittest.main()
