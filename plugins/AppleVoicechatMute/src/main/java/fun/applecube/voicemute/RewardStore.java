package fun.applecube.voicemute;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;
import java.util.logging.Level;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.plugin.Plugin;
import org.jetbrains.annotations.Nullable;

/** Who has already received the /voice reward. Main thread only. */
final class RewardStore {
    private record Claim(String name, long time, String address) {
    }

    private final Plugin plugin;
    private final Path file;
    private final Map<UUID, Claim> claims = new HashMap<>();
    private String salt = "";

    RewardStore(Plugin plugin) {
        this.plugin = plugin;
        this.file = plugin.getDataFolder().toPath().resolve("rewards.yml");
    }

    void load() {
        this.claims.clear();
        File source = this.file.toFile();
        YamlConfiguration yaml = source.isFile() ? YamlConfiguration.loadConfiguration(source) : new YamlConfiguration();
        this.salt = yaml.getString("salt", "");
        if (this.salt.isEmpty()) {
            byte[] random = new byte[16];
            new SecureRandom().nextBytes(random);
            this.salt = HexFormat.of().formatHex(random);
        }
        ConfigurationSection players = yaml.getConfigurationSection("claimed");
        if (players == null) {
            return;
        }
        for (String key : players.getKeys(false)) {
            try {
                this.claims.put(
                    UUID.fromString(key),
                    new Claim(players.getString(key + ".name", key), players.getLong(key + ".time"), players.getString(key + ".address", ""))
                );
            } catch (IllegalArgumentException invalid) {
                this.plugin.getLogger().warning("rewards.yml: пропущена запись с неверным UUID: " + key);
            }
        }
    }

    boolean claimed(UUID id) {
        return this.claims.containsKey(id);
    }

    /** True when some other account has already been rewarded from this network address. */
    boolean addressUsed(String address) {
        String hash = this.hash(address);
        for (Claim claim : this.claims.values()) {
            if (claim.address().equals(hash)) {
                return true;
            }
        }
        return false;
    }

    void mark(UUID id, String name, @Nullable String address) {
        this.claims.put(id, new Claim(name, System.currentTimeMillis(), address == null ? "" : this.hash(address)));
        this.save();
    }

    /** Forgets the claim (and its address), so the player can be rewarded again. */
    boolean forget(UUID id) {
        boolean removed = this.claims.remove(id) != null;
        if (removed) {
            this.save();
        }
        return removed;
    }

    @Nullable
    UUID byName(String name) {
        for (Map.Entry<UUID, Claim> entry : this.claims.entrySet()) {
            if (entry.getValue().name().equalsIgnoreCase(name)) {
                return entry.getKey();
            }
        }
        return null;
    }

    // Only a salted hash of the address is stored: enough to spot a second account, useless for anything else.
    private String hash(String address) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest((this.salt + '|' + address).getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(bytes, 0, 16);
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException(impossible);
        }
    }

    private void save() {
        YamlConfiguration yaml = new YamlConfiguration();
        yaml.set("salt", this.salt);
        for (Map.Entry<UUID, Claim> entry : this.claims.entrySet()) {
            String path = "claimed." + entry.getKey();
            yaml.set(path + ".name", entry.getValue().name());
            yaml.set(path + ".time", entry.getValue().time());
            yaml.set(path + ".address", entry.getValue().address());
        }
        try {
            Files.createDirectories(this.file.getParent());
            // write next to the file and swap, so a crash mid-write cannot leave a truncated rewards.yml
            Path temp = this.file.resolveSibling("rewards.yml.tmp");
            Files.writeString(temp, yaml.saveToString(), StandardCharsets.UTF_8);
            Files.move(temp, this.file, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException failure) {
            this.plugin.getLogger().log(Level.SEVERE, "Не удалось сохранить rewards.yml", failure);
        }
    }
}
