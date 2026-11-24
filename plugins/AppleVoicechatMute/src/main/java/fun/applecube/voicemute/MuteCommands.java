package fun.applecube.voicemute;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import net.kyori.adventure.text.minimessage.tag.resolver.Placeholder;
import net.kyori.adventure.text.minimessage.tag.resolver.TagResolver;
import org.bukkit.OfflinePlayer;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabExecutor;
import org.bukkit.entity.Player;
import org.jetbrains.annotations.Nullable;

/** /vmute, /vunmute, /vmutelist and the /applevoicemute admin command. */
final class MuteCommands implements TabExecutor {
    private static final List<String> DURATIONS = List.of("10m", "30m", "1h", "6h", "1d", "7d", "perm");
    private static final int PAGE_SIZE = 10;

    private record Target(UUID id, String name, @Nullable Player online) {
    }

    private final AppleVoicechatMutePlugin plugin;

    MuteCommands(AppleVoicechatMutePlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        switch (command.getName().toLowerCase(Locale.ROOT)) {
            case "vmute" -> this.mute(sender, args);
            case "vunmute" -> this.unmute(sender, args);
            case "vmutelist" -> this.list(sender, args);
            default -> this.admin(sender, args);
        }
        return true;
    }

    private boolean denied(CommandSender sender, String permission) {
        if (sender.hasPermission(permission)) {
            return false;
        }
        this.plugin.messages().send(sender, "errors.no-permission");
        return true;
    }

    private void mute(CommandSender sender, String[] args) {
        if (this.denied(sender, "applevoicemute.mute")) {
            return;
        }
        if (args.length == 0) {
            this.plugin.messages().send(sender, "mute.usage");
            return;
        }
        Target target = this.resolve(args[0]);
        if (target == null) {
            this.plugin.messages().send(sender, "errors.player-not-found", Placeholder.unparsed("player", args[0]));
            return;
        }
        long duration = Durations.PERMANENT;
        int reasonFrom = 1;
        if (args.length > 1) {
            long parsed = Durations.parseMillis(args[1]);
            // anything that is not a duration is already the first word of the reason
            if (parsed != Durations.NOT_A_DURATION) {
                duration = parsed;
                reasonFrom = 2;
            }
        }
        String reason = String.join(" ", Arrays.copyOfRange(args, Math.min(reasonFrom, args.length), args.length)).trim();
        if (reason.isEmpty()) {
            reason = this.plugin.getConfig().getString("mute.default-reason", "Нарушение правил голосового чата");
        }
        long now = System.currentTimeMillis();
        Mute mute = new Mute(target.id(), target.name(), sender.getName(), reason, now, duration == Durations.PERMANENT ? 0L : now + duration);
        this.plugin.mutes().put(mute);

        TagResolver info = this.plugin.describe(mute);
        this.plugin.messages().send(sender, "mute.done", info);
        this.notifyStaff(sender, "mute.broadcast", info);
        if (target.online() != null && !target.online().equals(sender)) {
            this.plugin.messages().send(target.online(), "mute.target", info);
        }
    }

    private void unmute(CommandSender sender, String[] args) {
        if (this.denied(sender, "applevoicemute.unmute")) {
            return;
        }
        if (args.length == 0) {
            this.plugin.messages().send(sender, "unmute.usage");
            return;
        }
        // the stored name first: it also finds players the server has no cached profile for
        Mute mute = this.plugin.mutes().byName(args[0]);
        if (mute == null) {
            Target target = this.resolve(args[0]);
            mute = target == null ? null : this.plugin.mutes().active(target.id());
        }
        if (mute == null) {
            this.plugin.messages().send(sender, "unmute.not-muted", Placeholder.unparsed("player", args[0]));
            return;
        }
        this.plugin.mutes().remove(mute.id());
        TagResolver info = TagResolver.resolver(Placeholder.unparsed("player", mute.name()), Placeholder.unparsed("by", sender.getName()));
        this.plugin.messages().send(sender, "unmute.done", info);
        this.notifyStaff(sender, "unmute.broadcast", info);
        Player online = this.plugin.getServer().getPlayer(mute.id());
        if (online != null && !online.equals(sender)) {
            this.plugin.messages().send(online, "unmute.target", info);
        }
    }

    private void list(CommandSender sender, String[] args) {
        if (this.denied(sender, "applevoicemute.list")) {
            return;
        }
        List<Mute> mutes = this.plugin.mutes().all();
        if (mutes.isEmpty()) {
            this.plugin.messages().send(sender, "list.empty");
            return;
        }
        int pages = (mutes.size() + PAGE_SIZE - 1) / PAGE_SIZE;
        int page = 1;
        if (args.length > 0) {
            try {
                page = Integer.parseInt(args[0]);
            } catch (NumberFormatException ignored) {
                // not a number: show the first page
            }
        }
        page = Math.max(1, Math.min(page, pages));
        this.plugin.messages().send(
            sender,
            "list.header",
            Placeholder.unparsed("count", String.valueOf(mutes.size())),
            Placeholder.unparsed("page", String.valueOf(page)),
            Placeholder.unparsed("pages", String.valueOf(pages))
        );
        for (Mute mute : mutes.subList((page - 1) * PAGE_SIZE, Math.min(page * PAGE_SIZE, mutes.size()))) {
            this.plugin.messages().send(sender, "list.entry", this.plugin.describe(mute));
        }
    }

    private void admin(CommandSender sender, String[] args) {
        if (this.denied(sender, "applevoicemute.admin")) {
            return;
        }
        if (args.length == 1 && args[0].equalsIgnoreCase("reload")) {
            this.plugin.reload();
            this.plugin.messages().send(sender, "admin.reloaded");
        } else if (args.length == 2 && args[0].equalsIgnoreCase("resetreward")) {
            UUID id = this.plugin.rewards().byName(args[1]);
            boolean removed = id != null && this.plugin.rewards().forget(id);
            this.plugin.messages().send(sender, removed ? "admin.reward-reset" : "admin.reward-none", Placeholder.unparsed("player", args[1]));
        } else {
            this.plugin.messages().send(sender, "admin.usage");
        }
    }

    /** Tells the other moderators online, and the console when the command came from a player. */
    private void notifyStaff(CommandSender sender, String key, TagResolver info) {
        for (Player staff : this.plugin.getServer().getOnlinePlayers()) {
            if (!staff.equals(sender) && staff.hasPermission("applevoicemute.notify")) {
                this.plugin.messages().send(staff, key, info);
            }
        }
        if (sender instanceof Player) {
            this.plugin.messages().send(this.plugin.getServer().getConsoleSender(), key, info);
        }
    }

    @Nullable
    private Target resolve(String name) {
        Player online = this.plugin.getServer().getPlayerExact(name);
        if (online != null) {
            return new Target(online.getUniqueId(), online.getName(), online);
        }
        // never asks Mojang: only players this server has already seen
        OfflinePlayer known = this.plugin.getServer().getOfflinePlayerIfCached(name);
        if (known == null) {
            return null;
        }
        return new Target(known.getUniqueId(), known.getName() == null ? name : known.getName(), null);
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String label, String[] args) {
        String name = command.getName().toLowerCase(Locale.ROOT);
        List<String> options = new ArrayList<>();
        if (args.length == 1) {
            switch (name) {
                case "vmute" -> this.plugin.getServer().getOnlinePlayers().forEach(player -> options.add(player.getName()));
                case "vunmute" -> options.addAll(this.plugin.mutes().names());
                case "applevoicemute" -> options.addAll(List.of("reload", "resetreward"));
                default -> {
                }
            }
        } else if (args.length == 2 && name.equals("vmute")) {
            options.addAll(DURATIONS);
        }
        String typed = args.length == 0 ? "" : args[args.length - 1].toLowerCase(Locale.ROOT);
        options.removeIf(option -> !option.toLowerCase(Locale.ROOT).startsWith(typed));
        return options;
    }
}
