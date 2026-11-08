"""Inside installed serving container: CPU preprocessing/tokenization ONLY, no tower."""
import sys,json,hashlib,os
from pathlib import Path
from collections import OrderedDict
from tokenizers import Tokenizer
from tensorfold.cuda.chat_template import ChatTemplate
from tensorfold.vision.glm import GlmVision,GlmVisionLimits
from tensorfold.server.prompts import prepare_images
payload=json.load(sys.stdin)
model=Path('/root/.cache/huggingface/hub/models--Mia-AiLab--GLM-5.3-Flash-EXL3-4bpw-TensorFold/snapshots/078455ffe6472f9a52fbc1139f58b9db2881b25c')
frontend=GlmVision.__new__(GlmVision) # deliberately bypass constructor/tower
frontend.allow_urls=False;frontend.limits=GlmVisionLimits.from_env();frontend.tok=Tokenizer.from_file(str(model/'tokenizer.json'));frontend.image_token=json.loads((model/'config.json').read_text())['image_token_id'];frontend._pictures=OrderedDict();frontend._canvases=OrderedDict()
assert frontend.limits.image_tokens==2048 and frontend.limits.request_image_tokens==16384 and frontend.limits.max_images==50
assert not hasattr(frontend,'tower')
template=ChatTemplate(model)
from tensorfold.families.glm5_next.cuda.app import media_template
media_template(template,model) # same in-memory vision template patch used by the running App
results={}
for name,body in payload.items():
    effort=body['reasoning_effort'];render=lambda messages:template.render(messages,tools=None,enable_thinking=True,extra={'reasoning_effort':effort},allow_images=True)
    prepared=prepare_images(frontend,body['messages'],render,context_limit=1048576)
    assert len(prepared.vision.positions)>0, 'Image markers were not expanded'
    results[name]={'prompt_tokens':len(prepared.tokens),'image_rows':len(prepared.vision.positions),'image_shapes':[list(x.shape) for _,x in prepared.vision.items],'fitted_pixel_hashes':[x.digest.hex() for _,x in prepared.vision.items],'requested_effort':effort,'mode':'Installed CPU preprocessing/template/tokenizer only; no model inference','tokens_sha256':hashlib.sha256(json.dumps(prepared.tokens).encode()).hexdigest()}
base=Path('/usr/local/lib/python3.12/dist-packages/tensorfold')
print(json.dumps({'limits':{k:getattr(frontend.limits,k) for k in ['image_tokens','request_image_tokens','max_images']},'requests':results,'sources':{n:hashlib.sha256((base/n).read_bytes()).hexdigest() for n in ['vision/glm.py','vision/images.py','server/prompts.py','cuda/chat_template.py','server/request_options.py','families/glm5_next/cuda/app.py']},'template_sha256':hashlib.sha256((model/'chat_template.jinja').read_bytes()).hexdigest(),'no_inference':True}))
