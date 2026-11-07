"""Reproducible chart atlas, not a collection of inferred experimental results.

Run: python gallery.py --out OUTPUT [--rscript PATH] [--only 01,02]
First run native R (--native-r); its saved built-ins feed the Python examples.
Optional --task-root adds already validated complex tasks, explicitly as reuse.
All new examples save source values, calculations, PDF/SVG and checked previews.
"""
from pathlib import Path
import argparse,hashlib,html,json,shutil,sys,traceback
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize,TwoSlopeNorm
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from scipy import stats
from editorial import (figure_style,canvas,axes_mm,raw_groups,interval_trajectory,
                       scientific_heatmap,estimate_column,component_matrix)
from composition import compose,label_line_ends
from publication import save_figure,write_json
from project_style import colormap
from color_tools import palette_project,contrast_text
from research_panels import paired_changes,joint_density
from field_tools import grid_field,scalar_field,field_surface

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--native-r',action='store_true')
parser.add_argument('--rscript')
parser.add_argument('--only',default='')
parser.add_argument('--task-root',type=Path)
args=parser.parse_args();OUT=args.out.resolve();FIG=OUT/'figures';DATA=OUT/'data'
FIG.mkdir(parents=True,exist_ok=True);DATA.mkdir(exist_ok=True)
project=palette_project('ocean',['setosa','versicolor','virginica'])
C=project['palettes']['categorical'];INK=project['roles']['ink']
project['typography'].update(base_pt=7.5,minimum_pt=7,heading_pt=8.5)
for a,b in [('Automatic','Manual'),('Male','Female'),('OJ','VC')]:
    project['groups'][a]={'color':C[0],'shape':16,'marker':'o'}
    project['groups'][b]={'color':C[1],'shape':17,'marker':'^'}
write_json(OUT/'project-style.json',project)
if args.native_r:
    from r_runtime import run_r
    result=run_r(ROOT/'assets/examples/gallery.R',[str(ROOT),str(OUT)],
               rscript=args.rscript,log=OUT/'R-runtime.json',cwd=OUT,timeout=240)
    print(result['stdout']);print(result['stderr'])
    if result['status']!='PASS':raise SystemExit(1)
    # R exports can be browsed before the Python gallery is generated.
    raise SystemExit(0)

from sklearn.datasets import load_iris,load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_curve,precision_recall_curve,roc_auc_score,average_precision_score
iris0=load_iris();iris=pd.DataFrame(iris0.data,columns=['sepal_length','sepal_width','petal_length','petal_width'])
iris['species']=np.array(iris0.target_names)[iris0.target];iris['source_record']=np.arange(len(iris))
iris.to_csv(DATA/'iris.csv',index=False);(DATA/'iris-source.txt').write_text(iris0.DESCR,encoding='utf8')
breast=load_breast_cancer();X=breast.data;y=1-breast.target
train,test=train_test_split(np.arange(len(y)),test_size=.30,stratify=y,random_state=27)
models={};scores=[]
subsets=[('Radius',[0]),('Radius + texture',[0,1]),('Shape',[0,1,2,3]),('All 30',list(range(30)))]
for label,features in subsets:
    model=make_pipeline(StandardScaler(),LogisticRegression(max_iter=3000,random_state=27))
    model.fit(X[train][:,features],y[train]);p=model.predict_proba(X[test][:,features])[:,1]
    models[label]=p;scores.append({'model':label,'features':features,'auc':roc_auc_score(y[test],p),'ap':average_precision_score(y[test],p)})
bc=pd.DataFrame(X,columns=breast.feature_names);bc['malignant']=y;bc['source_record']=np.arange(len(y));bc['split']=np.where(np.isin(np.arange(len(y)),test),'test','train')
bc.to_csv(DATA/'breast-cancer.csv',index=False);(DATA/'breast-cancer-source.txt').write_text(breast.DESCR,encoding='utf8')
pred=pd.DataFrame({'source_record':test,'malignant':y[test],**{k:v for k,v in models.items()}})
pred.to_csv(DATA/'heldout-predictions.csv',index=False);write_json(DATA/'model-scores.json',scores)
selection=set(args.only.split(',')) if args.only else None
existing=json.loads((OUT/'manifest.json').read_text('utf8')) if (OUT/'manifest.json').exists() else {'entries':[]}
entries={e['id']:e for e in existing['entries']};errors=dict(existing.get('errors',{}))

def chart(n,title,category,source,recipe,caption,*,data='iris.csv',backend='Python'):
    def wrap(fn):
        key=f'{n:02}'
        if selection is not None and key not in selection:return fn
        try:
            with figure_style(project=project):
                result=fn()
                if len(result)==2:c,axes=result;extra={}
                else:c,axes,extra=result
                if hasattr(c,'fit'):c.fit(max_passes=12);fig=c.figure
                else:fig=c
                base=FIG/(key+'_'+fn.__name__)
                qa=save_figure(fig,base,axes=axes,dpi=300,source_data=DATA/data,
                  alignment_options=extra.get('alignment_options'),grayscale=False)
                plt.close(fig)
            (base.with_suffix('.caption.md')).write_text(caption,encoding='utf8')
            entries[key]={'id':key,'title':title,'category':category,'backend':backend,'origin':'本次运行',
              'source':source,'recipe':recipe,'base':base.relative_to(OUT).as_posix(),
              'data':'data/'+data,'caption':caption,'automated_status':qa['automated_status'],
              'visual_review':'pending','details':extra.get('details',{})}
            if qa['automated_status'] in {'FAIL','NOT_AUDITABLE','IN_PROGRESS'}:
                errors[key]='Final-file checks failed: '+str(qa.get('failures',[]))
            else:errors.pop(key,None)
            print(key,title,qa['automated_status'],flush=True)
        except Exception as e:
            errors[key]=traceback.format_exc();plt.close('all');print(key,'ERROR',str(e),flush=True)
            if key in entries:entries[key]['automated_status']='FAILED_RUN'
        write_json(OUT/'manifest.json',{'entries':sorted(entries.values(),key=lambda e:e['id']),'errors':errors})
        return fn
    return wrap

def single(size=(110,88),projection=None):
    c=compose(size,[['main']],panels={'main':{'projection':projection,'min_plot_mm':(45,35)}},margins_mm=(5,5,5,5))
    return c,c.axes['main']

def outside_legend(ax,**kw):
    return ax.legend(loc='lower left',bbox_to_anchor=(0,1.025),borderaxespad=0,**kw)

def iris_groups():return [iris.loc[iris.species==s,'petal_length'].to_numpy() for s in iris0.target_names]
def species_points(ax,x,y,**kw):
    for k,s in enumerate(iris0.target_names):
        d=iris[iris.species==s];ax.scatter(d[x],d[y],s=13,c=C[k],marker=['o','s','^'][k],edgecolors='white',linewidths=.35,label=s,**kw)

@chart(1,'分组散点图','关系与分布','sklearn 内置 Iris，150 条实测记录','Matplotlib + compose',
       'Iris: all 150 measured flowers, three species (n=50 each). Colours and symbols both identify species; no fitted relation.')
def scatter():
    c,a=single();species_points(a,'sepal_length','petal_length');a.set(xlabel='Sepal length (cm)',ylabel='Petal length (cm)');outside_legend(a,ncol=3)
    return c,[a]

@chart(2,'箱线图与全部原始点','关系与分布','Iris','editorial.raw_groups',
       'Petal length for all 150 Iris observations. Boxes: median and quartiles; whiskers: 1.5 IQR. Horizontal jitter changes no measured value.')
def box_raw():
    c,a=single();raw_groups(a,iris_groups(),iris0.target_names,C[:3],seed=27,point_size=9);a.set_ylabel('Petal length (cm)');return c,[a]

@chart(3,'小提琴图与全部原始点','关系与分布','Iris','Matplotlib violin + raw observations',
       'All Iris petal lengths. Violin boundaries use Gaussian KDE (Scott bandwidth), truncated at the observed extrema; raw points and medians remain visible.')
def violin():
    c,a=single();rng=np.random.default_rng(27)
    for k,v in enumerate(iris_groups()):
        obj=a.violinplot(v,[k],widths=.75,showextrema=False,bw_method='scott')
        for b in obj['bodies']:b.set_facecolor(C[k]);b.set_edgecolor(C[k]);b.set_alpha(.18)
        a.scatter(k+rng.uniform(-.16,.16,len(v)),v,s=7,color=C[k],alpha=.7,linewidth=0)
        a.plot([k-.12,k+.12],[np.median(v)]*2,color=INK,lw=1.2)
    a.set(xticks=range(3),xticklabels=iris0.target_names,ylabel='Petal length (cm)');return c,[a]

@chart(4,'叠加直方图','关系与分布','Iris','Matplotlib common bin edges',
       'All 150 Iris petal lengths. Identical 0.5-cm bin edges are used for the three species; y encodes record counts, not density.')
def histogram():
    c,a=single();edges=np.arange(.5,7.51,.5)
    for k,v in enumerate(iris_groups()):a.hist(v,bins=edges,histtype='stepfilled',alpha=.20,color=C[k],edgecolor=C[k],lw=.8,label=iris0.target_names[k])
    a.set(xlabel='Petal length (cm)',ylabel='Count',ylim=(0,40));outside_legend(a,ncol=3);return c,[a]

@chart(5,'经验累积分布 ECDF','关系与分布','Iris','Matplotlib exact steps',
       'Empirical cumulative distributions of all observed petal lengths. Every jump is one of 50 observations per species; no density fitting.')
def ecdf():
    c,a=single()
    for k,v in enumerate(iris_groups()):a.step(np.sort(v),np.arange(1,len(v)+1)/len(v),where='post',color=C[k],ls=['-','--',':'][k],lw=1.2,label=iris0.target_names[k])
    a.set(xlabel='Petal length (cm)',ylabel='Cumulative fraction',ylim=(0,1.02));outside_legend(a,ncol=3);return c,[a]

@chart(6,'一维核密度图','关系与分布','Iris','scipy.stats.gaussian_kde, Scott bandwidth',
       'Descriptive Gaussian KDE of all Iris petal lengths, Scott bandwidth per species. Kernel tails extend beyond observed values and are smoothing, not extra observations.')
def kde():
    c,a=single();x=np.linspace(0,8,350)
    for k,v in enumerate(iris_groups()):
        yy=stats.gaussian_kde(v,bw_method='scott')(x);a.plot(x,yy,color=C[k],lw=1.1,label=iris0.target_names[k]);a.fill_between(x,yy,color=C[k],alpha=.09)
    a.set(xlabel='Petal length (cm)',ylabel='Density (1/cm)',ylim=(0,None));outside_legend(a,ncol=3);return c,[a]

@chart(7,'雨云图','关系与分布','Iris','One-sided KDE + box + all raw points',
       'Iris raincloud display: one-sided Gaussian KDE (Scott bandwidth), median/quartiles, and all raw lengths. Density cut off at observed extrema; random display jitter seed 27.')
def raincloud():
    c,a=single((125,88));rng=np.random.default_rng(27)
    for k,v in enumerate(iris_groups()):
        ygrid=np.linspace(v.min(),v.max(),150);dens=stats.gaussian_kde(v)(ygrid);dens=dens/dens.max()*.34
        a.fill_betweenx(ygrid,k-.07-dens,k-.07,color=C[k],alpha=.24,lw=0)
        a.boxplot([v],positions=[k],widths=.10,showfliers=False,manage_ticks=False,
          boxprops={'color':C[k]},medianprops={'color':INK,'linewidth':1.2},whiskerprops={'color':C[k]},capprops={'color':C[k]})
        a.scatter(k+.13+rng.uniform(0,.22,len(v)),v,s=7,color=C[k],alpha=.7,lw=0)
    a.set(xticks=range(3),xticklabels=iris0.target_names,xlim=(-.55,2.5),ylabel='Petal length (cm)');return c,[a]

@chart(8,'配对连线与变化量','配对与趋势','R datasets::sleep，10 位受试者','research_panels.paired_changes',
       'R sleep: the same ten subjects received two soporific drugs. Lines preserve ID matching. Right panel is drug 2 minus drug 1 in extra hours of sleep; no p value or interval inferred.',data='sleep.csv')
def paired():
    d=pd.read_csv(DATA/'sleep.csv');d['group']=d['group'].astype(str)
    wide=paired_changes(d,id='ID',condition='group',value='extra',order=['1','2']);wide.to_csv(DATA/'sleep-paired.csv')
    c=compose((140,88),[['pairs','delta']],width_ratios=[1.1,1],gap_mm=9,margins_mm=(5,5,5,5))
    a,b=c.axes.values()
    for _,r in wide.iterrows():a.plot([0,1],r[['1','2']],color=C[0],alpha=.45,lw=.8,marker='o',ms=3)
    a.set(xticks=[0,1],xticklabels=['Drug 1','Drug 2'],xlim=(-.3,1.3),ylabel='Extra sleep (h)')
    b.axvline(0,color='#C3C9CD',lw=.6);b.scatter(wide['change'],np.arange(10),color=C[1],s=16)
    b.set(xlabel='Within-subject change (h)',yticks=np.arange(10),yticklabels=[str(x) for x in wide.index],ylabel='Subject')
    return c,[a,b],{'alignment_options':{'panel_ids':['pairs','delta'],'row_groups':[['pairs','delta']],'column_groups':[]},'details':{'pairs':len(wide)}}

@chart(9,'个体纵向轨迹与末端标签','配对与趋势','R datasets::Orange，5 棵树','composition.label_line_ends',
       'All 35 Orange observations, five orange trees measured at seven ages. Straight segments connect the same tree only; no growth model or interpolated observations.',data='Orange.csv')
def individual_paths():
    d=pd.read_csv(DATA/'Orange.csv');c,a=single((125,88));lines=[]
    for k,(g,sub) in enumerate(d.groupby('Tree',sort=True)):
        sub=sub.sort_values('age');lines+=a.plot(sub.age,sub.circumference,marker=['o','s','^','D','v'][k],ms=2.7,color=C[k],lw=1,label=f'Tree {g}')
    label_line_ends(a,lines,minimum_gap_pt=12);a.set(xlabel='Age (days)',ylabel='Trunk circumference (mm)');return c,[a]

@chart(10,'中位数与四分位范围趋势','配对与趋势','R datasets::ChickWeight','editorial.interval_trajectory',
       'ChickWeight: median observed weight and interquartile range by diet and recorded day. IQR represents cross-sectional spread among the chicks still measured that day, not a confidence interval. Repeated measures and attrition retained.',data='ChickWeight.csv')
def interval_trend():
    d=pd.read_csv(DATA/'ChickWeight.csv');c,a=single((125,88));records=[]
    for k,(g,sub) in enumerate(d.groupby('Diet')):
        q=sub.groupby('Time').weight.quantile([.25,.5,.75]).unstack();interval_trajectory(a,q.index,q[.5],q[.25],q[.75],color=C[k],label=f'Diet {g}',marker=['o','s','^','D'][k]);records+=q.reset_index().assign(Diet=g).to_dict('records')
    pd.DataFrame(records).to_csv(DATA/'chick-quantiles.csv',index=False)
    a.set(xlabel='Time (days)',ylabel='Weight (g)');outside_legend(a,ncol=4);return c,[a]

@chart(11,'分组柱状图','比较与估计','Iris','Matplotlib observed group means',
       'Species means of two measured length variables in centimetres; n=50 records per species. Bars start at zero and no uncertainty is inferred. Raw distributions are available in entries 01–07.')
def grouped_bars():
    c,a=single((120,88));x=np.arange(2)
    for k,s in enumerate(iris0.target_names):
        v=iris[iris.species==s][['sepal_length','petal_length']].mean();a.bar(x+(k-1)*.23,v,width=.21,color=C[k],label=s)
    a.set(xticks=x,xticklabels=['Sepal length','Petal length'],ylabel='Mean length (cm)',ylim=(0,8));outside_legend(a,ncol=3);return c,[a]

@chart(12,'百分比堆叠柱','比较与估计','Iris，全部记录','Matplotlib explicit cut-point counts',
       'Observed petal-length composition in each Iris species, using explicitly declared ranges <2, 2–<5, and ≥5 cm. Each denominator is 50. These bins demonstrate composition and are not clinical or botanical thresholds.')
def stacked_proportions():
    d=iris.copy();d['range']=pd.cut(d.petal_length,[-np.inf,2,5,np.inf],right=False,labels=['<2 cm','2–<5 cm','≥5 cm'])
    tab=pd.crosstab(d.species,d['range']).reindex(iris0.target_names);tab.to_csv(DATA/'iris-composition.csv')
    c,a=single();bottom=np.zeros(3)
    for k,col in enumerate(tab):
        v=tab[col].to_numpy()/tab.sum(axis=1).to_numpy()*100;a.bar(range(3),v,bottom=bottom,color=C[k],width=.6,label=col)
        for j,num in enumerate(v):
            if num>=10:a.text(j,bottom[j]+num/2,f'{num:.0f}%',ha='center',va='center',color=contrast_text(C[k])[0])
        bottom+=v
    a.set(xticks=range(3),xticklabels=iris0.target_names,ylabel='Observed records (%)',ylim=(0,100));outside_legend(a,ncol=3);return c,[a]

@chart(13,'森林图与明确分母','比较与估计','Wisconsin breast cancer，569 记录','study_data.binomial_estimates + estimate_column',
       'Recorded malignant-label fractions by explicitly declared mean-radius bands (<12, 12–<16, ≥16 source units). Points and 95% Wilson intervals assume independent records; descriptive selection-sample fractions, not clinical risk or population prevalence. Positive/n is explicit.',data='breast-cancer.csv')
def forest():
    from study_data import binomial_estimates
    d=bc.copy();d['band']=pd.cut(d['mean radius'],[-np.inf,12,16,np.inf],right=False,labels=['<12','12–<16','≥16']).astype(str)
    est,_=binomial_estimates(d,event='malignant',groups=['band'],unit='source_record',levels={'band':['<12','12–<16','≥16']},interval='wilson')
    est.to_csv(DATA/'radius-fractions.csv',index=False)
    c,a=single((125,85));estimate_column(a,100*est.estimate,est.band,lower=100*est.lower,upper=100*est.upper,colors=C[:3],limits=(0,100),ticks=[0,25,50,75,100])
    a.set(xlabel='Recorded malignant labels (%)',ylabel='Mean-radius band')
    for k,r in est.iterrows():a.text(1.035,k,f'{int(r.numerator)}/{int(r.denominator)}',transform=a.get_yaxis_transform(),va='center')
    return c,[a]

@chart(14,'气泡矩阵','矩阵与多变量','Iris，3 物种 × 4 特征','Matplotlib area and colour encodings',
       'Each of 12 cells summarizes 50 flowers. Bubble area encodes the percentage above the pooled median of that feature; colour encodes mean measured length/width in cm. Pooled-median rule is explicit and not expression detection.')
def bubble_matrix():
    features=list(iris.columns[:4]);means=iris.groupby('species')[features].mean().reindex(iris0.target_names)
    above=(iris[features]>iris[features].median()).assign(species=iris.species).groupby('species').mean().reindex(iris0.target_names)*100
    c=canvas((145,95));a=axes_mm(c,28,23,80,55);cb=axes_mm(c,120,23,3,55)
    xx,yy=np.meshgrid(range(4),range(3));sc=a.scatter(xx,yy,s=above.to_numpy()*1.6,c=means.to_numpy().ravel(),cmap=colormap(),vmin=0,vmax=7,edgecolors='#71817F',linewidth=.35)
    c.colorbar(sc,cax=cb,label='Mean (cm)');a.set(xticks=range(4),xticklabels=['Sepal\nlength','Sepal\nwidth','Petal\nlength','Petal\nwidth'],yticks=range(3),yticklabels=iris0.target_names,xlim=(-.5,3.5),ylim=(2.5,-.5))
    handles=[a.scatter([],[],s=p*1.6,facecolor='white',edgecolor='#71817F',lw=.5,label=f'{p}%') for p in [25,50,100]]
    a.legend(handles=handles,loc='lower left',bbox_to_anchor=(0,1.08),ncol=3,title='Above pooled median',title_fontsize=7)
    means.to_csv(DATA/'iris-means.csv');above.to_csv(DATA/'iris-above-median.csv');return c,[a]

@chart(15,'带数值注释的热图','矩阵与多变量','Iris','editorial.scientific_heatmap',
       'Twelve unnormalized species means in centimetres, all observations retained. One common 0–7 cm colour scale. Annotation ink is selected from actual fill luminance.')
def annotated_matrix():
    mat=iris.groupby('species')[list(iris.columns[:4])].mean().reindex(iris0.target_names)
    c=canvas((140,84));a=axes_mm(c,26,17,77,54);cb=axes_mm(c,116,17,3,54)
    im=scientific_heatmap(a,mat,iris0.target_names,['Sepal L','Sepal W','Petal L','Petal W'],limits=(0,7),fmt='.2f');c.colorbar(im,cax=cb,label='Mean (cm)');return c,[a]

@chart(16,'三角相关矩阵','矩阵与多变量','Iris，150 条','Pearson r, no significance inference',
       'Pearson correlations among four measured Iris features across all 150 records, including between-species variation. Lower triangle is redundant and masked deliberately. Diverging scale has a meaningful zero centre; no significance test.')
def correlation():
    corr=iris.iloc[:,:4].corr();values=corr.to_numpy();masked=np.ma.array(values,mask=np.tril(np.ones((4,4),bool),-1))
    c=canvas((125,105));a=axes_mm(c,26,17,68,68);cb=axes_mm(c,105,17,3,68)
    cm=colormap(diverging=True).with_extremes(bad='white');norm=TwoSlopeNorm(0,-1,1);im=a.imshow(masked,cmap=cm,norm=norm)
    for i in range(4):
        for j in range(i,4):a.text(j,i,f'{values[i,j]:.2f}',ha='center',va='center',color=contrast_text(cm(norm(values[i,j])))[0])
    a.set(xticks=range(4),yticks=range(4),xticklabels=['Sepal L','Sepal W','Petal L','Petal W'],yticklabels=['Sepal L','Sepal W','Petal L','Petal W']);a.tick_params(length=0);a.xaxis.tick_top()
    for sp in a.spines.values():sp.set_visible(False)
    c.colorbar(im,cax=cb,label='Pearson r');corr.to_csv(DATA/'iris-correlations.csv');return c,[a]

@chart(17,'ROC 曲线','预测评估','Wisconsin breast cancer，固定分层留出集','Real held-out LogisticRegression probabilities',
       'Stratified 70/30 split, seed 27; training-only StandardScaler and logistic regression using mean radius and mean texture. Positive=malignant. ROC and AUC use the same held-out records. Educational model demonstration, not clinical validation.',data='heldout-predictions.csv')
def roc():
    p=models['Radius + texture'];fpr,tpr,threshold=roc_curve(y[test],p);pd.DataFrame({'fpr':fpr,'tpr':tpr,'threshold':threshold}).to_csv(DATA/'roc.csv',index=False)
    c,a=single();a.plot([0,1],[0,1],ls='--',color='#BAC3CA',lw=.7);a.step(fpr,tpr,where='post',color=C[0],lw=1.3,label=f'AUC {roc_auc_score(y[test],p):.3f}')
    a.set(xlabel='False-positive rate',ylabel='True-positive rate',xlim=(-.02,1.02),ylim=(-.02,1.02));outside_legend(a);return c,[a]

@chart(18,'精确率–召回率曲线','预测评估','同一固定留出集','sklearn precision_recall_curve',
       'Same held-out predictions and positive class as ROC. Step curve is raw precision versus recall, not an interpolated precision envelope. Dashed line is positive-label fraction in this test split; legend reports average precision.',data='heldout-predictions.csv')
def precision_recall():
    p=models['Radius + texture'];precision,recall,th=precision_recall_curve(y[test],p)
    pd.DataFrame({'precision':precision,'recall':recall}).to_csv(DATA/'precision-recall.csv',index=False)
    c,a=single();a.axhline(y[test].mean(),ls='--',color='#A6B0BA',lw=.8);a.step(recall,precision,where='post',color=C[2],lw=1.3,label=f'AP {average_precision_score(y[test],p):.3f}')
    a.set(xlabel='Recall',ylabel='Precision',xlim=(-.02,1.02),ylim=(-.02,1.02));outside_legend(a);return c,[a]

@chart(19,'火山图','比较与估计','Wisconsin breast cancer，30 实测特征','Mann–Whitney contrasts + explicit BH adjustment',
       'Exploratory volcano of 30 positive-valued measured image features, not genes. Effect=log2(malignant-group mean/benign-group mean); two-sided Mann–Whitney tests, BH adjustment across these 30 features. Dotted display thresholds are q=.05 and |log2 ratio|=.2. Group labels are observational; no causal interpretation.',data='breast-cancer.csv')
def volcano_contrasts():
    pvals=np.array([stats.mannwhitneyu(X[y==1,k],X[y==0,k],alternative='two-sided').pvalue for k in range(X.shape[1])]);order=np.argsort(pvals);adj=np.minimum.accumulate((pvals[order]*len(pvals)/np.arange(1,len(pvals)+1))[::-1])[::-1];q=np.empty_like(adj);q[order]=np.minimum(adj,1)
    effect=np.log2(X[y==1].mean(axis=0)/X[y==0].mean(axis=0));sig=(q<.05)&(np.abs(effect)>=.2)
    d=pd.DataFrame({'feature':breast.feature_names,'log2_mean_ratio':effect,'p':pvals,'q':q});d.to_csv(DATA/'feature-contrasts.csv',index=False)
    c,a=single((120,95));colors=np.where(sig,np.where(effect>0,C[1],C[0]),'#B7C0C7')
    a.scatter(effect,-np.log10(q),c=colors,s=22,edgecolors='white',lw=.4);a.axhline(-np.log10(.05),color='#B7C0C7',lw=.6,ls='--')
    for v in [-.2,.2]:a.axvline(v,color='#B7C0C7',lw=.6,ls='--')
    a.set(xlabel='log₂ mean ratio (malignant / benign)',ylabel='−log₁₀ BH-adjusted p');return c,[a]

def marginal_canvas():
    c=compose((130,110),[['top','.'],['main','right']],width_ratios=[4,1],height_ratios=[1,4],gap_mm=2.5,margins_mm=(5,5,5,5),panels={'top':{'share_x_with':'main','min_plot_mm':(45,9)},'right':{'share_y_with':'main','min_plot_mm':(9,40)}})
    return c,c.axes['main'],c.axes['top'],c.axes['right']

@chart(20,'散点与边缘分布','联合分布','Iris','Same-record scatter and common-bin marginals',
       'All 150 Iris flowers in the centre and both marginal histograms. Species colours are consistent; shared limits and common bins. Marginals describe the same records and are not independent evidence.')
def scatter_marginals():
    c,a,top,right=marginal_canvas();species_points(a,'sepal_length','petal_length')
    for k,s in enumerate(iris0.target_names):
        d=iris[iris.species==s];top.hist(d.sepal_length,bins=np.arange(4,8.51,.25),color=C[k],alpha=.25,edgecolor=C[k],lw=.5);right.hist(d.petal_length,bins=np.arange(.5,7.51,.25),orientation='horizontal',color=C[k],alpha=.25,edgecolor=C[k],lw=.5)
    a.set(xlabel='Sepal length (cm)',ylabel='Petal length (cm)',xlim=(4,8.5),ylim=(.5,7.5));top.set_ylabel('Count');right.set_xlabel('Count');top.tick_params(labelbottom=False);right.tick_params(labelleft=False);outside_legend(top,ncol=3,handles=a.get_legend_handles_labels()[0])
    return c,[a,top,right],{'alignment_options':{'panel_ids':['main','top','right'],'row_groups':[['main','right']],'column_groups':[['main','top']]}}

@chart(21,'六边形计数与边缘分布','联合分布','R datasets::faithful，272 次记录','research_panels.joint_density',
       'All 272 faithful records. Hexagon colour encodes count with 22-bin horizontal grid. Both marginal totals and the sum of hexagon counts are checked against the same source row count.',data='faithful.csv')
def hexbin_marginals():
    d=pd.read_csv(DATA/'faithful.csv');c,a,top,right=marginal_canvas();r=joint_density(a,top,right,d.eruptions,d.waiting,gridsize=22)
    assert r['hexbin_total']==r['x_hist_total']==r['y_hist_total']==len(d)
    a.set(xlabel='Eruption duration (min)',ylabel='Waiting time (min)')
    # Inset count key occupies the unused upper-right mosaic cell, not the data.
    cb=axes_mm(c.figure,111,5,3,15);c.figure.colorbar(r['mappable'],cax=cb,label='Count')
    write_json(DATA/'hexbin-checks.json',{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in r.items() if k!='mappable'})
    return c,[a,top,right],{'alignment_options':{'panel_ids':['main','top','right'],'row_groups':[['main','right']],'column_groups':[['main','top']]}}

@chart(22,'二维密度等高线','联合分布','faithful，272 次记录','scipy.stats.gaussian_kde, Scott bandwidth',
       'All faithful points with descriptive two-dimensional Gaussian KDE (Scott bandwidth). Contours show density levels, not confidence regions or counted observations; limits include every source record.',data='faithful.csv')
def density_contours():
    d=pd.read_csv(DATA/'faithful.csv');x=np.linspace(1.4,5.5,130);yy=np.linspace(40,100,150);xx,zz=np.meshgrid(x,yy);density=stats.gaussian_kde(np.vstack([d.eruptions,d.waiting]))(np.vstack([xx.ravel(),zz.ravel()])).reshape(xx.shape)
    c,a=single();a.scatter(d.eruptions,d.waiting,s=5,c=C[0],alpha=.28,lw=0);a.contour(xx,zz,density,levels=6,colors=C[2],linewidths=.8);a.set(xlabel='Eruption duration (min)',ylabel='Waiting time (min)',xlim=(1.4,5.5),ylim=(40,100));return c,[a]

@chart(23,'网络图','网络与结构','NetworkX Zachary karate club，34 节点、78 边','NetworkX spring_layout(seed=27), Matplotlib',
       'Zachary karate club graph distributed by NetworkX. All 34 nodes and 78 unweighted edges retained. Colours identify recorded club labels; node number is source ID. Spring coordinates (seed 27) are layout only and do not imply physical distance or inferred clusters.',data='karate-nodes.csv')
def network():
    import networkx as nx
    graph=nx.karate_club_graph();pos=nx.spring_layout(graph,seed=27,weight=None)
    pd.DataFrame([{'node':n,'club':v['club'],'x':pos[n][0],'y':pos[n][1]} for n,v in graph.nodes(data=True)]).to_csv(DATA/'karate-nodes.csv',index=False)
    pd.DataFrame(list(graph.edges),columns=['source','target']).to_csv(DATA/'karate-edges.csv',index=False)
    c,a=single((135,108))
    edge_artist=nx.draw_networkx_edges(graph,pos,ax=a,width=.55,edge_color='#AAB8C3',alpha=.7)
    edge_artist.set_rasterized(True)
    colors=[C[0] if graph.nodes[n]['club']=='Mr. Hi' else C[1] for n in graph]
    node_artist=nx.draw_networkx_nodes(graph,pos,ax=a,node_size=105,node_color=colors,edgecolors='white',linewidths=.5)
    node_artist.set_rasterized(True)
    for n,color in zip(graph,colors):a.text(*pos[n],str(n),ha='center',va='center',fontsize=7,color=contrast_text(color)[0])
    a.margins(.15);a.set_axis_off();a.set_aspect('equal')
    a.legend(handles=[Line2D([],[],ls='',marker='o',color=C[k],label=s) for k,s in enumerate(['Mr. Hi','Officer'])],loc='lower left',bbox_to_anchor=(0,1.01),ncol=2)
    return c,[a]

def terrain():
    z=pd.read_csv(DATA/'volcano.csv').to_numpy();x=np.arange(z.shape[1])*10;ygrid=np.arange(z.shape[0])*10
    return grid_field(x,ygrid,z,limits=(float(z.min()),float(z.max())))

@chart(24,'二维定量标量场','二维场与三维','R datasets::volcano，87 × 61 高程','field_tools.grid_field / scalar_field',
       'Maunga Whau volcano elevations from R datasets::volcano. All 5307 grid values retained, original 10-m coordinate spacing; no smoothing or invented fine grid. Colour limits are the observed range and match entry 26.',data='volcano.csv')
def scalar_map():
    field=terrain();c=canvas((135,115));a=axes_mm(c,24,9,73,92);cb=axes_mm(c,109,9,3,92)
    im=scalar_field(a,field);a.set(xlabel='Grid x (m)',ylabel='Grid y (m)');a.set_aspect('equal');c.colorbar(im,cax=cb,label='Elevation (m)');return c,[a]

@chart(25,'地形等高线','二维场与三维','同一 volcano 原始高程网格','Matplotlib contour (linear within grid)',
       'Same 5307 original volcano elevations as entries 24 and 26. Contours are interpolated at declared levels from the original 10-m grid; no resampling, terrain fitting or additional measurements.',data='volcano.csv')
def contour_map():
    f=terrain();c,a=single((115,120));cs=a.contour(f.x,f.y,f.z,levels=np.arange(100,191,10),colors=C[2],linewidths=.75)
    # Inline labels are intentionally placed in real contour gaps. Rasterizing
    # only the contour lines avoids treating their enclosing path boxes as ink.
    cs.set_rasterized(True)
    labels=a.clabel(cs,inline=True,fontsize=7.5,fmt='%d')
    for label in labels:label.set_rotation(0);label.set_bbox({'facecolor':'white','edgecolor':'none','pad':.25})
    a.set(xlabel='Grid x (m)',ylabel='Grid y (m)');a.set_aspect('equal');return c,[a]

@chart(26,'三维高程曲面','二维场与三维','同一 volcano 原始高程网格','field_tools.field_surface, every grid vertex',
       'Original volcano heights, every one of 5307 vertices rendered. Same observed-range colour limits as entry 24; shade=False prevents illumination from altering scalar colour meaning. View elev=27°, azim=−58°; x/y/elevation in metres. Projection and height-box aspect are display choices.',data='volcano.csv')
def surface_3d():
    f=terrain();fig=canvas((145,115));a=axes_mm(fig,7,7,112,93,projection='3d');cb=axes_mm(fig,127,22,3,65)
    im=field_surface(a,f);a.set(xlabel='x (m)',ylabel='y (m)',zlabel='Elevation (m)');a.set_xticks([0,300,600]);a.set_yticks([0,400,800]);a.set_zticks([100,140,180]);fig.colorbar(im,cax=cb,label='Elevation (m)');return fig,[a]

@chart(27,'三维散点','二维场与三维','Iris，150 条实测记录','Matplotlib 3D scatter, fixed camera',
       'Three measured Iris dimensions, all 150 source records. Species uses both colour and symbol. Camera elev=24°, azim=−58°, depthshade=False; no fitted manifold or projected clusters.')
def scatter_3d():
    fig=canvas((145,120));a=axes_mm(fig,10,17,115,88,projection='3d')
    for k,s in enumerate(iris0.target_names):
        d=iris[iris.species==s];a.scatter(d.sepal_length,d.sepal_width,d.petal_length,color=C[k],marker=['o','s','^'][k],s=12,depthshade=False,label=s,edgecolor='white',lw=.25)
    a.set(xlabel='Sepal length (cm)',ylabel='Sepal width (cm)',zlabel='Petal length (cm)');a.view_init(elev=24,azim=-58);a.set_box_aspect((1,1,1));a.legend(loc='lower center',bbox_to_anchor=(.5,1.06),ncol=3)
    a.set_xticks([4.5,6,7.5]);a.set_yticks([2,3,4]);a.set_zticks([1,3,5,7])
    a.xaxis.labelpad=12;a.yaxis.labelpad=20;a.zaxis.labelpad=7
    for axis in [a.xaxis,a.yaxis,a.zaxis]:axis.pane.set_facecolor((1,1,1,0));axis._axinfo['grid'].update(color=(.75,.8,.84,.4),linewidth=.4)
    return fig,[a]

@chart(28,'多尺度并列热图','矩阵与多变量','Iris，实际均值及样本数','Independent declared scales, shared row identity',
       'Species rows aligned across mean measured lengths (0–7 cm), within-species sample SD (0–1 cm), and record count (0–50). Each block declares its own units/scale; raw metrics are not normalized into a single comparable magnitude.')
def multi_scale():
    features=list(iris.columns[:4]);g=iris.groupby('species')[features];means=g.mean().reindex(iris0.target_names);sd=g.std().reindex(iris0.target_names)
    fig=canvas((180,93));a=axes_mm(fig,24,14,53,50);b=axes_mm(fig,89,14,53,50);nax=axes_mm(fig,153,14,12,50)
    labels=['Sepal L','Sepal W','Petal L','Petal W']
    im=scientific_heatmap(a,means,iris0.target_names,labels,limits=(0,7));im2=scientific_heatmap(b,sd,['']*3,labels,limits=(0,1),fmt='.2f');im3=scientific_heatmap(nax,np.full((3,1),50),['']*3,['n'],limits=(0,50),fmt='.0f')
    for imx,left,width,label in [(im,24,53,'Mean (cm)'),(im2,89,53,'Sample SD (cm)'),(im3,153,12,'Count')]:
        cb=axes_mm(fig,left,71,width,2.5);fig.colorbar(imx,cax=cb,orientation='horizontal',label=label)
    return fig,[a,b,nax],{'alignment_options':{'panel_ids':['means','sd','n'],'row_groups':[['means','sd','n']],'column_groups':[],
      'exemptions':[{'panels':['means','sd','n'],'checks':['panel-width','horizontal-gutter'],
        'reason':'Two four-variable blocks have equal widths; single n column is explicitly narrower, with independent physical colourbar/label corridors.'}]}}

@chart(29,'组件矩阵与留出集性能','预测评估','同一真实数据、同一固定留出集','editorial.component_matrix / estimate_column',
       'Four logistic models fitted on identical training IDs and evaluated on identical held-out IDs. Open/filled circles explicitly mark included feature sets; AUC and AP are point metrics only. No invented confidence interval, significance or causal claim. Correlated feature additions do not establish component causality.',data='heldout-predictions.csv')
def component_comparison():
    fig=canvas((180,90));a=axes_mm(fig,36,19,51,47);b=axes_mm(fig,101,19,30,47);d=axes_mm(fig,143,19,29,47)
    included=[[1,0,0],[1,1,0],[1,1,1],[1,1,1]]
    # Third column includes remaining features; Shape only uses perimeter/area.
    component_matrix(a,[[1,0,0,0],[1,1,0,0],[1,1,1,0],[1,1,1,1]],row_labels=[s[0] for s in subsets],column_labels=['Radius','Texture','Shape','Rest'],highlight=3)
    for ax,key,label in [(b,'auc','Test AUC'),(d,'ap','Test AP')]:
        vals=[s[key] for s in scores];estimate_column(ax,vals,['']*4,colors=[C[0],C[2],C[4],C[1]],highlight=3,limits=(.8,1),ticks=[.8,.9,1]);ax.set_xlabel(label)
        for i,v in enumerate(vals):ax.text(v,i+.31,f'{v:.3f}',ha='center',va='center',fontsize=7)
    return fig,[a,b,d],{'alignment_options':{'panel_ids':['design','auc','ap'],'row_groups':[['design','auc','ap']],'column_groups':[],
      'exemptions':[{'panels':['design','auc','ap'],'checks':['panel-width','horizontal-gutter'],
        'reason':'Four-column binary design and two single-metric estimate columns have different semantic roles; aligned rows and declared unequal widths retain room for source model labels.'}]}}

@chart(30,'向量场与流线','二维场与三维','解析演示 u=−y, v=x；非实测','Matplotlib quiver / streamplot',
       'Analytic demonstration only: u=−y, v=x on an explicitly declared Cartesian grid. Arrows encode local vectors; flow lines are numerical streamlines of that field. No experimental measurements or inferred fluid data.',data='analytic-vectors.csv')
def vector_field():
    x=np.linspace(-2,2,21);ygrid=x.copy();xx,yy=np.meshgrid(x,ygrid);u=-yy;v=xx
    pd.DataFrame({'x':xx.ravel(),'y':yy.ravel(),'u':u.ravel(),'v':v.ravel()}).to_csv(DATA/'analytic-vectors.csv',index=False)
    c,a=single((110,105));a.streamplot(x,ygrid,u,v,color=C[2],density=.75,linewidth=.65,arrowsize=.7);a.quiver(xx[::3,::3],yy[::3,::3],u[::3,::3],v[::3,::3],color=C[0],scale=28,width=.003)
    a.set(xlabel='x (analytic units)',ylabel='y (analytic units)',xlim=(-2.5,2.5),ylim=(-2.5,2.5));a.set_aspect('equal');return c,[a]

def import_render(key,title,category,path,source,recipe,data,caption=None,backend='Python',origin='已验证完整任务复用'):
    path=Path(path)
    if not path.with_suffix('.png').exists():return
    base=FIG/(key+'_'+path.name)
    previous=json.loads(base.with_suffix('.qa.json').read_text('utf8')) if base.with_suffix('.qa.json').exists() else None
    for ext in ['.png','.pdf','.svg','.pdf-preview.png','.qa.json','.caption.md']:
        if path.with_suffix(ext).exists():shutil.copy2(path.with_suffix(ext),base.with_suffix(ext))
    # QA keeps original task binding; gallery reports it and does not relabel it.
    q=json.loads(path.with_suffix('.qa.json').read_text('utf8'))
    from review_tools import bind_exports
    bind_exports(q,pdf=base.with_suffix('.pdf'),png=base.with_suffix('.png'))
    if previous:
        from review_tools import verify_exports
        if not verify_exports(previous):
            q['visual_review']=previous.get('visual_review',q['visual_review'])
    q['outputs']=[str(base.with_suffix(ext)) for ext in ['.pdf','.svg','.png']]
    q['gallery_copy_of']=str(path)
    write_json(base.with_suffix('.qa.json'),q)
    data_path=Path(data)
    if data_path.is_absolute() and data_path.is_file():
        local=DATA/(key+'_'+data_path.name);shutil.copy2(data_path,local)
        sidecar=Path(str(data_path)+'.lineage.json')
        if sidecar.exists():shutil.copy2(sidecar,Path(str(local)+'.lineage.json'))
        data=local.relative_to(OUT).as_posix()
    text=caption or (path.with_suffix('.caption.md').read_text('utf8') if path.with_suffix('.caption.md').exists() else '')
    base.with_suffix('.caption.md').write_text(text,encoding='utf8')
    entries[key]={'id':key,'title':title,'category':category,'backend':backend,'origin':origin,'source':source,
      'recipe':recipe,'base':base.relative_to(OUT).as_posix(),'data':data,'caption':text,
      'automated_status':q['automated_status'],'visual_review':q.get('visual_review',{}).get('status','pending'),'original_qa':str(path.with_suffix('.qa.json'))}

for key,name,title,cat,source,recipe,data,caption in [
 ('31','31_R_clustered','原生 R 聚类注释热图','原生 R','R datasets::mtcars，32 车辆 × 7 特征','domain_plots.R::annotated_heatmap_r','data/mtcars.csv','Seven measured variables across 32 mtcars records. Feature-wise sample z scores, synchronously reordered labels and transmission annotations, declared cylinder splits. Clustering is descriptive, not biological grouping.'),
 ('32','32_R_survival','原生 R 生存曲线与风险表','原生 R','survival::lung，228 记录','domain_plots.R::survival_panel_r','data/lung.csv','Descriptive Kaplan–Meier survival by recorded sex, source status 2=event and 1=censored. Steps, intervals, censor marks and risk counts derive from the same 228 lung records. Risk counts explicitly verified at 0,250,500,750,1000 days; observational, unadjusted comparison.'),
 ('33','33_R_facets','原生 R 分面原始点与中位数','原生 R','R datasets::ToothGrowth，60 只豚鼠','ggplot2 + native R review snapshot','data/ToothGrowth.csv','All 60 ToothGrowth records, 10 animals per dose/supplement cell. Horizontal display jitter leaves tooth length unchanged; black diamonds are cell medians. Dose categorical; no response fit or invented significance. Source does not declare a tooth-length unit.')]:
    path=FIG/name
    if path.with_suffix('.png').exists():
        q=json.loads(path.with_suffix('.qa.json').read_text('utf8'));path.with_suffix('.caption.md').write_text(caption,encoding='utf8')
        entries[key]={'id':key,'title':title,'category':cat,'backend':'R','origin':'本次原生 R 运行','source':source,'recipe':recipe,'base':path.relative_to(OUT).as_posix(),'data':data,'caption':caption,'automated_status':q['automated_status'],'visual_review':q.get('visual_review',{}).get('status','pending')}
if args.task_root:
    task=args.task_root.resolve();old=task/'v0.7-evidence-r-3d-color/tasks';new=task/'v0.8-multicentre'
    import_render('34','复杂分层证据主图','完整组合任务',new/'B_evidence_final','UCI Heart Disease，四来源共920条记录','study_data + evidence_tools + compose',str(new/'analysis-records.csv'),origin='本次完整任务，新配色')
    import_render('35','原像素图像板与 ROI','完整组合任务',old/'T04_image_plate','scikit-image immunohistochemistry 原始 RGB','image_layout.image_plate / link_roi',str(old/'IHC.npy'))
    import_render('36','体素等值面与正交切片','完整组合任务',old/'T05_volume','Allen Institute / scikit-image cells3d ROI','field_tools.volume_isosurface + image_panel',str(old/'cells3d-nuclei-ROI.npy'))
    import_render('37','纵向证据链与失访边界','完整组合任务',old/'T01_evidence','R datasets::ChickWeight，完整纵向记录','evidence_tools.plan_evidence + compose',str(old/'ChickWeight.csv'))
    import_render('38','原生 R 轨迹、分面与修订验证','完整组合任务',old/'T02_R_final','R datasets::CO2，84 条重复测量','native R review_tools.R + compare_revisions',str(old/'CO2.csv'),backend='R')

# Optional complete published-aggregate examples, freshly run with benchmark.py.
bench=OUT/'reported-benchmarks'
if (bench/'figure_legends.md').exists():
    legends=(bench/'figure_legends.md').read_text('utf8')
    for key,name,title,data in [
      ('39','01_method_comparison','多方法与多指标区间比较','immunostruct.json'),
      ('40','02_component_ablation','组件消融与参数敏感性','immunostruct.json'),
      ('41','03_structured_heatmap','方法族与双尺度分组矩阵','rnagenscape.json')]:
        import_render(key,title,'论文汇总数据重绘',bench/name,'figures4papers 提供的论文汇总值（CC BY-NC 4.0）',
          'assets/examples/benchmark.py',str(bench/data),caption=legends,origin='本次重跑，来源汇总数据')

manifest={'version':'0.8.0','entries':sorted(entries.values(),key=lambda e:e['id']),'errors':errors,
  'scope':'A runnable visual atlas. Basic examples demonstrate a construction, not a full independent research task. Complex validated tasks are explicitly reused. Original reference-only chart recipes are not claimed as callable coverage.',
  'tables':'Native LaTeX tables remain outside the figure count.',
  'models':{'seed':27,'train_n':len(train),'test_n':len(test),'positive':'malignant','preprocessing':'StandardScaler fitted only on training records'},
  'analytic_demo':['30'],'review':'Technical checks do not certify scientific or editorial quality.'}
write_json(OUT/'manifest.json',manifest)

def build_page():
    from PIL import Image,ImageDraw,ImageFont
    fontpath='C:/Windows/Fonts/msyh.ttc'
    font=ImageFont.truetype(fontpath,22);small=ImageFont.truetype(fontpath,17)
    items=manifest['entries'];sheets=[]
    for start in range(0,len(items),12):
        subset=items[start:start+12];width=2400;height=60+470*((len(subset)+3)//4)
        sheet=Image.new('RGB',(width,height),'#F4F6F7');draw=ImageDraw.Draw(sheet)
        draw.text((25,14),f'light-chart · 图型总览 {start+1}–{start+len(subset)} / {len(items)}',font=font,fill=INK)
        for k,e in enumerate(subset):
            x=(k%4)*600;y=60+(k//4)*470;draw.rectangle((x+10,y+8,x+590,y+460),fill='white')
            im=Image.open(OUT/(e['base']+'.png')).convert('RGB');im.thumbnail((565,385))
            sheet.paste(im,(x+300-im.width//2,y+15+(385-im.height)//2))
            draw.text((x+22,y+402),e['id']+'  '+e['title'],font=font,fill=INK)
            suffix=' · 需复核' if e['automated_status']!='PASS' else ''
            draw.text((x+22,y+435),e['backend']+' · '+e['origin']+suffix,font=small,fill='#647482')
        filename=f'总览_{start//12+1:02}.jpg';sheet.save(OUT/filename,quality=94);sheets.append(filename)
    parts=['''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>light-chart 图型图册</title>
<style>:root{color:#26333E;background:#F4F6F7;font:16px/1.65 Arial,"Microsoft YaHei",sans-serif}body{max-width:1420px;margin:32px auto;padding:0 24px}h1{font-size:30px;font-weight:600}h2{font-size:21px}a{color:#3E6FB0}nav{position:sticky;top:0;background:#F4F6F7ee;padding:14px 0;z-index:5;backdrop-filter:blur(10px)}button,input,select{font:inherit;padding:7px 12px;margin:3px;border:1px solid #CCD5DC;background:white;border-radius:4px}button{cursor:pointer}button.active{background:#3E6FB0;color:white}#cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,470px),1fr));gap:22px}article{background:white;padding:20px;border:1px solid #DEE5E9}article img{display:block;width:100%;height:370px;object-fit:contain;cursor:zoom-in}p{margin:10px 0}.meta{font-size:13px;color:#667684}.caption{font-size:13px;line-height:1.6}.flag{color:#9A5D2E}dialog{max-width:96vw;max-height:94vh;border:1px solid #CCD5DC;padding:12px}dialog img{max-width:92vw;max-height:82vh;object-fit:contain}dialog::backdrop{background:#18252Cbb}details{margin:12px 0}summary{cursor:pointer}#count{margin-left:12px}</style>''']
    parts.append(f'<h1>light-chart：{len(items)} 张基础图型、原生 R 与完整组合</h1><p>点击放大，或打开 PDF / SVG；图注、数据与检查记录随图可查。类别、连续量和零中心偏差分别配色，同一身份在一张图中保持一致。</p>')
    parts.append('<p class="meta">基础图展示具体构造；完整组合展示任务能力，两者不冒充独立科研验证。各图分别标注本次运行、既有任务复用和解析演示。表格直接交 LaTeX，不计为图。技术检查待复核提示保留原始状态。</p>')
    for sheet in sheets:parts.append(f'<a href="{sheet}">缩略总览 {sheets.index(sheet)+1}</a>　')
    if args.task_root:parts.append('<p><a href="../v0.8-multicentre/color-options/comparison.png">同一完整主图的三套实际配色</a> · <a href="../v0.8-multicentre/阅览.html">多中心完整任务</a></p>')
    cats=list(dict.fromkeys(e['category'] for e in items))
    parts.append('<nav><select id="backend" onchange="filter()"><option value="all">全部后端</option><option value="Python">Python</option><option value="R">R</option></select><input id="search" placeholder="搜索图型、数据或后端" oninput="filter()"><button class="active" onclick="choose(this,\'全部\')">全部</button>'+''.join(f'<button onclick="choose(this,\'{cat}\')">{cat}</button>' for cat in cats)+'<span id="count"></span></nav><div id="cards">')
    for e in items:
        base=e['base'];caption=html.escape(e['caption']);meta=html.escape(e['source']+' · '+e['recipe']);search=html.escape(json.dumps(e,ensure_ascii=False),quote=True)
        data=e['data'];data=Path(data).as_uri() if Path(data).is_absolute() else data
        parts.append(f'<article data-cat="{e["category"]}" data-backend="{e["backend"]}" data-search="{search}"><h2>{e["id"]}　{e["title"]}</h2><p class="meta">{e["backend"]} · {e["origin"]} · 程序检查：<span class="'+('flag' if e['automated_status']!='PASS' else '')+f'">{e["automated_status"]}</span></p><img loading="lazy" src="{base}.png" alt="{e["title"]}" onclick="zoom(this)"><p><a href="{base}.pdf">PDF</a> · <a href="{base}.svg">SVG</a> · <a href="{base}.caption.md">图注</a> · <a href="{data}">数据</a> · <a href="{base}.qa.json">检查</a></p><details><summary>数据、构造与解释边界</summary><p class="meta">{meta}</p><p class="caption">{caption}</p></details></article>')
    parts.append('''</div><details><summary>覆盖边界</summary><p>本图册覆盖当前本地实现的主要出图构造，并增加了已实际执行的常用统计图。四个来源仓库中仅有文档、需要外部数据/依赖、尚未适配的配方不算已运行能力，例如 chord、Sankey、系统发育树和专门的空间组学流程。不能从图册张数推断任意数据都能一键成图；实际任务仍需核对统计单位、选图和布局。</p></details><p class="meta"><a href="manifest.json">图型清单与实际状态</a> · <a href="data/model-scores.json">留出模型计算</a></p>
<dialog id="large" onclick="if(event.target===this)this.close()"><button onclick="document.getElementById('large').close()">关闭</button><br><img id="big"></dialog>
<script>let category='全部';function choose(b,c){category=c;document.querySelectorAll('nav button').forEach(x=>x.classList.remove('active'));b.classList.add('active');filter()}function filter(){const q=document.getElementById('search').value.toLowerCase();let n=0;document.querySelectorAll('article').forEach(a=>{const yes=(category==='全部'||a.dataset.cat===category)&&(document.getElementById('backend').value==='all'||a.dataset.backend===document.getElementById('backend').value)&&a.dataset.search.toLowerCase().includes(q);a.style.display=yes?'':'none';if(yes)n++});document.getElementById('count').textContent=n+' 张'}function zoom(i){document.getElementById('big').src=i.src;document.getElementById('large').showModal()}filter()</script></html>''')
    (OUT/'阅览.html').write_text(''.join(parts),encoding='utf8')
build_page()
print('GALLERY',len(entries),'ERRORS',len(errors),flush=True)
if errors:raise SystemExit(1)
