# APPLECUBE server changes

Source for the server-side work of 2026-11-24: one new plugin, a patch for AppleCore and the scripts that
redraw resource-pack textures and edit plugin configs. The server itself (jars, configs, pack art) is not in
this repository; the scripts take a copy of its `plugins/` folder as input.

| Path | What it is |
| --- | --- |
| `plugins/AppleVoicechatMute` | New Paper plugin: voice chat mutes for Simple Voice Chat and the `/voice` command |
| `patches/AppleCore` | Rebuilds `AppleCore-1.2.1.jar` from `AppleCore-1.2.0.jar` with the `/tptoggle` fix |
| `tools` | Title frames, menu backgrounds, the muted icon, and the config edits that wire them in |

## AppleVoicechatMute

```
cd plugins/AppleVoicechatMute && mvn package      # JDK 21; jar lands in target/
```

Needs Simple Voice Chat (`voicechat`) on the server; PlaceholderAPI is optional.

- `/vmute <player> [time] [reason]` — time is `30s`, `10m`, `2h`, `1d`, `1w`, a combination such as `1d12h`, or
  `perm`; without a time the mute is permanent. Works for offline players the server has seen.
  `/vunmute <player>`, `/vmutelist [page]`. One permission for moderators: `applevoicemute.staff`.
- A muted player's microphone packets are dropped on the server (`MicrophonePacketEvent`), so nobody hears
  them nearby or in a group. They get a reminder above the hotbar when they try to talk.
- `/voice` tells the player whether the mod was detected (`VoicechatConnection#isInstalled`), prints install
  steps, and runs the reward commands once per account and per network address (default
  `bcases give %player% donate 1`). Only a salted hash of the address is stored.
- `/applevoicemute reload | resetreward <player>` for admins.
- Placeholders: `%applevoicemute_muted%`, `_icon%`, `_left%`, `_reason%`, `_installed%`.

All texts are MiniMessage in `config.yml`.

## AppleCore 1.2.1

`/tptoggle` looked broken on admin accounts: the sender's `applecore.tptoggle.bypass` (default op, also granted
by `*` and by `essentials.tpo`) skipped the check silently for `/tpa`, `/tpahere`, `/tp` and `/tphere`. The patch
makes those commands always respect the toggle. Staff reach such a player deliberately with `/tpo`, `/tpohere`
or the new `/tpo <who> <target>`; the console is never blocked.

```
patches/AppleCore/build.sh AppleCore-1.2.0.jar vineflower-1.11.1.jar AppleCore-1.2.1.jar
```

The script decompiles the jar, applies `patch.py` to the two teleport command classes, recompiles only those
and puts them back; every other entry of the jar is copied unchanged.

## tools

Python 3 with Pillow and PyYAML. `<server root>` is a folder that holds a copy of the server's `plugins/`;
`<textures>` is `plugins/ItemsAdder/contents/bordo_menu/resourcepack/assets/bordo_menu/textures` inside it.

| Script | Does |
| --- | --- |
| `make_titles.py <textures> <out>` | Draws the ten animated unique titles from the pack's bold font: 16 frames per title, one sheet each, plus `preview.png` / `preview.gif` |
| `apply_titles.py <out> <server root>` | Copies the sheets into the pack, registers one character per frame (U+EC00 and up), rewrites the `title_<id>` TAB animations, the names in the unique titles menu and in the BCases title case |
| `build_menu_backgrounds.py <textures> <out>` | Removes the decorative category tile from six menus and redraws five flat ones (arrows, enchants, masks, personal, shop) in the pack's panel style |
| `apply_menus.py <out> <server root>` | Copies the backgrounds and moves the arrow shop items onto the new slot wells |
| `make_voice_mute_icon.py <textures> <png>` | The "muted by a moderator" tab icon |
| `apply_voice.py <png> <server root>` | Registers the icon (U+EBA6), adds the TAB condition that shows it for muted players, whitelists `/voice` in CommandWhitelist |
| `apply_drill.py <server root>` | Drill enchantment breaks every block type (`only-effective-blocks: false`, `max-hardness: 100`) |

Every `apply_*` script checks what is already there and can be run again. After copying the results to the
server: `/iazip`, then a restart (or `/tab reload`, `/dm reload`, `/bcases reload`, `/ai reload`, `/cw reload`).

## How it was checked

A local Paper 1.21.11 server with the real plugin jars and configs, driven by scripted clients:

- `/tptoggle`: reproduced with a `*` sender on 1.2.0 (requests and `/tp` went through), then on 1.2.1 every
  request and teleport is refused, `/tpo`, `/tpohere` and the console still work, and it turns back off.
- Drill: with the old config a 3x3 dig broke stone and cobblestone only; with the new one it also breaks dirt,
  planks, obsidian, glass and wool, from any starting block, and leaves the chest and bedrock.
- `/voice`: no mod → instructions; mod handshake → detected and one donate key in BCases; second call and an
  alt on the same address get nothing; a client with another protocol version is not counted.
- Mutes: mute, list, placeholders, expiry message, unmute, and that they survive a restart. The packet drop
  itself was confirmed by reading voicechat 2.6.25 (`Server#onMicPacket` skips a cancelled event), not by audio.
- TAB: after the menu's own commands the tab list and name tag cycle through all 16 frame characters; `/vmute`
  swaps the voice icon to the muted one and `/vunmute` swaps it back.
- Textures were compared pixel by pixel with the originals: changes stay inside the panel (or the tile cell).

Not checked in a real game client: how the pack renders. ItemsAdder was not available locally.
