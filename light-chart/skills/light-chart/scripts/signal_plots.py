"""Measured signals: faithful overview, windows and explicit density spectra.

Nature figure-contract: complementary evidence, fixed physical-size composition.
SciPilot: inspect sampling/units before selecting marks. FigMirror: retain a
reference's useful local structure without forcing its data or axes.
PSD follows scipy.signal.welch/spectrogram official APIs (scaling='density').
The latter is deliberately used for compatibility with older SciPy installs;
the computation backend and every window parameter are returned for audit.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import signal


def validate_signal(time, values, *, sampling_hz=None, time_unit='s', rtol=1e-5):
    """Require finite, strictly ordered real samples; spectral time is seconds.

    Irregular records may be drawn as raw signals or min/max bins, but are not
    resampled implicitly. A declaration of Hz must agree with second units.
    """
    for raw in (time, values):
        a = np.asarray(raw)
        if np.iscomplexobj(a) or (a.dtype == object and any(isinstance(x, complex) for x in a.flat)):
            raise ValueError('Real samples required; complex components need an explicit separate representation')
    t, y = np.asarray(time, float), np.asarray(values, float)
    if t.ndim != 1 or y.shape != t.shape or len(t) < 2:
        raise ValueError('At least two aligned 1-D samples required')
    if not np.isfinite(t).all() or not np.isfinite(y).all():
        raise ValueError('Finite samples required; resolve gaps explicitly')
    delta = np.diff(t)
    if np.any(delta <= 0):
        raise ValueError('Time must increase strictly; no sorting or duplicate removal is implicit')
    if not isinstance(time_unit, str) or not time_unit.strip():
        raise ValueError('Declare the time unit')
    uniform = bool(np.allclose(delta, np.median(delta), rtol=rtol, atol=0))
    actual_hz = 1 / float(np.median(delta)) if time_unit == 's' else None
    if sampling_hz is not None:
        if not np.isfinite(sampling_hz) or sampling_hz <= 0 or time_unit != 's':
            raise ValueError('Positive sampling_hz needs time_unit=s')
        if not uniform or not np.allclose(delta, 1 / sampling_hz, rtol=rtol, atol=0):
            raise ValueError('Sampling declaration disagrees with actual time intervals')
    return t, y, {'samples': len(t), 'time_range': [float(t[0]), float(t[-1])],
                  'uniform_sampling': uniform, 'sampling_hz': actual_hz,
                  'time_unit': time_unit, 'implicit_resampling': False}


def minmax_envelope(time, values, *, max_bins=1200):
    """Every source row belongs to exactly one contiguous min/max bin.

    Returns half-open source positions and exact extrema positions/times. Bins
    are display aggregation, not independent observations or confidence bands.
    """
    t, y, _ = validate_signal(time, values)
    if not isinstance(max_bins, int) or isinstance(max_bins, bool) or max_bins < 1:
        raise ValueError('max_bins must be a positive integer')
    edges = np.linspace(0, len(t), min(len(t), max_bins) + 1, dtype=int)
    records = []
    for start, stop in zip(edges[:-1], edges[1:]):
        lo = start + int(np.argmin(y[start:stop]))
        hi = start + int(np.argmax(y[start:stop]))
        records.append({'source_start': int(start), 'source_stop': int(stop),
                        'count': int(stop-start), 'time_start': t[start],
                        'time_stop': t[stop-1], 'minimum': y[lo], 'maximum': y[hi],
                        'minimum_position': lo, 'maximum_position': hi,
                        'minimum_time': t[lo], 'maximum_time': t[hi]})
    return pd.DataFrame(records)


def plot_signal_overview(ax, time, values, *, max_bins=1200, color='#285F8F', linewidth=.5):
    """Draw exact within-bin extrema as vertical ranges at bin midtimes."""
    from matplotlib.collections import LineCollection
    bins = minmax_envelope(time, values, max_bins=max_bins)
    mid = (bins.time_start.to_numpy() + bins.time_stop.to_numpy())/2
    segments = np.stack([np.column_stack([mid, bins.minimum]),
                         np.column_stack([mid, bins.maximum])], axis=1)
    mark = LineCollection(segments, colors=color, linewidths=linewidth)
    ax.add_collection(mark); ax.autoscale_view()
    ax.set_xlim(float(np.min(time)), float(np.max(time)))
    ax._light_chart_signal_bins = bins.to_dict('records')
    return bins, mark


def plot_signal_window(ax, time, values, *, window, color='#285F8F', linewidth=.7):
    """Plot unchanged records in an explicit inclusive time window."""
    t, y, _ = validate_signal(time, values)
    if len(window) != 2 or not np.isfinite(window).all() or window[0] >= window[1]:
        raise ValueError('Window must be finite and increasing')
    if window[0] < t[0] or window[1] > t[-1]:
        raise ValueError('Requested window extends beyond measured records')
    positions = np.flatnonzero((t >= window[0]) & (t <= window[1]))
    if len(positions) < 2:
        raise ValueError('Window contains fewer than two measured samples')
    line, = ax.plot(t[positions], y[positions], color=color, lw=linewidth)
    ax.set_xlim(*window)
    return positions, line


def signal_spectra(time, values, *, sampling_hz, signal_unit, nperseg,
                   noverlap, window='hann', detrend='constant'):
    """One-sided PSD and time-resolved PSD using identical explicit windows.

    No zero-padding, resampling or filtering; window centres only, without
    artificial edge extension. PSD units are signal_unit squared per Hz.
    """
    t, y, info = validate_signal(time, values, sampling_hz=sampling_hz)
    if not isinstance(signal_unit, str) or not signal_unit.strip():
        raise ValueError('Declare signal_unit')
    if not isinstance(nperseg, int) or isinstance(nperseg, bool) or not 2 <= nperseg <= len(y):
        raise ValueError('nperseg must be an integer between 2 and the sample count')
    if not isinstance(noverlap, int) or isinstance(noverlap, bool) or not 0 <= noverlap < nperseg:
        raise ValueError('noverlap must be a nonnegative integer below nperseg')
    if detrend not in ('constant', 'linear', False):
        raise ValueError('Declare constant, linear or False detrending')
    kwargs = dict(fs=float(sampling_hz), window=window, nperseg=nperseg,
                  noverlap=noverlap, nfft=nperseg, detrend=detrend,
                  return_onesided=True, scaling='density')
    frequency, psd = signal.welch(y, average='mean', **kwargs)
    f2, centres, power = signal.spectrogram(y, mode='psd', **kwargs)
    if not np.array_equal(frequency, f2):
        raise RuntimeError('Unexpected spectral frequency-grid mismatch')
    import scipy
    params = {**info, **kwargs, 'scipy_version': scipy.__version__,
              'backend': 'scipy.signal.welch + scipy.signal.spectrogram',
              'compatibility_note': 'spectrogram supports older SciPy without ShortTimeFFT',
              'signal_unit': signal_unit, 'density_unit': f'{signal_unit}^2/Hz',
              'frequency_resolution_hz': float(sampling_hz/nperseg),
              'window_duration_s': float(nperseg/sampling_hz),
              'hop_s': float((nperseg-noverlap)/sampling_hz),
              'segments': len(centres), 'implicit_filtering': False,
              'edge_padding': False, 'zero_padding': False}
    return {'frequency_hz': frequency, 'psd': psd, 'time_s': centres+t[0],
            'spectrogram': power, 'parameters': params}


def plot_spectrogram(ax, spectra, *, cmap='magma', frequency_range=None, limits=None,
                     out_of_range='error'):
    """Logarithmic density colour; full values stay in returned spectra.

    Explicit frequency views may crop the display, not the saved computation.
    Zero PSD cells are masked rather than replaced by fabricated tiny values.
    """
    from matplotlib.colors import LogNorm
    f, times, power = spectra['frequency_hz'], spectra['time_s'], spectra['spectrogram']
    selected = np.ones(len(f), dtype=bool)
    if frequency_range is not None:
        if len(frequency_range) != 2 or not 0 <= frequency_range[0] < frequency_range[1] <= f[-1]:
            raise ValueError('Frequency view must lie within the computed Nyquist range')
        selected = (f >= frequency_range[0]) & (f <= frequency_range[1])
    values = power[selected]
    positive = values[values > 0]
    if not len(positive):
        raise ValueError('All spectral densities are zero; logarithmic display is undefined')
    lo, hi = (float(positive.min()), float(positive.max())) if limits is None else limits
    if out_of_range not in {'error','extend'}:
        raise ValueError('out_of_range must be error or explicitly extend')
    under,over=int((positive<lo).sum()),int((positive>hi).sum())
    if not 0 < lo < hi or ((under or over) and out_of_range=='error'):
        raise ValueError('Positive full-range limits required unless an explicit extend display is declared')
    mark = ax.pcolormesh(times, f[selected], np.ma.masked_less_equal(values, 0),
                         norm=LogNorm(lo, hi), cmap=cmap, shading='auto', rasterized=True)
    view = {'frequency_range_hz': [float(f[selected][0]), float(f[selected][-1])],
            'density_limits': [lo, hi], 'zero_cells_masked': int((values <= 0).sum()),
            'below_display_limits':under,'above_display_limits':over,
            'out_of_range':out_of_range,
            'time_centres_range_s': [float(times[0]), float(times[-1])],
            'color_scale': 'logarithmic PSD; under/over cells explicitly counted, underlying values unchanged'}
    return mark, view


def plot_spectral_coverage(ax, mark, *, measured_time_range, color='#C0C3C7', label='Not computed'):
    """Identify display bins beyond actual computed window-centre mesh edges.

    The mesh edges come from Matplotlib's computed coordinates, so no endpoint
    width is invented. These are unavailable spectral estimates, not absent
    raw signal records. All measured time and all computed cells stay visible.
    """
    from matplotlib.patches import Patch
    bounds=np.asarray(measured_time_range,float)
    if bounds.shape!=(2,) or not np.isfinite(bounds).all() or bounds[0]>=bounds[1]:
        raise ValueError('Measured time range must be finite and increasing')
    coordinates=mark.get_coordinates()
    edges=np.asarray(coordinates[0,:,0],float)
    if len(edges)<2 or not np.isfinite(edges).all() or not np.all(np.diff(edges)>0):
        raise ValueError('A valid computed time mesh is required')
    intervals=[]
    if bounds[0]<edges[0]:intervals.append([float(bounds[0]),float(min(edges[0],bounds[1]))])
    if edges[-1]<bounds[1]:intervals.append([float(max(edges[-1],bounds[0])),float(bounds[1])])
    intervals=[pair for pair in intervals if pair[0]<pair[1]]
    for left,right in intervals:
        ax.axvspan(left,right,facecolor=color,edgecolor=color,linewidth=0,zorder=1)
    if intervals:
        ax.legend(handles=[Patch(facecolor=color,edgecolor=color,label=label)],
                  loc='lower right',bbox_to_anchor=(1,1.005),frameon=False,
                  fontsize=7,handlelength=1,handleheight=.7,borderaxespad=0)
    return {'measured_time_range_s':bounds.tolist(),'mesh_time_range_s':[float(edges[0]),float(edges[-1])],
            'uncomputed_display_intervals_s':intervals,
            'meaning':'No computed window-centred density bin; raw recording is present and no edge extrapolation is made'}
