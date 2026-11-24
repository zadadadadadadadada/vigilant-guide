"""Put the rebuilt menu backgrounds on the server and move the arrow shop items onto the new slot wells.

    python apply_menus.py <generated dir> <server root>

<generated dir> is the output of build_menu_backgrounds.py, <server root> the folder that holds plugins/.
  - copies font/gui/*.png and font/pets/pets_shop.png into the bordo_menu pack;
  - plugins/DeluxeMenus/gui_menus/shop/arrows.yml: the nine arrows sat in rows 3-4 under the old header band,
    the new background has their wells in rows 2-3, so every item slot moves up one row (minus 9).
Running it twice is safe: slots that are already in the new layout are left alone.
In game afterwards: /iazip, then /dm reload.
"""
import os
import re
import shutil
import sys

GEN, ROOT = sys.argv[1], sys.argv[2]
TEXTURES = os.path.join(ROOT, 'plugins/ItemsAdder/contents/bordo_menu/resourcepack/assets/bordo_menu/textures')
ARROWS = os.path.join(ROOT, 'plugins/DeluxeMenus/gui_menus/shop/arrows.yml')
OLD_SLOTS = (20, 21, 22, 23, 24, 29, 30, 32, 33)

copied = 0
for folder, _, files in os.walk(os.path.join(GEN, 'font')):
    for name in files:
        source = os.path.join(folder, name)
        rel = os.path.relpath(source, GEN)
        target = os.path.join(TEXTURES, rel)
        if not os.path.isfile(target):
            raise SystemExit('%s is not in the pack - refusing to add an unknown texture' % rel)
        shutil.copyfile(source, target)
        copied += 1

with open(ARROWS, encoding='utf-8') as f:
    text = f.read()
found = sorted(int(n) for n in re.findall(r'^    slot: (\d+)\s*$', text, re.M))
if found == sorted(OLD_SLOTS):
    text = re.sub(r'^(    slot: )(\d+)(\s*)$', lambda m: m.group(1) + str(int(m.group(2)) - 9) + m.group(3), text, flags=re.M)
    with open(ARROWS, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    moved = 'moved up one row'
elif found == sorted(n - 9 for n in OLD_SLOTS):
    moved = 'already in the new layout'
else:
    raise SystemExit('arrows.yml: unexpected item slots %s' % found)

print('textures copied: %d, arrows.yml: %s' % (copied, moved))
