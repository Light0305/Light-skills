"""Check the saved artifacts and the declared critical graph, not model accuracy."""
from pathlib import Path
import hashlib,json,zipfile,xml.etree.ElementTree as ET
from PIL import Image
import fitz

HERE=Path(__file__).resolve().parent
STEM='monoformer-final'
def read(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
def sha(name):return hashlib.sha256((HERE/name).read_bytes()).hexdigest()
scene=read('scene.json');audit=read(STEM+'.audit.json');manifest=read('source-manifest.json')
assert audit['passed']
assert audit['scene_sha256']==sha('scene.json')
assert scene['provenance']['source_sha256']==sha('source.png')==manifest['source_sha256']
assert sha('source.png')==sha('image-v2-edit.png')
corrected=scene['pages'][1]
es={e['id']:e for e in corrected['edges']}
ns={n['id']:n for n in corrected['nodes']}
def relation(id,src,dst):
    e=es[id];assert e['source']['node']==src and e['target']['node']==dst
for i in range(1,5):
    assert all(f'{kind}_{i}' in ns for kind in ('transformer','acm','ffd'))
    relation(f'direct_skip_{i}',f'transformer_{i}',f'ffd_{i}')
    relation(f'z_to_acm_{i}',f'transformer_{i}',f'acm_{i}')
    relation(f'acm_output_1_{i}',f'acm_{i}',f'ffd_{i}')
    relation(f'acm_output_2_{i}',f'att_{i}_2',f'ffd_{i}')
for lower in (4,3,2):relation(f'decoder_{lower}_{lower-1}',f'ffd_{lower}',f'ffd_{lower-1}')
relation('z4_to_residual','z_map_4_front','residual_unit')
relation('residual_to_ffd4','residual_unit','ffd_4')
relation('ff_u_residual','ff_u','ff_final')
relation('ff_u_to_product','ff_u','ff_product')
assert 'ff_wrong_raw_bypass' not in es
assert not any(n['id'].startswith('floating_output_') for n in corrected['nodes'])
assert not any(p['id']=='ambiguous_common_bus' for p in corrected['paths'])
assert es['tr_residual2']['begin_arrow']==es['ff_u_residual']['begin_arrow']==0
assert [ns[f'state_x{i}']['text'] for i in range(5)]==['X0','X1','X2','X3','X4']
assert [ns['tr_norm1']['text'],ns['tr_norm2']['text']]==['Norm','Norm']

report={'actual_rendering':True,'native_audit_passed':True,'source_and_scene_hashes_match':True,
 'critical_corrected_graph_checks_passed':True,
 'generation_review':{'image_v1':'Failed: missing pre-MSA Norm, reversed inset output, duplicate X states; other ports ambiguous.',
  'image_v2':'Improved: Norm and state counts repaired; extra FFD bypass, reversed source arrowheads and dangling/overlapping skip routes remain.',
  'generation_science_passed':False,'imagegen_calls':2,'method':'Same-assistant visual inspection; no independent blind review.'},
 'corrected_scope':'Checks only the declared conceptual forward graph, not full implementation equivalence or model performance.',
 'pages':[],'artifacts_sha256':{name:sha(name) for name in ['source.png','image-v1.png','image-v2-edit.png',
    'style-reference.jpg','prompt-v1.txt','prompt-v2-edit.txt','scene.json',STEM+'.vsdx']}}
v={'v':'http://schemas.microsoft.com/office/visio/2012/main'}
with zipfile.ZipFile(HERE/(STEM+'.vsdx')) as z:
    assert not any(p.startswith('visio/media/') for p in z.namelist())
    for i,spec in enumerate(scene['pages'],1):
        page=ET.fromstring(z.read(f'visio/pages/page{i}.xml'))
        png=HERE/(STEM+'-'+spec['slug']+'.png')
        with Image.open(png) as im:assert im.size==(1774,887)
        svg=ET.parse(HERE/(STEM+'-'+spec['slug']+'.svg'))
        assert not any(el.tag.endswith('}image') for el in svg.iter())
        assert all(not audit['reopened_pages'][i-1][k] for k in ['glue_failures','text_failures','arrow_failures'])
        report['pages'].append({'name':spec['name'],'native_shapes':len(page.findall('.//v:Shape',v)),
         'saved_connects':len(page.findall('.//v:Connect',v)),'semantic_edges':len(spec['edges']),
         'movement_probe':audit['movement_probes'][i-1],'png_size':[1774,887],'svg_images':0})
with fitz.open(HERE/(STEM+'.pdf')) as pdf:
    assert len(pdf)==2
    report['pdf_pages']=2
    report['pdf_text_lines']=[len(p.get_text().splitlines()) for p in pdf]
(HERE/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'pages':report['pages'],'generation_science_passed':False},ensure_ascii=False,indent=2))
