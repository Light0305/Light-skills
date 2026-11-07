"""Complete local tasks against real records, source aggregates and declared fields.

This is deterministic acceptance work, not an independent agent or aesthetic score.
The tasks exercise routed reusable implementations and export their plotted values.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

ROOT=Path(__file__).resolve().parents[2]
PKG=ROOT/'skills/light-chart'
sys.path.insert(0,str(PKG/'scripts'))
from editorial import figure_style,canvas,axes_mm,panel_heading,raw_groups,scientific_heatmap
from project_style import colors_for,role,colormap,current_project
from research_panels import paired_changes,joint_density,image_panel,network_panel
from publication import save_figure,write_json
from field_tools import grid_field,scalar_field,field_surface
from library import route
from table_tools import Column,to_latex,best_cells


def save(fig,out,name,*,axes=None,alignment_options=None,caption='',task='',checks=None):
    report=save_figure(fig,out/name,axes=axes,alignment_options=alignment_options,dpi=350)
    report['task_checks']=checks or {}
    report['design_review']={'status':'pending','basis':'Final PNG/PDF must be viewed; no independent reviewer claimed.'}
    write_json(out/(name+'.qa.json'),report)
    (out/(name+'.caption.md')).write_text(caption+'\n',encoding='utf-8')
    write_json(out/(name+'.route.json'),route(task))
    plt.close(fig)
    if report['automated_status'] in {'FAIL','NOT_AUDITABLE'}:
        raise RuntimeError(name+': '+str(report['failures']))
    return report


def pairs(out):
    data=pd.read_csv(out/'anorexia.csv')
    names={'Cont':'Control','CBT':'CBT','FT':'FT'}
    data['group']=data.Treat.map(names)
    long=data.melt(id_vars=['subject','group'],value_vars=['Prewt','Postwt'],var_name='condition',value_name='weight')
    long['condition']=long.condition.map({'Prewt':'Before','Postwt':'After'})
    # Scramble rows to verify matching never depends on row adjacency.
    long=long.sample(frac=1,random_state=81)
    wide=paired_changes(long,id='subject',condition='condition',value='weight',order=['Before','After'])
    wide=wide.join(data.set_index('subject')['group']);wide.to_csv(out/'T01_paired_values.csv')
    assert len(wide)==len(data)==72
    np.testing.assert_allclose(wide['change'],wide['After']-wide['Before'])
    groups=['Control','CBT','FT']; colors=colors_for(groups)
    fig=canvas((180,90)); axes=[]
    for j,(g,c) in enumerate(zip(groups,colors)):
        ax=axes_mm(fig,16+j*37,14,27,58,label='pair-'+g);axes.append(ax)
        z=wide[wide.group==g]
        for _,row in z.iterrows():ax.plot([0,1],[row.Before,row.After],color=c,alpha=.35,lw=.65)
        for i,col in enumerate(['Before','After']):
            ax.scatter(np.full(len(z),i),z[col],s=9,color=c,edgecolors='white',linewidths=.2,zorder=3)
        ax.set(xticks=[0,1],xticklabels=['Before','After'],xlim=(-.25,1.25),ylim=(65,110),yticks=[70,90,110])
        ax.set_title(f'{g} (n={len(z)})',fontsize=7.5,pad=7)
        if j==0:ax.set_ylabel('Weight (lb)')
        else:ax.tick_params(labelleft=False)
    ax=axes_mm(fig,139,14,35,58,label='change');axes.append(ax)
    raw_groups(ax,[wide.loc[wide.group==g,'change'].to_numpy() for g in groups],groups,colors,point_size=8)
    ax.axhline(0,color=role('muted'),lw=.6,ls='--',zorder=0)
    ax.set_ylabel('Weight change (lb)');ax.set_ylim(-15,25)
    ax.tick_params(axis='x',labelrotation=35)
    panel_heading(fig,'a','Paired observations',3,2);panel_heading(fig,'b','Change',129,2)
    save(fig,out,'T01_paired',axes=axes,
      alignment_options={'panel_ids':[a.get_label() for a in axes],'row_groups':[[a.get_label() for a in axes[:3]]],'column_groups':[]},
      task='配对记录和变化分布',checks={'subjects':72,'records':144,'id_matched':True},
      caption='MASS::anorexia: all 72 subjects and both weight measurements retained. Each line joins the same subject; right panel shows individual post-minus-pre changes, box medians/quartiles and 1.5-IQR whiskers. Treatment groups are descriptive here; no significance, adjusted effect or causal claim is inferred. Weight unit: pounds. No exclusions.')


def density(out):
    d=pd.read_csv(out/'faithful.csv');fig=canvas((124,110))
    joint=axes_mm(fig,17,29,72,65,label='joint');top=axes_mm(fig,17,7,72,17,label='top')
    right=axes_mm(fig,94,29,19,65,label='right');cax=axes_mm(fig,116,29,2,65,label='count')
    r=joint_density(joint,top,right,d.eruptions,d.waiting,cax=cax,gridsize=27,limits=[1.5,5.5,40,100])
    assert r['hexbin_total']==r['x_hist_total']==r['y_hist_total']==len(d)==272
    joint.set(xlabel='Eruption duration (min)',ylabel='Waiting time (min)')
    top.tick_params(axis='y',labelsize=6.5);right.tick_params(axis='x',labelsize=6.5)
    # A numeric colorbar with no separate title avoids a second competing margin.
    cax.set_ylabel('');cax.set_title('Count',fontsize=7,pad=4);cax.tick_params(labelsize=6.5)
    save(fig,out,'T02_joint_density',axes=[joint],task='联合密度和边缘分布',
      checks={k:v for k,v in r.items() if k not in {'mappable','x_edges','y_edges'}},
      caption='datasets::faithful: all 272 observed Old Faithful eruption/waiting pairs. Hexagons encode counts, with a shared count colorbar; marginals use exactly the same records. Color is not a fitted probability density. No regression, p value or causal relationship is inferred. Both axes are minutes.')


def network(out):
    d=pd.read_csv(out/'state_x77.csv',index_col=0);corr=d.corr();labels=list(d.columns)
    short=['Population','Income','Illiteracy','Life exp.','Murder','HS grad.','Frost','Area']
    theta=np.linspace(0,2*np.pi,8,endpoint=False)+np.pi/2;pos=np.c_[np.cos(theta),np.sin(theta)]
    edges=[];edge_colors=[];raw=[]
    for i in range(8):
        for j in range(i+1,8):
            r=float(corr.iloc[i,j])
            if abs(r)>=.6:
                edges.append((short[i],short[j],abs(r)));edge_colors.append(role('up') if r>0 else role('down'))
                raw.append({'source':labels[i],'target':labels[j],'r':r,'weight':abs(r)})
    fig=canvas((180,100));ax=axes_mm(fig,3,14,76,73,label='network');hm=axes_mm(fig,106,14,55,55,label='matrix')
    meta=network_panel(ax,short,pos,edges,edge_colors=edge_colors)
    ax.legend(handles=[Line2D([],[],color=role('up'),label='Positive'),Line2D([],[],color=role('down'),label='Negative')],
              loc='lower center',bbox_to_anchor=(.5,-.08),ncols=2,fontsize=7)
    im=scientific_heatmap(hm,corr.to_numpy(),short,short,limits=[-1,1],center=0,annotate=False)
    hm.xaxis.tick_bottom();hm.tick_params(axis='x',labelrotation=90);hm.tick_params(labelsize=7)
    cb=axes_mm(fig,164,14,2,55);fig.colorbar(im,cax=cb,label='Pearson r',ticks=[-1,-.5,0,.5,1])
    panel_heading(fig,'a','|r| ≥ 0.6',3,2);panel_heading(fig,'b','All correlations',104,2)
    corr.to_csv(out/'T05_correlations.csv');pd.DataFrame(raw).to_csv(out/'T05_edges.csv',index=False)
    assert meta['nodes']==8 and len(d)==50
    # The two panels have different physical roles, not comparable square cells.
    save(fig,out,'T05_network',axes=[hm],task='加权网络和矩阵',checks={**meta,'observations':50,'threshold':.6},
      caption='datasets::state.x77: Pearson correlations across all 50 states and eight historical variables. Left: undirected graph retaining |r| ≥ 0.6; line width encodes |r| and color its sign. Circular node positions are a declared layout, not geographic coordinates or observations. Right: the full correlation matrix, including weaker links. This describes aggregate associations and does not imply causality or individual-level effects.')


def images(out):
    from skimage.data import coins
    a=coins();np.save(out/'coins_original.npy',a)
    fig=canvas((180,104));axes=[];metas=[]
    crops=[None,(20,160,20,170),(120,260,185,335)]
    for j,crop in enumerate(crops):
        ax=axes_mm(fig,4+j*59,13,54,56,label='image'+str(j));axes.append(ax)
        metas.append(image_panel(ax,a,pixel_size=1,unit='px',limits=[0,255],scale_bar=50,crop=crop))
        panel_heading(fig,'abc'[j],['Original','Crop 1','Crop 2'][j],4+j*59,2)
    ax=axes_mm(fig,17,75,155,18,label='profile')
    row=140; ax.plot(np.arange(a.shape[1]),a[row],color=role('primary'),lw=.7)
    ax.set(xlabel='Column (px)',ylabel='Intensity',ylim=(0,255),yticks=[0,255])
    # Show the exact source row in the overview without modifying source pixels.
    axes[0].axhline(row,color='#E69F00',linewidth=.65)
    np.savetxt(out/'T07_intensity_profile.csv',np.c_[np.arange(a.shape[1]),a[row]],delimiter=',',header='column_px,intensity',comments='')
    save(fig,out,'T07_image_plate',axes=[ax],task='图像板 定标 裁剪 比例尺',
      checks={'source':'skimage.data.coins','original_sha256':hashlib.sha256(a.tobytes()).hexdigest(),'images':metas,'profile_row':row},
      caption='Technical image-handling task using the observed skimage.data.coins photograph, not biological experimental evidence. The original and two declared crops use identical 0–255 display limits and nearest-pixel rendering. Bars are 50 pixels; no physical calibration is known or invented. The orange overview line marks original row 140, whose complete intensity profile appears below. No denoising, pixel synthesis or cell counting is performed.')


def field(out):
    x=np.sign(np.linspace(-1,1,73))*np.abs(np.linspace(-1,1,73))**1.4*3
    y=np.sign(np.linspace(-1,1,55))*np.abs(np.linspace(-1,1,55))**1.2*2.4
    X,Y=np.meshgrid(x,y);z=np.exp(-((X+.8)**2+(Y-.5)**2))-.75*np.exp(-((X-1.1)**2+(Y+.6)**2)/.7)
    z[(X>2)&(Y>1.3)]=np.nan
    f=grid_field(x,y,z,limits=[-1,1],center=0)
    fig=canvas((180,100));ax=axes_mm(fig,17,14,64,65,label='map')
    surf=axes_mm(fig,100,10,65,72,projection='3d',label='surface')
    im=scalar_field(ax,f);field_surface(surf,f,elev=30,azim=-62)
    ax.set(xlabel='x (a.u.)',ylabel='y (a.u.)')
    surf.set(xlabel='x',ylabel='y',zlabel='Field',zlim=(-1,1),xticks=[-3,0,3],yticks=[-2,0,2],zticks=[-1,0,1])
    surf.tick_params(labelsize=6.5,pad=0)
    cb=axes_mm(fig,85,14,2,65);fig.colorbar(im,cax=cb,label='Field (a.u.)')
    panel_heading(fig,'a','Coordinate map',3,2);panel_heading(fig,'b','Same values',100,2)
    np.savez(out/'T06_field_values.npz',x=x,y=y,z=z)
    np.testing.assert_equal(f.z,z)
    save(fig,out,'T06_field',axes=[ax],task='非均匀网格连续场 三维曲面',checks={'shape':list(z.shape),'missing':int(np.isnan(z).sum()),'geometry_unchanged':True},
      caption='Declared analytical acceptance field, not measured research data: exp(-((x+0.8)^2+(y-0.5)^2)) - 0.75 exp(-((x-1.1)^2+(y+0.6)^2)/0.7), evaluated on a nonuniform 73×55 grid. The x>2,y>1.3 corner is explicitly missing. Map and surface share limits [-1,1], center zero and the same project colors. No fitting, imputation or silent vertex decimation. The map retains values obscured in the 3D projection.')


def reported(out):
    p=PKG/'assets/examples/benchmark.py';spec=importlib.util.spec_from_file_location('source_benchmark',p)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    for name,builder,source in [('T08_method_comparison',mod.method_comparison,'immunostruct.json'),
                              ('T09_ablation',mod.ablation,'immunostruct.json')]:
        data=mod.read(source);fig,axes,alignment=builder(data)
        save(fig,out,name,axes=axes,alignment_options=alignment,task='方法比较 消融 多指标',
          checks={'source':data['_provenance'],'values':'literal source arrays; no new tests or CIs'},
          caption='Source-report acceptance task using the bundled figures4papers ImmunoStruct aggregates (CC BY-NC 4.0). All source variants/methods and source error arrays are retained. These are reported aggregates, not independently validated experiments or reconstructed raw replicates. Mean PPVn source errors were already divided by sqrt(5); no reinterpretation as a CI. Cancer AUROC has an exact 0.771 tie; highlight is navigation, not proof of superiority. Component/sensitivity mapping follows the documented source interpretation and should be confirmed before research reuse.')
    table=mod.read('immunostruct.json')['data_comparison_Cancer']
    rows=[{'method':m,**{f'm{i}':v for i,v in enumerate(table['mean'][j])}} for j,m in enumerate(table['methods'])]
    cols=[Column('method','Method',.4,align='left')]+[Column(f'm{i}',label,.2,better='max') for i,label in enumerate(table['metrics'])]
    tex=to_latex(rows,cols,rank=True)
    (out/'T10_results_table.tex').write_text(tex,encoding='utf-8');pd.DataFrame(rows).to_csv(out/'T10_results_table.csv',index=False)
    chosen=best_cells(rows,cols)
    ties=[j for j,r in enumerate(rows) if r['m0']==.771]
    assert len(ties)==2 and all((j,1) in chosen for j in ties)
    write_json(out/'T10_results_table.checks.json',{'format':'native LaTeX fragment, no raster table','rows':len(rows),'exact_ties_retained':True,'compiled_this_run':False})


def main():
    tasks={f.__name__:f for f in (pairs,density,network,images,field,reported)}
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--project',type=Path,required=True)
    p.add_argument('--only',nargs='+',choices=list(tasks),help='Run selected complete tasks after a local correction')
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    with figure_style(project=args.project):
        for task in [tasks[k] for k in (args.only or tasks)]:
            task(args.out);print(task.__name__,'complete',flush=True)


if __name__=='__main__':main()
