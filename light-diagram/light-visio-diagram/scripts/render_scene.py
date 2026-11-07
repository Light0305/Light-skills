"""Render an inspected, manually authored pixel scene as native Visio shapes.

Requires Windows, desktop Visio and pywin32. No image recognition is performed.
Each invocation owns a separate Visio instance; it never attaches to user drawings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import sys
import zipfile
import xml.etree.ElementTree as ET



def _validate_structure(scene, illustrator=False):
    """Reject malformed geometry before any desktop application is touched."""
    def need(ok, message):
        if not ok:
            raise ValueError(message)
    def number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
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
        need(number(scene.get('points_per_pixel', .75)) and scene.get('points_per_pixel', .75) > 0,
             'points_per_pixel must be finite and positive')
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
                    need(item.get('type') in allowed + (('compound',) if illustrator else ()),
                         'Unsupported node type')
                    box = item.get('bbox')
                    need(isinstance(box, list) and len(box) == 4 and all(number(v) for v in box),
                         'Each node needs four finite bbox values')
                if 'radius_px' in item:
                    need(number(item['radius_px']) and item['radius_px'] >= 0, 'Invalid radius_px')
                style = object_(item.get('style', {}), 'style')
                for key in ('fill', 'fill_secondary', 'stroke', 'text_color'):
                    if key in style:
                        value = style[key]
                        need(isinstance(value, str) and (re.fullmatch(r'#[0-9a-fA-F]{6}', value)
                             or value == 'none' and key in ('fill', 'stroke')), 'Invalid color ' + key)
                if 'fill_secondary' in style:
                    need(style.get('fill') not in (None, 'none'), 'Gradient needs a primary fill color')
                for key in ('font_px', 'stroke_px'):
                    if key in style:
                        value = style[key]
                        need(number(value) and (value > 0 if key == 'font_px' or illustrator else value >= 0),
                             'Invalid style ' + key)
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
                        need((type(item[key]) is int and item[key] >= 0)
                             or illustrator and type(item[key]) is bool, 'Invalid ' + key)
                if kind != 'nodes' or item.get('type') in ('polygon', 'bezier'):
                    points = sequence(item.get('points'), 'points')
                    curve = item.get('curve', 'bezier' if item.get('type') == 'bezier' else 'polyline')
                    need(curve in ('polyline', 'bezier'), 'Unsupported curve')
                    need(len(points) >= 2, 'A path needs at least two points')
                    if item.get('type') == 'polygon':
                        need(len(points) >= 4, 'A polygon needs at least three vertices and closure')
                    for point in points:
                        need(isinstance(point, list) and len(point) == 2 and all(number(v) for v in point),
                             'Each point needs two finite coordinates')
                if kind == 'edges':
                    for key in ('source', 'target'):
                        endpoint = object_(item.get(key), key)
                        named(endpoint.get('node'), key + ' node')
                        anchor = endpoint.get('anchor')
                        need(isinstance(anchor, list) and len(anchor) == 2
                             and all(number(v) and 0 <= v <= 1 for v in anchor), 'Invalid anchor')
                if illustrator:
                    text = item.get('native_text') or item.get('text', '')
                    # Illustrator character ranges use UTF-16 code units.
                    text_length = len(text.encode('utf-16-le')) // 2
                    if 'subscript_start' in item:
                        start = item['subscript_start']
                        need(type(start) is int and 0 <= start < text_length, 'Invalid subscript_start')
                    for run in sequence(item.get('text_runs', []), 'text_runs'):
                        object_(run, 'text run')
                        start, length = run.get('start'), run.get('length')
                        need(type(start) is int and type(length) is int and start >= 0 and length > 0
                             and start + length <= text_length, 'Text run outside actual native text')
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
                                need(isinstance(point, list) and len(point) == 2 and all(number(v) for v in point),
                                     'Invalid contour point')

def _validate_scene(scene):
    _validate_structure(scene)
    if scene.get('schema_version') != '1.0':
        raise ValueError('schema_version must be 1.0')
    for key in ('width_px', 'height_px', 'pixels_per_inch'):
        v = scene['canvas'][key]
        if not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise ValueError(f'Invalid canvas {key}')
    if not scene.get('pages'):
        raise ValueError('No pages')
    names, slugs = set(), set()
    for page in scene['pages']:
        if page['name'] in names:
            raise ValueError('Duplicate page name')
        names.add(page['name'])
        slug = page.get('slug', '')
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', slug) or slug in slugs:
            raise ValueError('Each page needs a unique safe lowercase slug')
        slugs.add(slug)
        ids = set()
        for item in page.get('nodes', []) + page.get('paths', []) + page.get('edges', []):
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', item['id']):
                raise ValueError('IDs must start with a letter and use letters, digits or underscores')
            if item['id'] in ids:
                raise ValueError(f'Duplicate id: {item["id"]}')
            ids.add(item['id'])
        nodes = {n['id']: n for n in page.get('nodes', [])}
        if 'draw_order' in page:
            order = page['draw_order']
            if len(order) != len(ids) or set(order) != ids:
                raise ValueError('draw_order must list every node, path and edge exactly once')
            for edge in page.get('edges', []):
                if any(order.index(edge[side]['node']) > order.index(edge['id']) for side in ('source','target')):
                    raise ValueError('An edge must be drawn after both endpoint nodes')
        w, h = scene['canvas']['width_px'], scene['canvas']['height_px']
        for n in nodes.values():
            if n['type'] not in ('rect', 'roundrect', 'ellipse', 'text', 'junction', 'bezier', 'polygon'):
                raise ValueError(f'Unsupported node: {n["type"]}')
            x, y, nw, nh = n['bbox']
            if not all(math.isfinite(t) for t in n['bbox']) or min(nw, nh) <= 0:
                raise ValueError(f'Invalid bbox: {n["id"]}')
            if min(x, y) < 0 or x+nw > w or y+nh > h:
                raise ValueError(f'Outside canvas: {n["id"]}')
            if n['type'] == 'bezier':
                if len(n.get('points', [])) < 4 or (len(n['points'])-1) % 3:
                    raise ValueError(f'Cubic Bezier needs 3k+1 control points: {n["id"]}')
                if n['points'][0] != n['points'][-1]:
                    raise ValueError('A Bezier node must be closed; use paths for open curves')
            if n['type']=='polygon' and (len(n.get('points',[]))<4 or n['points'][0]!=n['points'][-1]):
                raise ValueError('A polygon needs at least three vertices and a repeated closing point')
        for edge in page.get('edges', []):
            for side in ('source', 'target'):
                if edge[side]['node'] not in nodes:
                    raise ValueError(f'Missing {side} node: {edge["id"]}')
                if len(edge[side]['anchor']) != 2 or not all(0 <= v <= 1 for v in edge[side]['anchor']):
                    raise ValueError('Anchor must be normalized top-left coordinates')
            if len(edge['points']) < 2:
                raise ValueError('An edge needs at least two points')
            for side, index in (('source', 0), ('target', -1)):
                box = nodes[edge[side]['node']]['bbox']
                u, v = edge[side]['anchor']
                expected = (box[0]+box[2]*u, box[1]+box[3]*v)
                if math.dist(expected, edge['points'][index]) > .2:
                    raise ValueError(f'Endpoint disagrees with anchor: {edge["id"]} {side}')
        for path in page.get('paths', []) + page.get('edges', []) + [n for n in nodes.values() if n['type'] in ('bezier','polygon')]:
            if path.get('curve','polyline') not in ('polyline','bezier'):
                raise ValueError(f'Unsupported curve type: {path["id"]}')
            if path.get('curve') == 'bezier' and (len(path['points']) < 4 or (len(path['points'])-1) % 3):
                raise ValueError(f'Cubic Bezier needs 3k+1 control points: {path["id"]}')
            for pt in path['points']:
                if len(pt) != 2 or not all(math.isfinite(v) for v in pt):
                    raise ValueError(f'Invalid path: {path["id"]}')
                if not (0 <= pt[0] <= w and 0 <= pt[1] <= h):
                    raise ValueError(f'Path outside canvas: {path["id"]}')


def color(value):
    value = value.lstrip('#')
    return 'RGB(%d,%d,%d)' % tuple(int(value[i:i+2], 16) for i in (0, 2, 4))


def setcell(shape, cell, formula):
    # Unsupported cells are failures, not silently ignored formatting losses.
    shape.CellsU(cell).FormulaU = str(formula)


def identify(shape, semantic_id):
    shape.NameU = 'Light_' + semantic_id
    if not shape.SectionExists(242, 0):  # visSectionUser
        shape.AddSection(242)
    shape.AddNamedRow(242, 'LightId', 0)
    setcell(shape, 'User.LightId', '"' + semantic_id.replace('"', '""') + '"')


def style_shape(shape, item, ppi, font_id):
    st = item.get('style', {})
    setcell(shape, 'ShdwPattern', 0)
    stroke = st.get('stroke', '#0b1532')
    if stroke != 'none':
        setcell(shape, 'LineColor', color(stroke))
    setcell(shape, 'LineWeight', f'{st.get("stroke_px", 2.5)/ppi} in')
    setcell(shape, 'LinePattern', 0 if stroke == 'none' else 1)
    setcell(shape, 'LineCap', st.get('line_cap', 0))
    if st.get('dash_pattern'):
        setcell(shape, 'LinePattern', st['dash_pattern'])
    fill = st.get('fill', 'none')
    setcell(shape, 'FillPattern', 0 if fill == 'none' else 1)
    if fill != 'none':
        setcell(shape, 'FillForegnd', color(fill))
    if st.get('fill_secondary'):
        setcell(shape, 'FillBkgnd', color(st['fill_secondary']))
        setcell(shape, 'FillPattern', 25)
    setcell(shape, 'Char.Font', font_id)
    setcell(shape, 'Char.Size', f'{st.get("font_px", 25)/ppi} in')
    setcell(shape, 'Char.Color', color(st.get('text_color', '#070e26')))
    setcell(shape, 'Char.Style', 1 if st.get('bold', True) else 0)
    setcell(shape, 'Para.HorzAlign', st.get('align', 1))
    setcell(shape, 'VerticalAlign', 1)
    for cell in ('LeftMargin', 'RightMargin', 'TopMargin', 'BottomMargin'):
        setcell(shape, cell, '0 in')
    shape.Text = item.get('text', '')


def draw_node(page, node, canvas, font_id):
    ppi, height = canvas['pixels_per_inch'], canvas['height_px']
    x, y, w, h = node['bbox']
    if node['type'] in ('bezier','polygon'):
        values = [v for px,py in node['points'] for v in (px/ppi, (height-py)/ppi)]
        shape = (page.DrawBezier(values,3,0) if node['type']=='bezier' else page.DrawPolyline(values,0))
        # Visio's curve bounding box is approximate. Fit to the explicitly
        # measured bbox so normalized glue anchors remain deterministic.
        for cell,value in (('Width',w/ppi),('Height',h/ppi),
                           ('PinX',(x+w/2)/ppi),('PinY',(height-y-h/2)/ppi)):
            setcell(shape,cell,f'{value} in')
    elif node['type'] in ('ellipse', 'junction'):
        shape = page.DrawOval(x/ppi, (height-y-h)/ppi, (x+w)/ppi, (height-y)/ppi)
    else:
        shape = page.DrawRectangle(x/ppi, (height-y-h)/ppi, (x+w)/ppi, (height-y)/ppi)
    style_shape(shape, node, ppi, font_id)
    if node['type'] == 'roundrect':
        setcell(shape, 'Rounding', f'{node.get("radius_px", 10)/ppi} in')
    identify(shape, node['id'])
    return shape


def draw_path(page, item, canvas, shapes, font_id, semantic=False):
    ppi, height = canvas['pixels_per_inch'], canvas['height_px']
    values = [v for x, y in item['points'] for v in (x/ppi, (height-y)/ppi)]
    if item.get('curve') == 'bezier':
        shape = page.DrawBezier(values, 3, 8 if semantic else 0)
    else:
        shape = page.DrawPolyline(values, 0)
    if semantic:
        # DrawPolyline defaults to a 2D shape. Converting before GlueToPos is
        # essential: 2D visual arrows are not connected Visio relationships.
        shape.OneD = 1
    style_shape(shape, item, ppi, font_id)
    setcell(shape, 'FillPattern', 0)
    setcell(shape, 'EndArrow', item.get('arrow', 13))
    setcell(shape, 'EndArrowSize', item.get('arrow_size', 2))
    setcell(shape, 'BeginArrow', item.get('begin_arrow', 0))
    if item.get('radius_px'):
        setcell(shape, 'Rounding', f'{item["radius_px"]/ppi} in')
    identify(shape, item['id'])
    if semantic:
        # Prevent auto-routing from replacing explicit image-traced waypoints.
        setcell(shape, 'GlueType', 2)
        for side, cell in (('source', 'BeginX'), ('target', 'EndX')):
            anchor = item[side]['anchor']
            shape.CellsU(cell).GlueToPos(shapes[item[side]['node']], anchor[0], 1-anchor[1])
    return shape


def inspect_page(page, spec, shapes):
    connects = []
    for c in page.Connects:
        connects.append({'from_id': c.FromSheet.ID, 'from_cell': c.FromCell.Name,
                         'to_id': c.ToSheet.ID, 'to_cell': c.ToCell.Name})
    failures, arrow_failures, edges = [], [], []
    for edge in spec.get('edges', []):
        s = shapes[edge['id']]
        links = [c for c in connects if c['from_id'] == s.ID]
        src_id, dst_id = shapes[edge['source']['node']].ID, shapes[edge['target']['node']].ID
        begin_ok = any(c['from_cell'] == 'BeginX' and c['to_id'] == src_id for c in links)
        end_ok = any(c['from_cell'] == 'EndX' and c['to_id'] == dst_id for c in links)
        if not (begin_ok and end_ok and s.OneD):
            failures.append(edge['id'])
        begin_arrow, end_arrow = int(s.CellsU('BeginArrow').ResultIU), int(s.CellsU('EndArrow').ResultIU)
        if begin_arrow != edge.get('begin_arrow',0) or end_arrow != edge.get('arrow',13):
            arrow_failures.append(edge['id'])
        edges.append({'id': edge['id'], 'shape_id': s.ID, 'begin_glued': begin_ok,
                      'end_glued': end_ok, 'source': edge['source']['node'],
                      'target': edge['target']['node'], 'one_d': bool(s.OneD),
                      'begin_arrow':begin_arrow,'end_arrow':end_arrow})
    text_failures = [n['id'] for n in spec.get('nodes', [])
                     if shapes[n['id']].Text.replace('\r', '') != n.get('text', '').replace('\r', '')]
    expected = sum(len(spec.get(key, [])) for key in ('nodes', 'paths', 'edges'))
    return {'name': page.Name, 'shape_count': page.Shapes.Count, 'expected_shape_count': expected,
            'shape_count_matches': page.Shapes.Count == expected, 'edge_count': len(edges),
            'text_failures': text_failures, 'glue_failures': failures, 'arrow_failures':arrow_failures,
            'edges': edges, 'connections': connects}


def probe_movement(spec, shapes):
    """Move one connected node and restore it, verifying actual glued endpoints."""
    candidates = [n for n in spec.get('nodes', []) if n['type'] not in ('text', 'junction')]
    for node in candidates:
        incident = [(e, side, cell) for e in spec.get('edges', [])
                    for side, cell in (('source', 'Begin'), ('target', 'End'))
                    if e[side]['node'] == node['id']]
        if not incident:
            continue
        s = shapes[node['id']]
        old_x, old_y = s.CellsU('PinX').FormulaU, s.CellsU('PinY').FormulaU
        delta = (.13, .07)
        before = [(shapes[e['id']].CellsU(cell+'X').ResultIU,
                   shapes[e['id']].CellsU(cell+'Y').ResultIU) for e, _, cell in incident]
        failures = []
        try:
            s.CellsU('PinX').ResultIU += delta[0]
            s.CellsU('PinY').ResultIU += delta[1]
            for (e, _, cell), (x, y) in zip(incident, before):
                actual = (shapes[e['id']].CellsU(cell+'X').ResultIU,
                          shapes[e['id']].CellsU(cell+'Y').ResultIU)
                if math.dist(actual, (x+delta[0], y+delta[1])) > 1e-5:
                    failures.append(e['id']+':'+cell)
        finally:
            setcell(s, 'PinX', old_x)
            setcell(s, 'PinY', old_y)
        restore_ok = all(math.dist((shapes[e['id']].CellsU(cell+'X').ResultIU,
                                   shapes[e['id']].CellsU(cell+'Y').ResultIU), xy) < 1e-5
                         for (e, _, cell), xy in zip(incident, before))
        return {'node': node['id'], 'tested_endpoints': len(incident),
                'failures': failures, 'restored': restore_ok,
                'passed': not failures and restore_ok}
    return {'node': None, 'tested_endpoints': 0, 'passed': True,
            'skipped': 'No connected non-junction node; no movement behavior tested.'}


def package_summary(path):
    ns = {'v': 'http://schemas.microsoft.com/office/visio/2012/main'}
    with zipfile.ZipFile(path) as z:
        media = [n for n in z.namelist() if n.startswith('visio/media/')]
        pages = []
        for name in z.namelist():
            if re.fullmatch(r'visio/pages/page\d+\.xml', name):
                xml = ET.fromstring(z.read(name))
                pages.append({'file': name, 'shape_count': len(xml.findall('.//v:Shape', ns)),
                              'text_count': len(xml.findall('.//v:Text', ns)),
                              'connect_count': len(xml.findall('.//v:Connect', ns))})
        return {'media_entries': media, 'pages': pages}


def render(scene, output, scene_path):
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    app = win32com.client.DispatchEx('Visio.Application')
    app.Visible = True
    doc = None
    report = {'visio_version': app.Version, 'scene_sha256': hashlib.sha256(scene_path.read_bytes()).hexdigest(),
              'font': scene.get('font', 'Arial Narrow'), 'pages': [], 'reopened_pages': [],
              'movement_probes': []}
    try:
        doc = app.Documents.Add('')
        # ID is looked up from this document, not assumed across installations.
        font_id = doc.Fonts.Item(scene.get('font', 'Arial Narrow')).ID
        c = scene['canvas']
        for i, spec in enumerate(scene['pages']):
            page = doc.Pages.Item(1) if i == 0 else doc.Pages.Add()
            page.Name = spec['name']
            setcell(page.PageSheet, 'PageWidth', f'{c["width_px"]/c["pixels_per_inch"]} in')
            setcell(page.PageSheet, 'PageHeight', f'{c["height_px"]/c["pixels_per_inch"]} in')
            shapes = {}
            inventory = {item['id']:(kind,item) for kind in ('nodes','paths','edges') for item in spec.get(kind,[])}
            for id in spec.get('draw_order', list(inventory)):
                kind,item=inventory[id]
                shapes[id] = (draw_node(page,item,c,font_id) if kind=='nodes' else
                              draw_path(page,item,c,shapes,font_id,kind=='edges'))
            report['pages'].append(inspect_page(page, spec, shapes))
        doc.SaveAs(str(output))
        # Reopen in our own app, proving labels and glue survive serialization.
        doc.Close()
        doc = app.Documents.Open(str(output))
        app.Settings.SetRasterExportSize(3, c['width_px'], c['height_px'], 0)
        for page, spec in zip(doc.Pages, scene['pages']):
            shapes = {s.NameU.removeprefix('Light_'): s for s in page.Shapes}
            reopened = inspect_page(page, spec, shapes)
            report['reopened_pages'].append(reopened)
            report['movement_probes'].append(probe_movement(spec, shapes))
            page.Export(str(output.with_name(output.stem + '-' + spec['slug'] + '.png')))
            page.Export(str(output.with_name(output.stem + '-' + spec['slug'] + '.svg')))
        doc.ExportAsFixedFormat(1, str(output.with_suffix('.pdf')), 1, 0)
        doc.Save()
        app.ActiveWindow.ViewFit = 1
        report['package'] = package_summary(output)
        report['sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
        report['passed'] = (not report['package']['media_entries'] and
                            all(p['shape_count_matches'] and not p['glue_failures'] and not p['text_failures'] and not p['arrow_failures']
                                for p in report['reopened_pages']) and
                            all(p['passed'] for p in report['movement_probes']))
        output.with_suffix('.audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'output': str(output), 'visio_version': report['visio_version'],
                          'passed': report['passed'], 'pages': [{k: p[k] for k in ('name', 'shape_count', 'edge_count', 'glue_failures', 'text_failures')}
                                                               for p in report['reopened_pages']]}, ensure_ascii=False, indent=2))
        if not report['passed']:
            raise RuntimeError('Saved document audit failed; inspect .audit.json')
        # Leave only the newly created saved drawing visible for user inspection.
    except Exception:
        # Never touch an existing Visio process. Close only this owned instance.
        if doc is not None:
            doc.Saved = True
            doc.Close()
        app.Quit()
        raise
    finally:
        pythoncom.CoUninitialize()


def validate(scene):
    try:
        return _validate_scene(scene)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValueError("Malformed scene: " + str(exc)) from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    parser.add_argument('output', type=Path, nargs='?')
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    scene_path = args.scene.resolve()
    scene = json.loads(scene_path.read_text(encoding='utf-8-sig'))
    validate(scene)
    if args.validate_only:
        print('Scene is valid.')
        return
    if not args.output or args.output.suffix.lower() != '.vsdx':
        parser.error('Specify a new output .vsdx')
    output = args.output.resolve()
    derived = [output, output.with_suffix('.pdf'), output.with_suffix('.audit.json')]
    derived += [output.with_name(output.stem+'-'+p['slug']+ext) for p in scene['pages'] for ext in ('.png', '.svg')]
    if any(p.exists() for p in derived):
        parser.error('An output file already exists; use a new output name')
    output.parent.mkdir(parents=True, exist_ok=True)
    render(scene, output, scene_path)


if __name__ == '__main__':
    main()
