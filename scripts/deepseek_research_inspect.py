#!/usr/bin/env python3
"""Read-only deployment and public metadata snapshot for the bounded comparison."""
import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from probe.common import atomic_json, sha
from probe.experiment import now
from probe import cloud_critic as cloud, kimi_escalation as kimi
from scripts import cookbook_quantity_trial as runtime


def inspect_run(run):
    out = run / 'inspection'
    out.mkdir(exist_ok=True)
    helper = runtime.owned_deepseek()
    snapshot = {'at': now(), 'nodes': {}, 'generation_calls': 0}
    for rank in (0, 1):
        glm = runtime.inspect('glm53-flash-tf', rank)
        ds = helper.inspect(rank)
        helper.verify_stopped(ds, rank)
        node = {'containers': {}, 'processes': runtime.cmd(['ps', '-eo', 'pid,ppid,comm,args'], rank),
                'running_containers': runtime.cmd(['docker', 'ps', '--format', '{{.ID}} {{.Names}}'], rank),
                'boot_id': runtime.cmd(['cat', '/proc/sys/kernel/random/boot_id'], rank).strip()}
        for kind, value in [('glm', glm), ('deepseek', ds)]:
            atomic_json(out / f'rank{rank}-{kind}-inspect.json', value)
            node['containers'][kind] = {'id': value['Id'], 'running': value['State']['Running'],
                'config_hash': runtime.config_id(value), 'image': value['Image']}
        snapshot['nodes'][str(rank)] = node
    snapshot['glm_health'] = runtime.http(8888, '/health')
    snapshot['glm_models'] = runtime.http(8888, '/v1/models')
    snapshot['resources'] = runtime.resources()
    runtime.guard_glm_ownership(run)
    atomic_json(out / 'initial-services.json', snapshot)
    atomic_json(out / 'restore-plan.json', {
        'observed': snapshot['nodes'], 'generation_calls_for_health': 0,
        'rule': 'Before mutation save immutable IDs/configuration hashes and handoff intent. '
                'Stop only verified idle owned GLM; start existing unchanged DS pair. '
                'In finally/signals stop only owned DS after idle; restart original GLM peer then head. '
                'Verify both original hashes and non-generating model discovery/health. '
                'Never restore a changed/substituted deployment or interrupt another owner.'})
    # Copy installed source from the stopped, immutable container; never start it.
    container = snapshot['nodes']['0']['containers']['deepseek']['id']
    paths = runtime.cmd(['docker', 'export', '--help'])  # no export/mutation
    # Locate using the prior run's installed-source provenance rather than assume a host checkout.
    image = runtime.cmd(['docker', 'image', 'inspect', snapshot['nodes']['0']['containers']['deepseek']['image']])
    atomic_json(out / 'deepseek-image.json', json.loads(image))
    for name in ['config.json', 'README.md', 'tokenizer_config.json']:
        source = Path('/home/mdi/models/deepseek/flash17-exl3-2.8bpw') / name
        (out / ('local-' + name)).write_bytes(source.read_bytes())
    urls = {
        'endpoints.json': 'https://openrouter.ai/api/v1/models/deepseek/deepseek-v4.1-flash-1017/endpoints',
        'models.json': 'https://openrouter.ai/api/v1/models',
        'zdr.json': 'https://openrouter.ai/api/v1/endpoints/zdr',
        'model-card.md': 'https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017/raw/main/README.md',
        'reference-model.py': 'https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017/raw/main/inference/model.py',
        'openrouter-parameters.html': 'https://openrouter.ai/docs/api_reference/parameters',
        'deepinfra-reasoning.html': 'https://docs.deepinfra.com/chat/reasoning',
        'deepinfra-vision.html': 'https://docs.deepinfra.com/chat/vision',
    }
    sources = {}
    for name, url in urls.items():
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                raw = response.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise ValueError('metadata byte limit')
            (out / name).write_bytes(raw)
            sources[name] = {'url': url, 'at': now(), 'sha256': sha(out / name)}
        except Exception as exc:
            sources[name] = {'url': url, 'error': str(exc), 'at': now()}
    atomic_json(out / 'sources.json', sources)
    client = object.__new__(cloud.CloudClient)
    client._key = cloud.read_key()
    client.config = {}
    client.timeout = 30
    allowance = client.control('/key', None, private=True)['data']
    history = kimi.history_snapshot(ROOT, exclude=(run,))
    atomic_json(out / 'history.json', history)
    atomic_json(out / 'allowance.json', {
        key: allowance.get(key) for key in ('limit', 'limit_remaining', 'limit_reset', 'usage')})
    print(json.dumps({'at': snapshot['at'], 'service_snapshot': str(out),
        'generation_calls': 0, 'history': history['summary'],
        'allowance': {key: allowance.get(key) for key in ('limit', 'limit_remaining', 'limit_reset')},
        'source_errors': {k: v for k, v in sources.items() if 'error' in v}}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    inspect_run(parser.parse_args().run.resolve())
