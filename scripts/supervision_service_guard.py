"""Trusted transient-service owner watchdog; stdlib only, no candidate imports.

Arguments come exclusively from the fixed controller, never from repair output.
When the controller disappears, this main process exits and systemd's mandatory
KillMode=control-group removes every descendant, including detached children.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def owner_identity(pid):
    try:
        fields = (Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()
        if fields[0] == 'Z': return None
        return {'pid': int(pid), 'start_ticks': fields[19],
                'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    except (OSError, ValueError): return None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--owner', required=True)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args(); owner = json.loads(a.owner)
    command = a.command[1:] if a.command and a.command[0] == '--' else a.command
    if not command or not isinstance(owner, dict) or owner_identity(owner.get('pid')) != owner:
        raise SystemExit('Controller identity not alive; command not executed')
    child = subprocess.Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr,
                             close_fds=True)
    while child.poll() is None:
        if owner_identity(owner['pid']) != owner:
            # Return immediately; the service manager owns complete cleanup.
            raise SystemExit(125)
        time.sleep(.1)
    raise SystemExit(child.returncode)


if __name__ == '__main__': main()
