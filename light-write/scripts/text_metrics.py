"""Count only the supplied plain-text scope; no Markdown/TeX parsing or model calls."""
import argparse
import json
from pathlib import Path
import sys
import unicodedata


def measure(text, unit, minimum=None, maximum=None):
    if not isinstance(text, str):
        raise ValueError('Text must be a string')
    if unit not in {'han', 'whitespace_words'}:
        raise ValueError('Unit must be han or whitespace_words')
    for name, value in (('minimum', minimum), ('maximum', maximum)):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(name + ' must be a nonnegative integer')
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError('Minimum exceeds maximum')
    if unit == 'han':
        count = sum(unicodedata.name(c, '').startswith(
            ('CJK UNIFIED IDEOGRAPH-', 'CJK COMPATIBILITY IDEOGRAPH-')) for c in text)
    else:
        count = len(text.split())
    return {'unit': unit, 'count': count, 'minimum': minimum, 'maximum': maximum,
            'within_limits': (minimum is None or count >= minimum) and (maximum is None or count <= maximum),
            'convention': 'Named CJK unified/compatibility ideographs in Python Unicode ' + unicodedata.unidata_version
                          if unit == 'han' else 'Whitespace-delimited tokens, not a universal journal word-count rule'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('text_file', help='UTF-8 plain-text passage or - for stdin')
    parser.add_argument('--unit', choices=['han', 'whitespace_words'], required=True)
    parser.add_argument('--min', type=int, dest='minimum')
    parser.add_argument('--max', type=int, dest='maximum')
    args = parser.parse_args(argv)
    try:
        body = sys.stdin.read() if args.text_file == '-' else Path(args.text_file).read_text(encoding='utf-8-sig')
        result = measure(body, args.unit, args.minimum, args.maximum)
        status = 0 if result['within_limits'] else 1
    except (OSError, UnicodeError, ValueError) as error:
        result, status = {'error': str(error)}, 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return status


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
