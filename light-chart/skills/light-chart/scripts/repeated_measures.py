"""Explicit repeated-unit trajectories, separate from independent row summaries.

SciPilot's >6 trajectory advice and figures4papers BrainTeaser's complete
shared-scale small multiples motivate the native-R construction. Neither a
day index nor a first observation is automatically a baseline or intervention.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def prepare_repeated_trajectory(source, *, unit, x, y, order, x_unit, y_unit):
    from chart_plan import read_data, data_digest
    data = read_data(source)
    fields = [unit, x, y]
    if (any(not isinstance(v, str) or not v for v in fields) or len(set(fields)) != 3
            or data.empty or data.columns.duplicated().any() or any(v not in data for v in fields)):
        raise ValueError('Nonempty repeated data need distinct existing unit/x/y fields')
    if not all(isinstance(v, str) and v.strip() for v in (x_unit, y_unit)):
        raise ValueError('Declare scientific x_unit and y_unit; neither index units nor baseline are guessed')
    ids = data[unit]
    if ids.isna().any() or any(isinstance(v, (bool, np.bool_)) for v in ids):
        raise ValueError('Repeated unit IDs must be explicit and nonmissing, not Boolean flags')
    labels = ids.astype(str)
    if not isinstance(order, (list, tuple)) or not order or len(set(map(str, order))) != len(order):
        raise ValueError('Declare complete unique unit order')
    ordered_ids = [str(v) for v in order]
    if set(ordered_ids) != set(labels): raise ValueError('Declared unit order must match all observed units exactly')
    if ids.nunique(dropna=False) != labels.nunique():
        raise ValueError('Unit IDs collide after text conversion; normalize identities explicitly')
    arrays = {}
    for field in (x, y):
        values = data[field].to_numpy()
        if (not pd.api.types.is_numeric_dtype(data[field]) or np.iscomplexobj(values)
                or any(isinstance(v, (bool, np.bool_)) for v in values)):
            raise ValueError('Trajectory coordinates/measurements must be real numeric observations, not Boolean/complex/text')
        arrays[field] = values.astype(float)
        if not np.isfinite(arrays[field]).all(): raise ValueError('Resolve missing/nonfinite trajectory observations explicitly; no automatic deletion or interpolation')
    traces = []
    for label in ordered_ids:
        positions = np.flatnonzero(labels.eq(label).to_numpy())
        if len(positions) < 2: raise ValueError('Every unit needs at least two real observations')
        xx = arrays[x][positions]
        if len(np.unique(xx)) != len(xx): raise ValueError('Duplicate unit/x observations need explicit repeat handling; no silent averaging')
        positions = positions[np.argsort(xx, kind='stable')]
        traces.append({'unit_id': label, 'source_positions': positions.tolist(),
            'x': arrays[x][positions].tolist(), 'y': arrays[y][positions].tolist(), 'observations': len(positions)})
    return {'source_sha256': data_digest(data), 'rows': len(data), 'unit_count': len(ordered_ids),
        'unit_order': ordered_ids, 'unit_field': unit, 'x_field': x, 'y_field': y,
        'x_unit': x_unit, 'y_unit': y_unit, 'traces': traces,
        'shared_x_limits': [float(arrays[x].min()), float(arrays[x].max())],
        'shared_y_limits': [float(arrays[y].min()), float(arrays[y].max())],
        'rows_are_independent_units': False, 'baseline_inferred': False,
        'boundary': 'Repeated measurements are descriptive; distinct IDs alone do not establish study independence. No model, uncertainty, significance or baseline adjustment.'}


def plan_repeated_chart(source, spec):
    blockers, diagnostics = [], {'rows_are_independent_units': False}
    try:
        diagnostics.update(prepare_repeated_trajectory(source, unit=spec.get('unit'), x=spec.get('x'),
            y=spec.get('y'), order=spec.get('order'), x_unit=spec.get('x_unit'), y_unit=spec.get('y_unit')))
        if spec.get('view') != 'small_multiples':
            raise ValueError('Declare view=small_multiples for the native-R repeated trajectory constructor')
        if spec.get('baseline') is not None:
            raise ValueError('Baseline adjustment is not performed by this raw-trajectory constructor; provide a separately audited derived table')
    except (ValueError, TypeError, KeyError) as exc:
        blockers.append(str(exc))
    candidate = {'construction': 'repeated-unit-small-multiples', 'query': 'repeated_trajectory_r',
        'backend': 'r', 'rank': 1,
        'reason': 'One fixed-scale facet per actual unit retains repeated identity and makes more than six trajectories readable without a large identity legend.',
        'tradeoff': 'Many units require more page area or multiple pages; do not shrink labels or add unsupported mean/CI bands.'}
    return {'status': 'needs_resolution' if blockers else 'ready', 'spec': spec, 'diagnostics': diagnostics,
        'recommended': None if blockers else candidate, 'candidates': [candidate], 'blockers': blockers,
        'warnings': ['Repeated rows are not independent n. Time/day labels do not establish treatment onset or a baseline.'],
        'rejected': [{'construction': 'independent-pooled-days-or-automatic-ci', 'reason': 'Repeated observations require an explicit unit-aware estimator; plotting does not create one.'}]}
