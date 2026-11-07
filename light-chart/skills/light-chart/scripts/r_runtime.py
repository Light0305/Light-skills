"""Run native R with a complete child environment and truthful exit reporting.

Some desktop launchers omit PROCESSOR_ARCHITECTURE. cli's Windows unload path
calls strcmp(getenv(...), "ARM64") without a NULL check, causing a shutdown
access violation. Restore the real native architecture in the child only.
"""
from __future__ import annotations
import argparse
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


def native_windows_architecture():
    from ctypes import wintypes as w
    class SystemInfo(ctypes.Structure):
        _fields_ = [('arch',w.WORD),('reserved',w.WORD),('page_size',w.DWORD),
                    ('minimum',ctypes.c_void_p),('maximum',ctypes.c_void_p),
                    ('mask',ctypes.c_size_t),('processors',w.DWORD),('type',w.DWORD),
                    ('granularity',w.DWORD),('level',w.WORD),('revision',w.WORD)]
    info=SystemInfo()
    ctypes.windll.kernel32.GetNativeSystemInfo(ctypes.byref(info))
    name={0:'x86',9:'AMD64',12:'ARM64'}.get(info.arch)
    if name is None:
        raise RuntimeError(f'Unrecognized Windows architecture: {info.arch}')
    return name


def child_environment(inherited=None):
    env=dict(os.environ if inherited is None else inherited)
    changes={}
    if os.name=='nt':
        if not env.get('PROCESSOR_ARCHITECTURE'):
            env['PROCESSOR_ARCHITECTURE']=native_windows_architecture()
            changes['PROCESSOR_ARCHITECTURE']=env['PROCESSOR_ARCHITECTURE']
        # These POSIX locale spellings are not recognized by Windows R.
        for key in list(env):
            if (key.startswith('LC_') or key in {'LANG','LANGUAGE'}) and env[key].casefold() in {'c.utf-8','c.utf8'}:
                env.pop(key); changes[key]='removed unsupported POSIX locale spelling'
    return env,changes


def find_rscript(path=None):
    found=path or shutil.which('Rscript')
    if not found and os.name=='nt':
        roots=sorted(Path(os.environ.get('ProgramFiles','C:/Program Files')).glob('R/R-*/bin/x64/Rscript.exe'))
        found=str(roots[-1]) if roots else None
    if not found or not Path(found).is_file():
        raise FileNotFoundError('Rscript not found; provide --rscript')
    return str(Path(found).resolve())


def run_r(script, args=(), *, rscript=None, cwd=None, timeout=180, log=None):
    script=Path(script).resolve()
    if not script.is_file():raise FileNotFoundError(script)
    env,changes=child_environment()
    command=[find_rscript(rscript),'--vanilla',str(script),*map(str,args)]
    before=time.monotonic()
    try:
        completed=subprocess.run(command,cwd=cwd,env=env,stdin=subprocess.DEVNULL,
          capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,
          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0) if os.name=='nt' else 0)
        result={'returncode':completed.returncode,'stdout':completed.stdout,'stderr':completed.stderr,
                'status':'PASS' if completed.returncode==0 else 'FAIL'}
    except subprocess.TimeoutExpired as exc:
        def decode(x):return x.decode('utf-8',errors='replace') if isinstance(x,bytes) else x or ''
        result={'returncode':None,'stdout':decode(exc.stdout),'stderr':decode(exc.stderr),'status':'TIMEOUT'}
    result.update({'script':str(script),'rscript':command[0],'seconds':round(time.monotonic()-before,3),
                   'child_environment_adjustments':changes,'forced_exit':False})
    if log:
        log=Path(log);log.parent.mkdir(parents=True,exist_ok=True)
        log.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


def doctor(rscript=None, log=None):
    with tempfile.TemporaryDirectory(prefix='light-chart-r-') as tmp:
        script=Path(tmp)/'doctor.R'
        script.write_text('library(ggplot2)\nlibrary(survival)\nlibrary(ComplexHeatmap)\n'
          'cat("R_RUNTIME_OK\\n")\n'
          'for(p in c("rlang","cli","ggplot2","survival","ComplexHeatmap")) '
          'cat(p,as.character(packageVersion(p)),"\\n")\n',encoding='utf-8')
        return run_r(script,rscript=rscript,log=log,timeout=45)


def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['doctor','run'])
    parser.add_argument('script',nargs='?')
    parser.add_argument('--rscript');parser.add_argument('--log')
    parser.add_argument('--timeout',type=float,default=180)
    parser.add_argument('--script-args',nargs=argparse.REMAINDER,default=[])
    args=parser.parse_args()
    if args.command=='run' and not args.script:parser.error('run requires a saved .R file')
    result=doctor(args.rscript,args.log) if args.command=='doctor' else run_r(
        args.script,args.script_args,rscript=args.rscript,timeout=args.timeout,log=args.log)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
