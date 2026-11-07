"""Opt-in native smoke: synthetic geometry only, no generation/API calls.

Run with a NEW output directory. Requires the existing local authoring runtime,
Windows apps and pywin32. Leaves only its own saved drawings open for inspection.
These checks do not establish scientific accuracy or visual fidelity.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    log=[]
    def run(label,*args):
        start=time.monotonic()
        result=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
        log.append(dict(step=label,returncode=result.returncode,elapsed_s=round(time.monotonic()-start,2),
                        stdout=result.stdout,stderr=result.stderr))
        print(json.dumps(dict(step=label,returncode=result.returncode)),flush=True)
        if result.returncode:raise RuntimeError(label+' failed')
    source=out/'synthetic-source.txt';source.write_text('Synthetic A-to-B geometry fixture. No research finding or measured data.',encoding='utf-8')
    scene={'schema_version':'1.0','font':'Arial',
      'canvas':dict(width_px=400,height_px=200,pixels_per_inch=96),
      'provenance':dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),scientific_source='Synthetic geometry only',corrections=[],limitations=['Small fixture, no scientific content']),
      'pages':[dict(name='Synthetic geometry',slug='fixture',mode='faithful',
        nodes=[dict(id='A',type='rect',bbox=[20,60,100,50],text='A',style=dict(fill='#e0effd',stroke='#27303b',font_px=18,bold=False)),
               dict(id='B',type='ellipse',bbox=[280,60,100,50],text='B',style=dict(fill='#e0effd',stroke='#27303b',font_px=18,bold=False))],
        paths=[],edges=[dict(id='edge',points=[[120,85],[280,85]],arrow=13,
            source=dict(node='A',anchor=[1,.5]),target=dict(node='B',anchor=[0,.5]),
            style=dict(stroke='#27303b',stroke_px=2))],draw_order=['A','B','edge'])]}
    results={}
    for backend in ('illustrator','powerpoint','visio'):
        folder=out/backend;folder.mkdir()
        s=copy.deepcopy(scene);sp=folder/'scene.json'
        try:
            if backend=='illustrator':
                s.update(schema_version='1.1',font='ArialMT',font_bold='Arial-BoldMT',points_per_pixel=.75,
                         layers=[dict(id='main',name='Main')],groups=[dict(id='group',layer='main',test_move=True)])
                for key in ('nodes','paths','edges'):
                    for item in s['pages'][0][key]:item['group']='group'
                sp.write_text(json.dumps(s,indent=2),encoding='utf-8')
                script=ROOT/'light-illustrator-diagram/scripts/illustrator.py'
                run('illustrator render',sys.executable,'-X','utf8','-B',script,'render',sp,folder/'fixture.ai','--stem',folder/'render','--delay-ms','0')
                run('illustrator verify',sys.executable,'-X','utf8','-B',script,'verify',sp,folder/'fixture.ai','--stem',folder/'verified')
                audit=folder/'verified.audit.json'
            elif backend=='powerpoint':
                sp.write_text(json.dumps(s,indent=2),encoding='utf-8')
                scripts=ROOT/'light-powerpoint-diagram/scripts'
                run('powerpoint render','node',scripts/'render_scene.mjs',sp,folder/'draft.pptx')
                run('powerpoint connectors',sys.executable,'-X','utf8','-B',scripts/'attach_connectors.py',sp,folder/'draft.pptx',folder/'connected.pptx')
                # Exercise protection against unsaved changes in an actual
                # temporary fixture, never a user's presentation.
                import win32com.client
                app=win32com.client.Dispatch('PowerPoint.Application')
                owned=app.Presentations.Open(str(folder/'connected.pptx'),False,False,False)
                owned.Saved=False
                try:
                    result=subprocess.run([sys.executable,'-X','utf8','-B',str(scripts/'verify_powerpoint.py'),str(sp),
                        str(folder/'connected.pptx'),str(folder/'connected.pptx.connections.json'),
                        str(folder/'guard-roundtrip.pptx'),str(folder/'guard'),'--hidden'],capture_output=True,text=True,encoding='utf-8',timeout=90)
                    guard=result.returncode!=0 and not bool(owned.Saved) and not (folder/'guard-roundtrip.pptx').exists()
                    if not guard:raise RuntimeError('Unsaved fixture guard failed')
                    log.append(dict(step='powerpoint unsaved fixture guard',passed=guard,stderr=result.stderr))
                finally:
                    owned.Saved=True;owned.Close()
                run('powerpoint verify',sys.executable,'-X','utf8','-B',scripts/'verify_powerpoint.py',sp,
                    folder/'connected.pptx',folder/'connected.pptx.connections.json',folder/'roundtrip.pptx',folder/'verified','--hidden')
                audit=folder/'verified.audit.json'
            else:
                sp.write_text(json.dumps(s,indent=2),encoding='utf-8')
                run('visio render/verify',sys.executable,'-X','utf8','-B',ROOT/'light-visio-diagram/scripts/render_scene.py',sp,folder/'fixture.vsdx')
                audit=folder/'fixture.audit.json'
            report=json.loads(audit.read_text('utf-8-sig'))
            results[backend]=dict(passed=report['passed'],audit=str(audit),scope='Small native geometry/save/reopen fixture only')
        except Exception as exc:
            results[backend]=dict(passed=False,error=str(exc))
        (out/'smoke-result.json').write_text(json.dumps(dict(results=results,steps=log),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False,indent=2))
    if not all(r['passed'] for r in results.values()):raise SystemExit(1)

if __name__=='__main__':main()
