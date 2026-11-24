"""Server-side wiring for AppleVoicechatMute: the "muted" tab icon and the /voice command for players.

    python apply_voice.py <mute icon png> <server root>

<mute icon png> comes from make_voice_mute_icon.py, <server root> is the folder that holds plugins/.
  - pack: font/voice/mute.png and its character U+EBA6 (next to voice on/off, U+EBA4 and U+EBA5);
  - TAB: the voice icon in groups.yml goes through the new condition voice_icon, which shows the muted
    icon for players silenced with /vmute and the usual on/off icon of AppleAddons for everyone else;
  - CommandWhitelist: /voice and its aliases are added to the default group, otherwise players cannot run it.
Every step checks what is already there, so it can be run again.
In game afterwards: /iazip, /tab reload, /cw reload.
"""
import json
import os
import re
import shutil
import sys

ICON, ROOT = sys.argv[1], sys.argv[2]
PACK = os.path.join(ROOT, 'plugins/ItemsAdder/contents/bordo_menu/resourcepack/assets')
SPACE_JSON = os.path.join(PACK, 'minecraft/font/include/space.json')
TAB_GROUPS = os.path.join(ROOT, 'plugins/TAB/groups.yml')
TAB_CONFIG = os.path.join(ROOT, 'plugins/TAB/config.yml')
WHITELIST = os.path.join(ROOT, 'plugins/CommandWhitelist/config.yml')
PACK_README = os.path.join(ROOT, 'plugins/ItemsAdder/contents/bordo_menu/README.txt')
MUTE_FILE, MUTE_CHAR = 'bordo_menu:font/voice/mute.png', '\uEBA6'
COMMANDS = ['voice', 'войс', 'голос']


def read(path):
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


done = []

# pack: texture and character
shutil.copyfile(ICON, os.path.join(PACK, 'bordo_menu/textures/font/voice/mute.png'))
space = json.loads(read(SPACE_JSON))
taken = [p for p in space['providers'] if MUTE_CHAR in ''.join(p.get('chars', [])) and p.get('file') != MUTE_FILE]
if taken:
    raise SystemExit('U+EBA6 is already used by ' + taken[0]['file'])
if not any(p.get('file') == MUTE_FILE for p in space['providers']):
    # right after voice/off.png, so the three voice icons stay together in the file
    index = next(i for i, p in enumerate(space['providers']) if p.get('file') == 'bordo_menu:font/voice/off.png')
    space['providers'].insert(index + 1, {'type': 'bitmap', 'file': MUTE_FILE, 'height': 8, 'ascent': 7, 'chars': [MUTE_CHAR]})
    write(SPACE_JSON, json.dumps(space, ensure_ascii=False, indent=1))
    done.append('pack character')

# TAB: condition and its use in the tab list and over the head
config = read(TAB_CONFIG)
if '  voice_icon:' not in config:
    eol = '\r\n' if '\r\n' in config else '\n'
    block = eol.join([
        'conditions:',
        "  voice_icon:  # AppleVoicechatMute: заглушён модератором (/vmute) - свой значок, иначе вкл/выкл из AppleAddons",
        '    conditions:',
        '    - "%applevoicemute_muted%=true"',
        "    true: '%applevoicemute_icon%'",
        "    false: '%applevoice_icon%'",
    ]) + eol
    # the top-level key only: every condition has a nested "conditions:" list of its own
    top = re.findall(r'^conditions:\r?\n', config, re.M)
    if len(top) != 1:
        raise SystemExit('TAB/config.yml: expected one top-level "conditions:", found %d' % len(top))
    config = re.sub(r'^conditions:\r?\n', lambda m: block, config, count=1, flags=re.M)
    write(TAB_CONFIG, config)
    done.append('TAB condition')
groups = read(TAB_GROUPS)
if '%applevoice_icon%' in groups:
    write(TAB_GROUPS, groups.replace('%applevoice_icon%', '%condition:voice_icon%'))
    done.append('TAB groups')

# CommandWhitelist: the default group's command list ends where its subcommands begin
whitelist = read(WHITELIST)
eol = '\r\n' if '\r\n' in whitelist else '\n'
head, marker, tail = whitelist.partition('    subcommands:')
if not marker:
    raise SystemExit('CommandWhitelist/config.yml: no "subcommands:" of the default group')
missing = [c for c in COMMANDS if ('    - ' + c + eol) not in head]
if missing:
    write(WHITELIST, head + ''.join('    - ' + c + eol for c in missing) + marker + tail)
    done.append('whitelist +' + ','.join(missing))

# the pack's own README lists what lives in each texture folder
readme = read(PACK_README)
if 'textures/font/voice/' not in readme:
    eol = '\r\n' if '\r\n' in readme else '\n'
    line = '      textures/font/voice/            значки войса для TAB: on / off / mute - символы U+EBA4 / U+EBA5 / U+EBA6' + eol
    # after the titles line when apply_titles.py has already added it, otherwise after the sidebar line
    for marker in ('      textures/font/titles/', '      textures/font/sidebar/, logo/'):
        start = readme.find(marker)
        if start >= 0:
            end = readme.index(eol, start) + len(eol)
            write(PACK_README, readme[:end] + line + readme[end:])
            done.append('pack README')
            break

print('voice wiring:', ', '.join(done) if done else 'nothing to do')
