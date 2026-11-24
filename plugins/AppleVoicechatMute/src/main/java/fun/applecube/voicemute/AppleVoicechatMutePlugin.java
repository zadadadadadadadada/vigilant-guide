package fun.applecube.voicemute;

import de.maxhenkel.voicechat.api.BukkitVoicechatService;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import net.kyori.adventure.text.minimessage.tag.resolver.Placeholder;
import net.kyori.adventure.text.minimessage.tag.resolver.TagResolver;
import org.bukkit.command.PluginCommand;
import org.bukkit.command.TabExecutor;
import org.bukkit.entity.Player;
import org.bukkit.plugin.IllegalPluginAccessException;
import org.bukkit.plugin.java.JavaPlugin;

public final class AppleVoicechatMutePlugin extends JavaPlugin {
    private final Map<UUID, Long> reminded = new ConcurrentHashMap<>();
    private Messages messages;
    private MuteStore mutes;
    private RewardStore rewards;
    private VoiceBridge voice;
    private volatile long remindMillis;

    @Override
    public void onEnable() {
        this.saveDefaultConfig();
        this.messages = new Messages(this);
        this.mutes = new MuteStore(this);
        this.rewards = new RewardStore(this);
        this.reload();

        BukkitVoicechatService service = this.getServer().getServicesManager().load(BukkitVoicechatService.class);
        if (service == null) {
            this.getLogger().severe("Simple Voice Chat не загружен - плагин отключён.");
            this.getServer().getPluginManager().disablePlugin(this);
            return;
        }
        this.voice = new VoiceBridge(this);
        service.registerPlugin(this.voice);

        MuteCommands muteCommands = new MuteCommands(this);
        this.bind("vmute", muteCommands);
        this.bind("vunmute", muteCommands);
        this.bind("vmutelist", muteCommands);
        this.bind("applevoicemute", muteCommands);
        this.bind("voice", new VoiceCommand(this));

        if (this.getServer().getPluginManager().isPluginEnabled("PlaceholderAPI")) {
            new MutePlaceholders(this).register();
        }
        this.getServer().getScheduler().runTaskTimer(this, this::expire, 20L, 20L);
    }

    private void bind(String name, TabExecutor executor) {
        PluginCommand command = this.getCommand(name);
        if (command != null) {
            command.setExecutor(executor);
            command.setTabCompleter(executor);
        }
    }

    /** Re-reads config.yml, mutes.yml and rewards.yml. */
    void reload() {
        this.reloadConfig();
        this.messages.reload();
        this.mutes.load();
        this.rewards.load();
        this.remindMillis = Math.max(0L, this.getConfig().getLong("mute.remind-seconds", 5L)) * 1000L;
    }

    Messages messages() {
        return this.messages;
    }

    MuteStore mutes() {
        return this.mutes;
    }

    RewardStore rewards() {
        return this.rewards;
    }

    VoiceBridge voice() {
        return this.voice;
    }

    /** The &lt;player&gt;, &lt;by&gt;, &lt;reason&gt; and &lt;time&gt; placeholders of a mute; time is what is left of it. */
    TagResolver describe(Mute mute) {
        String time = mute.permanent()
            ? this.getConfig().getString("mute.permanent-text", "навсегда")
            : Durations.format(mute.left(System.currentTimeMillis()));
        return TagResolver.resolver(
            Placeholder.unparsed("player", mute.name()),
            Placeholder.unparsed("by", mute.by()),
            Placeholder.unparsed("reason", mute.reason()),
            Placeholder.unparsed("time", time)
        );
    }

    /**
     * Tells a muted player why nobody hears them. Called from the voice chat thread for every dropped packet,
     * so it only hands a throttled task to the main thread.
     */
    void remind(UUID id) {
        long interval = this.remindMillis;
        if (interval <= 0L) {
            return;
        }
        long now = System.currentTimeMillis();
        Long last = this.reminded.get(id);
        if (last != null && now - last < interval) {
            return;
        }
        this.reminded.put(id, now);
        try {
            this.getServer().getScheduler().runTask(this, () -> {
                Player player = this.getServer().getPlayer(id);
                Mute mute = this.mutes.active(id);
                if (player != null && mute != null) {
                    player.sendActionBar(this.messages.line("mute.reminder", this.describe(mute)));
                }
            });
        } catch (IllegalPluginAccessException disabled) {
            // the plugin is shutting down while voice packets are still arriving
        }
    }

    private void expire() {
        for (Mute mute : this.mutes.removeExpired()) {
            this.reminded.remove(mute.id());
            Player player = this.getServer().getPlayer(mute.id());
            if (player != null) {
                this.messages.send(player, "mute.expired");
            }
        }
    }
}
