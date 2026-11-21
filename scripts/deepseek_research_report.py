#!/usr/bin/env python3
"""Saved-result statistics and compact inspection ZIP; never dispatches work."""
import argparse
import base64
import csv
import hashlib
import json
import random
import statistics
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from probe.common import atomic_json, read_json, sha, fingerprint
from probe import deepseek_research as r


def verify_no_runtime_secret(paths, secret):
    """Inspect bytes locally without exposing the credential in errors or output."""
    value = secret.encode()
    if not value:
        raise ValueError('Runtime credential unavailable for archive inspection')
    for path in paths:
        if value in Path(path).read_bytes():
            raise ValueError('Runtime credential detected in an inspection input; archive not created')


def qualification_recipe(run, kind):
    """Describe a public control exactly, without duplicating paper/image bytes."""
    original = read_json(run / 'qualification-inputs' / (kind + '.json'))
    def public_hash(messages):
        # Match the frozen pack's Unicode-preserving message hash, which is
        # intentionally distinct from the ASCII-escaped whole-request hash.
        return hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True,
                                         separators=(',', ':')).encode()).hexdigest()
    recipe = {'kind': kind, 'system_message': original[0],
              'messages_sha256': public_hash(original),
              'original_file_sha256': sha(run / 'qualification-inputs' / (kind + '.json'))}
    if kind == 'long':
        prefix = original[1]['content'].split('\n\n<source filename=', 1)[0]
        recipe.update(user_prefix=prefix, source_files=[
            'public/sources/' + name for name in ('rough_heston.tex', 'cos.tex', 'markov.tex')],
            reconstruction='Append each source in order using: two newlines, <source filename="BASENAME">, '
                           'newline, complete UTF-8 source text, newline, </source>. Sources are under run/pack/.')
        content = prefix
        for name in recipe['source_files']:
            content += '\n\n<source filename="' + Path(name).name + '">\n'
            content += (run / 'pack' / name).read_text() + '\n</source>'
    elif kind == 'image':
        recipe.update(text_part=original[1]['content'][0], image_file='numbers.png',
                      reconstruction='Use text_part followed by an image_url part whose URL is '
                                     'data:image/png;base64, plus standard base64 of run/qualification-inputs/numbers.png.')
        content = [recipe['text_part'], {'type': 'image_url', 'image_url': {
            'url': 'data:image/png;base64,' + base64.b64encode((run / 'qualification-inputs/numbers.png').read_bytes()).decode()}}]
    else:
        raise ValueError('Only source/image controls need reconstruction recipes')
    rebuilt = [recipe['system_message'], {'role': 'user', 'content': content}]
    if rebuilt != original or public_hash(rebuilt) != recipe['messages_sha256']:
        raise ValueError('Qualification reconstruction differs from frozen public input')
    recipe['reconstruction_verified'] = True
    return recipe


def refresh_mask(run, destination):
    """One random assignment for the whole plan; copy only terminal answers.

    Pending requests have no answer file or score. This permits useful masked
    work during an external outage without calling a partial batch complete.
    """
    _, state = r.verify(run)
    folder = run / 'grading'
    mapping_path = folder / 'identity-map.json'
    assignment_seal = folder / 'assignment.sha256'
    if not mapping_path.exists():
        plan = read_json(run / 'plan.json')
        random.SystemRandom().shuffle(plan)
        atomic_json(mapping_path, {f'M{i:03d}': task for i, task in enumerate(plan, 1)})
        assignment_seal.write_text(sha(mapping_path) + '\n')
        atomic_json(folder / 'mask-method.json', {
            'method': 'Masked Codex scoring; one randomized assignment across all64 frozen requests, '
                      'terminal final answers copied incrementally; no identity join until scores are locked.',
            'planned_requests': 64, 'assignment_sha256': sha(mapping_path),
            'implementation_sha256': sha(Path(__file__).resolve()),
            'reason_for_incremental_copy': 'Pinned hosted route became unavailable after17 terminal attempts; '
                                           'pending attempts are not failures and receive no scores.'})
    if sha(mapping_path) != assignment_seal.read_text().strip():
        raise ValueError('Random mask assignment changed')
    mapping = read_json(mapping_path)
    if {x['attempt_id'] for x in mapping.values()} != {x['attempt_id'] for x in read_json(run / 'plan.json')}:
        raise ValueError('Mask assignment differs from frozen schedule')
    terminal = {x['id'] for x in state['attempts'] if x['phase'] == 'scored'
                and x['status'] not in ('prepared', 'dispatched', 'uncertain_dispatch')}
    for masked, task in mapping.items():
        if task['attempt_id'] not in terminal:
            continue
        source = run / 'attempts' / task['attempt_id'] / 'answer.txt'
        target = folder / 'masked' / masked
        if (target / 'answer.txt').exists():
            if sha(target / 'answer.txt') != sha(source):
                raise ValueError('Previously masked answer changed')
        else:
            target.mkdir(parents=True)
            (target / 'answer.txt').write_bytes(source.read_bytes())
            atomic_json(target / 'task.json', {'base_id': task['base_id'], 'condition_id': task['condition_id'],
                                             'answer_sha256': sha(source)})
    atomic_json(folder / 'mask-seal.json', {str(p.relative_to(folder)): sha(p)
        for p in (folder / 'masked').rglob('*') if p.is_file() and p.name in ('answer.txt', 'task.json')})
    progress = {'copied_terminal_answers': len(terminal), 'planned': 64,
                'pending_unscored': 64 - len(terminal), 'collection_complete': state['status'] == 'finished'}
    atomic_json(folder / 'mask-progress.json', progress)
    print(json.dumps(progress))


def verify_finished(run, destination):
    """Check saved evidence and protected work without contacting either model."""
    binding, state = r.verify(run)
    if state['status'] != 'finished' or not state.get('restored_initial_configuration'):
        raise ValueError('Study is not finished and restored')
    plan = read_json(run / 'plan.json')
    scored = [x for x in state['attempts'] if x['phase'] == 'scored']
    if len(scored) != 64 or {x['id'] for x in scored} != {x['attempt_id'] for x in plan}:
        raise ValueError('Scored schedule incomplete or changed')
    if any(x['status'] in ('prepared', 'dispatched') for x in state['attempts']):
        raise ValueError('Nonterminal attempt remains')
    manifest = read_json(run / 'RUN_MANIFEST.json')
    if sha(run / 'RUN_MANIFEST.json') != (run / 'RUN_MANIFEST.sha256').read_text().strip():
        raise ValueError('Manifest changed')
    for name, digest in read_json(run / 'RUN_AUDIT_SEAL.json')['sha256'].items():
        if sha(run / name) != digest:
            raise ValueError('Pre-scored audit seal changed: ' + name)
    for name, digest in read_json(run / 'QUALIFICATION_REVIEW.json')['evidence'].items():
        # Final restoration replaces the live status file; the reviewed
        # qualification checkpoint is retained byte-for-byte separately.
        path = run / ('inspection/qualification-restoration.json' if name == 'restoration.json' else name)
        if sha(path) != digest:
            raise ValueError('Qualification evidence changed: ' + name)
    for task in plan:
        folder = run / 'attempts' / task['attempt_id']
        body = read_json(folder / 'request.json')
        r.validate_body(body, task['arm'], binding['config'])
        if fingerprint(body) != manifest['scored_requests'][task['attempt_id']]['request_sha256']:
            raise ValueError('Dispatched payload differs from manifest')
        saved = read_json(folder / 'outcome.json')
        observed_input = (saved.get('usage') or {}).get('prompt_tokens', (saved.get('tensorfold') or {}).get('prompt'))
        if observed_input is not None and observed_input > r.MAX_INPUT:
            raise ValueError('Observed scored input exceeded the study limit')
        if saved['status'] != next(x['status'] for x in scored if x['id'] == task['attempt_id']):
            raise ValueError('Attempt state differs from saved outcome')
    protected = read_json(run / 'protected-files.json')
    intentional = []
    for name, digest in protected.items():
        path = ROOT / name
        if not path.is_file():
            raise ValueError('Protected file missing: ' + name)
        current = sha(path)
        if current != digest:
            if name != 'probe/local_model.py' or current != binding['code'][name]:
                raise ValueError('Unexpected change to protected work: ' + name)
            intentional.append({'path': name, 'before': digest, 'after': current,
                                'reason': 'Allow the explicitly requested 7200-second simple_chapter transport bound'})
    ledger = r.ledger(run)
    entries = ledger.read()['reservations']
    ids = [x['generation_id'] for x in entries if x.get('generation_id')]
    if len(ids) != len(set(ids)):
        raise ValueError('Repeated provider generation ID')
    hosted = [x for x in state['attempts'] if x['arm'] == 'hosted_fp8']
    if len(entries) != len(hosted) or len(hosted) > 38:
        raise ValueError('Hosted attempt/ledger mismatch')
    restoration = read_json(run / 'restoration.json')
    if len(restoration['containers']) != 4 or not all(x['passed'] for x in restoration['containers']):
        raise ValueError('Restoration evidence incomplete')
    record = {'passed': True, 'scored_attempts': 64, 'generation_attempts': len(state['attempts']),
              'qualification_by_arm': {a: sum(x['phase'] == 'qualification' and x['arm'] == a
                                            for x in state['attempts']) for a in r.ARMS},
              'hosted_attempts': len(hosted), 'unique_hosted_generation_ids': len(ids),
              'protected_files_checked': len(protected), 'intentional_changes': intentional,
              'manifest_and_pre_scored_audit_seals_verified': True,
              'all_scored_requests_match_manifest': True, 'restoration': restoration,
              'billing': ledger.summary()}
    atomic_json(run / 'final-verification.json', record)
    print(json.dumps(record, indent=2))
    return record


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def metrics(run, destination):
    scores = read_json(run / 'grading/scores.json')
    if sha(run / 'grading/scores.json') != (run / 'grading/scores.sha256').read_text().strip():
        raise ValueError('Masked grades not locked')
    mapping = read_json(run / 'grading/identity-map.json')
    state = read_json(run / 'state.json')
    attempts = {x['id']: x for x in state['attempts']}
    billing_path = run / 'inspection/completion-audit-20261117/billing-verification.json'
    billed = ({x['reservation']: x['fresh_billing']['total_cost']
               for x in read_json(billing_path)['records'] if x.get('fresh_billing')}
              if billing_path.exists() else {})
    billing = read_json(run / 'billing.json') if (run / 'billing.json').exists() else {'reservations': []}
    holds = {x['id']: x['reserved_usd'] for x in billing['reservations'] if 'actual_cost_usd' not in x}
    interruptions = sorted((read_json(p) for p in (run / 'inspection').rglob('resume-intent.json')),
                           key=lambda x: x['at'])
    rows, criteria = [], []
    for masked, task in mapping.items():
        folder = run / 'attempts' / task['attempt_id']
        outcome = read_json(folder / 'outcome.json')
        grade = scores[masked]
        if not outcome['usable_final'] and any(grade['criteria']):
            raise ValueError('Missing final answer must receive zero practical credit')
        numerical_path = run / 'grading/masked' / masked / 'numerical.json'
        numerical = read_json(numerical_path) if numerical_path.exists() else {}
        usage, native = outcome.get('usage') or {}, outcome.get('tensorfold') or {}
        transport_path = folder / 'transport.json'
        if not transport_path.exists():
            transport_path = folder / 'transport-evidence.json'
        transport = read_json(transport_path) if transport_path.exists() else {}
        metadata = outcome.get('metadata') or {}
        dispatched_at = attempts[task['attempt_id']].get('dispatched_at')
        reservation = attempts[task['attempt_id']].get('billing_reservation')
        invocation = 1 + sum(dispatched_at is not None and dispatched_at >= event['at']
                             for event in interruptions)
        row = {**task, 'masked_id': masked, 'score': sum(grade['criteria']) * 5,
               'usable': outcome['usable_final'], 'status': outcome['status'],
               'finish_reason': outcome.get('finish_reason'), 'elapsed_seconds': outcome['elapsed_seconds'],
               'http_status': transport.get('http_status'), 'transport_error': transport.get('error'),
               'outcome_error': outcome.get('error'),
               'returned_providers': ';'.join(metadata.get('providers', [])),
               'returned_models': ';'.join(metadata.get('models', [])),
               'first_delta_after_headers_seconds': (outcome.get('metadata') or {}).get('first_stream_token_seconds_after_headers'),
               'native_reported_ttft_seconds': native.get('ttft_s'),
               'prompt_tokens': usage.get('prompt_tokens', native.get('prompt')),
               'completion_tokens': usage.get('completion_tokens', native.get('completion')),
               'reasoning_tokens': outcome.get('reasoning_tokens'), 'cost_usd': usage.get('cost'),
               'verified_generation_cost_usd': billed.get(reservation),
               'unresolved_reservation_usd': holds.get(reservation, '0'),
               'dispatched_at': dispatched_at, 'finished_at': outcome.get('finished_at'),
               'invocation': invocation,
               'cached_tokens': usage.get('prompt_tokens_details', {}).get('cached_tokens', native.get('cached')),
               'code_execution_category': numerical.get('category'),
               'code_checks_passed': numerical.get('checks', {}).get('passed'),
               'code_checks_total': numerical.get('checks', {}).get('total'),
               'contested': grade.get('contested', False), 'notes': grade['notes']}
        rows.append(row)
        for i, score in enumerate(grade['criteria'], 1):
            criteria.append({'attempt_id': task['attempt_id'], 'masked_id': masked, 'base_id': task['base_id'],
                             'condition_id': task['condition_id'], 'arm': task['arm'], 'repetition': task['repetition'],
                             'criterion': i, 'points': score,
                             'notes': grade.get('criterion_notes', [grade['notes']] * 5)[i-1]})
    if len(rows) != 64:
        raise ValueError('Complete result needs 64 scored terminal attempts')

    def balanced(subset):
        condition, base, family = defaultdict(list), defaultdict(list), defaultdict(list)
        for row in subset:
            condition[(row['family'], row['base_id'], row['condition_id'])].append(row['score'])
        for (fam, task, _), values in condition.items():
            base[(fam, task)].append(statistics.mean(values))
        for (fam, _), values in base.items():
            family[fam].append(statistics.mean(values))
        return {fam: statistics.mean(values) for fam, values in family.items()}

    result = {}
    for arm in r.ARMS:
        subset = [x for x in rows if x['arm'] == arm]
        families = balanced(subset)
        delivered = balanced([x for x in subset if x['usable']])
        result[arm] = {'families': families, 'overall': statistics.mean(families.values()),
                       'conditional_families': delivered,
                       'conditional_overall': statistics.mean(delivered.values()) if delivered else None,
                       'delivered': sum(x['usable'] for x in subset), 'total': len(subset),
                       'strict_successes': sum(x['status'] == 'success' for x in subset),
                       'delivery_rate': sum(x['usable'] for x in subset) / len(subset),
                       'family_coverage': {fam: {
                           'delivered': sum(x['usable'] for x in subset if x['family'] == fam),
                           'total': sum(x['family'] == fam for x in subset)} for fam in families},
                       'status_counts': dict(Counter(x['status'] for x in subset)),
                       'repetitions': {str(rep): balanced([x for x in subset if x['repetition'] == rep]) for rep in (1, 2)},
                       'conditional_repetitions': {str(rep): balanced([x for x in subset
                           if x['repetition'] == rep and x['usable']]) for rep in (1, 2)}}
    paired = []
    for base in sorted({x['base_id'] for x in rows}):
        for rep in (1, 2):
            by_arm = {arm: statistics.mean(x['score'] for x in rows
                if x['arm'] == arm and x['base_id'] == base and x['repetition'] == rep) for arm in r.ARMS}
            paired.append({'base_id': base, 'repetition': rep, **by_arm,
                           'hosted_minus_local': by_arm[r.ARMS[1]] - by_arm[r.ARMS[0]]})
    task_means = [statistics.mean(x['hosted_minus_local'] for x in paired if x['base_id'] == base)
                  for base in sorted({x['base_id'] for x in rows})]
    result['base_task_wins_ties_losses_hosted'] = {
        'wins': sum(x > 0 for x in task_means), 'ties': sum(x == 0 for x in task_means),
        'losses': sum(x < 0 for x in task_means), 'independent_base_task_clusters': 12}
    sensitivity = {}
    for arm in r.ARMS:
        bounds = {}
        for direction in ('lower', 'upper'):
            revised = []
            for row in rows:
                if row['arm'] != arm:
                    continue
                grade = scores[row['masked_id']]
                alternative = sum(grade.get('alternative_criteria', grade['criteria'])) * 5
                chosen = min(row['score'], alternative) if direction == 'lower' else max(row['score'], alternative)
                revised.append(dict(row, score=chosen))
            family_values = balanced(revised)
            delivered_values = balanced([x for x in revised if x['usable']])
            bounds[direction] = {'families': family_values, 'overall': statistics.mean(family_values.values()),
                                 'conditional_families': delivered_values,
                                 'conditional_overall': statistics.mean(delivered_values.values()) if delivered_values else None}
        sensitivity[arm] = bounds
    result['contested_grade_sensitivity'] = sensitivity
    result['contested_attempts'] = [{k: row[k] for k in ('attempt_id', 'masked_id', 'arm', 'score', 'notes')}
                                    for row in rows if row['contested']]
    result['timing'] = {
        'interpretation': 'Per-request timings exclude outage/reload gaps. Invocations and caches are not continuous; '
                          'do not interpret these as a controlled hardware or cold-cache benchmark.',
        'interruptions': interruptions,
        'by_arm_and_invocation': [{
            'arm': arm, 'invocation': invocation,
            'attempts': len(subset := [x for x in rows if x['arm'] == arm and x['invocation'] == invocation]),
            'median_elapsed_seconds': statistics.median(x['elapsed_seconds'] for x in subset),
            'sum_elapsed_seconds': sum(x['elapsed_seconds'] for x in subset)}
            for arm in r.ARMS for invocation in sorted({x['invocation'] for x in rows if x['arm'] == arm})]}
    result['cost_columns'] = {'cost_usd': 'Original stream/outcome-reported amount; not added to the verified amount.',
                              'verified_generation_cost_usd': 'Fresh generation billing record, when an ID is available.',
                              'unresolved_reservation_usd': 'Retained maximum liability, not an additional settled charge.'}
    controls = []
    for arm in r.ARMS:
        for base, control, treatment in [('L01', 'focused', 'long'), ('L02', 'focused', 'long'),
                                         ('V01', 'text', 'image'), ('V02', 'text', 'image')]:
            for rep in (1, 2):
                values = {suffix: next(x['score'] for x in rows if x['arm'] == arm and x['repetition'] == rep
                          and x['condition_id'] == base + '_' + suffix) for suffix in (control, treatment)}
                controls.append({'arm': arm, 'base_id': base, 'repetition': rep,
                    'control': control, 'treatment': treatment, 'control_score': values[control],
                    'treatment_score': values[treatment], 'difference': values[treatment] - values[control]})
    write_csv(destination / 'per-attempt.csv', rows)
    write_csv(destination / 'per-criterion.csv', criteria)
    condition_rows = []
    for arm in r.ARMS:
        for condition in sorted({x['condition_id'] for x in rows}):
            subset = [x for x in rows if x['arm'] == arm and x['condition_id'] == condition]
            usable = [x['score'] for x in subset if x['usable']]
            condition_rows.append({'arm': arm, 'family': subset[0]['family'], 'base_id': subset[0]['base_id'],
                'condition_id': condition, 'practical_score': statistics.mean(x['score'] for x in subset),
                'conditional_quality_score': statistics.mean(usable) if usable else None,
                'delivered': len(usable), 'attempts': len(subset)})
    task_rows = []
    for arm in r.ARMS:
        for base in sorted({x['base_id'] for x in rows}):
            subset = [x for x in condition_rows if x['arm'] == arm and x['base_id'] == base]
            usable = [x['conditional_quality_score'] for x in subset if x['conditional_quality_score'] is not None]
            task_rows.append({'arm': arm, 'family': subset[0]['family'], 'base_id': base,
                'practical_score': statistics.mean(x['practical_score'] for x in subset),
                'conditional_quality_score': statistics.mean(usable) if usable else None,
                'delivered': sum(x['delivered'] for x in subset), 'attempts': sum(x['attempts'] for x in subset),
                'conditions_with_delivery': len(usable), 'conditions': len(subset)})
    write_csv(destination / 'per-condition.csv', condition_rows)
    write_csv(destination / 'per-task.csv', task_rows)
    write_csv(destination / 'paired-differences.csv', paired)
    write_csv(destination / 'control-differences.csv', controls)
    atomic_json(destination / 'statistics.json', result)
    return result


def package(run, destination):
    included = {}

    def add(path, name):
        if not path.is_file() or path.is_symlink():
            raise ValueError('Missing/nonregular inspection input: ' + str(path))
        if name in included:
            raise ValueError('Duplicate archive member')
        included[name] = path

    for name in ('REPORT.md', 'BUDGET_RECONCILIATION.md', 'statistics.json', 'per-attempt.csv', 'per-criterion.csv',
                 'per-condition.csv', 'per-task.csv',
                 'paired-differences.csv', 'control-differences.csv'):
        if (destination / name).exists():
            add(destination / name, name)
    for name in ('CONFIG_AUDIT.md', 'RUN_STATUS.md', 'CHECKPOINT.md', 'route-blocker.json',
                 'RUN_MANIFEST.json', 'RUN_MANIFEST.sha256',
                 'binding.json', 'authorization.json', 'cost-plan.json', 'plan.json', 'QUALIFICATION_PLAN.json',
                 'QUALIFICATION_REVIEW.json', 'RUN_AUDIT_SEAL.json', 'offline-material-review.json', 'pack-copy.json',
                 'pack-verification.json', 'numerical-self-test.json', 'sandbox-self-test.json',
                 'state.json', 'billing.json', 'restoration.json', 'final-verification.json',
                 'full-tests.log', 'stream-adapter-tests.log', 'metrics-validation.json', 'reporting-validation.json'):
        if (run / name).exists():
            add(run / name, 'run/' + name)
    for directory in ('pack', 'grading', 'billing', 'preparation-history', 'reconciliations', 'checkpoints'):
        for path in sorted((run / directory).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                add(path, 'run/' + str(path.relative_to(run)))
    for i, adjustment in enumerate(read_json(run / 'binding.json')['config']['adjustments'], 1):
        add(Path(adjustment), 'billing-reconciliation/' + str(i) + '.json')
    previews = destination / 'request-previews'
    previews.mkdir(exist_ok=True)
    streams = []
    for attempt in sorted((run / 'attempts').glob('*')):
        if not attempt.is_dir():
            continue
        for name in ('answer.txt', 'outcome.json', 'tokenization.json', 'transport.json', 'transport-evidence.json'):
            if (attempt / name).exists():
                add(attempt / name, 'attempts/' + attempt.name + '/' + name)
        if (attempt / 'request.json').exists():
            body = read_json(attempt / 'request.json')
            messages = body.pop('messages')
            body['public_messages_sha256'] = r.packets(run / 'pack').messages_sha256(messages)
            body['messages_reconstruction'] = ('pack/tools/packets.py with condition_id from run/plan.json; '
                                               'qualification uses the separate qualification-inputs files')
            body['full_request_sha256'] = sha(attempt / 'request.json')
            atomic_json(previews / (attempt.name + '.json'), body)
            add(previews / (attempt.name + '.json'), 'request-previews/' + attempt.name + '.json')
        for path in attempt.rglob('*'):
            if path.is_file() and path.name in ('response.raw', 'stream-events.jsonl', 'reasoning.txt', 'response.json', 'response.assembled.json'):
                streams.append({'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size})
    for path in sorted((run / 'qualification-inputs').glob('*')):
        if path.is_file():
            if path.name in ('long.json', 'image.json'):
                preview = previews / ('qualification-' + path.stem + '-reconstruction.json')
                atomic_json(preview, qualification_recipe(run, path.stem))
                add(preview, 'run/qualification-inputs/' + path.stem + '-reconstruction.json')
            else:
                add(path, 'run/qualification-inputs/' + path.name)
    for path in sorted((run / 'inspection').rglob('*')):
        if path.is_file() and path.suffix in ('.json', '.zig', '.log', '.md', '.py', '.txt'):
            # Process command lines and raw full Docker environments stay local.
            if 'inspect.json' in path.name or path.name in ('initial-services.json', 'restore-plan.json'):
                continue
            add(path, 'run/inspection/' + str(path.relative_to(run / 'inspection')))
    implementation = set(read_json(run / 'binding.json')['code']) | {
        'scripts/deepseek_research_report.py', 'scripts/deepseek_research_account.py',
        'scripts/deepseek_research_inspect.py', 'tests/test_deepseek_research.py',
        'tests/test_deepseek_research_report.py'}
    for name in sorted(implementation):
        add(ROOT / name, 'implementation/' + name)
    atomic_json(destination / 'RAW-STREAM-INDEX.json', streams)
    add(destination / 'RAW-STREAM-INDEX.json', 'RAW-STREAM-INDEX.json')
    policy = destination / 'INSPECTION-CONTENTS.md'
    policy.write_text('Source TeX and scientific images appear once under run/pack/public. '
                      'The exact scored public packets reconstruct with run/pack/tools/packets.py; '
                      'run_plan.json binds their hashes across both arms/repetitions. Expanded duplicate '
                      'requests/base64, reasoning and wire streams stay in the run and are indexed with hashes. '
                      'Qualification long/image inputs have verified reconstruction recipes so their source/image bytes are not repeated. '
                      'All final answers, numerical checks, masked grades and criterion tables are included. '
                      'No key or environment file is included. Full Docker environments/process snapshots '
                      'remain local. This is an inspection package, not a full run backup.\n')
    add(policy, policy.name)
    verify_no_runtime_secret(included.values(), r.cloud.read_key())
    manifest = {name: sha(path) for name, path in included.items()}
    archive = ROOT / 'results/inspection' / (run.name + '.zip')
    archive.parent.mkdir(exist_ok=True)
    if archive.exists():
        raise ValueError('Existing inspection ZIP is immutable')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, path in included.items():
            z.write(path, name)
        z.writestr('ARCHIVE-HASHES.json', json.dumps(manifest, indent=2) + '\n')
    with tempfile.TemporaryDirectory(prefix='research-zip-verify-') as temp:
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:
                raise ValueError('ZIP CRC failed')
            for name in z.namelist():
                if Path(name).is_absolute() or '..' in Path(name).parts:
                    raise ValueError('Unsafe archive member')
            z.extractall(temp)
        for name, expected in manifest.items():
            if sha(Path(temp) / name) != expected:
                raise ValueError('Extracted payload mismatch: ' + name)
    record = {'path': str(archive), 'sha256': sha(archive), 'bytes': archive.stat().st_size,
              'payloads_verified': len(manifest), 'crc_and_extraction_hashes_passed': True,
              'all_bound_implementation_files_included': True, 'runtime_credential_absent': True}
    atomic_json(destination / 'INSPECTION.json', record)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['refresh-mask', 'verify', 'metrics', 'package'])
    p.add_argument('--run', required=True, type=Path)
    p.add_argument('--destination', required=True, type=Path)
    args = p.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    {'refresh-mask': refresh_mask, 'verify': verify_finished, 'metrics': metrics,
     'package': package}[args.command](args.run.resolve(), args.destination.resolve())
