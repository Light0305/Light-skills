"""Stage immutable visual reviews with the Light-Science review engine.

The adapter never launches a model, fabricates a review, or certifies independence.
The host supplies a genuinely fresh review session and its returned JSON. Host isolation remains separate from deterministic byte and state checks.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
import math
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

from PIL import Image, ImageDraw

import review_engine

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / 'references/visual-review'
TRANSPORT = 'host-role + explicit view_image compatibility adapter'
THREE_D_MODES = {'strict-reproduction', 'candidate-comparison', 'control-replacement'}
THREE_D_SUBTYPES = {'surfaces', 'fractured-surfaces', 'material-lighting',
    'volumetric-surfaces', 'extrema-fold-network', 'patch-composition', 'marks-and-panels'}
THREE_D_BASE_MODULES = ['three-d/route.md', 'three-d/evidence.md', 'three-d/camera.md',
    'three-d/selection.md', 'three-d/assessment.md', 'three-d/iteration.md', 'reviewer-contract.md']
THREE_D_MODULES = {'surfaces': 'surfaces', 'fractured-surfaces': 'discontinuities',
    'material-lighting': 'light-and-material', 'volumetric-surfaces': 'volumes',
    'extrema-fold-network': 'extrema-and-connections', 'patch-composition': 'layered-geometry',
    'marks-and-panels': 'marks-and-panels'}
THREE_D_DELTA_FIELDS = ['target_dimension', 'movement_delta', 'must_preserve',
    'candidate_regressions', 'remaining_gaps', 'next_single_change', 'accept_over_control']
THREE_D_MOVEMENTS = ['accepted', 'too_small', 'wrong_direction', 'overshoot',
    'right_direction_with_regression', 'no_visible_delta']


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _immutable(path, value):
    """Idempotent same bytes; never replace an earlier staged input."""
    path = Path(path)
    data = value.encode('utf-8') if isinstance(value, str) else value
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('xb') as handle:
            handle.write(data)
    except FileExistsError:
        if path.read_bytes() != data:
            raise ValueError('Cannot overwrite immutable review artifact: ' + str(path))


def _json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def _attempts(workdir):
    # Verify the owned ledger before using any recorded decision.
    return review_engine.review_history(Path(workdir))


def _capture(call, **kwargs):
    output = io.StringIO()
    with redirect_stdout(output):
        call(SimpleNamespace(**kwargs))
    return output.getvalue().strip()


def verify_stage(workdir, iteration):
    """Verify all images, prompt, QA and source diagnostics before using a review."""
    workdir = Path(workdir).resolve()
    view = workdir / f'audit_view_{iteration}'
    manifest_path = view/'stage_manifest.json'
    manifest = _json(manifest_path)
    config = _json(workdir/'review_cycle.json')
    anchor = view/'stage_manifest.sha256'
    # An existing binding belongs to the staged packet, not to a switch in
    # mutable metadata. Legacy unanchored packets remain readable, but editing
    # both JSON version flags cannot disable a binding already on disk.
    if anchor.exists() or config.get('stage_binding_version', 1) >= 2:
        if not anchor.is_file() or anchor.read_text(encoding='utf-8').strip() != _sha(manifest_path):
            raise ValueError('Stale or missing review stage manifest binding')
    if any(manifest.get(key) != value for key, value in config.items()):
        raise ValueError('Review stage manifest disagrees with its immutable cycle configuration')
    if manifest['iteration'] != iteration:
        raise ValueError('Review manifest iteration mismatch')
    errors = []
    for relative, digest in manifest['sha256'].items():
        path = (workdir / relative).resolve()
        if not path.is_relative_to(workdir):
            raise ValueError('Review artifact escapes its workdir')
        if not path.is_file() or _sha(path) != digest:
            errors.append(relative)
    if errors:
        raise ValueError('Stale or missing review artifacts: ' + ', '.join(errors))
    return manifest


def _brief_image(brief):
    """Explicitly labelled briefing card; it is never a purported paper figure."""
    image = Image.new('RGB', (760, 920), 'white')
    draw = ImageDraw.Draw(image)
    font = review_engine.font_for(26)
    lines = ['DATA-FIRST VISUAL REVIEW', '', 'No external style reference.',
             'This is a briefing card,', 'not scientific evidence.', '',
             'Review the DRAFT on the right.', '',
             'Read review_prompt.txt for', 'the scientific question and',
             'declared display semantics.']
    draw.multiline_text((36, 45), '\n'.join(lines), fill='#222222', font=font, spacing=14)
    stream = io.BytesIO()
    image.save(stream, format='PNG')
    return stream.getvalue()


def _schema(iteration, *, strict_3d=False, comparisons=()):
    string = {'type': 'string', 'minLength': 1}
    strings = {'type': 'array', 'items': string}
    schema = {'type': 'object', 'required': ['iter', 'reference_inventory', 'anchor',
              'quality_floor', 'fidelity', 'focus_themes', 'boxes'], 'properties': {
        'iter': {'const': iteration},
        'reference_inventory': {'type': 'object', 'required': ['chart_type', 'signature_element', 'motifs'],
            'properties': {'chart_type': string, 'signature_element': string,
                           'motifs': {**strings, 'minItems': 1}}},
        'anchor': {'type': 'object', 'required': ['what_is_right', 'measurements'],
            'properties': {'what_is_right': {**strings, 'minItems': 1},
                           'measurements': {'type': 'object'}}},
        'quality_floor': {'type': 'object', 'required': ['passed', 'violation_kinds', 'summary'],
            'properties': {'passed': {'type': 'boolean'},
              'violation_kinds': {'type': 'array', 'items': {'enum': sorted(review_engine.VIOLATION_KINDS)}},
              'summary': {'type': ['string', 'null']}}},
        'fidelity': {'type': 'object', 'required': ['verdict', 'paragraph'],
            'properties': {'verdict': {'enum': ['ship', 'close', 'off']}, 'paragraph': string}},
        'focus_themes': strings,
        'boxes': {'type': 'array', 'items': {'type': 'object',
            'required': ['x0', 'y0', 'x1', 'y1', 'note'],
            'properties': {**{k: {'type': 'integer'} for k in ['x0', 'y0', 'x1', 'y1']}, 'note': string}}}}}
    if strict_3d:
        scorecard = {'type': 'object', 'required': [*review_engine.SCORE_FIELDS, 'summary'],
            'properties': {**{k: {'type': 'integer', 'minimum': 0, 'maximum': 100}
                for k in review_engine.SCORE_FIELDS}, 'summary': string}}
        schema['required'] += ['three_d_scorecard', *THREE_D_DELTA_FIELDS]
        schema['properties'].update({'three_d_scorecard': scorecard,
            'target_dimension': string, 'movement_delta': {'enum': THREE_D_MOVEMENTS},
            **{k: strings for k in ['must_preserve', 'candidate_regressions', 'remaining_gaps']},
            'next_single_change': {'type': ['string', 'null']},
            'accept_over_control': {'type': 'boolean'}})
        if comparisons:
            schema['required'].append('comparison_scorecards')
            schema['properties']['comparison_scorecards'] = {'type': 'object',
                'required': list(comparisons), 'properties': {k: scorecard for k in comparisons}}
    return schema


def _three_d_inputs(mode, reference_role, three_d_mode, subtypes, geometry_evidence,
                    control, baseline, views, pdf):
    """Resolve an explicit strict route and bind real resources, never raster proxies."""
    if three_d_mode not in THREE_D_MODES:
        raise ValueError('Strict 3D needs an explicit three_d_mode: ' + ', '.join(sorted(THREE_D_MODES)))
    if three_d_mode == 'strict-reproduction' and (mode != 'reference-fit' or reference_role != 'design_reference'):
        raise ValueError('Strict reproduction needs reference-fit with a genuine design reference')
    if three_d_mode != 'strict-reproduction' and control is None:
        raise ValueError('Strict candidate comparison/control replacement needs an actual rendered control')
    if reference_role == 'brief_only':
        raise ValueError('Strict 3D needs an actual reference/control image, not a briefing card')
    if not pdf:
        raise ValueError('Strict 3D needs the actual final PDF')
    if not isinstance(subtypes, (list, tuple)) or not subtypes or any(s not in THREE_D_SUBTYPES for s in subtypes):
        raise ValueError('Declare the visible three_d_subtypes')
    modules = THREE_D_BASE_MODULES + ['three-d/' + THREE_D_MODULES[s] + '.md' for s in sorted(set(subtypes))]
    for relative in modules:
        if not (LIBRARY/relative).is_file():
            raise ValueError('Missing routed Light-Science 3D module: ' + relative)
    if not geometry_evidence:
        raise ValueError('Strict 3D needs geometry_evidence with actual resource hashes')
    evidence_path = Path(geometry_evidence).resolve()
    evidence = _json(evidence_path)
    if not isinstance(evidence, dict) or not str(evidence.get('representation', '')).strip():
        raise ValueError('Geometry evidence needs a declared representation')
    if not evidence.get('coordinate_units') or not isinstance(evidence.get('checks'), dict) or not evidence['checks']:
        raise ValueError('Geometry evidence needs coordinate_units and nonempty scientific checks')
    limitations = evidence.get('limitations')
    if not isinstance(limitations, list) or any(not isinstance(s, str) or not s.strip() for s in limitations):
        raise ValueError('Geometry evidence needs an explicit limitations list')
    assets = evidence.get('assets')
    if not isinstance(assets, list) or not assets:
        raise ValueError('Geometry evidence needs at least one actual geometry/source asset')
    bound = []
    for entry in assets:
        if not isinstance(entry, dict) or not str(entry.get('role', '')).strip() or not entry.get('path'):
            raise ValueError('Each geometry asset needs role, path and sha256')
        path = (evidence_path.parent/entry['path']).resolve()
        if not path.is_file() or _sha(path) != entry.get('sha256'):
            raise ValueError('Geometry asset missing or hash mismatch: ' + str(path))
        bound.append({'role': entry['role'], 'path': path, 'sha256': _sha(path)})
    if not isinstance(views or {}, dict) or any(name in {'control', 'baseline'} for name in (views or {})):
        raise ValueError('3D view names cannot replace the declared control or baseline')
    images = {}
    for role, path in [('control', control), ('baseline', baseline), *sorted((views or {}).items())]:
        if path is None:
            continue
        if role in images or role not in {'control', 'baseline'} and (not role or not role.replace('_', '').replace('-', '').isalnum()):
            raise ValueError('3D view names must be unique simple identifiers')
        path = Path(path).resolve()
        with Image.open(path) as image:
            image.verify()
        images[role] = path
    return {'mode': three_d_mode, 'subtypes': sorted(set(subtypes)), 'modules': modules,
        'evidence': evidence, 'evidence_sha256': _sha(evidence_path), 'assets': bound, 'images': images}


def _strict_prompt(route):
    return '\n' + f"""MODE OVERRIDE: strict 3D {route['mode']}.
This review uses the Light-Science strict schema and explicit host image delivery. Read reviewer.md and
EVERY file listed below, as well as geometry_evidence.json. All images listed
in stage_manifest.json required_images must actually be inspected. Compare
baseline, accepted control and current candidate separately when supplied.
The candidate's observation card is top-level three_d_scorecard; supplied
control/baseline each need their own comparison_scorecards entry. No raster
raster diagnostic is run or substituted for these observed judgments.

The staged scientific report is a supplied separate audit, not verified by this
script or by your image reading. Do not open geometry_sources_* or raw assets.
Its resource hashes bind this exact stage; visible slices, camera views and real
geometry checks complement one another. A visual topology score describes the
representation and visible skeleton; it cannot certify hidden mesh topology,
biological segmentation, object count, physical calibration or raw values.
Examine occlusion, visible extrema, volume/heightfield class, axes, units,
material versus scalar color, mixed-panel roles and final-size text/export.

Use the declared heuristic review thresholds; they are not calibrated quality measurements. A clean ship needs
overall >=85, every dimension >=75, topology/geometry_footprint/camera_box_aspect/
composition_occupancy >=82 and no active floor. Do not inflate scores to pass.
Provide actual target_dimension, movement_delta, must_preserve,
candidate_regressions, remaining_gaps, next_single_change and accept_over_control.
Reject primary regressions; beating baseline is not accepting over control.
For clean acceptance use movement_delta=accepted, accept_over_control=true,
empty regressions/gaps and next_single_change=null. Otherwise give close/off
and actual actionable repair. A numeric rubric alone cannot override these
control-preservation records. An initial reference-fit baseline with no control
must be described as such, not as independent improvement over a prior control.

Routed Light-Science guides (read all):
""" + '\n'.join('visual-review-3d/' + p for p in route['modules']) + '\n'


def _review_prompt(mode, reference_role, briefing, has_pdf):
    common = f"""You are an independent visual reviewer for exactly one immutable draft.
Transport: {TRANSPORT}. The host delivers the explicit images and a fresh review context. Open only this audit view's staged images
with view_image and read its review_prompt.txt, aesthetic-library.md, diagnostics.json
and review_schema.json. Do not run code, edit files, spawn agents, use network, read
draft source/raw data, author self-reviews, or prior review/iteration history.
Restrictions are prompt-level; the tool cannot prove host isolation or independence.

Actually inspect composite.png, reference_clean.png and draft_fullres.png. Also inspect
print_preview.png for final-size readability{', and pdf_preview.png for the final PDF' if has_pdf else ''}.
The print preview is a consistent 96-dpi screen proxy, not monitor calibration.
Read the convention library, but scientific meaning and the user's brief take priority.
Affirm concrete correct features and give at most five consequential repair themes.
Separate global canvas, per-panel aspect and gutter/label space. Examine small marks,
text, units, missingness keys, uncertainty, shared color semantics, grayscale direction,
legend lookup and complementary evidence. A dark-pixel diagnostic is only a cue;
never turn a library default or absent measurement into an observed fact.
Scientific calculations are checked separately; do not claim raw-data verification.

Return one strict JSON object following review_schema.json, no fences or side files.
Use actual observations, not schema/example prose. Inventory and positive anchors
must be nonempty. For a clean review use passed=true, no violations, summary=null,
verdict=ship, no themes and no boxes. A repair uses close/off plus specific themes
or boxes; failed floor also needs a listed supported violation and summary. Boxes
use COMPOSITE pixels, on its DRAFT half. The Light-Science review engine validates
consistency and controls retry, revision, minimum review count and iteration cap.

Scientific/display briefing supplied by the orchestrator (not independently verified):
{briefing}
"""
    if mode == 'reference-fit':
        return (common + '\nMODE: reference-fit. The left image is a design reference.\n'
                'Use the staged reviewer.md for reference inventory, construction/motif\n'
                'preservation and data-driven exceptions. Do not compare numerical values\n'
                'across different datasets. User/data constraints still take precedence.\n')
    return (common + f'\nMODE: data-first. Left image role: {reference_role}.\n'
        'No requirement to copy its graph type, motif, palette or numerical values.\n'
        'If the left image is a briefing card, it contains NO visual gold standard.\n'
        'If it is a previous draft, it is a visual comparison only, not scientific truth.\n'
        'Inventory the CURRENT DRAFT in reference_inventory (legacy schema field name).\n'
        'Here fidelity.verdict means draft readiness, not reference similarity. Judge\n'
        'whether its encoding, hierarchy and readability serve the stated question.\n'
        'Ground observations in [DRAFT], [BRIEF] or a named applicable [CONVENTION].\n'
        'Do not declare chart_type_abandoned solely because a design changed, and do\n'
        'not label self-comparison as fidelity evidence.\n')


def stage_review(workdir, draft, *, iteration=0, mode='data-first', reference=None,
                 reference_role=None, briefing='', size_mm=None, pdf=None, qa=None,
                 diagnostics=None, min_reviews=2, max_iters=3, strict_3d=False,
                 three_d_mode=None, three_d_subtypes=(), geometry_evidence=None,
                 control=None, baseline=None, three_d_views=None):
    """Copy actual exports into a bounded, immutable audit view; never run reviewers."""
    workdir, draft = Path(workdir).resolve(), Path(draft).resolve()
    if isinstance(iteration, bool) or not isinstance(iteration, int) or iteration < 0:
        raise ValueError('iteration must be a nonnegative integer')
    if mode not in {'data-first', 'reference-fit'}:
        raise ValueError('mode must be data-first or reference-fit')
    if not isinstance(briefing, str) or not briefing.strip():
        raise ValueError('A scientific question and declared display semantics are required')
    if not size_mm or len(size_mm) != 2 or any(not math.isfinite(float(v)) or float(v) <= 0 for v in size_mm):
        raise ValueError('Positive final width and height in mm are required')
    if any(isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in [min_reviews, max_iters]):
        raise ValueError('min_reviews and max_iters must be positive integers')
    if iteration >= max_iters:
        raise ValueError('Iteration cap reached')
    if mode == 'reference-fit' and reference is None:
        raise ValueError('reference-fit needs an actual external reference image')
    if reference_role is None:
        reference_role = 'design_reference' if reference else 'brief_only'
    allowed_roles = {'brief_only', 'design_reference', 'previous_draft'}
    if reference_role not in allowed_roles or (reference is None) != (reference_role == 'brief_only'):
        raise ValueError('Declare the actual reference role: design_reference, previous_draft or brief_only')
    if mode == 'reference-fit' and reference_role != 'design_reference':
        raise ValueError('reference-fit cannot promote a previous draft or briefing card to a reference')
    route = None
    if strict_3d:
        route = _three_d_inputs(mode, reference_role, three_d_mode, three_d_subtypes,
            geometry_evidence, control, baseline, three_d_views, pdf)
        if route['mode'] != 'strict-reproduction' and _sha(control) == _sha(draft):
            raise ValueError('Strict candidate comparison requires a changed candidate, not the same control')
    elif any([three_d_mode, three_d_subtypes, geometry_evidence, control, baseline, three_d_views]):
        raise ValueError('3D route arguments need explicit strict_3d=True')
    with Image.open(draft) as source:
        source.verify()
    if reference and _sha(reference) == _sha(draft):
        raise ValueError('Self-comparison is not reference or revision evidence')
    if qa:
        from source_binding import verify_report
        report = _json(qa)
        errors = verify_report(report)['errors']
        # A supplied QA must concern the actual draft/PDF being staged.
        for label, path in [('draft', draft), ('pdf', pdf)]:
            if path is None:
                continue
            hashes = {item.get('sha256') for item in report.get('review_artifacts', {}).values()
                      if isinstance(item, dict) and Path(item.get('path', '')).suffix.lower() == Path(path).suffix.lower()}
            if _sha(path) not in hashes:
                errors.append('QA is not bound to the staged '+label)
        if errors:
            raise ValueError('Stale or mismatched figure QA: '+'; '.join(errors))
    workdir.mkdir(parents=True, exist_ok=True)
    config = {'schema_version': 1, 'stage_binding_version': 2, 'mode': mode,
              'transport': TRANSPORT, 'min_reviews': min_reviews, 'max_iters': max_iters,
              'strict_3d': bool(strict_3d), 'size_mm': list(map(float, size_mm)),
              'briefing': briefing, 'independence': 'Host responsibility; not authenticated by this script'}
    if route:
        config['three_d_mode'] = route['mode']
        config['three_d_subtypes'] = route['subtypes']
    _immutable(workdir / 'review_cycle.json', _json_text(config))
    attempts = _attempts(workdir)
    manifest_path = workdir / f'audit_view_{iteration}' / 'stage_manifest.json'
    request = {'config':config, 'reference_role':reference_role, 'draft_sha256':_sha(draft),
        'reference_sha256':_sha(reference) if reference else None,
        'pdf_sha256':_sha(pdf) if pdf else None, 'qa_sha256':_sha(qa) if qa else None,
        'diagnostics':diagnostics or {}}
    if route:
        request['three_d'] = {'geometry_evidence_sha256': route['evidence_sha256'],
            'assets': [{k: a[k] for k in ['role', 'sha256']} for a in route['assets']],
            'images': {name: _sha(path) for name, path in route['images'].items()},
            'inserts': {name: _sha(LIBRARY/name) for name in route['modules']}}
    request_sha = hashlib.sha256(_json_text(request).encode('utf-8')).hexdigest()
    if manifest_path.exists():
        manifest = verify_stage(workdir, iteration)
        if request_sha != manifest['request_sha256']:
            raise ValueError('Cannot change an already staged draft or its review inputs')
        return manifest
    if attempts and attempts[-1]['action'] in {'ship', 'stop_at_cap'}:
        raise ValueError('Review cycle is already terminal')
    if iteration == 0 and attempts:
        raise ValueError('Cannot restage a different initial draft after review')
    if iteration:
        if not attempts or attempts[-1]['action'] != 'draw' or attempts[-1]['iter'] != iteration-1:
            raise ValueError('A valid draw decision must authorize this next iteration')
        verify_stage(workdir, iteration-1)
        if _sha(draft) == attempts[-1]['draft_sha256']:
            raise ValueError('Actionable feedback requires an actually changed draft')
    canonical = workdir / f'img_iter{iteration}.png'
    _immutable(canonical, draft.read_bytes())
    if reference is not None:
        ref_bytes = Path(reference).read_bytes()
        with Image.open(reference) as source:
            source.verify()
    else:
        ref_bytes = _brief_image(briefing)
    # Reference is per view so a data-first comparison may use the preceding draft.
    view = workdir / f'audit_view_{iteration}'
    if view.exists():
        raise ValueError('Unfinished audit view exists; preserve it and use a new cycle directory')
    view.mkdir()
    _immutable(view / 'reference_clean.png', ref_bytes)
    _immutable(view / 'draft_fullres.png', canonical.read_bytes())
    _immutable(view / 'aesthetic-library.md', (LIBRARY/'layout-and-type.md').read_bytes())
    if mode == 'reference-fit' or route:
        _immutable(view / 'reviewer.md', (LIBRARY/'reviewer-contract.md').read_bytes())
    geometry_files = []
    extra_images = []
    comparisons = []
    if route:
        for relative in route['modules']:
            _immutable(view/'visual-review-3d'/relative, (LIBRARY/relative).read_bytes())
        source_dir = workdir/f'geometry_sources_{iteration}'
        summary = {k: v for k, v in route['evidence'].items() if k != 'assets'}
        summary['assets'] = []
        for index, entry in enumerate(route['assets']):
            target = source_dir/f"asset_{index:03d}{entry['path'].suffix}"
            _immutable(target, entry['path'].read_bytes())
            geometry_files.append(target)
            summary['assets'].append({'role': entry['role'], 'sha256': entry['sha256'],
                'staged_path': str(target.relative_to(workdir)).replace('\\', '/')})
        _immutable(source_dir/'source_report.json', _json_text(route['evidence']))
        geometry_files.append(source_dir/'source_report.json')
        summary['verification_boundary'] = 'Supplied scientific audit; the adapter binds bytes but does not certify calculations or independence.'
        _immutable(view/'geometry_evidence.json', _json_text(summary))
        for name, path in route['images'].items():
            target = view/f'three_d_{name}.png'
            # Decode and re-encode: the canonical staged file really is PNG.
            with Image.open(path) as image:
                stream = io.BytesIO(); image.convert('RGB').save(stream, format='PNG')
            _immutable(target, stream.getvalue())
            extra_images.append(target.name)
            if name in {'control', 'baseline'}:
                comparisons.append(name)
    preview_size = tuple(max(1, round(float(v)/25.4*96)) for v in size_mm)
    with Image.open(canonical) as image:
        image.convert('RGB').resize(preview_size, Image.Resampling.LANCZOS).save(view / 'print_preview.png')
    if pdf:
        import fitz
        _immutable(view / 'draft.pdf', Path(pdf).read_bytes())
        with fitz.open(view/'draft.pdf') as doc:
            if len(doc) != 1:
                raise ValueError('A reviewable figure must be a single-page PDF')
            actual = [doc[0].rect.width/72*25.4, doc[0].rect.height/72*25.4]
            if any(abs(a-float(b)) > .3 for a,b in zip(actual,size_mm)):
                raise ValueError('Final PDF dimensions disagree with the declared size')
            doc[0].get_pixmap(dpi=160, alpha=False).save(view/'pdf_preview.png')
    diag = dict(diagnostics or {})
    diag['scientific_verification'] = 'A separate data/estimator audit is required; this is a visual stage'
    if qa:
        report = _json(qa)
        _immutable(view/'export_qa.json', Path(qa).read_bytes())
        for key in ['automated_status', 'mark_issues', 'layout_issues', 'failures', 'warnings']:
            if key in report:
                diag[key] = report[key]
        if iteration:
            previous_qa = workdir/f'audit_view_{iteration-1}'/'export_qa.json'
            if previous_qa.exists():
                from review_tools import compare_revisions
                diag['revision_comparison'] = compare_revisions(_json(previous_qa), report)
    _immutable(view/'diagnostics.json', _json_text(diag))
    _immutable(view/'review_schema.json', _json_text(_schema(iteration, strict_3d=bool(route), comparisons=comparisons)))
    base_prompt = _review_prompt(mode, reference_role, briefing, bool(pdf))
    if route:
        base_prompt += _strict_prompt(route)
    _immutable(view/'adapter_prompt.txt', base_prompt)
    _capture(review_engine.compose, ref=str(view/'reference_clean.png'), draft=str(canonical),
             out_dir=str(view), reviewer_md=str(view/'adapter_prompt.txt'), height=920, gutter=28)
    files = [canonical, workdir/'review_cycle.json', *geometry_files,
             *[p for p in view.rglob('*') if p.is_file()]]
    manifest = {**config, 'reference_role': reference_role, 'iteration': iteration,
        'request_sha256':request_sha, 'draft_sha256': _sha(canonical),
        'reference_evidence': reference_role,
        'required_images': ['composite.png', 'reference_clean.png', 'draft_fullres.png', 'print_preview.png']
                           + (['pdf_preview.png'] if pdf else []) + extra_images,
        'three_d_comparisons': comparisons,
        'sha256': {str(p.relative_to(workdir)).replace('\\','/'): _sha(p) for p in files},
        'audit_view': str(view), 'not_a_review': True}
    _immutable(manifest_path, _json_text(manifest))
    _immutable(view/'stage_manifest.sha256', _sha(manifest_path) + '\n')
    return manifest


def _data_first_repair_handoff(workdir, manifest, result):
    """Bind a semantic handoff to a real committed review, without rewriting it."""
    entries = [a for a in _attempts(workdir) if a['result_id'] == result['result_id']]
    if len(entries) != 1 or entries[0]['action'] != 'draw':
        raise ValueError('Repair handoff needs the committed draw review')
    entry = entries[0]
    if entry['draft_sha256'] != manifest['draft_sha256']:
        raise ValueError('Repair review is not bound to this staged draft')
    feedback = workdir / f"review_feedback_{manifest['iteration']}"
    review = entry['review']
    text = f"""# Data-first repair instructions

Use this file and annotated.png as the drawing handoff. The engine notes.md
preserves the returned observations. Repair the current draft against the frozen
scientific/display brief and its readability at the declared final size.
Preserve the review's positive anchors. Apply only its actual focus themes and
boxes; this handoff adds no aesthetic findings or scientific validation.

Reference role: {manifest['reference_role']}.
Do not copy the briefing card or treat it as a visual target. A previous draft
or declared design reference supplies context only, not scientific truth or a
requirement to reproduce its chart type, motifs, or palette.

Committed reviewer session: {entry['reviewer_session']}
Committed result ID: {entry['result_id']}
Draft SHA-256: {entry['draft_sha256']}
Returned payload SHA-256: {entry['terminal_payload_sha256']}

Frozen brief:
{manifest['briefing']}

Complete committed review (verbatim field values, including all positive
anchors, floor findings, focus themes and composite-pixel boxes):

```json
{_json_text(review).rstrip()}
```
"""
    path = feedback / 'repair_instructions.md'
    _immutable(path, text)
    binding = {'mode':'data-first', 'reference_role':manifest['reference_role'],
        'result_id':entry['result_id'], 'reviewer_session':entry['reviewer_session'],
        'draft_sha256':entry['draft_sha256'],
        'terminal_payload_sha256':entry['terminal_payload_sha256'],
        'committed_review_sha256':hashlib.sha256(_json_text(review).encode('utf-8')).hexdigest(),
        'repair_instructions_sha256':_sha(path), 'annotated_sha256':_sha(feedback/'annotated.png'),
        'original_notes_sha256':_sha(feedback/'notes.md')}
    _immutable(feedback/'repair_handoff.json', _json_text(binding))
    return path


def _strict_extension_error(review, comparisons):
    """Validate the routed control-comparison fields in addition to the base schema."""
    missing = [key for key in THREE_D_DELTA_FIELDS if key not in review]
    if missing:
        return 'Missing strict 3D fields: ' + ', '.join(missing)
    if not isinstance(review['target_dimension'], str) or not review['target_dimension'].strip():
        return 'target_dimension must be nonempty text'
    if review['movement_delta'] not in THREE_D_MOVEMENTS:
        return 'movement_delta must use a declared strict 3D enum value'
    for field in ['must_preserve', 'candidate_regressions', 'remaining_gaps']:
        value = review[field]
        if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
            return field + ' must be a string list'
    if not isinstance(review['accept_over_control'], bool):
        return 'accept_over_control must be boolean'
    if review['next_single_change'] is not None and not isinstance(review['next_single_change'], str):
        return 'next_single_change must be text or null'
    cards = review.get('comparison_scorecards', {})
    if comparisons and not isinstance(cards, dict):
        return 'comparison_scorecards must contain separately observed control/baseline cards'
    for name in comparisons:
        error = review_engine.scorecard_error({'three_d_scorecard': cards.get(name)}, require_pass=False)
        if error:
            return 'comparison_scorecards.' + name + ': ' + error
    if review['accept_over_control'] and 'control' in comparisons:
        # Original candidate-selection.md: primary records cannot regress
        # against the accepted rendered control. Check the observed cards,
        # rather than trusting an empty reviewer-written regression list or
        # allowing improved text/overall scores to compensate.
        candidate = review['three_d_scorecard']
        control = cards['control']
        regressed = [field for field in review_engine.PRIMARY_MINIMUMS
            if candidate[field] < control[field]]
        if regressed:
            return 'Strict 3D control acceptance has primary score regressions: ' + ', '.join(regressed)
    if review['fidelity']['verdict'] == 'ship' and (
            not review['accept_over_control'] or review['movement_delta'] != 'accepted'
            or review['candidate_regressions'] or review['remaining_gaps']
            or review['next_single_change'] not in (None, '')):
        return 'Strict 3D ship cannot reject control acceptance or leave regressions/gaps/repairs'
    return None


def _strict_repair_handoff(workdir, manifest, result):
    entries = [a for a in _attempts(workdir) if a['result_id'] == result['result_id']]
    if len(entries) != 1 or entries[0]['action'] != 'draw':
        raise ValueError('Strict repair handoff needs the committed draw review')
    entry = entries[0]
    if entry['draft_sha256'] != manifest['draft_sha256']:
        raise ValueError('Strict repair review is not bound to the staged candidate')
    feedback = workdir/f"review_feedback_{manifest['iteration']}"
    text = f"""# Strict 3D repair handoff

Read this file, annotated.png and the frozen audit view's routed
strict modules. The host must actually deliver these images and guides.
Start from the accepted rendered control; move only the actual review's active
record under its preserve locks. An independent redraw remains a probe.
Reject primary regressions; a baseline improvement alone cannot replace control.
Geometry/resource checks and all uncertainties remain separate scientific evidence.
The engine notes.md is preserved; no review wording can
promote an internal previous draft to an external published reference.

Mode: {manifest['three_d_mode']}
Reference role: {manifest['reference_role']}
Reviewer session: {entry['reviewer_session']}
Result ID: {entry['result_id']}
Candidate SHA-256: {entry['draft_sha256']}
Returned payload SHA-256: {entry['terminal_payload_sha256']}

Frozen brief:
{manifest['briefing']}

Complete committed review; preserve its anchors, scorecard, movement, locks,
regressions, remaining gaps and one next change verbatim:

```json
{_json_text(entry['review']).rstrip()}
```
"""
    path = feedback/'strict_3d_repair_instructions.md'
    _immutable(path, text)
    _immutable(feedback/'strict_3d_repair_handoff.json', _json_text({
        'result_id': entry['result_id'], 'draft_sha256': entry['draft_sha256'],
        'stage_manifest_sha256': _sha(workdir/f"audit_view_{manifest['iteration']}"/'stage_manifest.json'),
        'terminal_payload_sha256': entry['terminal_payload_sha256'],
        'repair_instructions_sha256': _sha(path), 'annotated_sha256': _sha(feedback/'annotated.png'),
        'original_notes_sha256': _sha(feedback/'notes.md')}))
    return path


def accept_review(workdir, review, *, iteration, reviewer_session):
    """Record an actual host-returned payload and materialize authorized repair notes."""
    workdir = Path(workdir).resolve()
    manifest = verify_stage(workdir, iteration)
    # Ledger validation also refuses further use after two invalid attempts.
    _attempts(workdir)
    if not isinstance(reviewer_session, str) or not reviewer_session.strip():
        raise ValueError('The actual fresh reviewer session ID is required')
    source = Path(review).resolve()
    if source.is_relative_to(workdir/f'audit_view_{iteration}'):
        raise ValueError('Incoming review must be outside the bounded audit view')
    # Percent encoding preserves the full real host ID even when it contains slashes.
    incoming = workdir / ('.review_incoming_' + quote(reviewer_session, safe='')
                         + f'_{iteration}_' + (_sha(source)[:12] if source.is_file() else 'missing') + '.json')
    if source.is_file():
        _immutable(incoming, source.read_bytes())
        if manifest['strict_3d']:
            try:
                payload = _json(incoming)
            except (ValueError, UnicodeError):
                payload = None  # The engine records the actual malformed bytes.
            classification, _ = review_engine.classify_review(payload, strict_3d=True)
            if classification != 'invalid':
                error = _strict_extension_error(payload, manifest.get('three_d_comparisons', []))
                if error:
                    # Keep the actual incoming bytes; never rewrite opinions or scores
                    # to manufacture an invalid review or a passing one.
                    raise ValueError('Strict 3D routed-field preflight rejected review: ' + error)
    output = _capture(review_engine.record_decision, workdir=str(workdir), review=str(incoming),
        draft=str(workdir/f'img_iter{iteration}.png'), iter=iteration,
        reviewer_session=reviewer_session, min_reviews=manifest['min_reviews'],
        max_iters=manifest['max_iters'], strict_3d=manifest['strict_3d'])
    result = json.loads(output)
    verify_stage(workdir, iteration)
    if result['draft_sha256'] != manifest['draft_sha256']:
        raise ValueError('Decision is not bound to the staged draft')
    if result['action'] == 'draw':
        feedback = workdir/f'review_feedback_{iteration}'
        if not result.get('replayed') or not (feedback/'annotated.png').is_file():
            _capture(review_engine.annotate, out_dir=str(feedback), max_iters=manifest['max_iters'])
        if manifest['strict_3d']:
            result['repair_instructions'] = str(_strict_repair_handoff(workdir,manifest,result))
        elif manifest['mode'] == 'data-first':
            result['repair_instructions'] = str(_data_first_repair_handoff(workdir,manifest,result))
        else:
            result['repair_instructions'] = str(feedback/'notes.md')
        result['annotated'] = str(feedback/'annotated.png')
    return result


def select_iteration(workdir, *, iteration, reason, unresolved=()):
    """Explicitly select a reviewed draft; a cap never implies clean acceptance."""
    workdir = Path(workdir).resolve()
    attempts = _attempts(workdir)
    if not attempts or attempts[-1]['action'] not in {'ship', 'stop_at_cap'}:
        raise ValueError('Selection needs a terminal review gate decision')
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError('Give the actual selection reason')
    if not isinstance(unresolved, (tuple,list)) or any(not isinstance(x,str) or not x.strip() for x in unresolved):
        raise ValueError('Unresolved issues must be specific text entries')
    terminal = attempts[-1]
    eligible = [a for a in attempts if a['iter']==iteration and a['classification'] in {'all_clear','actionable'}
        and a['review'].get('quality_floor',{}).get('passed') is True
        and a['review'].get('fidelity',{}).get('verdict') in {'ship','close'}]
    if not eligible:
        raise ValueError('Selected iteration has no floor-passing ship/close review')
    if terminal['action']=='ship' and (iteration!=terminal['iter'] or unresolved):
        raise ValueError('A clean ship selects the current iteration without unresolved repairs')
    if terminal['action']=='stop_at_cap' and not unresolved:
        raise ValueError('Cap selection must preserve unresolved review issues')
    manifest = verify_stage(workdir,iteration)
    if manifest['strict_3d']:
        accepted = [entry for entry in eligible
            if review_engine.scorecard_error(entry['review'], require_pass=True) is None
            and _strict_extension_error(entry['review'], manifest.get('three_d_comparisons', [])) is None
            and entry['review']['accept_over_control']
            and not entry['review']['candidate_regressions']]
        if not accepted:
            raise ValueError('Strict 3D selection needs passing declared rubric scores and explicit non-regressing control acceptance')
    result = {'selected_iteration': iteration, 'reason': reason, 'unresolved': list(unresolved),
        'status': 'ship' if terminal['action']=='ship' else 'selected_with_unresolved_issues',
        'scope': 'Visual/design gate only; scientific/data verification is separate',
        'terminal_action': terminal['action'], 'transport': TRANSPORT,
        'draft_sha256': manifest['draft_sha256'], 'png': str(workdir/f'img_iter{iteration}.png'),
        'pdf': str(workdir/f'audit_view_{iteration}'/'draft.pdf') if (workdir/f'audit_view_{iteration}'/'draft.pdf').is_file() else None,
        'independence': 'Host-supplied fresh session identifiers; isolation is not authenticated by this script'}
    _immutable(workdir/'selection.json', _json_text(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    stage = sub.add_parser('stage')
    stage.add_argument('--workdir',required=True); stage.add_argument('--draft',required=True)
    stage.add_argument('--iter',type=int,default=0); stage.add_argument('--mode',choices=['data-first','reference-fit'],default='data-first')
    stage.add_argument('--reference'); stage.add_argument('--reference-role',choices=['brief_only','design_reference','previous_draft'])
    stage.add_argument('--brief',required=True,help='Text file with scientific question and display semantics')
    stage.add_argument('--width-mm',required=True,type=float);stage.add_argument('--height-mm',required=True,type=float)
    stage.add_argument('--pdf');stage.add_argument('--qa');stage.add_argument('--diagnostics')
    stage.add_argument('--min-reviews',type=int,default=2);stage.add_argument('--max-iters',type=int,default=3)
    stage.add_argument('--strict-3d',action='store_true')
    stage.add_argument('--three-d-mode',choices=sorted(THREE_D_MODES))
    stage.add_argument('--three-d-subtype',action='append',default=[],choices=sorted(THREE_D_SUBTYPES))
    stage.add_argument('--geometry-evidence');stage.add_argument('--control');stage.add_argument('--baseline')
    stage.add_argument('--three-d-view',action='append',default=[],metavar='NAME=PATH')
    accept = sub.add_parser('accept')
    accept.add_argument('--workdir',required=True);accept.add_argument('--review',required=True)
    accept.add_argument('--iter',required=True,type=int);accept.add_argument('--reviewer-session',required=True)
    select = sub.add_parser('select')
    select.add_argument('--workdir',required=True);select.add_argument('--iter',required=True,type=int)
    select.add_argument('--reason',required=True);select.add_argument('--unresolved',action='append',default=[])
    args = parser.parse_args()
    if args.command=='stage':
        views = {}
        for item in args.three_d_view:
            name, separator, path = item.partition('=')
            if not separator or not path or name in views or name in {'control', 'baseline'}:
                parser.error('--three-d-view needs a unique nonreserved NAME=PATH')
            views[name] = path
        result=stage_review(args.workdir,args.draft,iteration=args.iter,mode=args.mode,
            reference=args.reference,reference_role=args.reference_role,
            briefing=Path(args.brief).read_text(encoding='utf-8'),size_mm=(args.width_mm,args.height_mm),
            pdf=args.pdf,qa=args.qa,diagnostics=_json(args.diagnostics) if args.diagnostics else None,
            min_reviews=args.min_reviews,max_iters=args.max_iters,strict_3d=args.strict_3d,
            three_d_mode=args.three_d_mode,three_d_subtypes=args.three_d_subtype,
            geometry_evidence=args.geometry_evidence,control=args.control,baseline=args.baseline,
            three_d_views=views)
    elif args.command=='accept':
        result=accept_review(args.workdir,args.review,iteration=args.iter,reviewer_session=args.reviewer_session)
    else:
        result=select_iteration(args.workdir,iteration=args.iter,reason=args.reason,unresolved=args.unresolved)
    print(_json_text(result))


if __name__=='__main__':
    main()
