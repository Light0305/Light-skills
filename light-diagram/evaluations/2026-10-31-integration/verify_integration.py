"""Exercise actual historical handoffs and reject stale or misleading declarations."""
from pathlib import Path
import copy,importlib.util,json
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('handoff',HERE.parents[1]/'scripts/validate_handoff.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def load(p):return json.loads(p.read_text('utf8'))

def main():
    results=[];docs={tool:load(HERE/f'handoff-{tool}.json') for tool in ('illustrator','powerpoint','visio')}
    def check(name,data,expected=True,error_fragment=None):
        r=module.validate(data,HERE);ok=r['passed']==expected
        if error_fragment:ok=ok and any(error_fragment in v for v in r['errors'])
        results.append({'case':name,'passed':ok,'expected_valid':expected,'observed_valid':r['passed'],'findings':r['errors']})
        if not ok:raise AssertionError(results[-1])
    for tool,d in docs.items():check('existing-'+tool+'-case',d)
    d=copy.deepcopy(docs['illustrator']);d['artifacts']['preview']['sha256']='0'*64;check('changed-preview-hash',d,False,'file hash changed')
    d=copy.deepcopy(docs['illustrator']);d['artifacts']['native_audit']=copy.deepcopy(docs['powerpoint']['artifacts']['native_audit']);check('audit-from-another-final-file',d,False,'native audit not bound')
    d=copy.deepcopy(docs['illustrator']);d['routing']['selected_tool']='visio';check('silent-tool-switch',d,False,'conflicts with explicit')
    d=copy.deepcopy(docs['illustrator']);d['generation']['status']='generated';check('old-reference-claimed-new-generation',d,False,'requires actual calls')
    d=copy.deepcopy(docs['illustrator']);d['checks']['native']={'status':'not_run','scope':'Native application unavailable','evidence':[]};check('delivered-without-native-test',d,False,'requires native evidence passed')
    d=copy.deepcopy(docs['illustrator']);d['reconstruction']['corrections']=[];check('source-errors-without-corrections',d,False,'require explicit corrections')
    d=copy.deepcopy(docs['illustrator']);d['reference_review']['status']='not_run';check('unreviewed-reference',d,False,'actually reviewed')
    d=copy.deepcopy(docs['illustrator']);d['artifacts']['reference']['path']='missing-source.png';check('missing-handoff-reference',d,False,'file missing')
    # Legitimate early exit: prompt-only does not need a generated reference or native editor.
    d=copy.deepcopy(docs['illustrator']);d.update(output_mode='prompt_only',input_kind='concept')
    d['artifacts']={k:v for k,v in d['artifacts'].items() if k in ('prompt','report')}
    d['generation']={'status':'not_run','calls_this_run':0,'executed_prompt':None};d['routing'].update(requested_tool=None,selected_tool=None)
    d['reference_review']={'status':'not_run','issues':[]}
    for k in ('file','science'):d['checks'][k]={'status':'passed','scope':'Existing written prompt quality evidence only; not generation.','evidence':['prompt','report']}
    for k in ('native','visual'):d['checks'][k]={'status':'not_applicable','scope':'Prompt-only task','evidence':[]}
    check('prompt-only-valid-without-native-file',d)
    # A real reference can also be delivered as an image without a native editor.
    d=copy.deepcopy(docs['illustrator']);d['output_mode']='image';d['checks']['native']={'status':'not_applicable','scope':'Image-only delivery','evidence':[]};d['routing'].update(requested_tool=None,selected_tool=None)
    check('image-only-valid-without-native-check',d)
    result={'passed':all(x['passed'] for x in results),'cases':results,'count':len(results),'scope':'File/index integration using prior real artifacts plus inconsistent-declaration rejection. No new image generation, native reconstruction or blind routing evaluation.'}
    (HERE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
