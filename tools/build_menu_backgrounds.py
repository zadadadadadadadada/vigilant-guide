"""Redraw the menu backgrounds that carried a fake "category tile" and a flat header band.

    python build_menu_backgrounds.py <bordo_menu textures dir> <output dir>

Two groups of textures in font/gui (output keeps the same relative paths):

  1. Menus already drawn in the panel style - ench_common, ench_custom, donpets, pets_shop, weapons, equip -
     only lose the red tile that sat in slot 4. Nothing else moves.
  2. arrows, enchants, masks, personal, shopsel had a flat panel with a dark band across the two top rows and
     tiles that did not line up with any slot. They are rebuilt from the ench_common panel (suns, gems, clouds,
     water line), shortened to five rows and recoloured, with slot wells exactly where the menu has items.

Slot geometry of a 240px-wide menu texture: slot (column, row) starts at x = 39 + 18*column, y = 41 + 18*row.
The colour helpers (Rule, recolor) follow tools/build_shop_menus.py from the 2026-11-23 backup.
Run it against the ORIGINAL textures: group 2 reads the title plates from them.
"""
import colorsys
import os
import shutil
import sys

from PIL import Image

SRC, OUT = sys.argv[1], sys.argv[2]
X0, Y0, P = 39, 41, 18
PANEL = (41, 40, 199, 131)        # inside of the full-width panel on a five-row texture, x1/y1 exclusive
CUT = (95, 113)                   # row 3 of the six-row template: removed to get five rows
TILE = (4, 0)                     # the slot the decorative tile was drawn in

BLUE = (195, 250)                 # ench_common panel, wells, water, gems
LIME = (58, 150)                  # ench_common suns and stars


def load(rel):
    return Image.open(os.path.join(SRC, rel)).convert('RGBA')


def cell(c, r):
    return X0 + c * P, Y0 + r * P


def hsv(c):
    h, s, v = colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)
    return h * 360, s, v


def rgb(h, s, v, a=255):
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
    return round(r * 255), round(g * 255), round(b * 255), a


class Rule:
    """Move every colour whose hue lies in `band` to hue `to`, keeping its shading."""

    def __init__(self, band, to, smul=1.0, vmul=1.0, spread=0.6, smin=0.10, vmin=0.03):
        self.band, self.to, self.smul, self.vmul, self.spread, self.smin, self.vmin = band, to, smul, vmul, spread, smin, vmin
        self.mid = (band[0] + band[1]) / 2

    def hit(self, c):
        if c[3] == 0:
            return False
        h, s, v = hsv(c)
        return self.band[0] <= h <= self.band[1] and s >= self.smin and v >= self.vmin

    def apply(self, c):
        h, s, v = hsv(c)
        return rgb(self.to + (h - self.mid) * self.spread, s * self.smul, v * self.vmul, c[3])


def recolor(im, rect, rules):
    px = im.load()
    for y in range(rect[1], rect[3]):
        for x in range(rect[0], rect[2]):
            for rule in rules:
                if rule.hit(px[x, y]):
                    px[x, y] = rule.apply(px[x, y])
                    break


def erase_tile(im):
    """Paint the sky back over the tile in slot 4. Every row there is one colour or a two-pixel dither,
    so the two pixels left of the tile continue it exactly; the same pixels on the right must agree.
    The tile's drop shadow disturbs the dither up to two pixels past the cell, hence the wider fill."""
    px = im.load()
    x0, y0 = cell(*TILE)
    for y in range(y0 + 1, y0 + P - 1):
        left = (px[x0 - 1, y], px[x0, y])
        right = (px[x0 + P + 1, y], px[x0 + P + 2, y])     # same parity as the left pair
        if left != right:
            raise SystemExit('row %d: the sky left and right of the tile differs, cannot erase it cleanly' % y)
        for x in range(x0 + 1, x0 + P + 1):
            px[x, y] = left[(x - (x0 - 1)) % 2]


def sky(template, y):
    """Background colour of a well row: the first panel column never carries a well, gem or star."""
    return template.getpixel((42, y))


def five_rows(template):
    """The six-row template without its fourth row, and the gradient eased across the seam."""
    w, h = template.size
    im = Image.new('RGBA', (w, h - (CUT[1] - CUT[0])), (0, 0, 0, 0))
    im.paste(template.crop((0, 0, w, CUT[0])), (0, 0))
    im.paste(template.crop((0, CUT[1], w, h)), (0, CUT[0]))
    # rows below the seam come from 18px lower in the gradient: lift them, fading out towards the water
    above, below = sky(template, CUT[0] - 1), sky(template, CUT[1])
    step = [above[i] - below[i] for i in range(3)]
    px = im.load()
    fade_rows = PANEL[3] - P - CUT[0]
    probe = Rule(BLUE, 0)
    for y in range(CUT[0], CUT[0] + fade_rows):
        k = 1.0 - (y - CUT[0]) / fade_rows
        for x in range(PANEL[0], PANEL[2]):
            c = px[x, y]
            if probe.hit(c):
                px[x, y] = tuple(max(0, min(255, round(c[i] + step[i] * k))) for i in range(3)) + (c[3],)
    return im


def set_wells(im, template, wells):
    """Keep the template wells listed in `wells`, wipe the others, and add wells the template lacks."""
    px, tpx = im.load(), template.load()
    present = {(c, r) for r in (1, 2) for c in range(1, 8)}
    for (c, r) in present - set(wells):
        x0, y0 = cell(c, r)
        for y in range(y0, y0 + P):
            for x in range(x0, x0 + P):
                px[x, y] = sky(template, y)
    sample = cell(1, 1)
    for (c, r) in set(wells) - present:
        x0, y0 = cell(c, r)
        for j in range(P):
            for i in range(P):
                if not (i in (0, P - 1) and j in (0, P - 1)):      # the four corners stay panel-coloured
                    px[x0 + i, y0 + j] = tpx[sample[0] + i, sample[1] + j]
    # The template shades the margins next to its outer wells with a faint dither. Those wells are gone, so
    # the dots go too; star and gem pixels in the same columns differ far more from the sky and stay.
    if not any(c in (1, 7) for (c, r) in wells):
        for y in range(cell(0, 1)[1], cell(0, 3)[1]):
            base = sky(template, y)
            for x in list(range(51, 57)) + list(range(183, 189)):
                if max(abs(px[x, y][i] - base[i]) for i in range(3)) <= 60:
                    px[x, y] = base
    # The template draws a light rim along the top of its well block (the row above row 1). Keep it only
    # above wells that have nothing on top of them, and give the same rim to wells that start lower.
    rim_y = cell(0, 1)[1] - 1
    lift = tuple(tpx[cell(4, 1)[0] + 4, rim_y][i] - sky(template, rim_y)[i] for i in range(3))
    for c in range(1, 8):
        for r in (1, 2, 3):
            x0, y0 = cell(c, r)
            base = sky(template, y0 - 1)
            if (c, r) in wells and (c, r - 1) not in wells:
                color = tuple(min(255, base[i] + lift[i]) for i in range(3)) + (255,)
            elif r == 1:
                color = base
            else:
                continue
            for x in range(x0, x0 + P):
                px[x, y0 - 1] = color


# name -> panel hue and tweaks, accent hue for suns and stars, slots that hold items
REBUILD = {
    'arrows': dict(panel=Rule(BLUE, 118, smul=0.92, vmul=0.86), accent=Rule(LIME, 46, smul=1.0, vmul=1.05),
                   wells=[(c, 1) for c in range(2, 7)] + [(2, 2), (3, 2), (5, 2), (6, 2)]),
    'enchants': dict(panel=Rule(BLUE, 292, smul=0.95, vmul=0.92), accent=Rule(LIME, 46, smul=1.0, vmul=1.05),
                     wells=[(3, 2), (5, 2)]),
    'masks': dict(panel=Rule(BLUE, 352, smul=0.95, vmul=0.80), accent=Rule(LIME, 28, smul=0.9, vmul=1.0),
                  wells=[(3, 2), (5, 2)]),
    'personal': dict(panel=Rule(BLUE, 190, smul=1.0, vmul=0.86), accent=Rule(LIME, 330, smul=0.8, vmul=1.05),
                     wells=[(3, 2), (5, 2)]),
    'shopsel': dict(panel=Rule(BLUE, 152, smul=0.95, vmul=0.84), accent=Rule(LIME, 46, smul=1.0, vmul=1.05),
                    wells=[(3, 2), (5, 2)]),
}
STRIP = ['ench_common', 'ench_custom', 'donpets', 'pets_shop', 'weapons', 'equip']
OUTLINE = (40, 39, 200, 131)      # the five-row panel with its dark outline, x1/y1 exclusive


def save(im, rel):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


def main():
    for name in STRIP:
        im = load('font/gui/bordo_%s.png' % name)
        erase_tile(im)
        save(im, 'font/gui/bordo_%s.png' % name)
    # ApplePets reads its own copy of the pet shop background
    os.makedirs(os.path.join(OUT, 'font/pets'), exist_ok=True)
    shutil.copyfile(os.path.join(OUT, 'font/gui/bordo_pets_shop.png'), os.path.join(OUT, 'font/pets/pets_shop.png'))

    template = load('font/gui/bordo_ench_common.png')
    erase_tile(template)
    for name, spec in REBUILD.items():
        im = five_rows(template)
        set_wells(im, template, spec['wells'])
        recolor(im, OUTLINE, [spec['panel'], spec['accent']])
        # Only the panel and its dark outline are taken over: the red frame, the title plate and the
        # inventory stay exactly as they are in the menu's own texture.
        out = load('font/gui/bordo_%s.png' % name)
        if out.size != im.size:
            raise SystemExit('%s: expected %s, built %s' % (name, out.size, im.size))
        out.paste(im.crop(OUTLINE), OUTLINE[:2])
        save(out, 'font/gui/bordo_%s.png' % name)
    print('stripped:', ', '.join(STRIP), '| rebuilt:', ', '.join(REBUILD))


if __name__ == '__main__':
    main()
