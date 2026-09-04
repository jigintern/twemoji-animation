import re, math, os, subprocess, json

D    = os.path.dirname(os.path.abspath(__file__))
SIZE = int(os.environ.get('SIZE', 192))
N    = int(os.environ.get('N', 20))
DUR  = int(os.environ.get('DUR', 25))      # ms per frame; N * DUR is the cycle
SQX  = float(os.environ.get('SQX', 0.28))  # min scaleX of a wing (1.0 = fully open)
SCY  = float(os.environ.get('SCY', 1.06))  # scaleY when the wings stand up
LIFT = float(os.environ.get('LIFT', 0.9))  # vertical travel of the body, svg units
AXIS = float(os.environ.get('AXIS', 18.1)) # body axis; wings fold toward it
CY   = float(os.environ.get('CY', 18.0))   # vertical center of the scale
WARP = float(os.environ.get('WARP', 1.0))  # <1 folds fast, >1 unfolds fast
MARGIN = float(os.environ.get('MARGIN', 0.02))

src = open(os.path.join(D, '1f98b.svg')).read()
els = re.findall(r'<path\b[^>]*?/?>', src)
assert len(els) == 11, len(els)
RIGHT, LEFT, BODY = els[0:5], els[5:10], els[10]

def w_of(u):    # 1.0 open at u=0, SQX folded at u=0.5
    return 1 - (1 - SQX) * (1 - math.cos(2 * math.pi * (u ** WARP))) / 2

def lift_of(u):
    return -LIFT * (1 - math.cos(2 * math.pi * u)) / 2

def body(u, vb):
    w = w_of(u)
    sy = 1 + (SCY - 1) * (1 - w) / (1 - SQX) if SQX < 1 else 1
    sc = (f'translate({AXIS} {CY}) scale({w:.4f} {sy:.4f}) translate({-AXIS} {-CY})')
    g = (f'<g transform="translate(0 {lift_of(u):.3f})">'
         f'<g transform="{sc}">{"".join(RIGHT)}{"".join(LEFT)}</g>'
         f'{BODY}</g>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">{g}</svg>'

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
print(json.dumps({'n': N, 'dur': DUR, 'cycle_ms': N * DUR, 'size': SIZE,
                  'sqx': SQX, 'scy': SCY, 'lift': LIFT, 'warp': WARP, 'viewBox': vb},
                 ensure_ascii=False))
