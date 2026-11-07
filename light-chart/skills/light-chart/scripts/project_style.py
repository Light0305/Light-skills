"""Shared JSON contract for Python/R colors, group identity and typography."""
from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

DEFAULT = Path(__file__).resolve().parent.parent / 'assets/project-style.json'
_ACTIVE = ContextVar('light_chart_project', default=None)


def load_project(path=None):
    from matplotlib.colors import is_color_like
    path = Path(path or DEFAULT).resolve()
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported project-style schema')
    for key in ('fonts', 'typography', 'roles', 'palettes', 'groups', 'metrics'):
        if not isinstance(data.get(key), dict):
            raise ValueError(f'Missing project object: {key}')
    if any(not isinstance(data['fonts'].get(k),str) or not data['fonts'][k].strip() for k in ('latin','cjk')):
        raise ValueError('Latin and CJK font names are required')
    if not isinstance(data['fonts'].get('serif'),bool):
        raise ValueError('fonts.serif must be true or false')
    for key in ('base_pt', 'minimum_pt', 'heading_pt'):
        val = data['typography'].get(key)
        if not isinstance(val, (int, float)) or not math.isfinite(val) or val <= 0:
            raise ValueError(f'Invalid typography {key}')
    if min(data['typography'][k] for k in ('base_pt','heading_pt')) < data['typography']['minimum_pt']:
        raise ValueError('Base font is smaller than the project minimum')
    required = {'ink','muted','baseline','primary','secondary','accent','pale','missing','down','up'}
    if not required <= data['roles'].keys() or not all(is_color_like(c) for c in data['roles'].values()):
        raise ValueError('Missing or invalid semantic colors')
    for key, count in [('categorical', 1), ('sequential', 2), ('diverging', 3)]:
        values = data['palettes'].get(key, [])
        if len(values) < count or not all(is_color_like(c) for c in values):
            raise ValueError(f'Invalid {key} palette')
    if len(data['palettes']['diverging']) != 3:
        raise ValueError('Diverging palette needs low, center and high colors')
    for label, spec in data['groups'].items():
        if not isinstance(spec, dict) or not is_color_like(spec.get('color')):
            raise ValueError(f'Group {label!r} needs an explicit color')
    for label, spec in data['metrics'].items():
        if not isinstance(spec, dict) or spec.get('direction') not in {'min','max','none'}:
            raise ValueError(f'Metric {label!r} needs direction=min/max/none')
    data['_path'] = str(path)
    data['_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    return data


def current_project():
    return _ACTIVE.get() or load_project()


def use_project(path=None):
    """Set this execution context's style for APIs that change global rcParams.

    Prefer project_context for local work; this never edits installed defaults.
    """
    data=load_project(path)
    _ACTIVE.set(data)
    return data


def role(name):
    return current_project()['roles'][name]


def palette(name='categorical'):
    return list(current_project()['palettes'][name])


def colors_for(labels):
    labels = list(labels)
    groups = current_project()['groups']
    if groups:
        absent = [str(x) for x in labels if str(x) not in groups]
        if absent:
            raise ValueError('Unmapped project groups: ' + ', '.join(absent))
        return [groups[str(x)]['color'] for x in labels]
    colors = palette()
    if len(labels) > len(colors):
        raise ValueError('Too many categories; define named group colors instead of cycling')
    return colors[:len(labels)]


def encodings_for(labels):
    """Keep identity, color and optional redundant channels together across plots."""
    labels=list(map(str,labels)); colors=colors_for(labels); groups=current_project()['groups']
    return {name:{**groups.get(name,{}),'color':color} for name,color in zip(labels,colors)}


def colormap(diverging=False):
    from matplotlib.colors import LinearSegmentedColormap
    key = 'diverging' if diverging else 'sequential'
    # Odd LUT length includes the exact diverging center; sRGB channel
    # interpolation matches circlize::colorRamp2(space='sRGB') in native R.
    return LinearSegmentedColormap.from_list('light_chart_' + key, palette(key),N=257).with_extremes(bad=role('missing'))


def resolved_fonts(project=None):
    from matplotlib import font_manager as fm
    data = project or current_project()
    available = {f.name for f in fm.fontManager.ttflist}
    serif = data['fonts'].get('serif', False)
    latin = [data['fonts'].get('latin'), 'Times New Roman' if serif else 'Arial',
             'DejaVu Serif' if serif else 'DejaVu Sans']
    cjk = [data['fonts'].get('cjk'), 'SimSun' if serif else 'Microsoft YaHei',
           'Noto Serif CJK SC' if serif else 'Noto Sans CJK SC', 'SimHei']
    latin = next((f for f in latin if f in available), None)
    cjk = next((f for f in cjk if f in available), None)
    if not latin:
        raise RuntimeError('No usable Latin font')
    return {'latin': latin, 'cjk': cjk}


def rc_params(project=None, *, lang='en'):
    from cycler import cycler
    data = project or current_project()
    fonts = resolved_fonts(data)
    if lang not in {'en','zh'}:
        raise ValueError('lang must be en or zh')
    if lang == 'zh' and not fonts['cjk']:
        raise RuntimeError('Chinese text requires an installed CJK font')
    # Native Arial/Times may lack scientific symbols, including subscripts.
    fallback = 'DejaVu Serif' if data['fonts'].get('serif') else 'DejaVu Sans'
    family = list(dict.fromkeys([fonts['latin'], fallback] + ([fonts['cjk']] if lang == 'zh' else [])))
    t = data['typography']
    return {'font.family': family, 'font.size': t['base_pt'], 'axes.labelsize': t['base_pt'],
            'axes.titlesize': t['heading_pt'], 'xtick.labelsize': t['base_pt'],
            'ytick.labelsize': t['base_pt'], 'legend.fontsize': t['base_pt'],
            'text.color': data['roles']['ink'], 'axes.labelcolor': data['roles']['ink'],
            'axes.prop_cycle': cycler(color=data['palettes']['categorical']),
            'axes.spines.top': False, 'axes.spines.right': False, 'axes.linewidth': .6,
            'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
            'axes.unicode_minus': True, 'legend.frameon': False}


@contextmanager
def project_context(path=None, *, lang='en'):
    import matplotlib as mpl
    data = load_project(path) if not isinstance(path, dict) else deepcopy(path)
    token = _ACTIVE.set(data)
    try:
        with mpl.rc_context(rc_params(data, lang=lang)):
            yield data
    finally:
        _ACTIVE.reset(token)


def snapshot():
    data = deepcopy(current_project())
    data['resolved_fonts'] = resolved_fonts(data)
    return data
