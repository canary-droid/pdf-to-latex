import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from probe import mathpix_experiment as api


def job(number=1,pages=4):
    return {'source_id':'test-'+str(number),'sha256':str(number).zfill(64),
            'physical_pages':list(range(1,pages+1)),'subset_sha256':'a'*64,'subset':'subset.pdf'}


class MathpixSafety(unittest.TestCase):
    def test_budget_and_uncertainty_survive_round_trip(self):
        ledger={}
        first,fresh=api.reserve(ledger,'key','budget',job(),'/run')
        self.assertTrue(fresh);self.assertEqual(first['reserved_microusd'],20000)
        ledger=json.loads(json.dumps(ledger))
        again,fresh=api.reserve(ledger,'key','budget',job(),'/other-run')
        self.assertFalse(fresh);self.assertEqual(again['status'],'reserved_uncertain')
        for n in range(2,51):api.reserve(ledger,'key','budget',job(n),'/run')
        with self.assertRaisesRegex(ValueError,'exhausted'):api.reserve(ledger,'key','budget',job(51),'/run')

    def test_budget_is_shared_across_key_rotation(self):
        ledger={}
        api.reserve(ledger,'key1','budget',job(1,200),'/run')
        with self.assertRaises(ValueError):api.reserve(ledger,'key2','budget',job(2,1),'/run')

    def test_redaction_and_privacy(self):
        c=api.Client({'app_id':'fake-app-secret','app_key':'fake-key-secret'})
        result=c.redact({'app_id':'fake-app-secret','nested':['failure fake-key-secret']})
        self.assertNotIn('fake-app-secret',json.dumps(result));self.assertNotIn('fake-key-secret',json.dumps(result))
        with self.assertRaises(ValueError):c.safe_bytes(b'provider echo fake-key-secret')
        self.assertFalse(api.OPTIONS['metadata']['improve_mathpix'])
        self.assertFalse(api.OPTIONS['rm_fonts']);self.assertTrue(api.OPTIONS['include_equation_tags'])

    def test_no_submission_replay_after_disconnect(self):
        from scripts import mathpix_comparison as controller
        class Broken:
            key_id='fake-key-id'
            calls=0
            def submit(self,*args):self.calls+=1;raise RuntimeError('connection lost')
            def redact(self,s):return s
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'subset.pdf').write_bytes(b'%PDF-fake')
            client=Broken()
            with patch.object(controller,'LEDGER',root/'ledger'):
                first=controller.submit_once(root,{'budget_id':'budget'},job(),client)
                second=controller.submit_once(root,{'budget_id':'budget'},job(),client)
            self.assertEqual(client.calls,1)
            self.assertEqual(first['status'],'uncertain_submission');self.assertIsNone(second['pdf_id'])

    def test_pdf_id_survives_optional_output_write_failure(self):
        from scripts import mathpix_comparison as controller
        from probe.common import atomic_json as real_save
        class Success:
            key_id='fake-key-id'
            calls=0
            def submit(self,*args):self.calls+=1;return 'known_pdf_id',{'pdf_id':'known_pdf_id'}
            def redact(self,s):return s
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'subset.pdf').write_bytes(b'%PDF-fake')
            client=Success()
            def save(path,value):
                if Path(path).name=='submission.json':raise OSError('simulated disk failure')
                real_save(path,value)
            with patch.object(controller,'LEDGER',root/'ledger'),patch.object(controller,'atomic_json',save):
                controller.submit_once(root,{'budget_id':'budget'},job(),client)
                record=controller.submit_once(root,{'budget_id':'budget'},job(),client)
            self.assertEqual(record['pdf_id'],'known_pdf_id');self.assertEqual(client.calls,1)

    def test_zip_rejects_traversal_and_preserves_tex(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr('../outside.tex','bad')
        with self.assertRaises(ValueError):api.safe_zip(b.getvalue())
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr('paper.tex',r'\alpha+\rho X')
        self.assertEqual(api.safe_zip(b.getvalue())['paper.tex'],br'\alpha+\rho X')

    def test_options_and_page_scope_are_part_of_reuse_identity(self):
        a=job();b=job();b['physical_pages']=[2,3,4,5]
        self.assertNotEqual(api.job_identity(a),api.job_identity(b))
        self.assertNotEqual(api.job_identity(a),api.job_identity(a,dict(api.OPTIONS,rm_fonts=True)))

    def test_finished_resume_never_loads_credentials_or_calls_network(self):
        from scripts import mathpix_comparison as controller
        with patch.object(controller,'read_json',return_value={'status':controller.FINISHED}), \
             patch.object(controller,'verify'),patch.object(controller.api,'Client',side_effect=AssertionError('Credential access')), \
             patch.object(controller.sys,'argv',['mathpix','resume','--run','/tmp/finished-mathpix']):
            controller.main()


if __name__=='__main__':unittest.main()
