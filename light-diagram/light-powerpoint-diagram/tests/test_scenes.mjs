import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,readdirSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {validate} from '../scripts/scene_validation.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
function scene(){return {
  schema_version:'1.0',font:'Arial',canvas:{width_px:400,height_px:200,pixels_per_inch:96},
  provenance:{source:'synthetic',source_sha256:'synthetic-only',scientific_source:'Synthetic geometry, no scientific claim'},
  pages:[{name:'Fixture',slug:'fixture',mode:'faithful',nodes:[
    {id:'A',type:'rect',bbox:[20,60,100,50],text:'A',style:{font_px:18}},
    {id:'B',type:'ellipse',bbox:[280,60,100,50],text:'B'}],paths:[],edges:[
    {id:'edge',points:[[120,85],[280,85]],source:{node:'A',anchor:[1,.5]},target:{node:'B',anchor:[0,.5]}}
  ]}]};}
test('valid scene',()=>assert.equal(validate(scene()).objects,3));
const cases={
  'root array':()=>[],
  'missing bbox':s=>{delete s.pages[0].nodes[0].bbox;},
  'empty path':s=>s.pages[0].paths.push({id:'p',points:[]}),
  'short polygon':s=>Object.assign(s.pages[0].nodes[0],{type:'polygon',points:[[1,1],[1,1]]}),
  'boolean canvas':s=>{s.canvas.width_px=true;},
  'infinite canvas':s=>{s.canvas.height_px=Infinity;},
  'bad scale metadata':s=>{s.canvas.pixels_per_inch=true;},
  'boolean point':s=>{s.pages[0].edges[0].points[0][0]=true;},
  'missing endpoint':s=>{s.pages[0].edges[0].target.node='missing';},
  'unknown curve':s=>{s.pages[0].edges[0].curve='magic';},
  'bad font size':s=>{s.pages[0].nodes[0].style.font_px=-1;},
  'bad color':s=>{s.pages[0].nodes[0].style.fill='#xxxxxx';},
  'gradient without base':s=>{s.pages[0].nodes[0].style.fill_secondary='#ffffff';},
  'invalid text range':s=>{s.pages[0].nodes[0].subscript_start=1;},
  'duplicate id':s=>{s.pages[0].nodes[1].id='A';},
  'reserved helper name':s=>{s.pages[0].nodes[1].id='B__seg_1';},
  'bad draw order':s=>{s.pages[0].draw_order=['A','B'];},
};
for(const [name,mutate] of Object.entries(cases))test(name,()=>{
  const s=scene();const result=mutate(s);assert.throws(()=>validate(Array.isArray(result)&&name==='root array'?result:s));
});
for(const directory of readdirSync(path.join(root,'evaluations'))){
  if(!directory.startsWith('2026-10-30-'))continue;
  const p=path.join(root,'evaluations',directory,'scene.json');
  test('historical scene '+directory,()=>assert.ok(validate(JSON.parse(readFileSync(p,'utf8')))));
}
test('validate-only does not load missing authoring module',()=>{
 const p=path.join(root,'evaluations/2026-10-30-monoformer/scene.json');
 const r=spawnSync(process.execPath,[path.join(root,'scripts/render_scene.mjs'),p,'--validate-only','Z:/missing/artifact.mjs'],{encoding:'utf8'});
 assert.equal(r.status,0,r.stderr);assert.equal(JSON.parse(r.stdout).valid,true);
});
