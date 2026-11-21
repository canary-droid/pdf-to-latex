#!/usr/bin/env python3
"""Read-only account/key checks. Never purchases credits or prints a credential."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from probe import cloud_critic as cloud
from probe.common import atomic_json
from probe.experiment import now


class AccountReader(cloud.CloudClient):
    def __init__(self):
        self._key = cloud.read_key()
        self.config = {}
        self.timeout = 30

    def _control_paths(self):
        return ('/key', '/credits')


def inspect(run):
    c = AccountReader()
    result = {'at': now(), 'generations': 0, 'mutations': 0}
    for path in ('/key', '/credits'):
        status, raw, elapsed = c._http('GET', path)
        data = json.loads(raw)
        # Only non-identifying financial fields enter persisted/displayed evidence.
        allowed = ('limit', 'limit_remaining', 'limit_reset', 'usage', 'usage_daily',
                   'usage_weekly', 'usage_monthly', 'is_management_key',
                   'include_byok_in_limit', 'total_credits', 'total_usage')
        result[path] = {'status': status, 'elapsed_seconds': elapsed,
                       'data': {k: v for k, v in data.get('data', {}).items() if k in allowed}}
        if status != 200:
            result[path]['error'] = data.get('error', {})
    atomic_json(run / 'inspection' / 'account-current.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True, type=Path)
    inspect(p.parse_args().run.resolve())
