"""Explicitly authorized MiMo-only transport and USD ledger for the critic pilot.

Never used by conversion or local fallback. Secret access is runtime only.
"""
import copy
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import http.client
import json
import os
from pathlib import Path
import re
import socket
import ssl
import stat
import threading
import time
import uuid

from .common import atomic_json,read_json,fingerprint,sha
from .local_model import LocalClient,ProbeError,MAX_REQUEST_BYTES,parse_json_response
from .batch_review import IdentityError,IntegrityError

BASE='https://openrouter.ai/api/v1'
MODEL='xiaomi/mimo-v2.6-pro'
TAG='xiaomi/fp8'
KEY_FILE='/home/mdi/.config/pdf-to-latex/openrouter.key'
DEFAULT_BUDGET_USD='10.00'
RATES={'prompt':'0.000000435','completion':'0.00000087','input_cache_read':'0.0000000036'}
RETENTION={'provider':'Xiaomi','documented_days':30,'accepted_days_exclusive':100,'training_reported':False,
           'source':'https://openrouter.ai/providers','checked_on':'2026-10-25',
           'scope':'Nonpersonal published book passages; user explicitly accepts retention below 100 days. No training opt-in.'}
POLICY={'only':[TAG],'allow_fallbacks':False,'require_parameters':True,'data_collection':'allow','zdr':False,
        'max_price':{'prompt':0.435,'completion':0.87}}
CONFIG={'endpoint':BASE,'model':MODEL,'max_tokens':32768,'timeout':900,'stream':False,
        'reasoning':{'enabled':True},'provider':POLICY,'plugins':[],
        'lower_reasoning_supported':False,'sampling':'server defaults omitted','profile':'mimo',
        'cloud_opt_in':True,'budget_usd':DEFAULT_BUDGET_USD,'rates':RATES,'key_file':KEY_FILE,'retention_policy':RETENTION,
        'response_mode':'strict_json_schema','readiness_calls':2,'readiness_max_tokens':2048}


class AdmissionError(RuntimeError):pass


def decimal(value):
    try:d=Decimal(str(value))
    except (InvalidOperation,TypeError):raise AdmissionError('Missing/invalid monetary value') from None
    if not d.is_finite() or d<0:raise AdmissionError('Negative/nonfinite monetary value')
    return d


def budget_amount(value):
    """Explicit preparation setting, never an unsealed live/environment override."""
    amount=decimal(value)
    try:rounded=amount.quantize(Decimal('0.01'))
    except InvalidOperation:raise AdmissionError('Budget must be a finite positive USD amount in whole cents') from None
    if amount<=0 or rounded!=amount:raise AdmissionError('Budget must be a finite positive USD amount in whole cents')
    return format(rounded,'.2f')


def profile(budget_usd=DEFAULT_BUDGET_USD):
    config=copy.deepcopy(CONFIG);config['budget_usd']=budget_amount(budget_usd);return config


def validate_config(config):
    expected=profile(config.get('budget_usd'))
    if config.get('critic_protocol'):
        from .critic_anchors import VERSIONS, MAX_INPUT_BYTES
        limits=config.get('paid_limits',{})
        if (config['critic_protocol'] not in VERSIONS or set(limits)!={'trial_calls','readiness_calls'}
            or type(limits['trial_calls']) is not int or not 1<=limits['trial_calls']<=6 or limits['readiness_calls']!=1):
            raise IntegrityError('Invalid selected MiMo stage limits')
        expected.update(critic_protocol=config['critic_protocol'],paid_limits=limits,readiness_calls=1,request_byte_limit=MAX_INPUT_BYTES)
    if config!=expected:raise IntegrityError('Remote profile differs from permitted configuration')
    return config['budget_usd']


def read_key(path=None):
    """Operator runtime only; no contents or key-derived fingerprint in artifacts."""
    p=Path(path or os.environ.get('OPENROUTER_API_KEY_FILE') or KEY_FILE)
    try:
        if p.is_symlink() or p.parent.is_symlink():raise ValueError()
        parent=p.parent.stat()
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'r',encoding='ascii') as f:
            s=os.fstat(f.fileno())
            if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600:raise ValueError()
            if parent.st_uid!=os.getuid() or stat.S_IMODE(parent.st_mode)!=0o700:raise ValueError()
            raw=f.read(1025)
        key=raw.rstrip('\r\n')
        if not 10<=len(key)<=1024 or not re.fullmatch(r'[!-~]+',key) or raw not in (key,key+'\n',key+'\r\n'):raise ValueError()
        return key
    except (OSError,ValueError,UnicodeError):
        raise AdmissionError('Private key file missing/empty/invalid or not owned mode 600 in an owned mode 700 directory; see operator setup. Contents not displayed.') from None


def body_for(messages,max_tokens=32768,response_format=None):
    from .text_critic import SCHEMA
    return {'model':MODEL,'messages':messages,'max_tokens':max_tokens,'stream':False,'reasoning':{'enabled':True},
        'provider':copy.deepcopy(POLICY),'plugins':[],
        'response_format':response_format or {'type':'json_schema','json_schema':{'name':'text_critic','strict':True,'schema':SCHEMA}}}


def token_bound(body):
    # No tokenizer is installed/downloaded. Reserve one token per UTF-8 byte of the
    # ENTIRE JSON payload (including schema), plus 4096 framing tokens. This is a
    # deliberately conservative text/byte-tokenizer bound, never bytes/4 averages.
    # Unknown provider expansion is not licensed: observed overflow stops admission.
    return len(json.dumps(body,ensure_ascii=False,allow_nan=False).encode('utf-8'))+4096


def cost_bound(body):
    if len(json.dumps(body).encode())>MAX_REQUEST_BYTES:raise AdmissionError('Request too large; no truncation')
    return (Decimal(token_bound(body))*decimal(RATES['prompt'])+Decimal(body['max_tokens'])*decimal(RATES['completion'])).quantize(Decimal('0.000000001'),rounding=ROUND_CEILING)


def route_check(endpoints,retention=None):
    # This is the explicitly accepted published policy, not a claim that the API
    # attests retention. No authenticated ZDR-list lookup is required or performed.
    retention=RETENTION if retention is None else retention
    days=retention.get('documented_days')
    if (retention.get('provider')!='Xiaomi' or type(days) is not int or not 0<=days<100
        or retention.get('accepted_days_exclusive')!=100 or retention.get('training_reported') is not False
        or not retention.get('source') or not retention.get('checked_on')):
        raise AdmissionError('Published Xiaomi policy must document retention below 100 days without training opt-in')
    data=endpoints.get('data',{})
    if data.get('id')!=MODEL:raise IdentityError('Different OpenRouter model metadata')
    matches=[e for e in data.get('endpoints',[]) if e.get('tag')==TAG]
    if len(matches)!=1:raise AdmissionError('Pinned Xiaomi FP8 endpoint unavailable; no fallback')
    e=matches[0]
    if e.get('model_id')!=MODEL or e.get('provider_name')!='Xiaomi' or e.get('quantization')!='fp8' or e.get('service_tier') not in (None,'standard'):
        raise IdentityError('Unexpected provider endpoint identity/tier')
    if e.get('status')!=0:raise AdmissionError('Pinned endpoint is not available')
    for k,maxprice in RATES.items():
        if decimal(e.get('pricing',{}).get(k))>decimal(maxprice):raise AdmissionError('Pinned route rate increased: '+k)
    for k,v in e.get('pricing',{}).items():
        if k not in (*RATES,'discount') and decimal(v)!=0:raise AdmissionError('Unexpected additional billing component: '+k)
    if e.get('max_completion_tokens',0)<32768 or e.get('context_length',0)<32768+4096:raise AdmissionError('Endpoint token limits insufficient')
    if not {'reasoning','max_tokens','response_format','structured_outputs'}<=set(e.get('supported_parameters',[])):
        raise AdmissionError('Pinned route lacks required reasoning/schema controls; no silent output-mode change')
    return e


def key_allowance(response,budget_usd=DEFAULT_BUDGET_USD):
    budget=decimal(budget_amount(budget_usd))
    d=response.get('data',{})
    if 'limit_reset' not in d or d['limit_reset'] is not None or decimal(d.get('limit'))!=budget:
        raise AdmissionError(f'Require a dedicated non-resetting USD {budget:.2f} standard inference key matching the sealed budget; never raise the limit automatically')
    remaining=decimal(d.get('limit_remaining'))
    if remaining>budget:raise AdmissionError('Inconsistent dedicated-key remaining allowance')
    return remaining


class Ledger:
    def __init__(self,run,*,create=False):
        self.run=Path(run);self.path=self.run/'billing.json'
        self.binding=sha(self.run/'binding.json')
        binding=read_json(self.run/'binding.json');self.ceiling=budget_amount(binding['config']['budget_usd'])
        self.budget=decimal(self.ceiling);self.inherited=binding.get('inherited_billing')
        self.stage_limits=binding['config'].get('paid_limits')
        self.prior=binding.get('prior_billing')
        if not self.path.exists():
            if not create:raise IntegrityError('Cloud budget ledger missing; never reset consumed charges')
            atomic_json(self.path,{'binding_sha256':self.binding,'ceiling_usd':self.ceiling,'reservations':[],'halt':None})
        self.read()

    def read(self):
        d=read_json(self.path)
        if d['binding_sha256']!=self.binding or d['ceiling_usd']!=self.ceiling:raise IntegrityError('Changed cloud budget binding')
        if self.inherited:
            p=Path(self.inherited['path'])
            if sha(p)!=self.inherited['sha256']:raise IntegrityError('Inherited billing evidence changed')
            old=read_json(p)
            if len(d['reservations'])<len(old['reservations']):raise IntegrityError('Inherited charges were reset')
            for before,after in zip(old['reservations'],d['reservations']):
                if any(after.get(k)!=v for k,v in before.items()):raise IntegrityError('Inherited charge/reservation changed')
            if old['halt'] and d['halt']!=old['halt']:raise IntegrityError('Inherited billing stop cleared')
        if [x['id'] for x in d['reservations']]!=[f'{i+1:04d}' for i in range(len(d['reservations']))]:raise IntegrityError('Cloud reservation sequence changed')
        seen=set()
        for x in d['reservations']:
            p=self.run/x['evidence']
            if not p.is_file() or sha(p)!=x['evidence_sha256']:raise IntegrityError('Cloud charge reservation disappeared/changed')
            frozen=read_json(p)
            if any(x.get(k)!=v for k,v in frozen.items()):raise IntegrityError('Cloud reservation changed')
            if x['folder'] in seen:raise IntegrityError('Duplicate cloud dispatch')
            seen.add(x['folder'])
            if x.get('settlement'):
                s=self.run/x['settlement']
                if sha(s)!=x['settlement_sha256'] or read_json(s)['actual_cost_usd']!=x['actual_cost_usd']:raise IntegrityError('Cloud settlement changed')
        # Directory membership, not just mutable totals, detects missing reservations.
        dirs={p.parent.name for p in (self.run/'billing').glob('*/reservation.json')}
        if dirs!={x['id'] for x in d['reservations']}:raise IntegrityError('Unregistered cloud reservation; manual accounting investigation required')
        self.prior_summary()
        return d

    def prior_summary(self):
        if not self.prior:return {}
        p=Path(self.prior['path'])
        if sha(p)!=self.prior['sha256']:raise IntegrityError('Prior paid-stage accounting changed')
        record=read_json(p);summary=record['summary']
        if summary['ceiling_usd']!=self.ceiling or summary.get('halt'):raise IntegrityError('Prior paid ceiling/stop is incompatible')
        for field in ('actual_reported_usd','unresolved_reserved_usd'):decimal(summary[field])
        return summary

    @staticmethod
    def exposure(d):return sum((decimal(x.get('actual_cost_usd',x['reserved_usd'])) for x in d['reservations']),Decimal(0))

    def admit(self,body,remaining):
        d=self.read()
        if d['halt']:raise AdmissionError(d['halt'])
        amount=cost_bound(body);pending=sum((decimal(x['reserved_usd']) for x in d['reservations'] if 'actual_cost_usd' not in x),Decimal(0))
        # Conservatively subtract ambiguous charges even if the provider may already count them.
        prior=self.prior_summary();prior_exposure=decimal(prior.get('actual_reported_usd',0))+decimal(prior.get('unresolved_reserved_usd',0))
        if prior_exposure+self.exposure(d)+amount>self.budget or pending+decimal(prior.get('unresolved_reserved_usd',0))+amount>remaining:
            raise AdmissionError(f'Insufficient remaining USD {self.ceiling} budget after actual costs and unresolved charge reservations; no request admitted')
        return amount

    def reserve(self,body,folder,remaining,phase):
        amount=self.admit(body,remaining);d=self.read();folder=str(Path(folder).resolve().relative_to(self.run.resolve()))
        if any(x['folder']==folder for x in d['reservations']):raise AdmissionError('Request already reserved; no blind paid retry')
        inherited=len(read_json(Path(self.inherited['path']))['reservations']) if self.inherited and self.stage_limits else 0
        count=sum(x['phase']==phase for x in d['reservations'][inherited:])
        limit=self.stage_limits['readiness_calls' if phase=='readiness' else 'trial_calls'] if self.stage_limits else (2 if phase=='readiness' else 16)
        if count>=limit:raise AdmissionError('Paid readiness/trial call ceiling exhausted')
        identity=f'{len(d["reservations"])+1:04d}'
        item={'id':identity,'folder':folder,'phase':phase,'request_sha256':fingerprint(body),
            'reserved_usd':str(amount),'prompt_token_bound':token_bound(body),'output_limit':body['max_tokens'],'rates':RATES}
        p=self.run/'billing'/identity/'reservation.json';atomic_json(p,item)
        # Crash between reservation and index fails closed on next read; never frees money.
        d['reservations'].append({**item,'evidence':str(p.relative_to(self.run)),'evidence_sha256':sha(p)})
        atomic_json(self.path,d);return identity

    def settle(self,identity,response,evidence_source):
        d=self.read();x=next(x for x in d['reservations'] if x['id']==identity)
        if 'actual_cost_usd' in x:return
        generation=response.get('id');usage=response.get('usage') or {};cost=usage.get('cost')
        if generation and isinstance(generation,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,200}',generation):x['generation_id']=generation
        if cost is not None:
            value=decimal(cost)
            if value>decimal(x['reserved_usd']):d['halt']='Provider reported cost above reservation; stop and investigate'
            if type(usage.get('prompt_tokens')) is int and usage['prompt_tokens']>x['prompt_token_bound']:d['halt']='Observed input tokens exceeded conservative bound; stop and investigate'
            if type(usage.get('completion_tokens')) is int and usage['completion_tokens']>x['output_limit']:d['halt']='Provider exceeded billed completion bound; stop and investigate'
            # A zero cost with positive generation tokens is not assumed free for this paid route.
            if value>0 or usage.get('completion_tokens')==0:
                p=self.run/'billing'/identity/'settlement.json'
                evidence={'actual_cost_usd':str(value),'source':evidence_source,'usage':usage,'generation_id':x.get('generation_id')}
                atomic_json(p,evidence);x.update(actual_cost_usd=str(value),settlement=str(p.relative_to(self.run)),settlement_sha256=sha(p))
        atomic_json(self.path,d)

    def summary(self):
        d=self.read();known=[x for x in d['reservations'] if 'actual_cost_usd' in x];unknown=[x for x in d['reservations'] if 'actual_cost_usd' not in x]
        prior=self.prior_summary();actual=sum((decimal(x['actual_cost_usd']) for x in known),decimal(prior.get('actual_reported_usd',0)))
        unresolved=sum((decimal(x['reserved_usd']) for x in unknown),decimal(prior.get('unresolved_reserved_usd',0)))
        return {'ceiling_usd':self.ceiling,'actual_reported_usd':str(actual),
            'unresolved_reserved_usd':str(unresolved),
            'remaining_local_usd':str(max(Decimal(0),self.budget-actual-unresolved)),'reservations':len(d['reservations'])+prior.get('reservations',0),
            'prior_stage':prior or None,'current_stage_reservations':len(d['reservations']),
            'readiness_calls':sum(x['phase']=='readiness' for x in d['reservations']),
            'unresolved_charge_ids':['prior:'+x for x in prior.get('unresolved_charge_ids',[])]+[x['id'] for x in unknown],
            'halt':d['halt'],'meaning':'Unknown charges remain at their maximum reservation. Includes readiness, failures and repairs.'}


class CloudClient:
    """Separate explicit remote client; reuses local completion parsing, not URL policy."""
    def __init__(self,base_url,model=None,timeout=900,max_tokens=32768,purpose='text_critic',*,run,key_path=None):
        if base_url!=BASE or model!=MODEL or purpose!='text_critic':raise ValueError('Only explicitly prepared MiMo critic profile allowed')
        if max_tokens not in (2048,32768) or timeout not in (120,900):raise ValueError('Unexpected paid request limits')
        self.run=Path(run).resolve();binding=read_json(self.run/'binding.json')
        self.budget_usd=validate_config(binding['config'])
        self.config=binding['config']
        self._key=read_key(key_path);self.base_url=BASE;self.requested_model=model;self.model=None
        self.max_tokens=max_tokens;self.timeout=timeout;self.purpose=purpose;self.ledger=Ledger(self.run);self.admission=None

    def _redact(self,value):
        if isinstance(value,bytes):
            try:
                obj=json.loads(value)
                encoded=json.dumps(obj,ensure_ascii=False)
                if self._key in encoded:return encoded.replace(self._key,'[REDACTED_API_KEY]').encode()
            except (ValueError,UnicodeError):pass
            return value.replace(self._key.encode(),b'[REDACTED_API_KEY]')
        return str(value).replace(self._key,'[REDACTED_API_KEY]')

    def _connection(self,timeout):return http.client.HTTPSConnection('openrouter.ai',443,timeout=timeout,context=ssl.create_default_context())

    def _http(self,method,path,body=None):
        """Fixed origin, verified TLS, no environment proxies, redirects, retries or tools."""
        allowed=('/models/xiaomi/mimo-v2.6-pro/endpoints','/key')
        if not ((method=='GET' and (path in allowed or re.fullmatch(r'/generation\?id=[A-Za-z0-9_-]{1,200}',path))) or (method=='POST' and path=='/chat/completions')):
            raise AdmissionError('Remote operation outside selected critic scope')
        timeout=self.timeout if method=='POST' else 30;conn=None;start=time.monotonic();raw=bytearray();timer=None
        def expire():
            if conn and conn.sock:
                try:conn.sock.shutdown(socket.SHUT_RDWR)
                except OSError:pass
        try:
            conn=self._connection(timeout)
            timer=threading.Timer(timeout,expire);timer.daemon=True;timer.start();conn.connect()
            conn.request(method,'/api/v1'+path,body=None if body is None else json.dumps(body,ensure_ascii=False).encode(),
                headers={'Authorization':'Bearer '+self._key,'Content-Type':'application/json','Accept':'application/json','User-Agent':'pdf2tex-opt-in-critic/1'})
            resp=conn.getresponse();status=resp.status
            while True:
                left=timeout-(time.monotonic()-start)
                if left<=0:raise TimeoutError()
                if conn.sock:conn.sock.settimeout(left)
                b=resp.read1(min(65536,8*1024*1024+1-len(raw)))
                if not b:break
                raw.extend(b)
                if len(raw)>8*1024*1024:raise ValueError('Response byte cap')
            declared=resp.getheader('Content-Length')
            if declared is not None and int(declared)!=len(raw):raise ValueError('Incomplete body')
            return status,self._redact(bytes(raw)),time.monotonic()-start
        except Exception as exc:
            # Never propagate a credential-bearing transport exception/context.
            raise ProbeError('OpenRouter transport '+type(exc).__name__+'; charge remains reserved if dispatched') from None
        finally:
            if timer:timer.cancel()
            if conn:conn.close()

    def control(self,path,folder,*,private=False):
        status,raw,elapsed=self._http('GET',path)
        if not private:
            folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);(folder/'response.raw').write_bytes(raw)
            atomic_json(folder/'record.json',{'http_status':status,'latency_seconds':elapsed,'url':BASE+path})
        if status!=200:raise AdmissionError('OpenRouter metadata HTTP '+str(status)+'; no inference admitted')
        try:return parse_json_response(raw.decode())
        except (ValueError,UnicodeError):raise AdmissionError('Invalid metadata response; no inference admitted') from None

    def check_admission(self,body):
        expected=body_for(body['messages'],body['max_tokens'],body.get('response_format'))
        required_format=body_for([])['response_format']
        if self.config.get('critic_protocol'):
            from .critic_anchors import required_response_format,bounded
            required_format=required_response_format(body,self.config['critic_protocol']);bounded(body)
        if body!=expected or body['response_format']!=required_format:
            raise IntegrityError('Changed paid request profile/schema')
        if any(set(m)!={'role','content'} or m['role'] not in ('system','user','assistant') or not isinstance(m['content'],str) for m in body['messages']):
            raise AdmissionError('Only explicit text messages are authorized; no images/tools/history uploads')
        folder=self.run/'cloud-controls'/uuid.uuid4().hex
        endpoints=self.control('/models/xiaomi/mimo-v2.6-pro/endpoints',folder/'endpoints')
        endpoint=route_check(endpoints)
        if token_bound(body)+body['max_tokens']>endpoint['context_length'] or (endpoint.get('max_prompt_tokens') and token_bound(body)>endpoint['max_prompt_tokens']):
            raise AdmissionError('Full text does not fit verified limits; never truncate')
        remaining=key_allowance(self.control('/key',None,private=True),self.budget_usd)
        self.ledger.admit(body,remaining)
        atomic_json(folder/'qualification.json',{'model':MODEL,'provider':TAG,'pricing':endpoint['pricing'],
            'retention_policy':RETENTION,'retention_verification':'published policy accepted by operator; not API-attested ZDR',
            'key_limit_usd':self.budget_usd,'key_limit_reset':None,'key_remaining_usd':str(remaining),'request_sha256':fingerprint(body)})
        self.admission=(fingerprint(body),remaining);return endpoint

    def discover_model(self,output_dir):
        # No generation; live route/key checks are performed immediately before paid dispatch.
        self.model=MODEL
        return {'selected_model':MODEL,'status':'prepared_identity_only; route_checked_before_each_dispatch'}

    def _request(self,method,endpoint,payload,output_dir,label):
        if (method,endpoint)!=('POST','/chat/completions'):raise AdmissionError('Unexpected paid transport operation')
        body=body_for(payload['messages'],payload['max_tokens'],payload.get('response_format'))
        folder=Path(output_dir).resolve();relative=folder.relative_to(self.run)
        if relative.parts[0] not in ('calls','readiness-attempts'):raise AdmissionError('Paid dispatch evidence outside bound run')
        phase='readiness' if relative.parts[0]=='readiness-attempts' else 'trial'
        if (phase=='readiness')!=(body['max_tokens']==2048):raise AdmissionError('Paid phase limits changed')
        if not self.admission or self.admission[0]!=fingerprint(body):self.check_admission(body)
        identity=self.ledger.reserve(body,folder,self.admission[1],phase);self.admission=None
        attempt=folder/'attempts'/uuid.uuid4().hex;attempt.mkdir(parents=True)
        atomic_json(attempt/'request.json',{'body':body,'url':BASE+endpoint,'headers':{'Authorization':'[REDACTED]'}})
        status=None;elapsed=None;raw=b'';record={'cloud_reservation':identity,'configured_model':MODEL,'configured_provider':TAG}
        try:
            status,raw,elapsed=self._http('POST',endpoint,body)
            (attempt/'response.raw').write_bytes(raw)
            try:data=parse_json_response(raw.decode())
            except (ValueError,UnicodeError):raise ProbeError('OpenRouter response not strict JSON',status=status) from None
            if not isinstance(data,dict):raise ProbeError('OpenRouter response not an object',status=status)
            self.ledger.settle(identity,data,str(attempt/'response.raw'))
            if status!=200:raise ProbeError('OpenRouter HTTP '+str(status)+'; no automatic network retry',status=status)
            if data.get('model')!=MODEL or data.get('provider')!='Xiaomi':raise IdentityError('OpenRouter returned different/missing exact model or Xiaomi provider')
            if self.ledger.read()['halt']:raise AdmissionError(self.ledger.read()['halt'])
            record.update(returned_model=data.get('model'),returned_provider=data.get('provider'))
            return data,{'attempt_dir':str(attempt),'http_status':status,'latency_seconds':elapsed,'provider':data.get('provider'),'generation_id':data.get('id')}
        finally:
            if not (attempt/'response.raw').exists():(attempt/'response.raw').write_bytes(raw)
            record.update(http_status=status,latency_seconds=elapsed);atomic_json(attempt/'record.json',record)

    def chat(self,messages,output_dir,label,response_format=None,*,reasoning_effort='server-default'):
        if reasoning_effort!='server-default':raise AdmissionError('MiMo uses explicit reasoning.enabled, not graded effort')
        return LocalClient.chat(self,messages,output_dir,label,response_format,reasoning_effort=reasoning_effort)

    def reconcile_costs(self):
        """GET-only; unknown IDs remain reserved. Never retransmit a completion."""
        for x in self.ledger.read()['reservations']:
            if 'actual_cost_usd' in x:continue
            # Recover an ID/cost saved before a crash without changing sealed attempt evidence.
            for raw in (self.run/x['folder']).glob('attempts/*/response.raw'):
                try:value=parse_json_response(raw.read_text())
                except (ValueError,UnicodeError):continue
                if isinstance(value,dict):self.ledger.settle(x['id'],value,str(raw))
            current=next(y for y in self.ledger.read()['reservations'] if y['id']==x['id'])
            if 'actual_cost_usd' in current or not current.get('generation_id'):continue
            genid=current['generation_id'];d=self.control('/generation?id='+genid,self.run/'billing'/x['id']/('lookup-'+uuid.uuid4().hex)).get('data',{})
            if d.get('id')!=genid or d.get('model')!=MODEL or d.get('provider_name')!='Xiaomi':raise IdentityError('Generation cost lookup identity changed')
            if d.get('is_byok') or d.get('num_search_results',0) or d.get('num_fetches',0):raise AdmissionError('Unexpected paid tools/provider billing')
            self.ledger.settle(x['id'],{'id':genid,'usage':{'cost':d.get('total_cost'),'prompt_tokens':d.get('native_tokens_prompt'),
                'completion_tokens':d.get('native_tokens_completion'),'completion_tokens_details':{'reasoning_tokens':d.get('native_tokens_reasoning')}}},'OpenRouter generation lookup')
        return self.ledger.summary()
