"""Full new-data tasks for evidence, native-R revisions, 3D and RGB plates.

No dependency on original reference repositories. All input/export provenance is
saved beside the figures. Built-in datasets are used as validation, not studies
conducted by the skill author.
"""
from pathlib import Path
import argparse
import json
import sys
import hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_PKG=ROOT if (ROOT/'SKILL.md').is_file() else ROOT/'skills/light-chart'
DEFAULT_OUT=ROOT/'artifacts/v0.7-evidence-r-3d-color/tasks' if (ROOT/'skills/light-chart/SKILL.md').is_file() else Path.cwd()/'light-chart-validation'
p=argparse.ArgumentParser();p.add_argument('--stage',choices=['inputs','evidence','r','3d','images','volume','all'],default='all')
p.add_argument('--skill-root',type=Path,default=DEFAULT_PKG)
p.add_argument('--out',type=Path,default=DEFAULT_OUT)
args=p.parse_args();PKG=args.skill_root.resolve();OUT=args.out.resolve();OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PKG/'scripts'))
from publication import save_figure,write_json
from editorial import figure_style
from composition import compose
from evidence_tools import plan_evidence,audit_evidence_layout
from color_tools import audit_palette,palette_preview,continuous_scale
from field_tools import grid_field,scalar_field,field_surface,volume_isosurface
from project_style import encodings_for,role
from image_layout import image_plate,link_roi
from review_tools import compare_revisions
from r_runtime import run_r


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def inputs():
    result=run_r(Path(__file__).with_suffix('.R'),['data',PKG,OUT],log=OUT/'R-data-runtime.json')
    if result['returncode']!=0:raise RuntimeError(result['stderr'])
    style=read(PKG/'assets/project-style.json')
    colors=['#0072B2','#B65022','#207A52','#88569A']
    styles=['-','--','-.',':'];markers=['o','s','^','D']
    style['groups']={f'Diet {i+1}':dict(color=c,linestyle=ls,marker=m)
        for i,(c,ls,m) in enumerate(zip(colors,styles,markers))}
    write_json(OUT/'ChickWeight-style.json',style)
    groups=['Quebec / nonchilled','Quebec / chilled','Mississippi / nonchilled','Mississippi / chilled']
    style['groups']={name:{'color':('#174B75' if i<2 else '#B65022'),
        'linetype':('solid' if i%2==0 else 'dashed'),'shape':(16 if i%2==0 else 17),
        'linestyle':('-' if i%2==0 else '--'),'marker':('o' if i%2==0 else '^')}
       for i,name in enumerate(groups)}
    write_json(OUT/'CO2-style.json',style)
    before=read(OUT/'CO2-style.json')
    for i,name in enumerate(groups):before['groups'][name]['color']=['#226D8D','#288C83','#427D93','#49998F'][i]
    write_json(OUT/'R-before-style.json',before)
    for label,project in [('CO2',style),('CO2-before',before)]:
        audit=audit_palette(project['groups']);write_json(OUT/(label+'-palette-audit.json'),audit)
        palette_preview(project['groups'],OUT/(label+'-palette.png'))
    from skimage import data
    pixels=data.immunohistochemistry();np.save(OUT/'IHC.npy',pixels)
    write_json(OUT/'provenance.json',{
      'ChickWeight':{'source':'R datasets::ChickWeight','rows':578,'units':'50 chicks, repeated ages; incomplete follow-up retained'},
      'CO2':{'source':'R datasets::CO2','rows':84,'units':'12 plants, 7 concentrations per plant; 3 plants per origin/treatment cell'},
      'volcano':{'source':'R datasets::volcano; local R help saved','shape':[87,61],
        'coordinates':'10 m sample spacing; local index axes, no inferred compass orientation','unit':'elevation m'},
      'IHC':{'source':'skimage.data.immunohistochemistry; CMMI','shape':list(pixels.shape),
        'sha256':hashlib.sha256(pixels.tobytes()).hexdigest(),'calibration':'not supplied; source pixel units only',
        'description':data.immunohistochemistry.__doc__}})


def export(c,name,data,caption,*,axes=None,alignment=None):
    geometry=c.fit(max_passes=18);c.labels()
    selected=list(c.axes.values()) if axes is None else axes
    qa=save_figure(c.figure,OUT/name,source_data=data,axes=selected,dpi=330,
      alignment_options=alignment or {'row_groups':[], 'column_groups':[]})
    (OUT/(name+'.caption.md')).write_text(caption+'\n',encoding='utf-8')
    write_json(OUT/(name+'.geometry.json'),geometry)
    plt.close(c.figure)
    print(name,qa['automated_status'],len(qa['mark_issues']))
    if qa['automated_status'] in ['FAIL','NOT_AUDITABLE']:raise ValueError(str(qa['failures']))
    return qa,geometry


def evidence():
    d=pd.read_csv(OUT/'ChickWeight.csv');d['Diet']=d.Diet.map(lambda x:f'Diet {x}')
    baseline=d[d.Time==0].set_index('Chick')['weight']
    endpoint=d[d.Time==21].copy();endpoint['gain']=endpoint.weight-endpoint.Chick.map(baseline)
    count=d.groupby(['Diet','Time']).Chick.nunique().rename('observed').reset_index()
    counts_wide=count.pivot(index='Diet',columns='Time',values='observed')
    counts_wide.columns=counts_wide.columns.astype(str);counts_wide=counts_wide.reset_index()
    endpoint.to_csv(OUT/'chick-endpoints.csv',index=False);count.to_csv(OUT/'chick-counts.csv',index=False)
    counts_wide.to_csv(OUT/'chick-count-matrix.csv',index=False)
    panels=[]
    for i in range(4):
        panels.append({'id':f'diet{i+1}','source':'longitudinal','select':{'Diet':[f'Diet {i+1}']},
          'role':'primary','question':f'What individual growth trajectories were observed under diet {i+1}?',
          'claim':'growth','chart':{'intent':'trend','x':'Time','y':'weight','unit':'Chick','ordered':True},
          'min_area_mm2':1100})
    panels.extend([
      {'id':'gain','source':'endpoint','role':'distribution','claim':'growth','depends_on':['diet1','diet2','diet3','diet4'],
       'question':'How heterogeneous is 0-to-21-day gain among chicks with both observations?',
       'chart':{'intent':'compare','y':'gain','group':'Diet','unit':'Chick'},'min_area_mm2':1500},
      {'id':'coverage','source':'counts','role':'boundary','claim':'growth','depends_on':['gain'],
       'question':'Which diets and ages have incomplete coverage?',
       'chart':{'intent':'matrix','unit':'Diet','values':list(counts_wide.columns[1:]),'data_level':'summary'},'min_area_mm2':1500}])
    spec={'question':'How do observed chick trajectories and endpoint gains differ by diet, within follow-up limits?',
      'claims':{'growth':{'required_roles':['primary','distribution','boundary'],
        'boundary':'Descriptive comparisons; endpoint gains are complete-pair summaries, not all 50 chicks or causal effect estimates.'}},'panels':panels}
    plan=plan_evidence({'longitudinal':d,'endpoint':endpoint,'counts':counts_wide},spec)
    write_json(OUT/'T01_evidence.spec.json',spec);write_json(OUT/'T01_evidence.plan.json',plan)
    if plan['status']!='ready':raise ValueError(plan['blockers'])
    # A second view of the same animals must not pass as independent validation.
    bad=json.loads(json.dumps(spec));bad['panels'][-2]['independence']={'from':'diet1','key':'Chick'}
    rejected=plan_evidence({'longitudinal':d,'endpoint':endpoint,'counts':counts_wide},bad)
    assert rejected['status']=='needs_resolution';write_json(OUT/'T01_rejected-independence.json',rejected)
    with figure_style(project=OUT/'ChickWeight-style.json'):
      enc=encodings_for([f'Diet {i}' for i in range(1,5)])
      write_json(OUT/'ChickWeight-palette-audit.json',audit_palette(enc));palette_preview(enc,OUT/'ChickWeight-palette.png')
      c=compose((180,183),[['diet1','diet2'],['diet3','diet4'],['gain','coverage']],
        panels={k:{'min_plot_mm':[58,32]} for k in ['diet1','diet2','diet3','diet4','gain','coverage']},
        margins_mm=(4,8,4,4),gap_mm=8,height_ratios=[1,1,1.03],balance_columns=True)
      for i in range(1,5):
        name=f'Diet {i}';a=c.axes[f'diet{i}'];e=enc[name];g=d[d.Diet==name]
        for _,unit in g.groupby('Chick',sort=True):
          a.plot(unit.Time,unit.weight,color=e['color'],lw=.5,alpha=.38)
        median=g.groupby('Time').weight.median()
        a.plot(median.index,median.values,color=e['color'],lw=1.35,linestyle=e['linestyle'],label=name)
        a.set(xlim=(-.6,21.6),ylim=(25,385),xticks=[0,7,14,21],yticks=[50,150,250,350],
          xlabel='Age (days)',ylabel='Body mass (g)')
        a.set_title(name,loc='left',color=e['color'],fontsize=8,pad=3)
      a=c.axes['gain']
      for i,(name,e) in enumerate(enc.items()):
        values=endpoint[endpoint.Diet==name].sort_values('Chick').gain.to_numpy()
        # Deterministic display jitter only in categorical x, never in gain.
        x=i+np.linspace(-.15,.15,len(values))
        a.scatter(x,values,s=16,color=e['color'],marker=e['marker'],lw=.3,edgecolor='white',label=name,zorder=3)
        a.plot([i-.23,i+.23],[np.median(values)]*2,color=role('ink'),lw=1)
      a.set(xticks=range(4),xticklabels=['1','2','3','4'],xlabel='Diet',ylabel='0–21-day gain (g)',
        xlim=(-.55,3.55),ylim=(0,350),yticks=[0,100,200,300])
      a.set_title('Endpoint gain',loc='left',fontsize=8,pad=3)
      a=c.axes['coverage']
      counts=count.pivot(index='Diet',columns='Time',values='observed').reindex(enc)
      # Coincident counts need a row for every identity; overlay hid two diets.
      a.imshow(counts.to_numpy(),aspect='auto',cmap='Blues',vmin=0,vmax=25,interpolation='nearest')
      for j in range(4):
        for k in range(counts.shape[1]):
          a.text(k,j,str(counts.iloc[j,k]),ha='center',va='center',fontsize=6.5,
            color='white' if counts.iloc[j,k]>=16 else role('ink'))
      a.set(xticks=[0,3,7,11],xticklabels=[str(t) for t in counts.columns[[0,3,7,11]]],
        yticks=range(4),yticklabels=['1','2','3','4'],xlabel='Age (days)',ylabel='Diet')
      a.set_title('Chicks observed',loc='left',fontsize=8,pad=3)
      qa,geo=export(c,'T01_evidence',d,
        f'R datasets::ChickWeight: {len(d)} observed weights from {d.Chick.nunique()} chicks. '
        f'Panels a–d retain all observed individual paths (thin) and age-specific medians (bold), not confidence bands. '
        f'Panel e includes {len(endpoint)} chicks observed at days 0 and 21, with all complete-pair gains and medians; '
        'no unobserved endpoint is imputed. Panel f is a discrete observed-age × diet matrix of actual observation counts; '
        'each cell is annotated, not a survival probability or an interpolated continuous time field. '
        'Diet color is stable; counts also use line/marker redundancy. Descriptive only; incomplete follow-up limits comparisons.',
        alignment={'row_groups':[['diet1','diet2'],['diet3','diet4'],['gain','coverage']],
          'column_groups':[['diet1','diet3','gain'],['diet2','diet4','coverage']]})
      check=audit_evidence_layout(plan,geo);assert check['status']=='PASS';write_json(OUT/'T01_evidence-coverage.json',check)
      assert sum(len(g) for _,g in d.groupby('Chick'))==578
      write_json(OUT/'T01_checks.json',{'rows_plotted':len(d),'units':int(d.Chick.nunique()),
        'complete_pairs':len(endpoint),'not_observed_day21':sorted(set(d.Chick)-set(endpoint.Chick)),
        'coverage':check,'excluded_longitudinal_rows':[]})


def native_r():
    result=run_r(Path(__file__).with_suffix('.R'),['figures',PKG,OUT],timeout=240,log=OUT/'R-runtime.json')
    print(result['stdout'][-700:])
    if result['returncode']!=0:raise RuntimeError(result['stderr'])
    before,after=(read(OUT/(f'T02_R_{v}.qa.json')) for v in ['before','final'])
    comparison=compare_revisions(before,after,required_panels=['response','endpoint'],
      required_classes={'response':['GeomLine'],'endpoint':['GeomPoint']})
    assert not comparison['errors']
    assert comparison['changes_requiring_justification']==['Named-series color mapping changed.']
    failures={v:compare_revisions(after,read(OUT/f'T02_R_{v}.qa.json')) for v in ['lost-layer','clipped','wrong-map']}
    assert all(c['status']=='regression' for c in failures.values())
    assert read(OUT/'T02_R_clipped.qa.json')['mark_issues']
    assert read(OUT/'T02_R_wrong-map.qa.json')['color_mapping_audit']['status']=='FAIL'
    write_json(OUT/'T02_revision-checks.json',{'native_R':True,'comparison':comparison,'negative_controls':failures,
      'raw_rows':84,'plants':12,'per_cell':3,'errors_waived':False})
    (OUT/'T02_R_final.caption.md').write_text(
      'R datasets::CO2: 84 uptake measurements from 12 plants, seven concentrations per plant, '
      'three plants in each origin/treatment cell. Thin lines are individual plants; bold lines are '
      'within-cell medians at each concentration. The right panel retains all 12 plants at 1000 µL/L. '
      'Blue/brown encode origin; solid/circle versus dashed/triangle encode treatment. '
      'This is a descriptive comparison, with no fitted curve, invented interval or significance test.\n',encoding='utf8')


def three_d():
    z=np.loadtxt(OUT/'volcano.csv',delimiter=',');x=np.arange(z.shape[1])*10.;y=np.arange(z.shape[0])*10.
    field=grid_field(x,y,z,limits=(90,200))
    with figure_style():
      norm,cmap,scale=continuous_scale(z,limits=(90,200),cmap='viridis')
      write_json(OUT/'T03_color-scale.json',scale)
      # Same full-resolution surface, two cameras, no smooth/fake craters.
      for version,azim in [('before',-60),('final',35)]:
        c=compose((180,118),[['surface','surface','map','bar'],['surface','surface','section','bar']],
          width_ratios=[1.6,1.6,1.6,.55],height_ratios=[1.25,1],gap_mm=4,
          panels={'surface':{'projection':'3d','plot_aspect':1,'min_plot_mm':[65,65]},
           'map':{'plot_aspect':600/860,'min_plot_mm':[28,38]},'section':{'min_plot_mm':[32,25]},
           'bar':{'min_plot_mm':[2,30],'panel_label':False}})
        ax=c.axes['surface'];surface=field_surface(ax,field,cmap=cmap,elev=37,azim=azim,
           box_aspect=(600,860,110*3))
        ax.set(xlabel='Grid x (m)',ylabel='Grid y (m)',zlabel='Elevation (m)',
          xlim=(0,600),ylim=(0,860),zlim=(90,200),xticks=[0,300,600],yticks=[0,400,800],zticks=[100,150,200])
        ax.tick_params(pad=0,labelsize=6.5);ax.xaxis.labelpad=8;ax.yaxis.labelpad=8;ax.zaxis.labelpad=5
        mesh=scalar_field(c.axes['map'],field,cmap='viridis')
        a=c.axes['map'];a.set_aspect('equal');a.set(xlabel='Grid x (m)',ylabel='Grid y (m)',
          xticks=[0,300,600],yticks=[0,400,800]);row=40
        a.axhline(y[row],color='white',ls='--',lw=.8)
        ax.plot(x,np.full(len(x),y[row]),z[row],color='white',lw=1.1,zorder=20)
        a=c.axes['section'];a.plot(x,z[row],color='#226D8D',lw=1.2)
        a.set(xlabel='Grid x (m)',ylabel='Elevation (m)',xlim=(0,600),ylim=(90,200),
          xticks=[0,300,600],yticks=[100,150,200]);a.set_title('y = 400 m',loc='left',fontsize=7.5,pad=3)
        c.figure.colorbar(mesh,cax=c.axes['bar'],label='Elevation (m)',ticks=[100,150,200])
        qa,geo=export(c,f'T03_terrain_{version}',pd.DataFrame(z),
          'R datasets::volcano: 87 × 61 observed elevations of Maungawhau, sampled on a 10 m grid. '
          'Axes use local grid coordinates, with no inferred compass orientation. Surface and map share 90–200 m '
          'viridis scale. All 5307 grid vertices are retained, no smoothing or interpolation. The 3D box uses '
          '3× vertical exaggeration, identically in both cameras. The dashed white map row and white surface '
          'transect locate y = 400 m; its original 61 elevations form panel c. The surface is an orientation aid; '
          'the map/section permit comparisons hidden by 3D occlusion.',axes=[c.axes['map']])
      before,after=(read(OUT/f'T03_terrain_{v}.qa.json') for v in ['before','final'])
      compare=compare_revisions(before,after,required_panels=['surface','map','section','bar'])
      assert compare['status']=='no_evidence_regression',compare
      write_json(OUT/'T03_checks.json',{'original_vertices':int(z.size),'transect_samples':len(x),
        'shared_limits':list(mesh.get_clim()),'vertical_exaggeration':3,'revision':compare,
        'camera_candidates':[-60,35],'camera_choice':35,'reason':'Viewed both cameras; +35 degrees exposes the crater that -60 hides.'})


def images():
    pixels=np.load(OUT/'IHC.npy');row=300
    entries={
      'whole':dict(pixels=pixels,pixel_size=1,unit='px',limits=None,scale_bar=100),
      'roi1':dict(pixels=pixels,pixel_size=1,unit='px',limits=None,scale_bar=40,crop=(80,240,80,280)),
      'roi2':dict(pixels=pixels,pixel_size=1,unit='px',limits=None,scale_bar=40,crop=(280,440,260,460))}
    with figure_style():
      c,records=image_plate((180,166),[['whole','whole','roi1'],['whole','whole','roi2'],['profile','profile','profile']],
        entries,panels={'profile':{'min_plot_mm':[120,27]}},height_ratios=[1,1,1.15],gap_mm=7,
        margins_mm=(4,8,5,4))
      link_roi(c,records,'whole','roi1',label='I',color='#F7D774')
      link_roi(c,records,'whole','roi2',label='II',color='#F7D774')
      a=c.axes['whole'];a.axhline(row+.5,color='white',ls='--',lw=.8)
      a=c.axes['profile']
      for i,(name,color,ls) in enumerate(zip(['R','G','B'],['#B65022','#207A52','#0072B2'],['-','--',':'])):
        a.plot(np.arange(512)+.5,pixels[row,:,i],label=name,color=color,ls=ls,lw=.8)
      a.set(xlim=(0,512),ylim=(0,260),xticks=[0,128,256,384,512],yticks=[0,128,255],
        xlabel='Source column (px)',ylabel='Native channel value (0–255)')
      a.legend(loc='upper left',bbox_to_anchor=(.01,1.22),ncol=3,handlelength=2)
      qa,geo=export(c,'T04_image_plate',pd.DataFrame(pixels.reshape(-1,3),columns=list('RGB')),
        'skimage.data.immunohistochemistry: CMMI colon-gland IHC image, FHL2/DAB with hematoxylin counterstain. '
        'All panels display unchanged native uint8 RGB pixels with nearest-neighbor display. Rectangles I and II '
        'mark exact source-pixel crops; the crop coordinates and source hash accompany the output. '
        'Physical calibration was not supplied, so bars are source pixels, not µm. ROI magnification may differ '
        'from the full field and is communicated by the pixel bars. Panel d plots the three raw channel values '
        'along source row 300 (white dashed line), without stain deconvolution, thresholding or protein-expression claims. '
        'This validates image-layout mechanics; it is not a biological quantification.',axes=[c.axes['profile']])
      for key,record in records.items():
        r0,r1,c0,c1=record['crop'];assert np.array_equal(pixels[r0:r1,c0:c1],c.axes[key].images[0].get_array())
      for i,line in enumerate(c.axes['profile'].lines):assert np.array_equal(line.get_ydata(),pixels[row,:,i])
      write_json(OUT/'T04_checks.json',{'native_RGB_unchanged':True,'physical_scale_unknown':True,
        'source_pixels':list(pixels.shape),'images':records,'profile_row':row,
        'profile_values':pixels[row].tolist(),'quantification_boundary':'raw display channels only'})


def volume():
    # Pinned official scikit-image dataset and registry checksum; urllib avoids
    # adding a global package solely for the optional pooch data downloader.
    import urllib.request
    import tifffile
    from skimage import data
    tif=OUT/'cells3d.tif'
    expected='afc7c7d80d38bfde09788b4064ac1e64ec14e88454ab785ebdc8dbba5ca3b222'
    url='https://gitlab.com/scikit-image/data/-/raw/2cdc5ce89b334d28f06a58c9f0ca21aa6992a5ba/cells3d.tif'
    if not tif.is_file():
        with urllib.request.urlopen(url,timeout=45) as response,tif.open('wb') as stream:
            while chunk:=response.read(1024*1024):stream.write(chunk)
    if hashlib.sha256(tif.read_bytes()).hexdigest()!=expected:raise ValueError('Volume download checksum mismatch')
    full=tifffile.imread(tif);a=full[:,1,70:190,80:200]
    origin=np.array([0,70*.26,80*.26]);spacing=np.array([.29,.26,.26]);upper=origin+(np.array(a.shape)-1)*spacing
    np.save(OUT/'cells3d-nuclei-ROI.npy',a)
    write_json(OUT/'T05_source.json',{'url':url,'sha256':expected,'documentation':data.cells3d.__doc__,
      'source_shape':list(full.shape),'channel':1,'crop_zyx':[[0,60],[70,190],[80,200]],
      'voxel_spacing_zyx_um':spacing.tolist(),'level':15000,'display_window':[0,30000],
      'voxels_above_display_window':int((a>30000).sum())})
    with figure_style():
      c=compose((180,138),[['mesh','xy','bar'],['xz','yz','bar']],
        width_ratios=[1.5,1,.4],height_ratios=[1.6,.9],gap_mm=6,
        panels={'mesh':{'projection':'3d','plot_aspect':1,'min_plot_mm':[58,58]},
          'xy':{'plot_aspect':1,'min_plot_mm':[26,26],
            'equal_unit_group':'orthogonal-um','data_span':[31.2,31.2]},
          'xz':{'plot_aspect':31.2/17.4,'min_plot_mm':[26,12],
            'equal_unit_group':'orthogonal-um','data_span':[17.4,31.2]},
          'yz':{'plot_aspect':31.2/17.4,'min_plot_mm':[26,12],
            'equal_unit_group':'orthogonal-um','data_span':[17.4,31.2]},
          'bar':{'min_plot_mm':[2,50],'panel_label':False}})
      ax=c.axes['mesh'];artist,mesh,vertices,faces=volume_isosurface(ax,a,spacing=spacing,origin=origin,level=15000)
      np.savez_compressed(OUT/'T05_mesh.npz',vertices_xyz_um=vertices,faces=faces)
      ax.set(xlabel='x (µm)',ylabel='y (µm)',zlabel='z (µm)',
        xticks=[25,35,45],yticks=[20,35,45],zticks=[0,8,16])
      ax.tick_params(pad=0,labelsize=6.5);ax.xaxis.labelpad=8;ax.yaxis.labelpad=8;ax.zaxis.labelpad=5
      for axis in [ax.xaxis,ax.yaxis,ax.zaxis]:
        axis.pane.set_facecolor((1,1,1,0));axis._axinfo['grid'].update(color=(.8,.82,.84,.5),linewidth=.35)
      z0,y0,x0=origin;z1,y1,x1=upper
      slices={'xy':(a[30],(x0-.13,x1+.13,y0-.13,y1+.13),'x (µm)','y (µm)','z = 8.70 µm'),
        'xz':(a[:,60,:],(x0-.13,x1+.13,z0-.145,z1+.145),'x (µm)','z (µm)','y = 33.80 µm'),
        'yz':(a[:,:,60],(y0-.13,y1+.13,z0-.145,z1+.145),'y (µm)','z (µm)','x = 36.40 µm')}
      for key,(pixels,extent,xlabel,ylabel,title) in slices.items():
        axy=c.axes[key];im=axy.imshow(pixels,origin='lower',extent=extent,vmin=0,vmax=30000,cmap='gray',interpolation='nearest')
        axy.set(xlabel=xlabel,ylabel=ylabel);axy.set_title(title,loc='left',fontsize=7.5,pad=3)
        axy.xaxis.set_major_locator(plt.MaxNLocator(3));axy.yaxis.set_major_locator(plt.MaxNLocator(3))
      cb=c.figure.colorbar(im,cax=c.axes['bar'],label='Native intensity (display window)',ticks=[0,15000,30000])
      cb.ax.set_yticklabels(['0','15000','≥30000'])
      qa,geo=export(c,'T05_volume',pd.DataFrame(a.reshape(-1,1),columns=['native_intensity']),
        f'Allen Institute/scikit-image cells3d nuclei channel (channel 1), ROI z[0:60], y[70:190], x[80:200]. '
        f'Distributed voxel spacing is (0.29,0.26,0.26) µm in z,y,x after the source data downsampling; '
        f'no additional data downsampling or smoothing is applied. Panel a is the explicitly chosen 15000-intensity '
        f'isovalue, linearly interpolated by marching cubes, with {mesh["vertices"]} vertices and {mesh["triangles"]} triangles. '
        f'Purple is material color with normal-based lighting (315° azimuth, 35° altitude), not intensity. '
        f'Lighting changes no vertices or faces. Surfaces can terminate at the ROI boundary; '
        f'this is not validated segmentation or a cell count. Panels b–d are exact orthogonal slices at the labeled '
        f'physical coordinates, equal physical mm per µm, and a shared 0–30000 raw-intensity display window. '
        f'{int((a>30000).sum())} ROI voxels exceed the display window and appear white; raw uint16 values and the '
        f'full ROI remain supplied. No artificial capping, hole filling, component selection or isotropic resampling.',
        axes=[c.axes['xy']])
      write_json(OUT/'T05_checks.json',{'mesh':mesh,'source_shape':list(full.shape),'roi_shape':list(a.shape),
        'native_voxels':int(a.size),'spacing_zyx_um':spacing.tolist(),'additional_resampling':False,
        'scientific_boundary':'Explicit isovalue, not validated segmentation/cell counting'})


stages={'inputs':inputs,'evidence':evidence,'r':native_r,'3d':three_d,'images':images,'volume':volume}
if args.stage=='all':
    for f in stages.values():f()
else:stages[args.stage]()
