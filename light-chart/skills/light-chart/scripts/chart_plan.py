"""Data-aware chart decisions. Explicit scientific roles take precedence over dtypes.

Synthesis of SciPilot's intent/shape/scale decision axes, Nature's evidence
contract, FigMirror's retained constructions and figures4papers' encodings.
This does not infer a study design, perform inference, or discard records.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd


# Fields carrying observed or supplied numerical/categorical outcomes. Identity,
# grouping and annotation fields are deliberately separate from measurements.
MEASUREMENT_ROLES = ('x', 'y', 'variable', 'count', 'lower', 'upper', 'time', 'event',
                     'numerator_events', 'numerator_non_events',
                     'comparator_events', 'comparator_non_events',
                     'true', 'predicted', 'frequency', 'real', 'imaginary')


def measurement_fields(spec):
    return {spec[k] for k in MEASUREMENT_ROLES if spec.get(k)} | set(spec.get('values', []))


def _trajectory_contract(data, spec, coordinate):
    """Validate the actual arrays required by the selected existing constructor.

    Raw shared-grid traces use assets/paper_patterns.trend_lines, whose bounds
    are optional. Supplied intervals use editorial.interval_trajectory per
    trace. Neither constructor aggregates duplicate observations or creates CIs.
    """
    errors, diagnostics = [], {}
    fields = [spec.get(coordinate), spec.get('y')]
    if not all(fields) or data.empty:
        return diagnostics, errors
    interval = bool(spec.get('lower') and spec.get('upper'))
    numeric_fields = fields + ([spec['lower'], spec['upper']] if interval else [])
    arrays = {}
    for field in numeric_fields:
        raw = data[field].to_numpy()
        if np.iscomplexobj(raw) or any(isinstance(v, (complex, np.complexfloating, bool, np.bool_)) for v in raw):
            errors.append('Trajectory coordinates, values and bounds must be real numeric observations, not complex or Boolean values.')
            continue
        values = pd.to_numeric(data[field], errors='coerce').to_numpy(dtype=float)
        if not np.isfinite(values).all():
            errors.append('Trajectory coordinates, values and bounds must be finite numerical measurements; categorical x is not a continuous coordinate.')
        arrays[field] = values
    if errors:
        return diagnostics, list(dict.fromkeys(errors))
    if spec.get('series'):
        trace_fields = [spec['series']]
    elif spec.get('unit') and data[spec['unit']].duplicated().any():
        trace_fields = [spec['unit']]
    else:
        trace_fields = [spec['group']] if spec.get('group') else []
    frame = data.reset_index(drop=True)
    if trace_fields and frame[trace_fields].isna().any().any():
        return diagnostics, ['Trajectory series identities must not be missing.']
    groups = frame.groupby(trace_fields[0], sort=False, observed=True).indices if trace_fields else {'all': np.arange(len(frame))}
    traces, grids = [], []
    for key, positions in groups.items():
        positions = np.asarray(positions)
        x = arrays[fields[0]][positions]
        if len(x) < 2:
            errors.append('Every trajectory needs at least two observed coordinates; choose points for a single observation.')
        if len(np.unique(x)) != len(x):
            errors.append('Trajectory x must be unique within each declared series/unit; define repeated-observation handling without implicit aggregation.')
        order = np.argsort(x, kind='stable')
        grid = x[order].tolist()
        grids.append(grid)
        traces.append({'identity': key, 'positions_in_used_rows': positions[order].tolist(), 'x': grid})
    if not interval and grids and any(grid != grids[0] for grid in grids[1:]):
        errors.append('The raw trend_lines constructor needs a complete shared x grid; declare a separate-panel or missing-grid design rather than dropping or interpolating records.')
    diagnostics.update(trajectory_coordinate=fields[0], trajectory_series_fields=trace_fields,
                       trajectory_traces=traces, constructor_symbol='interval_trajectory' if interval else 'trend_lines',
                       interval_source='caller_supplied' if interval else 'none', implicit_aggregation=False)
    return diagnostics, errors


def read_data(source):
    if isinstance(source, pd.DataFrame):
        return source.copy()
    path = Path(source)
    if path.suffix.lower() in {'.nc', '.nc4', '.cdf', '.netcdf'}:
        raise ValueError('NetCDF requires explicit variable/coordinates/selection: use prepare_netcdf_field or prepare_job with a scalar_field chart; binary data are not CSV')
    if path.suffix.lower() in {'.xlsx', '.xls'}:
        return pd.read_excel(path)
    sidecar = Path(str(path)+'.lineage.json')
    if sidecar.is_file():
        meta=json.loads(sidecar.read_text(encoding='utf8'))
        if meta.get('format_version')!=1 or hashlib.sha256(path.read_bytes()).hexdigest()!=meta.get('csv_sha256'):
            raise ValueError('Stored lineage does not match current CSV bytes')
        data=pd.read_csv(path,sep='\t' if path.suffix.lower()=='.tsv' else ',',dtype=meta['string_columns'],
                         keep_default_na=False,na_values=[''])
        if data_digest(data)!=meta['lineage']['data_sha256']:
            raise ValueError('Stored lineage does not match parsed CSV data')
        data.attrs['light_chart_lineage']=meta['lineage']
        return data
    return pd.read_csv(path, sep='\t' if path.suffix.lower() == '.tsv' else ',')


def data_digest(data):
    """Order-sensitive signature, including field names, types and missing records."""
    header = json.dumps([(str(c), str(t)) for c, t in data.dtypes.items()]).encode()
    return hashlib.sha256(header + pd.util.hash_pandas_object(data, index=True).values.tobytes()).hexdigest()


def plan_chart(source, spec, *, sources=None, profile=None):
    """Return candidates and blockers; spec declares intent and column semantics.

    Missing/duplicate observations stay visible in diagnostics. Only an explicit
    missing='complete_cases' declaration permits a complete-case row selection;
    its exact positional indices are returned, never applied to the source.
    """
    from field_data import is_netcdf, plan_field_chart
    if spec.get('intent') == 'scalar_field' or is_netcdf(source):
        return plan_field_chart(source, spec)
    data = read_data(source)
    if data.empty or data.columns.duplicated().any():
        raise ValueError('Nonempty data with unique columns required')
    # Optional domain constructors share the same decision contract. Unknown
    # intents return None; no heuristic fallback silently invents an analysis.
    try:
        from domain_decisions import plan_domain_chart
    except ModuleNotFoundError as exc:
        if exc.name != 'domain_decisions':
            raise
    else:
        domain_decision = plan_domain_chart(data, spec, sources=sources, profile=profile)
        if domain_decision is not None:
            return domain_decision
    intent = spec.get('intent')
    allowed = {'compare', 'change', 'distribution', 'association', 'trend',
               'estimates', 'matrix', 'survival', 'table', 'proportion'}
    if intent not in allowed:
        raise ValueError('Declare intent: ' + ', '.join(sorted(allowed)))
    if spec.get('data_level', 'raw') not in {'raw', 'summary'}:
        raise ValueError('data_level must be raw or summary')
    if spec.get('missing', 'resolve') not in {'resolve', 'complete_cases', 'display'}:
        raise ValueError('missing must be resolve, complete_cases or display (matrix only)')
    if spec.get('missing') == 'display' and intent != 'matrix':
        raise ValueError('display missingness is supported for matrix cells only')
    required_roles = {
        'compare': ['y', 'group'], 'change': ['y', 'unit', 'condition'],
        'distribution': ['y'], 'association': ['x', 'y'], 'trend': ['x', 'y'],
        'estimates': ['y', 'group'], 'matrix': [],
        'survival': ['time', 'event', 'unit'], 'proportion': ['event', 'group', 'unit'], 'table': []}[intent]
    blockers, warnings, candidates, rejected = [], [], [], []
    for name in required_roles:
        if not spec.get(name):
            blockers.append('Declare role: ' + name)
    fields = list(dict.fromkeys(spec[k] for k in
        ['x', 'y', 'group', 'unit', 'condition', 'lower', 'upper', 'time', 'event', 'series'] if spec.get(k)))
    fields += [c for c in spec.get('values', []) if c not in fields]
    absent = [c for c in fields if c not in data.columns]
    if absent:
        raise ValueError('Unknown fields: ' + ', '.join(absent))
    diag = {'rows': len(data), 'source_sha256': data_digest(data), 'fields': fields,
            'rows_are_independent_units': False, 'excluded_rows': [],
            'row_positions': list(range(len(data)))}
    if fields:
        invalid = data[fields].isna().any(axis=1).to_numpy()
        numeric_roles = ['y', 'lower', 'upper', 'time']
        if spec.get('x') and (intent == 'trend' or intent == 'association' and pd.api.types.is_numeric_dtype(data[spec['x']])):
            numeric_roles.append('x')
        for k in numeric_roles:
            if spec.get(k):
                if intent == 'trend' and any(isinstance(v, (complex, np.complexfloating, bool, np.bool_)) for v in data[spec[k]]):
                    blockers.append('Trajectory coordinates, values and bounds must be real numeric observations, not complex or Boolean values.')
                    continue
                numeric = pd.to_numeric(data[spec[k]], errors='coerce').to_numpy(dtype=float)
                invalid |= ~np.isfinite(numeric)
        diag['missing_or_nonfinite_rows'] = int(invalid.sum())
        if invalid.any():
            if spec.get('missing') == 'complete_cases':
                diag['excluded_rows'] = np.flatnonzero(invalid).tolist()
                diag['row_positions'] = np.flatnonzero(~invalid).tolist()
                warnings.append('Explicit complete cases: report excluded rows and missingness limits.')
            elif spec.get('missing') == 'display':
                warnings.append('Missing matrix cells stay missing; use a distinct missing-value color.')
            else:
                blockers.append('Resolve missing/nonfinite records; no implicit exclusion.')
    used = data.iloc[diag['row_positions']]
    if used.empty:
        blockers.append('No usable observations remain.')
    if spec.get('unit'):
        if data[spec['unit']].isna().any():
            blockers.append('Missing unit identities must be resolved explicitly.')
        diag['units'] = int(used[spec['unit']].nunique())
        diag['repeated_units'] = bool(used[spec['unit']].duplicated().any())
        diag['rows_have_unique_unit_ids'] = not diag['repeated_units']
        diag['rows_are_independent_units'] = None
        diag['sampling_independence'] = 'not_established_by_identity'
        if not diag['repeated_units']:
            warnings.append('Unique unit IDs establish record identity, not sampling independence; the study design and provenance must establish independent experimental units.')
        if diag['repeated_units'] and intent in {'compare', 'distribution', 'association'} and not spec.get('condition'):
            blockers.append('Repeated units require an explicit within-unit representation or aggregation design.')
    elif intent not in {'matrix', 'table', 'estimates'}:
        warnings.append('Independent sampling unit is undeclared; row counts are not an inferential n.')
    if spec.get('group'):
        diag['group_rows'] = {str(k): int(v) for k, v in used.groupby(spec['group'], observed=True).size().items()}
    summary = spec.get('data_level', 'raw') == 'summary'

    def add(construction, query, reason, tradeoff, **extra):
        candidates.append(dict(construction=construction, query=query, reason=reason, tradeoff=tradeoff, **extra))

    def reject(construction, reason):
        rejected.append(dict(construction=construction, reason=reason))

    paired = intent == 'change' or (intent == 'compare' and spec.get('unit') and spec.get('condition'))
    if paired and all(spec.get(k) for k in ['unit', 'condition', 'y']):
        keys = [spec['unit'], spec['condition']]
        if summary:
            blockers.append('ID-matched changes require individual records, not aggregate summaries.')
        if used.duplicated(keys).any():
            blockers.append('Duplicate unit-condition records: define technical-repeat aggregation first.')
        observed = used[spec['condition']].dropna().unique().tolist()
        order = spec.get('order')
        if not order or len(order) != len(set(order)) or set(order) != set(observed):
            blockers.append('Declare a unique condition order covering exactly the observed conditions.')
            order = observed
        counts = used.groupby(spec['unit'], observed=True)[spec['condition']].nunique()
        incomplete = counts[counts != len(order)].index
        diag['incomplete_units'] = list(map(str, incomplete))
        if len(incomplete):
            if spec.get('missing') == 'complete_cases':
                keep = ~data[spec['unit']].isin(incomplete).to_numpy()
                diag['row_positions'] = [i for i in diag['row_positions'] if keep[i]]
                diag['excluded_rows'] = sorted(set(range(len(data))) - set(diag['row_positions']))
                warnings.append('Incomplete units removed under the declared complete-pair policy.')
            else:
                blockers.append('Incomplete units: resolve missing pairs or explicitly declare complete cases.')
        diag['complete_units'] = int((counts == len(order)).sum())
        if not diag['complete_units']:
            blockers.append('No complete units remain.')
        if len(order) == 2:
            add('paired-change', 'paired', 'The question concerns change within the same unit.',
                'Show matched observations and individual differences; crowded lines may need faceting.')
            add('paired-differences', 'paired', 'Differences directly answer the change question.',
                'Retain a paired-observation panel when absolute levels are scientifically needed.')
        else:
            if spec.get('ordered'):
                trajectory, issues = _trajectory_contract(data.iloc[diag['row_positions']], spec, 'condition')
                diag.update(trajectory); blockers.extend(issues)
                add('within-unit-trajectories', trajectory.get('constructor_symbol', 'trend_lines'), 'More than two scientifically ordered conditions within each unit.',
                    'Use actual time/dose coordinates; do not pool rows as independent repeats.')
            else:
                add('matched-condition-points', 'paired', 'Repeated categorical conditions retain unit identity.',
                    'Do not connect categories into a continuous trajectory; choose an explicit contrast for change.')
                if intent == 'change':
                    blockers.append('More than two conditions: confirm scientific order/continuity or define a specific change contrast.')
        reject('independent-mean-bars', 'Would hide matching and the distribution of within-unit changes.')
    elif intent in {'compare', 'distribution'}:
        if summary:
            add('estimate-interval', 'benchmark', 'Only reported aggregate values are available.',
                'Use supplied bounds only; preserve their actual SD/SEM/CI/unspecified definition.')
            reject('box-violin-raw-points', 'Aggregate summaries do not identify individual observations or distributions.')
        else:
            add('raw-points-box', 'distribution', 'Observed values and group spread remain inspectable.',
                'A box summarizes quartiles; use point-only or ECDF if it hides meaningful shape.')
            add('ecdf', 'distribution', 'Shows every observed value without kernel smoothing.',
                'Requires readers to compare cumulative probabilities instead of individual locations.', availability='adapt_source')
            reject('mean-only-bars', 'Would discard individual variation for a distribution/comparison task.')
    elif intent == 'association':
        if summary:
            warnings.append('Association among aggregates cannot establish individual-level association.')
        if spec.get('x') and spec.get('y') and not used.empty:
            xy = used[[spec['x'], spec['y']]].apply(pd.to_numeric, errors='coerce').to_numpy(float)
            if not np.isfinite(xy).all():
                blockers.append('Association needs finite numerical coordinates or a different declared intent.')
            else:
                cells = np.floor((xy - xy.min(axis=0)) / np.maximum(np.ptp(xy, axis=0), 1e-15) * 31)
                density = 1 - len(np.unique(cells, axis=0)) / len(xy)
                diag['occupied_bin_collision_fraction_32x32'] = float(density)
                dense = density > spec.get('density_collision_threshold', .35)
                motifs = spec.get('reference', {}).get('required_elements', [])
                if 'marginals' in motifs:
                    add('joint-density-marginals', 'marginal', 'Reference marginals carry information about the same observed records.',
                        'Retain joint and marginal constructions; use the same valid-record mask.')
                add('hexbin' if dense else 'scatter', 'marginal' if dense else 'scatter',
                    'Observed coordinate occupancy indicates ' + ('overplotting.' if dense else 'individual marks remain feasible.'),
                    'Bin count is not probability density; any fit requires a separate analytical decision.')
                add('scatter' if dense else 'hexbin', 'scatter' if dense else 'marginal',
                    'Alternative exchanges individual visibility and local count readability.',
                    'Judge occupancy again at the actual physical panel size.')
        reject('connected-observations', 'An association does not imply an ordered trajectory.')
    elif intent == 'trend':
        if not spec.get('ordered'):
            blockers.append('Confirm that x has a scientifically meaningful order/continuity.')
        trajectory, issues = _trajectory_contract(used, spec, 'x')
        diag.update(trajectory); blockers.extend(issues)
        add('trajectory', trajectory.get('constructor_symbol', 'trend_lines'), 'A declared ordered coordinate is the subject of the question.',
            'Keep real x spacing; repeated units and source uncertainty need explicit handling.')
    elif intent == 'estimates':
        add('estimate-interval', 'benchmark', 'Compare estimates on aligned axes while keeping uncertainty.',
            'Different units get separate axes; do not derive confidence intervals from unspecified errors.')
        reject('violin', 'A list of point estimates is not a sample distribution.')
    elif intent == 'matrix':
        value_groups = spec.get('value_groups', {})
        if not spec.get('values'):
            blockers.append('Declare matrix value columns; numeric IDs must not enter the matrix.')
        else:
            a = used[spec['values']].to_numpy(float)
            diag['matrix_shape'] = list(a.shape)
            if np.isinf(a).any():
                blockers.append('Infinite matrix values need an explicit handling decision.')
            if value_groups:
                grouped = [c for g in value_groups.values() for c in g.get('columns', [])]
                if len(grouped) != len(set(grouped)) or set(grouped) != set(spec['values']):
                    blockers.append('Value groups must partition every matrix value column exactly once.')
                else:
                    for name, group_spec in value_groups.items():
                        limits = group_spec.get('limits')
                        if limits is not None:
                            if len(limits) != 2 or not np.isfinite(limits).all() or limits[0] >= limits[1]:
                                raise ValueError('Value group limits must be finite and increasing')
                            vals = used[group_spec['columns']].to_numpy(float)
                            observed = vals[np.isfinite(vals)]
                            if ((observed < limits[0]) | (observed > limits[1])).any():
                                blockers.append('Declared scale would clip supplied matrix values: '+name)
            else:
                warnings.append('Matrix units/scales undeclared: verify comparability before sharing a color scale.')
        diag['value_groups'] = value_groups
        multi = len(value_groups) > 1
        add('multi-scale-heatmaps' if multi else 'annotated-heatmap' if spec.get('annotations') else 'heatmap',
            'annotated heatmap' if spec.get('annotations') else 'heatmap',
            'Declared quantities need separate scales.' if multi else 'The task concerns a matrix pattern with explicit row/column identity.',
            'Keep identities aligned; declare units/normalization/clustering and a distinct missing color.', encoding_groups=value_groups)
    elif intent == 'proportion':
        if summary:
            blockers.append('This proportion route requires binary individual records; use estimates for supplied summaries.')
        if spec.get('unit') and used[spec['unit']].duplicated().any():
            blockers.append('Repeated records require a repeated-measure estimator, not independent binomial intervals.')
        if spec.get('event') and not used[spec['event']].isin([0,1]).all():
            blockers.append('Explicit binary event encoding required; missing outcomes cannot become negatives.')
        if all(spec.get(k) for k in ['group','event']):
            by=[spec['group']]+([spec['condition']] if spec.get('condition') else [])
            counts=used.groupby(by,observed=True)[spec['event']].agg(['count','sum'])
            diag['binomial_cells']=[{'levels':list(k) if isinstance(k,tuple) else [k],
                 'denominator':int(r['count']),'numerator':int(r['sum'])} for k,r in counts.iterrows()]
        add('proportion-interval','proportion', 'Binary outcomes require explicit numerators, denominators and interval definitions.',
            'Aligned dot/interval plots expose sparse-cell uncertainty; specify the interval method rather than deriving it from an unknown error.')
        add('proportion-matrix','heatmap','A matrix can reveal patterns over many crossed groups.',
            'Color alone hides denominators and uncertainty; retain cell counts and a precision view when they affect the conclusion.')
        reject('pooled-proportion-only','Pooling groups can hide cohort composition, different denominators and missingness.')
    elif intent == 'survival':
        if summary:
            blockers.append('The native survival implementation requires event/censor records.')
        if spec.get('unit') and used[spec['unit']].duplicated().any():
            blockers.append('One event/censor record per unit required for this right-censor implementation.')
        if spec.get('event') and not used[spec['event']].isin([0, 1]).all():
            blockers.append('Explicit binary event encoding required: event=1, censor=0.')
        if spec.get('time') and (used[spec['time']] < 0).any():
            blockers.append('Follow-up time cannot be negative.')
        if spec.get('design', 'right-censor') != 'right-censor':
            blockers.append('Left truncation, recurrent events and competing risks require another implementation.')
        add('kaplan-meier-risk', 'survival', 'Event times, censoring and risk counts must come from the same records.',
            'Unadjusted right-censored survival; no automatic hazard ratio or significance.')
    else:
        add('latex-table', 'table', 'Exact numerical lookup is the requested reading task.',
            'Keep native LaTeX and numeric data, with explicit precision and missing values.')
    if bool(spec.get('lower')) != bool(spec.get('upper')):
        blockers.append('Provide both lower and upper interval bounds.')
    elif spec.get('lower') and spec.get('y') and not blockers:
        a = used[[spec['lower'], spec['y'], spec['upper']]].to_numpy(float)
        if np.any(a[:, 0] > a[:, 1]) or np.any(a[:, 1] > a[:, 2]):
            blockers.append('Supplied intervals must bracket estimates.')
    for rank, candidate in enumerate(candidates, 1):
        candidate['rank'] = rank
    diag['used_rows'] = len(diag['row_positions'])
    if spec.get('unit'):
        diag['used_units'] = int(data.iloc[diag['row_positions']][spec['unit']].nunique())
    return dict(status='needs_resolution' if blockers else 'ready', intent=intent,
                spec=spec, diagnostics=diag, recommended=candidates[0] if candidates and not blockers else None,
                candidates=candidates, rejected=rejected, blockers=list(dict.fromkeys(blockers)), warnings=warnings,
                boundary='Candidate ordering is a reasoned heuristic, not a scientific or aesthetic score.')
