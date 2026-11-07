"""Explicit visible positioning repair, retaining the prior owned AI candidate."""
from pathlib import Path
import json,win32com.client
HERE=Path(__file__).resolve().parent
source=HERE/'.build/lis-illustrator-working-r1.ai'
dest=HERE/'.build/lis-illustrator-working-r2.ai'
if dest.exists():raise FileExistsError(dest)
s=json.loads((HERE/'scene.json').read_text('utf8'))
config={'source':source.as_posix(),'dest':dest.as_posix(),'scene':s}
script=r'''(function(C){
var doc=null;for(var i=0;i<app.documents.length;i++)try{if(app.documents[i].fullName.fsName===new File(C.source).fsName)doc=app.documents[i];}catch(e){}
if(!doc)doc=app.open(new File(C.source));if(!doc.saved)throw Error('Candidate has unsaved user changes');doc.activate();
var P=C.scene.pages[0],k=.75,H=C.scene.canvas.height_px*k,changed=[];
for(var i=0;i<P.nodes.length;i++){
 var n=P.nodes[i];if(!n.text)continue;var f=null,name='LD_'+n.id;
 for(var j=0;j<doc.textFrames.length;j++)if(doc.textFrames[j].name===name||doc.textFrames[j].name===name+'__text'){f=doc.textFrames[j];break;}
 if(!f)throw Error('Missing '+name);
 var outline=f.duplicate().createOutline(),b=outline.visibleBounds;b=[b[0],b[1],b[2],b[3]];outline.remove();
 var x=n.bbox[0]*k,top=H-n.bbox[1]*k,ww=n.bbox[2]*k,hh=n.bbox[3]*k,align=typeof n.style.align==='number'?n.style.align:1;
 if(align===2)x+=ww-(b[2]-b[0]);else if(align!==0)x+=(ww-(b[2]-b[0]))/2;
 var dx=x-b[0],dy=top-(hh-(b[1]-b[3]))/2-b[1];
 if(Math.abs(dx)+Math.abs(dy)>.01){f.translate(dx,dy);doc.selection=null;f.selected=true;app.redraw();$.sleep(260);changed.push(n.id);}
}
doc.selection=null;var opts=new IllustratorSaveOptions();opts.pdfCompatible=true;opts.compressed=true;doc.saveAs(new File(C.dest),opts);return changed.join(',');
})(CONFIG);'''.replace('CONFIG',json.dumps(config,ensure_ascii=True))
app=win32com.client.GetActiveObject('Illustrator.Application.30');changed=app.DoJavaScript(script)
(HERE/'.build/alignment-repair.json').write_text(json.dumps({'visible_native_edits':True,'source':str(source),'candidate':str(dest),'changed':str(changed).split(','),'cause':'ExtendScript chained conditional expression associativity; explicit if/else now used in renderer and verified by glyph position.'},ensure_ascii=False,indent=2),encoding='utf8')
print(changed)
