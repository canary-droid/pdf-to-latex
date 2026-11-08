"""Pure, auditable contracts for the finite extraction-engine comparison."""
import hashlib
import json
from pathlib import PurePosixPath

ARMS = ('baseline', 'mineru_pro', 'glm_ocr')
MODEL_PINS = {
    'mineru_pro': ('opendatalab/MinerU2.5-Pro-2605-1.2B', '08aaea840498d49ce16247b6263196cf02814885'),
    'glm_ocr': ('zai-org/GLM-OCR', '2e85a62840ccac27daa451df36c736c4636b8628'),
    'glm_layout': ('PaddlePaddle/PP-DocLayoutV3_safetensors', 'e4f489dc536556fc1be02b973ba06756e0d4a2ac'),
}
SDK_REVISION = '0288f96bb9e78cb439883eaa725eeae90bd177c5'
RUNTIME = 'vllm/vllm-openai@sha256:4f986370d7737abacc70ac17f86695acd1dc7892a02ad89ac132639d5afee0d0'


def runtime_dockerfile():
    # The official GLM-OCR vLLM instructions require Transformers >=5.3.
    # Upgrade only its Python dependency chain inside the NEW image. Keep the
    # image's GPU stack (Torch/CUDA/NCCL/vLLM) constrained and unchanged.
    import shlex
    allowed={
        'vllm 0.19.0 has requirement transformers<5,>=4.56.0, but you have transformers 5.3.0.',
        'compressed-tensors 0.14.0.1 has requirement transformers<5.0.0, but you have transformers 5.3.0.',
        'nvidia-cusparselt-cu12 0.7.1 is not supported on this platform',
    }
    # These exact upstream image metadata conflicts are recorded, not erased.
    # The vendor's documented Transformers override needs real BF16 GPU/model
    # qualification; sparse/quantized routes are not used by this experiment.
    check=('import subprocess,json,sys,importlib.metadata as m; from pathlib import Path; '
           'p=subprocess.run([sys.executable,"-m","pip","check"],capture_output=True,text=True); '
           'lines=[s.strip() for s in (p.stdout+p.stderr).splitlines() if s.strip()]; '
           'allowed='+repr(sorted(allowed))+'; '
           'unexpected=[s for s in lines if s not in allowed and s!="No broken requirements found."]; '
           'versions={n:m.version(n) for n in ("vllm","torch","transformers","mineru-vl-utils","glmocr")}; '
           'assert versions=={"vllm":"0.19.0","torch":"2.10.0+cu129","transformers":"5.3.0","mineru-vl-utils":"2.0.7","glmocr":"0.1.5"},versions; '
           'Path("/opt/extraction-dependency-check.json").write_text(json.dumps({"versions":versions,"pip_check":lines,"unexpected":unexpected,"qualification":"Not GPU-qualified: documented Transformers override; unchanged stock sparse-library metadata warning. BF16 execution must pass the frozen smoke page."},indent=2)); '
           'print(json.dumps({"versions":versions,"known_metadata_warnings":lines,"unexpected":unexpected})); sys.exit(bool(unexpected))')
    return ('FROM '+RUNTIME+'\n'
        'RUN python3 -m pip freeze | grep -viE "^(transformers|huggingface-hub|huggingface_hub|tokenizers)==" > /tmp/constraints.txt && '
        'python3 -m pip install --no-cache-dir -c /tmp/constraints.txt "transformers==5.3.0" '
        '"mineru-vl-utils==2.0.7" "glmocr[selfhosted] @ https://github.com/zai-org/GLM-OCR/archive/'+SDK_REVISION+'.tar.gz"\n'
        'RUN python3 -c '+shlex.quote(check)+'\n'
        'RUN python3 -m pip freeze > /opt/extraction-comparison-packages.txt\n'
        'ENV HF_HUB_DISABLE_TELEMETRY=1 DO_NOT_TRACK=1 VLLM_NO_USAGE_STATS=1\n')


def validate_plan(plan):
    documents = plan['documents']
    if not 6 <= len(documents) <= 8:
        raise ValueError('Document count outside the authorised comparison')
    identities = [d['source_id'] for d in documents]
    if len(set(identities)) != len(identities):
        raise ValueError('Duplicate source identity')
    count = 0
    for document in documents:
        if 'cooking' in document['filename'].lower() or 'collateralpdf' in document['filename'].lower():
            raise ValueError('Excluded source')
        digest = document['sha256']
        if len(digest) != 64 or document['source_id'] != 'original-'+digest[:16]:
            raise ValueError('Source identity does not match its full digest')
        pages = document['physical_pages']
        if pages != sorted(set(pages)) or any(type(p) is not int or p < 1 for p in pages):
            raise ValueError('Invalid or duplicate physical pages')
        if [p['physical_pdf_page'] for p in document['pages']] != pages:
            raise ValueError('Image/page mapping differs from selected scope')
        count += len(pages)
    if count != plan['page_count'] or not 24 <= count <= 36:
        raise ValueError('Page count outside frozen scope')
    if len(plan['downstream']) != 2 or plan['maximum_primary_downstream_requests'] != 12:
        raise ValueError('Unexpected downstream expansion')
    if (plan['conversion_effort'], plan['critic_effort'], plan['output_tokens'], plan['model'], plan['images_in_downstream']) != ('high','max',131072,'glm53-regular',False):
        raise ValueError('Downstream settings changed')


def check_relative(path):
    p = PurePosixPath(path)
    if p.is_absolute() or '..' in p.parts or '\\' in path:
        raise ValueError('Unsafe relative artifact path')
    return path


def task_allowed(record):
    """A crash with a reservation consumes the attempt until reconciliation."""
    return record is None or record.get('status') == 'pending'


def raw_text(blocks):
    """Readable comparison view only: retain every block and its original text."""
    lines = []
    for index, block in enumerate(blocks):
        text = block.get('content')
        if text is None: text = ''
        if not isinstance(text, str): text = json.dumps(text, ensure_ascii=False)
        lines.append(f'<!-- region {index}; type={block.get("type", "unknown")}; bbox={block.get("bbox")} -->\n'+text)
    return '\n\n'.join(lines)


def input_digest(body):
    return hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def safe_glmocr_config(layout_path):
    """Explicit local route; defaults must never select the hosted MaaS service."""
    return {'pipeline': {
        'maas': {'enabled':False,'api_key':None},
        'ocr_api': {'api_host':'127.0.0.1','api_port':18080,'model':'glm-ocr',
                    'api_scheme':'http','api_url':None,'api_key':None,'retry_max_attempts':0},
        'max_workers':2,
        'layout': {'model_dir':str(layout_path),'device':'cpu','batch_size':1,'workers':1,
                   'label_task_mapping': {'text':['abstract','algorithm','content','doc_title','figure_title','paragraph_title','reference_content','text','vertical_text','vision_footnote','seal','formula_number','header','footer','number','footnote'],
                                          'table':['table'],'formula':['display_formula','inline_formula'],
                                          'skip':['chart','image'],'abandon':[]}},
        'page_loader': {'max_tokens':8192,'pdf_dpi':200,'pdf_max_pages':None},
        'result_formatter': {'output_format':'both','enable_merge_formula_numbers':True,'enable_merge_text_blocks':True},
    }}
