"""Measured impedance constructors, without circuit fitting or area normalization.

Frequency, Re Z and physical Im Z must be explicitly mapped in Hz and ohms.
Nyquist uses (Re Z, -Im Z); Bode uses |Z| and atan2(Im Z, Re Z).
Matplotlib aspect reference: https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.set_aspect.html
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ImpedanceData:
    """Copied input rows, jointly sorted by spectrum and increasing frequency."""
    rows: pd.DataFrame
    spectrum_order: tuple[str, ...]
    units: str = 'ohm'


def _real(values, name):
    original = np.asarray(values, dtype=object)
    if any(isinstance(v, (complex, np.complexfloating, bool, np.bool_))
           for v in original.flat):
        raise ValueError(name + ' must contain real numeric observations, not complex or Boolean values')
    try:
        a = np.asarray(values, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(name + ' must be numeric') from exc
    if not np.isfinite(a).all():
        raise ValueError(name + ' must be finite')
    return a


def prepare_impedance(data, *, spectrum, frequency, real, imag, unit, spectrum_order=None):
    """Validate measured spectra with explicit physical Im Z, Hz and ohm units.

    Preserves every observation and extra source column in a copy. Duplicate
    frequencies within a spectrum are rejected; repeats need explicit separate
    spectrum identities. Spectra may have different frequency grids.
    """
    if unit != 'ohm':
        raise ValueError('Explicit unit=ohm is required; convert units before this constructor')
    names = [spectrum, frequency, real, imag]
    if len(set(names)) != 4 or not all(isinstance(n, str) and n for n in names):
        raise ValueError('Four distinct explicit field names are required')
    if not isinstance(data, pd.DataFrame) or data.empty or data.columns.duplicated().any():
        raise ValueError('A nonempty DataFrame with unique columns is required')
    if not set(names) <= set(data.columns):
        raise ValueError('Missing mapped impedance fields')
    ids = data[spectrum].tolist()
    if any(not isinstance(v, str) or not v.strip() for v in ids):
        raise ValueError('Spectrum identities must be nonempty strings')
    observed = list(dict.fromkeys(ids))
    order = observed if spectrum_order is None else list(spectrum_order)
    if len(order) != len(set(order)) or set(order) != set(observed):
        raise ValueError('spectrum_order must contain each observed identity exactly once')
    # A canonical source name is safe only in its matching physical role.
    # Exempting every mapped name would overwrite cross-role observations.
    canonical_sources = {'spectrum': spectrum, 'frequency_hz': frequency,
                         'real_ohm': real, 'imag_ohm': imag}
    reserved = {'spectrum', 'frequency_hz', 'real_ohm', 'imag_ohm',
                'negative_imag_ohm', 'magnitude_ohm', 'phase_deg', 'source_position'}
    matching = {name for name, source in canonical_sources.items() if name == source}
    collisions = (reserved & set(data.columns)) - matching
    if collisions:
        raise ValueError('Input has reserved derived-column names outside their matching roles: ' +
                         ', '.join(sorted(collisions)) + '; explicitly rename these source fields')
    rows = data.copy(deep=True)
    rows['spectrum'] = ids
    rows['frequency_hz'] = _real(data[frequency], frequency)
    rows['real_ohm'] = _real(data[real], real)
    rows['imag_ohm'] = _real(data[imag], imag)
    if (rows.frequency_hz <= 0).any():
        raise ValueError('Frequency must be strictly positive in Hz')
    if rows.duplicated(['spectrum', 'frequency_hz']).any():
        raise ValueError('Duplicate frequency within a spectrum; explicitly identify repeats')
    if (rows.groupby('spectrum').size() < 2).any():
        raise ValueError('Each spectrum needs at least two measured frequencies')
    rows['negative_imag_ohm'] = -rows.imag_ohm
    with np.errstate(over='raise', invalid='raise'):
        try:
            rows['magnitude_ohm'] = np.hypot(rows.real_ohm, rows.imag_ohm)
        except FloatingPointError as exc:
            raise ValueError('Impedance magnitude is outside finite floating-point range') from exc
    rows['phase_deg'] = np.rad2deg(np.arctan2(rows.imag_ohm, rows.real_ohm))
    rows['source_position'] = np.arange(len(rows))
    rank = {name: i for i, name in enumerate(order)}
    # Sort by external positional keys; source metadata named _rank is retained.
    positions = np.lexsort((rows.frequency_hz.to_numpy(), rows.spectrum.map(rank).to_numpy()))
    rows = rows.iloc[positions].reset_index(drop=True)
    return ImpedanceData(rows, tuple(order))


def _encodings(result, encodings):
    if not isinstance(result, ImpedanceData):
        raise ValueError('Use prepare_impedance before drawing')
    if not isinstance(encodings, Mapping) or set(encodings) != set(result.spectrum_order):
        raise ValueError('Explicit one-to-one spectrum encodings are required')
    for spec in encodings.values():
        if not isinstance(spec, Mapping) or not {'color','marker','linestyle'} <= set(spec):
            raise ValueError('Each spectrum needs color, marker and linestyle')


def _bounds(limits, *, x, y, detail):
    if limits is None:
        return None
    a = _real(limits, 'limits')
    if a.shape != (4,) or not (a[0] < a[1] and a[2] < a[3]):
        raise ValueError('Limits are (xmin,xmax,ymin,ymax), increasing and finite')
    if not detail and (x.min() < a[0] or x.max() > a[1] or y.min() < a[2] or y.max() > a[3]):
        raise ValueError('Overview limits must cover all measured points; use an explicit detail panel for zooming')
    return a


def _mark_style(spec, markersize, linewidth):
    """Per-spectrum physical marks; no coordinate offset or frequency thinning.

    A larger open marker behind a small filled marker can expose coincidence
    honestly. Size denotes identity only, never impedance or uncertainty.
    """
    values = {'markersize': spec.get('markersize', markersize),
              'linewidth': spec.get('linewidth', linewidth),
              'markeredgewidth': spec.get('markeredgewidth', .65),
              'zorder': spec.get('zorder', 2), 'alpha': spec.get('alpha', 1.)}
    for key, value in values.items():
        a = _real([value], key)[0]
        if (key in {'markersize', 'linewidth'} and a <= 0) or (
                key == 'markeredgewidth' and a < 0) or (key == 'alpha' and not 0 < a <= 1):
            raise ValueError('Drawing styles require positive visible marks and 0 < alpha <= 1')
    return {**values, 'markerfacecolor': spec.get('markerfacecolor', 'white')}


def plot_nyquist(ax, result, *, encodings, limits=None, detail=False, markersize=3, linewidth=1):
    """Draw all rows at equal physical units; detail=True explicitly permits zoom.

    A detail axes retains all source vertices and reports the visible-point
    counts. An overview remains necessary whenever some vertices are outside it.
    Lines join measured frequencies and do not imply a fitted circuit.
    """
    _encodings(result, encodings)
    if not isinstance(detail, bool):
        raise ValueError('detail must be Boolean')
    if detail and limits is None:
        raise ValueError('A detail panel needs explicit limits')
    r = result.rows
    lim = _bounds(limits, x=r.real_ohm, y=r.negative_imag_ohm, detail=detail)
    lines, visible = {}, {}
    for name in result.spectrum_order:
        part = r.loc[r.spectrum == name]
        spec = encodings[name]
        lines[name], = ax.plot(part.real_ohm, part.negative_imag_ohm, color=spec['color'],
            marker=spec['marker'], linestyle=spec['linestyle'],
            **_mark_style(spec, markersize, linewidth), label=name)
        inside = np.ones(len(part), dtype=bool) if lim is None else (
            part.real_ohm.between(lim[0],lim[1]) & part.negative_imag_ohm.between(lim[2],lim[3]))
        visible[name] = {'total': len(part), 'inside_view': int(np.sum(inside))}
    if lim is not None:
        ax.set_xlim(lim[:2]); ax.set_ylim(lim[2:])
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel('Re Z (Ω)'); ax.set_ylabel('−Im Z (Ω)')
    return {'lines': lines, 'detail': detail, 'coverage': visible,
            'requires_overview': any(v['inside_view'] < v['total'] for v in visible.values())}


def plot_bode(magnitude_ax, phase_ax, result, *, encodings, frequency_limits=None,
              magnitude_limits=None, phase_limits=None, markersize=3, linewidth=1):
    """Separate magnitude/phase panels with the same log-frequency extent.

    All magnitudes must be positive for log display. No inferred uncertainties,
    wrapping, unwrapping, smoothing or fitting is applied.
    """
    _encodings(result, encodings)
    if magnitude_ax is phase_ax:
        raise ValueError('Use separate magnitude and phase axes, not a dual y axis')
    r = result.rows
    if (r.magnitude_ohm <= 0).any():
        raise ValueError('Log Bode magnitude cannot display zero impedance')
    def validate_pair(limits, values, name, positive=False):
        if limits is None:
            return None
        a = _real(limits, name)
        if a.shape != (2,) or not a[0] < a[1] or (positive and a[0] <= 0):
            raise ValueError(name + ' must be increasing valid limits')
        if values.min() < a[0] or values.max() > a[1]:
            raise ValueError(name + ' must cover all measured values')
        return a
    fl = validate_pair(frequency_limits, r.frequency_hz, 'frequency_limits', True)
    ml = validate_pair(magnitude_limits, r.magnitude_ohm, 'magnitude_limits', True)
    pl = validate_pair(phase_limits, r.phase_deg, 'phase_limits')
    if fl is None:
        lo, hi = r.frequency_hz.min(), r.frequency_hz.max()
        pad = .035 * np.log10(hi/lo)
        fl = (lo/10**pad, hi*10**pad)
    lines = {}
    for name in result.spectrum_order:
        part = r.loc[r.spectrum == name]; spec = encodings[name]; pair = []
        for ax, y in [(magnitude_ax, part.magnitude_ohm),(phase_ax, part.phase_deg)]:
            line, = ax.plot(part.frequency_hz, y, color=spec['color'], marker=spec['marker'],
                linestyle=spec['linestyle'], **_mark_style(spec, markersize, linewidth), label=name)
            ax.set_xscale('log'); ax.set_xlim(fl); pair.append(line)
        lines[name] = pair
    magnitude_ax.set_yscale('log')
    if ml is not None: magnitude_ax.set_ylim(ml)
    if pl is not None: phase_ax.set_ylim(pl)
    magnitude_ax.set_ylabel('|Z| (Ω)'); phase_ax.set_ylabel('Phase (°)')
    phase_ax.set_xlabel('Frequency (Hz)')
    return {'lines':lines, 'frequency_limits':list(map(float,fl)),
            'rows_per_spectrum': r.groupby('spectrum').size().to_dict()}
