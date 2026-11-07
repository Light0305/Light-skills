"""Complete tasks for data-aware selection, measured layout and revision review.

Observed built-in data and literal paper results only. Layout comparisons use
identical marks; controlled failures are recorded separately from final figures.
"""
from pathlib import Path
import argparse
import json
import shutil
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--stage', choices=['inputs','python','r','all'], default='all')
parser.add_argument('--out', type=Path, default=ROOT/'artifacts/v0.6-decision-layout-review/tasks')
parser.add_argument('--skill-root', type=Path, default=ROOT/'skills/light-chart')
parser.add_argument('--only', choices=['paired','matrix','reference','growth'], help='One Python task for an isolated package/path check')
args = parser.parse_args()
PKG, OUT = args.skill_root.resolve(), args.out.resolve()
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(PKG/'scripts'))
from editorial import figure_style, raw_groups, scientific_heatmap
from composition import compose, label_line_ends
from project_style import role, colors_for
from research_panels import paired_changes, joint_density
from publication import save_figure, write_json
from library import plan
from chart_plan import plan_chart
from review_tools import compare_revisions
from r_runtime import run_r


def decision(data, spec, name):
    write_json(OUT/(name+'.spec.json'), spec)
    result = plan(data, spec)
    write_json(OUT/(name+'.plan.json'), result)
    if result['status'] != 'ready':
        raise ValueError(str(result['blockers']))
    return result


def export(composition, name, data, caption, *, fit=True, axes=None, allow_failure=False):
    if fit:
        composition.fit()
    selected = list(composition.axes.values()) if axes is None else axes
    report = save_figure(composition.figure, OUT/name, source_data=data,
        axes=selected, alignment_options={'row_groups':[[a.get_label() for a in selected]],'column_groups':[]}, dpi=350)
    write_json(OUT/(name+'.geometry.json'), getattr(composition.figure,'_light_chart_composition',{}))
    (OUT/(name+'.caption.md')).write_text(caption+'\n', encoding='utf-8')
    plt.close(composition.figure)
    print(name,report['automated_status'],len(report['mark_issues']))
    if report['automated_status'] in {'FAIL','NOT_AUDITABLE'} and not allow_failure:
        raise ValueError(str(report['failures']))
    return report


def paired():
    d = pd.read_csv(OUT/'sleep.csv').rename(columns={'ID':'id','group':'drug','extra':'hours'})
    d['drug'] = d.drug.map({1:'Drug 1',2:'Drug 2'})
    d = d.sample(frac=1,random_state=21).reset_index(drop=True)
    p = decision(d,{'intent':'change','unit':'id','condition':'drug','y':'hours',
        'order':['Drug 1','Drug 2'],'backend':'python'},'T01_paired')
    assert p['recommended']['construction'] == 'paired-change'
    wide = paired_changes(d,id='id',condition='drug',value='hours',order=['Drug 1','Drug 2'])
    assert len(wide) == 10 and len(d) == 20
    wide.to_csv(OUT/'T01_matched_values.csv')
    c = compose((132,84),[['paired','change']],width_ratios=[1.35,1],
        panels={'paired':{'role':'primary','min_plot_mm':[38,40]},
                'change':{'role':'within-unit differences','min_plot_mm':[26,40]}},gap_mm=6)
    ax, change = c.axes.values()
    for _, row in wide.iterrows():
        ax.plot([0,1],row[['Drug 1','Drug 2']],color=role('baseline'),lw=.75,alpha=.7)
    for i,name in enumerate(['Drug 1','Drug 2']):
        ax.scatter(np.full(10,i),wide[name],s=14,color=role('baseline') if i==0 else role('primary'),
            label=name,edgecolor='white',linewidth=.35,zorder=4)
    ax.set(xlim=(-.2,1.2),xticks=[0,1],xticklabels=['Drug 1','Drug 2'],
        ylabel='Extra sleep (h)',title='Matched observations')
    raw_groups(change,[wide.change.to_numpy()],['Drug 2 − Drug 1'],[role('primary')],point_size=14)
    change.axhline(0,color=role('muted'),ls='--',lw=.6,zorder=0)
    change.set(ylabel='Within-person difference (h)',title='Individual changes')
    c.fit();c.labels()
    export(c,'T01_paired',d,
        'Observed datasets::sleep records: 10 people measured under both drug conditions; all 20 records retained, shuffled then matched by ID. Extra sleep is measured in hours. Right: each drug-2 minus drug-1 difference, box median/quartiles and 1.5-IQR whiskers. No p value, interval estimate or causal claim is added.',fit=False)
    # Same field shapes, different semantics: unresolved duplicates and summaries
    # must not be passed on as usable paired data.
    missing = d.iloc[:-1]
    blocked = plan_chart(missing,p['spec'])
    resolved = plan_chart(missing,{**p['spec'],'missing':'complete_cases'})
    summary = plan_chart(pd.DataFrame({'drug':['Drug 1','Drug 2'],'hours':[.75,2.33]}),
        {'intent':'compare','group':'drug','y':'hours','data_level':'summary'})
    assert blocked['status']=='needs_resolution' and resolved['diagnostics']['used_units']==9
    assert summary['recommended']['construction']=='estimate-interval'
    write_json(OUT/'T01_boundary_checks.json',{'missing_pair':blocked,'explicit_complete_pairs':resolved,'summary_only':summary})


def matrix():
    source = json.loads((PKG/'assets/examples/rnagenscape.json').read_text(encoding='utf-8'))
    shutil.copy2(PKG/'assets/examples/rnagenscape.json',OUT/'rnagenscape.json')
    columns = ['OV +','OV −','ZF +','ZF −','RB +','RB −']
    domain = ['openvaccine','zebrafish','ribosome']
    delta = np.stack([source[f'results_{s}_delta_{v}'] for s in domain for v in ['pos','neg']],axis=1)
    pct = np.stack([source[f'results_{s}_pct_{v}'] for s in domain for v in ['pos','neg']],axis=1)
    methods = source['methods']
    d = pd.DataFrame(np.c_[delta,pct],columns=['change_'+s for s in columns]+['pct_'+s for s in columns])
    d.insert(0,'method',methods);d.to_csv(OUT/'T02_all_reported_values.csv',index=False)
    p = decision(d,{'intent':'matrix','unit':'method','values':list(d.columns[1:]),
        'data_level':'summary','backend':'python','value_groups':{
          'property-change':{'columns':list(d.columns[1:7]),'limits':[-3,3],'unit':'source property units unspecified'},
          'success-rate':{'columns':list(d.columns[7:]),'limits':[0,100],'unit':'%'}}},'T02_matrix')
    assert p['recommended']['construction']=='multi-scale-heatmaps'
    reports = []
    for balanced, name in [(False,'T02_equal_slots'),(True,'T02_matrix')]:
        c = compose((180,114),[['change','fraction'],['scale-change','scale-fraction']],
            height_ratios=[1,.10],balance_columns=balanced,gap_mm=5,
            panels={k:{'min_plot_mm':[30,2]} for k in ['scale-change','scale-fraction']})
        for key, values, limits, center, title, scale in [
            ('change',delta,[-3,3],0,'Median property change','scale-change'),
            ('fraction',pct,[0,100],None,'Success rate (%)','scale-fraction')]:
            ax=c.axes[key]
            image=scientific_heatmap(ax,values,methods,columns,limits=limits,center=center,
                annotate=False,row_breaks=[4,8,12],col_breaks=[2,4],highlight_row=12)
            ax.xaxis.tick_bottom();ax.set_title(title,pad=6,fontsize=8.5)
            if key=='fraction':ax.set_yticklabels([])
            bar=c.figure.colorbar(image,cax=c.axes[scale],orientation='horizontal',
                ticks=[-3,0,3] if center is not None else [0,50,100])
            bar.outline.set_visible(False)
            # All 156 exact source numbers are delivered separately. Selected
            # key-method values locate the comparison without filling every cell.
            for j,value in enumerate(values[-1]):
                rgba=image.cmap(image.norm(value));rgb=np.array(rgba[:3])
                linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
                lum=float(linear@ [.2126,.7152,.0722])
                color='white' if 1.05/(lum+.05)>(lum+.05)/.05 else 'black'
                ax.text(j,12,f'{value:.2f}' if center is not None else f'{value:.1f}',ha='center',va='center',fontsize=6.5,color=color)
        c.fit()
        # Letter only the evidence panels, not colorbars.
        for key,letter in [('change','a'),('fraction','b')]:
            slot=c.slots[key];c.figure.text(slot[0]/180,1-slot[1]/114,letter,fontsize=9,fontweight='bold',va='bottom')
        report=export(c,name,d,'Literal RNAGenScape paper results from the bundled figures4papers snapshot (CC BY-NC 4.0): all 13 methods, six tasks and both quantities retained, 156 reported numbers. OV=OpenVaccine; ZF=Zebrafish; RB=Ribosome; +/− specify target direction, not significance. Left uses one zero-centered −3 to 3 display range; right uses one 0–100% scale. Property-change units/normalization are not fully specified by the source plotting script: compare methods within tasks, without inferring cross-task effect magnitudes. These are reported aggregates with no invented replicates or uncertainty. White gaps separate method families/tasks; exact data and original provenance are supplied.',fit=False,axes=[c.axes['change'],c.axes['fraction']])
        reports.append(report)
    comp=compare_revisions(*reports,required_panels=['change','fraction','scale-change','scale-fraction'])
    assert comp['status']=='no_evidence_regression',comp
    rect=reports[-1]['composition']['plot_rectangles_mm']
    assert abs(rect['change'][2]-rect['fraction'][2])<.2
    write_json(OUT/'T02_comparison.json',comp)


def reference():
    d=pd.read_csv(OUT/'faithful.csv')
    shutil.copy2(PKG/'assets/examples/visual-review/04-joint-distribution.png',OUT/'T03_reference.png')
    p=decision(d,{'intent':'association','x':'eruptions','y':'waiting','backend':'python',
        'reference':{'required_elements':['hexbin','marginals','count-colorbar'],
            'adaptation':'Reference normalized axes and threshold lines do not apply to observed minutes; keep construction, replace labels/units and use sequential count colors.'}},'T03_reference')
    assert p['recommended']['construction']=='joint-density-marginals'
    c=compose((142,132),[['top','.','.'],['joint','count','right']],
        width_ratios=[1,.11,.2],height_ratios=[.18,1],gap_mm=4,
        panels={'joint':{'plot_aspect':1,'min_plot_mm':[65,65]},
                'top':{'share_x_with':'joint','min_plot_mm':[65,8]},
                'right':{'share_y_with':'joint','min_plot_mm':[8,65]},
                'count':{'share_y_with':'joint','min_plot_mm':[1,65]}})
    ax,top,right,cb=[c.axes[k] for k in ['joint','top','right','count']]
    r=joint_density(ax,top,right,d.eruptions,d.waiting,cax=cb,gridsize=24,limits=[1.5,5.5,40,100])
    ax.set(xlabel='Eruption duration (min)',ylabel='Waiting time (min)',xticks=[2,3,4,5],yticks=[40,60,80,100])
    top.set_yticks([0,20]);right.set_xticks([0,20]);cb.set_ylabel('');cb.set_title('Count',fontsize=7,pad=6)
    # The colorbar has its own slot between the joint and right marginal.
    c.fit()
    assert r['hexbin_total']==r['x_hist_total']==r['y_hist_total']==len(d)==272
    export(c,'T03_reference',d,'Observed datasets::faithful: all 272 eruption/waiting pairs, with both quantities in minutes. Layout reference is the Light-Science synthetic joint-distribution example; the real faithful observations use hexagonal counts instead of the reference scatter, with a count colorbar and matched marginal histograms. The synthetic reference values are not used as observations. All three count totals equal 272; no fitted distribution or regression is added.',fit=False,axes=[ax])
    write_json(OUT/'T03_counts.json',{k:v for k,v in r.items() if k not in {'mappable','x_edges','y_edges'}})


def growth():
    d=pd.read_csv(OUT/'Orange.csv')
    spec={'intent':'change','unit':'Tree','condition':'age','y':'circumference',
        'order':sorted(d.age.unique().tolist()),'ordered':True,'backend':'python'}
    p=decision(d,spec,'T05_growth')
    assert p['recommended']['construction']=='within-unit-trajectories'
    colors=colors_for(['Tree '+str(i) for i in range(1,6)])
    reports=[]
    for final,name in [(False,'T05_first_layout'),(True,'T05_growth')]:
        c=compose((164,94),[['growth','growth','change']],width_ratios=[1,1,1],gap_mm=7,
            panels={'growth':{'role':'primary','min_plot_mm':[65,38]},'change':{'role':'between-unit heterogeneity','min_plot_mm':[25,38]}})
        ax,change=c.axes.values()
        changes=[]
        for i,(tree,z) in enumerate(d.groupby('Tree',sort=True)):
            z=z.sort_values('age')
            ax.plot(z.age,z.circumference,label='Tree '+str(tree),color=colors[i],
                marker=['o','s','D','^','v'][i],markersize=3,lw=1)
            changes.append(float(z.circumference.iloc[-1]-z.circumference.iloc[0]))
        ax.set(xlabel='Tree age (days)',ylabel='Trunk circumference (mm)',title='Within-tree growth',
            xticks=[118,484,1004,1582])
        if final:
            label_line_ends(ax,minimum_gap_pt=12,fontsize=7)
        else:
            ax.legend(loc='center',fontsize=7,handlelength=1,columnspacing=.8)
        change.scatter(changes,np.arange(5),c=colors,s=20,edgecolor='white',linewidth=.4)
        change.set(yticks=np.arange(5),yticklabels=['Tree '+str(i) for i in range(1,6)],
            xlabel='Net growth (mm)',title='118 → 1582 days',ylim=(4.5,-.5),xticks=[100,150,200])
        change.spines['left'].set_visible(False);change.tick_params(axis='y',length=0)
        c.fit();c.labels()
        reports.append(export(c,name,d,'Observed datasets::Orange: five trees, seven observations each, all 35 records retained. Lines connect measurements from the same tree at their actual unequal ages in days; circumference and final-minus-first growth are in millimetres. The right panel has one difference per tree, not 35 independent replicates. No fitted growth model, error band or significance is introduced. Colors and marker shapes identify trees consistently.',fit=False,allow_failure=not final))
    comp=compare_revisions(*reports,required_panels=['growth','change'])
    assert comp['status']=='no_evidence_regression',comp
    assert any(x['code']=='legend_over_data' for x in reports[0]['mark_issues'])
    assert not reports[1]['mark_issues'],reports[1]['mark_issues']
    write_json(OUT/'T05_comparison.json',comp)


def inputs():
    project=json.loads((PKG/'assets/project-style.json').read_text(encoding='utf-8'))
    mappings={'Standard':'#226D8D','Test':'#CA7259',**dict(zip(['Tree '+str(i) for i in range(1,6)],
        ['#226D8D','#CA7259','#288C83','#7B6A9D','#9B823F']))}
    project['groups']={k:{'color':v} for k,v in mappings.items()}
    write_json(OUT/'project-style.json',project)
    r=run_r(Path(__file__).with_suffix('.R'),['data',PKG,OUT],timeout=90,log=OUT/'R-inputs.json')
    assert r['status']=='PASS',r
    d=pd.read_csv(OUT/'veteran.csv')
    decision(d,{'intent':'survival','unit':'id','time':'time','event':'status','group':'group',
        'backend':'r','design':'right-censor'},'T04_survival')


def native():
    r=run_r(Path(__file__).with_suffix('.R'),['plot',PKG,OUT],timeout=150,log=OUT/'R-runtime.json')
    assert r['status']=='PASS',r
    (OUT/'T04_survival.caption.md').write_text(
        'Observed survival::veteran data: 137 subjects; one event/censor record per subject, status 1=event and 0=censor. Native R Kaplan–Meier curves, stepwise 95% log-log Greenwood intervals, censor marks and risk counts use the same records. Risk counts are independently checked at every tick. Descriptive, unadjusted comparison; no hazard ratio, p value or causal treatment effect is inferred.\n',encoding='utf-8')


if args.stage in {'inputs','all'}:inputs()
if args.stage in {'python','all'}:
    with figure_style(project=OUT/'project-style.json'):
        for task in [paired,matrix,reference,growth]:
            if args.only is None or args.only==task.__name__:task()
if args.stage in {'r','all'}:native()
