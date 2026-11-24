package fun.applecube.voicemute;

import java.util.ArrayList;
import java.util.List;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.TextColor;
import net.kyori.adventure.text.minimessage.MiniMessage;
import net.kyori.adventure.text.minimessage.tag.Tag;
import net.kyori.adventure.text.minimessage.tag.resolver.Placeholder;
import net.kyori.adventure.text.minimessage.tag.resolver.TagResolver;
import org.bukkit.command.CommandSender;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.plugin.Plugin;

/**
 * MiniMessage texts from config.yml. Besides the standard tags every message may use the theme colours
 * (style.colors: &lt;text&gt;, &lt;accent&gt;, ...) and the prefixes (style.prefix: &lt;ok&gt;, &lt;error&gt;, ...).
 */
final class Messages {
    private final Plugin plugin;
    private final MiniMessage mini = MiniMessage.miniMessage();
    private TagResolver theme = TagResolver.empty();

    Messages(Plugin plugin) {
        this.plugin = plugin;
        this.reload();
    }

    void reload() {
        FileConfiguration config = this.plugin.getConfig();
        TagResolver.Builder builder = TagResolver.builder();
        ConfigurationSection colors = config.getConfigurationSection("style.colors");
        if (colors != null) {
            for (String name : colors.getKeys(false)) {
                TextColor color = TextColor.fromHexString(colors.getString(name, ""));
                if (color == null) {
                    this.plugin.getLogger().warning("style.colors." + name + ": нужен цвет вида \"#RRGGBB\"");
                } else {
                    builder.resolver(TagResolver.resolver(name, Tag.styling(color)));
                }
            }
        }
        ConfigurationSection prefixes = config.getConfigurationSection("style.prefix");
        if (prefixes != null) {
            for (String name : prefixes.getKeys(false)) {
                builder.resolver(Placeholder.parsed(name, prefixes.getString(name, "")));
            }
        }
        this.theme = builder.build();
    }

    /** The message as lines: a YAML list gives one line per entry, an empty string gives nothing. */
    List<Component> lines(String key, TagResolver... placeholders) {
        FileConfiguration config = this.plugin.getConfig();
        String path = "messages." + key;
        List<String> raw;
        if (config.isList(path)) {
            raw = config.getStringList(path);
        } else {
            // a missing key shows its own name, so a typo in the config is visible in game
            String single = config.getString(path, path);
            raw = single.isEmpty() ? List.of() : List.of(single);
        }
        TagResolver resolver = TagResolver.resolver(this.theme, TagResolver.resolver(placeholders));
        List<Component> out = new ArrayList<>(raw.size());
        for (String line : raw) {
            out.add(this.mini.deserialize(line, resolver));
        }
        return out;
    }

    Component line(String key, TagResolver... placeholders) {
        List<Component> lines = this.lines(key, placeholders);
        return lines.isEmpty() ? Component.empty() : lines.get(0);
    }

    void send(CommandSender to, String key, TagResolver... placeholders) {
        for (Component line : this.lines(key, placeholders)) {
            to.sendMessage(line);
        }
    }
}
