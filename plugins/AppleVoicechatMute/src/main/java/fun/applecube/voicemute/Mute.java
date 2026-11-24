package fun.applecube.voicemute;

import java.util.UUID;

/**
 * One voice mute.
 *
 * @param until epoch millis when the mute ends, 0 for a permanent mute
 */
record Mute(UUID id, String name, String by, String reason, long created, long until) {
    boolean permanent() {
        return this.until <= 0L;
    }

    boolean expired(long now) {
        return !this.permanent() && now >= this.until;
    }

    long left(long now) {
        return this.permanent() ? 0L : Math.max(0L, this.until - now);
    }
}
