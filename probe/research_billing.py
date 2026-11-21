"""Evidence-bound accounting adjustments, without rewriting historical attempts."""
import copy
from decimal import Decimal
from pathlib import Path
from .common import read_json, sha
from .batch_review import IntegrityError
from . import cloud_critic as cloud, kimi_escalation as kimi


def no_capacity_rejection(raw, error, reservation):
    """Narrow completed admission refusal; never infer zero from an empty answer."""
    e = raw.get('error', {})
    m = e.get('metadata', {})
    return (e.get('code') == 429 and m.get('provider_error_code') == 'no_asap_capacity'
            and m.get('limit_source') == 'upstream_provider_shared_pool'
            and m.get('provider_name') == 'Sail Research'
            and not raw.get('id') and not raw.get('choices') and not raw.get('usage')
            and not reservation.get('generation_id') and 'actual_cost_usd' not in reservation
            and error.get('message') == 'OpenRouter HTTP 429; no retry'
            and error.get('cloud_reservation') == reservation['id'])


def adjusted_history(root, adjustments, exclude=()):
    """Apply sealed zero-charge admission refusals once by original reservation ID."""
    history = kimi.history_snapshot(root, exclude=exclude)
    history = copy.deepcopy(history)
    releases = []
    seen = set()
    for path in adjustments:
        record = read_json(path)
        if record['kind'] != 'documented_no_capacity_rejections_v1':
            raise IntegrityError('Unsupported accounting adjustment')
        for item in record['releases']:
            identity = (item['origin_binding'], item['reservation_id'])
            if identity in seen:
                raise IntegrityError('Duplicate release')
            seen.add(identity)
            for filename, digest in item['evidence'].items():
                if sha(Path(filename)) != digest:
                    raise IntegrityError('Reconciliation evidence changed')
            matches = [x for x in history['charges'] if
                       (x['origin_binding'], x['reservation']['id']) == identity]
            if len(matches) != 1:
                raise IntegrityError('Reconciliation identity missing or ambiguous')
            old = matches[0]['reservation']
            if 'actual_cost_usd' in old:
                if cloud.decimal(old['actual_cost_usd']) != 0:
                    raise IntegrityError('Released rejection now has a billed charge')
                continue  # already settled, never subtract twice
            if old['request_sha256'] != item['request_sha256'] or old['reserved_usd'] != item['released_usd']:
                raise IntegrityError('Reservation changed')
            if not no_capacity_rejection(read_json(item['response_path']),
                                         read_json(item['error_path']), old):
                raise IntegrityError('Not a proven admission refusal')
            old.update(actual_cost_usd='0', reconciliation=str(path), disposition='rejected_before_generation')
            releases.append(item)
    unresolved = [x for x in history['charges'] if 'actual_cost_usd' not in x['reservation']]
    history['summary'].update(
        actual_reported_usd=str(sum((cloud.decimal(x['reservation'].get('actual_cost_usd', 0))
                                    for x in history['charges']), Decimal(0))),
        unresolved_reserved_usd=str(sum((cloud.decimal(x['reservation']['reserved_usd'])
                                        for x in unresolved), Decimal(0))),
        unresolved_charge_ids=[x['origin_binding'] + '|' + x['reservation']['id'] for x in unresolved],
        released_reservation_usd=str(sum((cloud.decimal(x['released_usd']) for x in releases), Decimal(0))),
        meaning='Deduplicated historical spending plus evidence-bound releases. Live key/account balances '
                'already subtract settled charges; subtract only remaining uncertain liabilities from them.')
    history['adjustments'] = {str(p): sha(Path(p)) for p in adjustments}
    return history


def available(key, credits, uncertain):
    """Balances are remaining funds; do not subtract lifetime usage a second time."""
    balance = cloud.decimal(credits['total_credits']) - cloud.decimal(credits['total_usage'])
    remaining = key.get('limit_remaining')
    bound = balance if remaining is None else min(balance, cloud.decimal(remaining))
    return max(Decimal(0), bound - cloud.decimal(uncertain))
