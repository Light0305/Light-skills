"""Synchronize the explicitly changed footer ports, then reconnect and save."""
from pathlib import Path
import json,time
import win32com.client
HERE=Path(__file__).resolve().parent
scene=json.loads((HERE/'scene.json').read_text('utf8'))
ca=json.loads((HERE/'.build/library-corrected-r1.pptx.connections.json').read_text('utf8'))
app=win32com.client.Dispatch('PowerPoint.Application');app.Visible=True
work=HERE/'.build/roundtrip-r1.pptx'
pres=next((app.Presentations(i) for i in range(1,app.Presentations.Count+1) if app.Presentations(i).FullName.casefold()==str(work).casefold()),None)
if pres is None:pres=app.Presentations.Open(str(work),False,False,True)
pres.Windows(1).Activate();dst=pres.Slides(1)
source=app.Presentations.Open(str(HERE/'.build/library-corrected-r1.pptx'),True,False,False);src=source.Slides(1)
try:
    for nid in ['failure_0','failure_2']:
        old=dst.Shapes('Light_'+nid);original=src.Shapes('Light_'+nid);original.Copy();new=dst.Shapes.Paste().Item(1)
        old.Delete();new.Name='Light_'+nid;new.Left=original.Left;new.Top=original.Top;new.Select();time.sleep(.6)
    lab=dst.Shapes('Light_parasitic_label');lab.TextFrame.TextRange.Font.Size=15*.8533333333333334*.75;lab.Select()
    items={dst.Shapes(i).Name:dst.Shapes(i) for i in range(1,dst.Shapes.Count+1)}
    for edge in scene['pages'][0]['edges']:
        for sid in ca['pages'][0]['edge_parts'][edge['id']]:
            original=src.Shapes('Light_'+sid);sh=items['Light_'+sid];cf=original.ConnectorFormat
            sh.ConnectorFormat.BeginConnect(items[cf.BeginConnectedShape.Name],cf.BeginConnectionSite)
            sh.ConnectorFormat.EndConnect(items[cf.EndConnectedShape.Name],cf.EndConnectionSite)
    pres.SaveAs(str(HERE/'.build/lis-corrected-working.pptx'),24)
finally:source.Close()
logpath=HERE/'.build/lis-live-working.drawing-log.json';log=json.loads(logpath.read_text('utf8'))
log['visible_replacements']=['failure_0: synchronized additional bottom connection site','failure_2: synchronized bottom target site','parasitic_label: explicit font 17 -> 15 px on tracing canvas']
logpath.write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf8')
print('Synchronized both endpoint shapes, reattached all semantic routes, saved visible corrected work file.')
