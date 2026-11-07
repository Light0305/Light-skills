"""Compare equal-sized reference/export images without calling it 1:1 fidelity."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter, ImageStat


def dark_mask(im):
    return im.convert('L').point(lambda p: 255 if p < 140 else 0)


def count(mask):
    return sum(mask.histogram()[1:])


def compare(source, rendered):
    with Image.open(source) as a, Image.open(rendered) as b:
        a,b=a.convert('RGB'),b.convert('RGB')
        if a.size != b.size:
            raise ValueError(f'Canvas mismatch: {a.size} vs {b.size}; do not silently rescale')
        diff=ImageChops.difference(a,b)
        nonwhite_a=ImageChops.difference(a,Image.new('RGB',a.size,'white')).convert('L').point(lambda p:255 if p>25 else 0)
        nonwhite_b=ImageChops.difference(b,Image.new('RGB',b.size,'white')).convert('L').point(lambda p:255 if p>25 else 0)
        foreground=ImageChops.lighter(nonwhite_a,nonwhite_b)
        ma,mb=dark_mask(a),dark_mask(b)
        na,nb=count(ma),count(mb)
        recall=count(ImageChops.darker(ma,mb.filter(ImageFilter.MaxFilter(7))))/na if na else 0
        precision=count(ImageChops.darker(mb,ma.filter(ImageFilter.MaxFilter(7))))/nb if nb else 0
        return {
            'canvas_px':list(a.size),
            'whole_canvas_rgb_mae_0_255':sum(ImageStat.Stat(diff).mean)/3,
            'foreground_union_rgb_mae_0_255':sum(ImageStat.Stat(diff,foreground).mean)/3,
            'foreground_union_fraction':count(foreground)/(a.width*a.height),
            'dark_pixel_recall_with_3px_square_tolerance':recall,
            'dark_pixel_precision_with_3px_square_tolerance':precision,
            'definitions':{
                'foreground':'Union of pixels >25 grayscale levels away from white in either image.',
                'dark':'Grayscale <140; tolerant match uses a 7x7 square dilation (3 px each direction).',
                'limitations':'Position-sensitive diagnostics, not perceptual similarity or a 1:1 percentage. Text, fill texture and antialiasing affect results. Scientific topology requires separate review.'}}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('rendered',type=Path)
    p.add_argument('report',type=Path)
    args=p.parse_args()
    if args.report.exists():
        p.error('Report exists; choose a new name')
    result=compare(args.source,args.rendered)
    result.update(source=str(args.source.resolve()),rendered=str(args.rendered.resolve()),
                  source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),
                  rendered_sha256=hashlib.sha256(args.rendered.read_bytes()).hexdigest())
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
