"""Opt-in child-process OCR diagnostics and evidence-gated subpixel crop handling."""
import hashlib,inspect,json,math,traceback
from pathlib import Path


def qualified_size(points,image_shape,size):
    """Only positive, nondegenerate in-image quads rounded to zero qualify."""
    if len(points)!=4 or any(len(p)!=2 for p in points):return None
    if any(not math.isfinite(float(x)) for p in points for x in p):return None
    h,w=image_shape[:2]
    if any(not (0<=p[0]<=w and 0<=p[1]<=h) for p in points):return None
    width=max(math.dist(points[0],points[1]),math.dist(points[2],points[3]));height=max(math.dist(points[0],points[3]),math.dist(points[1],points[2]))
    area=abs(sum(points[i][0]*points[(i+1)%4][1]-points[(i+1)%4][0]*points[i][1] for i in range(4)))/2
    if area<=1e-8 or width<=0 or height<=0 or tuple(size)!=(int(width),int(height)) or min(size)!=0:return None
    return (max(1,math.ceil(width)),max(1,math.ceil(height)))


def existing_width_rejection(points,minimum):
    """The exact pre-existing SDK predicate, with no new geometric threshold."""
    return float(points[2][0]-points[0][0]) < minimum


def install(output,repair=False):
    import numpy as np
    import docvortex.image as image
    import docvortex.foundation._image_numeric as numeric
    import mineru.model.ocr.image as crop
    original=numeric.warp_image
    def wrapped(array,matrix,size,**kw):
        try:return original(array,matrix,size,**kw)
        except Exception as exc:
            frames=inspect.stack();caller=frames[1];points=caller.frame.f_locals.get('points')
            quad=points.tolist() if hasattr(points,'tolist') else None
            candidate=qualified_size(quad,array.shape,size) if quad is not None and caller.function=='get_rotate_crop_image' else None
            record={'exception':type(exc).__name__+': '+str(exc),'traceback':traceback.format_exc(),'caller':{'file':caller.filename,'function':caller.function,'line':caller.lineno},
                    'image_shape':list(array.shape),'image_sha256':hashlib.sha256(array.tobytes()).hexdigest(),'matrix':np.asarray(matrix).tolist(),'size':list(size),'settings':kw,'points':quad,
                    'qualified_subpixel_size':candidate,'repair_enabled':repair,
                    'page_locals':[{'function':f.function,'locals':{k:v for k,v in f.frame.f_locals.items() if k in ('page_idx','page_index','page_num','page_id') and isinstance(v,(str,int))}} for f in frames]}
            evidence=Path(output)/('warp-input-'+record['image_sha256'][:20]+'.npz')
            if not evidence.exists():np.savez_compressed(evidence,image=array,matrix=np.asarray(matrix),points=np.asarray(points) if points is not None else np.empty((0,2)))
            record['exact_array_evidence']=evidence.name
            path=Path(output)/'warp-diagnostics.jsonl'
            with path.open('a') as out:out.write(json.dumps(record)+'\n')
            if (repair and str(exc)=='Unsupported warp settings' and candidate and kw.get('interpolation')=='cubic' and kw.get('border')=='replicate'):
                target=np.float32([[0,0],[candidate[0],0],[candidate[0],candidate[1]],[0,candidate[1]]]);matrix=image.perspective_matrix(points,target)
                # Caller retains its original rotation logic; no source content is dropped.
                return original(array,matrix,candidate,**kw)
            raise
    # Module-local aliases only, in this one stateless worker process.
    image.warp_image=wrapped;numeric.warp_image=wrapped;crop.warp_image=wrapped

    import sys
    import mineru.model.ocr.results as results
    original_results=results.get_ocr_result_list
    def checked_results(ocr_res,useful_list,ocr_enable,bgr_image):
        kept=[]
        for box in ocr_res:
            # Evaluate the exact raw-coordinate predicate used by upstream,
            # before its float32 crop conversion. Accepted boxes are untouched.
            if repair and ocr_enable and len(box)==4 and existing_width_rejection(box,results.OcrConfidence.min_width):
                record={'operation':'existing_min_width_guard_before_crop','width':float(box[2][0]-box[0][0]),'existing_threshold':results.OcrConfidence.min_width,'points':[[float(x) for x in p] for p in box],'useful_list':list(useful_list),'image_shape':list(bgr_image.shape),'image_sha256':hashlib.sha256(bgr_image.tobytes()).hexdigest(),'content_policy':'Exact same upstream raw-coordinate rejection predicate, reordered; no additional boxes discarded.'}
                with (Path(output)/'early-width-guard.jsonl').open('a') as out:out.write(json.dumps(record)+'\n')
                continue
            kept.append(box)
        return original_results(kept,useful_list,ocr_enable,bgr_image)
    for name,module in list(sys.modules.items()):
        if name.startswith('mineru.') and module is not None:
            for key,value in list(vars(module).items()):
                if value is original_results:setattr(module,key,checked_results)
