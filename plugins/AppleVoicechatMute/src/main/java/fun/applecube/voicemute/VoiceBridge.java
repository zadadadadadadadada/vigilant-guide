package fun.applecube.voicemute;

import de.maxhenkel.voicechat.api.VoicechatConnection;
import de.maxhenkel.voicechat.api.VoicechatPlugin;
import de.maxhenkel.voicechat.api.VoicechatServerApi;
import de.maxhenkel.voicechat.api.events.EventRegistration;
import de.maxhenkel.voicechat.api.events.MicrophonePacketEvent;
import de.maxhenkel.voicechat.api.events.VoicechatServerStartedEvent;
import de.maxhenkel.voicechat.api.events.VoicechatServerStoppedEvent;
import java.util.UUID;
import org.jetbrains.annotations.Nullable;

/** The Simple Voice Chat side: drops microphone packets of muted players and answers "does this player have the mod". */
final class VoiceBridge implements VoicechatPlugin {
    private final AppleVoicechatMutePlugin plugin;
    private volatile VoicechatServerApi api;

    VoiceBridge(AppleVoicechatMutePlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public String getPluginId() {
        return "applevoicechatmute";
    }

    @Override
    public void registerEvents(EventRegistration registration) {
        registration.registerEvent(VoicechatServerStartedEvent.class, event -> this.api = event.getVoicechat());
        registration.registerEvent(VoicechatServerStoppedEvent.class, event -> this.api = null);
        registration.registerEvent(MicrophonePacketEvent.class, this::onMicrophone);
    }

    // Runs on the voice chat network thread for every audio packet: keep it to one map lookup.
    private void onMicrophone(MicrophonePacketEvent event) {
        VoicechatConnection sender = event.getSenderConnection();
        if (sender == null) {
            return;
        }
        UUID id = sender.getPlayer().getUuid();
        Mute mute = this.plugin.mutes().active(id);
        if (mute != null) {
            event.cancel();
            this.plugin.remind(id);
        }
    }

    /** False until the voice chat server has started (or when it failed to bind its UDP port). */
    boolean ready() {
        return this.api != null;
    }

    @Nullable
    VoicechatConnection connection(UUID id) {
        VoicechatServerApi current = this.api;
        return current == null ? null : current.getConnectionOf(id);
    }

    /** True when the player's client answered the voice chat handshake, i.e. the mod is installed and compatible. */
    boolean installed(UUID id) {
        VoicechatConnection connection = this.connection(id);
        return connection != null && connection.isInstalled();
    }
}
