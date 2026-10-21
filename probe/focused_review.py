"""Offline region experiment with explicit selection and limited coverage."""
import copy

from .common import atomic_json, contained, files_manifest, read_json, sha
from .page_review import FOCUSED_PROMPT_VERSION, focused_prompt, preview_html, request_payload
from .portable_export import render_block
from .saved_pages import copy_evidence, render_region, saved_pages

MAX_REGIONS = 4


def saved_ocr_drafts(pages):
    """Review OCR as data, including broken math; never relax TeX export checks."""
    inventory = []
    for page in pages:
        for block in page['blocks']:
            try:
                latex, _ = render_block(block)
            except ValueError:
                content = block['native'].get('content')
                latex = ('\\[\n'+content+'\n\\]' if block['kind'] == 'equation'
                         and isinstance(content,str) and content.strip() else None)
            inventory.append({'block_id':block['id'],'operation':'unchanged','latex':latex})
    return inventory


def select_blocks(selection, pages, inventory, limits, *, draft_source='accepted_derivative'):
    if not isinstance(selection,dict) or set(selection) != {'block_ids'}:
        raise ValueError('Focused selection must contain only block_ids; no hints or expected answers')
    ids = selection['block_ids']
    if (not isinstance(ids,list) or not 1 <= len(ids) <= MAX_REGIONS
            or not all(isinstance(x,str) for x in ids) or len(set(ids)) != len(ids)):
        raise ValueError('Select one to four distinct blocks; no silent truncation')
    blocks = {b['id']:(p,b) for p in pages for b in p['blocks']}
    drafts = {item['block_id']:item for item in inventory}
    if set(ids) - set(blocks):
        raise ValueError('Unknown focused block selection')
    if len({blocks[x][0]['page_id'] for x in ids}) > limits['max_pages']:
        raise ValueError('Focused selection exceeds the page limit')
    regions = []
    for identity in ids:
        page, block = blocks[identity]
        draft = drafts.get(identity)
        if not draft or draft['operation'] == 'delete' or not draft.get('latex') or not block['bbox']:
            raise ValueError('Focused comparison requires a nonempty draft and a source bbox')
        region = copy.deepcopy(page)
        region.update(request_id=page['page_id']+'-b'+str(block['reading_order']),
                      review_scope='selected_blocks',blocks=[copy.deepcopy(block)],
                      draft_by_block=[{'block_id':identity,'latex':draft['latex'],'status':'unreviewed derivative draft'}],
                      context_blocks=[copy.deepcopy(b) for b in page['blocks']
                          if abs(b['reading_order']-block['reading_order']) == 1])
        if draft_source == 'saved_ocr':
            region['draft_source'] = 'saved_ocr'
            region['draft_by_block'][0]['status'] = 'unreviewed saved OCR draft'
        regions.append(region)
    return regions


def write_focused_preview(root, run, out, derivative, selection_path, model, base_url, limits, *, reasoning_effort, sources=None):
    from .acceptance import verify_derivative
    if derivative is not None:
        inventory = verify_derivative(root,run,derivative)
        sources = read_json(derivative/'acceptance.json')['selection']['sources']
    elif not isinstance(sources,str) or not sources:
        raise ValueError('Saved OCR focused preview requires explicit sources')
    pages = saved_pages(root,run,sources)
    draft_source = 'accepted_derivative' if derivative is not None else 'saved_ocr'
    if derivative is None:
        inventory = saved_ocr_drafts(pages)
    selection = read_json(selection_path)
    regions = select_blocks(selection,pages,inventory,limits,draft_source=draft_source)
    copy_evidence(run,regions,out)
    records = []
    for region in regions:
        region['focused_prompt_version'] = FOCUSED_PROMPT_VERSION
        folder = out/'pages'/region['request_id']
        folder.mkdir(parents=True)
        window = out/'evidence'/region['unit']/'input.pdf'
        original = render_region(window,region['page']['local_page_idx'],folder/'source.png',max_edge=limits['page_max_edge'])
        original.update(id='original',selection='complete page for context only',block_ids=[])
        detail = render_region(window,region['page']['local_page_idx'],folder/'region.png',
                               bbox=region['blocks'][0]['bbox'],max_edge=limits['crop_max_edge'])
        detail.update(id='selected-region',selection='explicit selected block',block_ids=[region['blocks'][0]['id']])
        region['images'] = [original,detail]
        atomic_json(folder/'page.json',region)
        payload, budgets = request_payload(region,folder,model,limits,reasoning_effort=reasoning_effort)
        atomic_json(folder/'request.json',payload)
        records.append({'page_id':region['request_id'],'source_page_id':region['page_id'],
                        'selected_block_ids':[region['blocks'][0]['id']],'status':'ready','budgets':budgets})
    atomic_json(out/'selection.json',selection)
    atomic_json(out/'preview.json',{'review_mode':'regions','focused_prompt_version':FOCUSED_PROMPT_VERSION,'source_run':str(run),
        'source_state_sha256':sha(run/'state.json'),'sources':sources,'draft_source':draft_source,
        'derivative_run':str(derivative) if derivative is not None else None,
        'derivative_manifest_sha256':sha(derivative/'artifact-manifest.json') if derivative is not None else None,
        'selection_sha256':sha(out/'selection.json'),'selected_block_ids':selection['block_ids'],
        'model':model,'endpoint':base_url,'limits':limits,'reasoning_effort':reasoning_effort,
        'pages':records,'status':'ready','known_source_used':False,'full_page_coverage':False,
        'mathematical_vision':'unqualified'})
    preview_html(out,records,'Offline focused-region inputs — no requests sent')
    atomic_json(out/'artifact-manifest.json',files_manifest(out))
    return True


def verify_focused_inputs(root, run, preview, metadata, pages):
    from .acceptance import verify_derivative
    focused_prompt(metadata)
    draft_source = metadata.get('draft_source','accepted_derivative')
    if draft_source == 'saved_ocr':
        if metadata.get('derivative_run') is not None or metadata.get('derivative_manifest_sha256') is not None:
            raise ValueError('Saved OCR preview must not claim an accepted derivative')
        inventory = saved_ocr_drafts(pages)
    elif draft_source == 'accepted_derivative':
        derivative = contained(root,metadata['derivative_run'])
        if sha(derivative/'artifact-manifest.json') != metadata['derivative_manifest_sha256']:
            raise ValueError('Focused derivative binding changed')
        inventory = verify_derivative(root,run,derivative)
    else:
        raise ValueError('Unknown focused draft source')
    selection = read_json(preview/'selection.json')
    if (sha(preview/'selection.json') != metadata['selection_sha256']
            or selection['block_ids'] != metadata['selected_block_ids']
            or metadata.get('full_page_coverage') is not False):
        raise ValueError('Focused selection/coverage changed')
    regions = select_blocks(selection,pages,inventory,metadata['limits'],draft_source=draft_source)
    if 'focused_prompt_version' in metadata:
        for region in regions:
            region['focused_prompt_version'] = metadata['focused_prompt_version']
    if [r['request_id'] for r in regions] != [r['page_id'] for r in metadata['pages']]:
        raise ValueError('Focused request membership differs from selected blocks')
    for region, record in zip(regions,metadata['pages']):
        folder = preview/'pages'/region['request_id']
        saved = read_json(folder/'page.json')
        if ({k:v for k,v in saved.items() if k != 'images'} != region
                or record['source_page_id'] != region['page_id']
                or record['selected_block_ids'] != [region['blocks'][0]['id']]):
            raise ValueError('Focused draft/context differs from bound source or derivative')
        payload, _ = request_payload(saved,folder,metadata['model'],metadata['limits'],
                                     reasoning_effort=metadata['reasoning_effort'])
        if payload != read_json(folder/'request.json'):
            raise ValueError('Focused request differs from exact selected inputs')
