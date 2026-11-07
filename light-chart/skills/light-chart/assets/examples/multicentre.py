"""Real four-file UCI task: source -> diagnostics -> alternatives -> final exports.

Download is explicit (--download), with raw hashes and the upstream corruption
warning retained. This is descriptive reanalysis, not clinical advice or a new
independent validation study. Captions contain definitions and limitations.
"""
from pathlib import Path
import argparse,copy,hashlib,io,json,sys,urllib.request,zipfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ROOT=Path(__file__).resolve().parents[2]
DEFAULT=ROOT if (ROOT/'SKILL.md').is_file() else ROOT/'skills/light-chart'
parser=argparse.ArgumentParser();parser.add_argument('--skill-root',type=Path,default=DEFAULT)
parser.add_argument('--out',type=Path,default=Path.cwd()/'artifacts/v0.8-multicentre')
parser.add_argument('--download',action='store_true')
parser.add_argument('--palette',choices=['ocean','mineral','orchid'],default='ocean');args=parser.parse_args()
PKG=args.skill_root.resolve();OUT=args.out.resolve();OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PKG/'scripts'))
from study_data import combine_cohorts,missingness_summary,binomial_estimates,grouped_lineage,lineage,save_study_table
from chart_plan import plan_chart
from evidence_tools import plan_evidence,audit_evidence_layout
from editorial import figure_style
from composition import compose
from publication import save_figure,write_json
from review_tools import compare_revisions
from color_tools import audit_palette,palette_preview,continuous_scale,vision_preview,palette_project,contrast_text
from table_tools import Column,to_latex

COLS='age sex cp trestbps chol fbs restecg thalach exang oldpeak slope ca thal num'.split()
COHORTS=['Cleveland','Hungary','Switzerland','VA Long Beach']
FILES=['cleveland','hungarian','switzerland','va']
TYPES=['Typical angina','Atypical angina','Non-anginal pain','Asymptomatic']
SHORT=['Typical','Atypical','Non-anginal','Asympt.']
THEME=palette_project(args.palette,COHORTS);ENC=THEME['groups']
BLUE=THEME['roles']['primary'];INK='#303B45';MUTED='#6F7B85'
CMAP=LinearSegmentedColormap.from_list(args.palette+'_quantity',THEME['palettes']['sequential'])


def download():
    raw=OUT/'raw';raw.mkdir(exist_ok=True)
    url='https://archive.ics.uci.edu/static/public/45/heart+disease.zip'
    b=urllib.request.urlopen(url,timeout=60).read();(raw/'heart-disease.zip').write_bytes(b)
    archive=zipfile.ZipFile(io.BytesIO(b));files=[]
    for name in [*['processed.'+key+'.data' for key in FILES],'heart-disease.names','WARNING']:
        value=archive.read(name);(raw/name).write_bytes(value)
        files.append({'path':name,'sha256':hashlib.sha256(value).hexdigest()})
    write_json(OUT/'source.json',{'url':url,'dataset':'https://archive.ics.uci.edu/dataset/45/heart+disease',
        'doi':'10.24432/C52P4X','license':'CC BY 4.0','creators':'Janosi, Steinbrunn, Pfisterer & Detrano',
        'zip_sha256':hashlib.sha256(b).hexdigest(),'files':files})


def inputs():
    tables={name:pd.read_csv(OUT/'raw'/('processed.'+file+'.data'),names=COLS,na_values=['?']) for name,file in zip(COHORTS,FILES)}
    # Preserve '?' as NA. Zero cholesterol is only flagged, never interpreted as
    # a real zero or recoded to NA without a verified centre-specific codebook.
    for name,d in tables.items():
        if not d.num.dropna().isin(range(5)).all() or not d.cp.dropna().isin(range(1,5)).all():
            raise ValueError('Unexpected source codes: resolve before plotting')
    miss,profile=missingness_summary(tables,COLS[:-1]);miss.to_csv(OUT/'missingness.csv',index=False)
    write_json(OUT/'cohort-profile.json',profile)
    analysis={name:d.assign(event=np.where(d.num.isna(),np.nan,(d.num>0).astype(float))) for name,d in tables.items()}
    combined=combine_cohorts(analysis);save_study_table(combined,OUT/'analysis-records.csv')
    fractions,intervals=binomial_estimates(combined,event='event',groups=['cp','cohort'],unit='record_id',
        levels={'cp':[1,2,3,4],'cohort':COHORTS},interval='wilson',missing='resolve')
    save_study_table(fractions,OUT/'stratified-fractions.csv');write_json(OUT/'intervals.json',intervals)
    mix=fractions.pivot(index='cohort',columns='cp',values='denominator').reindex(COHORTS)
    mix=mix.div(mix.sum(axis=1),axis=0);mix.columns=['cp'+str(int(k)) for k in mix.columns]
    mix=grouped_lineage(combined,mix.reset_index(),by=['cohort'],operation='chest-pain count / all records within centre')
    retained=pd.DataFrame(profile['cohorts'])[['cohort','records','complete_records']].copy()
    retained['estimate']=retained.complete_records/retained.records
    retained=grouped_lineage(combined,retained,by=['cohort'],operation='literal non-NA complete records / all records across 13 predictors')
    save_study_table(retained,OUT/'retention.csv');save_study_table(mix,OUT/'case-mix.csv')
    style=copy.deepcopy(THEME)
    style['typography']={'base_pt':7.5,'minimum_pt':7,'heading_pt':8}
    write_json(OUT/'project-style.json',style)
    write_json(OUT/'palette-audit.json',audit_palette(style['groups']))
    palette_preview(style['groups'],OUT/'palette.png')
    decision=plan_chart(combined,{'intent':'proportion','event':'event','group':'cohort','condition':'cp','unit':'record_id'})
    write_json(OUT/'chart-decision.json',decision)
    if decision['status']!='ready':raise ValueError(decision['blockers'])
    # Same records, complementary roles; deliberately no independent validation claim.
    spec={'question':'How do recorded disease fractions vary across centres and chest-pain presentations, and what constrains pooled comparison?',
       'claims':{'comparison':{'required_roles':['primary','composition','boundary'],
          'boundary':'Descriptive selected samples, no causal, population-prevalence, adjustment or independent-validation claim.'}},
       'panels':[
         {'id':'primary','source':'fractions','claim':'comparison','role':'primary','question':'How large and precise are within-presentation fractions?',
          'chart':{'intent':'estimates','data_level':'summary','y':'estimate','lower':'lower','upper':'upper','group':'cohort'},'min_area_mm2':4500},
         {'id':'case_mix','source':'mix','claim':'comparison','role':'composition','question':'Do cohorts have different chest-pain composition?',
          'chart':{'intent':'matrix','data_level':'summary','values':['cp1','cp2','cp3','cp4']},'min_area_mm2':1400},
         {'id':'retention','source':'retained','claim':'comparison','role':'boundary','question':'Which centres survive complete-case filtering?',
          'chart':{'intent':'estimates','data_level':'summary','y':'estimate','group':'cohort'},'min_area_mm2':1400}]}
    sources={'fractions':fractions,'mix':mix,'retained':retained}
    plan=plan_evidence(sources,spec);write_json(OUT/'evidence-plan.json',plan)
    bad=copy.deepcopy(spec);bad['panels'][2]['independence']={'from':'primary'}
    negative=plan_evidence(sources,bad);write_json(OUT/'rejected-false-validation.json',negative)
    assert plan['status']=='ready' and negative['status']=='needs_resolution'
    # Independent recomputation directly from original rows, not helper output.
    for row in fractions.to_dict('records'):
        source=tables[row['cohort']];mask=source.cp.eq(row['cp']) & source.num.notna()
        assert row['denominator']==int(mask.sum()) and row['numerator']==int(source.loc[mask,'num'].gt(0).sum())
    checks={'rows':len(combined),'cohorts':{k:len(v) for k,v in tables.items()},'strata':len(fractions),
      'complete_13_predictors':retained.complete_records.tolist(),'smallest_stratum':int(fractions.denominator.min()),
      'zero_cholesterol_by_cohort':{k:int(d.chol.eq(0).sum()) for k,d in tables.items()},
      'counts_match_original_records':True,'shared_record_false_validation_blocked':True,
      'cohort_identity':'source-file labels plus row positions; no cross-centre patient matching possible',
      'source_data_sha256':lineage(combined)['data_sha256']}
    write_json(OUT/'checks.json',checks)
    (OUT/'fractions.tex').write_text(to_latex(fractions.to_dict('records'),[
        Column('cohort','Centre',1,align='left'),Column('cp','Chest-pain code',1,fmt='.0f'),
        Column('numerator','Positive',1,fmt='.0f'),Column('denominator','Observed',1,fmt='.0f'),
        Column('estimate','Fraction',1,fmt='.3f'),Column('lower','Wilson lower',1,fmt='.3f'),
        Column('upper','Wilson upper',1,fmt='.3f')]),encoding='utf8')
    return tables,combined,fractions,mix,retained,miss,plan


def matrix(ax,values,rows,columns,*,percent=True):
    values=np.asarray(values,float)
    norm,cm,report=continuous_scale(values,mode='sequential',limits=[0,1],cmap=CMAP)
    image=ax.imshow(values,cmap=cm,norm=norm,aspect='auto',interpolation='nearest')
    ax.set(xticks=np.arange(len(columns)),xticklabels=columns,yticks=np.arange(len(rows)),yticklabels=rows)
    ax.tick_params(length=0);ax.tick_params(axis='x',rotation=35)
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            v=values[i,j];ink,_=contrast_text(cm(norm(v)))
            ax.text(j,i,f'{100*v:.0f}' if percent else str(v),ha='center',va='center',color=ink,fontsize=7.5)
    for s in ax.spines.values():s.set_visible(False)
    return image,report


def case_mix(ax,mix):
    matrix(ax,mix.set_index('cohort').loc[COHORTS].to_numpy(),COHORTS,['1','2','3','4'])
    ax.tick_params(axis='x',rotation=0)
    ax.set_xlabel('Chest-pain type')
    ax.set_title('Chest-pain composition (%)',loc='left',pad=8)


def retention(ax,retained):
    y=np.arange(4);n=retained.records.to_numpy();k=retained.complete_records.to_numpy();p=k/n
    ax.hlines(y,p,1,color='#C6CDD2',lw=.7)
    for i,name in enumerate(COHORTS):
        color=ENC[name]['color'];marker=ENC[name]['marker']
        ax.plot(1,i,marker=marker,color=color,ms=3.8,label=name)
        ax.plot(p[i],i,marker=marker,color=color,mfc='white',mew=.9,ms=4,label=name)
    for i,(ki,ni,pi) in enumerate(zip(k,n,p)):
        ax.annotate(str(int(ki)),(pi,i),xytext=(-6 if pi>.8 else 6,6),textcoords='offset points',
            ha='right' if pi>.8 else 'left',fontsize=7)
        ax.text(1.075,i,str(int(ni)),transform=ax.get_yaxis_transform(),va='center',ha='left',fontsize=7)
    ax.text(1.075,-.75,'Total n',transform=ax.get_yaxis_transform(),fontsize=7,ha='left')
    ax.set(xlim=(-.06,1.04),ylim=(3.65,-1.05),yticks=y,yticklabels=COHORTS,
       xticks=[0,.5,1],xticklabels=['0','50','100'],xlabel='Records retained (%)')
    ax.tick_params(axis='y',length=0);ax.spines['left'].set_visible(False)
    ax.set_title('Complete-case boundary',loc='left',pad=25)
    from matplotlib.lines import Line2D
    handles=[Line2D([],[],marker='o',ls='none',color=INK,ms=3.8,label='All records'),
        Line2D([],[],marker='o',ls='none',color=INK,mfc='white',ms=3.8,label='Complete 13 fields')]
    ax.legend(handles=handles,loc='lower left',bbox_to_anchor=(-.03,1.02),fontsize=7,handletextpad=.3,borderaxespad=0,
        ncol=2,columnspacing=.7,handlelength=1)


def forest(ax,fractions):
    ys=[];labels=[]
    for gi,label in enumerate(TYPES):
        base=gi*6
        ax.text(0,base-1.03,f'{gi+1}  {label}',transform=ax.get_yaxis_transform(),ha='left',weight='bold',fontsize=8)
        ax.vlines([0,.25,.5,.75,1],base-.45,base+3.45,color='#E3E7EA',lw=.4,zorder=0)
        for ci,cohort in enumerate(COHORTS):
            r=fractions[(fractions.cp==gi+1)&(fractions.cohort==cohort)].iloc[0];y=base+ci
            ax.errorbar(r.estimate,y,xerr=[[r.estimate-r.lower],[r.upper-r.estimate]],fmt=ENC[cohort]['marker'],
                color=ENC[cohort]['color'],ms=3.5,lw=.8,capsize=0,label=cohort)
            ax.text(1.065,y,f'{int(r.numerator)}/{int(r.denominator)}',transform=ax.get_yaxis_transform(),
                va='center',fontsize=7,ha='left');ys.append(y);labels.append(cohort)
    ax.text(1.065,-1.03,'Positive / n',transform=ax.get_yaxis_transform(),fontsize=7,ha='left')
    ax.set(xlim=(-.025,1.025),ylim=(22,-1.9),yticks=ys,yticklabels=labels,
        xticks=[0,.25,.5,.75,1],xticklabels=['0','25','50','75','100'],xlabel='Recorded disease (%)')
    ax.tick_params(axis='y',length=0,pad=4);ax.spines['left'].set_visible(False)
    ax.set_axisbelow(True)


CAPTION='''Four-centre descriptive reanalysis of the UCI Heart Disease processed files (Janosi, Steinbrunn, Pfisterer & Detrano; DOI 10.24432/C52P4X, CC BY 4.0). Cleveland n=303, Hungary n=294, Switzerland n=123, VA Long Beach n=200. These are selected historical clinical samples, not population surveys. Disease is explicitly recoded as source num>0, versus num=0; source missing outcomes would remain missing. Chest-pain codes 1–4 denote typical angina, atypical angina, non-anginal pain and asymptomatic presentation. No causal or adjusted centre effect is inferred.

Panel a: observed within-centre, within-presentation disease fractions. In the interval version, bars show 95% Wilson intervals under an independent-record binomial model; selection, centre heterogeneity and unknown cross-file patient overlap are not accounted for by those intervals. Positive/observed counts are shown, including strata as small as four records. Panel b: chest-pain composition within each centre, in percent; rounding can affect row totals. Panel c: retention when all 13 predictor fields must be nonmissing, compared with retaining all records used by the primary descriptive analysis. Open symbols show complete cases; adjacent numbers are retained counts. No imputation is performed. '?' is parsed as missing. Recorded cholesterol zeros (0, 0, 123 and 49 across the four centres) are flagged separately and are not recoded or used as physiological measurements. Complete-case counts therefore describe literal non-NA fields, not clinical validity. The original archive's corruption WARNING is retained; the processed files are used, rather than the warned-about raw Cleveland file. Derived summaries reuse the same records and do not provide independent validation.'''


def export(c,name,combined,caption):
    geometry=c.fit(max_passes=24);c.labels()
    alignment={'row_groups':[['age','missing']],'column_groups':[]} if name=='S01_context' else {'row_groups':[],'column_groups':[['case_mix','retention']]}
    q=save_figure(c.figure,OUT/name,axes=list(c.axes.values()),source_data=combined,dpi=330,
       alignment_options=alignment)
    write_json(OUT/(name+'.geometry.json'),geometry)
    (OUT/(name+'.caption.md')).write_text(caption+'\n',encoding='utf8')
    plt.close(c.figure);print(name,q['automated_status'],len(q['mark_issues']))
    if q['automated_status'] in ['FAIL','NOT_AUDITABLE']:raise RuntimeError(q['failures'])
    return q,geometry


def run():
    if args.download:download()
    tables,combined,fractions,mix,retained,miss,plan=inputs()
    with figure_style(project=OUT/'project-style.json'):
        # A legitimate compact overview candidate; it does not show precision.
        a=compose((180,120),[['primary','case_mix'],['primary','retention']],width_ratios=[1.12,1],gap_mm=7,
           margins_mm=(3,8,4,4))
        vals=fractions.pivot(index='cohort',columns='cp',values='estimate').reindex(COHORTS)
        matrix(a.axes['primary'],vals.to_numpy(),COHORTS,SHORT)
        a.axes['primary'].set_title('Recorded disease (%)',loc='left',pad=8)
        case_mix(a.axes['case_mix'],mix);retention(a.axes['retention'],retained)
        overview,ag=export(a,'A_overview',combined,CAPTION+'\n\nCandidate A shows the same 16 fractions as a compact matrix; its colour does not represent interval width. Counts and Wilson bounds are preserved in the accompanying CSV/LaTeX table.')
        # B dedicates the long axis to all 16 estimates and their actual intervals.
        b=compose((180,155),[['primary','case_mix'],['primary','retention']],width_ratios=[1.3,1],gap_mm=8,
           panels={'primary':{'min_plot_mm':[42,100]},'case_mix':{'min_plot_mm':[26,28]},'retention':{'min_plot_mm':[26,28]}},
           margins_mm=(3,8,4,4))
        forest(b.axes['primary'],fractions);case_mix(b.axes['case_mix'],mix);retention(b.axes['retention'],retained)
        final,bg=export(b,'B_evidence_final',combined,CAPTION)
        budget=audit_evidence_layout(plan,bg);write_json(OUT/'evidence-layout.json',budget)
        if budget['status']!='PASS':raise ValueError(budget)
        # Ancillary age context and all-field missingness stay in Extended Data.
        s=compose((180,95),[['age','missing']],width_ratios=[1,1.7],gap_mm=9,margins_mm=(3,8,4,4))
        ax=s.axes['age']
        for name,ls in zip(COHORTS,['-','--','-.',':']):
            ages=np.sort(tables[name].age.dropna().to_numpy())
            ax.step(np.r_[ages[0],ages],np.r_[0,np.arange(1,len(ages)+1)/len(ages)],where='post',color=ENC[name]['color'],lw=.9,ls=ls,label=name)
        ax.set(xlabel='Age (years)',ylabel='Cumulative fraction',ylim=(-.025,1.025),yticks=[0,.5,1],xlim=(25,80))
        ax.legend(loc='lower left',bbox_to_anchor=(0,1.02),ncol=2,fontsize=7,
            columnspacing=.8,handlelength=2,handletextpad=.5,borderaxespad=0)
        ax.set_title('Age composition',loc='left',pad=29)
        missing=miss.pivot(index='cohort',columns='variable',values='missing_fraction').reindex(index=COHORTS,columns=COLS[:-1])
        matrix(s.axes['missing'],missing.to_numpy(),COHORTS,COLS[:-1]);s.axes['missing'].tick_params(axis='x',rotation=90)
        s.axes['missing'].set_title('Literal missing values (%)',loc='left',pad=8)
        extra,sg=export(s,'S01_context',combined,'Extended Data. '+CAPTION+'\n\nAge is displayed as an empirical CDF without smoothing or fitted distributions. The missingness matrix reports literal question-mark/NA entries for all 13 predictors; recorded zeros are not counted as missing. Cell labels are percentages, rounded to integers.')
    for name in ['A_overview','B_evidence_final','S01_context']:
        for mode in ['gray','deutan']:vision_preview(OUT/(name+'.png'),OUT/(name+'.'+mode+'.png'),mode=mode)
    comparison=compare_revisions(overview,final,required_panels=['primary','case_mix','retention'])
    write_json(OUT/'candidate-comparison.json',{'chosen':'B_evidence_final','not_an_independent_four_agent_benchmark':True,
        'alternatives':['A_overview','B_evidence_final'],'same_source_records':overview['source_data_sha256']==final['source_data_sha256'],
        'construction_change':comparison,
        'decision':'The smallest cells contain four records. Aligned Wilson intervals and explicit positive/n show uncertainty the compact percentage matrix cannot show. Keep composition and complete-case boundary; move age and all-variable missingness to Extended Data.',
        'source_principles':{
            'nature-figure':'Question, distinct evidence roles, unequal area, boundary in main, ancillary material in Extended Data.',
            'SciPilot':'Real missingness/denominators and crossed group sizes determine dot-interval versus matrix choice.',
            'FigMirror':'Review whole composition and panel construction; preserve correct counts and identity during revision.',
            'figures4papers':'Aligned comparisons, shared scales and stable semantic roles; adapt source code rather than copy historical dimensions or method colours.'}})


if __name__=='__main__':run()
