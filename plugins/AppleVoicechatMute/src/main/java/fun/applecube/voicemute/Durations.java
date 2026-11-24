package fun.applecube.voicemute;

import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Parsing and Russian formatting of mute durations. */
final class Durations {
    /** Returned by {@link #parseMillis} when the text is not a duration at all. */
    static final long NOT_A_DURATION = -1L;
    /** Returned by {@link #parseMillis} for "perm", "навсегда" and friends. */
    static final long PERMANENT = 0L;

    private static final Pattern PART = Pattern.compile("(\\d{1,9})([smhdwсмчдн])");
    private static final Set<String> PERMANENT_WORDS = Set.of("perm", "permanent", "forever", "навсегда", "перм");

    private Durations() {
    }

    /** Accepts "30s", "10m", "2h", "1d", "1w", their Russian letters (с м ч д н) and combinations like "1d12h". */
    static long parseMillis(String text) {
        String value = text.toLowerCase(Locale.ROOT);
        if (PERMANENT_WORDS.contains(value)) {
            return PERMANENT;
        }
        Matcher matcher = PART.matcher(value);
        long total = 0L;
        int end = 0;
        while (matcher.find()) {
            if (matcher.start() != end) {
                return NOT_A_DURATION;
            }
            total += Long.parseLong(matcher.group(1)) * unitMillis(matcher.group(2).charAt(0));
            end = matcher.end();
        }
        // "0m" is not a mute length, and neither is a bare number or a word
        return end == value.length() && total > 0L ? total : NOT_A_DURATION;
    }

    private static long unitMillis(char unit) {
        return switch (unit) {
            case 's', 'с' -> 1_000L;
            case 'm', 'м' -> 60_000L;
            case 'h', 'ч' -> 3_600_000L;
            case 'd', 'д' -> 86_400_000L;
            default -> 604_800_000L; // w, н
        };
    }

    /** "2 ч 10 мин" — the two largest non-zero units, seconds rounded up so a running mute never shows zero. */
    static String format(long millis) {
        long seconds = Math.max(1L, (millis + 999L) / 1000L);
        long days = seconds / 86_400L;
        long hours = seconds % 86_400L / 3_600L;
        long minutes = seconds % 3_600L / 60L;
        long secs = seconds % 60L;
        long[] amounts = {days, hours, minutes, secs};
        String[] units = {"д", "ч", "мин", "сек"};
        StringBuilder out = new StringBuilder();
        int shown = 0;
        for (int i = 0; i < amounts.length && shown < 2; i++) {
            if (amounts[i] > 0L) {
                if (!out.isEmpty()) {
                    out.append(' ');
                }
                out.append(amounts[i]).append(' ').append(units[i]);
                shown++;
            }
        }
        return out.toString();
    }
}
