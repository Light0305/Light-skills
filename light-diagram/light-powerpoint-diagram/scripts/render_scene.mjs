/** Render a manually inspected pixel scene to editable PowerPoint geometry.
 * Author with the bundled @oai/artifact-tool. Connection-site serialization is
 * completed by attach_connectors.py; the source image is never inserted.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {pathToFileURL} from 'node:url';

import {validate} from './scene_validation.mjs';
export {validate} from './scene_validation.mjs';
const args = process.argv.slice(2);
if (!args.length) throw new Error('Usage: node render_scene.mjs scene.json [--validate-only | draft.pptx [artifact_tool.mjs]]');
const [sceneFile, outputFile, moduleFile] = args;
const scene = JSON.parse(await fs.readFile(sceneFile, 'utf8'));
const counts = validate(scene);
if(outputFile === '--validate-only') {
  console.log(JSON.stringify({valid:true,...counts,scope:'Offline scene validation only'}));
  process.exit(0);
}
if(!outputFile || path.extname(outputFile).toLowerCase()!=='.pptx')throw new Error('Specify a new output .pptx');
await fs.access(outputFile).then(() => {throw new Error('Refusing to overwrite: '+outputFile);}, e=>{if(e.code!=='ENOENT') throw e;});
const bundled = path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs');
const {Presentation, PresentationFile} = await import(pathToFileURL(moduleFile || process.env.ARTIFACT_TOOL_MODULE || bundled).href);

function contour(n) {
  const [x,y,w,h]=n.bbox;
  const M=(x,y)=>({moveTo:{x,y}}), L=(x,y)=>({lineTo:{x,y}}), C=(x1,y1,x2,y2,x,y)=>({cubicBezTo:{x1,y1,x2,y2,x,y}}), Z=()=>({close:{}});
  if(['polygon','bezier'].includes(n.type)) {
    const pts=n.points.map(p=>[p[0]-x,p[1]-y]); const cmds=[M(...pts[0])];
    if(n.type==='bezier') for(let i=1;i<pts.length;i+=3) cmds.push(C(...pts[i],...pts[i+1],...pts[i+2]));
    else for(const p of pts.slice(1)) cmds.push(L(...p));
    cmds.push(Z()); return cmds;
  }
  if(['ellipse','junction'].includes(n.type)) {
    const k=.5522847498307936, rx=w/2,ry=h/2;
    return [M(w,ry),C(w,ry+k*ry,rx+k*rx,h,rx,h),C(rx-k*rx,h,0,ry+k*ry,0,ry),C(0,ry-k*ry,rx-k*rx,0,rx,0),C(rx+k*rx,0,w,ry-k*ry,w,ry),Z()];
  }
  const r=n.type==='roundrect'?Math.min(n.radius_px??6,w/2,h/2):0, k=.5522847498307936;
  if(!r) return [M(0,0),L(w,0),L(w,h),L(0,h),Z()];
  return [M(r,0),L(w-r,0),C(w-r+k*r,0,w,r-k*r,w,r),L(w,h-r),C(w,h-r+k*r,w-r+k*r,h,w-r,h),L(r,h),C(r-k*r,h,0,h-r+k*r,0,h-r),L(0,r),C(0,r-k*r,r-k*r,0,r,0),Z()];
}
function stroke(st={}) {return {style:st.dash_pattern?'dashed':'solid',fill:st.stroke??'#101010',width:st.stroke==='none'?0:(st.stroke_px??1.3)};}
function fill(st={}) {return st.fill_secondary?{type:'gradient',gradientKind:'linear',angleDeg:90,stops:[{offset:0,color:st.fill},{offset:100000,color:st.fill_secondary}]}:(st.fill??'none');}
const presentation=Presentation.create({slideSize:{width:scene.canvas.width_px,height:scene.canvas.height_px}});
for(const page of scene.pages) {
  const slide=presentation.slides.add(); slide.background.fill='#ffffff';
  const entries=[...page.nodes.map(n=>[n.id,{...n,_node:true}]),...page.paths.map(n=>[n.id,n]),...page.edges.map(n=>[n.id,n])];
  const map=new Map(entries);
  for(const id of page.draw_order??entries.map(e=>e[0])) {
    const n=map.get(id); const st=n.style??{}; let box,commands;
    if(n._node) { box=n.bbox; commands=contour(n); }
    else {
      const xs=n.points.map(p=>p[0]),ys=n.points.map(p=>p[1]); const x=Math.min(...xs),y=Math.min(...ys);
      box=[x,y,Math.max(.01,Math.max(...xs)-x),Math.max(.01,Math.max(...ys)-y)];
      const q=n.points.map(p=>({x:p[0]-x,y:p[1]-y})); commands=[{moveTo:q[0]}];
      if(n.curve==='bezier') for(let i=1;i<q.length;i+=3) commands.push({cubicBezTo:{x1:q[i].x,y1:q[i].y,x2:q[i+1].x,y2:q[i+1].y,x:q[i+2].x,y:q[i+2].y}});
      else commands.push(...q.slice(1).map(p=>({lineTo:p})));
    }
    const [left,top,width,height]=box;
    const shape=slide.shapes.add({name:'Light_'+id,geometry:'custom',position:{left,top,width,height},fill:n._node?fill(st):'none',line:stroke(st),customPaths:[{width,height,commands}]});
    if(n.text) {
      shape.text=n.text;
      shape.text.style={typeface:scene.font??'Arial',fontSize:st.font_px??20,bold:st.bold??true,color:st.text_color??'#090d13',alignment:['left','center','right'][st.align??1],verticalAlignment:'middle',insets:0,wrap:'none',autoFit:'none'};
    }
  }
  slide.speakerNotes.text=`light-powerpoint-diagram. ${page.name}. Mode: ${page.mode}.\nReference: ${scene.provenance.source}; SHA256: ${scene.provenance.source_sha256}\nScientific source: ${scene.provenance.scientific_source}\n${page.mode==='faithful'?'Reproduces the generated image, including its documented scientific errors.':'Applies the explicitly documented scientific corrections.'}\nCorrections: ${(scene.provenance.corrections??[]).join('; ')}\nLimitations: ${(scene.provenance.limitations??[]).join('; ')}\nGeometry traced by an assistant, not automatic image recognition.`;
}
await fs.mkdir(path.dirname(path.resolve(outputFile)),{recursive:true});
await (await PresentationFile.exportPptx(presentation)).save(outputFile);
console.log(JSON.stringify({draft:path.resolve(outputFile),slides:scene.pages.length,nativeShapes:scene.pages.map(p=>p.nodes.length+p.paths.length+p.edges.length),authoring:'@oai/artifact-tool'}));
