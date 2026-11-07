/* Native Illustrator renderer. ES3 deliberately; Illustrator 30 has no JSON global. */
(function(C){
    function enc(v){
        if(v===null)return 'null';var t=typeof v,i,a=[];
        if(t==='string')return '"'+v.replace(/["\\\u0000-\u001f]/g,function(ch){if(ch==='"')return '\\"';if(ch==='\\')return '\\\\';var x=ch.charCodeAt(0).toString(16);return '\\u'+('0000'+x).slice(-4);})+'"';
        if(t==='number'||t==='boolean')return String(v);
        if(v instanceof Array){for(i=0;i<v.length;i++)a.push(enc(v[i]));return '['+a.join(',')+']';}
        for(i in v)if(v.hasOwnProperty(i)&&typeof v[i]!=='undefined')a.push(enc(i)+':'+enc(v[i]));return '{'+a.join(',')+'}';
    }
    function write(path,value){var f=new File(path);f.encoding='UTF-8';if(!f.open('w'))throw Error('Cannot write '+path);f.write(enc(value));f.close();}
    function load(path){var f=new File(path);f.encoding='UTF-8';if(!f.open('r'))throw Error('Cannot read '+path);var t=f.read();f.close();return eval('('+t+')');}
    function checkpoint(stage){write(C.stem+'.verify-progress.json',{stage:stage,complete:false});}
    function fail(message){throw Error(message);}
    var S=load(C.scene),P=S.pages[0],k=S.points_per_pixel||.75,H=S.canvas.height_px*k,W=S.canvas.width_px*k;
    function now(){return (new Date()).getTime();}
    var doc=null,owned=false,oldInteraction=app.userInteractionLevel,registry={},groups={},gradients={},gradientSerial=0,count=0,started=now(),trace=null;
    function xy(p){return [p[0]*k,H-p[1]*k];}
    function rgb(hex){var c=new RGBColor();c.red=parseInt(hex.slice(1,3),16);c.green=parseInt(hex.slice(3,5),16);c.blue=parseInt(hex.slice(5,7),16);return c;}
    function style(path,s,box){
        path.filled=!!s.fill&&s.fill!=='none';path.stroked=!!s.stroke&&s.stroke!=='none';
        if(path.filled){
            if(s.fill_secondary){
                var kind=s.gradient_type||'linear',key=s.fill+'|'+s.fill_secondary+'|'+kind,g=gradients[key];
                if(!g){g=doc.gradients.add();g.name='LD_gradient_'+gradientSerial++;g.type=kind==='radial'?GradientType.RADIAL:GradientType.LINEAR;g.gradientStops[0].rampPoint=0;g.gradientStops[1].rampPoint=100;g.gradientStops[0].color=rgb(s.fill);g.gradientStops[1].color=rgb(s.fill_secondary);gradients[key]=g;}
                var gc=new GradientColor();gc.gradient=g;var x=box[0],y=box[1],ww=box[2],hh=box[3];
                gc.origin=xy(kind==='radial'?[x+ww*.33,y+hh*.28]:[x,y]);gc.length=(kind==='radial'?Math.max(ww,hh)*.75:ww)*k;
                path.fillColor=gc;
            }else path.fillColor=rgb(s.fill);
        }
        if(path.stroked){path.strokeColor=rgb(s.stroke);path.strokeWidth=(s.stroke_px||1)*k;path.strokeCap=StrokeCap.ROUNDENDCAP;path.strokeJoin=StrokeJoin.ROUNDENDJOIN;path.strokeDashes=s.dash_pattern?[5*k,4*k]:[];}
        if(typeof s.opacity==='number')path.opacity=s.opacity;
    }
    function pathFrom(parent,points,curve,closed,name){
        var p=parent.pathItems.add();p.name=name;
        if(curve==='bezier'){
            var seg=(points.length-1)/3,n=closed?seg:seg+1;
            for(var i=0;i<n;i++){
                var pp=p.pathPoints.add(),a=points[i*3];pp.anchor=xy(a);
                pp.leftDirection=xy(i===0?(closed?points[points.length-2]:a):points[i*3-1]);
                pp.rightDirection=xy(i<seg?points[i*3+1]:a);pp.pointType=PointType.CORNER;
            }
        }else{var arr=[],n=points.length-(closed?1:0);for(var i=0;i<n;i++)arr.push(xy(points[i]));p.setEntirePath(arr);}
        p.closed=closed;return p;
    }
    function boxFromPoints(pts){var x=1e12,y=x,xx=-x,yy=-x;for(var i=0;i<pts.length;i++){x=Math.min(x,pts[i][0]);y=Math.min(y,pts[i][1]);xx=Math.max(xx,pts[i][0]);yy=Math.max(yy,pts[i][1]);}return [x,y,Math.max(.01,xx-x),Math.max(.01,yy-y)];}
    function arrow(parent,pts,atStart,s,name,curve){
        var tip=atStart?pts[0]:pts[pts.length-1],back=null,i=atStart?1:pts.length-2,step=atStart?1:-1;
        for(;i>=0&&i<pts.length;i+=step)if(Math.abs(pts[i][0]-tip[0])+Math.abs(pts[i][1]-tip[1])>.001){back=pts[i];break;}
        if(!back)fail('Zero-length arrow '+name);
        var dx=tip[0]-back[0],dy=tip[1]-back[1],len=Math.sqrt(dx*dx+dy*dy);dx/=len;dy/=len;
        var a=Math.max(9,(s.stroke_px||1)*3.8),b=a*.48,base=[tip[0]-dx*a,tip[1]-dy*a];
        var points=[tip,[base[0]-dy*b,base[1]+dx*b],[base[0]+dy*b,base[1]-dx*b],tip];
        var p=pathFrom(parent,points,'polyline',true,name);style(p,{fill:s.stroke||'#111111',stroke:'none'},boxFromPoints(points));return p;
    }
    function text(parent,n){
        var f=parent.textFrames.add();f.name='LD_'+n.id+'__text';f.contents=(n.native_text||n.text).replace(/\n/g,'\r');
        var s=n.style||{},ca=f.textRange.characterAttributes;ca.textFont=app.textFonts.getByName(s.bold===false?S.font:S.font_bold);ca.size=(s.font_px||18)*k;ca.fillColor=rgb(s.text_color||'#142530');ca.autoLeading=false;ca.leading=ca.size*1.12;
        f.textRange.paragraphAttributes.justification=Justification.LEFT;
        if(typeof n.subscript_start==='number')for(var z=n.subscript_start;z<f.characters.length;z++)f.characters[z].characterAttributes.baselinePosition=FontBaselineOption.SUBSCRIPT;
        if(n.text_runs)for(var ri=0;ri<n.text_runs.length;ri++){
            var run=n.text_runs[ri];for(var z=run.start;z<run.start+run.length;z++){
                var attr=f.characters[z].characterAttributes;
                if(run.baseline)attr.baselinePosition=run.baseline==='subscript'?FontBaselineOption.SUBSCRIPT:FontBaselineOption.SUPERSCRIPT;
                if(run.font)attr.textFont=app.textFonts.getByName(run.font);
            }
        }
        var b=inkBounds(f),x=n.bbox[0]*k,y=H-n.bbox[1]*k,ww=n.bbox[2]*k,hh=n.bbox[3]*k;
        var align=typeof s.align==='number'?s.align:1,dx=0;
        // ExtendScript 30 evaluates an unparenthesized chained ternary differently.
        if(align===2)dx=ww-(b[2]-b[0]);else if(align!==0)dx=(ww-(b[2]-b[0]))/2;
        f.translate(x+dx-b[0],y-(hh-(b[1]-b[3]))/2-b[1]);return f;
    }
    function item(n,category){
        var par=groups[n.group],s=n.style||{},o=null,x,y,ww,hh,b=n.bbox;
        if(category==='node'){
            if(n.type==='text')o=text(par,n);
            else if(n.type==='compound'){
                o=par.compoundPathItems.add();o.name='LD_'+n.id;
                for(var j=0;j<n.contours.length;j++){var co=n.contours[j],child=pathFrom(o,co.points,co.curve||'polyline',true,'LD_'+n.id+'__contour_'+j);child.evenodd=true;child.polarity=j===0?PolarityValues.POSITIVE:PolarityValues.NEGATIVE;}
                style(o.pathItems[0],s,b);
            }else{
                x=b[0]*k;y=H-b[1]*k;ww=b[2]*k;hh=b[3]*k;
                if(n.type==='rect')o=par.pathItems.rectangle(y,x,ww,hh);
                else if(n.type==='roundrect')o=par.pathItems.roundedRectangle(y,x,ww,hh,Math.min(n.radius_px||6,b[2]/2,b[3]/2)*k,Math.min(n.radius_px||6,b[2]/2,b[3]/2)*k);
                else if(n.type==='ellipse'||n.type==='junction')o=par.pathItems.ellipse(y,x,ww,hh);
                else if(n.type==='polygon'||n.type==='bezier')o=pathFrom(par,n.points,n.type==='bezier'?'bezier':'polyline',true,'LD_'+n.id);
                else fail('Unsupported node '+n.type);
                o.name='LD_'+n.id;style(o,s,b);
                if(n.text){var g=par.groupItems.add();g.name='LD_'+n.id+'__with_text';o.move(g,ElementPlacement.PLACEATEND);text(g,n);o=g;}
            }
        }else{
            o=par.groupItems.add();o.name='LD_'+n.id;var p=pathFrom(o,n.points,n.curve||'polyline',false,'LD_'+n.id+'__path');style(p,s,boxFromPoints(n.points));
            if(n.arrow)arrow(o,n.points,false,s,'LD_'+n.id+'__arrow',n.curve);if(n.begin_arrow)arrow(o,n.points,true,s,'LD_'+n.id+'__begin_arrow',n.curve);
        }
        if(n.type==='text')o.name='LD_'+n.id;registry[n.id]=o;
        o.note=enc({scene_id:n.id,category:category,source:n.source,target:n.target});
        count++;
        if(trace){trace.writeln(enc({order:count,id:n.id,category:category,group:n.group,elapsed_ms:now()-started}));if(count%10===0){trace.close();if(!trace.open('a'))fail('Trace cannot append');}}
        if(count%C.redraw_every===0){app.redraw();if(C.delay_ms)$.sleep(C.delay_ms*C.redraw_every);}
    }
    function leaves(parent,out){if(parent.typename==='Document'){for(var z=0;z<parent.layers.length;z++)leaves(parent.layers[z],out);return out;}var items=parent.pageItems;for(var i=0;i<items.length;i++){var a=items[i];if(a.parent!==parent)continue;if(a.typename==='GroupItem')leaves(a,out);else out.push(a);}return out;}
    var nativeIndex=null;
    function find(name){
        if(!nativeIndex){nativeIndex={};for(var i=0;i<doc.pageItems.length;i++){var it=doc.pageItems[i];if(it.name)nativeIndex[it.name]=it;}}
        if(nativeIndex[name])return nativeIndex[name];fail('Missing native item '+name);
    }
    function inkBounds(frame){var duplicate=frame.duplicate(),outline=null;try{outline=duplicate.createOutline();var b=outline.visibleBounds;return [b[0],b[1],b[2],b[3]];}finally{if(outline)outline.remove();else duplicate.remove();}}
    function geometry(p,points,curve,closed){
        var seg=curve==='bezier'?(points.length-1)/3:points.length-1,n=curve==='bezier'?(closed?seg:seg+1):(closed?points.length-1:points.length),err=0;
        if(p.pathPoints.length!==n||p.closed!==closed)return {passed:false,max_error_pt:null,points:p.pathPoints.length};
        function delta(a,b){return Math.max(Math.abs(a[0]-b[0]),Math.abs(a[1]-b[1]));}
        var best=1e20;
        // Saving a compound path may reverse winding or rotate its first knot.
        // Compare equivalent closed contours; open paths keep their direction.
        for(var offset=0;offset<(closed?n:1);offset++)for(var direction=1;direction>=(closed?-1:1);direction-=2){
            err=0;
            for(var z=0;z<n;z++){
                var idx=(offset+direction*z+n*2)%n,pp=p.pathPoints[z],a=points[curve==='bezier'?idx*3:idx];err=Math.max(err,delta(pp.anchor,xy(a)));
                if(curve==='bezier'){
                    var left=idx===0?(closed?points[points.length-2]:a):points[idx*3-1],right=idx<seg?points[idx*3+1]:a;
                    err=Math.max(err,delta(pp.leftDirection,xy(direction===1?left:right)),delta(pp.rightDirection,xy(direction===1?right:left)));
                }
            }
            best=Math.min(best,err);
        }
        return {passed:best<.01,max_error_pt:best,points:n};
    }
    function summary(){
        var rows=leaves(doc,[]),c={};for(var i=0;i<rows.length;i++)c[rows[i].typename]=(c[rows[i].typename]||0)+1;
        return {passed:true,application:'Adobe Illustrator',version:app.version,document:doc.fullName.fsName,artboard_rect:doc.artboards[0].artboardRect,artboards:doc.artboards.length,layers:doc.layers.length,group_items:doc.groupItems.length,path_items:doc.pathItems.length,compound_paths:doc.compoundPathItems.length,text_frames:doc.textFrames.length,raster_items:doc.rasterItems.length,placed_items:doc.placedItems.length,non_native_items:doc.nonNativeItems.length,mesh_items:doc.meshItems.length,gradient_definitions:doc.gradients.length,leaf_types:c,elapsed_ms:now()-started};
    }
    try{
        app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
        if(C.operation==='render'){
            if(new File(C.ai).exists)fail('AI exists');
            doc=app.documents.add(DocumentColorSpace.RGB,W,H);owned=true;doc.artboards[0].artboardRect=[0,H,W,0];doc.artboards[0].name=P.name;
            doc.views[0].centerPoint=[W/2,H/2];doc.views[0].zoom=Math.min(.8,1000/W);doc.activate();app.redraw();
            for(var i=0;i<S.layers.length;i++){var l=doc.layers.add();l.name=S.layers[i].name;}
            var initial=doc.layers[doc.layers.length-1];if(initial.pageItems.length===0)initial.remove();
            for(var i=0;i<S.groups.length;i++){var def=S.groups[i],layer=null;for(var j=0;j<S.layers.length;j++)if(S.layers[j].id===def.layer)layer=doc.layers.getByName(S.layers[j].name);var g=layer.groupItems.add();g.name='LD_GROUP_'+def.id;groups[def.id]=g;}
            trace=new File(C.stem+'.drawing.jsonl');trace.encoding='UTF-8';if(!trace.open('w'))fail('Trace cannot open');
            var all={};for(var i=0;i<P.nodes.length;i++)all[P.nodes[i].id]=[P.nodes[i],'node'];for(var i=0;i<P.paths.length;i++)all[P.paths[i].id]=[P.paths[i],'path'];for(var i=0;i<P.edges.length;i++)all[P.edges[i].id]=[P.edges[i],'edge'];
            for(var i=0;i<P.draw_order.length;i++){var v=all[P.draw_order[i]];item(v[0],v[1]);}
            trace.close();trace=null;
            var so=new IllustratorSaveOptions();so.pdfCompatible=true;so.compressed=true;so.embedICCProfile=true;doc.saveAs(new File(C.ai),so);app.redraw();
            var r=summary();r.authored_objects=count;r.visible_native_creation=true;r.delay_ms=C.delay_ms;r.redraw_every=C.redraw_every;write(C.stem+'.render.json',r);return 'OK|'+count;
        }
        // Operate only on the named AI document; never adopt an arbitrary active file.
        checkpoint('open_named_document');
        for(var i=0;i<app.documents.length;i++){try{if(app.documents[i].fullName.fsName===new File(C.ai).fsName){doc=app.documents[i];break;}}catch(e){}}
        if(doc&&!doc.saved)fail('Named AI document has unsaved changes; preserve it');
        if(doc)doc.close(SaveOptions.DONOTSAVECHANGES);
        doc=app.open(new File(C.ai));owned=true;doc.activate();doc.views[0].centerPoint=[W/2,H/2];doc.views[0].zoom=Math.min(.8,1000/W);app.redraw();
        var result=summary();result.text=[];result.edge_checks=[];result.geometry_checks=[];result.movement=[];var problems=[];
        checkpoint('inspect_native_objects');
        var nb={};for(var i=0;i<P.nodes.length;i++)nb[P.nodes[i].id]=P.nodes[i];
        for(var i=0;i<P.nodes.length;i++){
            var n=P.nodes[i],o=find('LD_'+n.id);
            if(n.text){var t=o.typename==='TextFrame'?o:find('LD_'+n.id+'__text');var b=inkBounds(t),fit=(b[2]-b[0])<=n.bbox[2]*k+.5&&(b[1]-b[3])<=n.bbox[3]*k+.5;var ok=t.contents===(n.native_text||n.text).replace(/\n/g,'\r');
                var runsOk=true;if(n.text_runs)for(var ri=0;ri<n.text_runs.length;ri++){var run=n.text_runs[ri];for(var q=run.start;q<run.start+run.length;q++){var attr=t.characters[q].characterAttributes;if(run.baseline&&attr.baselinePosition!==(run.baseline==='subscript'?FontBaselineOption.SUBSCRIPT:FontBaselineOption.SUPERSCRIPT))runsOk=false;if(run.font&&attr.textFont.name!==run.font)runsOk=false;}}
                var s=n.style||{},left=n.bbox[0]*k,top=H-n.bbox[1]*k,ww=n.bbox[2]*k,hh=n.bbox[3]*k,align=typeof s.align==='number'?s.align:1;
                if(align===2)left+=ww-(b[2]-b[0]);else if(align!==0)left+=(ww-(b[2]-b[0]))/2;
                var posErr=Math.max(Math.abs(b[0]-left),Math.abs(b[1]-(top-(hh-(b[1]-b[3]))/2)));
                result.text.push({id:n.id,passed:ok&&runsOk&&posErr<.02,fit:fit,font:t.textRange.characterAttributes.textFont.name,bounds:b,native_text:t.contents,source_text:n.text,ranges_verified:runsOk,position_error_pt:posErr});if(!ok||!fit||!runsOk||posErr>=.02)problems.push('Text mismatch/fit/range/position '+n.id);}
            if(n.type==='bezier'||n.type==='polygon'||n.type==='compound'){
                var expect=n.type==='compound'?n.contours.length:1,observed=n.type==='compound'?o.pathItems.length:1,geo={id:n.id,passed:observed===expect,contours:observed,max_error_pt:0};
                for(var gi=0;gi<expect&&gi<observed;gi++){
                    var co=n.type==='compound'?n.contours[gi]:{points:n.points,curve:n.type==='bezier'?'bezier':'polyline'},p=n.type==='compound'?find('LD_'+n.id+'__contour_'+gi):o,gg=geometry(p,co.points,co.curve||'polyline',true);
                    geo.passed=geo.passed&&gg.passed;geo.max_error_pt=Math.max(geo.max_error_pt,gg.max_error_pt||0);
                }
                result.geometry_checks.push(geo);if(!geo.passed)problems.push('Native contour/handles '+n.id);
            }
        }
        for(var i=0;i<P.paths.length;i++){
            var n=P.paths[i],p=find('LD_'+n.id+'__path'),gg=geometry(p,n.points,n.curve||'polyline',false);gg.id=n.id;result.geometry_checks.push(gg);if(!gg.passed)problems.push('Native path/handles '+n.id);
        }
        for(var i=0;i<P.edges.length;i++){
            var e=P.edges[i],o=find('LD_'+e.id+'__path'),a=o.pathPoints[0].anchor,b=o.pathPoints[o.pathPoints.length-1].anchor,u=xy(e.points[0]),v=xy(e.points[e.points.length-1]);
            var err=Math.max(Math.abs(a[0]-u[0]),Math.abs(a[1]-u[1]),Math.abs(b[0]-v[0]),Math.abs(b[1]-v[1]));var hasArrow=!e.arrow||!!find('LD_'+e.id+'__arrow');
            var refs=[e.source,e.target],ends=[a,b],nativeErr=0;
            for(var q=0;q<2;q++){var bb=find('LD_'+refs[q].node).geometricBounds,uv=refs[q].anchor,xx=bb[0]+(bb[2]-bb[0])*uv[0],yy=bb[1]-(bb[1]-bb[3])*uv[1];nativeErr=Math.max(nativeErr,Math.abs(ends[q][0]-xx),Math.abs(ends[q][1]-yy));}
            var meta=eval('('+find('LD_'+e.id).note+')'),metaOk=meta.source.node===e.source.node&&meta.target.node===e.target.node;
            result.edge_checks.push({id:e.id,source:e.source.node,target:e.target.node,max_endpoint_error_pt:err,native_anchor_error_pt:nativeErr,metadata_verified:metaOk,arrow:!!e.arrow,passed:err<.01&&nativeErr<.02&&hasArrow&&metaOk});if(err>=.01||nativeErr>=.02||!hasArrow||!metaOk)problems.push('Edge '+e.id);
        }
        // Whole-panel movement checks internal relative geometry; no live connectors claim.
        for(var i=0;i<S.groups.length;i++){
            var def=S.groups[i];if(!def.test_move)continue;
            var g=find('LD_GROUP_'+def.id),objs=leaves(g,[]),before=[];for(var j=0;j<objs.length;j++)before.push(objs[j].geometricBounds);
            g.translate(7.5,-3.75);var maxErr=0;
            for(var j=0;j<objs.length;j++){var bb=objs[j].geometricBounds;maxErr=Math.max(maxErr,Math.abs(bb[0]-before[j][0]-7.5),Math.abs(bb[1]-before[j][1]+3.75));}
            g.translate(-7.5,3.75);var restore=0;for(var j=0;j<objs.length;j++){var bb=objs[j].geometricBounds;for(var q=0;q<4;q++)restore=Math.max(restore,Math.abs(bb[q]-before[j][q]));}
            result.movement.push({group:def.id,leaves:objs.length,max_error_pt:maxErr,restore_error_pt:restore,passed:maxErr<.02&&restore<.02});if(maxErr>=.02||restore>=.02)problems.push('Movement '+def.id);
        }
        // Discard temporary movements and reopen unchanged bytes before exporting.
        checkpoint('reopen_after_movement');
        doc.close(SaveOptions.DONOTSAVECHANGES);doc=app.open(new File(C.ai));doc.activate();doc.views[0].centerPoint=[W/2,H/2];doc.views[0].zoom=Math.min(.8,1000/W);
        checkpoint('export_png');
        var png=new ExportOptionsPNG24();png.antiAliasing=true;png.transparency=false;png.artBoardClipping=true;png.horizontalScale=100/k;png.verticalScale=100/k;doc.exportFile(new File(C.stem+'.png'),ExportType.PNG24,png);
        var svg=new ExportOptionsSVG();svg.coordinatePrecision=4;svg.cssProperties=SVGCSSPropertyLocation.PRESENTATIONATTRIBUTES;svg.documentEncoding=SVGDocumentEncoding.UTF8;svg.fontType=SVGFontType.SVGFONT;svg.fontSubsetting=SVGFontSubsetting.GLYPHSUSED;svg.embedRasterImages=false;doc.exportFile(new File(C.stem+'.svg'),ExportType.SVG,svg);
        // app.open(C.ai) can return the SAME document, not a disposable copy.
        // Open distinct bytes at a distinct path before PDF saveAs/close.
        checkpoint('export_pdf_from_separate_copy');
        var tempFile=new File(C.stem+'.pdf-source.ai'),temp=null;
        if(tempFile.exists)fail('Temporary PDF source already exists');
        if(!(new File(C.ai)).copy(tempFile.fsName))fail('Cannot copy PDF source');
        try{temp=app.open(tempFile);var pdf=new PDFSaveOptions();pdf.preserveEditability=false;pdf.generateThumbnails=false;temp.saveAs(new File(C.stem+'.pdf'),pdf);}
        finally{if(temp)temp.close(SaveOptions.DONOTSAVECHANGES);if(tempFile.exists)tempFile.remove();}
        doc.activate();doc.views[0].centerPoint=[W/2,H/2];doc.views[0].zoom=Math.min(.8,1000/W);app.redraw();
        result.failures=problems;result.passed=problems.length===0&&result.raster_items===0&&result.placed_items===0&&result.non_native_items===0;result.roundtrip=true;result.native_dynamic_connectors=false;result.visible=true;
        result.total_elapsed_ms=now()-started;write(C.stem+'.audit.json',result);write(C.stem+'.verify-progress.json',{stage:'complete',complete:true,passed:result.passed});return 'OK|'+result.passed;
    }catch(err){
        if(trace){trace.writeln(enc({error:String(err),line:err.line,created:count}));trace.close();}
        write(C.stem+'.failure.json',{passed:false,error:String(err),line:err.line,created:count,owned_document:owned});throw err;
    }finally{app.userInteractionLevel=oldInteraction;}
})(LD_CONFIG);
