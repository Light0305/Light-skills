"""Initialize a selected light-write LaTeX layout or compile a LaTeX project.

Python 3.10+ standard library. Compilation requires latexmk and a TeX engine;
the bundled bibliography uses biber. This is not a scientific or visual audit.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'templates' / 'latex'
LAYOUTS = {'double': 'double-column.tex', 'single': 'single-column.tex'}
ENGINES = {'xelatex': '-xelatex', 'lualatex': '-lualatex', 'pdflatex': '-pdf'}


class LatexError(ValueError):
    pass


def initialize(destination, layout, language='en'):
    """Copy only a user-selected layout; never replace an existing project."""
    if layout not in LAYOUTS:
        raise LatexError('Select a layout explicitly: double or single')
    if language not in {'en', 'zh'}:
        raise LatexError('Language must be en or zh')
    destination = Path(destination).resolve()
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise LatexError('Destination must be new or empty; continue existing templates in place')
    source = TEMPLATES / LAYOUTS[layout]
    common = TEMPLATES / 'common'
    if not source.is_file() or not common.is_dir():
        raise LatexError('The installed skill is missing its bundled LaTeX templates')
    shutil.copytree(common, destination, dirs_exist_ok=True)
    shutil.copyfile(source, destination / 'main.tex')
    language_text = ('% Selected manuscript language; keep with the source project.\n'
                     '\\newif\\ifLWChinese\n' +
                     ('\\LWChinesetrue\n' if language == 'zh' else '\\LWChinesefalse\n'))
    (destination / 'language.tex').write_text(language_text, encoding='utf-8')
    return {'status': 'initialized', 'layout': layout, 'language': language,
            'source': str(destination / 'main.tex'), 'compiled': False,
            'note': 'Template instructions and author placeholders are not a completed manuscript.'}


def log_issues(log):
    """Inspect the FINAL engine log, not first-pass latexmk console warnings."""
    failures, warnings = [], []
    for line in log.splitlines():
        line = line.strip()
        if (re.search(r'(?:Citation|Reference) .+ undefined', line)
                or re.search(r'There were undefined (?:references|citations)', line)
                or line.startswith('Missing character:')
                or 'Please (re)run Biber' in line
                or 'Rerun to get cross-references right' in line
                or 'multiply defined' in line):
            failures.append(line)
        elif (re.search(r'(?:Over|Under)full \\[hv]box', line)
              or 'Warning:' in line or 'Empty bibliography' in line):
            warnings.append(line)
    return list(dict.fromkeys(failures)), list(dict.fromkeys(warnings))


def build(project, engine='xelatex', output=None, main='main.tex', timeout=180):
    """Compile with latexmk and reject broken references or missing glyphs."""
    if engine not in ENGINES:
        raise LatexError('Unsupported TeX engine')
    if timeout <= 0:
        raise LatexError('Timeout must be positive')
    project = Path(project).resolve()
    source = (project / main).resolve()
    if not source.is_relative_to(project) or source.suffix != '.tex' or not source.is_file():
        raise LatexError('Main source must be an existing .tex file within the LaTeX project')
    # Keep build products separate from editable source, respecting a chosen path.
    output = Path(output).resolve() if output else project.parent / 'build'
    if output == project or output == source.parent:
        raise LatexError('Use a separate build directory to preserve editable source')
    compiler = shutil.which('latexmk')
    if not compiler or not shutil.which(engine):
        raise LatexError('Compilation needs latexmk and ' + engine + ' on PATH; source is not a compiled PDF')
    output.mkdir(parents=True, exist_ok=True)
    pdf = output / (source.stem + '.pdf')
    log = output / (source.stem + '.log')
    previous = {path: (path.stat().st_mtime_ns, path.stat().st_size)
                for path in (pdf, log) if path.is_file()}
    # Relative arguments avoid Windows/Perl code-page loss for Chinese project
    # names. The normal source/build siblings only need the ASCII ../build.
    try:
        output_argument = Path(os.path.relpath(output, project)).as_posix()
    except ValueError:  # Explicit output on a different Windows drive.
        output_argument = output.as_posix()
    command = [compiler, '-norc', ENGINES[engine], '-g', '-interaction=nonstopmode',
               '-halt-on-error', '-file-line-error', '-no-shell-escape',
               '-outdir=' + output_argument, source.relative_to(project).as_posix()]
    transcript = output / 'latexmk-output.log'
    try:
        process = subprocess.run(command, cwd=project, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, timeout=timeout,
                                 encoding='utf-8', errors='replace', check=False)
    except subprocess.TimeoutExpired as error:
        captured = error.stdout or b''
        if isinstance(captured, bytes):
            captured = captured.decode('utf-8', errors='replace')
        transcript.write_text(captured, encoding='utf-8')
        raise LatexError(f'Compilation timed out after {timeout}s; see {transcript}') from error
    transcript.write_text(process.stdout, encoding='utf-8')
    if process.returncode:
        tail = '\n'.join(process.stdout.splitlines()[-18:])
        raise LatexError(f'Compilation failed ({process.returncode}); see {transcript}\n{tail}')
    if not pdf.is_file() or not log.is_file():
        raise LatexError('Compiler returned success but did not produce the expected PDF and log')
    if any((path.stat().st_mtime_ns, path.stat().st_size) == stamp
           for path, stamp in previous.items()):
        raise LatexError('The forced build left a prior PDF/log unchanged; current output is not verified')
    with pdf.open('rb') as stream:
        if stream.read(5) != b'%PDF-':
            raise LatexError('Compiler output is not a PDF')
    failures, warnings = log_issues(log.read_text(encoding='utf-8', errors='replace'))
    if failures:
        raise LatexError('Compilation has unresolved references, glyphs, or labels: ' +
                         '; '.join(failures) + f'; see {log}')
    return {'status': 'compiled', 'source': str(source), 'pdf': str(pdf),
            'engine': engine, 'log': str(log), 'transcript': str(transcript),
            'warnings': warnings, 'visual_review': 'pending',
            'note': 'Compilation does not establish visual quality, evidence validity, or submission readiness.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init', help='Copy a built-in layout after the user selects it')
    init.add_argument('destination', type=Path, help='New or empty LaTeX source directory')
    init.add_argument('--layout', choices=LAYOUTS, required=True,
                      help='User-selected layout; no implicit column default')
    init.add_argument('--language', choices=['en', 'zh'], default='en',
                      help='zh supports Chinese or mixed Chinese/English manuscripts')
    compile_parser = commands.add_parser('build', help='Compile and check the final engine log')
    compile_parser.add_argument('project', type=Path)
    compile_parser.add_argument('--engine', choices=ENGINES, default='xelatex')
    compile_parser.add_argument('--output', type=Path, help='Default: build/ beside the source directory')
    compile_parser.add_argument('--main', default='main.tex')
    compile_parser.add_argument('--timeout', type=int, default=180, help='Compilation limit in seconds')
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            result = initialize(args.destination, args.layout, args.language)
        else:
            result = build(args.project, args.engine, args.output, args.main, args.timeout)
    except (LatexError, OSError) as error:
        print(json.dumps({'status': 'failed', 'error': str(error)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
