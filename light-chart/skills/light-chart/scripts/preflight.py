"""Source preflight with explicitly declared helper scope and requested formats.

Wraps nature-figure's retained validator. Findings are static clues; actual
statistics, data mappings, PNG/PDF rendering and design require separate review.
"""
from __future__ import annotations
import argparse
import ast
from dataclasses import asdict
import json
from pathlib import Path
import re
import validate_figure as engine


def preflight(path, *, support=(), formats=('pdf','svg','png')):
    path=Path(path).resolve()
    backend=engine.detect_backend(path,'auto')
    paths=list(dict.fromkeys([path,*[Path(p).resolve() for p in support]]))
    if not set(formats) <= {'pdf','svg','png','tif','tiff','eps'} or not formats:
        raise ValueError('Declare at least one supported export format')
    texts=[];rows=[]
    for p in paths:
        if engine.detect_backend(p,'auto')!=backend:
            raise ValueError('Support files must use the selected plotting language')
        s=p.read_text(encoding='utf-8-sig');texts.append(s)
        syntax=engine.check_syntax(s,backend)
        rows.append(engine.finding('SOURCE-SYNTAX',syntax.level,f'{p.name}: {syntax.message}',syntax.evidence))
    combined='\n\n'.join(texts)
    for check in engine.CHECKS:
        if check is engine.check_syntax: continue
        row=check(combined,backend)
        # Source absence is not proof the runtime setting/device is absent.
        if row.check_id in {'FONT-FAMILY','EDITABLE-TEXT','PANEL-ALIGNMENT-GATE'} and row.level=='FAIL':
            row=engine.finding(row.check_id,'WARN',row.message+'; static scope cannot prove runtime behavior',row.evidence)
        if row.check_id=='LEGEND-LABEL-CASE':
            row=engine.finding(row.check_id,'WARN' if row.level=='WARN' else row.level,
                'Preserve canonical scientific/model names; review human labels in context',row.evidence)
        if row.check_id=='EXPORT-VECTOR':
            missing=[]
            if 'pdf' in formats and not re.search(r'\.pdf\b|cairo_pdf\s*\(|[\'"]pdf[\'"]',combined,re.I): missing.append('pdf')
            if 'svg' in formats and not re.search(r'\.svg\b|svglite\s*\(|[\'"]svg[\'"]',combined,re.I): missing.append('svg')
            row=engine.finding('EXPORT-VECTOR','WARN' if missing else 'PASS',
                'Requested vector export not found in static scope' if missing else 'Requested vector formats found or not requested',missing)
        if row.check_id=='EXPORT-RASTER' and not set(formats)&{'png','tif','tiff'}:
            row=engine.finding('EXPORT-RASTER','PASS','Raster export not requested')
        if row.check_id=='PANEL-ALIGNMENT-GATE' and row.level=='WARN' and re.search(r'\bsave_figure(?:_r)?\s*\(',combined):
            row=engine.finding(row.check_id,'WARN','Publication wrapper detected; inspect its included helper and final alignment report before declaring the gate wired')
        rows.append(row)
    if backend=='python':
        # This is a definite invalid interval, unlike style or dependency inference.
        for p,s in zip(paths,texts):
            try: tree=ast.parse(s)
            except SyntaxError: continue
            for node in ast.walk(tree):
                if not isinstance(node,ast.Call): continue
                name=getattr(node.func,'attr',getattr(node.func,'id',''))
                if name!='Normalize': continue
                kws={k.arg:k.value for k in node.keywords}
                try: lo,hi=ast.literal_eval(kws['vmin']),ast.literal_eval(kws['vmax'])
                except (KeyError,ValueError,TypeError): continue
                if isinstance(lo,(int,float)) and isinstance(hi,(int,float)) and lo>=hi:
                    rows.append(engine.finding('COLOR-LIMIT-ORDER','FAIL',f'{p.name}:{node.lineno}: Normalize requires vmin < vmax'))
    summary=engine.summarize(rows)
    return {'source':str(path),'backend':backend,'scope':[str(p) for p in paths],
        'scope_note':'Only explicit files were inspected. No imports executed, no runtime configuration or rendered appearance proven.',
        'requested_formats':list(formats),'ready_to_render':summary['ready'],
        'counts':summary['counts'],'findings':[asdict(row) for row in rows]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('--support',action='append',default=[],type=Path)
    p.add_argument('--formats',nargs='+',default=['pdf','svg','png'])
    p.add_argument('--json-out',type=Path)
    a=p.parse_args()
    try: report=preflight(a.source,support=a.support,formats=a.formats)
    except (OSError,ValueError) as exc: p.error(str(exc))
    s=json.dumps(report,ensure_ascii=False,indent=2)
    if a.json_out:
        a.json_out.parent.mkdir(parents=True,exist_ok=True);a.json_out.write_text(s+'\n',encoding='utf-8')
    else: print(s)
    return 0 if report['ready_to_render'] else 1

if __name__=='__main__':raise SystemExit(main())
