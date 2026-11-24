"""Animated unique titles for the bordo_menu pack: pixel-font plates with a colour flow, one sheet per title.

    python make_titles.py <bordo_menu textures dir> <output dir>

Reads the pack's own bold font (font/bold.png) and writes, under <output dir>:
    textures/font/titles/<id>.png   every frame of a title, one frame per row (10px high cells)
    titles.json                     code points, sizes and frame counts - input for apply_titles.py
    preview.png, preview.gif        what the titles look like in the tab list / over a head

Each frame is its own character (U+EC00 and up, see CODEPOINT_BASE) so TAB can flip through them.
Adding a title: append an entry to TITLES, rerun, rerun apply_titles.py, add its condition to the title_anim
chain in plugins/TAB/config.yml and its two items to the unique titles menu, then /iazip and /tab reload.
"""
import colorsys
import json
import math
import os
import random
import sys
from types import SimpleNamespace

from PIL import Image

SRC, OUT = sys.argv[1], sys.argv[2]

GLYPH_ROWS = ["АБВГДЕЁЖЗИЙКЛМНО", "ПРСТУФХЦЧШЩЪЫЬЭЮ", "ЯІЇЄҐABCDEFGHIJK", "LMNOPQRSTUVWXYZ0", "123456789.,:;!?-"]
CELL_W, CELL_H = 10, 8          # one glyph cell of font/bold.png
FRAME_H = CELL_H + 2            # glyph rows plus the outline above and below
ASCENT = 8                      # cell row 0 sits 7px above the baseline, the outline one more
FRAMES = 16
CODEPOINT_BASE, CODEPOINT_STEP = 0xEC00, 0x20   # 32 code points reserved per title

# 7x6 ornaments drawn next to the rarer titles, same height as the capitals
ORNAMENTS = {
    'star': ["...#...", "...#...", "#######", ".#####.", ".##.##.", "##...##"],
    'crown': ["#..#..#", "#.###.#", "#######", "#######", ".#####.", "#######"],
    'skull': [".#####.", "#######", "#..#..#", "#######", ".##.##.", ".#.#.#."],
    'spark': ["...#...", "..###..", "#######", "..###..", "...#...", "......."],
    'drop': ["...#...", "..###..", ".#####.", "#######", "#######", ".#####."],
}


def rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def scale(c, f):
    return tuple(max(0, min(255, round(v * f))) for v in c)


def cyclic(stops, u):
    """Colour at position u (any real number) on a gradient that loops back to its first stop."""
    u %= 1.0
    pos = u * len(stops)
    i = int(pos)
    return mix(stops[i % len(stops)], stops[(i + 1) % len(stops)], pos - i)


def rainbow(u, s=0.55, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(u % 1.0, s, v)
    return (round(r * 255), round(g * 255), round(b * 255))


class Font:
    def __init__(self, path):
        self.sheet = Image.open(path).convert('RGBA')

    def glyph(self, ch):
        """The glyph as a set of (x, y) pixels and its width."""
        row = next(i for i, r in enumerate(GLYPH_ROWS) if ch in r)
        col = GLYPH_ROWS[row].index(ch)
        cell = self.sheet.crop((col * CELL_W, row * CELL_H, (col + 1) * CELL_W, (row + 1) * CELL_H))
        alpha = cell.split()[3]
        width = alpha.getbbox()[2]
        return {(x, y) for x in range(width) for y in range(CELL_H) if alpha.getpixel((x, y)) > 127}, width


def layout(font, text, left=None, right=None):
    """Pixels of the whole plate (ornaments included), which of them belong to ornaments, and the plate width."""
    lit, deco, x = set(), set(), 0

    def ornament(name):
        nonlocal x
        for dy, line in enumerate(ORNAMENTS[name]):
            for dx, c in enumerate(line):
                if c == '#':
                    lit.add((x + dx, 1 + dy))
                    deco.add((x + dx, 1 + dy))
        x += 7 + 2

    if left:
        ornament(left)
    for ch in text:
        if ch == ' ':
            x += 3
            continue
        pixels, width = font.glyph(ch)
        lit.update((x + px, py) for px, py in pixels)
        x += width + 1
    if right:
        x += 1
        ornament(right)
        x -= 2
    else:
        x -= 1
    return lit, deco, x


# Vertical shading of the six capital rows (cell rows 1..6): lit from above, like the plates in the menus.
SHADE = {0: 1.22, 1: 1.22, 2: 1.10, 3: 1.0, 4: 0.94, 5: 0.84, 6: 0.72, 7: 0.72}
LIFT = {0: 0.30, 1: 0.30, 2: 0.12}      # how far the top rows are pulled towards white


def shaded(color, y):
    return scale(mix(color, (255, 255, 255), LIFT.get(y, 0.0)), SHADE[y])


def glint(color, x, y, phase, width, start=0.15, end=0.55):
    """A diagonal highlight that crosses the plate once per loop, between `start` and `end` of the cycle."""
    if not start <= phase < end:
        return color
    head = (phase - start) / (end - start) * (width + 14) - 7
    distance = abs((x + (6 - y) * 0.8) - head)
    return mix(color, (255, 255, 255), 0.85 if distance < 1.0 else 0.45 if distance < 2.2 else 0.0)


# ─── the titles ────────────────────────────────────────────────────────────────────────────────────────────
# flow(x, y, phase) -> base colour of a letter pixel; phase runs 0..1 over the loop and every effect is periodic in it.

def flowing(stops, period=34.0, slant=0.0):
    palette = [rgb(s) for s in stops]
    return lambda x, y, phase, w: cyclic(palette, (x + y * slant) / period - phase)


def fire(x, y, phase, w):
    # flames climb: the gradient runs bottom-up and scrolls, with a slow sideways wobble
    palette = [rgb(s) for s in ('#FF2200', '#FF6A00', '#FFB400', '#FFF27A', '#FFB400', '#FF6A00')]
    return cyclic(palette, (6 - y) / 9.0 + x / 60.0 - phase)


def unicorn(x, y, phase, w):
    return rainbow(x / 46.0 - phase, 0.50, 1.0)


def absolute(x, y, phase, w):
    return mix(rainbow((x + y) / 40.0 - phase, 0.38, 1.0), (255, 255, 255), 0.25)


def demon(x, y, phase, w):
    # pale body, as on the reference screenshot; the blood on top is painted in `post`
    palette = [rgb(s) for s in ('#FFE6EA', '#FFC2CC', '#FFE6EA', '#FFFFFF')]
    return cyclic(palette, x / 30.0 - phase)


def blood(ctx, x, y, color):
    """Blood on the top edge of the letters, as on the reference screenshot: the top row is always red and
    every column has its own drip that creeps down and retreats over the loop."""
    if (x, y) in ctx.deco:
        return mix(color, rgb('#FF4658'), 0.55) if y <= 2 else color
    rnd = random.Random(x * 7919)
    drip = 1.0 + 2.2 * rnd.random() * (0.5 + 0.5 * math.sin(2 * math.pi * (ctx.phase + rnd.random())))
    depth = y - min(py for (px, py) in ctx.lit if px == x and (px, py) not in ctx.deco)
    if depth < drip - 1.0:
        return rgb('#E0142E')
    if depth < drip:
        return rgb('#FF5466')    # the lighter tip of a drip
    return color


def twinkle(points):
    """Star pixels that flash white for two frames each, at their own moment of the loop."""
    def post(ctx, x, y, color):
        for (sx, sy, at) in points:
            if (x, y) == (sx, sy) and ctx.frame in (at % FRAMES, (at + 1) % FRAMES):
                return (255, 255, 255)
        return color
    return post


def glitch_rows(frame):
    """Row shifts for the glitch title: most frames are clean, a few tear one or two rows sideways."""
    tears = {3: {2: 1, 3: 1}, 4: {5: -1}, 9: {1: -1, 2: -1, 6: 1}, 10: {4: 1}, 13: {3: -1}}
    return tears.get(frame, {})


TITLES = [
    dict(id='imba', text='ИМБА', rarity='rare', flow=fire, outline='#5A0A00', glint=None),
    dict(id='toxic', text='ТОКСИК', rarity='rare', outline='#16330A', glint=None,
         flow=flowing(('#7CFF2B', '#D2FF4A', '#7CFF2B', '#B45CFF', '#7A2BE0', '#B45CFF'), period=40.0, slant=0.6)),
    dict(id='sigma', text='СИГМА', rarity='rare', outline='#16263A', glint=(0.10, 0.60),
         flow=flowing(('#7FA3CC', '#B9D6F2', '#EAF6FF', '#B9D6F2'), period=30.0)),
    dict(id='glitch', text='ГЛИТЧ', rarity='epic', outline='#1A0B33', glint=None, glitch=True,
         flow=flowing(('#22F2FF', '#FFFFFF', '#FF3BD8', '#FFFFFF'), period=22.0)),
    dict(id='cosmos', text='КОСМОС', rarity='epic', outline='#120A3A', glint=None, left='spark', right='spark',
         flow=flowing(('#4F6BFF', '#9A5CFF', '#FF78DC', '#9A5CFF'), period=44.0, slant=0.5),
         post=twinkle([(3, 3, 2), (14, 2, 7), (27, 5, 11), (38, 2, 14), (51, 3, 5)])),
    dict(id='unicorn', text='ЕДИНОРОГ', rarity='epic', flow=unicorn, outline='#3A1A4A', glint=None),
    dict(id='legend', text='ЛЕГЕНДА', rarity='legendary', outline='#4A2A00', glint=(0.05, 0.50), left='star', right='star',
         flow=flowing(('#FFB300', '#FFD84A', '#FFF3B0', '#FFD84A'), period=48.0)),
    dict(id='tsar', text='ЦАРЬ', rarity='legendary', outline='#2E0F45', glint=(0.55, 0.95), left='crown', right='crown',
         flow=flowing(('#FFC83C', '#FFE9A0', '#FFC83C', '#C45CFF', '#8A33E6', '#C45CFF'), period=46.0)),
    dict(id='demon', text='ДЕМОН', rarity='legendary', flow=demon, outline='#4A0612', glint=None, left='skull', right='skull',
         post=blood),
    dict(id='absolute', text='АБСОЛЮТ', rarity='mythic', flow=absolute, outline='#2A2440', glint=(0.0, 0.42),
         left='spark', right='spark', post=twinkle([(3, 3, 1), (12, 1, 9), (30, 6, 5), (47, 1, 13), (62, 3, 8)])),
]


def render(title, font):
    lit, deco, width = layout(font, title['text'], title.get('left'), title.get('right'))
    outline = rgb(title['outline'])
    w = width + 2
    frames = []
    for frame in range(FRAMES):
        phase = frame / FRAMES
        shifts = glitch_rows(frame) if title.get('glitch') else {}
        ctx = SimpleNamespace(frame=frame, phase=phase, lit=lit, deco=deco, width=width)
        pixels = {}
        for (x, y) in lit:
            color = title['flow'](x, y, phase, width)
            color = shaded(color, y)
            if title.get('post'):
                color = title['post'](ctx, x, y, color)
            if title.get('glint'):
                color = glint(color, x, y, phase, width, *title['glint'])
            pixels[(x, y)] = color
        image = Image.new('RGBA', (w, FRAME_H), (0, 0, 0, 0))
        px = image.load()
        # the outline never moves, so every frame of a title has exactly the same width
        for (x, y) in lit:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    px[x + 1 + dx, y + 1 + dy] = outline + (255,)
        for (x, y), color in pixels.items():
            px[x + 1, y + 1] = color + (255,)
        for y, dx in shifts.items():
            # a torn row: letter pixels slide inside the outline and leave a coloured fringe
            row = {x: pixels[(x, y)] for x in range(width) if (x, y) in pixels}
            for x in range(width):
                if (x, y) in lit:
                    source = row.get(x - dx)
                    px[x + 1, y + 1] = (source if source else rgb('#FF3BD8' if dx > 0 else '#22F2FF')) + (255,)
        frames.append(image)
    return frames, w


def main():
    font = Font(os.path.join(SRC, 'font', 'bold.png'))
    sheets = os.path.join(OUT, 'textures', 'font', 'titles')
    os.makedirs(sheets, exist_ok=True)
    manifest, rendered = [], []
    for index, title in enumerate(TITLES):
        frames, w = render(title, font)
        sheet = Image.new('RGBA', (w, FRAME_H * FRAMES), (0, 0, 0, 0))
        for i, frame in enumerate(frames):
            sheet.paste(frame, (0, i * FRAME_H))
        sheet.save(os.path.join(sheets, title['id'] + '.png'))
        base = CODEPOINT_BASE + index * CODEPOINT_STEP
        manifest.append(dict(id=title['id'], text=title['text'], rarity=title['rarity'], width=w, height=FRAME_H,
                             ascent=ASCENT, frames=FRAMES, codepoints=[base + i for i in range(FRAMES)],
                             file='font/titles/' + title['id'] + '.png'))
        rendered.append((title, frames, w))
    with open(os.path.join(OUT, 'titles.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    preview(rendered)
    print('titles:', ', '.join(f"{m['id']} {m['width']}x{m['height']}" for m in manifest))


def preview(rendered):
    """Titles on a tab-list-like dark strip, 5x. PNG shows four moments of the loop, GIF plays it."""
    k, pad, row_h = 5, 6, FRAME_H + 4
    width = max(w for _, _, w in rendered) + 2 * pad

    def board(frame_index):
        board = Image.new('RGBA', (width, row_h * len(rendered) + pad), rgb('#1B1D26') + (255,))
        for i, (_, frames, _) in enumerate(rendered):
            board.alpha_composite(frames[frame_index], (pad, pad // 2 + i * row_h + 2))
        return board

    moments = [0, FRAMES // 4, FRAMES // 2, 3 * FRAMES // 4]
    strip = Image.new('RGBA', (width * len(moments), row_h * len(rendered) + pad))
    for i, m in enumerate(moments):
        strip.paste(board(m), (i * width, 0))
    strip.resize((strip.width * k, strip.height * k), Image.NEAREST).save(os.path.join(OUT, 'preview.png'))
    boards = [board(i).resize((width * k, (row_h * len(rendered) + pad) * k), Image.NEAREST).convert('RGB') for i in range(FRAMES)]
    boards[0].save(os.path.join(OUT, 'preview.gif'), save_all=True, append_images=boards[1:], duration=100, loop=0)


if __name__ == '__main__':
    main()
