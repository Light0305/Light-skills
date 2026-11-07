"""Validate a measured scene, draw it visibly in Illustrator, and inspect saved AI.

No tracing/OCR. Windows bridge only; the reusable native renderer is runtime.jsx.
"""
from pathlib import Path
import argparse, hashlib, json, math, re, sys, time
HERE = Path(__file__).resolve().parent

def _validate_structure(scene, illustrator=False):
    """Reject malformed geometry before any desktop application is touched."""

    def need(ok, message):
        if not ok:
            raise ValueError(message)

    def number(value):
        return isinstance(value, (int, float)) and (not isinstance(value, bool)) and math.isfinite(value)

    def sequence(value, label):
        need(isinstance(value, list), label + ' must be a list')
        return value

    def object_(value, label):
        need(isinstance(value, dict), label + ' must be an object')
        return value

    def named(value, label):
        need(isinstance(value, str) and bool(value.strip()), label + ' must be nonempty text')
    object_(scene, 'scene')
    canvas = object_(scene.get('canvas'), 'canvas')
    for key in ('width_px', 'height_px') + (() if illustrator else ('pixels_per_inch',)):
        value = canvas.get(key)
        need(number(value) and value > 0, 'Invalid canvas ' + key)
    if illustrator:
        need(number(scene.get('points_per_pixel', 0.75)) and scene.get('points_per_pixel', 0.75) > 0, 'points_per_pixel must be finite and positive')
        for key in ('font', 'font_bold'):
            named(scene.get(key), key)
        for key in ('layers', 'groups'):
            for entry in sequence(scene.get(key), key):
                object_(entry, key + ' entry')
                named(entry.get('id'), key + ' id')
                named(entry.get('name' if key == 'layers' else 'layer'), key + ' label')
    elif 'font' in scene:
        named(scene['font'], 'font')
    pages = sequence(scene.get('pages'), 'pages')
    need(bool(pages), 'No pages')
    for page in pages:
        object_(page, 'page')
        named(page.get('name'), 'page name')
        for kind in ('nodes', 'paths', 'edges'):
            for item in sequence(page.get(kind, []), kind):
                object_(item, kind + ' item')
                named(item.get('id'), 'item id')
                for key in ('text', 'native_text'):
                    if key in item:
                        need(isinstance(item[key], str), key + ' must be text')
                if illustrator:
                    named(item.get('group'), 'item group')
                if kind == 'nodes':
                    allowed = ('rect', 'roundrect', 'ellipse', 'junction', 'text', 'polygon', 'bezier')
                    need(item.get('type') in allowed + (('compound',) if illustrator else ()), 'Unsupported node type')
                    box = item.get('bbox')
                    need(isinstance(box, list) and len(box) == 4 and all((number(v) for v in box)), 'Each node needs four finite bbox values')
                if 'radius_px' in item:
                    need(number(item['radius_px']) and item['radius_px'] >= 0, 'Invalid radius_px')
                style = object_(item.get('style', {}), 'style')
                for key in ('fill', 'fill_secondary', 'stroke', 'text_color'):
                    if key in style:
                        value = style[key]
                        need(isinstance(value, str) and (re.fullmatch('#[0-9a-fA-F]{6}', value) or (value == 'none' and key in ('fill', 'stroke'))), 'Invalid color ' + key)
                if 'fill_secondary' in style:
                    need(style.get('fill') not in (None, 'none'), 'Gradient needs a primary fill color')
                for key in ('font_px', 'stroke_px'):
                    if key in style:
                        value = style[key]
                        need(number(value) and (value > 0 if key == 'font_px' or illustrator else value >= 0), 'Invalid style ' + key)
                for key, choices in (('align', (0, 1, 2)), ('line_cap', (0, 1, 2))):
                    if key in style:
                        need(type(style[key]) is int and style[key] in choices, 'Invalid style ' + key)
                if 'bold' in style:
                    need(type(style['bold']) is bool, 'bold must be boolean')
                if 'dash_pattern' in style:
                    need(type(style['dash_pattern']) is int and style['dash_pattern'] >= 0, 'Invalid dash_pattern')
                if illustrator:
                    if 'opacity' in style:
                        need(number(style['opacity']) and 0 <= style['opacity'] <= 100, 'Invalid opacity')
                    need(style.get('gradient_type', 'linear') in ('linear', 'radial'), 'Invalid gradient_type')
                for key in ('arrow', 'begin_arrow', 'arrow_size'):
                    if key in item:
                        need(type(item[key]) is int and item[key] >= 0 or (illustrator and type(item[key]) is bool), 'Invalid ' + key)
                if kind != 'nodes' or item.get('type') in ('polygon', 'bezier'):
                    points = sequence(item.get('points'), 'points')
                    curve = item.get('curve', 'bezier' if item.get('type') == 'bezier' else 'polyline')
                    need(curve in ('polyline', 'bezier'), 'Unsupported curve')
                    need(len(points) >= 2, 'A path needs at least two points')
                    if item.get('type') == 'polygon':
                        need(len(points) >= 4, 'A polygon needs at least three vertices and closure')
                    for point in points:
                        need(isinstance(point, list) and len(point) == 2 and all((number(v) for v in point)), 'Each point needs two finite coordinates')
                if kind == 'edges':
                    for key in ('source', 'target'):
                        endpoint = object_(item.get(key), key)
                        named(endpoint.get('node'), key + ' node')
                        anchor = endpoint.get('anchor')
                        need(isinstance(anchor, list) and len(anchor) == 2 and all((number(v) and 0 <= v <= 1 for v in anchor)), 'Invalid anchor')
                if illustrator:
                    text = item.get('native_text') or item.get('text', '')
                    text_length = len(text.encode('utf-16-le')) // 2
                    if 'subscript_start' in item:
                        start = item['subscript_start']
                        need(type(start) is int and 0 <= start < text_length, 'Invalid subscript_start')
                    for run in sequence(item.get('text_runs', []), 'text_runs'):
                        object_(run, 'text run')
                        start, length = (run.get('start'), run.get('length'))
                        need(type(start) is int and type(length) is int and (start >= 0) and (length > 0) and (start + length <= text_length), 'Text run outside actual native text')
                        need(run.get('baseline', 'subscript') in ('subscript', 'superscript'), 'Invalid text baseline')
                        if 'font' in run:
                            named(run['font'], 'run font')
                    if item.get('type') == 'compound':
                        contours = sequence(item.get('contours'), 'contours')
                        need(len(contours) >= 2, 'A compound needs at least two contours')
                        for contour in contours:
                            object_(contour, 'contour')
                            need(contour.get('curve', 'polyline') in ('polyline', 'bezier'), 'Invalid contour curve')
                            pts = sequence(contour.get('points'), 'contour points')
                            need(len(pts) >= 4, 'Closed contour needs at least four points')
                            for point in pts:
                                need(isinstance(point, list) and len(point) == 2 and all((number(v) for v in point)), 'Invalid contour point')

def _validate_scene(scene):
    _validate_structure(scene, True)
    if not scene['schema_version'] in ('1.0', '1.1'):
        raise ValueError('Invalid scene or operation arguments')
    w, h = (scene['canvas']['width_px'], scene['canvas']['height_px'])
    if not (0 < w <= 16000 and 0 < h <= 16000):
        raise ValueError('Invalid scene or operation arguments')
    if not (scene.get('font') and scene.get('font_bold')):
        raise ValueError('Invalid scene or operation arguments')
    if not scene.get('points_per_pixel', 0.75) > 0:
        raise ValueError('Invalid scene or operation arguments')
    layers = {v['id'] for v in scene['layers']}
    groups = {v['id']: v for v in scene['groups']}
    if not (len(layers) == len(scene['layers']) and len(groups) == len(scene['groups'])):
        raise ValueError('Invalid scene or operation arguments')
    for v in groups.values():
        if not v['layer'] in layers:
            raise ValueError('Invalid scene or operation arguments')
    if not len(scene['pages']) == 1:
        raise ValueError('One scene per AI document; use separate cases for separate artboards.')
    pg = scene['pages'][0]
    nodes = {n['id']: n for n in pg['nodes']}
    items = pg['nodes'] + pg['paths'] + pg['edges']
    ids = [v['id'] for v in items]
    if not len(set(ids)) == len(ids):
        raise ValueError('Invalid scene or operation arguments')
    order = pg['draw_order']
    if not (len(order) == len(ids) and set(order) == set(ids)):
        raise ValueError('Invalid scene or operation arguments')

    def points(p, curve, closed=False):
        if not (len(p) >= 2 and all((len(a) == 2 and all((math.isfinite(x) for x in a)) for a in p))):
            raise ValueError('Invalid scene or operation arguments')
        if not all((-0.2 <= a[0] <= w + 0.2 and -0.2 <= a[1] <= h + 0.2 for a in p)):
            raise ValueError('Invalid scene or operation arguments')
        if curve == 'bezier':
            if not (len(p) - 1) % 3 == 0:
                raise ValueError('Invalid scene or operation arguments')
        if closed:
            if not math.dist(p[0], p[-1]) < 0.001:
                raise ValueError('Invalid scene or operation arguments')
    for v in items:
        if not re.fullmatch('[a-zA-Z][a-zA-Z0-9_]*', v['id']):
            raise ValueError('Invalid scene or operation arguments')
        if not v['group'] in groups:
            raise ValueError('Invalid scene or operation arguments')
        s = v.get('style', {})
        for k in ('fill', 'fill_secondary', 'stroke', 'text_color'):
            if k in s:
                if not (s[k] == 'none' or re.fullmatch('#[0-9a-fA-F]{6}', s[k])):
                    raise ValueError('Invalid scene or operation arguments')
        if 'bbox' in v:
            x, y, ww, hh = v['bbox']
            if not (all((math.isfinite(t) for t in v['bbox'])) and ww > 0 and (hh > 0)):
                raise ValueError('Invalid scene or operation arguments')
            if not (min(x, y) >= -0.2 and x + ww <= w + 0.2 and (y + hh <= h + 0.2)):
                raise ValueError(v['id'])
        if 'points' in v:
            points(v['points'], v.get('curve', 'bezier' if v.get('type') == 'bezier' else 'polyline'), v.get('type') in ('bezier', 'polygon'))
        if v.get('type') == 'compound':
            if not len(v['contours']) >= 2:
                raise ValueError('Invalid scene or operation arguments')
            for c in v['contours']:
                points(c['points'], c.get('curve', 'polyline'), True)
        if 'source' in v:
            for key, idx in (('source', 0), ('target', -1)):
                ref = v[key]
                n = nodes[ref['node']]
                x, y, ww, hh = n['bbox']
                u, z = ref['anchor']
                if not (0 <= u <= 1 and 0 <= z <= 1):
                    raise ValueError('Invalid scene or operation arguments')
                if not math.dist([x + ww * u, y + hh * z], v['points'][idx]) <= 0.2:
                    raise ValueError(v['id'])
    return {'nodes': len(pg['nodes']), 'paths': len(pg['paths']), 'logical_edges': len(pg['edges']), 'authored_objects': len(items)}

def validate(scene):
    try:
        return _validate_scene(scene)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValueError("Malformed scene: " + str(exc)) from exc


def foreground():
    import win32gui, win32con
    hits = []

    def visit(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and 'Adobe Illustrator' in win32gui.GetWindowText(hwnd):
            hits.append(hwnd)
    win32gui.EnumWindows(visit, None)
    for hwnd in hits[:1]:
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('operation', choices=['validate', 'render', 'verify'])
    ap.add_argument('scene', type=Path)
    ap.add_argument('ai', type=Path, nargs='?')
    ap.add_argument('--stem', type=Path)
    ap.add_argument('--delay-ms', type=int, default=35)
    ap.add_argument('--redraw-every', type=int, default=2)
    ap.add_argument('--progid', default='Illustrator.Application.30')
    args = ap.parse_args()
    scene = json.loads(args.scene.read_text('utf8'))
    counts = validate(scene)
    if args.operation == 'validate':
        print(json.dumps(counts))
        return
    if not (args.ai and args.ai.suffix.lower() == '.ai' and args.stem):
        raise ValueError('Invalid scene or operation arguments')
    if not (0 <= args.delay_ms <= 2000 and 1 <= args.redraw_every <= 100):
        raise ValueError('Invalid scene or operation arguments')
    ai = args.ai.resolve()
    stem = args.stem.resolve()
    stem.parent.mkdir(parents=True, exist_ok=True)
    ai.parent.mkdir(parents=True, exist_ok=True)
    suffixes = ('.png', '.pdf', '.svg', '.audit.json', '.verify-progress.json', '.pdf-source.ai') if args.operation == 'verify' else ('.drawing.jsonl', '.render.json')
    for suffix in suffixes + ('.failure.json',):
        if stem.with_suffix(suffix).exists():
            raise FileExistsError(stem.with_suffix(suffix))
    if args.operation == 'render' and ai.exists():
        raise FileExistsError(ai)
    if args.operation == 'verify' and (not ai.is_file()):
        raise FileNotFoundError(ai)
    import win32com.client, pythoncom
    pythoncom.CoInitialize()
    config = {'operation': args.operation, 'scene': str(args.scene.resolve()).replace('\\', '/'), 'ai': ai.as_posix(), 'stem': stem.as_posix(), 'delay_ms': args.delay_ms, 'redraw_every': args.redraw_every}
    code = 'var LD_CONFIG=' + json.dumps(config, ensure_ascii=True) + ';\n' + (HERE / 'runtime.jsx').read_text('utf8')
    started = time.monotonic()
    phase = 'connect'
    try:
        app = win32com.client.Dispatch(args.progid)
        foreground()
        phase = 'execute'
        result = app.DoJavaScript(code)
        phase = 'read_audit'
        report_path = stem.with_suffix('.audit.json' if args.operation == 'verify' else '.render.json')
        if not str(result).startswith('OK|'):
            raise RuntimeError(result)
        report = json.loads(report_path.read_text('utf-8-sig'))
        report.update(ai_sha256=hashlib.sha256(ai.read_bytes()).hexdigest(), scene_sha256=hashlib.sha256(args.scene.read_bytes()).hexdigest(), bridge_elapsed_s=round(time.monotonic() - started, 3))
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
        print(json.dumps({k: v for k, v in report.items() if k not in ('items', 'text', 'movement', 'edge_checks', 'geometry_checks', 'bounds')}, ensure_ascii=False, indent=2))
        if not report.get('passed'):
            sys.exit(1)
    except Exception as exc:
        # A COM/server failure may bypass the ExtendScript catch block.
        # Preserve a native failure record if it exists; never invent an audit.
        failure = stem.with_suffix('.failure.json')
        if not failure.exists():
            failure.write_text(json.dumps({
                'passed': False, 'phase': phase, 'error': str(exc),
                'operation': args.operation, 'ai': str(ai),
                'scene': str(args.scene.resolve()),
                'elapsed_s': round(time.monotonic() - started, 3),
                'scope': 'Bridge failure; application work may be partial. Inspect before retrying.'
            }, ensure_ascii=False, indent=2), encoding='utf-8')
        raise
    finally:
        pythoncom.CoUninitialize()
if __name__ == '__main__':
    main()
