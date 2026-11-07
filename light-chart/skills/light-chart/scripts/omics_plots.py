"""Descriptive bulk-count structure, with explicit identities and display boundaries.

CPM is library-total scaling, not a differential-expression estimator. No tests,
p/q values, batch correction, imputation or biological annotation are inferred.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


def align_sample_metadata(sample_ids, metadata, sample_id):
    """Return an exact, reordered one-to-one metadata copy; never drop samples."""
    ids = pd.Index(sample_ids)
    if not len(ids) or not ids.is_unique or ids.hasnans:
        raise ValueError('Sample IDs must be nonempty, unique and nonmissing')
    if sample_id not in metadata:
        raise ValueError('Metadata sample ID column is required')
    keys = pd.Index(metadata[sample_id])
    if not keys.is_unique or keys.hasnans:
        raise ValueError('Metadata IDs must be unique and nonmissing')
    if set(keys) != set(ids):
        raise ValueError('Sample IDs and metadata must match exactly')
    return metadata.set_index(sample_id, drop=False).loc[ids].copy()


@dataclass
class CountStructure:
    counts: pd.DataFrame
    metadata: pd.DataFrame
    cpm: pd.DataFrame
    log_cpm: pd.DataFrame
    gene_summary: pd.DataFrame
    sample_qc: pd.DataFrame
    scores: pd.DataFrame
    loadings: pd.DataFrame
    explained_variance_ratio: np.ndarray
    heatmap_z: pd.DataFrame
    heatmap_gene_order: list
    heatmap_sample_order: list
    parameters: dict


def analyze_count_structure(counts, metadata, *, sample_id, min_cpm=None,
                            min_samples=3, heatmap_n=24, pseudocount=1., min_count=None):
    """Analyze genes × samples counts without changing the source matrix.

    All rows are retained in counts/CPM/log2(CPM+pseudocount). PCA uses every gene
    meeting one declared prevalence rule and having nonzero sample variance:
    CPM >= min_cpm (default 1), or raw counts >= min_count, in >= min_samples.
    These two eligibility thresholds are mutually exclusive. PCA is gene-centered
    without variance scaling. The heatmap shows heatmap_n highest-variance genes
    from this same eligible set, then row z scores (sample SD, ddof=1).
    Ties are ordered by gene ID; clustering is average-linkage Euclidean with
    optimal leaf ordering. Heatmap sample distances use the full PCA input,
    rather than allowing the displayed feature subset to set sample order.
    """
    from scipy.cluster.hierarchy import linkage, leaves_list
    if not isinstance(counts, pd.DataFrame) or counts.shape[0] < 2 or counts.shape[1] < 3:
        raise ValueError('A genes-by-samples DataFrame with >=2 genes and >=3 samples is required')
    if (not counts.index.is_unique or counts.index.hasnans or
            not counts.columns.is_unique or counts.columns.hasnans):
        raise ValueError('Unique nonmissing gene and sample IDs are required')
    if any(not isinstance(v, str) or not v.strip() for v in [*counts.index, *counts.columns]):
        raise ValueError('Gene and sample IDs must be nonempty strings')
    if any(not pd.api.types.is_numeric_dtype(t) or pd.api.types.is_bool_dtype(t) for t in counts.dtypes):
        raise ValueError('Counts must be numeric, not booleans or strings')
    if np.iscomplexobj(counts.to_numpy()):
        raise ValueError('Counts must be real, not complex')
    a = counts.to_numpy(dtype=float)
    if not np.isfinite(a).all() or (a < 0).any() or not np.equal(a, np.floor(a)).all():
        raise ValueError('Finite nonnegative integer counts are required')
    if isinstance(min_samples, bool) or not isinstance(min_samples, int) or not 1 <= min_samples <= counts.shape[1]:
        raise ValueError('min_samples must be an integer within the sample count')
    def positive_scalar(value, name):
        if (isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating))
                or not np.isfinite(value) or value <= 0):
            raise ValueError(name + ' must be a finite positive real number')
    if min_count is not None and min_cpm is not None:
        raise ValueError('Declare only one eligibility threshold: min_cpm or min_count')
    if min_count is None:
        min_cpm = 1. if min_cpm is None else min_cpm
        positive_scalar(min_cpm, 'min_cpm')
    else:
        positive_scalar(min_count, 'min_count')
    positive_scalar(pseudocount, 'pseudocount')
    if isinstance(heatmap_n, bool) or not isinstance(heatmap_n, int) or heatmap_n < 2:
        raise ValueError('heatmap_n must be an integer >=2')
    meta = align_sample_metadata(counts.columns, metadata, sample_id)
    depth = a.sum(axis=0)
    if (depth <= 0).any() or not np.isfinite(depth).all():
        raise ValueError('Every sample needs a positive finite library total')
    cpm = counts.astype(float).div(depth, axis=1) * 1e6
    log = np.log2(cpm + pseudocount)
    variance = log.var(axis=1, ddof=1)
    basis, threshold = ('cpm', min_cpm) if min_count is None else ('count', min_count)
    passes = (cpm if basis == 'cpm' else counts) >= threshold
    eligible = (passes.sum(axis=1) >= min_samples) & (variance > 0)
    genes = sorted(counts.index[eligible])
    if len(genes) < 2:
        raise ValueError('At least two varying genes must meet the declared eligibility rule')
    # Sorting before factorization makes gene-input shuffles exactly reproducible.
    x = log.loc[genes].T
    centered = x - x.mean(axis=0)
    u, singular, vt = np.linalg.svd(centered.to_numpy(), full_matrices=False)
    for j in range(len(singular)):
        anchor = np.argmax(np.abs(vt[j]))
        if vt[j, anchor] < 0:
            u[:, j] *= -1
            vt[j] *= -1
    k = min(counts.shape[1] - 1, len(genes))
    names = [f'PC{i+1}' for i in range(k)]
    scores = pd.DataFrame(u[:, :k] * singular[:k], index=counts.columns, columns=names)
    loadings = pd.DataFrame(vt[:k].T, index=genes, columns=names)
    evr = singular[:k] ** 2 / np.sum(singular ** 2)
    ranked = sorted(genes, key=lambda g: (-variance[g], g))
    chosen = ranked[:min(heatmap_n, len(ranked))]
    heat = log.loc[chosen]
    z = heat.sub(heat.mean(axis=1), axis=0).div(heat.std(axis=1, ddof=1), axis=0)
    rows = leaves_list(linkage(z.to_numpy(), method='average', metric='euclidean', optimal_ordering=True))
    cols = leaves_list(linkage(centered.to_numpy(), method='average', metric='euclidean', optimal_ordering=True))
    gene_info = pd.DataFrame({'all_zero': a.sum(axis=1) == 0,
        'n_samples_' + basis + '_ge_threshold': passes.sum(axis=1),
        'log_cpm_variance_ddof1': variance, 'pca_eligible': eligible,
        'heatmap_selected': counts.index.isin(chosen)}, index=counts.index)
    qc = pd.DataFrame({'sum_gene_counts': depth,
        'detected_genes_nonzero': (a > 0).sum(axis=0),
        'genes_' + basis + '_ge_threshold': passes.sum(axis=0)}, index=counts.columns)
    return CountStructure(counts.copy(), meta, cpm, log, gene_info, qc, scores,
        loadings, evr, z, list(z.index[rows]), list(counts.columns[cols]),
        {'normalization': 'CPM = counts / sum_gene_counts * 1e6',
         'transformation': 'log2(1 + CPM)' if pseudocount == 1 else f'log2(CPM + {pseudocount:g})',
         'pseudocount': float(pseudocount),
         'all_zero_handling': 'counts and CPM remain zero; transformed value is log2(pseudocount); ineligible for PCA/heatmap',
         'all_zero_transformed_value': float(np.log2(pseudocount)),
         'eligibility_basis': basis, 'eligibility_threshold': float(threshold),
         'min_cpm': None if min_cpm is None else float(min_cpm),
         'min_count': None if min_count is None else float(min_count), 'min_samples': min_samples,
         'pca_genes': len(genes), 'pca_gene_scaling': 'center only; no variance scaling',
         'heatmap_selection': 'largest transformed-CPM sample variance; ties by gene ID',
         'heatmap_n_requested': heatmap_n, 'heatmap_n_actual': len(chosen),
         'heatmap_standardization': 'row z score; sample SD ddof=1',
         'row_clustering': 'average-linkage Euclidean on displayed row z scores; optimal leaf order',
         'sample_clustering': 'average-linkage Euclidean on full PCA input; optimal leaf order',
         'inference': None})


def pca_scores(ax, scores, metadata, *, sample_id, explained_variance_ratio,
               color, colors, shape=None, markers=None, point_size=28,
               edgecolor=None, linewidth=.45):
    """Draw unchanged PC1/PC2 with equal physical length per data unit.

    Metadata matches scores exactly by sample ID. Color and optional shape are
    independent categorical fields, so condition and pair/batch identities need
    not be collapsed. Returns one actual artist per ID, aligned metadata and the
    unchanged scores, plus separate legend handles for caller-owned placement.
    Pair connections can use these returned ID-indexed scores and metadata;
    pairing, line order and inference are never guessed. No labels/limits/legend
    are silently discarded to fit. Reserve physical space before drawing.
    """
    from matplotlib.colors import is_color_like
    from matplotlib.lines import Line2D
    from matplotlib.markers import MarkerStyle
    from project_style import role
    if ax.name != 'rectilinear' or ax.get_xscale() != 'linear' or ax.get_yscale() != 'linear':
        raise ValueError('PCA scores require a rectilinear axes with linear x/y scales')
    if (not isinstance(scores, pd.DataFrame) or scores.empty or
            not {'PC1', 'PC2'} <= set(scores.columns) or
            any(not pd.api.types.is_numeric_dtype(scores[c]) or pd.api.types.is_bool_dtype(scores[c])
                for c in ('PC1', 'PC2')) or np.iscomplexobj(scores[['PC1', 'PC2']].to_numpy()) or
            not np.isfinite(scores[['PC1', 'PC2']].to_numpy(dtype=float)).all()):
        raise ValueError('Finite real PC1/PC2 scores indexed by sample ID are required')
    meta = align_sample_metadata(scores.index, metadata, sample_id)
    evr = np.asarray(explained_variance_ratio)
    if (evr.ndim != 1 or len(evr) < 2 or np.iscomplexobj(evr) or
            not np.issubdtype(evr.dtype, np.number) or not np.isfinite(evr).all() or
            (evr < 0).any() or (evr > 1).any() or evr.sum() > 1 + 1e-9):
        raise ValueError('Explained variance ratios must be finite fractions summing to at most one')
    if color not in meta or meta[color].isna().any() or not isinstance(colors, dict) or not colors:
        raise ValueError('A complete metadata color field and explicit category colors are required')
    if not set(meta[color]) <= colors.keys() or not all(is_color_like(c) for c in colors.values()):
        raise ValueError('Every observed color category needs a valid explicit color')
    if shape is not None:
        if (shape not in meta or meta[shape].isna().any() or not isinstance(markers, dict) or
                not set(meta[shape]) <= markers.keys()):
            raise ValueError('Every observed shape category needs an explicit marker')
        for marker in markers.values():
            MarkerStyle(marker)
    elif markers is not None:
        raise ValueError('Declare the shape metadata field when supplying markers')
    if (not np.isfinite([point_size, linewidth]).all() or point_size <= 0 or linewidth < 0):
        raise ValueError('Positive finite point size and nonnegative linewidth required')
    edgecolor = role('ink') if edgecolor is None else edgecolor
    if not is_color_like(edgecolor):
        raise ValueError('A valid point edge color is required')
    artists = {}
    for sid in scores.index:
        artist = ax.scatter(*scores.loc[sid, ['PC1', 'PC2']], s=point_size,
            c=[colors[meta.loc[sid, color]]],
            marker='o' if shape is None else markers[meta.loc[sid, shape]],
            edgecolors=edgecolor, linewidths=linewidth, zorder=3)
        artist.set_gid(str(sid))
        artists[sid] = artist
    ax.set(xlabel=f'PC1 ({100*evr[0]:.1f}%)', ylabel=f'PC2 ({100*evr[1]:.1f}%)')
    ax.set_aspect('equal', adjustable='box')
    color_handles = [Line2D([], [], linestyle='none', marker='o', color=colors[c],
        markeredgecolor=edgecolor, label=str(c)) for c in colors if c in set(meta[color])]
    shape_handles = [] if shape is None else [Line2D([], [], linestyle='none', marker=markers[c],
        color=edgecolor, label=str(c)) for c in markers if c in set(meta[shape])]
    return {'artists': artists, 'scores': scores.copy(), 'metadata': meta,
            'sample_ids': list(scores.index), 'color_handles': color_handles,
            'shape_handles': shape_handles, 'color_field': color, 'shape_field': shape,
            'equal_data_units': True}


def expression_heatmap(ax, values, metadata, *, sample_id, annotation_axes,
                       annotation_colors, row_order=None, sample_order=None,
                       limits, cmap, sample_labels=None, negative_ticks=False):
    """Draw supplied values and categorical tracks; compute no analysis/filtering.

    Values and metadata require exact sample identity. Explicit orders must be
    permutations, annotation maps must cover every observed category, and color
    limits must contain every finite displayed value. Missing values are rejected.
    """
    from color_tools import continuous_scale
    from matplotlib.colors import ListedColormap
    if (not isinstance(values, pd.DataFrame) or values.empty or
            np.iscomplexobj(values.to_numpy()) or not np.isfinite(values.to_numpy(dtype=float)).all()):
        raise ValueError('A nonempty finite display matrix is required')
    if not values.index.is_unique or values.index.hasnans:
        raise ValueError('Unique nonmissing feature IDs are required')
    meta = align_sample_metadata(values.columns, metadata, sample_id)
    rows = list(values.index if row_order is None else row_order)
    cols = list(values.columns if sample_order is None else sample_order)
    if len(rows) != len(values) or len(set(rows)) != len(rows) or set(rows) != set(values.index):
        raise ValueError('Row order must be an exact feature permutation')
    if len(cols) != len(values.columns) or len(set(cols)) != len(cols) or set(cols) != set(values.columns):
        raise ValueError('Sample order must be an exact sample permutation')
    norm, cm, scale = continuous_scale(values.to_numpy(), mode='diverging', limits=limits, center=0, cmap=cmap)
    image = ax.imshow(values.loc[rows, cols], aspect='auto', interpolation='nearest', cmap=cm, norm=norm)
    sign_count = 0
    if negative_ticks:
        from project_style import role
        rr, cc = np.where(values.loc[rows, cols].to_numpy() < 0)
        ax.plot(cc-.32, rr, linestyle='none', marker='|', markersize=2.4,
                markeredgewidth=.55, color=role('ink'), label='_negative_z')
        sign_count = len(rr)
    labels = cols if sample_labels is None else [sample_labels[c] for c in cols]
    ax.set(xticks=range(len(cols)), xticklabels=labels, yticks=range(len(rows)), yticklabels=rows)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for column, track in annotation_axes.items():
        if column not in meta or column not in annotation_colors or meta[column].isna().any():
            raise ValueError('Complete annotation columns and color mappings are required')
        mapping = annotation_colors[column]
        if not set(meta[column]) <= set(mapping):
            raise ValueError('Unmapped annotation categories')
        categories = list(mapping)
        codes = [categories.index(meta.loc[c, column]) for c in cols]
        track.imshow([codes], aspect='auto', interpolation='nearest',
                     cmap=ListedColormap([mapping[c] for c in categories]),
                     vmin=-.5, vmax=len(categories)-.5)
        track.set(xticks=[], yticks=[])
        track.set_ylabel(column, rotation=0, ha='right', va='center', labelpad=5)
        for spine in track.spines.values():
            spine.set_visible(False)
    return {'image': image, 'scale': scale, 'row_ids': rows, 'sample_ids': cols,
            'negative_tick_count': sign_count,
            'annotations': {c: meta.loc[cols, c].tolist() for c in annotation_axes}}
