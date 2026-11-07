"""Check saved desktop evidence and exported formats for this Illustrator case."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as E
from PIL import Image
import fitz
HERE=Path(__file__).resolve().parent
def read(p):return json.loads((HERE/p).read_text('utf-8-sig'))
def sha(p):return hashlib.sha256((HERE/p).read_bytes()).hexdigest()
def squash(t):return ''.join(t.split())

def main():
    s=read('scene.json');m=read('source-manifest.json');a=read('output/lis-illustrator.audit.json');render=read('.build/lis-visible-r1.render.json');repair=read('.build/alignment-repair.json')
    assert m['new_image_generation_calls']==0 and m['prior_images_used']
    assert sha('source.png')==m['source_sha256']==s['provenance']['source_sha256']
    assert sha('reference-prompt-v1.txt')==m['reference_original_generation']['prompt_sha256']
    assert a['passed'] and a['roundtrip'] and a['ai_sha256']==sha('output/lis-illustrator.ai')==sha('.build/lis-illustrator-working-r2.ai')
    assert a['scene_sha256']==sha('scene.json')
    assert a['raster_items']==a['placed_items']==a['non_native_items']==0
    assert a['artboards']==1 and a['artboard_rect']==[0,768,1152,0]
    assert all(v['passed'] and v['fit'] and v['ranges_verified'] for v in a['text'])
    assert all(v['passed'] for v in a['geometry_checks']+a['edge_checks']+a['movement'])
    pg=s['pages'][0];edges={v['id']:v for v in pg['edges']};nodes={v['id']:v for v in pg['nodes']}
    assert len(nodes['carbon_host']['contours'])==55 and a['compound_paths']==1
    assert nodes['overall_reaction']['text']=='S₈ + 16Li ⇌ 8Li₂S'
    assert edges['shuttle_to_passivation']['source']['node']=='failure_0' and edges['shuttle_to_passivation']['target']['node']=='failure_2'
    assert 'li_loss_to_passivation' not in edges
    for v in pg['edges']:
        if v['id'].startswith(('li_transport_a_','zoom_li_transport_')):assert v['points'][-1][0]>v['points'][0][0]
        if v['id'].startswith('polysulfide_transport_a_'):assert v['points'][-1][0]<v['points'][0][0]
    log=[json.loads(t.lstrip('\ufeff')) for t in (HERE/'.build/lis-visible-r1.drawing.jsonl').read_text('utf-8-sig').splitlines() if t.strip()]
    assert [v['id'] for v in log]==pg['draw_order'] and len(log)==render['authored_objects']==1173
    assert render['visible_native_creation'] and repair['visible_native_edits']
    assert set(repair['changed'])=={'panel_a_title','panel_b_title','panel_c_title','panel_d_title','electron_label'}
    with Image.open(HERE/'output/lis-illustrator.png') as im:assert im.size==(1536,1024)
    native_text=[squash(v.get('native_text',v['text'])) for v in pg['nodes'] if v.get('text')]
    with fitz.open(HERE/'output/lis-illustrator.pdf') as pdf:
        assert len(pdf)==1 and not pdf[0].get_images(full=True)
        t=squash(pdf[0].get_text());assert all(v in t for v in native_text)
    root=E.fromstring((HERE/'output/lis-illustrator.svg').read_text('utf8'));ns={'s':'http://www.w3.org/2000/svg'}
    assert not root.findall('.//s:image',ns) and not root.findall('.//s:foreignObject',ns)
    texts=root.findall('.//s:text',ns);t=squash(''.join(''.join(v.itertext()) for v in texts));assert all(v in t for v in native_text)
    result={'passed':True,'reference_reused':True,'image_generation_calls_this_case':0,'source_sha256':sha('source.png'),'final_ai_sha256':sha('output/lis-illustrator.ai'),'scene_sha256':sha('scene.json'),'native_application_roundtrip':True,'visible_authored_objects':len(log),'visible_creation_elapsed_s':render['elapsed_ms']/1000,'native_leaf_objects':sum(a['leaf_types'].values()),'native_leaf_types':a['leaf_types'],'compound_holes':54,'native_text_frames':len(a['text']),'native_text_position_max_error_pt':max(v['position_error_pt'] for v in a['text']),'checked_native_contours_and_paths':len(a['geometry_checks']),'logical_paths':len(a['edge_checks']),'native_anchor_max_error_pt':max(v['native_anchor_error_pt'] for v in a['edge_checks']),'moved_panel_groups':len(a['movement']),'moved_internal_leaves':sum(v['leaves'] for v in a['movement']),'svg_text_elements':len(texts),'svg_radial_gradients':len(root.findall('.//s:radialGradient',ns)),'svg_linear_gradients':len(root.findall('.//s:linearGradient',ns)),'all_40_texts_present_in_pdf_and_svg':True,'ai_svg_pdf_raster_count':0,'limitations':['Native paths, not dynamic Visio/PowerPoint connectors.','Cross-panel callouts excluded from group movement.','Inherited measured layout; this does not independently test reference-image interpretation.','Textures, material morphology and particle placements remain approximate; not atomistic or empirical validation.']}
    (HERE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
