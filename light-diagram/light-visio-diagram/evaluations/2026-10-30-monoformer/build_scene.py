"""Manual reconstruction of the actual image-v2-edit output, including source flaws."""
from pathlib import Path
import copy,hashlib,json

HERE=Path(__file__).resolve().parent
nodes,paths,edges=[],[],[]
def node(id,box,text='',fill='none',kind='roundrect',**style):
    nodes.append({'id':id,'type':kind,'bbox':box,'text':text,'radius_px':6,
                  'style':{'fill':fill,'stroke':'#27303b','stroke_px':1.3,'font_px':20,
                           'text_color':'#090d13',**style}})
    return id
def label(id,box,text,size=20,**st):
    return node(id,box,text,kind='text',stroke='none',font_px=size,**st)
def poly(id,pts,fill,**st):
    xs,ys=zip(*pts)
    node(id,[min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)],fill=fill,kind='polygon',**st)
    nodes[-1]['points']=[list(p) for p in pts]+[list(pts[0])]
    return id
def junction(id,x,y):
    return node(id,[x-.1,y-.1,.2,.2],kind='junction',stroke='none')
def line(id,pts,width=1.2,color='#263340',**st):
    paths.append({'id':id,'points':[list(p) for p in pts],'arrow':0,
                  'style':{'stroke':color,'stroke_px':width,**st}})
def anchor(id,uv):
    x,y,w,h=next(n['bbox'] for n in nodes if n['id']==id)
    return [x+w*uv[0],y+h*uv[1]]
def uv_for_point(id,point):
    x,y,w,h=next(n['bbox'] for n in nodes if n['id']==id)
    return [(point[0]-x)/w,(point[1]-y)/h]
def left_edge_anchor(id,corners,y):
    a,_,_,d=corners
    return uv_for_point(id,lerp(a,d,(y-a[1])/(d[1]-a[1])))
T,B,L,R,C=[.5,0],[.5,1],[0,.5],[1,.5],[.5,.5]
def edge(id,src,dst,bends=(),arrow=13,begin=0,width=2.1):
    edges.append({'id':id,'source':{'node':src[0],'anchor':src[1]},
      'target':{'node':dst[0],'anchor':dst[1]},
      'points':[anchor(*src),*[list(p) for p in bends],anchor(*dst)],
      'arrow':arrow,'begin_arrow':begin,'arrow_size':1,
      'style':{'stroke':'#101010','stroke_px':width}})
def lerp(a,b,t):return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]
def slab(id,corners,cols=6,rows=4,depth=8,fill='#94bce4',gradient=False):
    a,b,c,d=corners
    poly(id+'_front',[d,c,[c[0],c[1]+depth],[d[0],d[1]+depth]],'#7896b1',stroke_px=1)
    poly(id+'_side',[b,c,[c[0],c[1]+depth],[b[0],b[1]+depth]],'#7392ad',stroke_px=1)
    secondary=('#c5efff' if fill=='#9eddff' else '#b6d9f6') if not gradient else fill
    poly(id,corners,fill,fill_secondary=secondary,stroke_px=1.2)
    if gradient:
        for j in range(cols):
            t=(j+.5)/cols
            stops=[(105,80,173),(196,103,164),(241,166,89),(246,215,66)]
            k=min(2,int(t*3));local=t*3-k
            rgb=[round(stops[k][q]+(stops[k+1][q]-stops[k][q])*local) for q in range(3)]
            color='#'+''.join(f'{v:02x}' for v in rgb)
            poly(id+f'_color_{j}',[lerp(a,b,j/cols),lerp(a,b,(j+1)/cols),
                 lerp(d,c,(j+1)/cols),lerp(d,c,j/cols)],color,stroke='none')
    for j in range(1,cols):line(id+f'_grid_c{j}',[lerp(a,b,j/cols),lerp(d,c,j/cols)],.8)
    for j in range(1,rows):line(id+f'_grid_r{j}',[lerp(a,d,j/rows),lerp(b,c,j/rows)],.8)
    return id

node('background',[0,0,1774,887],fill='#ffffff',kind='rect',stroke='none')
for id,box,fill in [('transformer_panel',[16,246,302,558],'#e7e8ea'),
                     ('acm_panel',[713,12,428,198],'#e0effd'),
                     ('ffd_panel',[1427,28,334,832],'#e0e3e7')]:
    node(id,box,fill=fill,stroke='#66717d',stroke_px=1,dash_pattern=2)
    nodes[-1]['radius_px']=22
label('title_transformer',[29,252,275,38],'Transformer block',25)
label('title_acm',[728,13,398,36],'Attention Connection Module',25)
label('title_ffd',[1440,34,309,38],'Feature Fusion Decoder',25)

# All input icon elements are native polygons, rectangles and ellipses.
node('image_frame',[38,70,205,106],fill='#f5f7fb',kind='rect',stroke_px=1.2)
node('image_sky',[43,74,195,98],fill='#eef5fb',kind='rect',stroke='none')
for i,(x,y,w,h) in enumerate([(45,85,20,49),(65,92,10,44),(84,102,12,33),(98,115,8,25),
                              (208,85,28,51),(199,98,13,43),(183,118,9,26),(171,126,9,21)]):
    node('building_'+str(i),[x,y,w,h],fill='#9baac0',kind='rect',stroke='none')
poly('road',[[57,171],[119,132],[163,132],[228,171]],'#74808f',stroke='none')
for i,(x,y,w,h) in enumerate([(138,138,2,7),(137,151,4,10),(136,166,5,6)]):
    node('road_mark_'+str(i),[x,y,w,h],fill='#ffffff',kind='rect',stroke='none')
for i,(x,y,r) in enumerate([(49,137,5),(73,128,8),(90,129,5),(110,128,3),(167,125,4),(184,131,5),(207,128,8)]):
    node('tree_'+str(i),[x-r,y-r,2*r,2*r],fill='#8293a5',kind='ellipse',stroke='none')
    line('tree_trunk_'+str(i),[[x,y],[x,y+r+7]],1.3,'#8293a5')
label('image_label',[91,41,99,29],'Image I',20)
poly('cnn',[[279,76],[363,95],[363,151],[279,170]],'#d5d6dd',fill_secondary='#eeeeef')
label('cnn_label',[287,105,67,35],'CNN',21)
slab('patch_tokens',[[433,94],[513,94],[478,138],[391,138]],6,5,10)
label('patch_label',[395,59,136,29],'Patch tokens',20)
node('projection',[545,93,120,61],'Linear\nProjection','#d7d8df',fill_secondary='#e5e5e8',font_px=19)
edge('image_to_cnn',('image_frame',R),('cnn',L))
edge('cnn_to_patch',('cnn',R),('patch_tokens',left_edge_anchor('patch_tokens',[[433,94],[513,94],[478,138],[391,138]],123)))
edge('patch_to_projection',('patch_tokens',uv_for_point('patch_tokens',lerp([513,94],[478,138],(123.5-94)/44))),('projection',L))

stage_y=[233,381,528,675]
acm_y=[260,405,551,702]
ffd_y=[240,386,534,684]
planes=[[[546,293],[646,298],[620,333],[519,329]],
        [[545,439],[646,444],[620,480],[518,476]],
        [[544,585],[648,590],[621,627],[517,622]],
        [[543,735],[651,740],[621,784],[514,778]]]
fused=[[[1299,240],[1379,248],[1350,299],[1261,291]],
       [[1298,391],[1384,399],[1355,450],[1262,442]],
       [[1299,538],[1389,550],[1359,598],[1262,590]],
       [[1300,690],[1395,701],[1365,750],[1263,740]]]
for i in range(1,5):
    idx=i-1
    node(f'transformer_{i}',[497,stage_y[idx],200,55],f'Transformer {i}','#c8dceb',fill_secondary='#e2ebf3')
    slab(f'z_map_{i}',planes[idx])
    label(f'z_label_{i}',[652,min(p[1] for p in planes[idx])+7,36,29],f'Z{i}',20)
    a,b,_,_=planes[idx]
    top=lerp(a,b,(593-a[0])/(b[0]-a[0]))
    edge(f'transformer_to_z_{i}',(f'transformer_{i}',[.48,1]),(f'z_map_{i}',uv_for_point(f'z_map_{i}',top)),arrow=0)
    node(f'acm_{i}',[804,acm_y[idx],166,49],f'ACM {i}','#c9e5f4',fill_secondary='#dceef7')
    offset=[0,144,292,444][idx]
    for j,dx in enumerate([0,82],1):
        slab(f'att_{i}_{j}',[[831+dx,320+offset],[883+dx,322+offset],
                             [858+dx,351+offset],[808+dx,350+offset]],5,4,8,fill='#9eddff')
        edge(f'acm_to_tile_{i}_{j}',(f'acm_{i}',[.29 if j==1 else .79,1]),
             (f'att_{i}_{j}',[.65,0]),arrow=0,width=1.4)
    node(f'ffd_{i}',[1096,ffd_y[idx],144,73],f'FFD {i}','#d3d3df',fill_secondary='#e4e3e9')
    slab(f'fused_{i}',fused[idx])
    edge(f'ffd_to_fused_{i}',(f'ffd_{i}',R),(f'fused_{i}',left_edge_anchor(f'fused_{i}',fused[idx],ffd_y[idx]+36.5)))
    sy=stage_y[idx]+15
    edge(f'direct_skip_{i}',(f'transformer_{i}',[1,15/55]),(f'ffd_{i}',[0,10/73]))
    edge(f'z_to_acm_{i}',(f'transformer_{i}',[1,15/55]),(f'acm_{i}',L),[(728,sy),(728,acm_y[idx]+24.5)])
    edge(f'acm_output_1_{i}',(f'acm_{i}',R),(f'ffd_{i}',[0,45/73]))
    jy=ffd_y[idx]+66
    junction(f'floating_output_{i}',979,jy)
    edge(f'acm_output_2_{i}',(f'floating_output_{i}',C),(f'ffd_{i}',[0,66/73]))

# All main backbone nodes now exist.
edge('projection_to_encoder',('projection',B),('transformer_1',[.54,0]))
for i in range(1,4):
    _,_,c,d=planes[i-1];bottom=lerp(d,c,(593-d[0])/(c[0]-d[0]));bottom[1]+=8
    edge(f'backbone_{i}_{i+1}',(f'z_map_{i}_front',uv_for_point(f'z_map_{i}_front',bottom)),(f'transformer_{i+1}',[.48,0]))
node('residual_unit',[745,811,229,51],'Residual Block Unit','#d7d7e1',fill_secondary='#e7e6ec',font_px=19)
_,_,c,d=planes[3];bottom=lerp(d,c,(591.5-d[0])/(c[0]-d[0]));bottom[1]+=8
edge('z4_to_residual',('z_map_4_front',uv_for_point('z_map_4_front',bottom)),('residual_unit',L),[(591.5,836.5)])
edge('residual_to_ffd4',('residual_unit',R),('ffd_4',B),[(1168,836.5)])
label('state_x4',[1010,809,50,30],'X4',20)
for lower in [4,3,2]:
    edge(f'decoder_{lower}_{lower-1}',(f'ffd_{lower}',T),(f'ffd_{lower-1}',B))
    label(f'state_x{lower-1}',[1175,[0,0,342,490,636][lower],45,29],f'X{lower-1}',20)
slab('depth',[[1220,76],[1373,80],[1338,146],[1168,145]],12,6,10,fill='#b198df',gradient=True)
label('depth_label',[1218,40,113,31],'Depth D',22)
label('state_x0',[1227,194,45,30],'X0',20)
edge('ffd1_to_depth',('ffd_1',[.88,0]),('depth_front',uv_for_point('depth_front',[1222.72,155.32])),[(1222.72,176)])

# Main-view bus is reproduced visually; independent-level routing replaces it on page 2.
line('ambiguous_common_bus',[[728,248],[728,727]],2,'#101010')
line('leader_transformer',[[318,398],[497,410]],1.3,'#425269',dash_pattern=2)
line('leader_acm',[[991,210],[991,344],[966,344]],1.3,'#425269',dash_pattern=2)
line('leader_ffd',[[1427,367],[1364,407]],1.3,'#425269',dash_pattern=2)

# Transformer inset, including the reverse arrowhead present at a residual source.
for id,box,text in [('tr_input',[114,749,118,40],'Input'),('tr_norm1',[114,685,118,40],'Norm'),
                     ('tr_msa',[114,620,118,40],'MSA'),('tr_norm2',[114,493,118,39],'Norm'),
                     ('tr_mlp',[114,425,118,40],'MLP'),('tr_output',[114,296,118,39],'Output')]:
    node(id,box,text,'#d5e8f8',fill_secondary='#e9f3fc')
node('tr_sum1',[152,554,42,43],'+','#dcecf9',kind='ellipse',font_px=27)
node('tr_sum2',[152,360,42,43],'+','#dcecf9',kind='ellipse',font_px=27)
seq=['tr_input','tr_norm1','tr_msa','tr_sum1','tr_norm2','tr_mlp','tr_sum2','tr_output']
for a,b in zip(seq,seq[1:]):edge(a+'_to_'+b,(a,T),(b,B))
edge('tr_residual1',('tr_input',L),('tr_sum1',[.05,.78]),[(76,769),(76,587.54)])
edge('tr_residual2',('tr_sum1',L),('tr_sum2',L),[(70,575.5),(70,381.5)],begin=13)

# ACM inset, role-level attention detail.
label('acm_detail_z',[727,112,26,29],'Z',20)
junction('acm_detail_fork',783,126.5)
node('acm_detail_conv',[815,66,67,42],'Conv','#dcebf7',font_px=19)
node('acm_position',[916,61,89,51],'Position\nAttention','#dcebf7',font_px=18)
node('acm_channel',[900,141,103,50],'Channel\nAttention','#dcebf7',font_px=18)
slab('detail_ap',[[1062,72],[1093,73],[1072,101],[1040,100]],5,4,7,fill='#9eddff')
slab('detail_ac',[[1062,152],[1093,153],[1072,182],[1040,181]],5,4,7,fill='#9eddff')
label('detail_ap_label',[1095,74,43,28],'A_p',19)
label('detail_ac_label',[1095,156,43,28],'A_c',19)
edge('detail_z_to_fork',('acm_detail_z',R),('acm_detail_fork',C),arrow=0)
edge('fork_to_position',('acm_detail_fork',C),('acm_detail_conv',L),[(783,87)])
edge('conv_to_position',('acm_detail_conv',R),('acm_position',L))
edge('position_to_ap',('acm_position',R),('detail_ap',L))
edge('fork_to_channel',('acm_detail_fork',C),('acm_channel',L),[(783,166.5)])
edge('channel_to_ac',('acm_channel',R),('detail_ac',L))

# FFD inset. Replica explicitly preserves the extra raw-attention-to-final-sum edge.
for id,box,text in [('ff_output',[1557,82,102,39],'Output'),('ff_tanh',[1544,266,124,39],'tanh'),
 ('ff_cn',[1527,439,159,39],'Channel Norm'),('ff_l2',[1534,551,143,39],'L2-Norm'),
 ('ff_conv',[1559,678,96,37],'Conv'),('ff_reweight',[1519,736,177,55],'Attention\nReweighting')]:
    node(id,box,text,'#d8e9f8',fill_secondary='#e9f3fb',font_px=19)
for id,box,text in [('ff_final',[1588,148,38,39],'+'),('ff_product',[1588,207,38,38],'×'),
 ('ff_beta',[1588,329,38,38],'+'),('ff_gamma',[1588,382,38,38],'×'),
 ('ff_alpha',[1588,495,38,38],'×'),('ff_u',[1588,618,38,38],'+')]:
    node(id,box,text,'#edf6fc',kind='ellipse',font_px=26)
for id,box,text in [('ff_z',[1526,824,28,28],'Z'),('ff_ac',[1581,823,45,30],'A_c'),
                     ('ff_ap',[1658,824,38,28],'A_p'),('ff_x',[1464,648,30,30],'X'),
                     ('ff_scalar_alpha',[1662,498,66,28],'alpha'),
                     ('ff_scalar_gamma',[1656,385,74,28],'gamma'),('ff_scalar_beta',[1667,330,56,28],'beta')]:
    label(id,box,text,19)
for id,uv in [('ff_z',[.15,1]),('ff_ac',[.5,1]),('ff_ap',[.88,1])]:
    edge(id+'_to_reweight',(id,T),('ff_reweight',uv))
seq=['ff_reweight','ff_conv','ff_u','ff_l2','ff_alpha','ff_cn','ff_gamma','ff_beta','ff_tanh','ff_product','ff_final','ff_output']
for a,b in zip(seq,seq[1:]):edge(a+'_to_'+b,(a,T),(b,B))
edge('decoder_x_to_u',('ff_x',R),('ff_u',B),[(1607,663)])
for scalar,target in [('alpha','ff_alpha'),('gamma','ff_gamma'),('beta','ff_beta')]:
    edge('scalar_'+scalar,('ff_scalar_'+scalar,L),(target,R))
edge('ff_u_to_product',('ff_u',R),('ff_product',R),[(1719,637),(1719,226)])
edge('ff_u_residual',('ff_u',L),('ff_final',L),[(1461,637),(1461,167.5)],begin=13)
edge('ff_wrong_raw_bypass',('ff_reweight',R),('ff_final',R),[(1741,763.5),(1741,167.5)])

replica={'name':'01 Generated reference replica','slug':'replica','mode':'faithful',
         'nodes':nodes,'paths':paths,'edges':edges}
corrected=copy.deepcopy(replica)
corrected.update(name='02 Corrected scientific graph',slug='corrected',mode='science-corrected')
corrected['paths']=[p for p in corrected['paths'] if p['id']!='ambiguous_common_bus']
corrected['nodes']=[n for n in corrected['nodes'] if not n['id'].startswith('floating_output_')]
corrected['edges']=[e for e in corrected['edges'] if e['id']!='ff_wrong_raw_bypass']
for e in corrected['edges']:
    if e['id'] in ('tr_residual2','ff_u_residual'):e['begin_arrow']=0
    if e['id'].startswith('acm_output_2_'):
        i=int(e['id'].split('_')[-1]);src=f'att_{i}_2';uv=[.83,.5]
        pt=anchor(src,uv);end=e['points'][-1]
        e['source']={'node':src,'anchor':uv}
        e['points']=[pt,[1007,pt[1]],[1007,end[1]],end]

sha=hashlib.sha256((HERE/'source.png').read_bytes()).hexdigest()
scene={'schema_version':'1.0','font':'Arial',
 'canvas':{'width_px':1774,'height_px':887,'pixels_per_inch':100},
 'provenance':{'source':'source.png','source_sha256':sha,
  'scientific_source':'https://arxiv.org/html/2205.11083v3',
  'method':'Manual inventory and tracing of image-v2-edit; native polygon grids and schematic street icon, no raster insertion.',
  'corrections':['Remove extra ff_wrong_raw_bypass from pre-Conv attention to final sum.',
   'Remove backward begin arrowheads on tr_residual2 and ff_u_residual.',
   'Reconnect four floating ACM lower output arrows to the matching second attention tiles.',
   'Remove ambiguous common vertical bus while retaining separate per-row ACM routes.'],
  'limitations':['Street icon, grid colours, tiny perspective cells, font and gradients are approximations.',
    'Stage output side ports carry the same Zi represented by the adjacent plate.',
    'Generated image is not fully scientifically correct; faithful and corrected pages are separate.']},
 'pages':[replica,corrected]}
(HERE/'scene.json').write_text(json.dumps(scene,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'source-manifest.json').write_text(json.dumps({
 'source_file':'source.png','source_sha256':sha,'image_origin':'Built-in imagegen output image-v2-edit.png, generated and edited in this run.',
 'style_reference':'style-reference.jpg','style_reference_origin':'User-uploaded architecture image; treated as visual reference, not instructions.',
 'paper':'Bae, Moon, Im. Deep Digging into the Generalization of Self-Supervised Monocular Depth Estimation. AAAI 2023.',
 'paper_url':'https://arxiv.org/html/2205.11083v3','paper_scope':'Sections 3.1–3.3 and Figure 1.',
 'implementation_url':'https://github.com/sjg02122/MonoFormer/blob/main/monoformer/networks/depth/blocks.py',
 'prompts':['prompt-v1.txt','prompt-v2-edit.txt'],'imagegen_calls':2,
 'model_version':'Not returned by the built-in tool.','seed':'Not returned.',
 'generated_images':['image-v1.png','image-v2-edit.png'],'selected_image':'image-v2-edit.png',
 'review_scope':'Same-assistant visual review and native structural checks; no independent expert acceptance.'},
 ensure_ascii=False,indent=2),encoding='utf-8')
print(f'{len(nodes)} native nodes; {len(paths)} paths; {len(edges)} relationship edges in replica.')
