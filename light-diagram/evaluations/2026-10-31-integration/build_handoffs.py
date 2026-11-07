"""Retrospectively connect existing, completed native cases to the parent workflow.

No image generation, native drawing or global skill installation is performed.
"""
from pathlib import Path
import hashlib,json,os
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def load(p):return json.loads(p.read_text('utf-8-sig'))
def file_ref(p):return {'path':os.path.relpath(p,HERE).replace('\\','/'),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

def main():
    configs=[
        ('illustrator',ROOT/'light-illustrator-diagram/evaluations/2026-10-30-lis-comparison','output/lis-illustrator.ai','output/lis-illustrator.png','output/lis-illustrator.audit.json','reference-prompt-v1.txt','Fine vector editing, real compound openings, gradients, layers and panel grouping.'),
        ('powerpoint',ROOT/'light-powerpoint-diagram/evaluations/2026-10-30-lis-complex','output/lis-final-r2.pptx','output/lis-corrected.png','output/lis.audit.json','prompt-v1.txt','Editable PPTX for slide use and team editing, including native connectors.'),
        ('visio',ROOT/'light-visio-diagram/evaluations/2026-10-30-monoformer','monoformer-final.vsdx','monoformer-final-corrected.png','monoformer-final.audit.json','prompt-v2-edit.txt','Dense architecture with node glue and native movement checks in VSDX.')]
    paths=[]
    for tool,case,native,png,audit,prompt,reason in configs:
        source=load(case/'source-manifest.json');scene=load(case/'scene.json')
        is_lis=tool!='visio'
        issues=source.get('reference_issues',source.get('generated_image_review',{}).get('issues',[]))
        if not is_lis:issues=['Source generation retained extra bypasses, reversed source arrowheads and ambiguous/dangling skip routes; see the prior REPORT and corrected scene page.']
        corrections=source.get('native_scientific_corrections',scene.get('provenance',{}).get('corrections',[]))
        if not corrections:corrections=['Apply the corrected scientific graph on page 2; preserve page 1 as labelled reference replica. Specific deleted/reconnected edges and rationale are recorded in the prior REPORT and scene.']
        files={'reference':case/'source.png','prompt':case/prompt,'scene':case/'scene.json','relation_spec':case/'scene.json','source_record':case/'source-manifest.json','report':case/'REPORT.md','native_audit':case/audit,'verification':case/'verification.json','final_native':case/native,'preview':case/png}
        data={'schema_version':'1.0','task_id':f'historical-{tool}-integration','record_context':'Retrospective indexing of a previously completed case. No image generation or native drawing repeated on 2026-10-31.','input_kind':'existing_image','output_mode':'editable','stage':'delivered','brief':{'domain':'Materials electrochemistry' if is_lis else 'Computer vision / depth estimation','visual_claim':'Coupled cell transport, sulfur conversion, separator mechanism and anode interface.' if is_lis else 'Multilevel Transformer encoding, attention connection and feature-fusion depth decoding.','evidence_boundary':source.get('evidence_boundary','Conceptual forward graph; no model performance, empirical data or full implementation equivalence claimed.'),'source_scope':source.get('scientific_sources',source.get('paper_scope','See source record and prior report.'))},'artifacts':{k:file_ref(v) for k,v in files.items()},'generation':{'status':'reused','calls_this_run':0,'executed_prompt':None,'lineage':'Actual prior executed prompt and source generation are recorded in source_record; no new generation in this integration.'},'reference_review':{'status':'issues_recorded','issues':issues},'reconstruction':{'mode':'science_corrected','corrections':corrections,'scope':'Entire native file is the corrected conceptual figure.' if is_lis else 'Page 2 corrected; page 1 deliberately retains source errors and is not claimed scientifically correct.'},'routing':{'requested_tool':tool,'selected_tool':tool,'reason':'Historical tool-specific test: '+reason,'visible_process':True},'checks':{
        'file':{'status':'passed','scope':'Previously executed file/native verification; current integration rechecks file identity only.','evidence':['verification','native_audit']},
        'native':{'status':'passed','scope':'Prior real desktop save/reopen, native objects and movement within the stated backend report limits; not rerun today.','evidence':['native_audit','verification']},
        'visual':{'status':'passed','scope':'Prior actual application export was inspected; geometric textures and particle placements remain approximations, not 1:1 fidelity.','evidence':['report','preview']},
        'science':{'status':'passed','scope':'Prior same-assistant conceptual relationship review and explicit corrections, not independent peer review. '+('' if is_lis else 'Only corrected page 2; source-replica page 1 retains labelled errors.'),'evidence':['report','verification','relation_spec']}}}
        if tool=='visio':data['checks']['native']['binding_record']='verification'
        dest=HERE/f'handoff-{tool}.json';dest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');paths.append(dest.name)
    print(json.dumps({'retrospective_handoffs':paths,'new_generation_calls':0,'native_redraws':0},ensure_ascii=False))

if __name__=='__main__':main()
