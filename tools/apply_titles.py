"""Wire the titles produced by make_titles.py into the server files.

    python apply_titles.py <generated dir> <server root>

<server root> is the folder that holds plugins/ (a local copy of the server is fine). Updated in place:
    plugins/ItemsAdder/contents/bordo_menu/resourcepack/assets/bordo_menu/textures/font/titles/<id>.png
    plugins/ItemsAdder/contents/bordo_menu/resourcepack/assets/minecraft/font/include/space.json   (one provider per title)
    plugins/TAB/animations.yml                                 (title_<id> animations: one frame character per step)
    plugins/DeluxeMenus/gui_menus/titles/unique_titles.yml     (names, suffix command, effect lines)
    plugins/BCases/prizes.yml                                  (names in the title case: prize, broadcast, screen title)
    plugins/ItemsAdder/contents/bordo_menu/README.txt          (one line about the new texture folder)
Safe to run again after regenerating: every step replaces what the previous run wrote.
In game afterwards: /iazip, /tab reload, /dm reload, /bcases reload.
"""
import json
import os
import re
import shutil
import sys

import yaml

GEN, ROOT = sys.argv[1], sys.argv[2]
PACK = os.path.join(ROOT, 'plugins/ItemsAdder/contents/bordo_menu/resourcepack/assets')
SPACE_JSON = os.path.join(PACK, 'minecraft/font/include/space.json')
ANIMATIONS = os.path.join(ROOT, 'plugins/TAB/animations.yml')
MENU = os.path.join(ROOT, 'plugins/DeluxeMenus/gui_menus/titles/unique_titles.yml')
PRIZES = os.path.join(ROOT, 'plugins/BCases/prizes.yml')
PACK_README = os.path.join(ROOT, 'plugins/ItemsAdder/contents/bordo_menu/README.txt')

RARITY = {'rare': 'редкий', 'epic': 'эпический', 'legendary': 'легендарный', 'mythic': 'мифический'}
INTERVAL = 100  # ms between frames; TAB needs a multiple of 50
# effect line in the menu tooltip: old text -> new text, only where the animation really changed
EFFECTS = {
    'буквы мерцают огнём': 'пламя поднимается по буквам',
    'алое сердцебиение': 'по буквам стекает кровь',
}

titles = json.load(open(os.path.join(GEN, 'titles.json'), encoding='utf-8'))


def read(path):
    # newline='' keeps the file's own line endings (animations.yml is CRLF) so untouched lines stay untouched
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def escaped(codepoint):
    return '\\u%04X' % codepoint


# 1. textures
target = os.path.join(PACK, 'bordo_menu/textures/font/titles')
os.makedirs(target, exist_ok=True)
for title in titles:
    shutil.copyfile(os.path.join(GEN, 'textures', title['file']), os.path.join(target, title['id'] + '.png'))

# 2. font providers: a sheet is one column of frames, so every row of "chars" is a single character
space = json.loads(read(SPACE_JSON))
space['providers'] = [p for p in space['providers'] if not str(p.get('file', '')).startswith('bordo_menu:font/titles/')]
for title in titles:
    space['providers'].append({
        'type': 'bitmap',
        'file': 'bordo_menu:' + title['file'],
        'height': title['height'],
        'ascent': title['ascent'],
        'chars': [chr(c) for c in title['codepoints']],
    })
write(SPACE_JSON, json.dumps(space, ensure_ascii=False, indent=1))

# 3. TAB animations: everything above the first non-title animation is ours
text = read(ANIMATIONS)
blocks = list(re.finditer(r'^([A-Za-z0-9_-]+):[ \t]*\r?$', text, re.M))
eol = '\r\n' if '\r\n' in text else '\n'
rest = next((m.start() for m in blocks if not m.group(1).startswith('title_')), len(text))
head = [
    '# TAB (plugins/TAB/animations.yml): анимации уникальных титулов. Имя анимации - title_<id>, её показывает',
    '# цепочка условий title_anim из config.yml (по мете LuckPerms title_anim=<id>).',
    '# Каждый кадр - отдельный символ ресурспака (картинка титула, U+EC00 и дальше): файлы',
    '# bordo_menu/textures/font/titles/<id>.png, символы прописаны в assets/minecraft/font/include/space.json.',
    '# change-interval - миллисекунды между кадрами (кратно 50). Если игроков много, а титулы стоят в табе и над',
    '# головой - увеличьте до 150-200: каждый кадр уходит пакетом всем, кто видит игрока.',
    '# Блоки собраны скриптами tools/make_titles.py и tools/apply_titles.py - ими же добавляется новый титул.',
    '',
]
for title in titles:
    head.append('# «%s» - %s' % (title['text'], RARITY[title['rarity']]))
    head.append('title_%s:' % title['id'])
    head.append('  change-interval: %d' % INTERVAL)
    head.append('  texts:')
    head.extend('    - "&f%s"' % escaped(c) for c in title['codepoints'])
write(ANIMATIONS, eol.join(head) + eol + text[rest:])

# 4. menu and title case: the styled name is one string that repeats in names, commands and messages
menu_text, prizes_text = read(MENU), read(PRIZES)
items = yaml.safe_load(menu_text)['items']
report = []
for title in titles:
    old = items['unique_' + title['id']]['display_name']
    new = '§f' + chr(title['codepoints'][0])
    in_menu, in_prizes = menu_text.count(old), prizes_text.count(old)
    if in_menu < 4 or in_prizes < 3:
        raise SystemExit('%s: expected the name 4+ times in the menu and 3+ in prizes.yml, found %d and %d' % (title['id'], in_menu, in_prizes))
    menu_text, prizes_text = menu_text.replace(old, new), prizes_text.replace(old, new)
    report.append('%s %d+%d' % (title['id'], in_menu, in_prizes))
for old, new in EFFECTS.items():
    menu_text = menu_text.replace(old, new)
for old, new in (
    ('TAB/animations_snippet.yml). В чате и там, где TAB не настроен, виден статичный градиент.',
     'TAB/animations.yml). В чате и там, где TAB не настроен, виден первый кадр - та же картинка без движения.'),
    ('# Названия титулов оставлены обычным шрифтом (это и есть суффикс), строки-действия - шрифт APPLECUBE.',
     '# Название титула - картинка из ресурспака (символ U+EC00 и дальше, он же суффикс), строки-действия - шрифт APPLECUBE.'),
    ('# Новый титул: tools/make_title_animation.py печатает статичный вид, кадры для TAB и условие.',
     '# Новый титул: tools/make_titles.py рисует кадры, tools/apply_titles.py прописывает их в пак, TAB, это меню и кейс.'),
):
    menu_text = menu_text.replace(old, new)
write(MENU, menu_text)
write(PRIZES, prizes_text)

# 5. the pack's own README lists what lives in each texture folder
readme = read(PACK_README)
if 'textures/font/titles/' not in readme:
    eol = '\r\n' if '\r\n' in readme else '\n'
    anchor = '      textures/font/sidebar/, logo/   скорборд и логотип TAB' + eol
    line = '      textures/font/titles/           уникальные титулы: лист кадров на титул, символы U+EC00..ED2F (TAB листает их анимацией)' + eol
    if readme.count(anchor) == 1:
        write(PACK_README, readme.replace(anchor, anchor + line))

print('titles applied:', ', '.join(report))
