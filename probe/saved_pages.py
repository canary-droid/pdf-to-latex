"""Validated saved OCR pages and local image rendering; never imports an OCR SDK."""
import math
import os
from pathlib import Path
import re
import shutil

from .common import contained, read_json, sha

COORDINATES = 'normalized [x0,y0,x1,y1], top-left origin, x right, y down on the original upright page'


def valid_bbox(value):
    return (isinstance(value, list) and len(value) == 4
            and all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1 for x in value)
            and value[0] < value[2] and value[1] < value[3])


def saved_pages(root, run, sources):
    from .cli import completed_integrity
    import fitz
    state = read_json(run / 'state.json')
    if state['status'] != 'conversion_completed_unreviewed':
        raise ValueError('Use a completed saved conversion run; no conversion is resumed here.')
    names = list(state['settings']['sources']) if sources == 'all' else sources.split(',')
    if not names or len(set(names)) != len(names):
        raise ValueError('Select distinct saved sources.')
    pages, seen = [], set()
    for name in names:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name not in state['settings']['sources']:
            raise ValueError('Unknown or invalid saved source: ' + name)
        source = state['settings']['sources'][name]
        if sha(contained(root, source['pdf'])) != source['sha256']:
            raise ValueError('Registered source hash changed: ' + name)
        for unit, record in state['units'].items():
            if record['source_id'] != name:
                continue
            if record['status'] != 'completed' or not completed_integrity(run, record):
                raise ValueError('Saved output/source evidence changed or incomplete: ' + unit)
            attempt = contained(run, record['attempt'])
            mapping = read_json(attempt / 'page-map.json')
            payload = read_json(attempt / 'output/middle_json.json')
            if payload.get('schema') != 'docvortex.middle' or payload.get('schema_version') != '2.0':
                raise ValueError('Unsupported saved structured OCR schema')
            native_pages = payload.get('pages')
            if (not isinstance(native_pages, list)
                    or any(not isinstance(p,dict) or type(p.get('page_idx')) is not int for p in native_pages)
                    or sorted(p['page_idx'] for p in native_pages) != list(range(len(mapping)))):
                raise ValueError('Saved OCR page indices do not match the page map')
            with fitz.open(attempt / 'input.pdf') as pdf:
                if len(pdf) != len(mapping):
                    raise ValueError('Input PDF and page map disagree')
                for index, mapped in enumerate(mapping):
                    selected = mapped.get('selected_page')
                    if (type(mapped.get('local_page_idx')) is not int or mapped['local_page_idx'] != index or type(selected) is not int
                            or not 1 <= selected <= source['pages']
                            or mapped.get('original_physical_page') != source['original_pages'][selected-1]
                            or type(mapped.get('owner')) is not bool):
                        raise ValueError('Invalid saved page mapping')
                    if not mapped['owner']:
                        continue
                    identity = (name, selected)
                    if identity in seen:
                        raise ValueError('Duplicate owned page: ' + str(identity))
                    seen.add(identity)
                    page = next(p for p in native_pages if p['page_idx'] == index)
                    if not isinstance(page.get('blocks'), list):
                        raise ValueError('Structured page has no complete block list')
                    if pdf[index].rotation:
                        raise ValueError('Rotated PDF page metadata requires coordinate qualification before this profile can render it.')
                    page_id = f'{name}-p{selected:04d}'
                    blocks = []
                    for order, block in enumerate(page['blocks']):
                        if not isinstance(block, dict) or not isinstance(block.get('type'), str):
                            raise ValueError('Invalid structured block')
                        if block.get('bbox') is not None and not valid_bbox(block['bbox']):
                            raise ValueError('Invalid normalized block bbox')
                        blocks.append({'id':f'{page_id}:b{order}', 'reading_order':order,
                                       'source_block_index':block.get('index'), 'kind':block['type'],
                                       'bbox':block.get('bbox'),
                                       'bbox_pdf_points':([value * (pdf[index].rect.width if axis % 2 == 0 else pdf[index].rect.height)
                                                           for axis,value in enumerate(block['bbox'])] if block.get('bbox') else None),
                                       'native':block})
                    pages.append({'page_id':page_id, 'source_id':name, 'unit':unit,
                                  'source_run':str(run), 'source_attempt':record['attempt'],
                                  'source_pdf_sha256':source['sha256'], 'input_pdf_sha256':sha(attempt/'input.pdf'),
                                  'structured_sha256':sha(attempt/'output/middle_json.json'),
                                  'page_map_sha256':sha(attempt/'page-map.json'), 'page_map':mapping,
                                  'page':mapped, 'coordinate_system':COORDINATES,
                                  'width_points':pdf[index].rect.width, 'height_points':pdf[index].rect.height,
                                  'pdf_rotation_degrees':pdf[index].rotation,
                                  'reading_order_basis':'saved native blocks array order; no layout repair',
                                  'native_page':page, 'blocks':blocks})
        expected = {(name, p) for p in range(1, source['pages']+1)}
        if not expected <= seen:
            raise ValueError('Missing owned pages for source: ' + name)
    if not pages:
        raise ValueError('No owned pages in the selected saved sources')
    return pages


def copy_evidence(run, pages, destination):
    """Copy only validated local evidence, with relative asset paths intact."""
    copied = set()
    for page in pages:
        unit = page['unit']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', unit):
            raise ValueError('Invalid saved unit identifier')
        if unit in copied:
            continue
        copied.add(unit)
        source = contained(run, page['source_attempt'])
        target = destination / 'evidence' / unit
        target.mkdir(parents=True)
        for name in ('input.pdf', 'page-map.json'):
            shutil.copyfile(source/name, target/name)
        for name in ('middle_json.json', 'document.tex', 'document.md'):
            path = source/'output'/name
            if path.is_file():
                shutil.copyfile(path, target/('native-'+name))
        images = source/'output/images'
        if images.is_dir():
            shutil.copytree(images, target/'images')


def render_region(pdf_path, index, destination, *, bbox=None, rotation=0, max_edge=1400):
    """Render in source coordinates, then rotate the selected crop clockwise."""
    import fitz
    if bbox is not None and not valid_bbox(bbox):
        raise ValueError('Invalid normalized crop bbox')
    if rotation not in (0, 90, 180, 270):
        raise ValueError('Crop rotation must be 0, 90, 180 or 270 degrees clockwise')
    with fitz.open(pdf_path) as pdf:
        page = pdf[index]
        rect = page.rect
        clip = fitz.Rect(bbox[0]*rect.width, bbox[1]*rect.height,
                         bbox[2]*rect.width, bbox[3]*rect.height) if bbox else rect
        scale = max_edge / max(clip.width, clip.height)
        matrix = fitz.Matrix(scale, scale).prerotate(rotation)
        pixmap = page.get_pixmap(matrix=matrix, clip=clip, alpha=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(destination)
        return {'path':destination.name, 'sha256':sha(destination), 'bytes':destination.stat().st_size,
                'width':pixmap.width, 'height':pixmap.height, 'bbox':bbox or [0,0,1,1],
                'bbox_pdf_points':list(clip), 'pdf_to_raster_matrix':list(matrix),
                'raster_origin_pixels':[pixmap.x,pixmap.y],
                'rotation_clockwise_degrees':rotation, 'coordinate_system':COORDINATES}


def converter_idle(root, proc_root=Path('/proc')):
    """Best-effort same-user project process check, not host-wide exclusion."""
    if not proc_root.is_dir():
        raise ValueError('Cannot check owned converter processes: /proc is unavailable')
    matches = []
    for process in proc_root.iterdir():
        if not process.name.isdigit():
            continue
        try:
            if process.stat().st_uid != os.getuid():
                continue
            args = (process/'cmdline').read_bytes().split(b'\0')
            words = [x.decode('utf-8', errors='replace') for x in args if x]
            for word in words:
                if Path(word).name not in ('mineru_worker.py', 'probe.py'):
                    continue
                script = Path(word)
                if not script.is_absolute():
                    script = (process/'cwd').resolve(strict=True)/script
                if script.resolve() == root/'probe/mineru_worker.py' or (script.resolve() == root/'probe.py' and 'convert' in words):
                    matches.append(int(process.name))
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError as exc:
            raise ValueError('Cannot verify owned converter process state') from exc
    if matches:
        raise ValueError('Owned project converter processes are still present; wait for their exit: ' + str(sorted(set(matches))))
    return {'owned_converter_pids':[], 'scope':'same-user visible project processes at check time; project writer lock is not host-wide exclusion'}
