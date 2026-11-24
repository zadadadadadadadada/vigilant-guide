"""The "muted by a moderator" voice icon for the tab list, in the family of the pack's voice on/off icons.

    python make_voice_mute_icon.py <bordo_menu textures dir> <output png>

Keeps the speaker of font/voice/off.png and swaps its cross for a red "no entry" ring, so the three states read
as: waves - voice on, cross - voice off, ring - silenced by staff. 13x8, same height as on.png and off.png.
"""
import os
import sys

from PIL import Image

SRC, OUT = sys.argv[1], sys.argv[2]

SPEAKER_COLUMNS = 6                      # the speaker itself; the rest of off.png is the cross
RING = ["..###.", ".#..##", ".#.#.#", ".##..#", "..###."]   # 5x5 ring with a slash, one empty column on the left
RING_AT = (6, 1)
RED = {0: '#FF5F4D', 1: '#FF5F4D', 2: '#F03A3F', 3: '#F03A3F', 4: '#C81B30'}   # top to bottom, as in the cross
OUTLINE_TOP, OUTLINE_BOTTOM = '#2B161B', '#0E0507'


def rgba(value):
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def main():
    off = Image.open(os.path.join(SRC, 'font', 'voice', 'off.png')).convert('RGBA')
    icon = Image.new('RGBA', (13, off.height), (0, 0, 0, 0))
    icon.paste(off.crop((0, 0, SPEAKER_COLUMNS, off.height)), (0, 0))
    red = {(RING_AT[0] + x, RING_AT[1] + y): RED[y] for y, row in enumerate(RING) for x, c in enumerate(row) if c == '#'}
    # outline first, then the ring on top of it
    for (x, y) in red:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                p = (x + dx, y + dy)
                if p not in red and 0 <= p[0] < icon.width and 0 <= p[1] < icon.height and icon.getpixel(p)[3] == 0:
                    icon.putpixel(p, rgba(OUTLINE_TOP if p[1] < 4 else OUTLINE_BOTTOM))
    for p, color in red.items():
        icon.putpixel(p, rgba(color))
    icon.save(OUT)
    print(OUT, icon.size)


if __name__ == '__main__':
    main()
