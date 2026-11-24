"""Let the drill enchantment ("Бур") break every block type.

    python apply_drill.py <server root>

Edits plugins/AppleItems/config.yml in place, keeping comments and layout:
    custom-enchantments.drill.only-effective-blocks: true -> false   (a pickaxe no longer skips dirt, wood, glass...)
    custom-enchantments.drill.max-hardness:          10   -> 100     (obsidian is 50; nothing breakable is harder than 55)
protect-containers and the blacklist are left as they are, so chests, spawners and bedrock stay safe.
In game afterwards: /ai reload.
"""
import os
import sys

path = os.path.join(sys.argv[1], 'plugins/AppleItems/config.yml')
with open(path, encoding='utf-8', newline='') as f:
    text = f.read()

changed = []
for old, new in (('    only-effective-blocks: true', '    only-effective-blocks: false'), ('    max-hardness: 10\n', '    max-hardness: 100\n')):
    if new in text:
        continue
    if text.count(old) != 1:
        raise SystemExit('%s: expected exactly one %r, found %d' % (path, old.strip(), text.count(old)))
    text = text.replace(old, new)
    changed.append(new.strip())

if changed:
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)
print('drill:', ', '.join(changed) if changed else 'already set')
