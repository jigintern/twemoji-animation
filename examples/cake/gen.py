import re, math, os, subprocess, json

D    = os.path.dirname(os.path.abspath(__file__))
SIZE = int(os.environ.get('SIZE', 192))
N    = int(os.environ.get('N', 20))
DUR  = int(os.environ.get('DUR', 30))      # ms per frame; N * DUR is the cycle
AMPY = float(os.environ.get('AMPY', 0.20)) # flame stretch along Y
AMPX = float(os.environ.get('AMPX', 0.08)) # flame squeeze along X, opposite phase
ROT  = float(os.environ.get('ROT', 4))     # flame tilt amplitude, degrees
SKEW = float(os.environ.get('SKEW', 14))    # flame shear: the tip sways, the base stays
H2   = float(os.environ.get('H2', 0.40))   # second harmonic, adds irregularity
SWAY = float(os.environ.get('SWAY', 0.12)) # horizontal drift of the flame tip, svg units
MARGIN = float(os.environ.get('MARGIN', 0.02))

src = open(os.path.join(D, '1f382.svg')).read()
els = re.findall(r'<(?:path|ellipse)\b[^>]*?/?>', src)
assert len(els) == 12, len(els)
FLAME_IX = [7, 9, 11]                      # the three #FAAA35 flames
STATIC   = [e for i, e in enumerate(els) if i not in FLAME_IX]
FLAMES   = [els[i] for i in FLAME_IX]

def bbox(el):                              # svg units, measured not assumed
    p = os.path.join(D, '.bb.svg')
    open(p, 'w').write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 36">{el}</svg>')
    png = p[:-4] + '.png'
    subprocess.run(['resvg', '-w', '720', '-h', '720', p, png], check=True)
    out = subprocess.run(['magick', png, '-format', '%@', 'info:'],
                         capture_output=True, text=True, check=True).stdout
    w, h, ox, oy = [int(v) * 36 / 720 for v in re.match(r'(\d+)x(\d+)\+(\d+)\+(\d+)', out).groups()]
    for f in (p, png):
        os.path.exists(f) and os.remove(f)
    return ox, oy, ox + w, oy + h

# pivot each flame at its own base: bottom edge, horizontal center
PIVOTS = []
for fl in FLAMES:
    x0, y0, x1, y1 = bbox(fl)
    PIVOTS.append(((x0 + x1) / 2, y1))

def wave(u, ph):                           # base wave plus a second harmonic
    return (math.sin(2 * math.pi * u + ph)
            + H2 * math.sin(4 * math.pi * u + ph * 1.7)) / (1 + H2)

def body(u, vb):
    g = list(STATIC)
    for k, (fl, (px, py)) in enumerate(zip(FLAMES, PIVOTS)):
        ph = 2 * math.pi * k / 3
        v  = wave(u, ph)
        sy = 1 + AMPY * v
        sx = 1 - AMPX * v
        r  = ROT * wave(u, ph + math.pi / 2)
        dx = SWAY * wave(u, ph + math.pi / 3)
        k2 = SKEW * wave(u, ph + math.pi / 5)
        g.append(f'<g transform="translate({dx:.3f} 0) rotate({r:.2f} {px:.3f} {py:.3f}) '
                 f'translate({px:.3f} {py:.3f}) skewX({k2:.2f}) scale({sx:.4f} {sy:.4f}) '
                 f'translate({-px:.3f} {-py:.3f})">{fl}</g>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">{"".join(g)}</svg>'

probe, W, BIG = os.path.join(D, '.probe.svg'), 400, '-30 -30 96 96'
lo_x = lo_y = 1e9; hi_x = hi_y = -1e9
for i in range(N):
    open(probe, 'w').write(body(i / N, BIG))
    png = probe[:-4] + '.png'
    subprocess.run(['resvg', '-w', str(W), '-h', str(W), probe, png], check=True)
    out = subprocess.run(['magick', png, '-format', '%@', 'info:'],
                         capture_output=True, text=True, check=True).stdout
    bw, bh, ox, oy = map(int, re.match(r'(\d+)x(\d+)\+(\d+)\+(\d+)', out).groups())
    k = 96 / W
    lo_x = min(lo_x, -30 + ox * k);        lo_y = min(lo_y, -30 + oy * k)
    hi_x = max(hi_x, -30 + (ox + bw) * k); hi_y = max(hi_y, -30 + (oy + bh) * k)

side = max(hi_x - lo_x, hi_y - lo_y) * (1 + MARGIN * 2)
cx, cy = (lo_x + hi_x) / 2, (lo_y + hi_y) / 2
vb = f'{cx - side/2:.3f} {cy - side/2:.3f} {side:.3f} {side:.3f}'

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
print(json.dumps({'n': N, 'dur': DUR, 'cycle_ms': N * DUR, 'size': SIZE, 'ampy': AMPY,
                  'ampx': AMPX, 'rot': ROT, 'skew': SKEW, 'h2': H2, 'sway': SWAY,
                  'pivots': [[round(x, 2), round(y, 2)] for x, y in PIVOTS], 'viewBox': vb},
                 ensure_ascii=False))
