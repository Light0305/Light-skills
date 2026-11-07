"""Literal aggregate counts, denominators and auditable categorical geometry.

Nature's evidence/denominator contracts and figures4papers' complete ophthal
composition case motivate explicit margins. Unlike its fixed heatmap scale,
these constructors derive area/thickness directly from caller-supplied counts.
No cells become pseudo-individuals; a static joint table is not a time flow.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import json
import math
from numbers import Integral, Real

import numpy as np
import pandas as pd


MAX_EXACT_COUNT = 2 ** 53


@dataclass(frozen=True)
class CountTable:
    dimensions: tuple
    count_field: str
    orders: dict
    cells: tuple
    total: int
    marginals: dict
    source_sha256: str


def _cell_id(values):
    return json.dumps(list(values), ensure_ascii=False, separators=(',', ':'))


def prepare_count_table(source, *, dimensions, count, order, count_semantics):
    """Validate a complete 2/3-axis integer count table without filling cells.

Category labels are explicit nonempty text. Every Cartesian cell, including
recorded zeros, must be present once. Missing cells are unknown, not inferred
zeros. Total <=2**53 keeps normalized geometry within exact integer input
range; raw integer counts and margins remain Python integers.
"""
    from chart_plan import read_data, data_digest
    data = read_data(source)
    if (not isinstance(dimensions, (list, tuple)) or len(dimensions) not in (2, 3)
            or not all(isinstance(d, str) and d for d in dimensions)
            or len(set(dimensions)) != len(dimensions) or count in dimensions
            or not isinstance(count, str) or not count):
        raise ValueError('Declare two or three distinct categorical dimensions and a separate count field')
    dimensions = tuple(dimensions)
    if data.empty or data.columns.duplicated().any() or any(d not in data for d in (*dimensions, count)):
        raise ValueError('A nonempty table with unique columns and all mapped dimensions/count is required')
    if count_semantics != 'observed_counts':
        raise ValueError('Declare count_semantics=observed_counts; survey weights/proportions are not literal counts')
    if not isinstance(order, dict) or set(order) != set(dimensions):
        raise ValueError('Declare an explicit complete category order for every dimension')
    orders = {}
    for dim in dimensions:
        levels = order[dim]
        if (not isinstance(levels, (list, tuple)) or not levels
                or any(not isinstance(v, str) or not v.strip() for v in levels)
                or len(set(levels)) != len(levels)):
            raise ValueError('Each category order must contain unique nonempty text labels')
        values = data[dim].tolist()
        if any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError('Categorical cells need nonmissing explicit text labels; normalize codes explicitly without guessing')
        if not set(values) <= set(levels):
            raise ValueError('Observed categories absent from declared order: ' + dim)
        orders[dim] = tuple(levels)
    if data.duplicated(list(dimensions)).any():
        raise ValueError('Duplicate joint cells must be resolved explicitly; no silent summation')
    parsed = []
    for value in data[count]:
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
            raise ValueError('Counts must be finite nonnegative integers, not Boolean/text/complex values')
        if isinstance(value, Integral):
            integer = int(value)
        elif math.isfinite(float(value)) and float(value).is_integer():
            integer = int(value)
        else:
            raise ValueError('Counts must be finite nonnegative integers; fractional counts are not survey-weight support')
        if not 0 <= integer <= MAX_EXACT_COUNT:
            raise ValueError('Counts must be nonnegative and <=2**53 for exact normalized geometry')
        parsed.append(integer)
    total = sum(parsed)
    if total > MAX_EXACT_COUNT:
        raise ValueError('Total count exceeds 2**53; use an explicit exact large-integer rendering strategy')
    lookup = {tuple(data.iloc[i][d] for d in dimensions): (parsed[i], i) for i in range(len(data))}
    combinations = list(product(*(orders[d] for d in dimensions)))
    if len(lookup) != len(combinations) or any(key not in lookup for key in combinations):
        raise ValueError('Complete Cartesian joint cells required, including recorded zeros; absent cells are not inferred zero')
    margins = {dim: {level: 0 for level in orders[dim]} for dim in dimensions}
    cells = []
    for key in combinations:
        n, position = lookup[key]
        for dim, level in zip(dimensions, key): margins[dim][level] += n
        cells.append({'cell_id': _cell_id(key), 'levels': list(key), 'count': n,
                      'source_position': position, 'joint_proportion': n / total if total else None})
    return CountTable(dimensions, count, orders, tuple(cells), total, margins, data_digest(data))


def conditional_proportions(table, *, given):
    """Exact group denominator and per-cell proportion; zero group => None."""
    if (not isinstance(given, (list, tuple)) or not given or len(set(given)) != len(given)
            or any(d not in table.dimensions for d in given)):
        raise ValueError('given must name unique existing conditioning dimensions')
    indices = [table.dimensions.index(d) for d in given]
    denominators = {}
    for cell in table.cells:
        key = tuple(cell['levels'][i] for i in indices)
        denominators[key] = denominators.get(key, 0) + cell['count']
    return [{'cell_id': cell['cell_id'], 'given': {d: cell['levels'][i] for d, i in zip(given, indices)},
             'count': cell['count'], 'denominator': denominators[tuple(cell['levels'][i] for i in indices)],
             'proportion': cell['count'] / denominators[tuple(cell['levels'][i] for i in indices)]
                if denominators[tuple(cell['levels'][i] for i in indices)] else None}
            for cell in table.cells]


def _palette(table, color_dimension, colors):
    from matplotlib.colors import to_rgba
    if color_dimension not in table.dimensions or not isinstance(colors, dict) or set(colors) != set(table.orders[color_dimension]):
        raise ValueError('Explicit color_dimension and complete category-to-color mapping required')
    for value in colors.values():
        rgba = to_rgba(value)
        if rgba[3] != 1: raise ValueError('Use opaque category colors; small-area transparency must not erase count support')
    return table.dimensions.index(color_dimension)


def plot_mosaic(ax, table, *, colors, color_dimension):
    """Two-axis statistical mosaic: rectangle area is exactly count/total.

No artificial gaps or minimum widths/heights are added. Zero-count cells and
zero-total categories retain IDs/geometry records and have zero actual area.
Long labels can be placed by the caller in a dedicated legend/layout corridor.
"""
    from matplotlib.patches import Rectangle
    if len(table.dimensions) != 2: raise ValueError('Statistical mosaic requires exactly two dimensions')
    ci = _palette(table, color_dimension, colors)
    first, second = table.dimensions
    geometry, artists, x = [], {}, 0.
    for a in table.orders[first]:
        marginal = table.marginals[first][a]
        width = marginal / table.total if table.total else 0.
        y = 0.
        for cell in (c for c in table.cells if c['levels'][0] == a):
            height = cell['count'] / marginal if marginal else 0.
            rect = Rectangle((x, y), width, height, facecolor=colors[cell['levels'][ci]],
                             edgecolor='white', linewidth=.35)
            rect.set_gid('cell:' + cell['cell_id']); ax.add_patch(rect)
            artists[cell['cell_id']] = rect
            geometry.append({**cell, 'x': x, 'y': y, 'width': width, 'height': height,
                             'area': width * height, 'color_dimension': color_dimension})
            y += height
        x += width
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    midpoints, tick_labels, x = [], [], 0.
    for a in table.orders[first]:
        width = table.marginals[first][a] / table.total if table.total else 0.
        if width:
            midpoints.append(x + width / 2); tick_labels.append(a)
        x += width
    ax.set_xticks(midpoints, tick_labels); ax.set_xlabel(first)
    ax.set_yticks([0, .5, 1], ['0', '0.5', '1']); ax.set_ylabel('Conditional proportion: ' + second)
    omitted_zero_labels = [a for a in table.orders[first] if not table.marginals[first][a]]
    if not table.total:
        ax.text(.5, .5, 'No observed counts', ha='center', va='center', transform=ax.transAxes)
    return {'artists': artists, 'geometry': geometry, 'total': table.total,
            'marginals': table.marginals, 'status': 'empty_total' if not table.total else 'drawn',
            'zero_width_categories_for_caption_or_companion': omitted_zero_labels,
            'boundary': 'Area encodes joint count; category order is declared, not inferred. Zero-total categories have zero width; no pseudo-counts.'}


def plot_alluvial(ax, table, *, colors, color_dimension, relationship_semantics,
                  node_gap=.025, node_width=.035):
    """Three static categorical axes, with one ribbon per original joint cell.

Node ordering and within-node joint-cell ordering are deterministic from the
declared category order. Every segment has the same count-derived thickness
at both ends; no pairwise aggregation loses the third-axis joint identity.
"""
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch, Rectangle
    if len(table.dimensions) != 3 or relationship_semantics != 'joint_categories':
        raise ValueError('Three-axis alluvial requires relationship_semantics=joint_categories; static attributes are not temporal flows')
    ci = _palette(table, color_dimension, colors)
    if (not isinstance(node_gap, Real) or not isinstance(node_width, Real)
            or isinstance(node_gap, (bool,np.bool_)) or isinstance(node_width, (bool,np.bool_))
            or not np.isfinite([node_gap, node_width]).all() or node_gap < 0
            or not 0 < node_width < .2):
        raise ValueError('Finite nonnegative node_gap and node_width in (0,.2) required')
    max_levels = max(len(table.orders[d]) for d in table.dimensions)
    available = 1 - node_gap * (max_levels - 1)
    if available <= 0: raise ValueError('Too many categories for node_gap; reduce the gap or split the figure')
    scale = available / table.total if table.total else 0.
    nodes, intervals, node_artists, ribbons, ribbon_artists = [], {}, {}, [], {}
    for axis, dim in enumerate(table.dimensions):
        cursor = 0.
        for level in table.orders[dim]:
            n = table.marginals[dim][level]; height = n * scale
            node_id = _cell_id([dim, level])
            node = {'node_id': node_id, 'axis': axis, 'dimension': dim, 'level': level,
                    'count': n, 'y0': cursor, 'y1': cursor + height}
            nodes.append(node)
            rect = Rectangle((axis - node_width / 2, cursor), node_width, height,
                facecolor=colors[level] if dim == color_dimension else '#737A80', edgecolor='none', zorder=3)
            rect.set_gid('node:' + node_id); ax.add_patch(rect); node_artists[node_id] = rect
            offset = cursor
            for cell in table.cells:
                if cell['levels'][axis] != level: continue
                thickness = cell['count'] * scale
                intervals[(axis, cell['cell_id'])] = (offset, offset + thickness)
                offset += thickness
            cursor += height + node_gap
    for cell in table.cells:
        for left in range(2):
            lo0, hi0 = intervals[(left, cell['cell_id'])]
            lo1, hi1 = intervals[(left + 1, cell['cell_id'])]
            x0, x1 = left + node_width / 2, left + 1 - node_width / 2
            dx = x1 - x0
            vertices = [(x0, lo0), (x0 + .45 * dx, lo0), (x1 - .45 * dx, lo1), (x1, lo1),
                        (x1, hi1), (x1 - .45 * dx, hi1), (x0 + .45 * dx, hi0), (x0, hi0), (x0, lo0)]
            path = Path(vertices, [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4,
                                  Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.CLOSEPOLY])
            patch = PathPatch(path, facecolor=colors[cell['levels'][ci]], edgecolor='none', zorder=1)
            key = (cell['cell_id'], left); patch.set_gid('ribbon:' + cell['cell_id'] + ':' + str(left))
            ax.add_patch(patch); ribbon_artists[key] = patch
            ribbons.append({**cell, 'left_axis': left, 'right_axis': left + 1, 'x0': x0, 'x1': x1,
                'left_interval': [lo0, hi0], 'right_interval': [lo1, hi1], 'thickness': cell['count'] * scale,
                'vertices': [list(v) for v in vertices]})
    ax.set_xlim(-.2, 2.2); ax.set_ylim(0, 1)
    ax.set_xticks(range(3), list(table.dimensions)); ax.set_yticks([])
    if not table.total:
        ax.text(.5, .5, 'No observed counts', ha='center', va='center', transform=ax.transAxes)
    return {'nodes': nodes, 'ribbons': ribbons, 'node_artists': node_artists, 'ribbon_artists': ribbon_artists,
            'count_to_height': scale, 'total': table.total, 'status': 'empty_total' if not table.total else 'drawn',
            'boundary': 'Static joint categorical membership, not time, transitions or causality. All cells retain identity, including zero-thickness ribbons.'}


def plan_count_chart(source, spec):
    """Same data/selection decision contract as the existing domain planners."""
    blockers, diagnostics = [], {'rows_are_independent_units': False, 'data_level': 'aggregate_count_cells'}
    view = spec.get('view')
    try:
        table = prepare_count_table(source, dimensions=spec.get('dimensions'), count=spec.get('count'),
            order=spec.get('order'), count_semantics=spec.get('count_semantics'))
        if view not in ('mosaic', 'alluvial'): raise ValueError('Declare count_table view=mosaic or alluvial')
        if (view == 'mosaic' and len(table.dimensions) != 2) or (view == 'alluvial' and len(table.dimensions) != 3):
            raise ValueError('mosaic needs two dimensions; alluvial needs three')
        if view == 'alluvial' and spec.get('relationship_semantics') != 'joint_categories':
            raise ValueError('Declare relationship_semantics=joint_categories for static alluvial data')
        diagnostics.update(rows=len(table.cells), used_rows=len(table.cells), source_sha256=table.source_sha256,
            fields=[*table.dimensions, table.count_field], row_positions=[c['source_position'] for c in table.cells],
            excluded_rows=[], total_count=table.total, marginals=table.marginals,
            cells=list(table.cells), zero_cells=sum(c['count'] == 0 for c in table.cells),
            conditional_proportions=conditional_proportions(table, given=spec.get('given', [table.dimensions[0]])),
            implicit_individual_expansion=False, implicit_aggregation=False)
    except (ValueError, TypeError, KeyError) as exc:
        blockers.append(str(exc))
    candidate = {'construction': 'statistical-mosaic' if view == 'mosaic' else 'static-joint-alluvial',
        'query': 'prepare_count_table conditional_proportions plot_mosaic' if view == 'mosaic' else 'prepare_count_table conditional_proportions plot_alluvial',
        'backend': 'python', 'rank': 1,
        'reason': 'Explicit integer cell counts determine joint/marginal support and area/thickness without pseudo-individual expansion.',
        'tradeoff': 'Small cells and many categories need a numeric companion or simpler view; static joint membership is not a temporal flow.'}
    return {'status': 'needs_resolution' if blockers else 'ready', 'spec': spec, 'diagnostics': diagnostics,
        'recommended': None if blockers else candidate, 'candidates': [candidate], 'blockers': blockers,
        'warnings': ['Counts denote supplied aggregate support, not independent rows; no survey weighting, CI, p-value or causal inference is computed.'],
        'rejected': [{'construction': 'expanded-individuals-or-inferred-transitions', 'reason': 'Aggregate joint cells do not provide individual records or longitudinal transition identity.'}]}
