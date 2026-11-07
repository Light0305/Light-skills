"""Preserve the initial live drawing, then visibly remove two known relations.

Run once before draw_visible.py --append with library-corrected-r1.pptx.
All replacements are native objects from that library; no screenshot overlay.
"""
from pathlib import Path
import json
import win32com.client
HERE=Path(__file__).resolve().parent
working=HERE/'.build/lis-live-working.pptx';prior=HERE/'.build/lis-before-corrections.pptx'
if prior.exists():raise FileExistsError(prior)
app=win32com.client.Dispatch('PowerPoint.Application');app.Visible=True
pres=next(app.Presentations(i) for i in range(1,app.Presentations.Count+1) if app.Presentations(i).FullName.casefold()==str(working).casefold())
pres.Windows(1).Activate();pres.SaveCopyAs(str(prior),24)
names=['Light_li_loss_to_passivation','Light_anode_zoom_callout']
for name in names:pres.Slides(1).Shapes(name).Delete()
pres.Save()
logpath=working.with_suffix('.drawing-log.json');log=json.loads(logpath.read_text('utf8'))
log['removed_objects']=[o for o in log['objects'] if o['name'] in names]
log['objects']=[o for o in log['objects'] if o['name'] not in names];log['object_count']=len(log['objects'])
log['visible_corrections']=['Remove Li loss -> Passivation, add separate Shuttle -> Passivation branch.','Replace anode zoom leader with one originating at visible Li anode.']
logpath.write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf8')
print('Preserved initial live drawing; removed two explicitly identified native objects.')
