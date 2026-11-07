"""Inspect data marks, bind reviews to exact exports and compare revisions.

Combines SciPilot's rendered loop, Nature's data/export checks, FigMirror's
preserve-and-compare discipline and figures4papers' consistent visual mappings.
Geometry diagnostics do not replace a visual or scientific review.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _coordinates(ax):
    """Yield data-coordinate marks, including intervals, excluding axis guides."""
    from matplotlib.collections import PathCollection, LineCollection, PolyCollection
    from matplotlib.patches import Rectangle, PathPatch
    for i, line in enumerate(ax.lines):
        if line.get_visible() and line.get_transform() is ax.transData:
            yield f'line:{i}', line, np.asarray(line.get_xydata(), float), line.get_transform()
    for i, item in enumerate(ax.collections):
        if not item.get_visible():
            continue
        if isinstance(item, PathCollection) and item.get_offset_transform() is ax.transData:
            yield f'scatter:{i}', item, np.ma.asarray(item.get_offsets()).filled(np.nan), item.get_offset_transform()
        elif isinstance(item, LineCollection) and item.get_transform() is ax.transData:
            seg = item.get_segments()
            if seg:
                yield f'interval:{i}', item, np.concatenate(seg), item.get_transform()
        elif isinstance(item, PolyCollection) and item.get_transform() is ax.transData:
            from matplotlib.transforms import AffineDeltaTransform
            offsets = item.get_offsets()
            if len(offsets) > 1 and isinstance(item.get_offset_transform(), AffineDeltaTransform):
                # Matplotlib hexbin stores one origin-centered hexagon plus
                # data-space centers. That template is not evidence at (0,0).
                yield f'binned:{i}', item, np.asarray(offsets,float), ax.transData
            else:
                paths = [p.vertices for p in item.get_paths()]
                if paths:
                    yield f'filled:{i}', item, np.concatenate(paths), item.get_transform()
    for i, item in enumerate(ax.patches):
        if item.get_visible() and isinstance(item, Rectangle) and item.get_data_transform() is ax.transData:
            x, y = item.get_xy(); w, h = item.get_width(), item.get_height()
            yield f'bar:{i}', item, np.array([[x,y], [x+w,y+h]]), item.get_data_transform()
        elif item.get_visible() and isinstance(item, PathPatch) and item.get_transform() is ax.transData:
            # Static alluvial ribbons retain their actual Bezier endpoints and
            # control vertices through clipping/revision checks, not just nodes.
            yield f'path:{i}', item, np.asarray(item.get_path().vertices, float), item.get_transform()


def audit_marks(fig, axes=None):
    """Catch clipped finite mark vertices and legend intersections on 2D axes.

    Nonfinite vertices are breaks/masks, not observations to invent. Explicit
    scientific crops may be legitimate and must be resolved during actual review.
    """
    from audit_figure_collisions import segment_intersects_rect
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    findings = []
    for index, ax in enumerate(fig.axes if axes is None else axes):
        if hasattr(ax, 'zaxis') or not ax.get_visible():
            continue
        key = ax.get_label() or f'axes-{index}'
        bounds = ax.get_window_extent(renderer)
        legend = ax.get_legend()
        lb = legend.get_window_extent(renderer) if legend and legend.get_visible() else None
        if lb is not None:
            lb = lb.padded(-1)
        for mark, artist, xy, transform in _coordinates(ax):
            if not len(xy):
                continue
            pixels = transform.transform(xy)
            finite = np.isfinite(xy).all(axis=1) & np.isfinite(pixels).all(axis=1)
            p = pixels[finite]
            outside = (p[:,0] < bounds.x0-1) | (p[:,0] > bounds.x1+1) | (p[:,1] < bounds.y0-1) | (p[:,1] > bounds.y1+1)
            if outside.any() and artist.get_clip_on():
                findings.append({'code':'data_clipped', 'panel':key, 'mark':mark,
                    'count':int(outside.sum()), 'severity':'WARN',
                    'action':'Inspect source limits and full intervals; change limits/layout or document an intentional crop.'})
            if lb is None:
                continue
            inside = (p[:,0] >= lb.x0) & (p[:,0] <= lb.x1) & (p[:,1] >= lb.y0) & (p[:,1] <= lb.y1)
            hit = bool(inside.any())
            if not hit and mark.startswith('line:'):
                for a, b in zip(pixels, pixels[1:]):
                    if np.isfinite([a,b]).all() and segment_intersects_rect((tuple(a),tuple(b)), tuple(lb.extents)):
                        hit = True; break
            if hit:
                findings.append({'code':'legend_over_data', 'panel':key, 'mark':mark,
                    'severity':'WARN', 'action':'Move legend to a reserved corridor or use direct labels; preserve data marks.'})
    return findings


def _array_signature(value):
    a = np.ma.asarray(value)
    if np.ma.isMaskedArray(a):
        if a.dtype.kind in 'biu' and np.ma.getmaskarray(a).any():
            a = a.astype(float)
        a = a.filled(np.nan)
    if a.dtype.kind in 'biufc':
        a = np.asarray(a, dtype='<f8').copy()
        a[np.isnan(a)] = np.nan
        return {'shape':list(a.shape), 'sha256':hashlib.sha256(a.tobytes()).hexdigest()}
    return {'shape':list(a.shape), 'values':a.tolist()}


def figure_snapshot(fig):
    """Capture plotted evidence and named-series identity separately from layout."""
    panels, styles = {}, {}
    for i, ax in enumerate(fig.axes):
        if not ax.get_visible():
            continue
        key = ax.get_label() or f'axes-{i}'
        if key in panels:
            raise ValueError('Unique axes labels required for revision comparison: ' + key)
        marks, identified_encodings = {}, {}
        # Matplotlib stores errorbar/bar labels on containers, while the actual
        # data artist is usually '_nolegend_'. Keep this real identity for colour
        # auditing; use the primary data line rather than stylistic error caps.
        container_labels={}
        for container in ax.containers:
            label=container.get_label()
            if not label or label.startswith('_'):continue
            if type(container).__name__=='ErrorbarContainer':
                point=container.lines[0]
                children=[point] if point is not None else container.get_children()
            else:children=container.get_children()
            container_labels.update({id(child):label for child in children})
        coordinates = [] if hasattr(ax,'zaxis') else _coordinates(ax)
        for name, artist, xy, _ in coordinates:
            marks[name] = _array_signature(xy)
            # GIDs on data artists bind original cell/node/ribbon identity to
            # actual geometry. They need no public label or legend entry. Read
            # facecolors from the artists themselves, not constructor metadata;
            # ordinary anonymous patches remain free to change decoration.
            gid = artist.get_gid()
            if gid is not None:
                encoding = {'gid': gid}
                if hasattr(artist, 'get_facecolor'):
                    encoding['facecolor'] = np.asarray(artist.get_facecolor()).tolist()
                elif hasattr(artist, 'get_color'):
                    encoding['color'] = np.asarray(artist.get_color()).tolist()
                identified_encodings[name] = encoding
            label = artist.get_label()
            if not label or label.startswith('_'):label=container_labels.get(id(artist),label)
            if label and not label.startswith('_'):
                if hasattr(artist, 'get_color'):
                    color = np.asarray(artist.get_color()).tolist()
                else:
                    color = np.asarray(artist.get_facecolor()).tolist()
                styles[key+'/'+name+'/'+label] = {'color':color,'label':label}
        if hasattr(ax,'zaxis'):
            for j,line in enumerate(ax.lines):
                if hasattr(line,'get_data_3d'):
                    marks[f'line3d:{j}']=_array_signature(np.column_stack(line.get_data_3d()))
            for j,item in enumerate(ax.collections):
                if hasattr(item,'_offsets3d'):
                    marks[f'scatter3d:{j}']=_array_signature(np.column_stack(item._offsets3d))
                elif hasattr(item,'_vec'):
                    marks[f'faces3d:{j}']=_array_signature(item._vec)
                elif hasattr(item,'_faces'):
                    marks[f'faces3d:{j}']=_array_signature(item._faces)
                elif hasattr(item,'_segments3d'):
                    marks[f'segments3d:{j}']=[_array_signature(s) for s in item._segments3d]
                else:
                    raise ValueError('Unsupported native 3D geometry snapshot: '+type(item).__name__)
        for j, image in enumerate(ax.images):
            marks[f'image:{j}'] = {'pixels':_array_signature(image.get_array()),
                                  'extent':list(image.get_extent()), 'clim':list(image.get_clim())}
        # Scalar fields/heatmaps carry values as well as mesh geometry.
        for j, c in enumerate(ax.collections):
            if c.get_array() is not None:
                marks[f'array:{j}'] = _array_signature(c.get_array())
        view={'x':list(ax.get_xlim()),'y':list(ax.get_ylim())}
        labels={'x':ax.get_xlabel(),'y':ax.get_ylabel()}
        if hasattr(ax,'zaxis'):
            view['z']=list(ax.get_zlim());labels['z']=ax.get_zlabel()
        color_scales=[]
        for item in [*ax.images,*ax.collections]:
            if item.get_array() is not None:
                norm=item.norm
                color_scales.append({'type':type(item).__name__,'clim':list(item.get_clim()),
                  'norm':type(norm).__name__,'center':getattr(norm,'vcenter',None),
                  'colors':_array_signature(item.get_cmap()(np.linspace(0,1,257)))})
        panels[key] = {'marks':marks, 'xscale':ax.get_xscale(), 'yscale':ax.get_yscale(),
                       'view_limits':view,'axis_labels':labels,'color_scales':color_scales,
                       'artist_classes':sorted({type(c).__name__ for c in [*ax.lines,*ax.collections,*ax.images,*ax.patches]})}
        if identified_encodings:
            panels[key]['identified_artist_encodings'] = identified_encodings
    return {'panels':panels, 'named_series_colors':styles}


def bind_exports(report, *, pdf, png=None, additional_exports=()):
    """Generate a final-PDF raster and hash exports; usable with Python or R QA."""
    import fitz
    pdf = Path(pdf).resolve()
    preview = pdf.with_suffix('.pdf-preview.png')
    with fitz.open(pdf) as doc:
        if len(doc) != 1:
            raise ValueError('One-page figure required')
        doc[0].get_pixmap(dpi=160, alpha=False).save(preview)
    files = [pdf, preview]
    if png is not None:
        files.append(Path(png).resolve())
    files.extend(Path(path).resolve() for path in additional_exports)
    if len({p.name for p in files}) != len(set(files)):
        raise ValueError('Export filenames must be distinct')
    report['review_artifacts'] = {p.name:{'path':str(p), 'sha256':sha(p)} for p in files}
    report['visual_review'] = {'status':'pending', 'notes':[],
                               'scope':'Executor inspection must name the exact current PNG and PDF render.'}
    return report


def verify_exports(report):
    assets = report.get('review_artifacts', {})
    if not assets:
        return ['No revision-bound exports were recorded.']
    if not isinstance(assets, dict):
        return ['Malformed review_artifacts']
    errors = []
    for name, item in assets.items():
        try:
            if not Path(item['path']).is_file() or sha(item['path']) != item['sha256']:
                errors.append(str(name)+' changed or is missing')
        except (KeyError, OSError, TypeError, ValueError):
            errors.append('Export unavailable or malformed: '+str(name))
    return errors


def compare_revisions(previous, current, *, required_panels=(), required_classes=None):
    """Detect evidence/identity regression; never rank aesthetics with a scalar."""
    errors = verify_exports(previous) + verify_exports(current)
    if previous.get('source_data_sha256') != current.get('source_data_sha256'):
        errors.append('Source records changed between revisions.')
    if not current.get('source_data_sha256'):
        errors.append('Source records are not bound to the revision.')
    before, after = previous.get('figure_snapshot'), current.get('figure_snapshot')
    changes = []
    if before is None or after is None:
        errors.append('No comparable artist snapshots; source-data comparison and manual review required.')
    else:
        for panel in required_panels:
            if panel not in after['panels']:
                errors.append('Required panel missing: '+panel)
        for panel, classes in (required_classes or {}).items():
            actual = after['panels'].get(panel, {}).get('artist_classes', [])
            for name in classes:
                if name not in actual:
                    errors.append(f'Required construction missing: {panel}/{name}')
        for panel, content in before['panels'].items():
            if panel not in after['panels']:
                errors.append('Panel removed: '+panel)
            elif content['marks'] != after['panels'][panel]['marks']:
                changes.append('Plotted values/marks changed: '+panel)
            elif (content['xscale'],content['yscale']) != (after['panels'][panel]['xscale'],after['panels'][panel]['yscale']):
                changes.append('Axis scale changed: '+panel)
            for field,label in [('view_limits','View limits'),('axis_labels','Axis labels/units'),
                                ('color_scales','Scalar color encoding'),
                                ('identified_artist_encodings','Identified data-artist encoding')]:
                if panel not in after['panels']:continue
                newer=after['panels'][panel]
                if (field in content)!=(field in newer):
                    changes.append(f'Encoding metadata availability changed: {panel}/{field}')
                elif content.get(field)!=newer.get(field):
                    changes.append(label+' changed: '+panel)
        if before['named_series_colors'] != after['named_series_colors']:
            changes.append('Named-series color mapping changed.')
    def codes(r):
        return {(x['code'],x['panel'],x['mark']) for x in r.get('mark_issues', [])}
    old, new = codes(previous), codes(current)
    return {'status':'regression' if errors or changes else 'no_evidence_regression',
            'errors':errors, 'changes_requiring_justification':changes,
            'resolved_mark_findings':[list(x) for x in sorted(old-new)],
            'new_mark_findings':[list(x) for x in sorted(new-old)],
            'boundary':'Different construction may be justified by data; preserve prior draft and document that decision.'}


def record_review(qa_path, *, inspected, observations, unresolved=(), previous=None,
                  required_panels=(), required_classes=None, resolutions=(), justified_changes=None):
    """Record executor review after actual viewing, refusing stale files/unchecked regressions.

    inspected is a list of paths actually viewed; observations are specific notes.
    This cannot prove a person/model saw pixels and never claims independence.
    """
    path = Path(qa_path)
    report = json.loads(path.read_text(encoding='utf-8'))
    from source_binding import verify_sources, binding_scope
    errors = verify_exports(report) + verify_sources(report)
    seen = {str(Path(p).resolve()) for p in inspected}
    for name, item in report.get('review_artifacts', {}).items():
        if name.endswith('.png') and item['path'] not in seen:
            errors.append('Current rendered artifact not inspected: '+name)
    if not observations or not all(isinstance(s,str) and s.strip() for s in observations):
        errors.append('Specific observations required.')
    snapshot = report.get('figure_snapshot', {}).get('panels', {})
    for panel in required_panels:
        if panel not in snapshot:
            errors.append('Required panel missing: '+panel)
    for panel, classes in (required_classes or {}).items():
        actual = snapshot.get(panel, {}).get('artist_classes', [])
        for name in classes:
            if name not in actual:
                errors.append(f'Required construction missing: {panel}/{name}')
    resolved = {(r.get('code'),r.get('panel'),r.get('mark')) for r in resolutions
                if r.get('evidence','').strip() and r.get('decision') in {'intentional','nonblocking'}}
    if not unresolved:
        for issue in report.get('mark_issues', []):
            if (issue['code'],issue['panel'],issue['mark']) not in resolved:
                errors.append('Mark finding needs revision or a specific evidenced resolution: '+str(issue))
    comparison = None
    if previous:
        prior = json.loads(Path(previous).read_text(encoding='utf-8'))
        comparison = compare_revisions(prior, report, required_panels=required_panels, required_classes=required_classes)
        justified_changes = justified_changes or {}
        unchecked = [c for c in comparison['changes_requiring_justification'] if not str(justified_changes.get(c,'')).strip()]
        if comparison['errors'] or unchecked:
            errors.append('Revision regression needs a scientific/design decision; automatic acceptance refused.')
        elif comparison['status'] == 'regression':
            comparison['status'] = 'changes_justified_by_executor'
            comparison['justifications'] = justified_changes
    if report.get('automated_status') in {'FAIL','NOT_AUDITABLE','IN_PROGRESS'}:
        errors.append('Technical checks remain unresolved.')
    if errors:
        raise ValueError('; '.join(errors))
    report['visual_review'] = {'status':'needs_revision' if unresolved else 'self_reviewed',
        'reviewer':'executor', 'inspected':sorted(seen), 'notes':observations,
        'unresolved':list(unresolved), 'resolutions':list(resolutions),
        'binding_scope':binding_scope(report),
        'source_hashes':{k:v['sha256'] for k,v in report.get('source_manifest', {}).items()},
        'artifact_hashes':{k:v['sha256'] for k,v in report['review_artifacts'].items()}}
    if comparison:
        report['revision_comparison'] = comparison
    from publication import write_json
    write_json(path, report)
    return report
