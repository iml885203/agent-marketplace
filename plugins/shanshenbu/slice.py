# Regenerate: python slice.py <rows> hooks/frames.ts spritesheet.webp [preview.png]
import sys, struct, base64, json
from PIL import Image
ROWS = int(sys.argv[1]) if len(sys.argv) > 1 else 14
sheet = Image.open(sys.argv[3]).convert('RGBA')
CW, CH = 192, 208
NAMES = ['idle','runRight','runLeft','wave','jump','failed','waiting','working','review']
frames = {}
for r, name in enumerate(NAMES):
    fs = []
    for c in range(8):
        cell = sheet.crop((c*CW, r*CH, (c+1)*CW, (r+1)*CH))
        if cell.getbbox() is None or cell.getchannel('A').getextrema()[1] < 32: continue
        fs.append(cell)
    frames[name] = fs
# union bbox across all frames
box = [CW, CH, 0, 0]
for fs in frames.values():
    for f in fs:
        b = f.getchannel('A').point(lambda a: 255 if a > 32 else 0).getbbox()
        box = [min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3])]
w, h = box[2]-box[0], box[3]-box[1]
H = ROWS * 2
W = round(w * H / h)
DEF = 0x01000000
def pack(img):
    px = img.load()
    words = []
    for y in range(ROWS):
        for x in range(W):
            t, b = px[x, 2*y], px[x, 2*y+1]
            ta, ba = t[3] >= 110, b[3] >= 110
            rgb = lambda p: (p[0] << 16) | (p[1] << 8) | p[2]
            if ta and ba: words += [0x2580, rgb(t), rgb(b)]
            elif ta: words += [0x2580, rgb(t), DEF]
            elif ba: words += [0x2584, rgb(b), DEF]
            else: words += [0x20, DEF, DEF]
    return base64.b64encode(struct.pack('<%dI' % len(words), *words)).decode()
def shrink(f):
    c = f.crop(tuple(box))
    # premultiplied downscale keeps edges clean
    return c.resize((W, H), Image.LANCZOS, reducing_gap=3.0)
out = {}
preview = Image.new('RGBA', (W*8*8, H*8*len(NAMES)), (40, 40, 40, 255))
for r, name in enumerate(NAMES):
    out[name] = []
    for i, f in enumerate(frames[name]):
        s = shrink(f)
        out[name].append(pack(s))
        a = s.copy(); a.putalpha(a.getchannel('A').point(lambda v: 255 if v >= 110 else 0))
        preview.alpha_composite(a.resize((W*8, H*8), Image.NEAREST), (i*W*8, r*H*8))
preview.save(sys.argv[4]) if len(sys.argv) > 4 else None
with open(sys.argv[2], 'w') as fh:
    fh.write('// Generated from the 閃身步 spritesheet by slice.py; do not edit.\n')
    fh.write(f'export const COLUMNS = {W}\nexport const ROWS = {ROWS}\n\n')
    fh.write('export type Anim = ' + ' | '.join(repr(n) for n in NAMES) + '\n\n')
    fh.write('export const FRAMES: Record<Anim, string[]> = ' + json.dumps(out, indent=1) + '\n')
print(W, ROWS, {k: len(v) for k, v in out.items()})
