#!/usr/bin/env python3
"""Offline evidence preparation for the finite extraction comparison."""
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from probe.common import atomic_json, sha, writer_lock, files_manifest
from probe import focused_recovery

ORIGINALS = ROOT / 'runs/originals-batch-20261101T212602Z-ab2d41'
RECOVERY = ROOT / 'runs/focused-recovery-20261103T223632Z-d9c8f9'
SELECTION = [
    ('original-21debf82bc2c0a3d', [4, 5, 6], 'Dense characteristic-function cases, equations and unreliable secondary text'),
    ('original-185f783748bb248e', list(range(25, 30)), 'Recovered OCR window and adjacent spectral derivations'),
    ('original-496de5aa992285e2', list(range(7, 12)), 'Argument, appendix and charts after references'),
    ('original-ead9d04e4c78147d', list(range(7, 11)), 'Difficult moment formulae with contiguous context'),
    ('original-1fc68aa26e4deb3b', list(range(3, 7)), 'Two-column mathematics, Table A and later figures/content'),
    ('original-dcbf009549ec6318', list(range(2, 6)), 'Ordinary control including complete Section 2'),
    ('original-547334b059504dcb', list(range(3, 7)), 'Six-panel Figure 1 and Tables 1–4'),
    ('original-59498c386e495139', [1, 2, 3], 'Previously successful two-column journal control; adjacent opening pages'),
]


def prepare():
    import fitz
    from scripts import originals_batch as batch
    if not all(batch.books.speed.idle(p) for p in (ROOT, ROOT/'runs', ORIGINALS, RECOVERY)):
        raise RuntimeError('Existing project writer is active; preparation deferred')
    pointer = ROOT/'results/extraction-comparison-current.json'
    if pointer.exists():
        raise RuntimeError('Comparison preparation already exists; inspect it before replacing anything')
    parent = json.loads((ORIGINALS/'state.json').read_text())
    recovered = json.loads((RECOVERY/'state.json').read_text())
    if parent['status'] != 'collection_finished_with_report' or recovered['status'] != 'focused_trial_finished':
        raise RuntimeError('Parent work is not settled')
    inventory = {d['source_id']: d for d in json.loads((ORIGINALS/'collection.json').read_text())['documents']}
    with writer_lock(ROOT), writer_lock(ROOT/'runs'):
        run = ROOT/'runs'/('extraction-comparison-'+time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
        run.mkdir()
        rows = []
        for sid, pages, reason in SELECTION:
            identity = inventory[sid]
            original = ORIGINALS/parent['documents'][sid]['original']
            if sha(original) != identity['sha256']:
                raise RuntimeError('Source identity changed: '+sid)
            source = RECOVERY/'inputs'/sid
            if not source.exists(): source = ORIGINALS/'inputs'/sid
            native = json.loads((source/'native.json').read_text())
            chosen = [b for b in native['blocks'] if b['page']['original_physical_page'] in pages]
            if set(pages) != {b['page']['original_physical_page'] for b in chosen}:
                raise RuntimeError('Saved baseline lacks an assigned physical page: '+sid)
            destination = run/'sources'/sid
            destination.mkdir(parents=True)
            atomic_json(destination/'baseline.json', {'blocks': chosen, 'source_native':str(source/'native.json'), 'source_native_sha256':sha(source/'native.json')})
            image_rows = []
            with fitz.open(original) as pdf:
                secondary = []
                for number in pages:
                    page = pdf[number-1]
                    image = destination/f'page-{number:03}.png'
                    pix = page.get_pixmap(matrix=fitz.Matrix(200/72, 200/72), alpha=False)
                    pix.save(image)
                    text = page.get_text(sort=True)
                    secondary.append({'physical_pdf_page':number,'text':text})
                    furniture = [b['tex'] for b in chosen if b['page']['original_physical_page']==number and b['kind']=='page_number']
                    image_rows.append({'physical_pdf_page':number,'printed_label_evidence':furniture,'printed_label_status':'saved extraction; pending image check','image':str(image.relative_to(run)),'sha256':sha(image),'width':pix.width,'height':pix.height,'dpi':200,'rotation':page.rotation,'mediabox':list(page.mediabox),'cropbox':list(page.cropbox)})
            quality = focused_recovery.secondary_assessment(secondary)
            if sid == 'original-21debf82bc2c0a3d':
                quality['experiment_policy'] = 'Known corrupted native text quarantined identically in all arms; original retained.'
                quality['supplied_pages'] = []
            else: quality['supplied_pages'] = quality['pages']
            atomic_json(destination/'secondary-assessment.json',quality)
            # Asset copies retain existing basenames; source records remain untouched.
            assets=[]
            for reference in json.loads((source/'assets.json').read_text()):
                asset = source.parent/reference
                if asset.exists():
                    target=destination/reference;target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(asset,target)
                    assets.append({'path':str(target.relative_to(run)),'sha256':sha(target),'original':str(asset)})
            rows.append({'source_id':sid,'filename':identity['originals'][0]['name'],'sha256':identity['sha256'],'original':str(original),'physical_pages':pages,'reason':reason,'pages':image_rows,'assets':assets,'baseline_native_sha256':sha(source/'native.json')})
        metadata=ROOT/'results/extraction-comparison-development'
        pins={name:json.loads((metadata/(name+'.json')).read_text())['sha'] for name in ('mineru-model','glmocr-model','layout-model','glmocr-sdk')}
        plan={'status':'scope_prepared_not_frozen','created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'documents':rows,'page_count':sum(len(r['pages']) for r in rows),'pins':pins,
              'runtime_candidate':'vllm/vllm-openai@sha256:4f986370d7737abacc70ac17f86695acd1dc7892a02ad89ac132639d5afee0d0',
              'downstream':[{'source_id':SELECTION[0][0],'scope':'Complete Cases 13–18; other page material is context only','physical_pages':[4,5,6]}, {'source_id':SELECTION[5][0],'scope':'Complete Section 2, Information derivatives, before Section 3','physical_pages':[2,3,4]}],
              'maximum_primary_downstream_requests':12,'conversion_effort':'high','critic_effort':'max','output_tokens':131072,'model':'glm53-regular','images_in_downstream':False,
              'baseline_timing':'Historical multi-page overlapping windows; not paired per-page timing',
              'source_checks':'Pending direct image inspection and frozen structural expectations',
              'author_tex':'Not yet checked against existing local source audit; no new source searches',
              'scope_exclusions':['Cooking with Collateral','production queues','paid or hosted inference']}
        atomic_json(run/'plan-draft.json',plan)
        atomic_json(run/'prepared-files.json',files_manifest(run/'sources'))
        atomic_json(run/'progress.json',{'status':'preparation_in_progress','run':str(run),'pages':plan['page_count'],'models_run':0,'downstream_requests':0})
        atomic_json(pointer,{'run':str(run),'status':'preparation_in_progress'})
        print(run)
        return run


if __name__ == '__main__': prepare()
