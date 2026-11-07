"""Compile a declared scientific evidence graph against actual input tables.

Nature's claim/role architecture, SciPilot's data decisions, FigMirror's motif
preservation and figures4papers' complementary comparisons. No inference is
invented: independence and claims remain explicit scientific decisions.
"""
from __future__ import annotations
import hashlib
import json
from itertools import combinations
from chart_plan import read_data, data_digest, plan_chart, measurement_fields
from study_data import lineage


def selected_panel_data(data, source_positions):
    """Take recorded iloc positions in order and assign canonical panel indices.

    The source is unchanged. Original row identity stays in the source digest,
    source_positions and original-record lineage, rather than a retained pandas
    index that could be noncontiguous, repeated or unrelated to row positions.
    """
    return data.iloc[list(source_positions)].reset_index(drop=True)


def plan_evidence(tables, spec, *, profiles=None):
    """Validate panel-level decisions, dependencies, coverage and independence.

    tables maps source names to DataFrames/files. Each panel declares id, source,
    role, question, claim, chart spec and optional depends_on. Optional select is
    a dict of field -> allowed values; exact selected source positions are saved.
    Selection preserves source row order. Panel indices start at zero; the
    original source digest and source_positions retain the exact row mapping.
    independence={from:panel_id,key:unit_field} checks actual identity overlap;
    disjoint IDs alone never establish independent assays or study populations.
    """
    data = {k: read_data(v) for k,v in tables.items()}
    if not spec.get('question') or not spec.get('claims') or not spec.get('panels'):
        raise ValueError('Declare question, claims and panels')
    claims = spec['claims']
    if len({p['id'] for p in spec['panels']}) != len(spec['panels']):
        raise ValueError('Unique panel IDs required')
    blockers, warnings, panels, selected, complementary = [], [], {}, {}, []
    for panel in spec['panels']:
        key = panel['id']; source = panel['source']
        if source not in data or panel.get('claim') not in claims:
            raise ValueError(f'{key}: unknown source or claim')
        if not panel.get('role') or not panel.get('question'):
            raise ValueError(f'{key}: declare a distinct role and question')
        d = data[source]; keep = d.index.to_series().map(lambda _: True).to_numpy()
        for field, values in panel.get('select', {}).items():
            if field not in d or not isinstance(values,list) or not values:
                raise ValueError(f'{key}: explicit nonempty selection values required')
            keep &= d[field].isin(values).to_numpy()
        positions = [i for i,v in enumerate(keep) if v]
        used = selected_panel_data(d, positions)
        if used.empty: raise ValueError(f'{key}: selection is empty')
        decision = plan_chart(used, panel['chart'], sources=data, profile=(profiles or {}).get(source))
        if decision['status'] != 'ready':
            blockers.extend(f'{key}: {b}' for b in decision['blockers'])
        ancestry=lineage(d,source)
        tokens=sorted({token for i in positions for token in ancestry['row_origins'][i]})
        panels[key] = {**panel, 'source_positions':positions, 'selected_data_sha256':data_digest(used),
                       'selection_provenance':{'source_sha256':data_digest(d),
                           'row_order':'source row order; select values specify membership, not ordering',
                           'index_policy':'zero-based contiguous panel index; source_positions[i] maps panel row i to original source iloc position'},
                       'origin_records':tokens, 'original_sources':ancestry['sources'], 'decision':decision}
        selected[key] = used
    # Dependencies are semantic reading dependencies, not fabricated causality.
    active, visited, order = set(), set(), []
    def visit(key):
        if key not in panels: raise ValueError('Unknown dependency: '+key)
        if key in active: raise ValueError('Evidence dependency cycle: '+key)
        if key in visited: return
        active.add(key)
        for dep in panels[key].get('depends_on',[]): visit(dep)
        active.remove(key); visited.add(key); order.append(key)
    for key in panels: visit(key)
    for claim, contract in claims.items():
        supporting = [p for p in panels.values() if p['claim']==claim]
        for role in contract.get('required_roles',[]):
            if role not in {p['role'] for p in supporting}:
                blockers.append(f'{claim}: required evidence role absent: {role}')
        if not supporting: blockers.append('Unsupported claim: '+claim)
        if not contract.get('boundary'):
            warnings.append(f'{claim}: declare the limit of this claim')
    def measured(chart):
        # The aggregate-count role belongs to count_table. Other constructors
        # ignore it, so an extra key must not manufacture a new measurement.
        return measurement_fields(chart if chart.get('intent') == 'count_table' else
                                  {k:v for k,v in chart.items() if k != 'count'})
    for a,b in combinations(panels,2):
        pa,pb=panels[a],panels[b]
        ca,cb=pa['chart'],pb['chart']
        same_records = (pa['source']==pb['source'] and pa['source_positions']==pb['source_positions']) or pa['selected_data_sha256']==pb['selected_data_sha256']
        if same_records and measured(ca)==measured(cb):
            warnings.append(f'{a}/{b}: same records and measurements; complementary views are not independent validation')
        ma,mb=measured(ca),measured(cb)
        if same_records and ma & mb:
            same_transform = all(ca.get(k)==cb.get(k) for k in
                                 ('transform','normalization','aggregate','estimand'))
            semantic_keys=('intent','x','y','values','group','condition','unit','series','repeat','lower','upper',
                           'time','event','transform','normalization','aggregate','estimand',
                           'numerator_events','numerator_non_events','comparator_events','comparator_non_events',
                           'true','predicted','class_order','spectrum','frequency','real','imaginary',
                           'confidence','effect','effect_scale','reference','risk_scale',
                           'min_cpm','min_samples','heatmap_n','method','value_semantics')
            if ca.get('intent') == cb.get('intent') == 'count_table':
                semantic_keys += ('dimensions','count','count_semantics')
                if ca.get('view') == cb.get('view') == 'alluvial':
                    semantic_keys += ('relationship_semantics',)
            def construction(panel):
                decision=panel['decision']
                return (decision.get('recommended') or (decision['candidates'][0] if decision['candidates'] else {})).get('construction')
            # Real count/impedance view choices already select distinct
            # constructions. Ignored view prose is not a different encoding.
            same_encoding=(construction(pa)==construction(pb) and
                           all(ca.get(k)==cb.get(k) for k in semantic_keys))
            contained=ma <= mb or mb <= ma
            needs_explanation=same_transform and contained
            gains={key:panels[key].get('unique_inference','') for key in (a,b)}
            complementary.append({'panels':[a,b], 'shared_measurements':sorted(ma & mb),
                'relationship':'same_measurements' if ma==mb else 'contained_measurements' if contained else 'overlapping_measurements',
                'same_declared_transform':same_transform,'same_declared_encoding':same_encoding,
                'declared_unique_inference':gains,
                'review_required':needs_explanation,
                'boundary':'Shared inputs may support necessary complementary views; this is a review cue, not a redundancy verdict.'})
            if needs_explanation:
                warnings.append(f'{a}/{b}: possible repeated evidence; explain the distinct inference gained from each view')
                if spec.get('require_complementarity') and not all(gains.values()):
                    blockers.append(f'{a}/{b}: declare unique_inference for overlapping evidence views')
                elif spec.get('require_complementarity') and same_encoding:
                    blockers.append(f'{a}/{b}: identical records, measurements and construction do not add distinct evidence; change the actual view or merge the duplicate panels')
            if same_encoding and gains[a] and gains[a]==gains[b]:
                warnings.append(f'{a}/{b}: identical encoding and inference description; review merging or moving one panel')
        overlap=set(pa['origin_records']) & set(pb['origin_records'])
        if overlap and not same_records:
            warnings.append(f'{a}/{b}: derived views share {len(overlap)} original records; not independent validation')
    for key,panel in panels.items():
        independence=panel.get('independence')
        if independence:
            other, field = independence['from'], independence.get('key')
            if other not in panels: raise ValueError('Unknown independence comparison panel')
            original_overlap=set(panels[key]['origin_records']) & set(panels[other]['origin_records'])
            if original_overlap:
                blockers.append(f'{key}: claimed independent evidence shares {len(original_overlap)} original records with {other}')
            if field is None:
                if not original_overlap: warnings.append(f'{key}: no original-record overlap found; distinct patients/experiments still require provenance')
                continue
            if other not in selected or any(field not in selected[k] for k in (key,other)):
                raise ValueError('Independence check requires known panels and identity fields')
            if any(selected[k][field].isna().any() for k in (key,other)):
                blockers.append(f'{key}: missing identities prevent independence comparison')
            shared=set(selected[key][field]) & set(selected[other][field])
            panel['identity_overlap']={'field':field,'count':len(shared),'against':other}
            if shared: blockers.append(f'{key}: claimed independent evidence shares {len(shared)} identities with {other}')
            else: warnings.append(f'{key}: disjoint IDs checked; study/assay independence still requires provenance')
    sources={k:{'sha256':data_digest(v),'rows':len(v),'columns':list(v.columns)} for k,v in data.items()}
    digest=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest()
    return {'status':'needs_resolution' if blockers else 'ready', 'question':spec['question'],
            'claims':claims,'panels':panels,'reading_order':order,'sources':sources,
            'source_data_sha256':digest,'blockers':blockers,'warnings':warnings,
            'complementarity':complementary,
            'boundary':'Checks declared contracts against records; does not prove claims or scientific independence.'}


def audit_evidence_layout(plan, composition_report):
    """Check required panels and their declared minimum physical evidence areas."""
    rectangles=composition_report['plot_rectangles_mm']; errors=[]
    for key,panel in plan['panels'].items():
        if key not in rectangles:
            errors.append('Required evidence panel absent: '+key); continue
        rect=rectangles[key]; area=rect[2]*rect[3]
        if area < panel.get('min_area_mm2',0):
            errors.append(f'{key}: data area {area:.1f} mm² below declared minimum')
    return {'status':'FAIL' if errors or plan['status']!='ready' else 'PASS','errors':errors,
            'source_data_sha256':plan['source_data_sha256'],
            'boundary':'Physical budgets and declared coverage; necessity and interpretability need rendered review.'}
