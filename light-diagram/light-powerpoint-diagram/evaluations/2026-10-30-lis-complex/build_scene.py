"""Manually authored geometry inventory for the new generated Li–S reference.

This module's helpers do not recognize the image. Actual measured placement is
added after inspecting source.png. Geometry coordinates use a normalized 1800
by 1200 tracing canvas and are scaled to the generated image dimensions.
"""
from pathlib import Path
import hashlib,json,math
import random,sys
from PIL import Image

HERE=Path(__file__).resolve().parent
NODES=[];PATHS=[];EDGES=[];ORDER=[]

def node(nid,kind,box,fill='none',stroke='none',text='',font=18,bold=False,**extra):
    style={'fill':fill,'stroke':stroke,'stroke_px':1.3,'font_px':font,'bold':bold,'text_color':'#142530'}
    style.update(extra.pop('style',{}));n={'id':nid,'type':kind,'bbox':list(box),'text':text,'style':style,**extra};NODES.append(n);ORDER.append(nid);return n
def text(nid,content,box,font=18,bold=False,color='#142530',align=1):
    return node(nid,'text',box,text=content,font=font,bold=bold,style={'text_color':color,'align':align})
def poly(nid,pts,fill,stroke='#5b6a70',**extra):
    xs,ys=zip(*pts);p=[list(v) for v in pts]
    if p[-1]!=p[0]:p.append(p[0])
    return node(nid,'polygon',[min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)],fill,stroke,points=p,**extra)
def line(nid,pts,color='#526675',width=1.4,curve='polyline',arrow=0,dashed=False):
    p={'id':nid,'points':[list(v) for v in pts],'curve':curve,'arrow':arrow,'style':{'stroke':color,'stroke_px':width}}
    if dashed:p['style']['dash_pattern']=2
    PATHS.append(p);ORDER.append(nid);return p
def sphere(nid,x,y,r,color='#e6b945',stroke='#b08a28',highlight=True):
    n=node(nid,'ellipse',[x-r,y-r,2*r,2*r],color,stroke,style={'fill_secondary':shade(color,.75),'stroke_px':.8})
    if highlight:node(nid+'_shine','ellipse',[x-r*.5,y-r*.62,r*.58,r*.32],shade(color,1.35),'none')
    return n
def shade(c,f):
    rgb=[int(c[i:i+2],16) for i in (1,3,5)]
    return '#'+''.join(f'{min(255,round(v*f)):02x}' for v in rgb)
def ion(nid,x,y,r=9):
    n=sphere(nid,x,y,r,'#83bde8','#4c86ac',False)
    return n
def chain(nid,x,y,count=5,r=6,angle=0,color='#e5b947',highlight=True):
    coords=[]
    for i in range(count):
        t=angle+(i%2)*.38;coords.append((x+i*r*1.65*math.cos(angle),y+i*r*1.65*math.sin(angle)+(i%2)*r*.55))
    for i in range(len(coords)-1):line(nid+f'_bond_{i}',[coords[i],coords[i+1]],'#a47b28',r*.7)
    for i,(px,py) in enumerate(coords):sphere(nid+f'_s_{i}',px,py,r,color,'#b48b29',highlight)
    return coords
def plate(nid,x,y,w,h,depth=18,fill='#c3d1dc',edge='#748795',dx=15):
    front=node(nid,'rect',[x,y,w,h],fill,edge,style={'fill_secondary':shade(fill,.84)})
    poly(nid+'_top',[(x,y),(x+dx,y-depth),(x+w+dx,y-depth),(x+w,y)],shade(fill,1.1),edge)
    poly(nid+'_side',[(x+w,y),(x+w+dx,y-depth),(x+w+dx,y+h-depth),(x+w,y+h)],shade(fill,.75),edge)
    return front
def port(nid,x,y):return node(nid,'junction',[x-.5,y-.5,1,1],'none','none')
def edge(nid,source,target,points,color='#3b6074',width=2.2,arrow=13,dashed=False):
    sm=next(n for n in NODES if n['id']==source);tm=next(n for n in NODES if n['id']==target)
    def uv(n,p):
        x,y,w,h=n['bbox'];return [(p[0]-x)/w,(p[1]-y)/h]
    e={'id':nid,'source':{'node':source,'anchor':uv(sm,points[0])},'target':{'node':target,'anchor':uv(tm,points[-1])},'points':[list(p) for p in points],'curve':'polyline','arrow':arrow,'style':{'stroke':color,'stroke_px':width}}
    if dashed:e['style']['dash_pattern']=2
    EDGES.append(e);ORDER.append(nid);return e
def panel(nid,letter,title,box):
    x,y,w,h=box;node(nid,'roundrect',box,'#ffffff','#d4dde3',radius_px=14,style={'stroke_px':1.3})
    text(nid+'_letter',letter,[x+13,y+9,28,32],26,True)
    text(nid+'_title',title,[x+49,y+10,w-65,31],23,True,align=0)

def save_scene():
    with Image.open(HERE/'source.png') as im:w,h=im.size
    sx,sy=w/1800,h/1200
    for n in NODES:
        n['bbox']=[n['bbox'][0]*sx,n['bbox'][1]*sy,n['bbox'][2]*sx,n['bbox'][3]*sy]
        if 'points' in n:n['points']=[[x*sx,y*sy] for x,y in n['points']]
        n['style']['font_px']*=min(sx,sy);n['style']['stroke_px']*=min(sx,sy)
        if 'radius_px' in n:n['radius_px']*=min(sx,sy)
    for p in PATHS+EDGES:
        p['points']=[[x*sx,y*sy] for x,y in p['points']];p['style']['stroke_px']*=min(sx,sy)
    source_hash=hashlib.sha256((HERE/'source.png').read_bytes()).hexdigest()
    s={'schema_version':'1.0','font':'Arial','canvas':{'width_px':w,'height_px':h,'pixels_per_inch':96},'provenance':{'source':'source.png','source_sha256':source_hash,'scientific_source':'https://doi.org/10.1039/D4TA03930K','method':'Manual inspection and measured reconstruction of the newly generated four-panel reference. Native geometry, not automatic tracing.','corrections':['Replace Li loss to Passivation with a separate Shuttle to Passivation branch.','Route the anode interface callout from the visible Li anode rather than the separator.'],'limitations':['Surface texture, exact particle placements, isometric geometry, colours and type differ from the generated reference.','Particle and molecular icons are schematic, not atomistic models or measurements.','Flux endpoints are mostly transparent path ports; they do not establish whole-layer grouping or dragging.']},'pages':[{'name':'Li-S multiscale mechanism with explicit corrections','slug':'corrected','mode':'science-corrected','nodes':NODES,'paths':PATHS,'edges':EDGES,'draw_order':ORDER}]}
    (HERE/'scene.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'nodes':len(NODES),'paths':len(PATHS),'edges':len(EDGES),'objects':len(ORDER),'canvas':[w,h]}))

def cell_architecture():
    rng=random.Random(21031)
    poly('liquid_top',[(110,169),(215,111),(1110,131),(1074,188)],'#e8f8ff','#91b9ce')
    poly('liquid_front',[(110,169),(1074,188),(1074,585),(110,539)],'#d9f1fb','#90b7ce',style={'fill_secondary':'#c7e6f5'})
    # A few native waves carry the water-like rendering without a raster fill.
    for j in range(13):
        yy=194+j*25
        line(f'liquid_wave_{j}',[(143,yy),(220,yy-17),(320,yy+20),(522,yy+8)],'#cae9f7',5,'bezier')
    poly('li_anode',[(40,165),(95,166),(95,552),(40,548)],'#b4c7dc','#697d92',style={'fill_secondary':'#809ab6'})
    poly('li_anode_top',[(40,165),(160,97),(208,103),(95,166)],'#cfdfeb','#697d92')
    poly('li_anode_side',[(95,166),(208,103),(211,484),(95,552)],'#91acbf','#697d92',style={'fill_secondary':'#c5dce8'})
    poly('liquid_glass',[(111,170),(213,115),(216,479),(111,540)],'#a9d9ed','#ebf7fc',style={'stroke_px':3,'fill_secondary':'#d8eff7'})
    # Porous cathode, punctuated with electrolyte pores and sulfur particles.
    poly('carbon_host',[(701,153),(1067,132),(1070,568),(690,573)],'#414b4d','#344044',style={'fill_secondary':'#293539'})
    poly('carbon_top',[(701,153),(752,127),(1100,124),(1067,154)],'#606768','#3f4a4d')
    for row in range(9):
        for col in range(6):
            x=731+col*58+rng.uniform(-9,9);y=181+row*43+rng.uniform(-8,8)
            rr=rng.uniform(14,24)
            node(f'carbon_pore_{row}_{col}','ellipse',[x-rr,y-rr*.72,rr*2,rr*1.5],'#afc5d0','#59656b',style={'stroke_px':6,'fill_secondary':'#2f414b'})
            if (row+col)%3!=1:sphere(f'cathode_sulfur_{row}_{col}',x+2,y+3,rr*.71,'#e5b52d','#a67f24')
            if (row*3+col)%4==0:ion(f'cathode_li_{row}_{col}',x+rr*.5,y-rr*.4,6)
    # Separator is an oblique, fibrous beige layer with a teal cathode coating.
    poly('separator_back',[(530,178),(617,113),(664,119),(649,579),(539,570)],'#d6c7a0','#a79b7e',style={'fill_secondary':'#f4ecd4'})
    poly('separator_coating',[(620,164),(694,111),(694,519),(647,579)],'#3c9b99','#357d80',style={'fill_secondary':'#75c5bd'})
    for row in range(12):
        for col in range(3):
            x=553+col*24+rng.uniform(-3,3);y=187+row*31-col*14
            node(f'sep_pore_{row}_{col}','ellipse',[x-10,y-12,20,25],'#9cb9b9','#f4ead1',style={'stroke_px':5})
            line(f'sep_fibre_{row}_{col}',[(x-14,y-16),(x+7,y-21),(x+13,y+4),(x+21,y+10)],'#fff4d9',3.3,'bezier')
    for row in range(15):
        for col in range(3):
            x=651+col*12+rng.uniform(-2,2);y=170+row*25-col*7
            sphere(f'coating_site_{row}_{col}',x,y,4.3,'#399c9a','#267579',False)
    for j in range(8):chain(f'adsorbed_chain_{j}',659+(j%2)*10,175+j*45,3+(j%2),5.5,angle=.4)
    poly('collector',[(1075,178),(1102,161),(1102,594),(1075,593)],'#a0a7ae','#5e6971',style={'fill_secondary':'#707a83'})
    poly('collector_side',[(1102,161),(1148,109),(1150,541),(1102,594)],'#87939c','#5e6971',style={'fill_secondary':'#bbc1c7'})
    for j in range(29):
        x=rng.uniform(175,519);y=rng.uniform(191,526)
        ion(f'li_ion_a_{j}',x,y,rng.uniform(4.5,7))
    for j in range(5):chain(f'dissolved_chain_a_{j}',193+j*39,304+j*41,4+(j%2),5.2,angle=.1)
    # Route each physical transport between separate, explicit endpoint ports.
    for j,(x,y,ex) in enumerate([(262,254,490),(225,293,353),(328,334,507),(305,416,502),(529,238,590),(528,439,591)]):
        port(f'li_route_a_{j}_s',x,y);port(f'li_route_a_{j}_t',ex,y)
        edge(f'li_transport_a_{j}',f'li_route_a_{j}_s',f'li_route_a_{j}_t',[(x,y),(ex,y)],'#128be0',4)
    for j,(x,y,ex) in enumerate([(529,371,287),(526,437,271),(538,488,396),(730,303,683),(715,378,676)]):
        port(f'ps_route_a_{j}_s',x,y);port(f'ps_route_a_{j}_t',ex,y-3)
        edge(f'polysulfide_transport_a_{j}',f'ps_route_a_{j}_s',f'ps_route_a_{j}_t',[(x,y),(ex,y-3)],'#9b43cf',2.8,dashed=True)
    # External circuit is above the electrolyte, from anode to collector.
    port('wire_anode_terminal',128,126);port('wire_cathode_terminal',1075,144)
    edge('external_electron_path','wire_anode_terminal','wire_cathode_terminal',[(128,126),(128,81),(1075,81),(1075,144)],'#b85419',3.2,arrow=0)
    node('load','roundrect',[574,66,74,35],'#efa26c','#b65a29',radius_px=4,style={'fill_secondary':'#ca7b47'})
    port('electron_arrow_s',664,63);port('electron_arrow_t',723,63)
    edge('electron_direction','electron_arrow_s','electron_arrow_t',[(664,63),(723,63)],'#d46612',3.3)
    text('electron_label','e- during discharge',[727,31,260,35],25,True,'#bd540b',0)
    for j,(label,x,yy) in enumerate([('Li+',349,199),('Li+',366,287),('Li+',350,397)]):text(f'li_label_a_{j}',label,[x,yy,56,27],21,True,'#075a9c')
    text('shuttle_label','Polysulfide shuttle',[210,473,237,30],22,True,'#8533b2')
    for nid,label,box,point in [
        ('anode_label','Li anode',[27,592,129,34],(70,518)),
        ('electrolyte_label','Electrolyte',[263,600,154,34],(343,542)),
        ('separator_label','Functional separator',[490,603,246,34],(598,551)),
        ('cathode_label','Sulfur / carbon cathode',[753,601,291,34],(823,559)),
        ('collector_label','Current\ncollector',[1054,600,103,56],(1120,536))]:
        n=text(nid,label,box,21,True);cx=box[0]+box[2]/2
        line(nid+'_leader',[(cx,box[1]),point],'#40484c',1.6)
        sphere(nid+'_dot',point[0],point[1],4,'#243139','#ffffff',False)

def sulfur_conversion():
    for i in range(8):
        a=-math.pi/2+i*math.pi/4
        sphere(f's8_ring_{i}',1477+52*math.cos(a),119+42*math.sin(a),15,'#e6b623','#a48320')
    text('s8_label','S₈ (solid)',[1557,106,175,38],25,True)
    node('soluble_band','roundrect',[1225,216,494,133],'#ece5fb','none',radius_px=20)
    text('soluble_label','Soluble polysulfides',[1281,219,385,33],25,True)
    for nid,label,x,y,num in [('ps8','Li₂S₈',1248,269,8),('ps6','Li₂S₆',1427,276,6),('ps4','Li₂S₄',1610,283,4)]:
        chain(nid,x,y,num,9.8,angle=.035)
        text(nid+'_label',label,[x-7,309,145,33],24,True)
    for i,(dx,dy,r) in enumerate([(-42,3,13),(-20,-12,14),(4,-20,16),(28,-5,15),(48,7,12),(-8,12,15),(20,15,13)]):sphere(f'li2s2_{i}',1477+dx,458+dy,r)
    text('li2s2_label','Li₂S₂ (solid)',[1557,443,187,38],25,True)
    for row in range(4):
        for col in range(5):
            x=1421+col*25+(row%2)*13;y=555+row*19
            sphere(f'li2s_s_{row}_{col}',x,y,14,'#e3b023','#a48320')
            if (row+col)%2==0:ion(f'li2s_li_{row}_{col}',x+12,y-8,8)
    text('li2s_label','Li₂S (solid)',[1571,565,169,39],25,True)
    text('overall_reaction','S₈ + 16Li ⇌ 8Li₂S',[1341,652,371,39],28,True)
    for i,(y0,y1) in enumerate([(181,210),(353,421),(500,541)]):
        port(f'reaction_{i}_s',1477,y0);port(f'reaction_{i}_t',1477,y1)
        edge(f'discharge_stage_{i}',f'reaction_{i}_s',f'reaction_{i}_t',[(1477,y0),(1477,y1)],'#18202c',4)
    text('discharge_label','Discharge',[1298,369,176,34],25,True)
    port('charge_route_s',1702,604);port('charge_route_t',1748,135)
    edge('charge_return','charge_route_s','charge_route_t',[(1702,604),(1774,604),(1774,135),(1748,135)],'#aa49c8',4)
    text('charge_label','Charge',[1638,385,100,31],24,True,'#8633aa')

def blob(nid,x,y,rx,ry,fill,stroke,width=1.3,seed=0):
    rng=random.Random(seed);pts=[]
    for i in range(9):
        a=2*math.pi*i/9;f=rng.uniform(.83,1.1);pts.append((x+rx*f*math.cos(a),y+ry*f*math.sin(a)))
    control=[pts[0]]
    for i in range(len(pts)):
        p0=pts[(i-1)%len(pts)];p1=pts[i];p2=pts[(i+1)%len(pts)];p3=pts[(i+2)%len(pts)]
        control.extend([(p1[0]+(p2[0]-p0[0])/6,p1[1]+(p2[1]-p0[1])/6),(p2[0]-(p3[0]-p1[0])/6,p2[1]-(p3[1]-p1[1])/6),p2])
    xs,ys=zip(*control)
    return node(nid,'bezier',[min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)],fill,stroke,points=[list(v) for v in control],style={'stroke_px':width,'fill_secondary':shade(fill,1.13)})

def separator_zoom():
    rng=random.Random(11314)
    poly('zoom_teal_back',[(25,821),(291,811),(887,836),(887,1179),(26,1179)],'#3e9f9e','#478786',style={'fill_secondary':'#91cfbe'})
    poly('zoom_teal_side',[(859,847),(888,836),(888,1177),(859,1180)],'#278e8c','#427d7c')
    for j in range(37):
        x=rng.uniform(308,858);y=rng.uniform(830,891)
        sphere(f'zoom_back_site_{j}',x,y,rng.uniform(3,6),'#4fa5a0','#367b77',False)
    poly('zoom_membrane',[(22,838),(195,834),(855,867),(851,1181),(21,1181)],'#ded2b0','#beaf8d',style={'fill_secondary':'#f2e8cd'})
    # Cellular pores are actual closed cubic paths; ragged highlights and
    # struts approximate the source's fibrous, irregular material.
    centres=[]
    for row in range(4):
        for col in range(6):
            x=79+col*136+(row%2)*19+rng.uniform(-12,12)
            y=884+row*80+rng.uniform(-11,11)
            rx=rng.uniform(43,57);ry=rng.uniform(25,35)
            centres.append((x,y))
            blob(f'zoom_pore_{row}_{col}',x,y,rx,ry,'#a6d6df','#b6a681',5,seed=300+row*11+col)
            line(f'zoom_pore_highlight_{row}_{col}',[(x-rx,y),(x-rx*.9,y-ry),(x+rx*.3,y-ry*1.2),(x+rx,y-ry*.1)],'#fff5db',7,'bezier')
            if (row+col)%2==0:ion(f'zoom_li_{row}_{col}',x-10,y+3,9)
    for row in range(3):
        for col in range(5):
            x=95+col*136;yy=927+row*80
            line(f'zoom_fibre_shadow_{row}_{col}',[(x-55,yy+2),(x-12,yy-20),(x+35,yy+17),(x+77,yy)],'#c8b99a',9,'bezier')
            line(f'zoom_fibre_light_{row}_{col}',[(x-55,yy),(x-12,yy-23),(x+35,yy+14),(x+77,yy-2)],'#f9edcf',5,'bezier')
    chain('trapped_chain',182,891,5,11,angle=.18)
    for j in range(3):
        sphere(f'polar_site_{j}',470+j*40,941,14,'#3ca3a0','#267c7a')
        chain(f'polar_ps_{j}',470+j*29,873+(j%2)*8,2,10,angle=-.15)
        line(f'adsorption_link_{j}',[(470+j*40,925),(470+j*29,893)],'#9f46b4',2.2,dashed=True)
    for j in range(4):sphere(f'catalytic_site_{j}',674+j*35,943,12,'#3ca3a0','#267c7a')
    for j,(x,y,r) in enumerate([(681,881,13),(709,901,14),(751,871,16),(779,911,12),(810,886,12)]):sphere(f'catalysis_ps_{j}',x,y,r)
    line('conversion_loop_1',[(705,886),(719,862),(739,857),(752,865)],'#283d45',1.8,'bezier',13)
    line('conversion_loop_2',[(792,892),(782,914),(770,927),(755,930)],'#283d45',1.8,'bezier',13)
    chain('zoom_lower_ps',665,1021,5,9.5,angle=.15)
    for j,(x,y,ex) in enumerate([(85,967,178),(191,1046,278),(303,1027,397),(586,1059,682)]):
        port(f'zoom_li_{j}_s',x,y);port(f'zoom_li_{j}_t',ex,y+7)
        edge(f'zoom_li_transport_{j}',f'zoom_li_{j}_s',f'zoom_li_{j}_t',[(x,y),(ex,y+7)],'#118bdc',4)
    for nid,label,box,point in [
        ('physical_label','Physical confinement',[39,788,270,31],(185,864)),
        ('polar_label','Polar adsorption',[388,788,250,31],(485,858)),
        ('catalytic_label','Catalytic conversion',[645,788,240,31],(762,851))]:
        text(nid,label,box,22,True);line(nid+'_leader',[(box[0]+box[2]/2,box[1]+30),point],'#263a45',1.7)
        sphere(nid+'_dot',*point,4.2,'#263a45','#ffffff',False)
    node('zoom_transport_tag','roundrect',[237,1043,201,39],'#ffffff','none',radius_px=5)
    text('zoom_transport_label','Li+ transport',[240,1045,195,34],24,True,'#0866b7')
    # Neutral callouts identify the same separator region at a larger scale.
    line('separator_zoom_callout_1',[(558,540),(204,724)],'#8b969a',1.7,dashed=True)
    line('separator_zoom_callout_2',[(651,551),(842,724)],'#8b969a',1.7,dashed=True)

def anode_interfaces():
    rng=random.Random(7152)
    for nid,x,title,head in [('bad',936,'Shuttle-dominated interface','#f8dddd'),('good',1363,'Controlled transport','#dff2ef')]:
        node(nid+'_panel','roundrect',[x,784,413,293],'#e2f2fb','#8c9ca5',radius_px=10,style={'fill_secondary':'#b1d4eb'})
        node(nid+'_header','roundrect',[x,784,413,44],head,'none',radius_px=10)
        text(nid+'_title',title,[x+9,788,395,33],22,True)
        node(nid+'_lithium','rect',[x+2,1008,409,67],'#a3bed5','#839db5',style={'fill_secondary':'#7f9fbd'})
        text(nid+'_li_label','Li anode',[x+103,1027,208,32],23,True)
    # Rough, heterogeneous passivation in the shuttle-dominated illustration.
    for j in range(21):
        x=947+j*19;y=996-rng.uniform(8,27);rx=rng.uniform(11,18);ry=rng.uniform(13,24)
        blob(f'bad_deposit_{j}',x,y,rx,ry,'#b8bcc1','#8e969e',1.2,seed=500+j)
        if j%2==0:blob(f'bad_parasitic_{j}',x+4,y-4,rx*.72,ry*.9,'#db9589','#bf7b70',1,seed=700+j)
    for j in range(4):chain(f'bad_incoming_ps_{j}',953+j*100,846+(j%2)*8,4+(j%2),5.8,angle=.25)
    for j in range(5):
        x=996+j*68;y=891+(j%2)*14;ion(f'bad_ion_{j}',x,y,8)
        line(f'bad_ion_path_{j}',[(x,y+10),(x-11,y+28),(x+9,971),(x+3,988)],'#188fd6',2.4,'bezier',13)
    for j in range(4):
        x=975+j*102
        line(f'bad_shuttle_path_{j}',[(x,871),(x-22,909),(x+32,927),(x+19,972)],'#ab43d3',2.4,'bezier',13,True)
    text('parasitic_label','Parasitic reactions',[1185,923,151,29],15,True)
    line('parasitic_label_leader',[(1208,952),(1199,979)],'#273a40',1.6)
    sphere('parasitic_label_dot',1199,979,4,'#273a40','#ffffff',False)
    # Thin, comparatively uniform interphase: qualitative design illustration.
    top=[]
    for j in range(21):top.append((1366+j*20,1004+math.sin(j*1.4)*4))
    poly('controlled_interphase',top+[(1766,1017),(1366,1017)],'#53b3ab','#388e8b',style={'fill_secondary':'#9ad5ca'})
    line('controlled_interphase_light',[(1366,1002),(1460,995),(1610,1013),(1766,1002)],'#b6eee2',3.3,'bezier')
    for j in range(7):
        x=1403+j*53;y=910+(j%2)*7;ion(f'good_ion_{j}',x,y,8)
        line(f'good_ion_path_{j}',[(x,y+10),(x-5,942),(x+4,971),(x,993)],'#188fd6',2.6,'bezier',13)
    for j in range(4):chain(f'good_retained_ps_{j}',1418+j*92,853+(j%2)*9,4,5.5,angle=-.05)
    for j in range(3):
        x=1462+j*100
        line(f'good_ps_route_{j}',[(x,878),(x-25,898),(x-36,861),(x-12,849)],'#a347cf',2.1,'bezier',13,True)
    for j,(x,label,fill) in enumerate([(1014,'Shuttle','#e8dcf6'),(1260,'Li loss','#f7d5d5'),(1511,'Passivation','#f0f3f7')]):
        node(f'failure_{j}','roundrect',[x,1099,188,58],fill,'#55505f',text=label,font=24,bold=True,radius_px=10)
    edge('shuttle_to_li_loss','failure_0','failure_1',[(1202,1128),(1260,1128)],'#55545d',4)
    edge('shuttle_to_passivation','failure_0','failure_2',[(1108,1157),(1108,1173),(1605,1173),(1605,1157)],'#55545d',2.6)
    line('anode_zoom_callout',[(40,450),(22,450),(22,665),(1080,665),(1080,724)],'#8b969a',1.7,dashed=True)

def build():
    node('background','rect',[0,0,1800,1200],'#ffffff','none')
    panel('panel_a','a','Cell architecture and transport',[11,10,1172,696])
    panel('panel_b','b','Sulfur conversion',[1196,10,594,696])
    panel('panel_c','c','Functional separator zoom',[11,723,895,465])
    panel('panel_d','d','Anode interface comparison',[919,723,871,465])
    cell_architecture()
    phase=int(sys.argv[1]) if len(sys.argv)>1 else 1
    if phase>=2:sulfur_conversion()
    if phase>=3:separator_zoom()
    if phase>=4:anode_interfaces()
    save_scene()

if __name__=='__main__':build()
