"""Mathpix accounting and secret-safe HTTP primitives. No implicit paid calls."""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import io
import json
from pathlib import PurePosixPath
import re
import stat
import urllib.error
import urllib.request
import uuid
import zipfile

API='https://api.mathpix.com/v3/'
RATE_MICROUSD=5000
CAP_MICROUSD=1000000
OPTIONS={'metadata':{'improve_mathpix':False},'rm_fonts':False,'rm_spaces':False,
         'include_equation_tags':True,'include_page_breaks':True,'include_page_info':True,
         'preserve_section_numbering':True,'auto_number_sections':False,'remove_section_numbering':False,
         'conversion_formats':{'md':True,'tex.zip':True,'mmd.zip':True}}


def now():return datetime.now(timezone.utc).isoformat()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def job_identity(document,options=OPTIONS):
    return fingerprint({'source_sha256':document['sha256'],'pages':document['physical_pages'],
                        'endpoint':'/v3/pdf','options':options})


def reserve(ledger,key_id,budget_id,job,run,*,external_budget=None):
    """Caller holds the ledger lock and must fsync the result BEFORE POST."""
    expected={'external_shared_budget':{k:v for k,v in external_budget.items() if k!='reservation'}} if external_budget else {'cap_microusd':CAP_MICROUSD}
    budget=ledger.setdefault('budgets',{}).setdefault(budget_id,expected)
    if budget!=expected:raise ValueError('Budget binding changed')
    if external_budget:
        shared=__import__('json').loads(__import__('pathlib').Path(external_budget['ledger']).read_text());reservation=shared['reservations'][external_budget['reservation']]
        if shared['approval_sha256']!=external_budget['approval_sha256'] or Decimal(str(reservation['reserved_usd']))<Decimal(len(job['physical_pages']))/200:raise ValueError('Shared reservation missing/insufficient')
        expected_unit={'source_id':job['source_id'],'source_sha256':job['sha256'],'physical_pages':job['physical_pages'],'subset_sha256':job['subset_sha256']}
        if reservation.get('unit_identity')!=expected_unit:raise ValueError('Shared reservation belongs to a different source/subset')
    keys=ledger.setdefault('keys',{});records=keys.setdefault(key_id,{'jobs':{}})['jobs']
    identity=job_identity(job)
    if identity in records:return records[identity],False
    used=sum(r['reserved_microusd'] for k in keys.values() for r in k['jobs'].values() if r['budget_id']==budget_id)
    count=len(job['physical_pages']);cost=count*RATE_MICROUSD
    if count<1 or (not external_budget and used+cost>CAP_MICROUSD):raise ValueError('Persistent experiment budget exhausted')
    record={'identity':identity,'budget_id':budget_id,'run':str(run),'source_id':job['source_id'],
            'source_sha256':job['sha256'],'physical_pages':job['physical_pages'],'page_count':count,
            'subset_sha256':job['subset_sha256'],'options':OPTIONS,'reserved_at':now(),
            'reserved_microusd':cost,'estimated_incurred_microusd':None,
            'status':'reserved_uncertain','pdf_id':None,'submission_filename':'comparison-'+identity[:20]+'.pdf'}
    records[identity]=record
    return record,True


class APIError(RuntimeError):
    def __init__(self,status):
        super().__init__('Mathpix HTTP '+str(status));self.status=status


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


class Client:
    def __init__(self,credentials,opener=None):
        if set(credentials)!= {'app_id','app_key'} or not all(isinstance(v,str) and v for v in credentials.values()):
            raise ValueError('Credential file must contain nonempty app_id and app_key fields')
        self._secrets=tuple(credentials.values())
        self._headers=dict(credentials)
        self.key_id=hashlib.sha256((credentials['app_id']+'\0'+credentials['app_key']).encode()).hexdigest()
        self.opener=opener or urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())

    def redact(self,value):
        if isinstance(value,dict):
            return {k:('[REDACTED]' if k.lower() in ('app_id','app_key','authorization') else self.redact(v)) for k,v in value.items()}
        if isinstance(value,list):return [self.redact(v) for v in value]
        if isinstance(value,str):
            for secret in self._secrets:value=value.replace(secret,'[REDACTED]')
        return value

    def safe_bytes(self,data):
        if any(secret.encode() in data for secret in self._secrets):raise ValueError('Credential material in provider output; output not saved')
        return data

    def request(self,path,*,data=None,content_type=None):
        if not re.fullmatch(r'(?:pdf(?:/[A-Za-z0-9_.-]+)?|converter/[A-Za-z0-9_.-]+|ocr-usage(?:\?[^\s]*)?)',path):
            raise ValueError('Unexpected Mathpix endpoint')
        if data is not None and path!='pdf':raise ValueError('Only the frozen PDF submission endpoint permits POST')
        headers=dict(self._headers)
        if content_type:headers['Content-Type']=content_type
        request=urllib.request.Request(API+path,data=data,headers=headers,method='POST' if data is not None else 'GET')
        try:
            with self.opener.open(request,timeout=60) as response:
                payload=response.read(256*1024*1024+1)
                if len(payload)>256*1024*1024:raise ValueError('Output exceeds bounded download size')
                return payload
        except urllib.error.HTTPError as exc:
            # Do not log request/header objects or an unredacted error body.
            raise APIError(exc.code) from None
        except (urllib.error.URLError,TimeoutError,OSError):
            raise RuntimeError('Mathpix transport interrupted; POST charge/status may be uncertain') from None

    def get_json(self,path):
        result=json.loads(self.request(path))
        if path.startswith('ocr-usage') and isinstance(result,dict):
            rows=result.get('ocr_usage',[])
            if isinstance(rows,list):
                excluded=[r for r in rows if r.get('app_id') not in (None,self._headers['app_id'])]
                result['ocr_usage']=[r for r in rows if r not in excluded]
                result['excluded_other_key_rows']=len(excluded)
                result['key_attribution']='matched app_id where returned; rows without app_id are not independently attributable to this key'
        return self.redact(result)

    def submit(self,pdf,filename):
        boundary='pdf2tex-'+uuid.uuid4().hex
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="options_json"\r\nContent-Type: application/json\r\n\r\n'.encode()
              +json.dumps(OPTIONS).encode()+f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: application/pdf\r\n\r\n'.encode()
              +pdf+f'\r\n--{boundary}--\r\n'.encode())
        response=self.redact(json.loads(self.request('pdf',data=body,content_type='multipart/form-data; boundary='+boundary)))
        identifier=response.get('pdf_id')
        if not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',identifier):
            raise RuntimeError('Submission returned no usable pdf_id; retained as potentially billable, no retry')
        return identifier,response


def safe_zip(data):
    """Return archive entries without executing or following any supplied paths."""
    result={};total=0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if len(z.infolist())>2000:raise ValueError('Too many archive members')
        for entry in z.infolist():
            p=PurePosixPath(entry.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in entry.filename or stat.S_ISLNK(entry.external_attr>>16):
                raise ValueError('Unsafe archive member')
            if entry.is_dir():continue
            if entry.filename in result:raise ValueError('Duplicate archive member')
            total+=entry.file_size
            if total>256*1024*1024 or entry.file_size>64*1024*1024:raise ValueError('Archive exceeds inspection limit')
            result[entry.filename]=z.read(entry)
    return result
