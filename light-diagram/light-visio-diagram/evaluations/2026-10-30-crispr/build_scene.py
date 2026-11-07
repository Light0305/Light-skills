"""Advanced freeform reconstruction: all protein and nucleic-acid shapes native."""
from pathlib import Path
import hashlib
import json
import math
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=ROOT/'light-diagram-prompt/evaluations/2026-10-27/02-crispr/image-v3.png'
shutil.copy2(SOURCE,HERE/'source.png')
nodes,paths,edges=[],[],[]

def node(id,box,text='',fill='none',kind='text',**st):
    nodes.append({'id':id,'type':kind,'bbox':box,'text':text,'radius_px':15,
                  'style':{'fill':fill,'stroke':'none','font_px':30,'bold':False,**st}})
    return id

def blob(id,box,points,fill,secondary,stroke):
    node(id,box,fill=fill,kind='bezier',fill_secondary=secondary,stroke=stroke,stroke_px=2)
    nodes[-1]['points']=points

def curve(id,points,stroke,width=4,**extra):
    p={'id':id,'curve':'bezier','points':points,'arrow':0,
       'style':{'stroke':stroke,'stroke_px':width},**extra}
    paths.append(p)

def line(id,a,b,stroke,width=3):
    paths.append({'id':id,'points':[a,b],'arrow':0,'style':{'stroke':stroke,'stroke_px':width}})

def ribbon(id,points,dark,light,width=10):
    # Two editable strokes give restrained tubular depth, without embedding pixels.
    curve(id+'_outline',points,dark,width)
    curve(id+'_core',points,light,width*.55)

def dot(id,x,y,r=7):
    node(id,[x-r,y-r,2*r,2*r],fill='#15191e',kind='ellipse',stroke='#ffffff',stroke_px=2)

def junction(id,x,y):
    return node(id,[x-.1,y-.1,.2,.2],kind='junction')

def anchor(id,uv):
    x,y,w,h=next(n['bbox'] for n in nodes if n['id']==id)
    return [x+w*uv[0],y+h*uv[1]]

def edge(id,src,dst,points=None,curved=False,width=3,color='#161616',arrow=13):
    pts=[anchor(*src),*(points or []),anchor(*dst)]
    edges.append({'id':id,'source':{'node':src[0],'anchor':src[1]},
                  'target':{'node':dst[0],'anchor':dst[1]},'points':pts,
                  'curve':'bezier' if curved else 'polyline','arrow':arrow,
                  'style':{'stroke':color,'stroke_px':width}})

C=[.5,.5]
node('background',[0,0,1536,1024],fill='#ffffff',kind='rect')
node('dual_card',[25,80,472,276],kind='roundrect',stroke='#bec0c1',stroke_px=5)
node('chimeric_card',[25,697,472,204],kind='roundrect',stroke='#bec0c1',stroke_px=5)

blob('cas9',[574,232,571,540],[
 [779,318],[813,273],[870,232],[930,232],
 [986,227],[1009,250],[1032,271],
 [1053,289],[1070,274],[1105,305],
 [1140,335],[1163,412],[1116,464],
 [1141,493],[1156,533],[1136,577],
 [1116,602],[1102,623],[1117,643],
 [1158,705],[1096,748],[1042,764],
 [976,782],[919,764],[873,740],
 [834,717],[822,726],[794,726],
 [743,728],[704,702],[697,664],
 [690,633],[682,620],[644,610],
 [606,600],[570,573],[577,537],
 [582,493],[623,467],[660,443],
 [632,399],[660,358],[700,336],
 [728,321],[758,314],[779,318]],'#e7cf9e','#fff1d2','#bda16d')
blob('hnh',[825,352,174,134],[
 [830,374],[853,345],[900,350],[928,361],
 [954,372],[956,399],[978,413],
 [1002,431],[1002,460],[988,482],
 [955,475],[954,448],[922,444],
 [881,447],[842,434],[831,412],
 [823,399],[822,385],[830,374]],'#eca68f','#f8d0bd','#dda28b')
blob('ruvc',[807,570,201,146],[
 [812,596],[824,568],[858,563],[885,580],
 [905,591],[907,620],[934,624],
 [965,627],[1007,642],[1007,670],
 [1016,704],[962,720],[923,713],
 [884,715],[841,696],[825,676],
 [806,651],[805,621],[812,596]],'#8faec9','#d1e1ed','#8ea3b2')

node('crrna_label',[81,122,142,48],'crRNA',font_px=34,bold=True)
node('tracrrna_label',[103,280,153,44],'tracrRNA',font_px=33,bold=True)
node('chimera_label',[75,730,224,48],'Chimeric RNA',font_px=33,bold=True)
node('cas9_label',[873,281,128,56],'Cas9',font_px=45,bold=True)
node('hnh_label',[846,370,84,44],'HNH',font_px=32)
node('ruvc_label',[845,649,145,44],'RuvC-like',font_px=31)
node('complementary_label',[328,423,282,43],'Complementary strand',font_px=30)
node('noncomplementary_label',[320,601,330,43],'Noncomplementary strand',font_px=28)
node('product_label',[1269,430,257,44],'Double-strand break',font_px=29)
dot('complementary_anchor',581,513)
dot('noncomplementary_anchor',600,568)
junction('hnh_cut',923,463)
junction('ruvc_cut',925,598)
junction('cleavage_source',1207,555)
junction('cleavage_target',1277,555)

# Pairing rungs are native line shapes underneath the backbones.
for i,x in enumerate(range(202,310,15)):
    line(f'dual_pair_{i}',[x,204],[x,239],'#9fa89b',4)
for i,y in enumerate(range(231,295,16)):
    line(f'dual_hairpin_pair_{i}',[417,y],[444,y],'#8ba681',4)
for i,y in enumerate(range(796,858,16)):
    line(f'chimera_pair_{i}',[406,y],[434,y],'#8ba681',4)
for i,y in enumerate(range(400,481,20)):
    line(f'complex_hairpin_pair_{i}',[1045,y],[1075,y-1],'#8eab81',4)

purple,green='#773b9e','#2f8539'
ribbon('dual_crrna',[[50,191],[98,145],[108,204],[153,207],
 [176,208],[181,202],[203,202],
 [231,202],[271,203],[301,201],
 [354,204],[339,134],[381,125]],purple,'#b57bd1',11)
ribbon('dual_tracrrna',[[60,274],[77,270],[77,252],[101,265],
 [144,289],[152,241],[199,242],
 [236,242],[267,241],[295,243],
 [338,241],[339,295],[382,306],
 [405,312],[419,302],[418,283],
 [417,265],[417,245],[417,230],
 [419,219],[395,218],[400,189],
 [408,150],[462,158],[464,191],
 [469,214],[444,218],[444,230],
 [444,248],[443,273],[444,292],
 [444,307],[461,312],[474,324]],green,'#63b856',11)
ribbon('chimera_targeting',[[53,805],[95,763],[105,822],[153,822],
 [174,822],[176,815],[203,816],
 [228,816],[258,816],[280,816]],purple,'#b57bd1',11)
ribbon('chimera_scaffold',[[280,816],[348,812],[341,866],[383,867],
 [409,869],[408,853],[408,834],
 [408,815],[409,805],[408,795],
 [404,785],[385,781],[393,755],
 [406,717],[457,731],[455,758],
 [456,779],[434,786],[434,796],
 [435,813],[434,839],[435,857],
 [435,872],[449,875],[467,875]],green,'#63b856',11)

# Main RNA stem-loop and guide follow one continuous conceptual guide path.
ribbon('complex_scaffold',[[1042,508],[1050,499],[1049,484],[1047,467],
 [1047,446],[1046,418],[1045,396],
 [1046,387],[1023,383],[1024,357],
 [1022,315],[1085,315],[1093,349],
 [1101,377],[1074,382],[1075,396],
 [1076,420],[1075,451],[1076,477],
 [1076,514],[1089,523],[1112,531]],green,'#68bb5a',12)

# Straight duplex ends; rungs are not a measured sequence.
for i,x in enumerate(range(426,500,18)):
    line(f'left_dna_pair_{i}',[x,517],[x,560],'#a6abb0',5)
for i,x in enumerate(range(585,656,18)):
    line(f'entry_dna_pair_{i}',[x,517],[x,562],'#b0b0a6',5)
for i,x in enumerate(range(1088,1190,19)):
    line(f'right_dna_pair_{i}',[x,531],[x,575],'#a6abb0',5)
for i,x in enumerate(range(1298,1515,18)):
    if 1383<x<1417:continue
    line(f'product_pair_{i}',[x,517],[x,558],'#a6abb0',5)

guide_pts=[[654,514],[690,524],[704,538],[732,519],
 [769,492],[811,499],[850,499],
 [890,501],[927,499],[960,503],
 [995,506],[1003,527],[1042,508]]
for i,(x,yu,yl) in enumerate([(728,478,518),(746,469,508),(764,463,502),(783,459,500),
 (802,457,499),(821,457,499),(840,458,499),(859,459,500),(878,460,501),(896,462,502),
 (944,470,502),(962,476,504),(981,485,509)]):
    line(f'rna_dna_pair_{i}',[x,yu],[x,yl],'#bdac7c',5)
ribbon('complex_guide',guide_pts,purple,'#aa70c8',13)

upper_left=[[419,515],[448,515],[471,512],[486,514],
 [518,513],[532,545],[566,556],
 [545,543],[555,518],[581,514],
 [615,513],[638,516],[659,510],
 [697,500],[717,472],[755,462],
 [806,447],[859,454],[909,464]]
upper_right=[[938,468],[996,473],[1019,500],[1050,517],
 [1091,541],[1121,531],[1190,531]]
lower_left=[[419,563],[444,563],[472,563],[488,562],
 [524,559],[538,527],[565,519],
 [535,533],[558,565],[600,565],
 [628,565],[651,562],[676,574],
 [716,595],[730,615],[782,619],
 [834,625],[867,614],[910,600]]
lower_right=[[939,598],[980,600],[1006,598],[1034,581],
 [1083,548],[1104,570],[1143,578],
 [1163,580],[1176,579],[1190,580]]
ribbon('dna_lower_before_cut',lower_left,'#164f83','#337ab4',18)
ribbon('dna_lower_after_cut',lower_right,'#164f83','#337ab4',18)
ribbon('dna_upper_before_cut',upper_left,'#268fc4','#63c2ed',18)
ribbon('dna_upper_after_cut',upper_right,'#268fc4','#63c2ed',18)
for part,x1,x2 in [('left',1289,1388),('right',1413,1515)]:
    ribbon('product_upper_'+part,[[x1,514],[x1+(x2-x1)/3,514],[x1+2*(x2-x1)/3,514],[x2,514]],'#268fc4','#63c2ed',17)
    ribbon('product_lower_'+part,[[x1,561],[x1+(x2-x1)/3,561],[x1+2*(x2-x1)/3,561],[x2,561]],'#164f83','#337ab4',17)

for id,x,y in [('hnh',924,464),('ruvc',925,597),('product_top',1401,511),('product_bottom',1401,563)]:
    for j,angle in enumerate([-165,-130,-92,-52,-8]):
        a=math.radians(angle if 'bottom' not in id else -angle)
        line(f'{id}_cut_ray_{j}',[x+12*math.cos(a),y+12*math.sin(a)],
             [x+23*math.cos(a),y+23*math.sin(a)],'#ec4c2c',3)

# Assembly is alternative, not sequential: each card has its own curved arrow.
edge('dual_rna_assembly',('dual_card',[1,104/276]),('cas9',[(653-574)/571,(326-232)/540]),
     [[579,188],[620,250]],curved=True,width=7,color='#717171')
edge('chimeric_rna_assembly',('chimeric_card',[1,110/204]),('cas9',[(653-574)/571,(653-232)/540]),
     [[578,795],[623,724]],curved=True,width=7,color='#717171')
edge('label_complementary',('complementary_label',[.8,1]),('complementary_anchor',C),width=3,arrow=0)
edge('label_noncomplementary',('noncomplementary_label',[.7,0]),('noncomplementary_anchor',C),width=3,arrow=0)
edge('hnh_to_cut',('hnh_label',[.8,1]),('hnh_cut',C),width=3)
edge('ruvc_to_cut',('ruvc_label',[.48,0]),('ruvc_cut',C),width=3)
edge('double_strand_cleavage',('cleavage_source',C),('cleavage_target',C),width=10,color='#717171')

sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
scene={'schema_version':'1.0','font':'Times New Roman',
 'canvas':{'width_px':1536,'height_px':1024,'pixels_per_inch':100},
 'provenance':{'source':'source.png','source_sha256':sha,
   'method':'Manual control-point tracing and native cubic Bezier reconstruction. No raster components.',
   'scientific_source':'https://doi.org/10.1126/science.1225829',
   'intent':'Faithful conceptual reconstruction; no atomic structure or molecular-scale precision implied.',
   'declared_differences':['Smooth editable gradients replace raster protein texture and ribbon highlights.',
      'Control-point traces approximate irregular outlines; individual rung positions are schematic.']},
 'pages':[{'name':'01 CRISPR native replica','slug':'replica','mode':'faithful',
           'nodes':nodes,'paths':paths,'edges':edges,
           'draw_order':[n['id'] for n in nodes if n['id'] not in ('complementary_anchor','noncomplementary_anchor')]
                       +[p['id'] for p in paths]
                       +['complementary_anchor','noncomplementary_anchor']+[e['id'] for e in edges]}]}
(HERE/'scene.json').write_text(json.dumps(scene,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'source-manifest.json').write_text(json.dumps({
 'source_file':'source.png','source_sha256':sha,'original_file':str(SOURCE),
 'image_origin':'Actual image-v3 output of earlier light-diagram-prompt test, not Jinek paper Figure 5.',
 'paper':'Jinek et al. A Programmable Dual-RNA–Guided DNA Endonuclease in Adaptive Bacterial Immunity (2012)',
 'paper_doi':'10.1126/science.1225829','paper_url':'https://computingbiology.github.io/docs/jinek2012.pdf',
 'checks':['Two independent upper RNAs; continuous lower chimera; alternatives converge on Cas9.',
   'HNH points to complementary DNA cut; RuvC-like to noncomplementary DNA cut.',
   'DNA cut gaps and cleavage products; labels terminate on DNA, not RNA.'],
 'scope':'Advanced native Visio geometry test; schematic in-vitro cleavage, PAM and nucleotide orientation omitted as in reference.'
 },ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Wrote scene: {len(nodes)} nodes, {len(paths)} geometric paths, {len(edges)} glued edges.')
