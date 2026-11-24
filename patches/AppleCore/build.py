"""Build the patched AppleCore jar from the original 1.2.0 jar.

    python build.py <original AppleCore-1.2.0.jar> <compiled classes dir> <output jar>
    python build.py --messages <plugins/AppleCore/messages.yml>

The first form swaps in the recompiled teleport classes, adds the staff hint message and bumps the version
to 1.2.1; everything else in the jar is copied through untouched.
The second form adds the same message to a server's own messages.yml, so it can be edited there. The jar
carries it as a default, so this step is optional.
"""
import re
import sys
import zipfile
from pathlib import Path

PATCHED = re.compile(r'^fun/applecube/core/module/teleport/(RequestCommands|TeleportCommands)(\$[^/]*)?\.class$')


def replace_once(text, old, new, name):
    if text.count(old) != 1:
        raise SystemExit(f'{name}: expected exactly one match for {old!r}, found {text.count(old)}')
    return text.replace(old, new)


def plugin_yml(text):
    text = replace_once(text, "version: '1.2.0'", "version: '1.2.1'", 'plugin.yml')
    return replace_once(
        text,
        'description: Reach players who disabled teleports with /tp, /tphere and /tpa (essentials.tpo)',
        'description: Unused since 1.2.1 - /tptoggle always applies to /tp, /tphere and /tpa; staff override with /tpo and /tpohere',
        'plugin.yml',
    )


def messages_yml(text):
    disabled = '  disabled: "<prefix:error><text>Игрок <accent><player></accent> отключил телепортацию к себе."\n'
    staff = (
        '  # То же для /tp и /tphere, когда у отправителя есть право на обход: <command> - /tpo или /tpohere\n'
        '  disabled-staff: "<prefix:error><text>Игрок <accent><player></accent> отключил телепортацию к себе. '
        'Телепортироваться всё равно: <accent><command> <player></accent>"\n'
    )
    text = replace_once(text, disabled, disabled + staff, 'messages.yml')
    return replace_once(
        text,
        'usage: "<prefix:info><text>Использование: <accent>/tpo <игрок></accent>"',
        'usage: "<prefix:info><text>Использование: <accent>/tpo <игрок> [к кому]</accent>"',
        'messages.yml',
    )


def build_jar(original, classes, output):
    compiled = {p.relative_to(classes).as_posix(): p for p in classes.rglob('*.class')}
    if not compiled or not all(PATCHED.match(name) for name in compiled):
        raise SystemExit(f'unexpected compiled classes: {sorted(compiled)[:5]}')
    with zipfile.ZipFile(original) as src, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            if PATCHED.match(item.filename):
                continue  # replaced below, including nested classes that may no longer exist
            data = src.read(item.filename)
            if item.filename == 'plugin.yml':
                data = plugin_yml(data.decode('utf-8')).encode('utf-8')
            elif item.filename == 'messages.yml':
                data = messages_yml(data.decode('utf-8')).encode('utf-8')
            dst.writestr(item, data)
        for name in sorted(compiled):
            dst.write(compiled[name], name)
    print(f'{output}: {len(compiled)} classes replaced')


def patch_messages(path):
    with open(path, encoding='utf-8', newline='') as f:
        text = f.read()
    if 'disabled-staff:' in text:
        print(f'{path}: already has tpa.disabled-staff')
        return
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(messages_yml(text))
    print(f'{path}: tpa.disabled-staff added')


if __name__ == '__main__':
    if sys.argv[1] == '--messages':
        patch_messages(sys.argv[2])
    else:
        build_jar(sys.argv[1], Path(sys.argv[2]), sys.argv[3])
