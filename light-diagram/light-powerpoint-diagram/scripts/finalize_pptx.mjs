/** Run the installed Presentations skill finalizer on a reviewed native PPTX.
 * Usage: node finalize_pptx.mjs scene.json candidate.pptx final.pptx skill_dir python_executable
 * Set RUNTIME_NODE_MODULES to the bundled Node packages before running.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [scenePath,candidate,final,skillDir,pythonExecutable]=process.argv.slice(2);
if(!pythonExecutable)throw new Error('Expected scene, candidate, final, Presentations skill directory and runtime Python executable');
if(path.resolve(candidate)===path.resolve(final))throw new Error('Candidate and final must be different files');
await fs.access(final).then(()=>{throw new Error('Refusing to overwrite: '+final);},e=>{if(e.code!=='ENOENT')throw e;});
const scene=JSON.parse(await fs.readFile(scenePath,'utf8'));
const workspaceDir=path.dirname(path.resolve(scenePath));
const {finalizePresentation}=await import(pathToFileURL(path.join(skillDir,'container_tools/artifact_tool_utils.mjs')).href);
await fs.mkdir(path.dirname(path.resolve(final)),{recursive:true});
const receiptPath=path.join(workspaceDir,'.build',path.basename(final)+'.validation.json');
const result=await finalizePresentation({
  explicitTotalSlideCount:scene.pages.length,
  requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
  workspaceDir,candidatePath:path.resolve(candidate),finalPath:path.resolve(final),
  pythonExecutable:path.resolve(pythonExecutable),
  integrityValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu',`${Math.round(scene.canvas.width_px*9525)},${Math.round(scene.canvas.height_px*9525)}`,'--validate-bullet-geometry','--validate-heading-fit'],
  fontPolicy:{basis:'design',families:[scene.font??'Arial']},
  verifyArtifactToolImport:true,receiptPath,
});
console.log(JSON.stringify({final:path.resolve(final),receiptPath,result}));
