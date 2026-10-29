"""Read-only DocVortex renderer bridge; uses the installed MinerU environment.

No analyze/pipeline/model imports, OCR, networking or dependency installation.
"""
import copy
import json
import sys
from pathlib import Path
from docvortex.schema import MiddleJson
from docvortex.render.latex import render_latex


def main():
    items=json.loads(Path(sys.argv[1]).read_text())
    rendered={}
    for item in items:
        payload=copy.deepcopy(item['document'])
        block=copy.deepcopy(item['native'])
        # Rendering one complete block avoids overlap/continuation merging. Native
        # evidence stays untouched; auxiliary text otherwise omitted by renderer.
        if block['type'] in ('header','footer','page_number','aside_text'):
            block['type']='text'
        block.pop('continues_prev',None)
        payload['pages']=[{'page_idx':0,'blocks':[block]}]
        payload['is_full_document']=True
        try:
            tex=render_latex(MiddleJson.model_validate(payload))
            body=tex.split('\\begin{document}',1)[1].rsplit('\\end{document}',1)[0].strip()
            rendered[item['id']]={'tex':body,'error':None}
        except Exception as exc:
            rendered[item['id']]={'tex':'','error':type(exc).__name__+': '+str(exc)}
    Path(sys.argv[2]).write_text(json.dumps(rendered,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
