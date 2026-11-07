"""Measured test scene; coordinates are pixels in the inspected reference image."""
from pathlib import Path
import copy
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / 'light-diagram-prompt/evaluations/2026-10-27/01-transformer/image-v4-edit.png'
# HERE.parents[2] is light-diagram, not the skill directory.
if not SOURCE.exists():
    raise FileNotFoundError(SOURCE)
shutil.copy2(SOURCE, HERE / 'source.png')

nodes, paths, edges = [], [], []

def node(id, box, text='', fill='none', kind='roundrect', **style):
    n = {'id': id, 'type': kind, 'bbox': box, 'text': text,
         'radius_px': 10, 'style': {'fill': fill, 'font_px': 23, **style}}
    nodes.append(n)
    return id

def junction(id, x, y):
    return node(id, [x-.1, y-.1, .2, .2], kind='junction', stroke='none')

def label(id, box, text, size=25):
    return node(id, box, text, kind='text', stroke='none', font_px=size)

def anchor(id, uv):
    n = next(n for n in nodes if n['id'] == id)
    x,y,w,h = n['bbox']
    return [x+w*uv[0], y+h*uv[1]]

def edge(id, src, dst, bends=(), arrow=13):
    a,b = src,dst
    edges.append({'id': id, 'source': {'node': a[0], 'anchor': a[1]},
                  'target': {'node': b[0], 'anchor': b[1]},
                  'points': [anchor(*a), *[list(p) for p in bends], anchor(*b)],
                  'arrow': arrow, 'radius_px': 5,
                  'style': {'stroke': '#0b1532', 'stroke_px': 3.5}})

T,B,L,R,C = [0.5,0],[0.5,1],[0,.5],[1,.5],[.5,.5]
node('page_background', [0,0,1536,1024], fill='#ffffff', kind='rect', stroke='none')
node('encoder_container', [215,238,404,516], fill='#c2e4fc', fill_secondary='#cde9fc', stroke='#39a5ed', stroke_px=3.2)
nodes[-1]['radius_px']=18
node('decoder_container', [940,238,398,528], fill='#ffe0c2', fill_secondary='#ffe6ce', stroke='#ff8c28', stroke_px=3.2)
nodes[-1]['radius_px']=18

yellow, blue, purple, green, pink = '#ffeab1','#b9def8','#d9c9fa','#bce6d5','#f2c2ee'
node('enc_norm2', [284,271,278,51], 'Add & Norm', yellow)
node('enc_ff', [284,363,278,63], 'Feed Forward', blue)
node('enc_norm1', [284,480,278,56], 'Add & Norm', yellow)
node('enc_attention', [284,574,278,100], 'Multi-Head\nSelf-Attention', purple)
node('inputs', [284,950,278,54], 'Inputs', green)
node('input_embedding', [284,870,278,51], 'Input Embedding', pink)
node('enc_position', [142,785,174,67], 'Positional\nEncoding', blue, font_px=23)
node('enc_add', [395,788,52,52], '+', '#f7f7fb', kind='ellipse', font_px=34)

node('dec_norm3', [1022,258,257,45], 'Add & Norm', yellow)
node('dec_ff', [1022,330,257,49], 'Feed Forward', blue)
node('dec_norm2', [1022,417,257,47], 'Add & Norm', yellow)
node('cross_attention', [1022,489,257,55], 'Cross-Attention', purple, font_px=24)
node('dec_norm1', [1022,587,257,48], 'Add & Norm', yellow)
node('masked_attention', [1022,657,257,74], 'Masked\nSelf-Attention', purple)
node('shifted_outputs', [1024,950,258,54], 'Shifted Outputs', green)
node('output_embedding', [1024,871,258,50], 'Output Embedding', pink)
node('dec_position', [893,786,169,66], 'Positional\nEncoding', blue, font_px=23)
node('dec_add', [1122,790,51,51], '+', '#f7f7fb', kind='ellipse', font_px=34)
node('linear', [995,166,285,43], 'Linear', purple)
node('softmax', [995,91,285,48], 'Softmax', green)
node('probabilities', [995,14,285,50], 'Output Probabilities', green)

# Mild gradients approximate the raster reference while keeping every fill editable.
for n in nodes:
    if n['style'].get('fill') in (yellow, blue, purple, green, pink):
        n['style']['fill_secondary'] = {
            yellow:'#fff0c4',blue:'#c5e6fd',purple:'#e1d4fc',green:'#cfeddf',pink:'#f5d1f1'
        }[n['style']['fill']]

label('encoder_label', [36,274,143,40], 'Encoder', 30)
label('decoder_label', [1383,274,150,40], 'Decoder', 30)
label('encoder_repeat', [67,500,113,35], '6 layers', 26)
label('decoder_repeat', [1374,500,113,35], '6 layers', 26)
label('memory_label', [811,468,57,31], 'K,V', 25)
label('query_label', [1110,550,26,29], 'Q', 25)

for id,x,y in [('enc_input_branch',421,704),('enc_memory',421,188),
               ('memory_split',971,502),('dec_input_branch',1147.5,747)]:
    junction(id,x,y)

paths.extend([
 {'id':'encoder_brace','points':[[201,270],[195,271],[191,277],[191,502],[188,512],
     [181,519],[188,525],[191,534],[191,733],[195,741],[201,744]],
  'arrow':0,'radius_px':7,'style':{'stroke':'#0b1532','stroke_px':3.5}},
 {'id':'decoder_brace','points':[[1351,271],[1356,273],[1359,280],[1359,502],[1362,512],
     [1369,519],[1362,525],[1359,534],[1359,735],[1356,743],[1351,747]],
  'arrow':0,'radius_px':7,'style':{'stroke':'#0b1532','stroke_px':3.5}},
 # The reference draws an arrowhead part-way up a continuous memory line.
 {'id':'memory_arrowhead','points':[[421,222],[421,201]],'arrow':13,
  'style':{'stroke':'#0b1532','stroke_px':3.5}},
 {'id':'enc_input_arrowhead','points':[[421,780],[421,757]],'arrow':13,
  'style':{'stroke':'#0b1532','stroke_px':3.5}},
 {'id':'dec_input_arrowhead','points':[[1147.5,782],[1147.5,766]],'arrow':13,
  'style':{'stroke':'#0b1532','stroke_px':3.5}},
])

edge('inputs_to_embedding',('inputs',T),('input_embedding',B))
edge('input_embedding_to_add',('input_embedding',T),('enc_add',B),[(421,852)])
edge('enc_position_to_add',('enc_position',R),('enc_add',L))
edge('enc_add_to_branch',('enc_add',T),('enc_input_branch',C),arrow=0)
edge('enc_branch_to_attention',('enc_input_branch',C),('enc_attention',[137/278,1]))
edge('enc_attention_to_norm',('enc_attention',[137/278,0]),('enc_norm1',[137/278,1]))
edge('enc_attention_residual',('enc_input_branch',C),('enc_norm1',L),[(240,704),(240,508)])
edge('enc_norm_to_ff',('enc_norm1',[137/278,0]),('enc_ff',[137/278,1]))
edge('enc_ff_to_norm',('enc_ff',[137/278,0]),('enc_norm2',[137/278,1]))
edge('enc_ff_residual',('enc_norm1',[35/278,0]),('enc_norm2',L),[(319,465),(240,465),(240,296.5)])
edge('enc_to_memory',('enc_norm2',[137/278,0]),('enc_memory',C),arrow=0)
edge('memory_to_split',('enc_memory',C),('memory_split',C),[(763,188),(763,502)],arrow=0)
edge('memory_to_cross',('memory_split',C),('cross_attention',[0,13/55]))

edge('outputs_to_embedding',('shifted_outputs',T),('output_embedding',B))
edge('output_embedding_to_add',('output_embedding',T),('dec_add',B),[(1147.5,855)])
edge('dec_position_to_add',('dec_position',R),('dec_add',L))
edge('dec_add_to_branch',('dec_add',T),('dec_input_branch',C),arrow=0)
edge('dec_branch_to_masked',('dec_input_branch',C),('masked_attention',[125.5/257,1]))
edge('masked_to_norm',('masked_attention',[125.5/257,0]),('dec_norm1',[125.5/257,1]))
edge('masked_residual',('dec_input_branch',C),('dec_norm1',L),[(971,747),(971,611)])
edge('norm_to_query',('dec_norm1',[125.5/257,0]),('cross_attention',[125.5/257,1]))
edge('cross_to_norm',('cross_attention',[125.5/257,0]),('dec_norm2',[125.5/257,1]))
edge('cross_residual',('dec_norm1',[1,0]),('dec_norm2',R),[(1320,587),(1320,440.5)])
edge('dec_norm_to_ff',('dec_norm2',[125.5/257,0]),('dec_ff',[125.5/257,1]))
edge('dec_ff_to_norm',('dec_ff',[125.5/257,0]),('dec_norm3',[125.5/257,1]))
edge('dec_ff_residual',('dec_norm2',[43/257,0]),('dec_norm3',L),[(1065,404),(971,404),(971,280.5)])
edge('extra_memory_to_norm',('memory_split',C),('dec_norm2',L),[(971,440.5)])
edge('decoder_to_linear',('dec_norm3',[125.5/257,0]),('linear',B))
edge('linear_to_softmax',('linear',T),('softmax',B))
edge('softmax_to_probabilities',('softmax',T),('probabilities',B))

replica = {'name':'01 Reference replica','slug':'replica','mode':'faithful',
           'nodes':nodes,'paths':paths,'edges':edges}
corrected = copy.deepcopy(replica)
corrected.update(name='02 Corrected topology',slug='corrected',mode='science-corrected')
corrected['edges']=[e for e in corrected['edges'] if e['id']!='extra_memory_to_norm']
scene={'schema_version':'1.0','font':'Arial',
       'canvas':{'width_px':1536,'height_px':1024,'pixels_per_inch':100},
       'provenance':{'source':'source.png','source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
           'method':'Manual visual inventory and pixel measurements; no automatic image parsing.',
           'scientific_source':'https://arxiv.org/abs/1706.03762',
           'changes':{'replica':[], 'corrected':['Remove extra_memory_to_norm: K,V memory must not bypass cross-attention into the following Add & Norm.']}},
       'pages':[replica,corrected]}
(HERE/'scene.json').write_text(json.dumps(scene,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'source-manifest.json').write_text(json.dumps({
    'source_file':'source.png','source_sha256':scene['provenance']['source_sha256'],
    'original_file':str(SOURCE),'image_origin':'Earlier light-diagram-prompt live image-generation test; not the original paper figure.',
    'paper':'Vaswani et al. Attention Is All You Need (2017)',
    'paper_url':'https://arxiv.org/abs/1706.03762',
    'reference_repository_root':'Reference  Repositories/工具',
    'scope':'Native Visio reconstruction test; not a new image-generation run.'},
    ensure_ascii=False,indent=2),encoding='utf-8')
print('Wrote source snapshot, provenance and two-page scene.')
