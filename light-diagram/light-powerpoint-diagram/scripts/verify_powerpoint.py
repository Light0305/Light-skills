"""Open a specific PPTX visibly in desktop PowerPoint, round-trip and audit it.

Never quit PowerPoint or close unrelated presentations. The active saved result
stays visible. Temporary movement is tested and restored without saving it.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as E

def ensure_saved(presentation):
    if not presentation.Saved:
        raise ValueError('The named presentation has unsaved changes; save or use a separate candidate before verification')


def export_paths(stem, scene):
    return ([Path(str(stem)+'-'+page['slug']+'.png').resolve() for page in scene['pages']]
            + [Path(str(stem)+'.pdf').resolve(), Path(str(stem)+'.audit.json').resolve()])


def text_value(shape):
    return shape.TextFrame.TextRange.Text.replace('\r\n','\n').replace('\r','\n').replace('\v','\n') if shape.HasTextFrame else ''

def endpoint(shape,begin):
    # Native straight connectors store direction in flip/rotation; positive
    # bounding-box width alone does not identify the source endpoint.
    left,top,w,h=shape.Left,shape.Top,shape.Width,shape.Height
    x=(-w/2 if begin else w/2);y=(-h/2 if begin else h/2)
    if shape.HorizontalFlip: x=-x
    if shape.VerticalFlip:y=-y
    a=math.radians(shape.Rotation)
    return (left+w/2+x*math.cos(a)-y*math.sin(a),top+h/2+x*math.sin(a)+y*math.cos(a))

def inspect(pres,scene,connection_audit):
    errors=[]; pages=[]
    if pres.Slides.Count!=len(scene['pages']):errors.append('Slide count differs')
    for i,page in enumerate(scene['pages'],1):
        slide=pres.Slides(i);ca=connection_audit['pages'][i-1]
        items={slide.Shapes(j).Name:slide.Shapes(j) for j in range(1,slide.Shapes.Count+1)}
        if slide.Shapes.Count!=ca['native_shapes']:errors.append(f'Slide {i}: native shape count')
        text_count=0;bound=0;arrows=0;native_count=0
        for node in page['nodes']:
            name='Light_'+node['id']
            if name not in items:errors.append('Missing '+name);continue
            sh=items[name];actual=text_value(sh)
            if actual!=node.get('text',''):errors.append(f'Slide {i}: text {node["id"]}: {actual!r}')
            if actual:
                text_count+=1
                if sh.TextFrame.TextRange.Font.Name!=scene.get('font','Arial'):errors.append('Font '+name)
                if sh.TextFrame2.TextRange.BoundWidth>sh.Width+1.5 or sh.TextFrame2.TextRange.BoundHeight>sh.Height+1.5:errors.append('Text overflow '+name)
        for edge in page['edges']:
            parts=ca['edge_parts'][edge['id']]
            for j,sid in enumerate(parts):
                sh=items.get('Light_'+sid)
                if sh is None or not sh.Connector:errors.append('Not a connector '+sid);continue
                native_count+=1;cf=sh.ConnectorFormat
                for begin in (True,False):
                    connected=cf.BeginConnected if begin else cf.EndConnected
                    if not connected:errors.append('Detached '+sid);continue
                    bound+=1
                    target=cf.BeginConnectedShape if begin else cf.EndConnectedShape
                    expected=(edge['source']['node'] if j==0 else f'{edge["id"]}__bend_{j}') if begin else (edge['target']['node'] if j==len(parts)-1 else f'{edge["id"]}__bend_{j+1}')
                    if target.Name!='Light_'+expected:errors.append('Wrong connected node '+sid)
                for prop,has in [('BeginArrowheadStyle',j==0 and bool(edge.get('begin_arrow',0))),('EndArrowheadStyle',j==len(parts)-1 and bool(edge.get('arrow',0)))]:
                    val=getattr(sh.Line,prop)
                    if (val!=1)!=bool(has):errors.append('Wrong arrowhead '+sid+' '+prop)
                    arrows+=bool(has)
        # Probe each visible node participating in an edge, on both ends. All
        # attached segments must move with its exact translated connection site.
        movement=[]
        for node in page['nodes']:
            nid=node['id']; attached=[]
            for edge in page['edges']:
                parts=ca['edge_parts'][edge['id']]
                if edge['source']['node']==nid:attached.append((items['Light_'+parts[0]],True))
                if edge['target']['node']==nid:attached.append((items['Light_'+parts[-1]],False))
            if not attached:continue
            sh=items['Light_'+nid];x,y=sh.Left,sh.Top
            before=[endpoint(e,b) for e,b in attached];dx,dy=7.5,3.75
            try:
                sh.Left=x+dx;sh.Top=y+dy
                moved=[endpoint(e,b) for e,b in attached]
                delta=max(math.dist((a[0]+dx,a[1]+dy),b) for a,b in zip(before,moved))
            finally:
                sh.Left=x;sh.Top=y
            restored=[endpoint(e,b) for e,b in attached]
            restore_error=max(math.dist(a,b) for a,b in zip(before,restored))
            ok=delta<.1 and restore_error<.1
            movement.append({'node':nid,'tested_endpoints':len(attached),'max_error_pt':round(delta,6),'restore_error_pt':round(restore_error,6),'passed':ok})
            if not ok:errors.append('Movement failed '+nid)
        pages.append({'slide':i,'slug':page['slug'],'shapes':slide.Shapes.Count,'logical_edges':len(page['edges']),'native_connector_segments':native_count,'connected_segment_endpoints':bound,'text_shapes':text_count,'arrowheads':arrows,'movement':movement})
    return pages,errors

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene',type=Path);p.add_argument('candidate',type=Path);p.add_argument('connections',type=Path);p.add_argument('roundtrip',type=Path);p.add_argument('export_stem',type=Path);p.add_argument('--apply-text-format',action='store_true');p.add_argument('--hidden',action='store_true');p.add_argument('--verify-saved',action='store_true');a=p.parse_args()
    if a.verify_saved:
        if a.candidate.resolve()!=a.roundtrip.resolve() or a.apply_text_format:p.error('--verify-saved requires the same candidate/roundtrip and no text changes')
    elif a.roundtrip.exists():p.error('Output exists; choose a new roundtrip filename')
    scene=json.loads(a.scene.read_text('utf8'));ca=json.loads(a.connections.read_text('utf8'))
    for out in export_paths(a.export_stem, scene):
        if out.exists():p.error('Export already exists; use a new export stem: '+str(out))
    a.export_stem.resolve().parent.mkdir(parents=True,exist_ok=True)
    import win32com.client
    app=win32com.client.Dispatch('PowerPoint.Application')
    if not a.hidden:app.Visible=True
    candidate=str(a.candidate.resolve());pres=None
    for i in range(1,app.Presentations.Count+1):
        existing=app.Presentations(i)
        if existing.FullName.casefold()==candidate.casefold():
            ensure_saved(existing);pres=existing;break
    if pres is None:pres=app.Presentations.Open(candidate,False,False,not a.hidden)
    if not a.hidden:
        if not pres.Windows.Count:pres.NewWindow()
        pres.Windows(1).Activate()
    changes=[]
    if a.apply_text_format:
        for i,page in enumerate(scene['pages'],1):
            slide=pres.Slides(i)
            if not a.hidden:pres.Windows(1).View.GotoSlide(i)
            for n in page['nodes']:
                if not ('subscript_start' in n or n.get('native_text_edit')):continue
                sh=slide.Shapes('Light_'+n['id']);before=text_value(sh)
                sh.TextFrame.TextRange.Text=n.get('text','')
                tr=sh.TextFrame.TextRange;tr.Font.Name=scene.get('font','Arial');tr.Font.Size=n['style']['font_px']*.75;tr.Font.Bold=-1 if n['style'].get('bold',True) else 0
                if 'subscript_start' in n:
                    start=n['subscript_start'];run=tr.Characters(start+1,len(n['text'])-start);run.Font.BaselineOffset=-.25;run.Font.Size=tr.Font.Size*.75
                changes.append({'slide':i,'node':n['id'],'before':before,'after':text_value(sh),'subscript_start':n.get('subscript_start')})
    a.roundtrip.parent.mkdir(parents=True,exist_ok=True)
    if not a.verify_saved:pres.SaveAs(str(a.roundtrip.resolve()),24)
    pres.Close()
    pres=app.Presentations.Open(str(a.roundtrip.resolve()),False,False,not a.hidden)
    pages,errors=inspect(pres,scene,ca)
    # Probe changes are restored, then discarded by reopening the saved file.
    pres.Saved=True;pres.Close()
    pres=app.Presentations.Open(str(a.roundtrip.resolve()),False,False,not a.hidden)
    files=[]
    for i,page in enumerate(scene['pages'],1):
        out=Path(str(a.export_stem)+'-'+page['slug']+'.png').resolve()
        pres.Slides(i).Export(str(out),'PNG',scene['canvas']['width_px'],scene['canvas']['height_px']);files.append(str(out))
    pdf=Path(str(a.export_stem)+'.pdf').resolve();pres.SaveCopyAs(str(pdf),32);files.append(str(pdf))
    with zipfile.ZipFile(a.roundtrip) as z:
        media=[n for n in z.namelist() if n.startswith('ppt/media/')]
        if media:errors.append('Unexpected image/media entries')
        ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
        for i in range(1,len(scene['pages'])+1):
            root=E.fromstring(z.read(f'ppt/slides/slide{i}.xml'))
            if root.findall('.//p:pic',ns) or root.findall('.//a:blip',ns):errors.append(f'Slide {i} embeds image')
    report={'passed':not errors,'scope':'Native desktop PowerPoint roundtrip, text, shapes, arrows, endpoints and movement; visual/scientific review is separate.','powerpoint_version':app.Version,'visible':not a.hidden,'file':str(a.roundtrip.resolve()),'sha256':hashlib.sha256(a.roundtrip.read_bytes()).hexdigest(),'scene_sha256':hashlib.sha256(a.scene.read_bytes()).hexdigest(),'connections_sha256':hashlib.sha256(a.connections.read_bytes()).hexdigest(),'native_text_refinements':changes,'media_entries':media,'pages':pages,'exports':files,'errors':errors}
    Path(str(a.export_stem)+'.audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    if not a.hidden:pres.Windows(1).Activate();pres.Windows(1).View.GotoSlide(2 if len(scene['pages'])>1 else 1)
    else:pres.Close()
    print(json.dumps({'passed':report['passed'],'pages':[{k:v for k,v in x.items() if k!='movement'} for x in pages],'errors':errors},ensure_ascii=False))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
