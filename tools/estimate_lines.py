"""Estimate how many printed lines a CV markdown file will take.

105 chars per line for paragraphs, 95 for bullets, one extra line per heading.
Limit 55 for one page. Calibrated against real renders: 57 estimated lines came out
at 44 to 47 rendered lines and a page holds about 46, so 57 is borderline and 55
is safe. The estimate is a guide; render.py's page count is the authority.

    python tools/estimate_lines.py my-cv.md [more files]
    python tools/estimate_lines.py --verbose my-cv.md
"""
import math, sys

PARA, BULLET = 105, 95


def estimate(path, verbose=False):
    total = 0
    rows = []
    for raw in open(path, encoding='utf-8').read().splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith('#'):
            n = 2                      # the heading line plus its spacing
            kind = 'head'
        elif line.startswith('- '):
            n = math.ceil(len(line) / BULLET)
            kind = 'bullet'
        else:
            n = math.ceil(len(line) / PARA)
            kind = 'para'
        total += n
        rows.append((n, kind, len(line), line[:70]))
    if verbose:
        for n, kind, ln, head in rows:
            print(f'{n:2d} {kind:6s} {ln:4d}  {head}')
    words = sum(len(l.split()) for l in open(path, encoding='utf-8').read().splitlines()
                if l.strip() and not l.startswith('#'))
    return total, words


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    verbose = '--verbose' in sys.argv
    if not args:
        sys.exit(__doc__)
    for p in args:
        total, words = estimate(p, verbose)
        flag = '' if total <= 55 else f'  OVER by {total - 55}'
        print(f'{total:3d} lines  {words:4d} words  {p}{flag}')
