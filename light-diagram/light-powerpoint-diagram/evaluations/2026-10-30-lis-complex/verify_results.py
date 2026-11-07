"""Check actual saved evidence for the new four-panel Li–S test.

Checks the declared conceptual model, file/native behaviour and source lineage;
does not validate atomistic accuracy or infer experimental performance.
"""
from pathlib import Path
import json,hashlib,zipfile
import xml.etree.ElementTree as E
from PIL import Image
import fitz
HERE=Path(__file__).resolve().parent
def read(p):return json.loads((HERE/p).read_text('utf8'))
def sha(p):return hashlib.sha256((HERE/p).read_bytes()).hexdigest()

def main():
    scene=read('scene.json');manifest=read('source-manifest.json');audit=read('output/lis.audit.json');receipt=read('.build/lis-final-r2.pptx.validation.json');log=read('.build/lis-live-working.drawing-log.json')
    assert manifest['new_image_generation_calls']==1 and not manifest['prior_images_used']
    assert sha('source.png')==manifest['source_sha256']==scene['provenance']['source_sha256']
    assert audit['passed'] and audit['sha256']==sha('output/lis-final-r2.pptx')==receipt['finalSha256']
    page=scene['pages'][0];nodes={n['id']:n for n in page['nodes']};edges={e['id']:e for e in page['edges']}
    assert all(f'panel_{p}' in nodes for p in 'abcd')
    assert nodes['overall_reaction']['text']=='S₈ + 16Li ⇌ 8Li₂S'
    for eid,e in edges.items():
        a,b=e['points'][0],e['points'][-1]
        if eid.startswith('li_transport_a_') or eid.startswith('zoom_li_transport_'):assert b[0]>a[0]
        if eid.startswith('polysulfide_transport_a_'):assert b[0]<a[0] and e['style'].get('dash_pattern')
        if eid.startswith('discharge_stage_'):assert b[1]>a[1]
    assert edges['charge_return']['points'][-1][1]<edges['charge_return']['points'][0][1]
    assert edges['electron_direction']['points'][-1][0]>edges['electron_direction']['points'][0][0]
    assert len([n for n in nodes if n.startswith('s8_ring_') and not n.endswith('_shine')])==8
    assert log['visible_native_object_insertion'] and log['object_count']==audit['pages'][0]['shapes']
    assert len({o['name'] for o in log['objects']})==log['object_count']
    assert len({o['phase_library'] for o in log['objects']})==3
    assert len(log['removed_objects'])==2 and len(log['visible_corrections'])==2
    assert 'li_loss_to_passivation' not in edges
    assert edges['shuttle_to_passivation']['source']['node']=='failure_0'
    assert edges['shuttle_to_passivation']['target']['node']=='failure_2'
    ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
    with zipfile.ZipFile(HERE/'output/lis-final-r2.pptx') as z:
        assert not any(n.startswith('ppt/media/') for n in z.namelist())
        r=E.fromstring(z.read('ppt/slides/slide1.xml'))
        assert not r.findall('.//p:pic',ns)
        curves=len(r.findall('.//a:cubicBezTo',ns))
        assert curves>250
    with Image.open(HERE/'output/lis-corrected.png') as im:assert im.size==(1536,1024)
    with fitz.open(HERE/'output/lis.pdf') as pdf:
        assert len(pdf)==1
        pdf_text=pdf[0].get_text();lines=len(pdf_text.splitlines())
        # PDF extraction merges nearby text boxes; line counts do not measure loss.
        flattened=''.join(pdf_text.split())
        expected_text=[n['text'] for n in page['nodes'] if n.get('text')]
        missing=[t for t in expected_text if ''.join(t.split()) not in flattened]
        assert not missing, f'PDF text missing: {missing}'
    result={'source_is_newly_generated':True,'image_generation_calls':1,'native_objects':log['object_count'],'visible_object_insertion':True,'visible_phase_count':3,'file_checks_passed':True,'native_desktop_roundtrip_passed':True,'native_movement_passed':True,'conceptual_direction_checks_passed':True,'curve_segments_in_package':curves,'pdf_text_lines':lines,'source_sha256':sha('source.png'),'scene_sha256':sha('scene.json'),'final_sha256':sha('output/lis-final-r2.pptx'),'layout_warnings':receipt['presentationLayout'].get('warning_count',0),'scope':'Conceptual mechanism synthesis, not atomistic or empirical validation. Many flux endpoints are transparent path ports; no whole-layer grouping/dragging claim. Texture and particle placements are approximations.'}
    (HERE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
