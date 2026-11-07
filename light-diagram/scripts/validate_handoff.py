"""Check light-diagram handoff consistency, local file hashes and audit binding.

This does not generate an image, render native artwork or judge visual/scientific
correctness. A passed record is a consistency check of declared evidence only.
"""
from pathlib import Path
import argparse,hashlib,json,re
import math

TOOLS={'illustrator':'.ai','powerpoint':'.pptx','visio':'.vsdx'}
STATUS={'not_run','passed','failed','not_applicable'}

def _validate_legacy(data,base):
    errors=[];files={}
    def need(ok,msg):
        if not ok:errors.append(msg)
    need(data.get('schema_version')=='1.0','schema_version must be 1.0')
    need(bool(data.get('task_id')),'task_id missing')
    mode=data.get('output_mode');stage=data.get('stage');kind=data.get('input_kind')
    need(kind in {'paper','concept','existing_image'},'input_kind invalid')
    need(mode in {'prompt_only','image','editable'},'output_mode invalid')
    if 'requested_output_mode' in data:
        need(data['requested_output_mode'] in {'prompt_only','image','editable'},'requested_output_mode invalid')
    need(stage in {'planned','prompt_ready','reference_ready','reconstructing','delivered'},'stage invalid')
    brief=data.get('brief',{})
    for key in ('visual_claim','evidence_boundary','source_scope'):need(bool(brief.get(key)),f'brief.{key} missing')
    artifacts=data.get('artifacts',{});need(isinstance(artifacts,dict),'artifacts must be an object')
    if not isinstance(artifacts,dict):artifacts={}
    for key,ref in artifacts.items():
        if not isinstance(ref,dict):need(False,f'{key}: file reference must be object');continue
        raw=ref.get('path','');digest=ref.get('sha256','')
        need(bool(raw),f'{key}: path missing');need(bool(re.fullmatch('[0-9a-f]{64}',digest)),f'{key}: SHA-256 missing/invalid')
        if not raw:continue
        path=(base/raw).resolve();files[key]=path
        if not path.is_file():need(False,f'{key}: file missing {path}');continue
        need(file_hash(path)==digest,f'{key}: file hash changed')
    def artifact(key):need(key in files,f'artifact {key} required')
    gen=data.get('generation',{});calls=gen.get('calls_this_run');state=gen.get('status');ep=gen.get('executed_prompt')
    need(isinstance(calls,int) and not isinstance(calls,bool) and calls>=0,'generation calls invalid')
    need(state in {'not_run','generated','reused','failed'},'generation status invalid')
    if state=='generated':
        need(isinstance(calls,int) and calls>=1,'generated requires actual calls >=1');artifact('reference')
        need(bool(ep) and ep in files,'generated requires executed_prompt file reference')
    elif state=='failed':
        need(isinstance(calls,int) and not isinstance(calls,bool) and calls>=1,'failed requires actual calls >=1')
        need(bool(ep) and ep in files,'failed requires sent prompt file reference')
        need(gen.get('failure_record') in files,'failed requires failure_record artifact')
    else:need(calls==0,'reused/not_run requires 0 calls_this_run')
    if state=='not_run':need(ep is None,'not_run cannot have executed_prompt')
    if state=='reused':artifact('reference');artifact('source_record')
    if ep is not None:need(ep in files,'executed_prompt references missing artifact')
    selection=gen.get('selection')
    if selection is not None:
        need(selection in {'builtin','custom','prompt_only'},'generation.selection invalid')
        if state in {'generated','failed'}:need(selection in {'builtin','custom'},'actual calls require builtin/custom selection')
        if state in {'generated','failed'}:need('prompt_delivery' in data,'new generation requires prompt_delivery')
    delivery=data.get('prompt_delivery')
    if delivery is not None:
        need(isinstance(delivery,dict),'prompt_delivery must be object')
        if isinstance(delivery,dict):
            key=delivery.get('artifact');need(key in files,'prompt_delivery artifact missing')
            need(delivery.get('channel') in {'inline','file_link'},'prompt_delivery channel invalid')
            need(delivery.get('before_call') is True,'prompt must be delivered before call')
            if state in {'generated','failed'} and key in files and ep in files:
                need(artifacts[key].get('sha256')==artifacts[ep].get('sha256'),'executed prompt differs from delivered prompt')
    review=data.get('reference_review',{});need(review.get('status') in {'not_run','passed','issues_recorded'},'reference_review status invalid')
    issues=review.get('issues');need(isinstance(issues,list),'reference_review.issues must be list')
    if review.get('status')=='issues_recorded':need(bool(issues),'issues_recorded requires actual issues')
    rec=data.get('reconstruction',{});need(rec.get('mode') in {'faithful','science_corrected'},'reconstruction mode invalid')
    corrections=rec.get('corrections');need(isinstance(corrections,list),'corrections must be list')
    route=data.get('routing',{});tool=route.get('selected_tool');requested=route.get('requested_tool')
    need(tool is None or tool in TOOLS,'selected_tool invalid');need(requested is None or requested in TOOLS,'requested_tool invalid')
    need(isinstance(route.get('visible_process'),bool),'visible_process must be boolean')
    if requested is not None and tool is not None:need(requested==tool,'selected_tool conflicts with explicit requested_tool')
    if stage in {'reference_ready','reconstructing'} or (stage=='delivered' and mode!='prompt_only'):
        artifact('reference');need(state in {'generated','reused'},'reference must have generation or reuse lineage')
        need(review.get('status')!='not_run','reference must be actually reviewed')
    if stage=='prompt_ready' or (stage=='delivered' and mode=='prompt_only'):artifact('prompt')
    if stage=='reconstructing' or (stage=='delivered' and mode=='editable'):
        need(tool in TOOLS,'editable reconstruction requires selected_tool');need(bool(route.get('reason')),'routing reason required')
        if issues and rec.get('mode')=='science_corrected':need(bool(corrections),'source issues require explicit corrections')
        if issues and rec.get('mode')=='faithful':artifact('report')
    checks=data.get('checks',{})
    for key in ('file','native','visual','science'):
        c=checks.get(key,{});cs=c.get('status');ev=c.get('evidence',[])
        need(cs in STATUS,f'{key}: check status invalid');need(bool(c.get('scope')),f'{key}: scope missing');need(isinstance(ev,list),f'{key}: evidence must be list')
        if not isinstance(ev,list):continue
        for name in ev:need(name in files,f'{key}: missing evidence {name}')
        if cs in {'passed','failed'}:need(bool(ev),f'{key}: recorded result requires evidence')
    if stage=='delivered':
        required=('file','native','visual','science') if mode=='editable' else ('file','science') if mode=='prompt_only' else ('file','visual','science')
        for key in required:need(checks.get(key,{}).get('status')=='passed',f'delivered requires {key} evidence passed')
        if mode=='editable':
            for key in ('final_native','preview','scene','report','native_audit'):artifact(key)
            if tool in TOOLS and 'final_native' in files:need(files['final_native'].suffix.lower()==TOOLS[tool],'final file format does not match tool')
            audit_path=files.get('native_audit')
            if audit_path and audit_path.is_file():
                try:
                    audit=json.loads(audit_path.read_text('utf-8-sig'));need(audit.get('passed') is True,'native audit did not pass')
                    # Actual local audit names differ; do not invent one common backend API.
                    final_hash=artifacts.get('final_native',{}).get('sha256')
                    declared=audit.get('ai_sha256',audit.get('sha256'))
                    if declared is None:
                        # Legacy Visio audit has no final hash; use its contemporaneous
                        # verification index, which separately recorded file hashes.
                        binding_key=checks.get('native',{}).get('binding_record')
                        binding_path=files.get(binding_key)
                        if binding_path and binding_path.is_file():
                            binding=json.loads(binding_path.read_text('utf-8-sig'))
                            need(binding.get('native_audit_passed') is True,'binding record did not confirm native audit')
                            declared=binding.get('artifacts_sha256',{}).get(files['final_native'].name)
                            need(binding.get('artifacts_sha256',{}).get(files['scene'].name)==artifacts.get('scene',{}).get('sha256'),'binding record has another scene')
                    need(declared==final_hash,'native audit not bound to this final file hash')
                    scene_hash=audit.get('scene_sha256')
                    if scene_hash:need(scene_hash==artifacts.get('scene',{}).get('sha256'),'audit bound to another scene')
                except (ValueError,OSError,KeyError) as exc:need(False,f'native audit/binding unreadable: {exc}')
    return {'passed':not errors,'scope':'Handoff declarations, file hashes, stage requirements and native audit hash binding only; not rendering or scientific/visual verification.','task_id':data.get('task_id'),'stage':stage,'selected_tool':tool,'files_checked':len(files),'errors':errors}

def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    def constant(value):
        raise ValueError(f'Non-JSON numeric constant: {value}')
    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('Nonfinite JSON number: ' + value)
        return result
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite_float)


def validate(data, base):
    """Read-only consistency validation; legacy records remain readable.

    Version 1.1 binds check declarations to the files actually checked, not
    just the report containing the declaration. This cannot authenticate a
    human judgment or establish scientific correctness.
    """
    errors, warnings = [], []
    def need(ok, message):
        if not ok:
            errors.append(message)
    def obj(value, label):
        if not isinstance(value, dict):
            errors.append(f'{label} must be an object')
            return {}
        return value
    def string(value):
        return isinstance(value, str) and bool(value.strip())
    def sha(value):
        return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None
    def read_ref(ref, label):
        ref = obj(ref, label)
        raw, digest = ref.get('path'), ref.get('sha256')
        need(string(raw), f'{label}: path must be nonempty text')
        need(sha(digest), f'{label}: SHA-256 missing/invalid')
        if not string(raw):
            return None
        try:
            path = (Path(base) / raw).resolve()
            need(path.is_file(), f'{label}: file missing')
            if path.is_file() and sha(digest):
                need(file_hash(path) == digest, f'{label}: file hash changed')
            return path
        except (OSError, ValueError) as exc:
            errors.append(f'{label}: invalid or unreadable path: {exc}')
            return None

    data = obj(data, 'handoff')
    version = data.get('schema_version')
    need(version in ('1.0', '1.1'), 'schema_version must be 1.0 or 1.1')
    for key in ('brief', 'artifacts', 'generation', 'reference_review',
                'reconstruction', 'routing', 'checks'):
        obj(data.get(key), key)
    if isinstance(data.get('brief'), dict):
        for key in ('visual_claim', 'evidence_boundary', 'source_scope'):
            value = data['brief'].get(key)
            structured_scope = (key == 'source_scope' and isinstance(value, list) and bool(value)
                                and all(string(entry) or isinstance(entry, dict) and string(entry.get('scope'))
                                        for entry in value))
            need(string(value) or structured_scope, f'brief.{key} must be nonempty text or a structured source-scope list')
    artifacts = data.get('artifacts') if isinstance(data.get('artifacts'), dict) else {}
    for key, ref in artifacts.items():
        need(string(key), 'artifact key must be nonempty text')
        ref = obj(ref, f'artifact {key}')
        need(string(ref.get('path')), f'{key}: path must be nonempty text')
        need(sha(ref.get('sha256')), f'{key}: SHA-256 missing/invalid')
    checks = data.get('checks') if isinstance(data.get('checks'), dict) else {}
    for name in ('file', 'native', 'visual', 'science'):
        check = obj(checks.get(name), f'check {name}')
        need(string(check.get('scope')), f'{name}: scope must be nonempty text')
    result = {}
    if not errors:
        try:
            result = _validate_legacy(dict(data, schema_version='1.0'), Path(base))
            errors.extend(result['errors'])
        except (TypeError, AttributeError, KeyError, ValueError, OSError) as exc:
            errors.append(f'Invalid record structure or unreadable file: {exc}')
    if version == '1.0':
        warnings.append('Legacy 1.0: visual/science subjects and complete scene binding are not required.')
    if version == '1.1' and not errors:
        if data['generation'].get('status') in ('generated', 'failed'):
            need(data['generation'].get('selection') in ('builtin', 'custom'),
                 'new generation must declare actual builtin/custom selection')
            need(isinstance(data.get('prompt_delivery'), dict),
                 'new generation requires prompt_delivery')
        revision = data.get('revision')
        need(isinstance(revision, int) and not isinstance(revision, bool) and revision >= 1,
             'revision must be a positive integer')
        parent = data.get('parent')
        if parent is not None:
            path = read_ref(parent, 'parent')
            if path and path.is_file():
                try:
                    previous = obj(strict_json(path.read_text('utf-8-sig')), 'parent record')
                    need(previous.get('task_id') == data.get('task_id'), 'parent belongs to another task')
                    old_revision = previous.get('revision')
                    if previous.get('schema_version') == '1.0' and old_revision is None:
                        warnings.append('Parent is legacy 1.0 with no revision; its hash and task identity are bound.')
                    else:
                        need(isinstance(old_revision, int) and not isinstance(old_revision, bool)
                             and isinstance(revision, int) and old_revision < revision,
                             'parent revision must precede this revision')
                except (ValueError, OSError) as exc:
                    errors.append(f'Parent unreadable: {exc}')
        sources = data.get('science_sources', [])
        need(isinstance(sources, list), 'science_sources must be a list')
        source_keys = set()
        if isinstance(sources, list):
            for source in sources:
                source = obj(source, 'science source')
                key = source.get('artifact')
                need(string(key) and key in artifacts, 'science source artifact missing')
                need(string(source.get('locator')), 'science source locator missing')
                need(string(source.get('scope')), 'science source scope missing')
                if string(key):
                    source_keys.add(key)
            if not sources:
                warnings.append('No file-based scientific source declared; inspect brief/source scope.')
        if data['generation'].get('status') == 'generated':
            need('reference' not in source_keys, 'generated reference cannot be its own scientific source')
        if data.get('requested_output_mode', data['output_mode']) != data['output_mode']:
            need(data.get('requested_output_fulfilled') is False,
                 'fallback output must state requested_output_fulfilled=false')
            warnings.append('Delivered output differs from the requested output; original request remains unfulfilled.')
        for name in ('file', 'native', 'visual', 'science'):
            check = checks[name]
            if check.get('status') not in ('passed', 'failed'):
                continue
            subjects = obj(check.get('subjects'), f'{name}.subjects')
            need(bool(subjects), f'{name}: recorded result requires checked subjects')
            for key, digest in subjects.items():
                need(key in artifacts and sha(digest)
                     and artifacts.get(key, {}).get('sha256') == digest,
                     f'{name}: checked subject {key} is missing or changed')
        if data.get('stage') == 'delivered':
            mode = data['output_mode']
            if mode == 'editable':
                required = {
                    'file': {'final_native', 'scene', 'preview'},
                    'native': {'final_native', 'scene'},
                    'visual': {'final_native', 'preview', 'reference'},
                    'science': {'scene', 'preview', 'reference'} | source_keys,
                }
            elif mode == 'image':
                required = {'file': {'reference'}, 'visual': {'reference'},
                            'science': {'reference'} | source_keys}
            else:
                required = {'file': {'prompt'}, 'science': {'prompt'} | source_keys}
            for name, keys in required.items():
                subjects = checks.get(name, {}).get('subjects', {})
                need(isinstance(subjects, dict) and keys <= subjects.keys(),
                     f'{name}: missing required checked subjects {sorted(keys)}')
            if mode == 'editable':
                audit_path = Path(base) / artifacts['native_audit']['path']
                try:
                    audit = obj(strict_json(audit_path.read_text('utf-8-sig')), 'native audit')
                    need(audit.get('scene_sha256') == artifacts['scene']['sha256'],
                         'native audit must bind this scene hash')
                    need(audit.get('ai_sha256', audit.get('sha256')) == artifacts['final_native']['sha256'],
                         'native audit must bind this final file hash')
                except (ValueError, OSError) as exc:
                    errors.append(f'Native audit unreadable: {exc}')
    result.update(passed=not errors, errors=errors, warnings=warnings,
                  task_id=data.get('task_id'), stage=data.get('stage'))
    result.setdefault('scope', 'Declarations and file/hash bindings only; no rendering or scientific/visual judgment.')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('handoff',type=Path);a=p.parse_args()
    try:
        result=validate(strict_json(a.handoff.read_text('utf-8-sig')),a.handoff.resolve().parent)
    except (ValueError,OSError,TypeError,AttributeError,KeyError) as exc:
        result={'passed':False,'errors':[str(exc)],'scope':'Input parsing or file access only.'}
    print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['passed'] else 1)

if __name__=='__main__':main()
