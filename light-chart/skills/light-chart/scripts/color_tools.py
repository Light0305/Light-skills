"""Color semantics and inspectable diagnostics; no aesthetic certification.

Severity-100 CVD matrices: Machado, Oliveira & Fernandes (2009),
doi:10.1109/TVCG.2009.113, supplementary tables, also distributed in
colorspacious/cvd.py (Nathaniel Smith, MIT). Calculations use linear RGB.
Pair-distance/contrast thresholds below are configurable plotting heuristics.
"""
from __future__ import annotations
from itertools import combinations
import numpy as np
from matplotlib.colors import to_rgb, Normalize, TwoSlopeNorm


def palette_project(name, identities=()):
    """Create a task project from a visual family; save it before drawing.

    Families are starting points, not journal or accessibility certifications.
    Explicit identity order is fixed once per project, never cycled per panel.
    """
    import json
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    families=json.loads((root/'assets/palette-families.json').read_text(encoding='utf8'))
    if name not in families:raise ValueError('Unknown palette family')
    family=families[name];labels=list(identities)
    if len(labels)!=len(set(labels)) or len(labels)>len(family['categorical']):
        raise ValueError('Unique identities within the explicit palette capacity required')
    project=json.loads((root/'assets/project-style.json').read_text(encoding='utf8'))
    project['name']='light-chart-'+name;project['palettes']=dict(family)
    project['palettes'].pop('label');project['palette_family']=name
    project['roles'].update(primary=family['categorical'][0],secondary=family['categorical'][2],accent=family['categorical'][1],
                            down=family['diverging'][0],up=family['diverging'][-1],pale=family['sequential'][0])
    markers=['o','s','^','D','v','P'];lines=['-','--','-.',':','-','--']
    project['groups']={label:{'color':color,'marker':markers[i],'linestyle':lines[i]}
        for i,(label,color) in enumerate(zip(labels,family['categorical']))}
    return project


def contrast_text(facecolor, *, background='white', minimum=4.5):
    """Choose label ink from actual composited colour, not from scalar value."""
    from matplotlib.colors import to_rgba
    rgba=np.asarray(to_rgba(facecolor));bg=np.asarray(to_rgb(background))
    face=rgba[:3]*rgba[3]+bg*(1-rgba[3]);lum=float(_linear(face) @ [.2126,.7152,.0722])
    candidates=['#24313B','#FFFFFF','#000000'];ratios=[]
    for ink in candidates:
        li=float(_linear(to_rgb(ink)) @ [.2126,.7152,.0722])
        ratios.append((max(li,lum)+.05)/(min(li,lum)+.05))
    preferred=max(range(2),key=lambda i:ratios[i])
    if ratios[preferred]<minimum:preferred=int(np.argmax(ratios))
    return candidates[preferred],{'contrast':float(ratios[preferred]),'minimum':minimum,
        'status':'PASS' if ratios[preferred]>=minimum else 'REVIEW_REQUIRED'}

_CVD={
 'protan':[[.152286,1.052583,-.204868],[.114503,.786281,.099216],[-.003882,-.048116,1.051998]],
 'deutan':[[.367322,.860646,-.227968],[.280085,.672501,.047413],[-.011820,.042940,.968881]],
 'tritan':[[1.255528,-.076749,-.178779],[-.078411,.930809,.147602],[.004733,.691367,.303900]]}


def _linear(rgb):
    rgb=np.asarray(rgb,float)
    return np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)


def _srgb(rgb):
    rgb=np.clip(rgb,0,1)
    return np.where(rgb<=.0031308,12.92*rgb,1.055*rgb**(1/2.4)-.055)


def simulate_colors(colors, mode='normal'):
    """Approximate display preview, including out-of-gamut clipping; not diagnosis."""
    rgb=np.asarray([to_rgb(c) for c in colors]); linear=_linear(rgb)
    if mode=='gray':
        return _srgb(np.repeat((linear @ [.2126,.7152,.0722])[:,None],3,axis=1))
    if mode=='normal':return rgb
    if mode not in _CVD:raise ValueError('Unknown color-vision mode')
    return _srgb(linear @ np.array(_CVD[mode]).T)


def _lab(rgb):
    xyz=_linear(rgb) @ np.array([[.4124564,.2126729,.0193339],
       [.3575761,.7151522,.1191920],[.1804375,.0721750,.9503041]])
    xyz=xyz/[.95047,1.,1.08883]; d=6/29
    f=np.where(xyz>d**3,np.cbrt(xyz),xyz/(3*d*d)+4/29)
    return np.column_stack((116*f[:,1]-16,500*(f[:,0]-f[:,1]),200*(f[:,1]-f[:,2])))


def audit_palette(encodings, *, background='white', alpha=1., distance_min=12., contrast_min=3.):
    """Evaluate the colors actually used, after alpha compositing on background.

    encodings maps identities to {color, marker?, linestyle?}. Similar pairs are
    flagged even with redundant channels; redundancy is recorded, not a waiver.
    Gray and three CVD previews support actual inspection of the final figure.
    """
    if not encodings or not 0<alpha<=1 or min(distance_min,contrast_min)<=0:
        raise ValueError('Nonempty encodings and positive thresholds/alpha required')
    names=list(encodings); bg=np.array(to_rgb(background))
    colors=[alpha*np.array(to_rgb(encodings[n]['color']))+(1-alpha)*bg for n in names]
    findings=[]; modes={}
    for mode in ['normal','gray',*_CVD]:
        rgb=simulate_colors(colors,mode); lab=_lab(rgb); pairs=[]
        for i,j in combinations(range(len(names)),2):
            distance=float(np.linalg.norm(lab[i]-lab[j]))
            redundancy=any(encodings[names[i]].get(k)!=encodings[names[j]].get(k)
               for k in ['marker','linestyle'] if encodings[names[i]].get(k) and encodings[names[j]].get(k))
            row={'identities':[names[i],names[j]],'deltaE76':distance,'redundant_channel':redundancy}
            pairs.append(row)
            if distance<distance_min:findings.append({'code':'similar_colors','mode':mode,**row})
        modes[mode]={'rgb':rgb.tolist(),'pairs':pairs}
    lum=_linear(colors) @ [.2126,.7152,.0722]; bgl=float(_linear(bg) @ [.2126,.7152,.0722])
    contrasts=(np.maximum(lum,bgl)+.05)/(np.minimum(lum,bgl)+.05)
    for name,ratio in zip(names,contrasts):
        if ratio<contrast_min:findings.append({'code':'low_mark_contrast','identity':name,'ratio':float(ratio)})
    return {'status':'REVIEW_REQUIRED' if findings else 'PASS','findings':findings,'modes':modes,
      'contrast':dict(zip(names,map(float,contrasts))), 'thresholds':{'distance_min':distance_min,'contrast_min':contrast_min},
      'boundary':'Heuristic flagging; size, stroke, density and redundant encodings require actual figure inspection.'}


def continuous_scale(values, *, mode='sequential', limits=None, center=None, cmap=None):
    """Validate quantity semantics; never choose a diverging midpoint from median."""
    import matplotlib as mpl
    from project_style import colormap
    a=np.asarray(values,float); finite=a[np.isfinite(a)]
    if not finite.size or np.isinf(a).any():raise ValueError('Finite values required; NA may stay missing')
    lo,hi=limits if limits is not None else (finite.min(),finite.max())
    if not np.isfinite([lo,hi]).all() or not lo<hi or finite.min()<lo or finite.max()>hi:
        raise ValueError('Color limits must cover all finite values without clipping')
    if mode=='diverging':
        if center is None or not np.isfinite(center) or not lo<center<hi:
            raise ValueError('Diverging scale requires an explicit meaningful center inside limits')
        norm=TwoSlopeNorm(center,lo,hi)
    elif mode=='sequential':
        if center is not None:raise ValueError('Sequential scale has no central reference')
        norm=Normalize(lo,hi)
    else:raise ValueError('mode must be sequential or diverging')
    cm=mpl.colormaps[cmap] if isinstance(cmap,str) else cmap or colormap(diverging=mode=='diverging')
    lightness=_lab(cm(np.linspace(0,1,257))[:,:3])[:,0]
    chunks=[lightness] if mode=='sequential' else [lightness[:129],lightness[128:]]
    monotonic=all(np.all(np.diff(v)>=-.1) or np.all(np.diff(v)<=.1) for v in chunks)
    return norm,cm,{'mode':mode,'limits':[float(lo),float(hi)],'center':center,
       'lightness_monotonic_each_arm':bool(monotonic),'cmap':cm.name,
       'status':'PASS' if monotonic else 'REVIEW_REQUIRED'}


def palette_preview(encodings, path):
    """A diagnostic sheet outside the scientific figure, not an extra figure panel."""
    import matplotlib.pyplot as plt
    names=list(encodings); modes=['normal','gray',*_CVD]
    fig,ax=plt.subplots(figsize=(max(5,len(names)*1.1),2.6))
    for row,mode in enumerate(modes):
        for col,color in enumerate(simulate_colors([encodings[n]['color'] for n in names],mode)):
            ax.add_patch(plt.Rectangle((col,row),.9,.75,facecolor=color,edgecolor='none'))
    ax.set(xticks=np.arange(len(names))+.45,xticklabels=names,yticks=np.arange(len(modes))+.375,
      yticklabels=modes,xlim=(-.05,len(names)),ylim=(len(modes),-.1))
    ax.tick_params(length=0,labelsize=8); [s.set_visible(False) for s in ax.spines.values()]
    fig.tight_layout();fig.savefig(path,dpi=160);plt.close(fig)


def audit_rendered_mapping(snapshot, project):
    """Compare actual named artists/native R scale mappings to the project JSON.

    Only declared group identities are checked. Unnamed marks and independent
    continuous variables are not guessed to be group encodings.
    """
    groups=project.get('groups',{}); findings=[]; checked=[]
    def check(identity,actual,where):
        if identity not in groups:return
        expected=np.array(to_rgb(groups[identity]['color']))
        values=np.asarray([to_rgb(actual)] if isinstance(actual,str) else actual,float)
        if values.ndim==1:values=values[None,:]
        if values.shape[1] not in (3,4):raise ValueError('Unrecognized rendered color shape')
        checked.append({'identity':identity,'where':where})
        if not np.allclose(values[:,:3],expected[None,:],atol=1/255+.0001):
            findings.append({'code':'identity_color_drift','identity':identity,'where':where,
                'expected':groups[identity]['color'],'actual':values.tolist()})
    for where,item in snapshot.get('named_series_colors',{}).items():
        if item.get('label') and 'color' in item:check(item['label'],item['color'],where)
        if '/scale/' in where and where.endswith(('/colour','/fill')):
            limits=item.get('limits',[]);mapped=item.get('mapped',[])
            if isinstance(limits,str):limits=[limits]
            if isinstance(mapped,str):mapped=[mapped]
            for label,color in zip(limits,mapped):check(str(label),color,where)
    return {'status':'FAIL' if findings else 'PASS' if checked else 'NOT_APPLICABLE',
       'checked':checked,'findings':findings,'boundary':'Named identities only; aesthetic quality and unnamed data encodings require review.'}


def vision_preview(png, out, *, mode='deutan'):
    """Accessibility diagnostic of an export; preserves geometry, never overwrites it."""
    from pathlib import Path
    from PIL import Image
    if Path(png).resolve()==Path(out).resolve():raise ValueError('Keep original scientific export')
    a=np.array(Image.open(png).convert('RGB'));shape=a.shape
    rgb=a.reshape(-1,3)/255.;linear=_linear(rgb)
    if mode=='gray':linear=np.repeat((linear @ [.2126,.7152,.0722])[:,None],3,axis=1)
    elif mode in _CVD:linear=linear @ np.array(_CVD[mode]).T
    else:raise ValueError('Choose gray, protan, deutan or tritan')
    Image.fromarray(np.uint8(np.rint(_srgb(linear).reshape(shape)*255))).save(out)


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser(description='Check actual Python/R mapped identities in a saved QA report')
    p.add_argument('--qa',required=True);a=p.parse_args();path=Path(a.qa)
    report=json.loads(path.read_text(encoding='utf-8'))
    audit=audit_rendered_mapping(report.get('figure_snapshot',{}),report['project_style'])
    report['color_mapping_audit']=audit
    if audit['status']=='FAIL':
        report['automated_status']='FAIL';report.setdefault('failures',[]).append('Rendered group colors differ from project identity mapping')
    from publication import write_json
    write_json(path,report)
    raise SystemExit(1 if audit['status']=='FAIL' else 0)
