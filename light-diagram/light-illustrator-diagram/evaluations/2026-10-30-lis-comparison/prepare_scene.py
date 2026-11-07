"""Adapt the inspected Li-S scene for an Illustrator same-reference comparison.

Copies reference lineage; does not generate a new image or trace a bitmap.
Adds actual compound-path openings and vector grain, not experimental detail.
"""
from pathlib import Path
import json,hashlib,math,random,shutil
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[2]/'light-powerpoint-diagram/evaluations/2026-10-30-lis-complex'

def organic_loop(box,seed):
    rng=random.Random(seed);x,y,w,h=box;ps=[]
    for j in range(9):
        t=j*math.tau/9;f=rng.uniform(.83,1.08);ps.append([x+w/2+math.cos(t)*w/2*f,y+h/2+math.sin(t)*h/2*f])
    out=[ps[0]]
    for i in range(9):
        a,b,c,d=ps[(i-1)%9],ps[i],ps[(i+1)%9],ps[(i+2)%9]
        out += [[b[0]+(c[0]-a[0])/6,b[1]+(c[1]-a[1])/6],[c[0]-(d[0]-b[0])/6,c[1]-(d[1]-b[1])/6],c]
    return out

def main():
    HERE.mkdir(parents=True,exist_ok=True);(HERE/'.build').mkdir(exist_ok=True);(HERE/'output').mkdir(exist_ok=True)
    for name in ('source.png',):
        dest=HERE/name
        if not dest.exists():shutil.copyfile(SOURCE/name,dest)
    original=json.loads((SOURCE/'source-manifest.json').read_text('utf8'))
    shutil.copyfile(SOURCE/'prompt-v1.txt',HERE/'reference-prompt-v1.txt')
    source_manifest={'task':'Illustrator same-reference comparison; no new generation in this case','source':'source.png','source_sha256':original['source_sha256'],'new_image_generation_calls':0,'prior_images_used':True,'reference_reused_from':str(SOURCE/'source.png'),'reference_original_generation':{'tool':original['image_generation_tool'],'calls':1,'prompt':'reference-prompt-v1.txt','prompt_sha256':original['prompt_sha256'],'model_version':None,'seed':None},'scientific_sources':original['scientific_sources'],'evidence_boundary':original['evidence_boundary'],'reference_issues':original['generated_image_review']['issues'],'native_scientific_corrections':original['native_scientific_corrections']}
    (HERE/'source-manifest.json').write_text(json.dumps(source_manifest,ensure_ascii=False,indent=2),encoding='utf8')
    s=json.loads((SOURCE/'scene.json').read_text('utf8'));s.update(schema_version='1.1',font='ArialMT',font_bold='Arial-BoldMT',points_per_pixel=.75)
    s['layers']=[{'id':key,'name':label} for key,label in [('paper','00 Paper'),('a','10 Cell architecture'),('b','20 Sulfur conversion'),('c','30 Separator mechanism'),('d','40 Anode comparison'),('callouts','50 Cross-panel callouts')]]
    s['groups']=[{'id':key,'layer':key,'test_move':key in ('a','b','c','d')} for key in ('paper','a','b','c','d','callouts')]
    pg=s['pages'][0];pg['name']='Li-S multiscale mechanism - Illustrator';pg['slug']='illustrator';nodes={n['id']:n for n in pg['nodes']}
    # Compound carbon skeleton: real open contours, not ellipses covering a slab.
    host=nodes['carbon_host'];outer=host.pop('points');host['type']='compound';host['contours']=[{'curve':'polyline','points':outer}]
    pores=[n for n in pg['nodes'] if n['id'].startswith('carbon_pore_')]
    for i,pore in enumerate(pores):
        pore['type']='bezier';pore['points']=organic_loop(pore['bbox'],800+i)
        host['contours'].append({'curve':'bezier','points':pore['points']})
        pore['style'].update(fill='none',stroke='#697475',stroke_px=3.2)
        pore['style'].pop('fill_secondary',None)
    # Radial shading stays a native GradientColor and editable sphere.
    for n in pg['nodes']:
        if n['type']=='ellipse' and n['style'].get('fill_secondary'):n['style']['gradient_type']='radial'
    rng=random.Random(903);grain=[]
    for j in range(220):
        x=rng.uniform(602,907);y=rng.uniform(145,480)
        if any(((x-(n['bbox'][0]+n['bbox'][2]/2))/(n['bbox'][2]*.67))**2+((y-(n['bbox'][1]+n['bbox'][3]/2))/(n['bbox'][3]*.67))**2<1 for n in pores):continue
        nid=f'carbon_grain_{j}';grain.append({'id':nid,'points':[[x,y],[x+rng.uniform(1,3),y+rng.uniform(-1,1)]],'curve':'polyline','arrow':0,'style':{'stroke':'#7d8784','stroke_px':.55,'opacity':40}})
    pg['paths'].extend(grain);pos=pg['draw_order'].index('carbon_top')+1;pg['draw_order'][pos:pos]=[v['id'] for v in grain]
    def section(v):
        nid=v['id']
        if nid=='background':return 'paper'
        if 'callout' in nid:return 'callouts'
        if nid.startswith('panel_'):return nid.split('_')[1]
        if 'bbox' in v:x,y,w,h=v['bbox'];cx,cy=x+w/2,y+h/2
        else:cx=sum(p[0] for p in v['points'])/len(v['points']);cy=sum(p[1] for p in v['points'])/len(v['points'])
        return ('a' if cx<1016 else 'b') if cy<610 else ('c' if cx<780 else 'd')
    for v in pg['nodes']+pg['paths']+pg['edges']:v['group']=section(v)
    def native_text(n):
        if not n.get('text'):return
        out='';runs=[]
        for ch in n['text']:
            if '₀'<=ch<='₉':
                runs.append({'start':len(out),'length':1,'baseline':'subscript'});out+=str(ord(ch)-ord('₀'))
            else:
                if ch=='⇌':runs.append({'start':len(out),'length':1,'font':'CambriaMath'})
                out+=ch
        if runs:n['native_text']=out;n['text_runs']=runs
    for n in pg['nodes']:native_text(n)
    s['provenance']['method']='Adaptation of manually measured, science-corrected Li-S scene for a same-reference native Illustrator comparison; compound carbon pores, radial gradients and sparse vector grain added.'
    s['provenance']['comparison_scene_sha256']=hashlib.sha256((SOURCE/'scene.json').read_bytes()).hexdigest()
    s['provenance']['limitations']=['Conceptual synthesis; pore shapes and particle locations remain approximations.','Illustrator paths do not have Visio/PowerPoint dynamic connector attachment. Group movement covers internal artwork; cross-panel callouts must be rerouted explicitly.']
    (HERE/'scene.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf8')
    probe={'schema_version':'1.1','font':'ArialMT','font_bold':'Arial-BoldMT','points_per_pixel':.75,'canvas':{'width_px':600,'height_px':360},'layers':[{'id':'paper','name':'00 Paper'},{'id':'a','name':'10 Native primitives'}],'groups':[{'id':'paper','layer':'paper'},{'id':'a','layer':'a','test_move':True}],'pages':[{'name':'Native Illustrator probe','nodes':[{'id':'background','type':'rect','bbox':[0,0,600,360],'style':{'fill':'#ffffff'},'group':'paper'},{'id':'porous','type':'compound','bbox':[45,65,300,190],'contours':[{'points':[[45,65],[345,65],[345,255],[45,255],[45,65]]},{'curve':'bezier','points':organic_loop([105,110,150,90],12)}],'style':{'fill':'#396a79','fill_secondary':'#243b4a','stroke':'#142530','stroke_px':2},'group':'a'},{'id':'label','type':'text','bbox':[360,100,210,90],'text':'Native Li₂S\nEditable text','style':{'font_px':22,'bold':True,'text_color':'#142530'},'group':'a'},{'id':'ball','type':'ellipse','bbox':[380,235,55,55],'style':{'fill':'#e8c338','fill_secondary':'#9e6c13','gradient_type':'radial','stroke':'#b28b29'},'group':'a'}],'paths':[{'id':'curve','points':[[70,300],[140,260],[220,345],[310,300]],'curve':'bezier','arrow':1,'style':{'stroke':'#168be0','stroke_px':3},'group':'a'}],'edges':[],'draw_order':['background','porous','label','ball','curve']}]}
    probe['pages'][0]['nodes'][2]['text']='Native Li₂S\nS₈ ⇌ Li₂S'
    probe['pages'][0]['nodes'][2]['style']['align']=0
    native_text(probe['pages'][0]['nodes'][2])
    (HERE/'.build/probe-scene.json').write_text(json.dumps(probe,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'nodes':len(pg['nodes']),'paths':len(pg['paths']),'edges':len(pg['edges']),'new_vector_grain':len(grain),'compound_holes':len(host['contours'])-1}))

if __name__=='__main__':main()
