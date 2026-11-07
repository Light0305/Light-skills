"""Light-Science's deterministic visual-review ledger (MIT).

This module records supplied observations. It does not inspect scientific meaning,
call a model, authenticate reviewers, or certify a figure from a numeric score.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import uuid

from PIL import Image, ImageDraw, ImageFont

VIOLATION_KINDS = frozenset({
    'axis_drawn_off_canvas', 'chart_type_abandoned', 'default_matplotlib_aesthetic',
    'encoding_oversimplified', 'font_family_mismatch', 'font_weight_too_heavy',
    'illegible_at_print_size', 'label_clipped', 'signature_motif_dropped',
    'text_obscured_by_marks', 'text_overlaps_text_in_axes', 'text_overlaps_tick',
    'text_overlaps_title', 'misleading_scale', 'unit_or_legend_missing', 'color_unreadable',
})
# Field names remain compatible with already staged Light Chart review schemas.
# These are a review rubric, not calibrated measurements of scientific quality.
SCORE_FIELDS = ('topology', 'geometry_footprint', 'camera_box_aspect',
    'composition_occupancy', 'surface_or_mark_style', 'color_semantics',
    'text_export_floor', 'overall')
PRIMARY_MINIMUMS = dict.fromkeys(SCORE_FIELDS[:4], 82)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def immutable(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('xb') as stream:
            stream.write(data)
    except FileExistsError:
        if path.read_bytes() != data:
            raise ValueError('Existing review artifact differs: ' + str(path))


def font_for(size):
    for candidate in ('DejaVuSans.ttf', 'C:/Windows/Fonts/arial.ttf'):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _strings(value, nonempty=False):
    return isinstance(value, list) and (bool(value) or not nonempty) and all(map(_text, value))


def scorecard_error(review, *, require_pass=False):
    card = review.get('three_d_scorecard') if isinstance(review, dict) else None
    if not isinstance(card, dict) or not _text(card.get('summary')):
        return 'three_d_scorecard needs explicit scores and an observed summary'
    for field in SCORE_FIELDS:
        value = card.get(field)
        if type(value) is not int or not 0 <= value <= 100:
            return field + ' must be an integer from 0 to 100'
    if require_pass:
        limits = {**dict.fromkeys(SCORE_FIELDS, 75), **PRIMARY_MINIMUMS, 'overall': 85}
        below = [field for field, minimum in limits.items() if card[field] < minimum]
        if below:
            return 'Review rubric below declared thresholds: ' + ', '.join(below)
    return None


def classify_review(review, *, strict_3d=False):
    """Check a structured observation, including contradictory acceptance claims."""
    if not isinstance(review, dict) or type(review.get('iter')) is not int or review['iter'] < 0:
        return 'invalid', 'Review must be an object with a nonnegative integer iter'
    inventory, anchor = review.get('reference_inventory'), review.get('anchor')
    if not isinstance(inventory, dict) or not all(_text(inventory.get(k)) for k in ('chart_type', 'signature_element')):
        return 'invalid', 'Describe the actual display and its identifying construction'
    if not _strings(inventory.get('motifs'), True):
        return 'invalid', 'reference_inventory.motifs must contain observations'
    if not isinstance(anchor, dict) or not _strings(anchor.get('what_is_right'), True) or not isinstance(anchor.get('measurements'), dict):
        return 'invalid', 'Record positive anchors and explicit measurements'
    floor, fidelity = review.get('quality_floor'), review.get('fidelity')
    if not isinstance(floor, dict) or type(floor.get('passed')) is not bool:
        return 'invalid', 'quality_floor.passed must be boolean'
    violations = floor.get('violation_kinds')
    if not isinstance(violations, list) or any(not isinstance(v, str) or v not in VIOLATION_KINDS for v in violations):
        return 'invalid', 'Unknown or malformed quality-floor violations'
    if floor.get('summary') is not None and not _text(floor.get('summary')):
        return 'invalid', 'quality_floor.summary must be specific text or null'
    if floor['passed'] and violations:
        return 'invalid', 'A passing floor cannot contain unresolved floor violations'
    if not floor['passed'] and (not violations or not _text(floor.get('summary'))):
        return 'invalid', 'A failed floor needs a violation and an explanation'
    if not isinstance(fidelity, dict) or fidelity.get('verdict') not in ('ship', 'close', 'off') or not _text(fidelity.get('paragraph')):
        return 'invalid', 'Explain the fidelity verdict'
    if not _strings(review.get('focus_themes')) or not isinstance(review.get('boxes'), list):
        return 'invalid', 'focus_themes and boxes must be arrays'
    for box in review['boxes']:
        if not isinstance(box, dict) or not _text(box.get('note')) or any(type(box.get(k)) is not int for k in ('x0', 'y0', 'x1', 'y1')):
            return 'invalid', 'Each box needs integer coordinates and a specific note'
        if box['x0'] < 0 or box['y0'] < 0 or box['x1'] <= box['x0'] or box['y1'] <= box['y0']:
            return 'invalid', 'Box must have positive area and nonnegative coordinates'
    issues = bool(review['focus_themes'] or review['boxes'] or not floor['passed'])
    if fidelity['verdict'] == 'ship' and issues:
        return 'invalid', 'A ship verdict contradicts unresolved repair requests'
    if fidelity['verdict'] != 'ship' and not issues:
        return 'invalid', 'A non-ship verdict needs an actionable observation'
    if strict_3d:
        error = scorecard_error(review, require_pass=fidelity['verdict'] == 'ship')
        if error:
            return 'invalid', error
    return ('actionable', 'Repair the supplied observations') if issues else ('all_clear', 'No unresolved visual repairs reported')


def _local(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Review artifact escapes its work directory')
    return path


def review_history(workdir):
    """Verify recorded bytes and links before allowing any subsequent decision."""
    root = Path(workdir).resolve()
    directory = root / 'review_attempts'
    paths = sorted(directory.glob('attempt_*.json'))
    head_path = directory / 'head.json'
    if not paths:
        if head_path.exists():
            raise ValueError('Review ledger head has no events')
        return []
    if not head_path.is_file():
        raise ValueError('Review ledger head missing; recover interrupted commit explicitly')
    events, previous = [], None
    for index, path in enumerate(paths, 1):
        if path.name != f'attempt_{index:06d}.json':
            raise ValueError('Review ledger has a missing or reordered event')
        event = json.loads(path.read_bytes())
        actual = event.get('record_sha256')
        body = {k: v for k, v in event.items() if k != 'record_sha256'}
        if actual != digest(encoded(body)) or event.get('previous_sha256') != previous:
            raise ValueError('Review ledger integrity mismatch')
        for key, expected in [('payload_file', event['terminal_payload_sha256']), ('draft_file', event['draft_sha256'])]:
            source = _local(root, event[key])
            if not source.is_file() or digest(source.read_bytes()) != expected:
                raise ValueError('Recorded review input changed: ' + event[key])
        events.append(event)
        previous = actual
    head = json.loads(head_path.read_bytes())
    if head != {'count': len(events), 'last_sha256': previous}:
        raise ValueError('Review ledger head disagrees with committed events')
    return events


@contextmanager
def _lock(root):
    path = root / '.review-engine.lock'
    try:
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('Review ledger is busy; inspect any interrupted writer before retrying') from None
    try:
        os.close(handle)
        yield
    finally:
        path.unlink()


def _exhausted(events):
    return len(events) >= 2 and all(e['classification'] == 'invalid' for e in events[-2:])


def decide(*, workdir, review, draft, iteration, reviewer_session, min_reviews=2, max_iters=3, strict_3d=False):
    root, image_path = Path(workdir).resolve(), Path(draft).resolve()
    if type(iteration) is not int or iteration < 0 or any(type(n) is not int or n < 1 for n in (min_reviews, max_iters)) or iteration >= max_iters:
        raise ValueError('Invalid iteration or review budget')
    if not _text(reviewer_session) or not image_path.is_file() or not image_path.is_relative_to(root):
        raise ValueError('An actual reviewer identifier and staged local draft are required')
    root.mkdir(parents=True, exist_ok=True)
    with _lock(root):
        events = review_history(root)
        if _exhausted(events):
            raise ValueError('Reviewer retry budget exhausted; preserve events and resolve the cause')
        source = Path(review)
        payload_bytes = source.read_bytes() if source.is_file() else b''
        image_bytes = image_path.read_bytes()
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.verify()
        settings = {'min_reviews': min_reviews, 'max_iters': max_iters, 'strict_3d': bool(strict_3d)}
        identity = {'iter': iteration, 'reviewer_session': reviewer_session,
                    'terminal_payload_sha256': digest(payload_bytes), 'draft_sha256': digest(image_bytes), **settings}
        request_id = digest(encoded(identity))
        for event in events:
            if event['request_sha256'] == request_id:
                return {**event, 'replayed': True}
        if events:
            last = events[-1]
            if any(last[k] != v for k, v in settings.items()):
                raise ValueError('Review budgets and mode are immutable within a cycle')
            if last['action'] in ('ship', 'stop_at_cap'):
                raise ValueError('Review cycle is already terminal')
            if iteration == last['iter']:
                if last['action'] == 'draw' or identity['draft_sha256'] != last['draft_sha256']:
                    raise ValueError('Use the authorized next iteration for a changed draft')
            elif iteration != last['iter'] + 1 or last['action'] != 'draw' or identity['draft_sha256'] == last['draft_sha256']:
                raise ValueError('A valid draw decision and changed draft must authorize the next iteration')
        elif iteration != 0:
            raise ValueError('A cycle starts with iteration zero')
        try:
            payload = json.loads(payload_bytes, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON value')))
        except (ValueError, UnicodeError):
            payload = None
        classification, reason = classify_review(payload, strict_3d=strict_3d)
        if any(e['reviewer_session'] == reviewer_session for e in events):
            classification, reason = 'invalid', 'Reviewer session was already used for another returned payload'
        if isinstance(payload, dict) and payload.get('iter') != iteration:
            classification, reason = 'invalid', 'Returned review concerns a different iteration'
        if classification != 'invalid' and payload['boxes']:
            meta_path = root / f'audit_view_{iteration}' / 'comparison.json'
            if not meta_path.is_file():
                classification, reason = 'invalid', 'Boxes need a staged comparison coordinate frame'
            else:
                meta = json.loads(meta_path.read_bytes())
                x0, y0, x1, y1 = meta['draft_rect']
                if any(not (x0 <= b['x0'] < b['x1'] <= x1 and y0 <= b['y0'] < b['y1'] <= y1) for b in payload['boxes']):
                    classification, reason = 'invalid', 'A box lies outside the composite draft panel'
        count = sum(e['classification'] != 'invalid' for e in events) + (classification != 'invalid')
        action = ('retry_reviewer' if classification == 'invalid' else
                  'ship' if classification == 'all_clear' and count >= min_reviews else
                  'review_same_draft' if classification == 'all_clear' else
                  'stop_at_cap' if iteration + 1 >= max_iters else 'draw')
        directory = root / 'review_attempts'
        payload_file = directory / ('payload_' + digest(payload_bytes) + '.bin')
        immutable(payload_file, payload_bytes)
        previous = events[-1]['record_sha256'] if events else None
        event = {**identity, 'engine': 'light-science-review/1', 'classification': classification,
                 'reason': reason, 'action': action, 'valid_review_count': count,
                 'review': payload, 'request_sha256': request_id, 'previous_sha256': previous,
                 'result_id': digest(encoded([request_id, previous]))[:24],
                 'payload_file': payload_file.relative_to(root).as_posix(),
                 'draft_file': image_path.relative_to(root).as_posix()}
        event['record_sha256'] = digest(encoded(event))
        immutable(directory / f'attempt_{len(events)+1:06d}.json', encoded(event))
        head = directory / 'head.json'
        temporary = directory / ('.head-' + uuid.uuid4().hex)
        immutable(temporary, encoded({'count': len(events)+1, 'last_sha256': event['record_sha256']}))
        os.replace(temporary, head)
        if _exhausted(events + [event]):
            raise ValueError('A second invalid review was recorded; reviewer retry budget exhausted')
        return {**event, 'replayed': False}


def compose(args):
    """Produce a comparison with an explicit composite-pixel coordinate frame."""
    output = Path(args.out_dir)
    if type(args.height) is not int or args.height < 100 or type(args.gutter) is not int or args.gutter < 0:
        raise ValueError('Comparison height must be >=100 and gutter nonnegative')
    panels = []
    for source in (args.ref, args.draft):
        with Image.open(source) as image:
            image = image.convert('RGBA')
            white = Image.new('RGBA', image.size, 'white')
            white.alpha_composite(image)
            width = max(1, round(image.width * args.height / image.height))
            panels.append(white.convert('RGB').resize((width, args.height), Image.Resampling.LANCZOS))
    header = 44
    offset = panels[0].width + args.gutter
    canvas = Image.new('RGB', (offset + panels[1].width, args.height + header), 'white')
    draw = ImageDraw.Draw(canvas)
    for x, label, panel in ((0, 'REFERENCE / CONTEXT', panels[0]), (offset, 'DRAFT', panels[1])):
        draw.text((x+12, 10), label, fill='#202020', font=font_for(19))
        canvas.paste(panel, (x, header))
    data = io.BytesIO(); canvas.save(data, format='PNG')
    immutable(output / 'composite.png', data.getvalue())
    meta = {'schema_version': 1, 'size': list(canvas.size),
            'reference_rect': [0, header, panels[0].width, canvas.height],
            'draft_rect': [offset, header, canvas.width, canvas.height],
            'reference_sha256': digest(Path(args.ref).read_bytes()),
            'draft_sha256': digest(Path(args.draft).read_bytes())}
    immutable(output / 'comparison.json', encoded(meta))
    prompt = Path(args.reviewer_md).read_text(encoding='utf-8')
    prompt += '\n\nComposite coordinates: ' + json.dumps(meta) + '\n'
    prompt += 'Boxes use integer COMPOSITE pixels inside draft_rect. Open the full-resolution draft too.\n'
    immutable(output / 'review_prompt.txt', prompt.encode('utf-8'))
    print(json.dumps({'composite': str(output/'composite.png'), **meta}))


def record_decision(args):
    result = decide(workdir=args.workdir, review=args.review, draft=args.draft,
        iteration=args.iter, reviewer_session=args.reviewer_session,
        min_reviews=args.min_reviews, max_iters=args.max_iters, strict_3d=args.strict_3d)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


def annotate(args):
    destination = Path(args.out_dir).resolve()
    root = destination.parent
    events = review_history(root)
    if not events or events[-1]['action'] != 'draw':
        raise ValueError('Annotations require a committed draw decision')
    event = events[-1]
    if destination.name != f"review_feedback_{event['iter']}":
        raise ValueError('Feedback destination must match the committed iteration')
    view = root / f"audit_view_{event['iter']}"
    with Image.open(view/'composite.png') as source:
        canvas = source.convert('RGB')
    drawing = ImageDraw.Draw(canvas)
    for number, box in enumerate(event['review']['boxes'], 1):
        drawing.rectangle(tuple(box[k] for k in ('x0', 'y0', 'x1', 'y1')), outline='#b42318', width=3)
        drawing.text((box['x0']+3, box['y0']+3), str(number), font=font_for(18), fill='#b42318')
    stream = io.BytesIO(); canvas.save(stream, format='PNG')
    immutable(destination/'annotated.png', stream.getvalue())
    notes = ['# Recorded visual review', '', 'Apply only the observations returned by the reviewer.',
             'Preserve the positive anchors and verify the scientific inputs separately.', '',
             'Result: ' + event['result_id'], 'Draft SHA-256: ' + event['draft_sha256'], '',
             '```json', json.dumps(event['review'], ensure_ascii=False, indent=2), '```', '']
    immutable(destination/'notes.md', '\n'.join(notes).encode('utf-8'))
    immutable(destination/'annotation.json', encoded({'result_id': event['result_id'],
        'source_sha256': digest((view/'composite.png').read_bytes()),
        'annotated_sha256': digest(stream.getvalue()), 'boxes': event['review']['boxes']}))
    print(json.dumps({'annotated': str(destination/'annotated.png')}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    comparison = sub.add_parser('compose', help='Stage two actual images for review')
    for option in ('ref', 'draft', 'out-dir', 'reviewer-md'):
        comparison.add_argument('--'+option, required=True)
    comparison.add_argument('--height', type=int, default=920)
    comparison.add_argument('--gutter', type=int, default=28)
    comparison.set_defaults(call=compose)
    decision = sub.add_parser('decide', help='Record a host-returned review; never launch a reviewer')
    for option in ('workdir', 'review', 'draft', 'reviewer-session'):
        decision.add_argument('--'+option, required=True)
    decision.add_argument('--iter', type=int, required=True)
    decision.add_argument('--min-reviews', type=int, default=2)
    decision.add_argument('--max-iters', type=int, default=3)
    decision.add_argument('--strict-3d', action='store_true')
    decision.set_defaults(call=record_decision)
    draw = sub.add_parser('annotate', help='Annotate only committed review observations')
    draw.add_argument('--out-dir', required=True)
    draw.set_defaults(call=annotate)
    args = parser.parse_args()
    args.call(args)


if __name__ == '__main__':
    main()
