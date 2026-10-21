"""Explicit, hash-bound selection of saved proposals. No inference or source edits."""
from datetime import datetime, timezone
from pathlib import Path
import shutil

from .common import atomic_json, contained, files_manifest, fingerprint, read_json, sha
from .local_model import parse_json_response
from .page_review import validate_proposals, verify_preview
from .portable_export import accepted_fragment, export_saved
from .saved_pages import saved_pages


def manifest_digest(path):
    return fingerprint(files_manifest(path))


def verified_review(root, run, review, preview):
    metadata = verify_preview(preview)
    if metadata.get('review_mode', 'pages') != 'pages':
        raise ValueError('Acceptance of focused responses is deferred; use a saved whole-page review')
    pages = saved_pages(root, run, metadata['sources'])
    provenance = read_json(review/'provenance.json')
    if (metadata['source_run'] != str(run) or metadata['source_state_sha256'] != sha(run/'state.json')
            or provenance['source_run'] != str(run) or provenance['source_state_sha256'] != sha(run/'state.json')
            or provenance['preview_run'] != str(preview)
            or provenance['preview_manifest_sha256'] != sha(preview/'artifact-manifest.json')):
        raise ValueError('Stale source/review/preview binding')
    expected = [p['page_id'] for p in pages]
    summary = read_json(review/'summary.json')
    if ([p['page_id'] for p in metadata['pages']] != expected
            or summary['completed_pages'] != expected or summary.get('failed_pages') or summary.get('pending_pages')):
        raise ValueError('Incomplete or inconsistent saved review coverage')
    if provenance['model'] != metadata['model'] or provenance['endpoint'] != metadata['endpoint']:
        raise ValueError('Review identity differs from preview')
    catalog = []
    for page in pages:
        folder = review/'pages'/page['page_id']
        original = preview/'pages'/page['page_id']
        supplied = read_json(folder/'page.json')
        if ({k:v for k,v in supplied.items() if k != 'images'} != page
                or (folder/'page.json').read_bytes() != (original/'page.json').read_bytes()):
            raise ValueError('Saved review page differs from source/preview')
        for image in supplied['images']:
            if sha(contained(folder,image['path'])) != image['sha256']:
                raise ValueError('Saved review image changed')
        prepared, actual = read_json(original/'request.json'), read_json(folder/'request.json')
        if 'response_format' not in actual:
            prepared.pop('response_format', None)
        if actual != prepared:
            raise ValueError('Saved request differs from preview')
        answer = read_json(folder/'assistant-response.json')
        record = read_json(folder/'proposals.json')
        value = validate_proposals(parse_json_response(answer['content']), page)
        if (answer.get('finish_reason') != 'stop' or answer.get('actual_model') != metadata['model']
                or record.get('status') != 'proposals_unaccepted' or record.get('proposal') != value
                or record.get('model_evidence') != {k:v for k,v in answer.items() if k != 'content'}):
            raise ValueError('Invalid or conflicting saved response/proposal evidence')
        # Bind the parsed proposal to the raw HTTP evidence as well as its saved projection.
        attempt = folder/'attempts'/Path(answer['attempt_dir']).name
        raw = read_json(attempt/'response.raw')
        choices = raw.get('choices', [])
        if (read_json(attempt/'request.json').get('body') != actual or raw.get('model') != metadata['model']
                or len(choices) != 1 or choices[0].get('finish_reason') != 'stop'
                or choices[0].get('message',{}).get('content') != answer['content']):
            raise ValueError('Raw HTTP evidence differs from saved review')
        for index, proposal in enumerate(value['proposals']):
            digest = fingerprint(proposal)
            catalog.append({'proposal_id':f"{page['page_id']}:proposal-{index}-{digest[:16]}",
                'page_id':page['page_id'], 'proposal_index':index, 'proposal_sha256':digest,
                'block_ids':proposal['block_ids'], 'proposal':proposal,
                'target_sha256':{b['id']:fingerprint(b) for b in page['blocks'] if b['id'] in proposal['block_ids']}})
    return metadata, pages, catalog


def make_plan(root, run, review, preview):
    metadata, pages, catalog = verified_review(root, run, review, preview)
    return {'schema':'saved-proposal-selection-v1', 'source_run':str(run.relative_to(root)),
        'review_run':str(review.relative_to(root)), 'preview_run':str(preview.relative_to(root)),
        'bindings':{'source_manifest_sha256':manifest_digest(run), 'review_manifest_sha256':manifest_digest(review),
                    'preview_manifest_sha256':sha(preview/'artifact-manifest.json'),
                    'source_pages_sha256':fingerprint(pages)},
        'sources':metadata['sources'], 'catalog':catalog,
        'authorization':'', 'selected':[], 'correction_groups':[], 'unresolved_issues':[]}


def validated_selection(root, plan):
    if not isinstance(plan,dict) or plan.get('schema') != 'saved-proposal-selection-v1':
        raise ValueError('Unsupported acceptance selection schema')
    run, review, preview = [contained(root, plan[key]) for key in ('source_run','review_run','preview_run')]
    fresh = make_plan(root, run, review, preview)
    for key in ('bindings','sources','catalog'):
        if plan.get(key) != fresh[key]:
            raise ValueError('Stale or changed acceptance evidence: '+key)
    if not isinstance(plan.get('authorization'),str) or not plan['authorization'].strip():
        raise ValueError('Explicit operator authorization is required; certainty is not acceptance')
    catalog = {p['proposal_id']:p for p in fresh['catalog']}
    selected = plan.get('selected')
    if not isinstance(selected,list) or not selected:
        raise ValueError('Select proposals explicitly; an empty selection accepts nothing')
    ids, edits = set(), {}
    for selection in selected:
        if not isinstance(selection,dict) or set(selection) != {'proposal_id','operation'}:
            raise ValueError('Selection needs proposal_id and explicit replace/delete operation')
        identity = selection['proposal_id']
        if not isinstance(identity,str) or identity not in catalog or identity in ids:
            raise ValueError('Unknown or conflicting duplicate proposal selection')
        ids.add(identity)
        item = catalog[identity]
        targets = item['block_ids']
        if len(targets) != 1:
            raise ValueError('Only single-block replacements/deletions are supported; missing-region, merge and split edits are deferred')
        target = targets[0]
        if target in edits:
            raise ValueError('Conflicting edits to the same block: '+target)
        operation, latex = selection['operation'], item['proposal']['suggested_latex']
        if operation == 'replace':
            accepted_fragment(latex)
        elif operation != 'delete' or latex != '':
            raise ValueError('Deletion must be explicit and the saved suggestion must be empty')
        edits[target] = {'operation':operation,'latex':latex,'proposal_id':identity,
                         'target_sha256':item['target_sha256'][target]}
    groups = plan.get('correction_groups')
    if not isinstance(groups,list):
        raise ValueError('Correction groups must be explicit lists of proposal IDs')
    grouped = set()
    for group in groups:
        if (not isinstance(group,list) or len(group)<2 or not all(isinstance(x,str) and x in catalog for x in group)
                or len(set(group)) != len(group) or grouped.intersection(group)):
            raise ValueError('Unknown, duplicate or overlapping correction group')
        grouped.update(group)
        if ids.intersection(group) and not set(group) <= ids:
            raise ValueError('Dependent correction group must be selected and applied atomically')
    blocks = {b['id'] for p in saved_pages(root,run,fresh['sources']) for b in p['blocks']}
    issues = plan.get('unresolved_issues')
    if not isinstance(issues,list):
        raise ValueError('Unresolved issues must be a list')
    for issue in issues:
        if (not isinstance(issue,dict) or set(issue) != {'block_id','note'} or issue['block_id'] not in blocks
                or issue['block_id'] in edits or not isinstance(issue['note'],str) or not issue['note'].strip()):
            raise ValueError('Unknown, applied or invalid unresolved issue target')
    return run, review, preview, edits


def apply_accepted(root, plan_path, out):
    plan = read_json(plan_path)
    run, review, preview, edits = validated_selection(root, plan)
    if out.exists() and any(out.iterdir()):
        raise ValueError('Derivative output must be new and empty')
    out.mkdir(parents=True,exist_ok=True)
    export_saved(root,run,out,plan['sources'],accepted_edits=edits,unresolved_issues=plan['unresolved_issues'])
    shutil.copytree(review,out/'review-evidence')
    atomic_json(out/'acceptance.json',{'status':'explicit_selection_applied',
        'accepted_at_utc':datetime.now(timezone.utc).isoformat(), 'plan_sha256':sha(plan_path),
        'selection':plan, 'applied_edits':edits, 'original_review_status':'proposals_unaccepted'})
    provenance = read_json(out/'provenance.json')
    provenance.update(acceptance_sha256=sha(out/'acceptance.json'), bindings=plan['bindings'],
                      review_run=str(review),preview_run=str(preview),acceptance_code_sha256=sha(__file__))
    atomic_json(out/'provenance.json',provenance)
    summary = read_json(out/'summary.json')
    summary['status'] = 'exported_with_explicit_acceptance'
    atomic_json(out/'summary.json',summary)
    atomic_json(out/'artifact-manifest.json',[e for e in files_manifest(out) if e['path'] != 'artifact-manifest.json'])
    return out


def verify_derivative(root, run, derivative):
    entries = read_json(derivative/'artifact-manifest.json')
    if [e for e in files_manifest(derivative) if e['path'] != 'artifact-manifest.json'] != entries:
        raise ValueError('Derivative artifacts changed')
    record = read_json(derivative/'acceptance.json')
    source, _, _, edits = validated_selection(root,record['selection'])
    if source != run or record['applied_edits'] != edits:
        raise ValueError('Derivative belongs to different source/selection')
    return read_json(derivative/'inventory.json')
