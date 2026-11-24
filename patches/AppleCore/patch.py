"""Apply the /tptoggle fix to the decompiled AppleCore 1.2.0 teleport classes.

    python patch.py <dir with RequestCommands.java and TeleportCommands.java>

The two files are the Vineflower 1.11.1 output for
fun/applecube/core/module/teleport/{RequestCommands,TeleportCommands}.class from AppleCore-1.2.0.jar.
Every replacement must match exactly once, so the script fails loudly on any other jar or decompiler version.

What changes:
  - /tpa, /tpahere, /tpaall: a player who ran /tptoggle can no longer be reached by anyone. Before, the sender's
    applecore.tptoggle.bypass (default op, also granted by "*" and by essentials.tpo) skipped the check silently.
  - /tp, /tphere: same, except for the console. A sender who is allowed to use the override commands gets a hint.
  - /tpo also accepts "<who> <target>", the override twin of "/tp <who> <target>".
"""
import pathlib
import sys

root = pathlib.Path(sys.argv[1])


def edit(path, replacements):
    text = path.read_text(encoding='utf-8')
    for old, new in replacements:
        if text.count(old) != 1:
            raise SystemExit(f'{path.name}: expected exactly one match, found {text.count(old)}:\n{old}')
        text = text.replace(old, new)
    path.write_text(text, encoding='utf-8')


edit(root / 'RequestCommands.java', [(
    '''      } else if (!plugin.users().user(to).teleportRequests() && !ctx.hasPermission("applecore.tptoggle.bypass")) {
         throw new CommandException("tpa.disabled", Ph.of("player", to.getName()));''',
    '''      } else if (!plugin.users().user(to).teleportRequests()) {
         // /tptoggle is absolute for requests: no permission, wildcard or op status gets a request through
         throw new CommandException("tpa.disabled", Ph.of("player", to.getName()));''',
)])

edit(root / 'TeleportCommands.java', [
    (
        '''   static void checkToggle(AppleCorePlugin plugin, CommandContext ctx, Player target) throws CommandException {
      if (!ctx.isSelf(target) && !plugin.users().user(target).teleportRequests() && !ctx.hasPermission("applecore.tptoggle.bypass")) {
         throw new CommandException("tpa.disabled", Ph.of("player", target.getName()));
      }
   }''',
        '''   // /tp and /tphere always respect /tptoggle, whatever the sender's permissions: staff reach such players
   // on purpose with /tpo and /tpohere. The console is never blocked, so automation keeps working.
   static void checkToggle(AppleCorePlugin plugin, CommandContext ctx, Player target, String override) throws CommandException {
      if (ctx.isPlayer() && !ctx.isSelf(target) && !plugin.users().user(target).teleportRequests()) {
         if (ctx.hasPermission("applecore." + override)) {
            throw new CommandException("tpa.disabled-staff", Ph.of("player", target.getName()), Ph.of("command", "/" + override));
         } else {
            throw new CommandException("tpa.disabled", Ph.of("player", target.getName()));
         }
      }
   }''',
    ),
    (
        'TeleportCommands.checkToggle(this.plugin, ctx, target);\n                     this.plugin.teleports().teleport(self,',
        'TeleportCommands.checkToggle(this.plugin, ctx, target, "tpo");\n                     this.plugin.teleports().teleport(self,',
    ),
    (
        'TeleportCommands.checkToggle(this.plugin, ctx, who);',
        'TeleportCommands.checkToggle(this.plugin, ctx, who, "tpo");',
    ),
    (
        'TeleportCommands.checkToggle(this.plugin, ctx, target);\n                     this.plugin\n',
        'TeleportCommands.checkToggle(this.plugin, ctx, target, "tpo");\n                     this.plugin\n',
    ),
    (
        '               TeleportCommands.checkToggle(this.plugin, ctx, target);\n            }',
        '               TeleportCommands.checkToggle(this.plugin, ctx, target, "tpohere");\n            }',
    ),
    (
        '''      @Override
      public void execute(CommandContext ctx) throws CommandException {
         Player self = ctx.player();
         Player target = ctx.onlinePlayer(0);
         this.plugin.teleports().teleport(self, target.getLocation(), 0, () -> ctx.reply("commands.tp.to-player", Ph.of("player", target.getName())));
      }

      @Override
      public List<String> suggest(CommandContext ctx) {
         return ctx.size() == 1 ? this.players(ctx) : List.of();
      }
   }
}''',
        '''      @Override
      public void execute(CommandContext ctx) throws CommandException {
         if (ctx.has(1)) {
            // /tpo <who> <target>: the override twin of /tp <who> <target>
            ctx.require("applecore.tp.others");
            Player who = ctx.onlinePlayer(0);
            Player target = ctx.onlinePlayer(1);
            this.plugin
               .teleports()
               .teleport(
                  who,
                  target.getLocation(),
                  0,
                  () -> ctx.reply("commands.tp.other-to-player", Ph.of("player", who.getName()), Ph.of("target", target.getName()))
               );
         } else {
            Player self = ctx.player();
            Player target = ctx.onlinePlayer(0);
            this.plugin.teleports().teleport(self, target.getLocation(), 0, () -> ctx.reply("commands.tp.to-player", Ph.of("player", target.getName())));
         }
      }

      @Override
      public List<String> suggest(CommandContext ctx) {
         return ctx.size() <= 2 ? this.players(ctx) : List.of();
      }
   }
}''',
    ),
])
print('patched')
