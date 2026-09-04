import re, math, os, subprocess, json

D    = os.path.dirname(os.path.abspath(__file__))
SIZE = int(os.environ.get('SIZE', 192))
N    = int(os.environ.get('N', 20))
DUR  = int(os.environ.get('DUR', 20))   # ms per frame; N * DUR is the cycle
ROT  = float(os.environ.get('ROT', 26))    # degrees at full open, per hand
PX   = float(os.environ.get('PX', 18))     # pivot x
PY   = float(os.environ.get('PY', 40))     # pivot y
POW  = float(os.environ.get('POW', 0.90))  # s(u) sharpness at contact
WARP = float(os.environ.get('WARP', 1.0))  # <1 opens fast, >1 closes fast
FLASH= float(os.environ.get('FLASH', 0.30))# impact line duration, fraction of half-cycle
MARGIN = float(os.environ.get('MARGIN', 0.02))

src = open(os.path.join(D, '1f44f.svg')).read()
P = {}
for m in re.finditer(r'<path\b[^>]*>', src):
    f = re.search(r'fill="([^"]*)"', m.group(0)).group(1)
    P[{'#EF9645': 'back', '#FA743E': 'lines', '#FFDB5E': 'front'}[f]] = m.group(0)

def s_of(u):   return math.sin(math.pi * (u ** WARP)) ** POW
def a_of(u):
    d = min(u, 1 - u) * 2
    return max(0.0, 1 - (d / FLASH) ** 1.4)

def body(u, vb):
    s, a = s_of(u), a_of(u)
    r = s * ROT
    g = [f'<g transform="rotate({-r:.3f} {PX} {PY})">{P["back"]}</g>',
         f'<g transform="rotate({r:.3f} {PX} {PY})">{P["front"]}</g>']
    if a > 0.004:
        k = 1 + (1 - a) * 0.22
        g.append(f'<g opacity="{a:.3f}" transform="translate(18 18) scale({k:.3f}) translate(-18 -18)">{P["lines"]}</g>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">{"".join(g)}</svg>'

# pass 1: find the union bbox across all frames, in svg units
probe, W = os.path.join(D, '.probe.svg'), 400
big = '-40 -40 116 116'
lo_x = lo_y = 1e9; hi_x = hi_y = -1e9
for i in range(N):
    open(probe, 'w').write(body(i / N, big))
    png = probe[:-4] + '.png'
    subprocess.run(['resvg', '-w', str(W), '-h', str(W), probe, png], check=True)
    out = subprocess.run(['magick', png, '-format', '%@', 'info:'],
                         capture_output=True, text=True, check=True).stdout
    w, h, ox, oy = map(int, re.match(r'(\d+)x(\d+)\+(\d+)\+(\d+)', out).groups())
    k = 116 / W
    lo_x = min(lo_x, -40 + ox * k);      lo_y = min(lo_y, -40 + oy * k)
    hi_x = max(hi_x, -40 + (ox + w) * k); hi_y = max(hi_y, -40 + (oy + h) * k)

side = max(hi_x - lo_x, hi_y - lo_y) * (1 + MARGIN * 2)
cx, cy = (lo_x + hi_x) / 2, (lo_y + hi_y) / 2
vb = f'{cx - side/2:.3f} {cy - side/2:.3f} {side:.3f} {side:.3f}'

# pass 2: emit frames
OUT = os.path.join(D, 'frames')
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))
for i in range(N):
    p = os.path.join(OUT, 'f%03d.svg' % i)
    open(p, 'w').write(body(i / N, vb))
    subprocess.run(['resvg', '-w', str(SIZE), '-h', str(SIZE), p, p[:-4] + '.png'], check=True)
for f in (probe, probe[:-4] + '.png'):
    os.path.exists(f) and os.remove(f)
open(os.path.join(OUT, 'duration'), 'w').write(str(DUR))
print(json.dumps({'n': N, 'dur': DUR, 'cycle_ms': N * DUR, 'size': SIZE, 'rot': ROT,
                  'pivot': [PX, PY], 'pow': POW, 'warp': WARP, 'viewBox': vb}, ensure_ascii=False))
