package fun.applecube.voicemute;

import me.clip.placeholderapi.expansion.PlaceholderExpansion;
import org.bukkit.OfflinePlayer;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

/**
 * PlaceholderAPI: %applevoicemute_muted%, %applevoicemute_icon%, %applevoicemute_left%, %applevoicemute_reason%
 * and %applevoicemute_installed%. Loaded only when PlaceholderAPI is present.
 */
final class MutePlaceholders extends PlaceholderExpansion {
    private final AppleVoicechatMutePlugin plugin;

    MutePlaceholders(AppleVoicechatMutePlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public @NotNull String getIdentifier() {
        return "applevoicemute";
    }

    @Override
    public @NotNull String getAuthor() {
        return "APPLECUBE";
    }

    @Override
    public @NotNull String getVersion() {
        return this.plugin.getPluginMeta().getVersion();
    }

    @Override
    public boolean persist() {
        return true;
    }

    @Override
    public @Nullable String onRequest(OfflinePlayer player, @NotNull String params) {
        if (player == null) {
            return "";
        }
        Mute mute = this.plugin.mutes().active(player.getUniqueId());
        return switch (params) {
            case "muted" -> String.valueOf(mute != null);
            case "icon" -> this.plugin.getConfig().getString(mute != null ? "placeholders.muted-icon" : "placeholders.unmuted-icon", "");
            case "left" -> mute == null
                ? ""
                : mute.permanent() ? this.plugin.getConfig().getString("mute.permanent-text", "навсегда") : Durations.format(mute.left(System.currentTimeMillis()));
            case "reason" -> mute == null ? "" : mute.reason();
            case "installed" -> String.valueOf(this.plugin.voice().installed(player.getUniqueId()));
            default -> null;
        };
    }
}
