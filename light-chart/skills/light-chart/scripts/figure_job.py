"""Prepare a Nature-style scientific figure job from actual inputs.

This joins the adapted SciPilot data profiler, data-aware chart decisions,
Nature evidence contracts and concrete implementation retrieval. It prepares
and validates a task; drawing, reading the render and revision remain explicit.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import numpy as np

from chart_plan import read_data, data_digest, measurement_fields
from evidence_tools import plan_evidence, selected_panel_data
from library import plan as plan_chart_resources
from profile_data import profile_data


FIELD_ROLES = ('x','y','variable','count','unit','group','condition','lower','upper','time','event',
               'label','numerator_events','numerator_non_events','comparator_events',
               'comparator_non_events','series','repeat','true','predicted',
               'spectrum','frequency','real','imaginary')


def _profiles(data, spec, charts):
    profiles={}
    for name, table in data.items():
        relevant=[chart for source,chart in charts if source==name]
        explicit=spec.get('profiles',{}).get(name,{})
        groups=list(dict.fromkeys(c[k] for c in relevant for k in ('group','condition') if c.get(k)))
        identities=list(dict.fromkeys(c['unit'] for c in relevant if c.get('unit')))
        identities += [c['spectrum'] for c in relevant if c.get('spectrum') and c['spectrum'] not in identities]
        identities += [c['sample_id'] for _,c in charts if c.get('metadata_source')==name and c.get('sample_id') not in identities and c.get('sample_id') in table]
        groups += [field for _,c in charts if c.get('metadata_source')==name for field in c.get('annotations',[]) if field in table and field not in groups]
        options={'group_cols':groups,'id_cols':identities,**explicit}
        # The SciPilot real-valued summaries must not cast away imaginary
        # components before the scientific constructor can reject/map them.
        complex_columns=[field for field in table if np.iscomplexobj(table[field].to_numpy()) or
                         any(isinstance(value,(complex,np.complexfloating)) for value in table[field])]
        if complex_columns:
            options['column_types']={**options.get('column_types',{}), **{field:'unknown' for field in complex_columns}}
        pairs={(c['unit'],c['condition']) for c in relevant if c.get('unit') and c.get('condition')}
        if len(pairs)==1 and not {'pair_col','condition_col'} & explicit.keys():
            pair,condition=next(iter(pairs));options.update(pair_col=pair,condition_col=condition)
        profiles[name]=profile_data(table,**options)
        if any(c.get('intent') == 'count_table' for c in relevant):
            profiles[name]['observation_structure'] = {
                'data_level':'aggregate_count_cells', 'rows_are_independent_units':False,
                'boundary':'Cell rows and zero cells are supplied summaries, not individual observations or survey weights; use explicit integer counts and denominators.'}
        if any(c.get('intent') == 'repeated_trajectory' for c in relevant):
            profiles[name]['observation_structure'] = {
                'data_level':'repeated_observations', 'rows_are_independent_units':False,
                'boundary':'Unit IDs link observations; row count is not independent sample size, and the first coordinate is not an inferred baseline.'}
        if complex_columns:
            profiles[name]['unsupported_complex_columns']=complex_columns
            profiles[name]['warnings'].append('Complex columns were retained without real-valued summary statistics; explicitly map physical components before a real-valued constructor.')
    return profiles


def prepare_job(sources, spec):
    """Validate and retrieve a single-chart or multi-panel task.

    ``sources`` is a DataFrame/file or a name -> DataFrame/file mapping.
    Single-chart specs contain ``question`` and ``chart`` (or a flat intent).
    Multi-panel specs use plan_evidence's question/claims/panels contract.
    ``profiles`` optionally maps source names to profiler semantic overrides.
    Domain adapters may compute explicitly declared descriptive quantities and
    working-model intervals for validation. No figures or global preferences
    are created, and no unrequested estimator or filtering rule is inferred.
    """
    if not isinstance(spec,dict):
        raise TypeError('spec must be an object')
    if not isinstance(sources,dict):
        sources={'data':sources}
    if not sources:
        raise ValueError('At least one real input table is required')
    from field_data import is_netcdf, expand_netcdf_inputs, FieldPreparationError
    if any(is_netcdf(value) for value in sources.values()):
        if not isinstance(spec.get('question'),str) or not spec['question'].strip():
            return {'status':'needs_resolution', 'decisions':{}, 'profiles':{}, 'field_mapping':{},
                    'implementation_adaptations':[], 'source_use':[],
                    'blockers':['Declare the scientific question before selecting a figure.'], 'warnings':[],
                    'boundary':'NetCDF preparation did not execute without a scientific question.'}
        try:
            prepared_sources, prepared_spec, provenance = expand_netcdf_inputs(sources, spec)
        except FieldPreparationError as exc:
            return {'status':'needs_resolution', 'question':spec.get('question'), 'decisions':{},
                    'profiles':{}, 'field_mapping':{}, 'implementation_adaptations':[],
                    'source_use':[], 'blockers':[str(exc)], 'warnings':[],
                    'next_action':'Resolve the explicit NetCDF scientific input contract before rendering.',
                    'boundary':'No source was silently skipped; NetCDF preparation failed before rendering.'}
        result = prepare_job(prepared_sources, prepared_spec)
        result['input_preparation'] = provenance
        for panel_id, entry in provenance.items():
            result.get('field_mapping',{}).get(panel_id,{}).update(original_source=entry['original_source'])
        result['source_use'].append({'source':'light-chart','operation':'executed',
            'implementation':'scripts/field_data.py:prepare_netcdf_field',
            'result':'Explicit CF selection/reduction before the ordinary profiler/evidence/implementation decisions; no time-by-space table.'})
        return result
    data={name:read_data(source) for name,source in sources.items()}
    if any(not name or table.empty for name,table in data.items()):
        raise ValueError('Named nonempty input tables required')
    blockers=[]
    if not isinstance(spec.get('question'),str) or not spec['question'].strip():
        blockers.append('Declare the scientific question before selecting a figure.')
    backend=spec.get('backend')
    if backend not in {None,'python','r'}:
        raise ValueError('backend must be python or r')
    size=spec.get('size_mm')
    if size is not None and (not isinstance(size,(list,tuple)) or len(size)!=2 or
            any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in size)):
        raise ValueError('size_mm must be positive finite width and height')
    if spec.get('panels'):
        # Required question/claim logic is checked before any recommendation.
        if blockers:
            return {'status':'needs_resolution','blockers':blockers,'panels':{},
                    'boundary':'Task preparation only; no drawing or review was performed.'}
        charts=[(panel['source'],panel['chart']) for panel in spec['panels']]
        profiles=_profiles(data,spec,charts)
        evidence=plan_evidence(data,spec,profiles=profiles)
        panels=evidence['panels']
    else:
        chart=spec.get('chart') or {k:v for k,v in spec.items() if k not in
            {'question','size_mm','profiles','archetype','claim','output'}}
        if not chart.get('intent'):
            blockers.append('Declare an expression intent; a blank task must not select arbitrary templates.')
        name=spec.get('source') or (next(iter(data)) if len(data)==1 else None)
        if name not in data:
            raise ValueError('Select a known source for this single-chart task')
        charts=[(name,chart)]
        evidence=None
        panels={'main':{'source':name,'question':spec.get('question',''),
                        'role':'primary','chart':chart}}
        profiles=_profiles(data,spec,charts)
    decisions={key:plan_chart_resources(
        selected_panel_data(data[p['source']],p['source_positions']) if 'source_positions' in p else data[p['source']],
        p['chart'], backend=backend or p['chart'].get('backend'), sources=data, profile=profiles[p['source']])
        for key,p in panels.items()} if not blockers else {}
    if evidence:
        for key,decision in decisions.items():
            panels[key]['decision']=decision
        blockers.extend(evidence['blockers'])
    else:
        for decision in decisions.values():
            blockers.extend(decision['blockers'])
    backends={decision.get('backend') for decision in decisions.values() if decision.get('backend')}
    if len(backends)>1:
        blockers.append('One exported figure needs one rendering backend; resolve mixed Python/R panels.')
    for panel_id,decision in decisions.items():
        panel=panels[panel_id]; chart=panel['chart']; profile=profiles[panel['source']]
        if backend and chart.get('backend') not in {None,backend}:
            blockers.append(f'{panel_id}: chart backend conflicts with the figure backend.')
        identifiers=[c for c,m in profile['columns'].items() if m['type']=='identifier' and not m['type_is_heuristic']]
        quantities=measurement_fields(chart)
        wrongly_measured=sorted(quantities & set(identifiers))
        if wrongly_measured:
            blockers.append(f'{panel_id}: declared identifiers are not measurement fields: '+', '.join(wrongly_measured))
        decision['profile_context']={'source':panel['source'],
            'declared_identifiers':identifiers,
            'measurement_profiles':{c:profile['columns'][c] for c in quantities if c in profile['columns']},
            'groups':profile['group_summary'], 'pair_summary':profile.get('pair_summary'),
            'heuristic_suggestions':profile['suggestions'],
            'boundary':'Use declared identities and observed missingness/distribution; heuristic profiler suggestions never establish a study design or statistical estimator.'}
    adaptations=[]
    for panel,decision in decisions.items():
        chosen=decision.get('recommended')
        if chosen and chosen['resources']['status']!='implementation_found':
            adaptations.append({'panel':panel,'construction':chosen['construction'],
                'resource_status':chosen['resources']['status'],
                'unimplemented_concepts':chosen['resources']['unimplemented_concepts'],
                'unimplemented_symbols':chosen['resources'].get('unimplemented_symbols',[])})
    field_map={key:{'source':p['source'],
        'selection':{**p['selection_provenance'], 'source_positions':p['source_positions'],
                     'selected_data_sha256':p['selected_data_sha256']} if 'selection_provenance' in p else None,
        'roles':{k:p['chart'][k] for k in FIELD_ROLES if p['chart'].get(k)},
        'values':p['chart'].get('values',[]),
        'dimensions':p['chart'].get('dimensions',[]),
        'metadata_source':p['chart'].get('metadata_source'),
        'annotations':p['chart'].get('annotations',[]),
        'metadata_mapping':{'source':p['chart']['metadata_source'], 'sample_id':p['chart'].get('sample_id'),
                            'annotations':p['chart'].get('annotations',[])} if p['chart'].get('metadata_source') else None,
        'question':p.get('question'), 'role':p.get('role'),
        'unique_inference':p.get('unique_inference')}
        for key,p in panels.items()}
    uses=[{'source':'SciPilot','operation':'executed',
        'implementation':'scripts/profile_data.py:profile_data',
        'result':'profiles'}]
    if decisions:
        uses.append({'source':'nature-figure','operation':'executed_adapted_contract',
         'implementation':'scripts/evidence_tools.py:plan_evidence' if evidence else 'scripts/chart_plan.py:plan_chart',
         'result':'evidence' if evidence else 'decisions'})
    # Retrieval evidence is deliberately separate from code execution evidence.
    retrieved={}
    for decision in decisions.values():
        for candidate in decision['candidates']:
            for resource in candidate['resources']['source_routes']:
                retrieved[(resource['source'],resource['path'])]=resource
    uses.extend({'source':source,'operation':'retrieved_not_executed','path':path}
                for source,path in retrieved)
    return {'status':'needs_resolution' if blockers else 'adaptation_required' if adaptations else 'prepared',
        'question':spec.get('question'),'claim':spec.get('claim'),
        'backend':backend or next(iter(backends),None),
        'archetype':spec.get('archetype','quantitative grid'), 'size_mm':size,
        'sources':{name:{'rows':len(table),'columns':list(table.columns),'sha256':data_digest(table)}
                   for name,table in data.items()},
        'profiles':profiles,'field_mapping':field_map,'evidence':evidence,'decisions':decisions,
        'implementation_adaptations':adaptations,'source_use':uses,
        'blockers':list(dict.fromkeys(blockers)),
        'warnings':list(dict.fromkeys((evidence or {}).get('warnings',[])+
                         [w for decision in decisions.values() for w in decision['warnings']])),
        'next_action':'Resolve blockers before rendering.' if blockers else
            'Implement the declared missing construction before claiming executable coverage.' if adaptations else
            'Read selected implementation and reference, design the final-size layout, then render and review.',
        'boundary':'Prepared inputs and decisions; no plot, unrequested inference, independent review or journal-quality certification was produced.'}


def _json_safe(value):
    if isinstance(value,dict): return {str(k):_json_safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [_json_safe(v) for v in value]
    if hasattr(value,'tolist'): return _json_safe(value.tolist())
    if hasattr(value,'item'): return _json_safe(value.item())
    if isinstance(value,float) and not math.isfinite(value): return None
    return value


def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',action='append',required=True,help='CSV/TSV/XLSX or explicit scalar_field NetCDF, optionally NAME=path; repeat for multiple sources')
    parser.add_argument('--spec',required=True,help='Short scientific question and chart/evidence JSON')
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    tables={}
    for arg in args.data:
        name,path=arg.split('=',1) if '=' in arg else ('data',arg)
        if name in tables:parser.error('Duplicate source name: '+name)
        tables[name]=path
    result=prepare_job(tables,json.loads(Path(args.spec).read_text(encoding='utf-8')))
    target=Path(args.out);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(_json_safe(result),ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'out':str(target),'blockers':result['blockers']},ensure_ascii=False))
    return 2 if result['status']=='needs_resolution' else 0


if __name__=='__main__':raise SystemExit(main())
