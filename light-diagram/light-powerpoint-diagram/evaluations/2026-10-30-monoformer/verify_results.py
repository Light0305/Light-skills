"""Verify this saved scientific-diagram fixture and its evidence boundaries."""
from pathlib import Path
import hashlib,json,zipfile
import xml.etree.ElementTree as E
from PIL import Image
import fitz

HERE=Path(__file__).resolve().parent
def read(p):return json.loads((HERE/p).read_text('utf8'))
def sha(p):return hashlib.sha256((HERE/p).read_bytes()).hexdigest()
scene=read('scene.json');audit=read('output/monoformer.audit.json');receipt=read('.build/monoformer-final.pptx.validation.json')
assert audit['passed'] and audit['sha256']==sha('output/monoformer-final.pptx')==receipt['finalSha256']
assert sha('source.png')==scene['provenance']['source_sha256']
assert not audit['errors'] and not audit['media_entries']
corrected=scene['pages'][1];edges={e['id']:e for e in corrected['edges']};nodes={n['id']:n for n in corrected['nodes']}
def relation(eid,source,target):
    e=edges[eid];assert e['source']['node']==source and e['target']['node']==target
for i in range(1,5):
    assert all(f'{k}_{i}' in nodes for k in ('transformer','acm','ffd'))
    relation(f'direct_skip_{i}',f'transformer_{i}',f'ffd_{i}')
    relation(f'z_to_acm_{i}',f'transformer_{i}',f'acm_{i}')
    relation(f'acm_output_1_{i}',f'acm_{i}',f'ffd_{i}')
    relation(f'acm_output_2_{i}',f'att_{i}_2',f'ffd_{i}')
for i in (4,3,2):relation(f'decoder_{i}_{i-1}',f'ffd_{i}',f'ffd_{i-1}')
relation('z4_to_residual','z_map_4_front','residual_unit');relation('residual_to_ffd4','residual_unit','ffd_4')
relation('ff_u_residual','ff_u','ff_final');relation('ff_u_to_product','ff_u','ff_product')
assert 'ff_wrong_raw_bypass' not in edges
assert not any(n['id'].startswith('floating_output_') for n in corrected['nodes'])
assert not any(p['id']=='ambiguous_common_bus' for p in corrected['paths'])
assert edges['tr_residual2']['begin_arrow']==edges['ff_u_residual']['begin_arrow']==0
assert [nodes[f'state_x{i}']['text'] for i in range(5)]==['X0','X1','X2','X3','X4']
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
with zipfile.ZipFile(HERE/'output/monoformer-final.pptx') as z:
    assert not any(n.startswith('ppt/media/') for n in z.namelist())
    for i,p in enumerate(scene['pages'],1):
        root=E.fromstring(z.read(f'ppt/slides/slide{i}.xml'))
        assert len(root.findall('.//p:cxnSp',ns))==audit['pages'][i-1]['native_connector_segments']
        assert len(root.findall('.//a:stCxn',ns))+len(root.findall('.//a:endCxn',ns))==audit['pages'][i-1]['connected_segment_endpoints']
        assert not root.findall('.//p:pic',ns)
        with Image.open(HERE/f'output/monoformer-{p["slug"]}.png') as im:assert im.size==(1774,887)
        assert all(m['passed'] for m in audit['pages'][i-1]['movement'])
with fitz.open(HERE/'output/monoformer.pdf') as pdf:
    assert len(pdf)==2
    text_counts=[len(p.get_text().splitlines()) for p in pdf]
    assert all(n>55 for n in text_counts)
report={
 'file_checks_passed':True,'desktop_powerpoint_roundtrip_verified':True,'native_movement_verified':True,
 'corrected_critical_graph_passed':True,'scope':'Declared conceptual relationships only, not implementation equivalence, cross-platform compatibility, or model accuracy.',
 'new_image_generation_calls':0,'generation_source':'Reused the actual light-diagram-prompt MonoFormer image-v2-edit from the preceding Visio evaluation.',
 'source_generation_science_passed':False,'native_only':True,'source_sha256':sha('source.png'),'scene_sha256':sha('scene.json'),'final_sha256':sha('output/monoformer-final.pptx'),
 'shapes':[p['shapes'] for p in audit['pages']],
 'logical_edges':[p['logical_edges'] for p in audit['pages']],
 'native_connector_segments':[p['native_connector_segments'] for p in audit['pages']],
 'connected_segment_endpoints':[p['connected_segment_endpoints'] for p in audit['pages']],
 'moved_scene_nodes':[len(p['movement']) for p in audit['pages']],
 'moved_scene_endpoints':[sum(m['tested_endpoints'] for m in p['movement']) for p in audit['pages']],
 'pdf_text_lines':text_counts,'visual_review':'Same assistant inspected both full-size native exports. No independent blind review.',
 'layout_warning_count':len(receipt['presentationLayout'].get('warnings',[])),
 'layout_warning_review':'Eight bounding-box overlap diagnostics: residual initialization route below X4 glyphs and right residual route within wide Greek-label boxes. Full-size native renders show no line crossing the visible glyphs.'
}
(HERE/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))
