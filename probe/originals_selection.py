"""Exact, never-started source deferrals; no inference, retries or service control."""
from pathlib import Path
from .common import read_json, sha, fingerprint, contained
from .experiment import verify_seal

CANDIDATES = {
    'Attention_2017.pdf': '1706.03762',
    'Brigo_Deep_Interpretability.pdf': '2411.19317',
    'COS Le Floch.pdf': '2005.13248',
    'SINC.pdf': '2009.00557',
    'bayer_breneis23a_arxiv.pdf': '2309.07023',
    'Implied_Vol_Homescu.pdf': '1107.1834',
}
REASON = 'deferred for arXiv-source intake'
STATUS = 'deferred_for_arxiv_source_intake'
HANDOFF_FILES = {'scripts/originals_batch.py', 'probe/originals_selection.py'}


def decisions(manifest, state):
    """A reservation (including failed/uncertain) permanently establishes started."""
    tasks = {t['id']: t for t in state['tasks']}
    started = {}
    for call in state['calls']:
        if call['parent'] == 'readiness':
            continue
        if call['parent'] not in tasks:
            raise ValueError('Unmapped document reservation: ' + call['id'])
        source = tasks[call['parent']]['source_key']
        bound = call.get('concurrency_binding', {}).get('source_key', source)
        if bound != source:
            raise ValueError('Reservation source binding mismatch')
        started.setdefault(source, []).append(call['id'])
    rows = []
    for filename, arxiv in CANDIDATES.items():
        matches = [d for d in manifest['documents'] if any(o['name'] == filename for o in d['originals'])]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous exact filename: ' + filename)
        d = matches[0]; source = d['source_id']
        calls = started.get(source, [])
        units = [t for t in state['tasks'] if t['source_key'] == source]
        if not calls and any(t['status'] not in ('pending', STATUS) or t.get('call') for t in units):
            raise ValueError('Task disposition without its reservation: ' + source)
        if not calls and (state.get('versions', {}).get(source) or any(t['key'] in state.get('versions', {}) for t in units)):
            raise ValueError('Saved model version without its reservation: ' + source)
        rows.append({'filename': filename, 'source_id': source, 'sha256': d['sha256'],
                     'arxiv_candidate': arxiv, 'arxiv_status': 'operator-supplied paper-level match; exact version deferred',
                     'reservation_ids': calls, 'decision': 'retained' if calls else 'deferred',
                     'reason': 'document-level GLM reservation already exists' if calls else REASON,
                     'processing_status': state['documents'][source]['status']})
    return rows


def deferred(state, source):
    return source in state.get('deferred_sources', {})


def document_status(state, source):
    return STATUS if deferred(state, source) else state['documents'][source]['status']


def apply(state, rows):
    """Only pending task disposition and admission selection change; history stays."""
    chosen = {r['source_id']: r for r in rows if r['decision'] == 'deferred'}
    blocked = {t['id'] for t in state['tasks'] if t['source_key'] in chosen}
    if any(c['parent'] in blocked for c in state['calls']):
        raise ValueError('Selection became stale: a document reservation now exists')
    for source, row in chosen.items():
        if row['reservation_ids']:
            raise ValueError('Cannot defer a started document')
    state['deferred_sources'] = chosen
    for t in state['tasks']:
        if t['source_key'] in chosen:
            if t['status'] not in ('pending', STATUS):
                raise ValueError('Cannot defer settled or active task')
            t['status'] = STATUS
    state['production_stage']['task_ids'] = [x for x in state['production_stage']['task_ids'] if x not in blocked]


def active_tasks(state, tasks):
    return [t for t in tasks if not deferred(state, t['source_key'])]


def assert_dispatch(state, task):
    if deferred(state, task['source_key']) or task['id'] not in state['production_stage']['task_ids']:
        raise ValueError('Source is outside the current admitted selection: ' + task['source_key'])


def binding(run, state):
    path = state.get('binding_path', 'binding.json')
    if path != 'binding.json' and not path.startswith('continuations/'):
        raise ValueError('Invalid continuation binding path')
    return read_json(contained(run, path))


def verify(run, state):
    continuation = state.get('selection_continuation')
    if not continuation:
        if state.get('deferred_sources') or state.get('binding_path'):
            raise ValueError('Unbound source deferrals')
        return
    folder = contained(run, continuation['path'])
    verify_seal(folder, continuation['seal'])
    prior = read_json(folder/'prior-state.json')
    record = read_json(folder/'selection.json')
    if not state.get('recovery_continuation') and sha(contained(run, state['binding_path'])) != sha(folder/'binding.json'):
        raise ValueError('Continuation binding changed')
    if record['inventory_sha256'] != sha(run/'collection.json'):
        raise ValueError('Frozen inventory changed')
    expected = {r['source_id']: r for r in record['candidates'] if r['decision'] == 'deferred'}
    if state.get('deferred_sources') != expected:
        raise ValueError('Source selection differs from sealed continuation')
    if state['calls'][:len(prior['calls'])] != prior['calls']:
        raise ValueError('Inherited reservations or outcomes changed')
    for key in ('execution_limits', 'phase_efforts', 'concurrency_policy', 'timing_policy'):
        if state[key] != prior[key]:
            raise ValueError('Selection continuation changed execution policy: ' + key)
    tasks = {t['id']: t for t in state['tasks']}
    allowed = [x for x in prior['production_stage']['task_ids'] if tasks[x]['source_key'] not in expected]
    if state.get('recovery_continuation'):
        from .originals_recovery import extra_ids, SUPERSEDED
        allowed = [ident for ident in allowed if ident not in SUPERSEDED] + extra_ids(run,state)
    if state['production_stage']['task_ids'] != allowed:
        raise ValueError('Changed admitted task list')
    for call in state['calls']:
        if call['parent'] != 'readiness' and tasks[call['parent']]['source_key'] in expected:
            raise ValueError('Deferred source has a reservation')
    for t in state['tasks']:
        if t['source_key'] in expected and t['status'] != STATUS:
            raise ValueError('Deferred task reactivated')
