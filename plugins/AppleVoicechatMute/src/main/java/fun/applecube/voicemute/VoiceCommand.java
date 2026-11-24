package fun.applecube.voicemute;

import de.maxhenkel.voicechat.api.VoicechatConnection;
import java.net.InetSocketAddress;
import java.util.List;
import net.kyori.adventure.text.event.ClickEvent;
import net.kyori.adventure.text.event.HoverEvent;
import net.kyori.adventure.text.minimessage.tag.Tag;
import net.kyori.adventure.text.minimessage.tag.resolver.Placeholder;
import net.kyori.adventure.text.minimessage.tag.resolver.TagResolver;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabExecutor;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.entity.Player;

/** /voice: says whether the voice chat mod was detected, explains how to install it and rewards players who have it. */
final class VoiceCommand implements TabExecutor {
    private final AppleVoicechatMutePlugin plugin;

    VoiceCommand(AppleVoicechatMutePlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        Messages messages = this.plugin.messages();
        if (!(sender instanceof Player player)) {
            messages.send(sender, "errors.players-only");
            return true;
        }
        String address = this.plugin.getConfig().getString("voice.download-url", "https://modrinth.com/plugin/simple-voice-chat");
        // <url> prints the address, <link>…</link> makes its content open it
        TagResolver url = TagResolver.resolver(
            Placeholder.unparsed("url", address),
            TagResolver.resolver("link", Tag.styling(ClickEvent.openUrl(address), HoverEvent.showText(messages.line("voice.link-hover"))))
        );
        messages.send(player, "voice.header");

        VoicechatConnection connection = this.plugin.voice().connection(player.getUniqueId());
        if (connection == null || !connection.isInstalled()) {
            // without a running voice server nobody can be detected, so do not tell the player the mod is missing
            messages.send(player, this.plugin.voice().ready() ? "voice.not-installed" : "voice.unavailable");
            messages.send(player, "voice.instructions", url);
            return true;
        }
        messages.send(player, connection.isConnected() ? "voice.installed" : "voice.installed-not-connected");
        messages.send(player, "voice.controls");
        this.reward(player);
        return true;
    }

    private void reward(Player player) {
        FileConfiguration config = this.plugin.getConfig();
        if (!config.getBoolean("voice.reward.enabled", true)) {
            return;
        }
        Messages messages = this.plugin.messages();
        RewardStore rewards = this.plugin.rewards();
        if (rewards.claimed(player.getUniqueId())) {
            messages.send(player, "voice.reward-already");
            return;
        }
        InetSocketAddress socket = player.getAddress();
        String address = socket == null || socket.getAddress() == null ? null : socket.getAddress().getHostAddress();
        if (address != null && config.getBoolean("voice.reward.one-per-address", true) && rewards.addressUsed(address)) {
            messages.send(player, "voice.reward-address");
            return;
        }
        // recorded before the commands run: a failing command must not turn into a reward that can be claimed forever
        rewards.mark(player.getUniqueId(), player.getName(), address);
        for (String line : config.getStringList("voice.reward.commands")) {
            this.plugin.getServer().dispatchCommand(this.plugin.getServer().getConsoleSender(), line.replace("%player%", player.getName()));
        }
        messages.send(player, "voice.reward-given");
        this.plugin.getLogger().info(player.getName() + " получил награду за установленный мод голосового чата.");
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String label, String[] args) {
        return List.of();
    }
}
