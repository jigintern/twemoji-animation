import re, math, os, subprocess, json

D    = os.path.dirname(os.path.abspath(__file__))
SIZE = int(os.environ.get('SIZE', 192))
N    = int(os.environ.get('N', 26))
DUR  = int(os.environ.get('DUR', 35))       # ms per frame; N * DUR is the cycle
SPRD = float(os.environ.get('SPRD', 1.30))  # how far a bit flies, as a fraction of its own radius
RIB  = float(os.environ.get('RIB', 0.35))   # streamers travel this fraction of SPRD
RIBR = float(os.environ.get('RIBR', 16))    # streamer spin at full travel, degrees
ROTB = float(os.environ.get('ROTB', 5))     # popper recoil amplitude, degrees
FIN  = float(os.environ.get('FIN', 0.06))   # fade-in of the confetti, fraction of the cycle
HOLD = float(os.environ.get('HOLD', 0.60))  # confetti stays fully opaque until here
FOUT = float(os.environ.get('FOUT', 1.0))   # fade-out sharpness after HOLD
EASE = float(os.environ.get('EASE', 0.55))  # <1 flies fast then coasts
CUT  = float(os.environ.get('CUT', 0.04))   # below this opacity an element is dropped
CX   = float(os.environ.get('CX', 18.0))    # burst origin
CY   = float(os.environ.get('CY', 18.0))
BX   = float(os.environ.get('BX', 4.0))     # popper pivot: base of the cone
BY   = float(os.environ.get('BY', 33.0))
PAD  = float(os.environ.get('PAD', 2.0))    # viewBox padding when FIT=0, svg units
FIT  = int(os.environ.get('FIT', 0))        # 1 fits every frame, 0 lets the confetti fly off-frame
MARGIN = float(os.environ.get('MARGIN', 0.02))

src = open(os.path.join(D, '1f389.svg')).read()
els = re.findall(r'<(?:path|circle)\b[^>]*?/?>', src)
assert len(els) == 15, len(els)
CONE, STREAM, BITS = els[0:3], els[3:7], els[7:15]

def bbox(el):                               # svg units, measured not assumed
    p = os.path.join(D, '.bb.svg')
    open(p, 'w').write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 36">{el}</svg>')
    png = p[:-4] + '.png'
    subprocess.run(['resvg', '-w', '720', '-h', '720', p, png], check=True)
    out = subprocess.run(['magick', png, '-format', '%@', 'info:'],
                         capture_output=True, text=True, check=True).stdout
    w, h, ox, oy = [int(v) * 36 / 720 for v in re.match(r'(\d+)x(\d+)\+(\d+)\+(\d+)', out).groups()]
    for f in (p, png):
        os.path.exists(f) and os.remove(f)
    return (ox + w / 2, oy + h / 2)

CENTERS = {id(e): bbox(e) for e in STREAM + BITS}

def prog(u):   return u ** EASE             # travel, 0 at the burst
def alpha(u):
    # opaque until HOLD, then a smoothstep down to 0 at u=1 so the loop seam stays soft
    if u <= 0: return 0.0
    t = 0.0 if u <= HOLD else min(1.0, (u - HOLD) / (1 - HOLD))
    return min(1.0, u / FIN) * (1 - t * t * (3 - 2 * t)) ** FOUT

def fly(el, u, k):                          # k scales the travel distance
    cx, cy = CENTERS[id(el)]
    t = 1 + SPRD * k * prog(u)
    return (cx - CX) * (t - 1), (cy - CY) * (t - 1)

def body(u, vb):
    a = alpha(u)
    r = ROTB * math.sin(2 * math.pi * u) * (1 - u) ** 1.2
    g = [f'<g transform="rotate({r:.3f} {BX} {BY})">{"".join(CONE)}</g>']
    if a > CUT:
        for el in STREAM:
            dx, dy = fly(el, u, RIB)
            cx, cy = CENTERS[id(el)]
            sp = RIBR * prog(u)
            g.append(f'<g opacity="{a:.3f}" transform="translate({dx:.3f} {dy:.3f}) '
                     f'rotate({sp:.2f} {cx:.3f} {cy:.3f})">{el}</g>')
        for el in BITS:
            dx, dy = fly(el, u, 1.0)
            g.append(f'<g opacity="{a:.3f}" transform="translate({dx:.3f} {dy:.3f})">{el}</g>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">{"".join(g)}</svg>'

probe, W, BIG = os.path.join(D, '.probe.svg'), 400, '-40 -40 116 116'
if FIT:
    lo_x = lo_y = 1e9; hi_x = hi_y = -1e9
    for i in range(N):
        open(probe, 'w').write(body(i / N, BIG))
        png = probe[:-4] + '.png'
        subprocess.run(['resvg', '-w', str(W), '-h', str(W), probe, png], check=True)
        out = subprocess.run(['magick', png, '-format', '%@', 'info:'],
                             capture_output=True, text=True, check=True).stdout
        bw, bh, ox, oy = map(int, re.match(r'(\d+)x(\d+)\+(\d+)\+(\d+)', out).groups())
        k = 116 / W
        lo_x = min(lo_x, -40 + ox * k);        lo_y = min(lo_y, -40 + oy * k)
        hi_x = max(hi_x, -40 + (ox + bw) * k); hi_y = max(hi_y, -40 + (oy + bh) * k)
    side = max(hi_x - lo_x, hi_y - lo_y) * (1 + MARGIN * 2)
    cx, cy = (lo_x + hi_x) / 2, (lo_y + hi_y) / 2
    vb = f'{cx - side/2:.3f} {cy - side/2:.3f} {side:.3f} {side:.3f}'
else:
    side = 36 + PAD * 2
    vb = f'{-PAD:.3f} {-PAD:.3f} {side:.3f} {side:.3f}'

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
print(json.dumps({'n': N, 'dur': DUR, 'cycle_ms': N * DUR, 'size': SIZE, 'sprd': SPRD,
                  'rib': RIB, 'ribr': RIBR, 'rotb': ROTB, 'fin': FIN, 'hold': HOLD, 'fout': FOUT,
                  'ease': EASE, 'fit': FIT, 'pad': PAD, 'viewBox': vb}, ensure_ascii=False))
