"""Frozen public packets, bounded accounting and durable comparison attempts.

This separate diagnostic never changes production selection or cloud routing.
"""
import copy
import importlib.util
import json
import os
import re
import socket
import threading
import time
from decimal import Decimal, ROUND_CEILING
from pathlib import Path

from .common import atomic_json, read_json, sha, fingerprint, writer_lock
from .batch_review import IdentityError, IntegrityError
from .experiment import now
from . import cloud_critic as cloud, research_billing
from .chapter_stream import ChapterStream, DurableText
from .local_model import LocalClient, ProbeError, _strict_json

MODEL = 'deepseek/deepseek-v4.1-flash-1017'
LOCAL_MODEL = 'DeepSeek-V4.1-Flash-TF'
LOCAL_URL = 'http://127.0.0.1:8894/v1'
TAG = 'deepinfra/fp8'
ARMS = ('local_exl3', 'hosted_fp8')
CAPS = (262144, 131072, 65536)
TIMEOUT = 7200
MAX_INPUT = 196608
MAX_CALLS = 76
WINDOW = 18 * 3600
ROOT = Path(__file__).resolve().parents[1]


def packets(pack):
    spec = importlib.util.spec_from_file_location('research_public_packets', Path(pack) / 'tools/packets.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_pack(pack):
    pack = Path(pack)
    manifest = read_json(pack / 'manifest.json')
    for name, digest in manifest['sha256'].items():
        if sha(pack / name) != digest:
            raise IntegrityError('Pack changed: ' + name)
    module = packets(pack)
    plan = read_json(pack / 'run_plan.json')
    if plan != module.run_plan() or len(plan) != 64 or len({x['attempt_id'] for x in plan}) != 64:
        raise IntegrityError('Fixed schedule changed')
    return module, plan


def provider(rates):
    return {'only': [TAG], 'order': [TAG], 'allow_fallbacks': False,
            'require_parameters': True, 'data_collection': 'deny', 'zdr': True,
            'max_price': {k: float(cloud.decimal(rates[k]) * 1000000) for k in ('prompt', 'completion')}}


def body_for(messages, arm, cap, seed, config):
    if cap not in CAPS or arm not in ARMS:
        raise IntegrityError('Undeclared arm or output allowance')
    body = {'messages': copy.deepcopy(messages), 'model': LOCAL_MODEL if arm == ARMS[0] else MODEL,
            'max_tokens': cap, 'temperature': 1.0, 'top_p': 1.0, 'top_k': 0, 'min_p': 0.0,
            'stream': True, 'seed': seed}
    if arm == ARMS[0]:
        # Installed native sampler has no penalty terms; min_p request is ignored,
        # with a verified zero default. Native EOS tokens remain enabled.
        body['reasoning_effort'] = 'high'
    else:
        body.update(reasoning={'effort': 'high', 'exclude': False}, provider=provider(config['rates']),
                    plugins=[], frequency_penalty=0.0, presence_penalty=0.0,
                    repetition_penalty=1.0, stream_options={'include_usage': True})
    return body


def validate_body(body, arm, config):
    expected = body_for(body['messages'], arm, body['max_tokens'], body['seed'], config)
    if body != expected:
        raise IntegrityError('Request differs from frozen transport controls')
    if len(body['messages']) != 2 or [x['role'] for x in body['messages']] != ['system', 'user']:
        raise IntegrityError('Conversation is not fresh')


def endpoint(metadata, config=None):
    data = metadata['endpoints']['data']
    matches = [e for e in data['endpoints'] if e.get('tag') == TAG]
    if data['id'] != MODEL or len(matches) != 1:
        raise IdentityError('Exact checkpoint/route absent')
    e = matches[0]
    if e.get('model_id') != MODEL or e.get('provider_name') != 'DeepInfra' or e.get('quantization') != 'fp8' or e.get('status') != 0:
        raise IdentityError('Pinned hosted identity/status changed')
    core = {'temperature', 'top_p', 'top_k', 'min_p', 'reasoning', 'max_tokens', 'seed',
            'frequency_penalty', 'presence_penalty', 'repetition_penalty'}
    if not core <= set(e['supported_parameters']):
        raise cloud.AdmissionError('Required controls unavailable; no silent omission')
    if 'image' not in data['architecture']['input_modalities']:
        raise cloud.AdmissionError('Route lacks images')
    if 'high' not in metadata['model']['reasoning']['supported_efforts']:
        raise cloud.AdmissionError('High unavailable')
    if not any(z.get('model_id') == MODEL and z.get('tag') == TAG and z.get('safety_retention') is False
               for z in metadata['zdr']['data']):
        raise cloud.AdmissionError('Exact private route unavailable')
    for k, v in e['pricing'].items():
        if k not in ('prompt', 'completion', 'input_cache_read', 'discount') and cloud.decimal(v) != 0:
            raise cloud.AdmissionError('Unaccounted price component')
    if config:
        if e['context_length'] != config['context_length']:
            raise cloud.AdmissionError('Hosted context changed')
        if any(cloud.decimal(e['pricing'][k]) > cloud.decimal(v) for k, v in config['rates'].items()):
            raise cloud.AdmissionError('Hosted price increased')
    return e


def metadata_from(folder):
    folder = Path(folder)
    return {'endpoints': read_json(folder / 'endpoints.json'), 'zdr': read_json(folder / 'zdr.json'),
            'model': next(x for x in read_json(folder / 'models.json')['data'] if x['id'] == MODEL)}


def input_bound(config, body):
    # Reserve ALL admissible context, including unobservable hosted image/framing
    # expansion. This is a billing bound, not the measured study input limit.
    return config['context_length'] - body['max_tokens']


def cost_bound(config, body):
    return (cloud.decimal(config['rates']['prompt']) * input_bound(config, body)
            + cloud.decimal(config['rates']['completion']) * body['max_tokens']).quantize(
                Decimal('.000000001'), rounding=ROUND_CEILING)


def ledger(run, create=False):
    c = read_json(Path(run) / 'binding.json')['config']
    return cloud.Ledger(run, create=create, rates=c['rates'],
                        token_estimator=lambda b: input_bound(c, b),
                        cost_estimator=lambda b: cost_bound(c, b))


def save(run, state):
    atomic_json(Path(run) / 'state.json', state)


def verify(run):
    run = Path(run)
    binding = read_json(run / 'binding.json')
    for name, digest in binding['files'].items():
        if sha(run / name) != digest:
            raise IntegrityError('Frozen input changed: ' + name)
    for name, digest in binding['code'].items():
        if sha(ROOT / name) != digest:
            raise IntegrityError('Bound implementation changed: ' + name)
    state = read_json(run / 'state.json')
    if len(state['attempts']) != len({a['id'] for a in state['attempts']}):
        raise IntegrityError('Duplicate attempt identity')
    for arm in ARMS:
        if sum(x['arm'] == arm and x['phase'] == 'qualification' for x in state['attempts']) > 6:
            raise IntegrityError('Qualification allowance exceeded')
        if sum(x['arm'] == arm and x['phase'] == 'scored' for x in state['attempts']) > 32:
            raise IntegrityError('Scored allowance exceeded')
    if len(state['attempts']) > MAX_CALLS:
        raise IntegrityError('Total allowance exceeded')
    return binding, state


class HostedStream(ChapterStream):
    """Normalize OpenRouter's usage trailer; retain original bytes in response.raw."""
    def event(self, raw):
        if raw == b'[DONE]':
            return super().event(raw)
        value = self.parse(raw.decode('utf-8'))
        if isinstance(value, dict):
            choices = value.get('choices')
            if isinstance(choices, list) and len(choices) == 1:
                choice = choices[0]
                delta = choice.get('delta', {})
                if isinstance(delta, dict):
                    # OpenRouter exposes reasoning under this field. Keep both
                    # in the parsed event; never duplicate reasoning_details.
                    if 'reasoning_content' not in delta and isinstance(delta.get('reasoning'), str):
                        delta['reasoning_content'] = delta['reasoning']
                    repeated = self.finish is not None and choice.get('finish_reason') == self.finish
                    empty = not any(delta.get(k) for k in ('content', 'reasoning', 'reasoning_content',
                                                           'reasoning_details', 'tool_calls', 'function_call'))
                    if repeated and empty and isinstance(value.get('usage'), dict):
                        choice['finish_reason'] = None
                        value['adapter_normalization'] = 'Repeated identical finish in empty usage trailer'
        return super().event(json.dumps(value, ensure_ascii=False).encode())


class HostedClient(cloud.CloudClient):
    """CloudClient TLS/credential/control/ledger plus durable SSE capture."""
    def __init__(self, run, key_reader=cloud.read_key):
        self.run = Path(run)
        self.config = read_json(self.run / 'binding.json')['config']
        self._key = key_reader()
        self.timeout = TIMEOUT
        self.ledger = ledger(run)

    def _control_paths(self):
        return ('/key', '/credits', '/models/' + MODEL + '/endpoints', '/models', '/endpoints/zdr')

    def admission(self, body, folder, remaining_calls=1):
        validate_body(body, ARMS[1], self.config)
        key = self.control('/key', None, private=True)['data']
        credits = self.control('/credits', None, private=True)['data']
        meta = {'endpoints': self.control('/models/' + MODEL + '/endpoints', folder / 'route'),
                'zdr': self.control('/endpoints/zdr', folder / 'zdr')}
        meta['model'] = next(x for x in self.control('/models', folder / 'models')['data'] if x['id'] == MODEL)
        e = endpoint(meta, self.config)
        if body['max_tokens'] > e['max_completion_tokens']:
            raise cloud.AdmissionError('Output allowance exceeds published route limit')
        history = research_billing.adjusted_history(ROOT, self.config['adjustments'], exclude=(self.run,))
        funds = research_billing.available(key, credits, history['summary']['unresolved_reserved_usd'])
        pending = cloud.decimal(self.ledger.summary()['unresolved_reserved_usd'])
        required = cost_bound(self.config, body) * remaining_calls
        if required + pending > funds or required + self.ledger.exposure(self.ledger.read()) > cloud.decimal(self.config['budget_usd']):
            raise cloud.AdmissionError('Whole remaining planned maximum exceeds key/account/experiment funds')
        record = {'at': now(), 'key_lifetime_limit_usd': key.get('limit'),
                  'key_lifetime_usage_usd': key.get('usage'), 'key_remaining_usd': key.get('limit_remaining'),
                  'account_credit_usd': str(cloud.decimal(credits['total_credits']) - cloud.decimal(credits['total_usage'])),
                  'historical_uncertain_usd': history['summary']['unresolved_reserved_usd'],
                  'available_before_own_holds_usd': str(funds), 'remaining_maximum_usd': str(required)}
        atomic_json(folder / 'admission.json', record)
        self.ledger.admit(body, funds)
        return funds

    def stream(self, body, folder):
        """One POST, absolute deadline including prefill; save before parsing."""
        conn = None
        transport_socket = None
        collector = None
        raw = None
        started = time.monotonic()
        record = {'started_at': now(), 'absolute_timeout_seconds': TIMEOUT}

        def expire():
            sock = (conn.sock if conn and conn.sock else transport_socket)
            if sock:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

        timer = threading.Timer(TIMEOUT, expire)
        timer.daemon = True
        try:
            conn = self._connection(TIMEOUT)
            timer.start()
            conn.connect()
            transport_socket = conn.sock
            conn.request('POST', '/api/v1/chat/completions',
                         body=json.dumps(body, ensure_ascii=False).encode(),
                         headers={'Authorization': 'Bearer ' + self._key, 'Content-Type': 'application/json',
                                  'Accept': 'text/event-stream', 'User-Agent': 'pdf2tex-research/1'})
            response = conn.getresponse()
            record['http_status'] = response.status
            is_sse = response.status == 200 and 'text/event-stream' in (response.getheader('Content-Type') or '')
            if is_sse:
                collector = HostedStream(folder, MODEL, _strict_json, self._key)
            else:
                raw = DurableText(folder / 'response.raw', self._key)
            size = 0
            while True:
                left = TIMEOUT - (time.monotonic() - started)
                if left <= 0:
                    raise TimeoutError('Absolute request deadline')
                if transport_socket:
                    transport_socket.settimeout(left)
                part = response.read1(65536)
                if not part:
                    break
                size += len(part)
                if size > 128 * 1024 * 1024:
                    raise ProbeError('Response byte limit')
                if collector:
                    collector.feed(part)
                    if collector.done:
                        break
                else:
                    raw.write(part)
                    raw.flush()
            if not is_sse:
                raise ProbeError('Hosted HTTP/stream error; raw response retained')
            result = collector.response()
            return result, record
        except Exception as exc:
            record['error'] = self._redact(str(exc))
            raise
        finally:
            timer.cancel()
            if conn:
                conn.close()
            if collector:
                collector.close()
            if raw:
                raw.close()
            record.update(finished_at=now(), elapsed_seconds=time.monotonic() - started)
            atomic_json(folder / 'transport.json', record)


def stream_metadata(folder):
    ids, providers, models = set(), set(), set()
    first = None
    for path in Path(folder).rglob('stream-events.jsonl'):
        for line in path.read_text().splitlines():
            event = json.loads(line)
            value = event['value']
            if value.get('id'):
                ids.add(value['id'])
            if value.get('provider'):
                providers.add(value['provider'])
            if value.get('model'):
                models.add(value['model'])
            for choice in value.get('choices', []):
                delta = choice.get('delta', {})
                if first is None and any(delta.get(k) for k in ('content', 'reasoning', 'reasoning_content', 'reasoning_details')):
                    first = event['elapsed_seconds']
    return {'generation_ids': sorted(ids), 'providers': sorted(providers), 'models': sorted(models),
            'first_stream_token_seconds_after_headers': first}


def outcome(response, error=None):
    choices = response.get('choices') or [{}]
    choice = choices[0]
    text = choice.get('message', {}).get('content') or ''
    finish = choice.get('finish_reason')
    if error:
        status = 'partial_final_answer' if text.strip() else 'uncertain_dispatch'
    elif finish == 'length':
        status = 'output_exhaustion'
    elif finish == 'stop' and text.strip():
        status = 'success'
    elif text.strip():
        status = 'partial_final_answer'
    else:
        status = 'no_final_answer'
    return {'status': status, 'usable_final': bool(text.strip()), 'finish_reason': finish,
            'error': error, 'usage': response.get('usage'), 'tensorfold': response.get('tensorfold'),
            'reasoning_tokens': (response.get('usage') or {}).get('completion_tokens_details', {}).get('reasoning_tokens')}


def recover_attempts(run, state):
    """Only undispatched work may resume. A preflight reservation is not resent."""
    for item in state['attempts']:
        path = Path(run) / 'attempts' / item['id'] / 'outcome.json'
        if path.exists():
            item.update(read_json(path))
        elif item['status'] == 'dispatched':
            item.update(status='uncertain_dispatch', error='Interrupted after dispatch; never resubmit')
    save(run, state)


def dispatch(run, state, task, body, client=None, before_local=None):
    run = Path(run)
    old = next((x for x in state['attempts'] if x['id'] == task['attempt_id']), None)
    if old and old['status'] != 'prepared':
        return old
    binding = read_json(run / 'binding.json')
    validate_body(body, task['arm'], binding['config'])
    folder = run / 'attempts' / task['attempt_id']
    folder.mkdir(parents=True, exist_ok=True)
    if not old:
        phase_limit = 6 if task['phase'] == 'qualification' else 32
        if len(state['attempts']) >= MAX_CALLS or sum(
                x['arm'] == task['arm'] and x['phase'] == task['phase']
                for x in state['attempts']) >= phase_limit:
            raise IntegrityError('Finite attempt allowance exhausted')
        old = {'id': task['attempt_id'], 'arm': task['arm'], 'phase': task['phase'],
               'status': 'prepared', 'request_hash': fingerprint(body), 'prepared_at': now()}
        state['attempts'].append(old)
        atomic_json(folder / 'request.json', body)
        save(run, state)
    elif old['request_hash'] != fingerprint(body):
        raise IntegrityError('Prepared request changed')
    reservation = None
    if task['arm'] == ARMS[1]:
        funds = client.admission(body, folder / 'controls')
        # A reservation surviving before the dispatch marker is kept conservative.
        reservation = client.ledger.reserve(body, folder, funds,
                                            'readiness' if task['phase'] == 'qualification' else 'trial')
    elif before_local:
        before_local(body, folder)
    old.update(status='dispatched', dispatched_at=now(), billing_reservation=reservation)
    save(run, state)  # durable BEFORE invoking any transport
    error = None
    response = {}
    started = time.monotonic()
    try:
        if task['arm'] == ARMS[1]:
            response, evidence = client.stream(body, folder)
        else:
            local = client or LocalClient(LOCAL_URL, LOCAL_MODEL, api_key='', purpose='simple_chapter',
                                         timeout=TIMEOUT, max_tokens=body['max_tokens'],
                                         max_response_bytes=128 * 1024 * 1024)
            local.model = LOCAL_MODEL
            response, evidence = local._request('POST', '/chat/completions', body, folder, 'research')
        atomic_json(folder / 'response.json', response)
        atomic_json(folder / 'transport-evidence.json', evidence)
    except Exception as exc:
        error = client._redact(str(exc)) if task['arm'] == ARMS[1] else str(exc)
        assembled = list(folder.rglob('response.assembled.json'))
        if assembled:
            response = read_json(assembled[0])
    meta = stream_metadata(folder)
    if task['arm'] == ARMS[1]:
        if len(meta['generation_ids']) == 1:
            response['id'] = meta['generation_ids'][0]
        client.ledger.settle(reservation, response, str(folder))
        if meta['providers'] != ['DeepInfra'] or meta['models'] != [MODEL]:
            error = 'Hosted provider/model missing or mismatch: ' + str(meta)
            state['identity_blocker'] = error
        if client.ledger.read().get('halt'):
            state['identity_blocker'] = client.ledger.read()['halt']
    elif response.get('model') != LOCAL_MODEL:
        error = 'Local model identity missing/mismatch'
        state['identity_blocker'] = error
    result = outcome(response, error)
    result.update(metadata=meta, elapsed_seconds=time.monotonic() - started, finished_at=now())
    if error and (folder / 'transport.json').exists():
        status = read_json(folder / 'transport.json').get('http_status')
        if status is not None and status != 200:
            result['status'] = 'api_error'
    text = (response.get('choices') or [{}])[0].get('message', {}).get('content') or ''
    (folder / 'answer.txt').write_text(text)
    atomic_json(folder / 'outcome.json', result)
    old.update(result)
    save(run, state)
    print(now(), task['attempt_id'], old['status'], round(old['elapsed_seconds'], 1), flush=True)
    return old
