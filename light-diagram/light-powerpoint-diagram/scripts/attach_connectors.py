"""Complete native OOXML connection sites after Artifact Tool export.

No raster conversion, python-pptx or Office authoring dependency. Every semantic
edge becomes native straight connector segments, joined at transparent native
bend anchors. Desktop PowerPoint rejects custom-path p:cxnSp in this fixture.
Native application reopening and movement still require separate verification.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import zipfile
from lxml import etree as E

NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
for prefix,uri in NS.items(): E.register_namespace(prefix,uri)
def q(prefix,name): return '{'+NS[prefix]+'}'+name
def add(parent,tag,**attrs): return E.SubElement(parent,q('a',tag),{k:str(v) for k,v in attrs.items()})

def complete(scene_path, candidate, output):
    if Path(output).exists(): raise FileExistsError(output)
    scene=json.loads(Path(scene_path).read_text('utf-8'))
    replacements={}; audit=[]
    with zipfile.ZipFile(candidate) as zin:
        for i,page in enumerate(scene['pages'],1):
            filename=f'ppt/slides/slide{i}.xml'
            raw=zin.read(filename)
            # Preserve scoped namespace declarations. ElementTree's hoisting
            # made this Artifact Tool export unreadable in desktop PowerPoint.
            root=E.fromstring(raw); tree=root.find('p:cSld/p:spTree',NS)
            shapes={s.find('p:nvSpPr/p:cNvPr',NS).get('name')[6:]:s for s in tree.findall('p:sp',NS)}
            expected={x['id'] for x in page['nodes']+page['paths']+page['edges']}
            if set(shapes)!=expected: raise ValueError('Shape inventory differs from scene')
            ports={n['id']:[] for n in page['nodes']}
            for edge in page['edges']:
                for side in ('source','target'):
                    n=edge[side]['node']; uv=tuple(edge[side]['anchor'])
                    if uv not in ports[n]: ports[n].append(uv)
            for nid,uvs in ports.items():
                shape=shapes[nid]; geom=shape.find('p:spPr/a:custGeom',NS)
                if geom is None: raise ValueError('Expected editable custom geometry '+nid)
                for tag in ('avLst','gdLst','ahLst','cxnLst','rect'):
                    old=geom.find('a:'+tag,NS)
                    if old is not None: geom.remove(old)
                av=E.Element(q('a','avLst')); gd=E.Element(q('a','gdLst')); ah=E.Element(q('a','ahLst')); cx=E.Element(q('a','cxnLst'))
                rect=E.Element(q('a','rect'),{'l':'0','t':'0','r':'w','b':'h'})
                for index,(u,v) in enumerate(uvs):
                    # Guides scale ports on resize, unlike literal EMU constants.
                    add(gd,'gd',name=f'lx{index}',fmla=f'*/ w {round(u*1000000)} 1000000')
                    add(gd,'gd',name=f'ly{index}',fmla=f'*/ h {round(v*1000000)} 1000000')
                    ang=min([(u,10800000),(1-u,0),(v,16200000),(1-v,5400000)])[1]
                    c=add(cx,'cxn',ang=ang);add(c,'pos',x=f'lx{index}',y=f'ly{index}')
                for index,el in enumerate([av,gd,ah,cx,rect]):geom.insert(index,el)
            for item in page['paths']+page['edges']:
                shape=shapes[item['id']]; sppr=shape.find('p:spPr',NS); ln=sppr.find('a:ln',NS)
                if ln is None: ln=add(sppr,'ln',w=round(item.get('style',{}).get('stroke_px',1.3)*9525))
                for tag,value in [('headEnd',item.get('begin_arrow',0)),('tailEnd',item.get('arrow',0))]:
                    old=ln.find('a:'+tag,NS)
                    if old is not None:ln.remove(old)
                    add(ln,tag,type='triangle' if value else 'none',w='lg',len='lg')
            next_id=max(int(el.get('id')) for el in root.findall('.//p:cNvPr',NS))+1
            segment_count=bend_count=0
            edge_parts={}
            for edge in page['edges']:
                curved=edge.get('curve')=='bezier'
                if curved and edge.get('native_curve_approximation') not in ('curvedConnector2','curvedConnector3'):
                    raise ValueError('Semantic Bezier edge needs an explicitly accepted native_curve_approximation')
                route=[edge['points'][0],edge['points'][-1]] if curved else edge['points']
                old=shapes[edge['id']]; inserted=[]; ends=[]; names=[]
                src=edge['source'];dst=edge['target']
                ends.append((shapes[src['node']].find('p:nvSpPr/p:cNvPr',NS).get('id'),ports[src['node']].index(tuple(src['anchor']))))
                for j,(x,y) in enumerate(route[1:-1],1):
                    bend=E.Element(q('p','sp'));nv=E.SubElement(bend,q('p','nvSpPr'))
                    E.SubElement(nv,q('p','cNvPr'),{'id':str(next_id),'name':f'Light_{edge["id"]}__bend_{j}'})
                    E.SubElement(nv,q('p','cNvSpPr'));E.SubElement(nv,q('p','nvPr'))
                    sp=E.SubElement(bend,q('p','spPr'));xf=add(sp,'xfrm');add(xf,'off',x=round(x*9525),y=round(y*9525));add(xf,'ext',cx=95,cy=95)
                    geom=add(sp,'custGeom');add(geom,'avLst');add(geom,'gdLst');add(geom,'ahLst');cx=add(geom,'cxnLst');c=add(cx,'cxn',ang=0);add(c,'pos',x=0,y=0);add(geom,'rect',l=0,t=0,r='w',b='h')
                    pl=add(geom,'pathLst');pa=add(pl,'path',w=95,h=95);add(add(pa,'moveTo'),'pt',x=0,y=0);add(add(pa,'lnTo'),'pt',x=95,y=0);add(add(pa,'lnTo'),'pt',x=95,y=95);add(pa,'close')
                    add(sp,'noFill');add(add(sp,'ln',w=0),'noFill')
                    inserted.append(bend);ends.append((str(next_id),0));next_id+=1;bend_count+=1
                ends.append((shapes[dst['node']].find('p:nvSpPr/p:cNvPr',NS).get('id'),ports[dst['node']].index(tuple(dst['anchor']))))
                for j,(pt0,pt1) in enumerate(zip(route,route[1:])):
                    sid=edge['id'] if len(route)==2 else f'{edge["id"]}__seg_{j+1}'
                    new=E.Element(q('p','cxnSp'));nv=E.SubElement(new,q('p','nvCxnSpPr'))
                    E.SubElement(nv,q('p','cNvPr'),{'id':str(next_id),'name':'Light_'+sid});next_id+=1
                    cnv=E.SubElement(nv,q('p','cNvCxnSpPr'));add(cnv,'cxnSpLocks')
                    for tag,(target_id,port) in [('stCxn',ends[j]),('endCxn',ends[j+1])]:add(cnv,tag,id=target_id,idx=port)
                    E.SubElement(nv,q('p','nvPr'));sp=E.SubElement(new,q('p','spPr'));xf=add(sp,'xfrm')
                    x0,y0=pt0;x1,y1=pt1
                    if x1<x0:xf.set('flipH','1')
                    if y1<y0:xf.set('flipV','1')
                    add(xf,'off',x=round(min(x0,x1)*9525),y=round(min(y0,y1)*9525));add(xf,'ext',cx=round(abs(x1-x0)*9525),cy=round(abs(y1-y0)*9525))
                    add(add(sp,'prstGeom',prst=edge['native_curve_approximation'] if curved else 'straightConnector1'),'avLst');add(sp,'noFill')
                    ln=copy.deepcopy(old.find('p:spPr/a:ln',NS));sp.append(ln)
                    ln.find('a:headEnd',NS).set('type','triangle' if j==0 and edge.get('begin_arrow',0) else 'none')
                    ln.find('a:tailEnd',NS).set('type','triangle' if j==len(route)-2 and edge.get('arrow',0) else 'none')
                    inserted.append(new);names.append(sid);segment_count+=1
                pos=list(tree).index(old);tree.remove(old)
                for j,el in enumerate(inserted):tree.insert(pos+j,el)
                edge_parts[edge['id']]=names
            # Artifact Tool's default noGrp is irrelevant to this editable asset.
            for lock in root.findall('.//a:spLocks',NS):lock.attrib.pop('noGrp',None)
            replacements[filename]=E.tostring(root,encoding='utf-8',xml_declaration=True)
            audit.append({'slide':i,'slug':page['slug'],'native_shapes':len(expected)-len(page['edges'])+segment_count+bend_count,'logical_edges':len(page['edges']),'native_connectors':segment_count,'bend_anchors':bend_count,'attached_endpoints':2*segment_count,'custom_ports':sum(map(len,ports.values())),'edge_parts':edge_parts})
        Path(output).parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():zout.writestr(item,replacements.get(item.filename,zin.read(item.filename)))
    return {'authoring':'Artifact Tool plus explicit native OOXML connection sites','pages':audit,'application_roundtrip_verified':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene');p.add_argument('candidate');p.add_argument('output');a=p.parse_args()
    result=complete(a.scene,a.candidate,a.output)
    Path(a.output+'.connections.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
