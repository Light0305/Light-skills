"""Paper-value table and explicit analytical field, using the shipped helpers."""
from pathlib import Path
import argparse
import json
import csv
import sys
import numpy as np

PACKAGE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PACKAGE/'scripts'))
from editorial import figure_style,canvas,axes_mm,text_mm
from table_tools import Column,to_latex
from field_tools import grid_field,scalar_field,field_surface
from publication import save_figure


def paper_table(out):
    source=json.loads((Path(__file__).parent/'immunostruct.json').read_text(encoding='utf-8'))
    keys=['data_comparison_IEDB','data_comparison_Cancer']
    methods=list(source[keys[1]]['methods'])
    rows=[]
    for method in methods:
        row={'method':method}
        for prefix,key in zip(['i','c'],keys):
            obj=source[key]
            idx=obj['methods'].index(method) if method in obj['methods'] else None
            for j in range(3):
                row[f'{prefix}{j}']=None if idx is None else obj['mean'][idx][j]
                row[f'{prefix}{j}d']=None if idx is None else f"{obj['mean'][idx][j]:.3f} ± {obj['std'][idx][j]:.3f}"
        rows.append(row)
    columns=[Column('method','Method',.25,align='left')]
    for prefix in ['i','c']:
        for j,label in enumerate(['AUROC ↑','AUPRC ↑','Mean PPVn ↑']):
            columns.append(Column(f'{prefix}{j}',label,.125,better='max',display_key=f'{prefix}{j}d'))
    tex=to_latex(rows,columns,spanners=[('IEDB',1,4),('Cancer',4,7)],rank=True,section_starts=[5,8,9])
    (out/'07_method_comparison.tex').write_text(tex,encoding='utf-8')
    with (out/'07_method_comparison.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (out/'07_table_notes.md').write_text(
      '## Table caption and notes (outside the tabular)\n\n'
      'Method comparison across IEDB and Cancer, using repository-reported values. '
      'Values are mean ± source error. AUROC/AUPRC retain literal std entries; '
      'Mean PPVn errors were already divided by √5 in the source. Replicate definitions are unavailable. '
      'Bold indicates the largest raw mean per column, including exact ties, not statistical significance. '
      'A dash denotes an unreported value. No imputation or hypothesis testing.\n\n'
      'Use \\usepackage{booktabs} and \\input{07_method_comparison.tex} in the manuscript. '
      'The fragment has no float, caption, forced font size or raster output.\n',encoding='utf-8')
    (out/'table_source_and_mapping.json').write_text(json.dumps({'source':'Bundled immunostruct.json, extracted from figures4papers raw_data.py',
      'rows':rows,'missing':'NeoaPred absent in IEDB source; retained as missing, never imputed',
      'ranking':'Raw means, max per column, exact ties retained; no hypothesis testing',
      'error_definition':source['_provenance']['note']},ensure_ascii=False,indent=2),encoding='utf-8')
    return out/'07_method_comparison.tex'


def analytical_field(out):
    # An explicit, nonuniform analytical grid, not experimental observations.
    x=np.r_[np.linspace(-3,-.8,22,endpoint=False),np.linspace(-.8,1.4,43,endpoint=False),np.linspace(1.4,3,17)]
    y=np.linspace(-3,3,61)
    X,Y=np.meshgrid(x,y)
    Z=np.exp(-((X-.9)**2/.6+(Y-.6)**2/.9))-.7*np.exp(-((X+.9)**2/.8+(Y+.5)**2/.7))
    # Declared missing domain, retained in both renderings, not hidden imputation.
    missing=(X<-2.1)&(Y>1.7)
    Z[missing]=np.nan
    field=grid_field(x,y,Z,limits=(-.8,1),center=0)
    with figure_style():
        fig=canvas((180,108))
        text_mm(fig,3,2,'a',fontsize=9,fontweight='bold')
        text_mm(fig,91,2,'b',fontsize=9,fontweight='bold')
        ax=axes_mm(fig,17,11,66,66)
        mesh=scalar_field(ax,field,cmap='RdBu_r',levels=[-.6,-.3,0,.3,.6,.9])
        ax.set(xlabel='x (model units)',ylabel='y (model units)',xlim=(-3,3),ylim=(-3,3))
        ax.set_aspect('equal',adjustable='box')
        ax3=axes_mm(fig,99,11,66,66,projection='3d')
        field_surface(ax3,field,cmap='RdBu_r',box_aspect=(1,1,.65))
        ax3.set(xlabel='x',ylabel='y',zlabel='f(x, y)',zlim=(-.8,1))
        ax3.set_xticks([-3,0,3]);ax3.set_yticks([-2,0,2]);ax3.set_zticks([-.5,0,.5,1])
        ax3.tick_params(labelsize=6,pad=0)
        ax3.xaxis.labelpad=-1;ax3.yaxis.labelpad=-1;ax3.zaxis.labelpad=-1
        cbax=axes_mm(fig,31,92,118,2.5)
        cb=fig.colorbar(mesh,cax=cbax,orientation='horizontal',ticks=[-.8,-.4,0,.4,.8,1])
        cb.outline.set_visible(False)
        cb.set_label('f(x, y)',fontsize=7)
        report=save_figure(fig,out/'08_quantitative_field',dpi=450,axes=[ax,ax3],
          alignment_options={'panel_ids':['a','b'],'row_groups':[['a','b']],
            'column_groups':[]},label_panels=False)
    np.savez_compressed(out/'analytical_field.npz',x=x,y=y,z=Z,missing=missing)
    (out/'field_definitions.json').write_text(json.dumps({'type':'Explicit analytical demonstration, not research observations',
      'formula':'exp(-((x-.9)^2/.6+(y-.6)^2/.9)) - .7*exp(-((x+.9)^2/.8+(y+.5)^2/.7))',
      'grid':[len(y),len(x)],'missing':'x < -2.1 and y > 1.7 is declared unobserved',
      'limits':[-.8,1],'center':0,'smoothing':False,'interpolation':False,'decimation':False},indent=2),encoding='utf-8')
    (out/'08_field_caption.md').write_text(
      '**Analytical demonstration, not experimental data.** a, Coordinate-aware map; '
      'b, the same values rendered as a surface. Both views use the same zero-centered color scale. '
      'Formula: f = exp(-[(x-0.9)^2/0.6 + (y-0.6)^2/0.9]) '
      '- 0.7 exp(-[(x+0.9)^2/0.8 + (y+0.5)^2/0.7]). '
      'The grid has 82 nonuniform x coordinates and 61 y coordinates. '
      'The declared unobserved domain x < -2.1, y > 1.7 appears gray/open; it is not zero or imputed. '
      'No smoothing, interpolation or decimation. Projection partly occludes the valley; use a for quantitative reading.\n',encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('domain-figures'))
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    table=paper_table(a.output)
    print(f'Native LaTeX table: {table}')
    reports=[analytical_field(a.output)]
    if any(r.get('automated_status') in {'FAIL','NOT_AUDITABLE','IN_PROGRESS'} for r in reports):
        raise SystemExit('Inspect failed/unavailable technical checks')
    if any(r.get('automated_status')=='REVIEW_REQUIRED' for r in reports):
        print('Rendering complete; geometry/overlay warnings require actual visual review. See QA reports.')

if __name__=='__main__':main()
