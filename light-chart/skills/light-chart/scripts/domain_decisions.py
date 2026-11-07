"""Value-aware decisions for domain constructors; unsupported intents return None.

Sampling/identity/transform gates complement the Nature evidence contract and
SciPilot diagnosis. This module neither estimates significance nor silently
resamples, aggregates repeated units, filters species or fits mechanisms.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def plan_domain_chart(source, spec, *, sources=None, profile=None):
    intent = spec.get('intent')
    if intent == 'count_table':
        from count_tables import plan_count_chart
        return plan_count_chart(source, spec)
    if intent == 'repeated_trajectory':
        from repeated_measures import plan_repeated_chart
        return plan_repeated_chart(source, spec)
    if intent not in {'signal', 'ordination', 'impedance', 'count_structure',
                      'two_arm_risk_evidence', 'computational-sweep', 'confusion-counts'}:
        return None
    from chart_plan import read_data, data_digest
    data = read_data(source)
    if data.empty or data.columns.duplicated().any():
        raise ValueError('Nonempty data with unique columns required')
    if intent in {'computational-sweep', 'confusion-counts'}:
        from computational_plots import plan_computational_chart
        result = plan_computational_chart(data, spec)
        roles = ('x', 'y', 'series', 'repeat') if intent == 'computational-sweep' else ('unit', 'true', 'predicted')
        result['diagnostics'].update(source_sha256=data_digest(data), row_positions=list(range(len(data))),
            fields=list(dict.fromkeys(spec[k] for k in roles if spec.get(k))))
        if intent == 'computational-sweep' and any(
                np.iscomplexobj(data[spec[k]].to_numpy()) for k in ('x', 'y') if spec.get(k) in data):
            result['blockers'].append('Measured computational x/y must be real, not complex')
            result.update(status='needs_resolution', recommended=None)
        return result
    blockers, warnings, candidates, rejected = [], [], [], []
    diag = {'rows': len(data), 'source_sha256': data_digest(data),
            'row_positions': list(range(len(data))), 'excluded_rows': [],
            'used_rows': len(data), 'rows_are_independent_units': False}

    def candidate(name, query, reason, tradeoff, **extra):
        candidates.append(dict(construction=name, query=query, reason=reason,
                               tradeoff=tradeoff, rank=len(candidates)+1, **extra))

    def required_fields(roles):
        fields = []
        for role in roles:
            value = spec.get(role)
            if not value:
                blockers.append('Declare role: '+role)
            elif value not in data:
                raise ValueError('Unknown field: '+str(value))
            else:
                fields.append(value)
        diag['fields'] = list(dict.fromkeys(fields))
        return len(fields) == len(roles)

    if intent == 'count_structure':
        fields_ok = required_fields(['unit'])
        values = spec.get('values', [])
        if not isinstance(values, list) or len(values) < 3 or len(set(values)) != len(values):
            blockers.append('Declare at least three unique sample count fields')
            fields_ok = False
        elif any(v not in data for v in values):
            raise ValueError('Unknown sample count fields')
        elif spec.get('unit') in values:
            blockers.append('Gene identity must be separate from sample count fields')
            fields_ok = False
        else:
            diag['fields'] += values
        for key, expected in [('value_semantics', 'gene_counts'), ('normalization', 'library_total_cpm')]:
            if spec.get(key) != expected:
                blockers.append(f'Declare {key}={expected} for the bulk-count constructor')
        transform = spec.get('transform')
        pseudocount = spec.get('pseudocount', 1.)
        if transform == 'log2_1plus_cpm':
            if pseudocount != 1.:
                blockers.append('log2_1plus_cpm requires pseudocount=1; use log2_cpm for another declared positive pseudocount')
        elif transform == 'log2_cpm':
            if 'pseudocount' not in spec:
                blockers.append('Declare pseudocount for transform=log2_cpm')
        else:
            blockers.append('Declare transform=log2_1plus_cpm or log2_cpm with explicit pseudocount')
        thresholds = [k for k in ('min_cpm', 'min_count') if k in spec]
        thresholds_valid = len(thresholds) == 1 and all(spec[k] is not None for k in thresholds)
        if not thresholds_valid:
            blockers.append('Declare exactly one finite positive eligibility threshold: min_cpm or min_count')
        for key in ('min_samples', 'heatmap_n'):
            if key not in spec:
                blockers.append('Declare '+key)
        metadata_name = spec.get('metadata_source')
        sample_id = spec.get('sample_id')
        metadata = None
        if not isinstance(metadata_name, str) or not metadata_name or not sources or metadata_name not in sources:
            blockers.append('Named sample metadata_source from the supplied sources is required; sample names do not define annotations')
        else:
            metadata = read_data(sources[metadata_name])
            diag['metadata_source'] = metadata_name
            diag['metadata_sha256'] = data_digest(metadata)
        if not isinstance(sample_id, str) or not sample_id:
            blockers.append('Declare sample_id in the named metadata source')
        annotations = spec.get('annotations', [])
        if not isinstance(annotations, list) or len(annotations) != len(set(annotations)):
            blockers.append('Annotations must be unique metadata field names')
        elif metadata is not None:
            for field in annotations:
                if field not in metadata or metadata[field].isna().any():
                    blockers.append('Complete explicit metadata annotation required: '+str(field))
        if (fields_ok and metadata is not None and sample_id and thresholds_valid and
                all(k in spec for k in ('min_samples', 'heatmap_n'))):
            from omics_plots import analyze_count_structure
            try:
                analysis = analyze_count_structure(data.set_index(spec['unit'])[values], metadata,
                    sample_id=sample_id, pseudocount=pseudocount,
                    **{k:spec[k] for k in (*thresholds,'min_samples','heatmap_n')})
                diag.update(gene_ids=list(analysis.counts.index), sample_ids=list(analysis.counts.columns),
                    metadata_ids_in_count_order=analysis.metadata[sample_id].tolist(),
                    metadata_join='exact_one_to_one', genes=len(analysis.counts), samples=len(values),
                    eligible_genes=analysis.parameters['pca_genes'], parameters=analysis.parameters,
                    explained_variance_ratio=analysis.explained_variance_ratio.tolist(),
                    profile_supplied=profile is not None)
            except (ValueError, TypeError, KeyError) as exc:
                blockers.append(str(exc))
        candidate('count-expression-structure', 'analyze_count_structure pca_scores expression_heatmap',
                  'Sample projection, raw-library coverage and named feature patterns answer distinct descriptive questions.',
                  'Variance-selected display genes do not establish differential expression; CPM is library-total scaling.', backend='python')
        rejected.extend([{'construction': name, 'reason': reason} for name, reason in [
            ('volcano-or-MA-inference', 'Counts alone supply neither differential estimates nor p/q values.'),
            ('hellinger-count-ordination', 'This bulk-gene question declares log-transformed CPM, not ecological proportions.'),
            ('PC-score-heatmap', 'Repeating the same projection does not expose named feature structure.')]])
        warnings.append('No differential expression, enrichment, batch correction or biological annotation is inferred.')
    elif intent == 'two_arm_risk_evidence':
        roles = ['unit', 'label', 'numerator_events', 'numerator_non_events', 'comparator_events', 'comparator_non_events']
        fields_ok = required_fields(roles)
        expected = {'independent_binomial_working_model_explicit': True, 'effect': 'RR',
                    'effect_scale': 'ratio', 'reference': 1, 'zero_event_policy': 'unavailable_no_correction'}
        for key, value in expected.items():
            if spec.get(key) != value or (key == 'independent_binomial_working_model_explicit' and spec.get(key) is not True):
                blockers.append(f'Declare {key}={value}; only unadjusted independent-binomial study risks are supported')
        if 'confidence' not in spec:
            blockers.append('Declare confidence for log-Wald RR and Wilson arm-risk intervals')
        if spec.get('risk_scale') not in {'linear', 'log'}:
            blockers.append('Declare risk_scale=linear/log')
        if any(spec.get(k) for k in ('adjusted', 'pooled', 'clustered', 'weights')):
            blockers.append('Adjusted, pooled or clustered evidence requires a justified estimator and supplied analysis; this constructor does none')
        if fields_ok and 'confidence' in spec:
            from effect_plots import analyze_2x2, validate_effects, align_studies
            count_fields = [spec[k] for k in roles[2:]]
            try:
                if np.iscomplexobj(data[count_fields].to_numpy()):
                    raise ValueError('Observed 2x2 counts must be real, not complex')
                analysis = analyze_2x2(data, id_col=spec['unit'], label_col=spec['label'],
                    counts=count_fields, confidence=spec['confidence'])
                methods = analysis.attrs['methods'].copy()
                analysis = align_studies(analysis, spec.get('order', analysis[spec['unit']]),
                    id_col=spec['unit'], label_col=spec['label'])
                available = validate_effects(analysis, effect_scale=spec.get('effect_scale'), reference=spec.get('reference'),
                    id_col=spec['unit'], label_col=spec['label'])
                risk_cols = ['risk_'+arm+suffix for arm in ('numerator', 'comparator') for suffix in ('', '_low', '_high')]
                risk = analysis[risk_cols].to_numpy(float)
                if spec.get('risk_scale') == 'log' and (risk <= 0).any():
                    blockers.append('Zero risk/bound cannot be hidden on a log axis; use linear')
                diag.update(study_ids=analysis[spec['unit']].tolist(), units=len(analysis), methods=methods,
                    rr_available=int(available.sum()), unavailable_rr_ids=analysis.loc[~available, spec['unit']].tolist(),
                    recommended_risk_scale='linear' if (risk <= 0).any() else spec.get('risk_scale'),
                    observed_risk_evidence=analysis[[spec['unit'], 'n_numerator', 'n_comparator', 'rr', 'rr_low', 'rr_high', 'rr_status', *risk_cols]].to_dict('records'))
                for key, bounds in [('effect_limits', analysis.loc[available, ['rr_low','rr_high']].to_numpy(float).ravel()),
                                    ('risk_limits', analysis[[c for c in risk_cols if c.endswith(('_low','_high'))]].to_numpy(float).ravel()*100)]:
                    limits = spec.get(key)
                    if limits is not None:
                        values_to_show = np.r_[bounds, 1] if key == 'effect_limits' else bounds
                        if (len(limits) != 2 or not np.isfinite(limits).all() or limits[0] >= limits[1] or
                                (key == 'effect_limits' and limits[0] <= 0) or
                                (values_to_show < limits[0]).any() or (values_to_show > limits[1]).any()):
                            blockers.append(key+' must retain every interval and the declared reference on its scale')
            except (ValueError, TypeError, KeyError) as exc:
                blockers.append(str(exc))
        candidate('study-risk-ratio-and-absolute-risk', 'two-arm-counts risk-ratio absolute-risk',
                  'Within-study RR supplies relative contrast; aligned arm risks and counts restore baseline risk and support.',
                  'Log-Wald RR and Wilson risks use the explicit independent-binomial working model; zero-event RR stays unavailable.', backend='python')
        rejected.append({'construction': 'pooled-or-adjusted-effect', 'reason': 'Observed 2x2 counts alone do not specify pooling, adjusted effects or design-based uncertainty.'})
        warnings.append('Study rows remain descriptive study-specific evidence; arms are not independent replications of studies, and binomial CIs need not reproduce original design-based uncertainty.')
    elif intent == 'signal':
        fields_ok = required_fields(['time', 'y'])
        for key in ('time_unit', 'signal_unit'):
            if not isinstance(spec.get(key), str) or not spec[key].strip():
                blockers.append('Declare '+key)
        if fields_ok:
            from signal_plots import validate_signal
            try:
                _, _, sampling = validate_signal(data[spec['time']], data[spec['y']],
                    sampling_hz=spec.get('sampling_hz'), time_unit=spec.get('time_unit', ''))
                diag.update(sampling)
            except (ValueError, TypeError) as exc:
                blockers.append(str(exc))
        candidate('signal-overview-window', 'signal waveform',
                  'Full-span extrema and unchanged local records answer different scale questions.',
                  'Display bins are not confidence intervals or independent samples.')
        if diag.get('uniform_sampling') and spec.get('sampling_hz') and spec.get('time_unit') == 's':
            candidate('signal-time-frequency', 'signal spectrogram PSD',
                      'Uniform measured seconds support explicit windowed density spectra.',
                      'Choose and report window duration, overlap, detrending and frequency view.')
        else:
            rejected.append({'construction': 'signal-time-frequency',
                             'reason': 'Hz-domain spectra require actual uniform second sampling and its declared rate; no implicit interpolation.'})
        rejected.append({'construction': 'smoothed-representative-waveform',
                         'reason': 'Would conceal extrema or nonstationary changes without an explicit analysis method.'})
        warnings.append('One measured trace is not a population sample; no inferential n is supplied.')
    elif intent == 'ordination':
        values = spec.get('values', [])
        field_ok = required_fields(['unit'])
        if not isinstance(values, list) or len(values) < 2 or len(set(values)) != len(values):
            blockers.append('Declare at least two unique numerical value fields')
        else:
            if any(v not in data for v in values):
                raise ValueError('Unknown matrix fields')
            numeric = data[values].apply(pd.to_numeric, errors='coerce')
            complex_input = np.iscomplexobj(numeric.to_numpy())
            a = None if complex_input else numeric.to_numpy(float)
            diag['fields'] += values
            diag['features'] = len(values)
            if complex_input:
                blockers.append('Hellinger input must be real; complex matrix values are not cover classes or counts')
            elif not np.isfinite(a).all():
                blockers.append('Resolve missing/nonfinite matrix cells; no implicit species/site exclusion')
            elif (a < 0).any():
                blockers.append('Hellinger input must be nonnegative')
            elif (a.sum(axis=1) == 0).any():
                blockers.append('Zero-total sites have undefined Hellinger proportions')
            elif np.linalg.matrix_rank(np.sqrt(a/a.sum(axis=1, keepdims=True)) - np.sqrt(a/a.sum(axis=1, keepdims=True)).mean(axis=0)) < 2:
                blockers.append('Fewer than two nonzero ordination dimensions')
        if field_ok:
            ids = data[spec['unit']]
            if ids.isna().any() or ids.astype(str).duplicated().any():
                blockers.append('Unique nonmissing site/sample IDs required')
            diag['units'] = int(ids.nunique())
        if spec.get('transform') != 'hellinger' or spec.get('method') != 'pca':
            blockers.append('Current native-R constructor requires explicit transform=hellinger and method=pca')
        if not spec.get('value_semantics'):
            blockers.append('Declare value_semantics (for example cover_class or counts)')
        candidate('hellinger-pca-ordination', 'ordination PCA',
                  'Hellinger transformation and centred, unscaled PCA describe compositional site differences.',
                  'Axes are a projection, not causal effects; labels and metadata must retain site identities.', backend='r')
        candidate('community-matrix', 'heatmap',
                  'The original feature matrix identifies species patterns hidden by projection.',
                  'Use explicit raw/normalized semantics and keep all requested rows and columns.', backend='r')
        warnings.append('Environmental grouping is descriptive; group separation is not a hypothesis test.')
    else:
        fields_ok = required_fields(['spectrum', 'frequency', 'real', 'imaginary'])
        for key, expected in [('frequency_unit','Hz'), ('impedance_unit','ohm'),
                              ('imaginary_convention','physical_signed')]:
            if spec.get(key) != expected:
                blockers.append('Measured impedance requires explicit '+key+'='+expected+'; convert source units/sign convention before this constructor')
        view = spec.get('view', 'nyquist_bode')
        if view not in {'nyquist_bode','nyquist','bode'}:
            blockers.append('Declare impedance view=nyquist_bode, nyquist or bode')
        for key in ('fit','circuit_fit','mechanism','area_normalization','phase_unwrap'):
            value = spec.get(key)
            if value is not None and value is not False and value != 'none':
                blockers.append('The measured impedance constructor does not perform '+key)
        if fields_ok and not blockers:
            from impedance_plots import prepare_impedance
            try:
                analysis = prepare_impedance(data, spectrum=spec['spectrum'], frequency=spec['frequency'],
                    real=spec['real'], imag=spec['imaginary'], unit=spec['impedance_unit'], spectrum_order=spec.get('order'))
                rows = analysis.rows
                if view != 'nyquist' and (rows.magnitude_ohm <= 0).any():
                    blockers.append('Logarithmic Bode requires nonzero measured |Z|; zero observations cannot be hidden')
                ranges = {'frequency_limits':(rows.frequency_hz, True),
                          'magnitude_limits':(rows.magnitude_ohm, True),
                          'phase_limits':(rows.phase_deg, False)}
                for key, (values, positive) in ranges.items():
                    if spec.get(key) is not None:
                        raw = np.asarray(spec[key])
                        if np.iscomplexobj(raw) or any(isinstance(v,(complex,np.complexfloating,bool,np.bool_)) for v in raw.flat):
                            raise ValueError(key+' must contain real numerical bounds')
                        bounds = np.asarray(raw, dtype=float)
                        if (bounds.shape != (2,) or not np.isfinite(bounds).all() or bounds[0]>=bounds[1]
                                or (positive and bounds[0]<=0) or values.min()<bounds[0] or values.max()>bounds[1]):
                            raise ValueError(key+' must preserve every measured observation on the declared scale')
                if spec.get('nyquist_limits') is not None:
                    raw = np.asarray(spec['nyquist_limits'])
                    if np.iscomplexobj(raw) or any(isinstance(v,(complex,np.complexfloating,bool,np.bool_)) for v in raw.flat):
                        raise ValueError('nyquist_limits must contain real numerical bounds')
                    bounds=np.asarray(raw,dtype=float)
                    if (bounds.shape!=(4,) or not np.isfinite(bounds).all() or bounds[0]>=bounds[1] or bounds[2]>=bounds[3]
                            or rows.real_ohm.min()<bounds[0] or rows.real_ohm.max()>bounds[1]
                            or rows.negative_imag_ohm.min()<bounds[2] or rows.negative_imag_ohm.max()>bounds[3]):
                        raise ValueError('Nyquist overview limits must preserve every measured observation; an explicit detail requires its full overview')
                diag.update(spectrum_order=list(analysis.spectrum_order),
                    spectrum_rows={name:int((rows.spectrum==name).sum()) for name in analysis.spectrum_order},
                    frequency_extents_Hz={name:[float(part.frequency_hz.min()),float(part.frequency_hz.max())]
                        for name,part in rows.groupby('spectrum',sort=False)},
                    positive_physical_imaginary_points={name:int((part.imag_ohm>0).sum())
                        for name,part in rows.groupby('spectrum',sort=False)},
                    source_positions_in_frequency_order=rows.source_position.tolist(),
                    phase_range_deg=[float(rows.phase_deg.min()),float(rows.phase_deg.max())],
                    view=view, frequency_unit='Hz', impedance_unit='ohm', imaginary_convention='physical_signed',
                    all_signed_quadrants_retained=True, implicit_resampling=False, no_rows_excluded=True)
            except (ValueError,TypeError,OverflowError) as exc:
                blockers.append(str(exc))
        query = {'nyquist_bode':'prepare_impedance plot_nyquist plot_bode',
                 'nyquist':'prepare_impedance plot_nyquist', 'bode':'prepare_impedance plot_bode'}.get(view,'prepare_impedance')
        candidate('measured-impedance-'+str(view), query,
                  'Measured complex-plane geometry and frequency-resolved magnitude/phase expose different features of the same observations.',
                  'Keep signed quadrants and physical units; a magnified detail complements its overview. Lines join observations, not fitted circuits.', backend='python')
        rejected.append({'construction':'fitted-circuit-or-area-normalized-impedance',
                         'reason':'Measured spectra alone do not establish a circuit mechanism, causal intervention effect or a reliable electrode-area normalization.'})
        warnings.append('Sequential spectra are not automatically independent replicates. No fit, mechanism, filtering, phase unwrapping or inferential interval is computed.')
    return dict(status='needs_resolution' if blockers else 'ready', intent=intent,
                spec=spec, diagnostics=diag, recommended=candidates[0] if candidates and not blockers else None,
                candidates=candidates, rejected=rejected, blockers=list(dict.fromkeys(blockers)),
                warnings=warnings, boundary='Domain checks do not establish scientific claims or visual quality.')
