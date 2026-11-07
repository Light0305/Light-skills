"""Explicit local CF-NetCDF preparation for the existing scalar-field pipeline.

Coordinates/decoding follow xarray's public open_dataset/isel/mean contracts:
https://docs.xarray.dev/en/stable/generated/xarray.open_dataset.html
https://docs.xarray.dev/en/stable/generated/xarray.DataArray.mean.html
Only a selected/reduced 2D grid becomes a table for Nature evidence contracts
and the adapted SciPilot profiler. A time-by-space cube is never flattened.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

from field_tools import grid_field


ATTR = 'light_chart_field'
CONTRACT_KEYS = ('variable', 'x', 'y', 'time', 'isel', 'coordinate_ranges', 'reduce',
                 'value_transform', 'value_unit', 'x_unit', 'y_unit', 'limits', 'center', 'engine')


class FieldPreparationError(ValueError):
    """An unresolved scientific input contract, not a valid prepared figure."""


@dataclass(frozen=True)
class PreparedField:
    table: pd.DataFrame
    field: object
    report: dict


def is_netcdf(source):
    return isinstance(source, (str, Path)) and Path(source).suffix.lower() in {'.nc', '.nc4', '.cdf', '.netcdf'}


def _digest_file(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _plain(value):
    if isinstance(value, dict): return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [_plain(v) for v in value]
    if isinstance(value, np.ndarray): return _plain(value.tolist())
    if isinstance(value, np.generic): return _plain(value.item())
    if isinstance(value, float) and not np.isfinite(value): return None
    if isinstance(value, (str, int, float, bool)) or value is None: return value
    return str(value)


def _unit(coord, explicit, role):
    observed = coord.attrs.get('units')
    if explicit is not None and (not isinstance(explicit, str) or not explicit.strip()):
        raise FieldPreparationError(f'{role}_unit must be nonempty text')
    if observed and explicit and observed != explicit:
        raise FieldPreparationError(f'{role}_unit conflicts with source units; declare an explicit value_transform for conversion')
    result = observed or explicit
    if not isinstance(result, str) or not result.strip():
        raise FieldPreparationError(f'Missing source units: declare {role}_unit explicitly')
    return result


def _bounds(values, bounds, name):
    if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
        raise FieldPreparationError(f'{name}: declare a closed [start, stop] range')
    try:
        if np.issubdtype(values.dtype, np.datetime64):
            lo, hi = np.datetime64(bounds[0]), np.datetime64(bounds[1])
            if np.isnat(lo) or np.isnat(hi): raise ValueError()
        else:
            lo, hi = float(bounds[0]), float(bounds[1])
            if not np.isfinite([lo, hi]).all(): raise ValueError()
        if lo > hi: raise ValueError()
        positions = np.flatnonzero((values >= lo) & (values <= hi))
    except (ValueError, TypeError, OverflowError) as exc:
        raise FieldPreparationError(f'{name}: valid increasing bounds in the source coordinate type required') from exc
    if not len(positions): raise FieldPreparationError(f'{name}: selection is empty')
    return positions


def _coordinate(ds, name, role, dims):
    if not isinstance(name, str) or not name or name not in ds:
        raise FieldPreparationError(f'Declare an existing {role} coordinate variable')
    coord = ds[name]
    if coord.ndim != 1 or coord.dims[0] not in dims:
        raise FieldPreparationError(f'{role} must be a one-dimensional rectilinear coordinate; curvilinear/auxiliary grids need an explicit adapter')
    values = coord.values
    if role == 'time':
        if not np.issubdtype(values.dtype, np.datetime64) or np.isnat(values).any():
            raise FieldPreparationError('Time must be CF-decoded finite datetime64; unsupported calendars need their optional calendar dependency and a dedicated adapter')
    else:
        if values.dtype.kind not in 'iuf' or not np.isfinite(values).all():
            raise FieldPreparationError(f'{role} must contain finite real numeric coordinates')
    # Compare neighbouring values directly: subtraction can wrap unsigned
    # descending axes and overflow widely separated signed/date coordinates.
    valid = np.all(values[1:] > values[:-1]) or np.all(values[1:] < values[:-1])
    if len(values) < (1 if role == 'time' else 2) or (len(values) > 1 and not valid):
        raise FieldPreparationError(f'{role} coordinates must be strictly monotonic and unique')
    return coord


def _range_slice(positions):
    # Closed bounds on a monotone coordinate are contiguous. Basic slice
    # indexing also works with CF-packed SciPy backends that lack oindex.
    return slice(int(positions[0]), int(positions[-1]) + 1)


def prepare_netcdf_field(source, spec):
    """Return an immutable GridField, its small cell table and bound provenance.

Required chart keys: intent=scalar_field, variable, x, y and explicit limits.
Extra dimensions require scalar integer ``isel``. If time remains, ``reduce``
declares mean or difference_of_means, ranges, weighting=equal_samples and
missing=skip/propagate. Difference is explicitly second_minus_first. No layer,
variable, mean, projection, longitude wrap, area weighting or interpolation is
guessed. Optional value_transform applies an explicit affine unit conversion
before reduction. Source pixels and coordinates are never edited.
"""
    if spec.get('intent') != 'scalar_field':
        raise FieldPreparationError('A NetCDF source requires intent=scalar_field and explicit coordinate/variable mapping')
    if 'limits' not in spec: raise FieldPreparationError('Declare explicit scalar color limits before preparation')
    path = Path(source)
    if not path.is_file(): raise FieldPreparationError('Local NetCDF input file not found: ' + str(path))
    try:
        import xarray as xr
    except ImportError as exc:
        raise FieldPreparationError('NetCDF preparation requires optional xarray and a reader for this file; CSV preparation remains available') from exc
    engines = xr.backends.list_engines()
    engine = spec.get('engine')
    if engine is None:
        with path.open('rb') as stream: magic = stream.read(8)
        if magic[:3] == b'CDF':
            engine = 'scipy' if 'scipy' in engines else 'netcdf4'
        elif magic == b'\x89HDF\r\n\x1a\n':
            engine = 'h5netcdf' if 'h5netcdf' in engines else 'netcdf4'
        else:
            raise FieldPreparationError('Unsupported NetCDF container; an explicit installed xarray engine is required')
    if not isinstance(engine, str) or engine not in engines:
        raise FieldPreparationError('The NetCDF file needs optional reader engine ' + str(engine) + '; available engines: ' + ', '.join(sorted(engines)))
    try:
        # CF decoding preserves packed scale/offset and masks declared fill
        # values. decode_coords exposes named coordinates; it does not regrid.
        dataset = xr.open_dataset(path, engine=engine, decode_cf=True, mask_and_scale=True, decode_times=True, decode_coords='all', chunks=None)
    except (ValueError, ImportError, OSError) as exc:
        raise FieldPreparationError('Cannot CF-decode this NetCDF file with available readers/calendar dependencies: ' + str(exc)) from exc
    with dataset as ds:
        variable = spec.get('variable')
        if not isinstance(variable, str) or variable not in ds.data_vars:
            raise FieldPreparationError('Declare an existing data variable; no variable is guessed')
        arr = ds[variable]
        if arr.dtype.kind not in 'iuf': raise FieldPreparationError('Field values must be real numeric measurements')
        names = [spec.get('x'), spec.get('y'), variable]
        if any(not isinstance(v, str) or not v for v in names) or len(set(names)) != 3:
            raise FieldPreparationError('Declare distinct variable, x and y names')
        x = _coordinate(ds, spec['x'], 'x', arr.dims)
        y = _coordinate(ds, spec['y'], 'y', arr.dims)
        xdim, ydim = x.dims[0], y.dims[0]
        if xdim == ydim: raise FieldPreparationError('x and y must span different dimensions')
        units = {'x': _unit(x, spec.get('x_unit'), 'x'), 'y': _unit(y, spec.get('y_unit'), 'y'),
                 'value': _unit(arr, spec.get('value_unit'), 'value')}
        original = {'dimensions': list(arr.dims), 'shape': list(arr.shape), 'attrs': _plain(arr.attrs),
                    'encoding': _plain({k: v for k, v in arr.encoding.items() if k in ('dtype', 'scale_factor', 'add_offset', '_FillValue', 'missing_value', 'calendar', 'units')})}
        coord_report = {role: {'name': name, 'dimension': coord.dims[0], 'attrs': _plain(coord.attrs),
                              'original_values': _plain(coord.values)}
                        for role, name, coord in [('x', spec['x'], x), ('y', spec['y'], y)]}
        coords = {spec['x']: x, spec['y']: y}
        time = None
        if spec.get('time'):
            if spec['time'] in names: raise FieldPreparationError('Time coordinate must be distinct from variable/x/y')
            time = _coordinate(ds, spec['time'], 'time', arr.dims)
            if time.dims[0] in (xdim, ydim): raise FieldPreparationError('Time must span its own dimension')
            coords[spec['time']] = time
            coord_report['time'] = {'name': spec['time'], 'dimension': time.dims[0],
                'attrs': _plain(time.attrs), 'encoding': _plain({k: v for k, v in time.encoding.items() if k in ('calendar', 'units')}),
                'original_count': int(time.size)}
        arr = arr.assign_coords(coords)
        indexers = spec.get('isel', {})
        if not isinstance(indexers, dict): raise FieldPreparationError('isel must map dimensions to explicit scalar indices')
        for dim, index in indexers.items():
            if dim not in arr.dims or dim in (xdim, ydim) or isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < arr.sizes[dim]:
                raise FieldPreparationError('isel needs valid nonnegative scalar indices for non-spatial dimensions; spatial subsetting uses coordinate_ranges')
        arr = arr.isel(indexers)
        ranges = spec.get('coordinate_ranges', {})
        if not isinstance(ranges, dict) or set(ranges) - {spec['x'], spec['y']}:
            raise FieldPreparationError('coordinate_ranges supports explicit x/y coordinate bounds only')
        spatial_positions = {}
        for name, bounds in ranges.items():
            coord = arr[name]; positions = _bounds(coord.values, bounds, name)
            spatial_positions[name] = positions.tolist()
            arr = arr.isel({coord.dims[0]: _range_slice(positions)})
        extra = set(arr.dims) - {xdim, ydim}
        timedim = time.dims[0] if time is not None else None
        if extra - ({timedim} if timedim else set()):
            raise FieldPreparationError('Explicit isel required for every extra dimension (including singleton layers): ' + ', '.join(sorted(extra - ({timedim} if timedim else set()))))
        transform = spec.get('value_transform')
        transform_report = None
        if transform is not None:
            if not isinstance(transform, dict) or set(transform) != {'scale', 'offset', 'unit'}:
                raise FieldPreparationError('value_transform requires exactly scale, offset and output unit')
            scale, offset = transform['scale'], transform['offset']
            if isinstance(scale, bool) or isinstance(offset, bool) or not isinstance(scale, (float, int)) or not isinstance(offset, (float, int)) or not np.isfinite([scale, offset]).all() or scale == 0 or not isinstance(transform['unit'], str) or not transform['unit'].strip():
                raise FieldPreparationError('Finite nonzero scale, finite offset and explicit output unit required')
            transform_report = {**transform, 'input_unit': units['value'], 'applied': 'before temporal reduction'}
            units['value'] = transform['unit']
        reduction = spec.get('reduce')
        counts, time_records = [], []
        if timedim in extra:
            if not isinstance(reduction, dict) or reduction.get('dimension') != spec['time'] or reduction.get('operation') not in {'mean', 'difference_of_means'}:
                raise FieldPreparationError('Time requires an explicit mean/difference_of_means reduction and dimension=time-coordinate-name, or an explicit scalar isel')
            if reduction.get('weighting') != 'equal_samples' or reduction.get('missing') not in {'skip', 'propagate'}:
                raise FieldPreparationError('Declare reduce weighting=equal_samples and missing=skip or propagate; duration/area weighting is not inferred')
            periods = reduction.get('ranges')
            expected = 1 if reduction['operation'] == 'mean' else 2
            if not isinstance(periods, list) or len(periods) != expected:
                raise FieldPreparationError(f'reduce ranges requires exactly {expected} closed time interval(s)')
            if expected == 2 and reduction.get('direction') != 'second_minus_first':
                raise FieldPreparationError('Declare difference direction=second_minus_first')
            fields = []
            alltimes = arr[spec['time']].values
            for bounds in periods:
                positions = _bounds(alltimes, bounds, 'reduce time')
                part = arr.isel({timedim: _range_slice(positions)}).astype('float64').load()
                if np.isinf(part.values).any(): raise FieldPreparationError('Infinite field values are not a missing-value encoding')
                count = part.count(dim=timedim)
                if transform is not None: part = part * scale + offset
                # Explicit skipna prevents xarray dtype defaults from defining
                # an unstated missing-data policy. All-missing cells stay NA.
                fields.append(part.mean(dim=timedim, skipna=reduction['missing'] == 'skip', keep_attrs=True))
                counts.append(count.transpose(ydim, xdim).values.astype(int))
                time_records.append({'range': list(bounds), 'selected_positions_after_isel': positions.tolist(),
                                     'timestamps': [str(v) for v in alltimes[positions]], 'count': len(positions)})
            reduced = fields[0] if expected == 1 else fields[1] - fields[0]
        else:
            if reduction is not None: raise FieldPreparationError('No remaining declared time dimension to reduce')
            reduced = arr.astype('float64')
            if transform is not None: reduced = reduced * scale + offset
            counts = [np.isfinite(reduced.transpose(ydim, xdim).values).astype(int)]
            if time is not None and spec['time'] in arr.coords:
                time_records = [{'scalar_after_isel': str(arr[spec['time']].values)}]
        z = reduced.transpose(ydim, xdim).values
        xx, yy = arr[spec['x']].values, arr[spec['y']].values
        try:
            field = grid_field(xx, yy, z, limits=spec['limits'], center=spec.get('center'))
        except (ValueError, TypeError) as exc:
            raise FieldPreparationError(str(exc)) from exc
        # Keep per-cell sample counts in exactly the rendered ascending axes.
        if np.all(xx[1:] < xx[:-1]): counts = [v[:, ::-1].copy() for v in counts]
        if np.all(yy[1:] < yy[:-1]): counts = [v[::-1, :].copy() for v in counts]
        X, Y = np.meshgrid(field.x, field.y)
        table = pd.DataFrame({spec['x']: X.ravel(), spec['y']: Y.ravel(), variable: field.z.ravel()})
        file_hash = _digest_file(path)
        report = {'source_path': str(path), 'source_file_sha256': file_hash, 'variable': variable,
            'chart_contract': _plain({key: spec.get(key) for key in CONTRACT_KEYS}),
            'source_variable': original, 'coordinates': coord_report, 'isel': dict(indexers),
            'coordinate_ranges': ranges, 'spatial_positions': spatial_positions, 'reduce': reduction,
            'selected_time': time_records, 'value_transform': transform_report, 'units': units,
            'grid_shape_yx': list(field.z.shape), 'valid_counts_yx': [v.tolist() for v in counts],
            'limits': list(spec['limits']), 'center': spec.get('center'), 'grid_center_convention': 'source coordinates are displayed as cell centers; edges extrapolate half the adjacent spacing',
            'missing_cells': int(np.isnan(field.z).sum()), 'finite_cells': int(np.isfinite(field.z).sum()),
            'decoded_with': 'xarray decode_cf=True, mask_and_scale=True, decode_times=True',
            'engine': engine,
            'grid_mapping': _plain(arr.attrs.get('grid_mapping', arr.encoding.get('grid_mapping'))),
            'implicit_interpolation': False, 'implicit_area_or_duration_weighting': False,
            'boundary': 'Descriptive rectilinear grid; cells/time records are not independent experiments. No projection or longitude conversion, significance, uncertainty or climate attribution is inferred.'}
        from chart_plan import data_digest
        digest = data_digest(table)
        table.attrs[ATTR] = {'report': report, 'data_sha256': digest}
        # Conservative file-level ancestry prevents two reductions of one file
        # being labelled independent. It avoids expanding time*space records.
        table.attrs['light_chart_lineage'] = {'sources': {file_hash: {'name': str(path), 'sha256': file_hash, 'rows': 1,
            'record_unit': 'whole source file; conservative ancestry, not one experimental observation'}},
            'row_origins': [[file_hash + ':0'] for _ in range(len(table))], 'data_sha256': digest,
            'operation': 'explicit CF decode/selection/reduction to grid cells; file-level ancestry, not independent cell observations'}
        return PreparedField(table, field, report)


def field_from_table(data, spec):
    """Validate a prepared cell table and return the same existing GridField."""
    from chart_plan import data_digest
    meta = data.attrs.get(ATTR)
    if not meta or meta.get('data_sha256') != data_digest(data):
        raise FieldPreparationError('A bound NetCDF preparation is required; grid cells or metadata changed after preparation')
    report = meta['report']
    if _plain({key: spec.get(key) for key in CONTRACT_KEYS}) != report['chart_contract']:
        raise FieldPreparationError('Coordinate/selection/reduction/color contract differs from the prepared field; prepare this panel again')
    x, y = spec.get('x'), spec.get('y')
    if x != report['coordinates']['x']['name'] or y != report['coordinates']['y']['name']:
        raise FieldPreparationError('Coordinate mapping differs from the prepared field')
    if len(data) != int(np.prod(report['grid_shape_yx'])) or data.duplicated([y, x]).any():
        raise FieldPreparationError('Grid selection must retain every prepared cell, including missing cells')
    table = data.pivot(index=y, columns=x, values=spec['variable']).sort_index().sort_index(axis=1)
    return grid_field(table.columns.to_numpy(), table.index.to_numpy(), table.to_numpy(), limits=spec['limits'], center=spec.get('center'))


def plan_field_chart(source, spec):
    """Use the ordinary decision schema and actual field constructor checks."""
    from chart_plan import read_data, data_digest
    blockers, diagnostics = [], {'rows_are_independent_units': False}
    warnings = ['A spatial pattern is not independent replication; projection, area/duration weighting and scientific inference remain explicit.']
    try:
        if is_netcdf(source):
            prepared = prepare_netcdf_field(source, spec)
            data, field, report = prepared.table, prepared.field, prepared.report
        else:
            data = read_data(source)
            field = field_from_table(data, spec)
            report = data.attrs[ATTR]['report']
        diagnostics.update(rows=len(data), used_rows=len(data), source_sha256=data_digest(data),
            fields=[spec['x'], spec['y'], spec['variable']], grid_shape_yx=list(field.z.shape),
            finite_cells=int(np.isfinite(field.z).sum()), missing_cells=int(np.isnan(field.z).sum()),
            input_preparation=report, limits=report['limits'], center=report['center'],
            implicit_aggregation=False, row_positions=list(range(len(data))), excluded_rows=[])
        if report['missing_cells']:
            warnings.append('Prepared missing cells remain visible as NA; they are not zero or interpolated.')
    except (FieldPreparationError, ValueError, TypeError) as exc:
        blockers.append(str(exc))
    if spec.get('backend') not in (None, 'python'):
        blockers.append('This NetCDF scalar-field adapter has a Python constructor; native R needs a separately verified adapter.')
    candidate = {'construction': 'rectilinear-scalar-field', 'query': 'prepare_netcdf_field field_from_table grid_field scalar_field',
        'reason': 'Retains explicit physical cell-center coordinates and the declared scalar/missing-value semantics.',
        'tradeoff': 'A flat coordinate-aware map supports precise scalar comparison; no projection, coast geometry, interpolation or 3D view is invented.',
        'backend': 'python', 'rank': 1}
    return {'status': 'needs_resolution' if blockers else 'ready', 'spec': spec, 'diagnostics': diagnostics,
        'candidates': [candidate], 'recommended': None if blockers else candidate, 'blockers': blockers,
        'warnings': warnings, 'rejected': [{'construction': 'automatic-surface-or-projection',
            'reason': 'A scalar grid does not establish a topographic surface or a map projection; choose these only with explicit scientific grounds.'}]}


def expand_netcdf_inputs(sources, spec):
    """Prepare only mapped 2D panel tables, then reuse the ordinary job chain.

This returns transformed sources/spec and provenance. No new parallel evidence
or recommendation system is introduced. Mixed CSV sources remain in that chain.
"""
    import copy
    updated = copy.deepcopy(spec)
    netcdf = {name for name, source in sources.items() if is_netcdf(source)}
    tables = {name: value for name, value in sources.items() if name not in netcdf}
    provenance, used = {}, set()
    if updated.get('panels'):
        for panel in updated['panels']:
            name = panel['source']
            if name not in netcdf: continue
            if panel.get('select'):
                raise FieldPreparationError('NetCDF panel selection belongs in chart.isel/coordinate_ranges/reduce before the cell table is prepared')
            key = '__netcdf__' + name + '__' + panel['id']
            if key in sources or key in tables: raise FieldPreparationError('Reserved prepared source name collision')
            prepared = prepare_netcdf_field(sources[name], panel['chart'])
            tables[key] = prepared.table
            panel['source'] = key
            if name in updated.get('profiles', {}):
                updated['profiles'][key] = copy.deepcopy(updated['profiles'][name])
            provenance[panel['id']] = {'original_source': name, 'prepared_source': key, 'report': prepared.report}
            used.add(name)
    else:
        chart = updated.get('chart')
        if not isinstance(chart, dict): raise FieldPreparationError('A NetCDF task needs an explicit chart object')
        name = updated.get('source') or (next(iter(sources)) if len(sources) == 1 else None)
        if name in netcdf:
            prepared = prepare_netcdf_field(sources[name], chart)
            tables[name] = prepared.table
            provenance['main'] = {'original_source': name, 'prepared_source': name, 'report': prepared.report}
            used.add(name)
    if netcdf - used:
        raise FieldPreparationError('Every supplied NetCDF source needs an explicitly mapped panel: ' + ', '.join(sorted(netcdf - used)))
    return tables, updated, provenance
