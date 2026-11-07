"""Auditable multi-table descriptive summaries, not automatic study inference.

Every derived row retains exact original record positions. Attribute hashes
reject stale provenance after an unrecorded DataFrame edit. Row identity denotes
source records; it does not establish independent patients or experiments.
"""
from itertools import product
from statistics import NormalDist
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from chart_plan import read_data, data_digest

ATTR = 'light_chart_lineage'


def lineage(data, name='input'):
    """Return validated provenance, creating literal-record provenance if absent."""
    meta = data.attrs.get(ATTR)
    if meta is None:
        digest = data_digest(data)
        return {'sources': {digest: {'name': name, 'sha256': digest, 'rows': len(data)}},
                'row_origins': [[f'{digest}:{i}'] for i in range(len(data))],
                'data_sha256': digest, 'operation': 'literal source records'}
    if meta.get('data_sha256') != data_digest(data) or len(meta.get('row_origins', [])) != len(data):
        raise ValueError('Stale lineage: data changed without recording its derivation')
    for tokens in meta['row_origins']:
        for token in tokens:
            digest, position = token.rsplit(':', 1)
            if digest not in meta['sources'] or not position.isdigit() or not 0 <= int(position) < meta['sources'][digest]['rows']:
                raise ValueError('Invalid original-record reference')
    return meta


def _bind(data, sources, row_origins, operation):
    data.attrs[ATTR] = {'sources': sources, 'row_origins': row_origins,
                       'data_sha256': data_digest(data), 'operation': operation}
    return data


def save_study_table(data, path):
    """Persist CSV plus byte-bound original-record lineage; preserve text codes.

    read_data() automatically validates/loads the sidecar. The binding uses the
    actual parsed storage table, so ordinary floating-point CSV round trips do
    not incorrectly inherit the in-memory signature. Raw source bytes remain
    the caller's separate provenance responsibility.
    """
    if data.columns.duplicated().any() or any(not isinstance(c,str) for c in data.columns):
        raise ValueError('Unique text column names required for CSV storage')
    meta=lineage(data);path=Path(path)
    if path.suffix.lower() not in ['.csv','.tsv']: raise ValueError('CSV or TSV path required')
    path.parent.mkdir(parents=True,exist_ok=True);sep='\t' if path.suffix.lower()=='.tsv' else ','
    text={str(c):'str' for c in data if pd.api.types.is_string_dtype(data[c].dtype) or data[c].dtype==object}
    for c in text:
        if not all(isinstance(v,str) for v in data[c].dropna()):
            raise ValueError('Object columns must contain text; normalize mixed objects explicitly')
        if data[c].eq('').any():raise ValueError('Empty text is ambiguous in CSV; normalize it explicitly')
    data.to_csv(path,index=False,sep=sep)
    restored=pd.read_csv(path,sep=sep,dtype=text,keep_default_na=False,na_values=[''])
    bound={**meta,'data_sha256':data_digest(restored)}
    payload={'format_version':1,'csv_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
             'string_columns':text,'lineage':bound}
    Path(str(path)+'.lineage.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return payload


def combine_cohorts(tables, *, cohort='cohort', record='record_id'):
    """Concatenate equal schemas without deduplication or invented patient IDs."""
    if not tables or cohort == record:
        raise ValueError('Named tables and distinct reserved column names required')
    frames, origins, sources, schema = [], [], {}, None
    known=set()
    for name, source in tables.items():
        d = read_data(source)
        if d.empty or d.columns.duplicated().any() or cohort in d or record in d:
            raise ValueError('Nonempty unique schemas without reserved columns required')
        if schema is None: schema = list(d.columns)
        if set(schema) != set(d.columns):
            raise ValueError('Cohort schemas differ: harmonize meanings explicitly before combining')
        meta = lineage(d, str(name)); tokens={token for row in meta['row_origins'] for token in row}
        if known & tokens:raise ValueError('Known original records reused across cohorts; resolve duplicate sources before pooling')
        known.update(tokens);sources.update(meta['sources']);origins.extend(meta['row_origins'])
        d = d[schema].copy(); d.attrs = {}
        d[cohort] = str(name); d[record] = [f'{name}:row:{i}' for i in range(len(d))]
        frames.append(d)
    result = pd.concat(frames, ignore_index=True)
    if result[record].duplicated().any(): raise ValueError('Source names do not give unique record labels')
    return _bind(result, sources, origins, 'concatenate equal-schema cohorts; no patient matching')


def missingness_summary(tables, columns):
    """Count literal NA and recorded zeros separately; never reinterpret zero."""
    if not columns or len(columns) != len(set(columns)):
        raise ValueError('Unique, explicit analysis columns required')
    cells, cohorts = [], []
    for name, source in tables.items():
        d = read_data(source)
        if d.empty or any(c not in d for c in columns): raise ValueError('Missing columns or empty cohort')
        complete = ~d[columns].isna().any(axis=1)
        cohorts.append({'cohort': str(name), 'records': len(d), 'complete_records': int(complete.sum()),
                        'complete_positions': np.flatnonzero(complete).tolist(), 'source_sha256': data_digest(d)})
        for col in columns:
            cells.append({'cohort': str(name), 'variable': col, 'records': len(d),
                          'missing': int(d[col].isna().sum()), 'recorded_zero': int(d[col].eq(0).sum()),
                          'missing_fraction': float(d[col].isna().mean())})
    return pd.DataFrame(cells), {'cohorts': cohorts, 'columns': list(columns),
        'boundary': 'Complete-case counts refer only to these fields; recorded zeros are not inferred missing values.'}


def grouped_lineage(source, result, *, by, operation):
    """Bind a caller-computed grouped table to its contributing source records.

    This verifies group membership and provenance, not the arithmetic or validity
    of the declared operation. Empty declared groups retain an empty footprint.
    """
    d=read_data(source); result=result.copy(); meta=lineage(d)
    if not by or not operation or any(c not in d or c not in result for c in by):
        raise ValueError('Declared operation and shared grouping fields required')
    if d[by].isna().any().any() or result[by].isna().any().any():
        raise ValueError('Resolve missing grouping identities before binding lineage')
    lookup={}
    for i,key in enumerate(d[by].itertuples(index=False,name=None)):
        lookup.setdefault(key,set()).update(meta['row_origins'][i])
    origins=[sorted(lookup.get(key,set())) for key in result[by].itertuples(index=False,name=None)]
    result.attrs={}
    return _bind(result,meta['sources'],origins,operation)


def binomial_estimates(source, *, event, groups, unit, levels, interval,
                       confidence=.95, missing='resolve'):
    """Observed binary fractions with explicit Wilson intervals and denominators.

    Groups/levels specify the full cross-product, including empty cells. Missing
    outcomes never become negatives. Duplicate units block accidental repeated-
    measure inference. Wilson intervals assume independent Bernoulli records;
    the caller must justify that assumption for the scientific application.
    """
    d = read_data(source)
    if interval != 'wilson' or not 0 < confidence < 1 or missing not in ['resolve', 'exclude']:
        raise ValueError('Explicit Wilson method, confidence in (0,1), and missing policy required')
    if not groups or len(groups) != len(set(groups)) or set(levels) != set(groups):
        raise ValueError('Unique grouping columns and their complete levels required')
    if any(c not in d for c in [event, unit, *groups]) or len({event, unit, *groups}) != 2+len(groups):
        raise ValueError('Distinct existing event, unit and grouping fields required')
    if d[unit].isna().any() or d[unit].duplicated().any():
        raise ValueError('One nonmissing record per declared unit required; repeated measures need another estimator')
    observed = d[event].dropna()
    if not observed.isin([0, 1]).all(): raise ValueError('Event must be explicitly binary; no automatic recoding')
    for field in groups:
        values = levels[field]
        if not values or len(values) != len(set(values)) or any(pd.isna(v) for v in values):
            raise ValueError('Nonempty unique nonmissing group levels required')
        if not d[field].dropna().isin(values).all(): raise ValueError('Group levels would silently omit observed values')
    invalid = d[[event, *groups]].isna().any(axis=1).to_numpy()
    if invalid.any() and missing == 'resolve': raise ValueError('Resolve missing outcomes/groups or explicitly exclude and report')
    meta = lineage(d); rows, origins = [], []
    if any(len(tokens)!=1 for tokens in meta['row_origins']):
        raise ValueError('Binomial intervals require individual records, not grouped derivatives')
    if len({tokens[0] for tokens in meta['row_origins']})!=len(d):
        raise ValueError('Known original records repeated; unit labels do not establish independence')
    z = NormalDist().inv_cdf((1+confidence)/2)
    for values in product(*(levels[g] for g in groups)):
        mask = ~invalid
        for field, value in zip(groups, values): mask = mask & d[field].eq(value).to_numpy()
        positions = np.flatnonzero(mask); n = len(positions); k = int(d.iloc[positions][event].sum())
        p = k/n if n else np.nan
        if n:
            den = 1+z*z/n; mid = (p+z*z/(2*n))/den
            half = z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
            low, high = max(0., mid-half), min(1., mid+half)
        else: low = high = np.nan
        rows.append(dict(zip(groups, values), numerator=k, denominator=n, estimate=p, lower=low, upper=high))
        origins.append(sorted({token for i in positions for token in meta['row_origins'][i]}))
    result = _bind(pd.DataFrame(rows), meta['sources'], origins, 'grouped binary fraction; explicit Wilson interval')
    return result, {'source_data_sha256': data_digest(d), 'event': event, 'unit': unit, 'groups': groups,
        'levels': levels, 'confidence': confidence, 'interval': interval, 'included_records': int((~invalid).sum()),
        'excluded_positions': np.flatnonzero(invalid).tolist(),
        'missing_outcome_positions': np.flatnonzero(d[event].isna()).tolist(),
        'empty_cells': [r for r in rows if r['denominator']==0],
        'boundary': 'Observed sample fractions, not population prevalence or causal effects; independent-record Wilson model is an explicit assumption.'}
