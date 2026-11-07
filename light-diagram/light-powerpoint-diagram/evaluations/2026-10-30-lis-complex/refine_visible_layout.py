"""Final visible cleanup: remove redundant + glyphs and clear label routes."""
from pathlib import Path
import json
import win32com.client
HERE=Path(__file__).resolve().parent
s=json.loads((HERE/'scene.json').read_text('utf8'));nodes={n['id']:n for n in s['pages'][0]['nodes']};edges={e['id']:e for e in s['pages'][0]['edges']}
app=win32com.client.Dispatch('PowerPoint.Application');app.Visible=True
working=HERE/'.build/roundtrip-r2.pptx'
pres=next((app.Presentations(i) for i in range(1,app.Presentations.Count+1) if app.Presentations(i).FullName.casefold()==str(working).casefold()),None)
if pres is None:pres=app.Presentations.Open(str(working),False,False,True)
pres.Windows(1).Activate();slide=pres.Slides(1)
removed=[]
for i in range(slide.Shapes.Count,0,-1):
    sh=slide.Shapes(i)
    if sh.Name.startswith('Light_') and sh.Name.endswith('_sign'):
        removed.append(sh.Name);sh.Delete()
node=nodes['charge_route_t'];sh=slide.Shapes('Light_charge_route_t');sh.Left=node['bbox'][0]*.75;sh.Top=node['bbox'][1]*.75
for j,pt in enumerate(edges['charge_return']['points'][1:-1],1):
    sh=slide.Shapes(f'Light_charge_return__bend_{j}');sh.Left=pt[0]*.75;sh.Top=pt[1]*.75
box=nodes['charge_label']['bbox'];sh=slide.Shapes('Light_charge_label');sh.Left=box[0]*.75;sh.Top=box[1]*.75;sh.Width=box[2]*.75
library=app.Presentations.Open(str(HERE/'.build/library-final-r2.pptx'),True,False,False)
try:
    old=slide.Shapes('Light_anode_zoom_callout');src=library.Slides(1).Shapes('Light_anode_zoom_callout');src.Copy();new=slide.Shapes.Paste().Item(1);old.Delete();new.Name='Light_anode_zoom_callout';new.Left=src.Left;new.Top=src.Top;new.Select()
finally:library.Close()
pres.SaveAs(str(HERE/'.build/lis-refined-working.pptx'),24)
p=HERE/'.build/lis-live-working.drawing-log.json';log=json.loads(p.read_text('utf8'))
log['visual_removed_objects']=[o for o in log['objects'] if o['name'] in removed];log['objects']=[o for o in log['objects'] if o['name'] not in removed];log['object_count']=len(log['objects'])
log['visible_replacements']+=['Remove redundant white + glyphs; blue Li+ spheres and explanatory Li+ labels retained.','Clear anode callout and charge path from visible labels.']
p.write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'removed_redundant_glyphs':len(removed),'native_shapes':slide.Shapes.Count,'active_log_objects':log['object_count']}))
