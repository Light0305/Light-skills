"""Copy authored native objects into a visible blank PowerPoint, one at a time.

The source library is made by Artifact Tool and the connection completer. The
target is an explicitly named, empty work file. This is real native object
insertion, not a video or visibility animation of a precompleted slide.
"""
import argparse,json,time
from pathlib import Path

def main():
    start=time.monotonic()
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('library',type=Path);p.add_argument('working',type=Path);p.add_argument('connections',type=Path);p.add_argument('scene',type=Path);p.add_argument('--delay',type=float,default=.22);p.add_argument('--append',action='store_true');a=p.parse_args()
    if not .05<=a.delay<=2:p.error('--delay must be between .05 and 2 seconds')
    if a.library.resolve()==a.working.resolve():p.error('Library and working presentation must be different files')
    import win32com.client
    app=win32com.client.Dispatch('PowerPoint.Application');app.Visible=True
    target=next((app.Presentations(i) for i in range(1,app.Presentations.Count+1) if app.Presentations(i).FullName.casefold()==str(a.working.resolve()).casefold()),None)
    if target is not None and not target.Saved:raise ValueError('Working presentation has unsaved changes; save before continuing')
    if target is None:target=app.Presentations.Open(str(a.working.resolve()),False,False,True)
    if not a.append and any(target.Slides(i).Shapes.Count for i in range(1,target.Slides.Count+1)):raise ValueError('Working slides must be empty; nothing was deleted')
    if any(app.Presentations(i).FullName.casefold()==str(a.library.resolve()).casefold() for i in range(1,app.Presentations.Count+1)):
        raise ValueError('Library is already open; use a separate saved library copy')
    source=app.Presentations.Open(str(a.library.resolve()),True,False,False)
    scene=json.loads(a.scene.read_text('utf8'));connections=json.loads(a.connections.read_text('utf8'));log=[]
    log_path=a.working.with_suffix('.drawing-log.json')
    prior_log={}
    if a.append and log_path.exists():prior_log=json.loads(log_path.read_text('utf8'));log=prior_log['objects']
    inserted_now=0
    try:
        for index,page in enumerate(scene['pages'],1):
            src=source.Slides(index);dst=target.Slides(index) if index<=target.Slides.Count else target.Slides.Add(index,12)
            target.Windows(1).Activate();target.Windows(1).View.GotoSlide(index)
            existing_names={dst.Shapes(k).Name for k in range(1,dst.Shapes.Count+1)}
            for j in range(1,src.Shapes.Count+1):
                original=src.Shapes(j)
                if original.Name in existing_names:continue
                for attempt in range(3):
                    try:
                        original.Copy();pasted=dst.Shapes.Paste().Item(1);break
                    except Exception:
                        if attempt==2:raise
                        time.sleep(.15)
                pasted.Name=original.Name
                # The native clipboard preserves paths and text. Explicitly
                # retain transforms in case the app offsets pasted objects.
                pasted.Left=original.Left;pasted.Top=original.Top
                pasted.Select()
                inserted_now+=1
                log.append({'slide':index,'order':j,'name':pasted.Name,'elapsed_s':round(time.monotonic()-start,3),'phase_library':a.library.name})
                if j%12==0:
                    target.Save();print(json.dumps({'slide':index,'inserted':j,'total':src.Shapes.Count,'last_shape':pasted.Name}),flush=True)
                time.sleep(a.delay)
            items={dst.Shapes(j).Name:dst.Shapes(j) for j in range(1,dst.Shapes.Count+1)}
            srcitems={src.Shapes(j).Name:src.Shapes(j) for j in range(1,src.Shapes.Count+1)}
            for edge in page['edges']:
                for sid in connections['pages'][index-1]['edge_parts'][edge['id']]:
                    original=srcitems['Light_'+sid];sh=items['Light_'+sid];cf=original.ConnectorFormat
                    sh.ConnectorFormat.BeginConnect(items[cf.BeginConnectedShape.Name],cf.BeginConnectionSite)
                    sh.ConnectorFormat.EndConnect(items[cf.EndConnectedShape.Name],cf.EndConnectionSite)
                    sh.Select();time.sleep(a.delay)
            # Copy existing notes text without replacing slide placeholders.
            notes=src.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text
            dst.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text=notes
            target.Save()
    finally:
        source.Close()
        log_path.write_text(json.dumps({**prior_log,'visible_native_object_insertion':True,'source':str(a.library.resolve()),'working':str(a.working.resolve()),'object_count':len(log),'objects':log},ensure_ascii=False,indent=2),encoding='utf8')
    target.Windows(1).Activate();target.Windows(1).View.GotoSlide(1)
    print(json.dumps({'completed':True,'objects':len(log),'new_objects':inserted_now,'elapsed_s':round(time.monotonic()-start,2)}))

if __name__=='__main__':
    start=time.monotonic();main()
