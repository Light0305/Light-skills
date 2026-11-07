"""Descriptive raster diagnostics, never a scientific or perceptual quality score."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def pixels(path):
    with Image.open(path) as source:
        rgba = source.convert('RGBA')
        backdrop = Image.new('RGBA', rgba.size, 'white')
        backdrop.alpha_composite(rgba)
        return np.asarray(backdrop.convert('RGB'), dtype=np.float64) / 255


def describe(path, *, white_tolerance=0.04):
    if not 0 <= white_tolerance < 1:
        raise ValueError('white_tolerance must be in [0, 1)')
    rgb = pixels(path)
    mask = np.max(1-rgb, axis=2) > white_tolerance
    y, x = np.nonzero(mask)
    gray = rgb @ np.array([0.2126, 0.7152, 0.0722])
    dx = np.abs(np.diff(gray, axis=1))
    dy = np.abs(np.diff(gray, axis=0))
    return {'path': str(Path(path)), 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        'width_px': rgb.shape[1], 'height_px': rgb.shape[0],
        'aspect_ratio': rgb.shape[1]/rgb.shape[0],
        'nonwhite_fraction': float(mask.mean()),
        'nonwhite_bounds_xyxy': [int(x.min()), int(y.min()), int(x.max()+1), int(y.max()+1)] if len(x) else None,
        'mean_adjacent_luminance_change': {'horizontal': float(dx.mean()) if dx.size else 0,
                                            'vertical': float(dy.mean()) if dy.size else 0},
        'white_tolerance': white_tolerance}


def compare(reference, candidate):
    left, right = pixels(reference), pixels(candidate)
    if left.shape != right.shape:
        return {'same_pixel_grid': False, 'reason': 'No implicit resize, crop, alignment or pixel-error comparison'}
    delta = np.abs(left-right)
    return {'same_pixel_grid': True, 'mean_absolute_channel_difference': float(delta.mean()),
            'p95_absolute_channel_difference': float(np.quantile(delta, .95)),
            'changed_pixel_fraction_at_1_over_255': float((delta.max(axis=2) > 1/255).mean())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('images', nargs='+')
    parser.add_argument('--reference')
    parser.add_argument('--white-tolerance', type=float, default=.04)
    parser.add_argument('--out')
    args = parser.parse_args()
    report = {'scope': 'Raster bookkeeping only. No geometry, meaning, rank, acceptance or statistical inference.',
              'images': [describe(path, white_tolerance=args.white_tolerance) for path in args.images]}
    if args.reference:
        report['comparisons'] = [{'candidate': path, **compare(args.reference, path)} for path in args.images]
    output = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    if args.out:
        Path(args.out).write_text(output, encoding='utf-8')
    else:
        print(output, end='')


if __name__ == '__main__':
    main()
