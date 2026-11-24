package fun.applecube.voicemute;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.plugin.Plugin;
import org.jetbrains.annotations.Nullable;

/**
 * Active voice mutes, kept in memory and mirrored to mutes.yml.
 * Lookups come from the voice chat network thread, so the map is concurrent and reads never touch the disk.
 */
final class MuteStore {
    private final Plugin plugin;
    private final Path file;
    private final Map<UUID, Mute> mutes = new ConcurrentHashMap<>();

    MuteStore(Plugin plugin) {
        this.plugin = plugin;
        this.file = plugin.getDataFolder().toPath().resolve("mutes.yml");
    }

    void load() {
        this.mutes.clear();
        File source = this.file.toFile();
        if (!source.isFile()) {
            return;
        }
        ConfigurationSection root = YamlConfiguration.loadConfiguration(source).getConfigurationSection("mutes");
        if (root == null) {
            return;
        }
        long now = System.currentTimeMillis();
        for (String key : root.getKeys(false)) {
            ConfigurationSection entry = root.getConfigurationSection(key);
            if (entry == null) {
                continue;
            }
            try {
                Mute mute = new Mute(
                    UUID.fromString(key),
                    entry.getString("name", key),
                    entry.getString("by", "?"),
                    entry.getString("reason", ""),
                    entry.getLong("created"),
                    entry.getLong("until")
                );
                if (!mute.expired(now)) {
                    this.mutes.put(mute.id(), mute);
                }
            } catch (IllegalArgumentException invalid) {
                this.plugin.getLogger().warning("mutes.yml: пропущена запись с неверным UUID: " + key);
            }
        }
    }

    /** The mute that currently applies to the player, or null. Safe to call from any thread. */
    @Nullable
    Mute active(UUID id) {
        Mute mute = this.mutes.get(id);
        return mute == null || mute.expired(System.currentTimeMillis()) ? null : mute;
    }

    @Nullable
    Mute byName(String name) {
        for (Mute mute : this.mutes.values()) {
            if (mute.name().equalsIgnoreCase(name)) {
                return mute;
            }
        }
        return null;
    }

    void put(Mute mute) {
        this.mutes.put(mute.id(), mute);
        this.save();
    }

    @Nullable
    Mute remove(UUID id) {
        Mute removed = this.mutes.remove(id);
        if (removed != null) {
            this.save();
        }
        return removed;
    }

    /** Drops mutes whose time has run out and returns them so their owners can be told. */
    List<Mute> removeExpired() {
        long now = System.currentTimeMillis();
        List<Mute> expired = new ArrayList<>();
        for (Mute mute : this.mutes.values()) {
            if (mute.expired(now) && this.mutes.remove(mute.id(), mute)) {
                expired.add(mute);
            }
        }
        if (!expired.isEmpty()) {
            this.save();
        }
        return expired;
    }

    List<Mute> all() {
        long now = System.currentTimeMillis();
        List<Mute> out = new ArrayList<>();
        for (Mute mute : this.mutes.values()) {
            if (!mute.expired(now)) {
                out.add(mute);
            }
        }
        out.sort(Comparator.comparing(Mute::name, String.CASE_INSENSITIVE_ORDER));
        return out;
    }

    List<String> names() {
        return this.all().stream().map(Mute::name).toList();
    }

    void save() {
        YamlConfiguration yaml = new YamlConfiguration();
        for (Mute mute : this.mutes.values()) {
            String path = "mutes." + mute.id();
            yaml.set(path + ".name", mute.name());
            yaml.set(path + ".by", mute.by());
            yaml.set(path + ".reason", mute.reason());
            yaml.set(path + ".created", mute.created());
            yaml.set(path + ".until", mute.until());
        }
        try {
            Files.createDirectories(this.file.getParent());
            // write next to the file and swap, so a crash mid-write cannot leave a truncated mutes.yml
            Path temp = this.file.resolveSibling("mutes.yml.tmp");
            Files.writeString(temp, yaml.saveToString(), StandardCharsets.UTF_8);
            Files.move(temp, this.file, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException failure) {
            this.plugin.getLogger().log(Level.SEVERE, "Не удалось сохранить mutes.yml", failure);
        }
    }
}
