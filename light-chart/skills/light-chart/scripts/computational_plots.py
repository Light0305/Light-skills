"""Measured computational sweeps and exact count matrices.

Adapted from complete figures4papers examples: RNAGenScape/plot_sweep.py
(numeric irregular-x curves with shared identities) and
ophthal_review/plot_composition.py (annotated matrix and both marginal totals).
Input validation, repeated-run identity and full count range replace source
fixed arrays, biological categories, TeX, font size and vmax=20 assumptions.
These constructors plot supplied measurements; they never fit/predict models.
"""
from __future__ import annotations

from decimal import Decimal
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize


def ordered_sweep(records, *, x, y, series, repeat, series_order):
    """Return jointly sorted x and repeated-run matrices; require a complete grid.

    Each (series, repeat, x) must identify one measured value. Repeats are
    identities supplied by the caller, not an assertion of independent units.
    series_order must cover the input identities exactly; no silent exclusions.
    """
    data = pd.DataFrame(records).copy()
    required = [x, y, series, repeat]
    if len(set(required)) != 4 or any(c not in data for c in required) or data.empty:
        raise ValueError('Four distinct existing fields and nonempty records required')
    if data[required].isna().any().any():
        raise ValueError('Sweep keys and measurements cannot be missing')
    source_x = data[x].copy()
    for field in [x, y]:
        if any(isinstance(v, (complex, np.complexfloating, bool, np.bool_)) for v in data[field]):
            raise ValueError('Sweep x and y require real numeric values, never complex or Boolean inputs')
        try:
            data[field] = pd.to_numeric(data[field], errors='raise')
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError('Finite real numeric x and y required') from exc
        if not np.isfinite(data[field].to_numpy(float)).all():
            raise ValueError('Finite real numeric x and y required')
    # Compare source keys before assigning the floating-point plotting grid.
    coordinates = data[x].to_numpy(float)
    coordinate_keys = {}
    for value, coordinate in zip(source_x, coordinates):
        key = Decimal(str(value))
        if (isinstance(value, (str, int, np.integer, Decimal))
                and key == key.to_integral_value() and int(key) != int(coordinate)):
            raise ValueError('Sweep integer x must be exactly representable as floating-point coordinates')
        if coordinate in coordinate_keys and coordinate_keys[coordinate] != key:
            raise ValueError('Distinct sweep x values cannot collapse to the same floating-point coordinate')
        coordinate_keys[coordinate] = key
    data[x] = coordinates
    order = list(series_order)
    if len(order) != len(set(order)) or set(order) != set(data[series]):
        raise ValueError('series_order must contain every series exactly once')
    if data.duplicated([series, repeat, x]).any():
        raise ValueError('Duplicate series/repeat/x measurements are ambiguous')
    xx = np.sort(data[x].unique().astype(float))
    repetitions = list(pd.unique(data[repeat]))
    matrices = {}
    for name in order:
        sub = data[data[series] == name]
        index = pd.MultiIndex.from_product([repetitions, xx], names=[repeat, x])
        aligned = sub.set_index([repeat, x])[y].reindex(index)
        if aligned.isna().any():
            raise ValueError('Every series must share the complete x-by-repeat grid')
        matrices[name] = aligned.to_numpy(float).reshape(len(repetitions), len(xx))
    return {'x': xx, 'series_order': order, 'repeat_ids': repetitions,
            'values': matrices, 'x_field': x, 'y_field': y,
            'repeat_semantics': 'Caller supplied run identities; no independence or interval inferred'}


def plot_budget_sweep(ax, records, *, x, y, series, repeat, series_order,
                      encodings, xscale='linear', labels=None,
                      run_style=None, mean_style=None):
    """Plot every measured repeat plus a mean curve on actual numeric x.

    Thin lines and small unfilled markers show each run. The large marker and
    thicker line show their arithmetic mean. No interval or uncertainty model
    is invented. xscale is explicit; logarithmic coordinates require x>0.
    Returns validated arrays and artist identities for scientific checking.
    Optional run_style/mean_style control only physical marks: linewidth,
    markersize, markeredgewidth, alpha, markerfacecolor and zorder. They never
    offset, subsample or change measurements. run_artists preserves the returned
    repeat_ids order; line identity alone does not promise visible seed tracking.
    """
    result = ordered_sweep(records, x=x, y=y, series=series, repeat=repeat, series_order=series_order)
    if xscale not in {'linear', 'log'} or (xscale == 'log' and np.any(result['x'] <= 0)):
        raise ValueError('Use linear x or log x with strictly positive measurements')
    if set(encodings) != set(series_order):
        raise ValueError('Provide one stable encoding for every series')
    def style(base, supplied):
        if supplied is None:
            return base
        if not isinstance(supplied, dict) or set(supplied) - set(base):
            raise ValueError('Drawing style contains unsupported properties')
        merged = {**base, **supplied}
        for key in ['linewidth', 'markersize', 'markeredgewidth', 'alpha', 'zorder']:
            value = merged[key]
            if isinstance(value, (bool, np.bool_, complex, np.complexfloating)):
                raise ValueError('Drawing style numbers must be finite real values')
            try:
                value = float(value)
                finite = np.isfinite(value)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError('Drawing style numbers must be finite real values') from exc
            if not finite or (key in {'linewidth', 'markersize'} and value <= 0) or (
                    key == 'markeredgewidth' and value < 0) or (key == 'alpha' and not 0 < value <= 1):
                raise ValueError('Drawing styles require positive visible marks and 0 < alpha <= 1')
            merged[key] = value
        return merged
    runs = style(dict(markersize=2.3, markerfacecolor='white', markeredgewidth=.55,
                      linewidth=.45, alpha=.55, zorder=2), run_style)
    means = style(dict(markersize=3.7, markerfacecolor=None, markeredgewidth=.6,
                       linewidth=1.15, alpha=1., zorder=2), mean_style)
    ax.set_xscale(xscale)
    artists = {}
    run_artists = {}
    for name in result['series_order']:
        e = encodings[name]
        if not all(k in e for k in ['color', 'marker', 'linestyle']):
            raise ValueError('Each series needs explicit color, marker and linestyle')
        values = result['values'][name]
        run_artists[name] = []
        for row in values:
            line, = ax.plot(result['x'], row, color=e['color'], linestyle=e['linestyle'],
                            marker=e['marker'], **runs, label='_nolegend_')
            run_artists[name].append(line)
        artists[name], = ax.plot(result['x'], values.mean(axis=0), color=e['color'],
                                linestyle=e['linestyle'], marker=e['marker'], **means,
                                label=(labels or {}).get(name, str(name)))
    for precision in range(6, 18):
        tick_labels = [format(v, f'.{precision}g') for v in result['x']]
        if len(set(tick_labels)) == len(tick_labels):
            break
    ax.set_xticks(result['x'], labels=tick_labels)
    ax.minorticks_off()
    result['artists'] = artists
    result['run_artists'] = run_artists
    return result


def prepare_count_matrix(counts, *, row_ids, column_ids, row_order=None, column_order=None):
    """Validate nonnegative integer counts, reorder jointly and return exact totals.

    No normalization is applied. IDs must be unique and each requested order
    must preserve every ID, including rows/columns of zeros. Labels are distinct
    from IDs and can be formatted at drawing time.
    """
    # Inspect the original elements before NumPy can coerce mixed Boolean lists
    # into integer counts (for example [[4, True]] -> [[4, 1]]).
    original = np.asarray(counts, dtype=object)
    if any(isinstance(v, (complex, np.complexfloating, bool, np.bool_)) for v in original.flat):
        raise ValueError('Counts must be finite nonnegative integers, never complex or Boolean values')
    values = np.asarray(counts)
    rows, columns = list(row_ids), list(column_ids)
    if values.ndim != 2 or values.shape != (len(rows), len(columns)) or not values.size:
        raise ValueError('A nonempty matrix matching both identity arrays is required')
    if len(set(rows)) != len(rows) or len(set(columns)) != len(columns):
        raise ValueError('Unique row and column IDs required')
    if any(pd.isna(v) for v in [*rows, *columns]):
        raise ValueError('Matrix IDs cannot be missing')
    if values.dtype.kind not in 'iuf' or not np.isfinite(values).all() or (values < 0).any() or (values != np.floor(values)).any():
        raise ValueError('Counts must be finite nonnegative integers, never proportions')
    if any(int(value) > np.iinfo(np.int64).max for value in values.flat):
        raise ValueError('Counts exceed supported int64 range')
    values = values.astype(np.int64)
    # Prevent silently overflowing exact integer marginals.
    if sum(map(int, values.flat)) > np.iinfo(np.int64).max:
        raise ValueError('Total exceeds supported int64 range')
    ro, co = list(row_order) if row_order is not None else rows, list(column_order) if column_order is not None else columns
    if len(ro) != len(set(ro)) or set(ro) != set(rows) or len(co) != len(set(co)) or set(co) != set(columns):
        raise ValueError('Orders must preserve every matrix ID exactly once')
    values = values[np.ix_([rows.index(v) for v in ro], [columns.index(v) for v in co])]
    return {'counts': values, 'row_ids': ro, 'column_ids': co,
            'row_totals': values.sum(1), 'column_totals': values.sum(0),
            'total': int(values.sum()), 'normalization': 'none; raw counts'}


def confusion_counts(true, predicted, *, class_order, record_ids):
    """Build a full class-by-class count matrix without dropping zero supports."""
    actual, inferred, ids, classes = list(true), list(predicted), list(record_ids), list(class_order)
    if not actual or len(actual) != len(inferred) or len(ids) != len(actual) or len(set(ids)) != len(ids):
        raise ValueError('Equal nonempty predictions and unique original record IDs required')
    if any(pd.isna(v) for v in [*actual, *inferred, *ids, *classes]):
        raise ValueError('Labels and record IDs cannot be missing')
    if not classes or len(classes) != len(set(classes)) or not set(actual + inferred) <= set(classes):
        raise ValueError('Explicit unique class order must cover every actual and predicted label')
    lookup = {v: i for i, v in enumerate(classes)}
    counts = np.zeros((len(classes), len(classes)), dtype=np.int64)
    np.add.at(counts, ([lookup[v] for v in actual], [lookup[v] for v in inferred]), 1)
    result = prepare_count_matrix(counts, row_ids=classes, column_ids=classes)
    result['record_ids'] = ids
    result['correct'] = int(np.trace(counts))
    return result


def plot_count_matrix(ax, counts, *, row_ids, column_ids, cmap='Blues',
                      row_order=None, column_order=None, labels=None, column_labels=None, vmax=None,
                      include_marginals=True, annotation_size=7.2, rotation=45):
    """Draw raw count cells with a sequential full-range scale and exact supports.

    Returns image, norm, counts and totals; the caller places its colorbar.
    Explicit vmax may exceed but must never clip any cell. Zero is always zero.
    Marginals live in axis labels, not as fabricated observations in the matrix.
    """
    from color_tools import contrast_text
    result = prepare_count_matrix(counts, row_ids=row_ids, column_ids=column_ids,
                                  row_order=row_order, column_order=column_order)
    maximum = int(result['counts'].max())
    if isinstance(vmax, (complex, np.complexfloating, bool, np.bool_)):
        raise ValueError('Color maximum requires a real numeric value, never complex or Boolean inputs')
    try:
        upper = float(maximum or 1) if vmax is None else float(vmax)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError('Color maximum requires a finite real numeric value') from exc
    if not np.isfinite(upper) or upper <= 0 or upper < maximum:
        raise ValueError('Color maximum must cover every count without clipping')
    norm = Normalize(vmin=0, vmax=upper)
    image = ax.imshow(result['counts'], origin='upper', interpolation='nearest',
                      aspect='equal', cmap=cmap, norm=norm)
    for i in range(len(result['row_ids'])):
        for j in range(len(result['column_ids'])):
            value = int(result['counts'][i, j])
            ink, _ = contrast_text(image.cmap(norm(value)))
            ax.text(j, i, str(value), ha='center', va='center', color=ink, fontsize=annotation_size)
    def tick(value, total, mapping):
        name = str((mapping or {}).get(value, value))
        return f'{name}\nn={int(total)}' if include_marginals else name
    ax.set_xticks(np.arange(len(result['column_ids'])), [tick(v, n, column_labels if column_labels is not None else labels) for v, n in zip(result['column_ids'], result['column_totals'])],
                  rotation=rotation, ha='right' if rotation else 'center', rotation_mode='anchor')
    ax.set_yticks(np.arange(len(result['row_ids'])), [tick(v, n, labels) for v, n in zip(result['row_ids'], result['row_totals'])])
    ax.set_xticks(np.arange(-.5, len(result['column_ids']), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(result['row_ids']), 1), minor=True)
    ax.grid(which='minor', color='white', lw=.7)
    ax.tick_params(which='both', length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    result.update(image=image, norm=norm, color_limits=[0., upper], count_units='records')
    return result


def plan_computational_chart(records, spec):
    """Value-aware routing for supplied computational measurements/predictions.

    This narrowly scoped adapter can be delegated to by domain_decisions.
    It checks the actual keys/counts; declared split names and repeat semantics
    are not proof of independence, fitting quality or absence of leakage.
    """
    intent = spec.get('intent')
    if intent not in {'computational-sweep', 'confusion-counts'}:
        return None
    data = pd.DataFrame(records)
    blockers, warnings = [], []
    diagnostics = {'rows': len(data), 'excluded_rows': [], 'used_rows': len(data),
                   'rows_are_independent_units': False, 'evaluation_split': spec.get('evaluation_split')}
    if spec.get('evaluation_split') not in {'validation','test','cross_validation'}:
        blockers.append('Declare evaluation_split=validation/test/cross_validation; this is caller metadata, not a leakage audit')
    candidate = None
    try:
        if intent == 'computational-sweep':
            if not isinstance(spec.get('repeat_semantics'),str) or not spec['repeat_semantics'].strip():
                blockers.append('Declare the repeat unit; algorithmic seeds are not independent datasets')
            if spec.get('objective_direction') not in {'min','max'}:
                blockers.append('Declare objective_direction=min/max for the measured metric')
            result = ordered_sweep(data,**{key:spec[key] for key in ['x','y','series','repeat','series_order']})
            diagnostics.update(x_values=result['x'].tolist(),series_order=result['series_order'],repeat_ids=result['repeat_ids'],
                               repeated_values={str(k):v.tolist() for k,v in result['values'].items()})
            candidate = dict(construction='measured-budget-sweep',query='computational sweep',backend='python',
                             reason='Actual numeric budgets and every declared run remain aligned across settings.',
                             tradeoff='Mean curves plus measured runs; no inferred confidence interval or hardware-general efficiency claim.')
        else:
            result = confusion_counts(data[spec['true']],data[spec['predicted']],class_order=spec['class_order'],record_ids=data[spec['unit']])
            diagnostics.update(class_order=result['row_ids'],counts=result['counts'].tolist(),
                               true_support=result['row_totals'].tolist(),predicted_support=result['column_totals'].tolist(),
                               total=result['total'],correct=result['correct'],normalization=result['normalization'])
            candidate = dict(construction='raw-confusion-counts',query='confusion matrix counts',backend='python',
                             reason='All prediction records and exact class supports contribute to a full count matrix.',
                             tradeoff='Raw counts show errors and denominators; class imbalance also requires reading support, not color alone.')
    except (KeyError,ValueError,TypeError) as exc:
        blockers.append(str(exc))
    warnings.append('Declared evaluation/repeat roles do not establish independent collection generalization or certify absence of model leakage.')
    return dict(status='needs_resolution' if blockers else 'ready',intent=intent,spec=spec,diagnostics=diagnostics,
                recommended=candidate if not blockers else None,candidates=[candidate] if candidate else [],
                rejected=[],blockers=blockers,warnings=warnings,boundary='Precomputed observations only; no model fitting, selection or statistical inference performed.')
