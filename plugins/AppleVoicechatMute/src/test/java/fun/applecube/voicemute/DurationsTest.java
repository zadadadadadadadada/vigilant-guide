package fun.applecube.voicemute;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class DurationsTest {
    @Test
    void parsesSingleUnitsInLatinAndCyrillic() {
        assertEquals(30_000L, Durations.parseMillis("30s"));
        assertEquals(600_000L, Durations.parseMillis("10m"));
        assertEquals(7_200_000L, Durations.parseMillis("2h"));
        assertEquals(86_400_000L, Durations.parseMillis("1d"));
        assertEquals(604_800_000L, Durations.parseMillis("1w"));
        assertEquals(600_000L, Durations.parseMillis("10м"));
        assertEquals(7_200_000L, Durations.parseMillis("2Ч"));
    }

    @Test
    void parsesCombinations() {
        assertEquals(86_400_000L + 12 * 3_600_000L, Durations.parseMillis("1d12h"));
    }

    @Test
    void permanentWords() {
        assertEquals(Durations.PERMANENT, Durations.parseMillis("perm"));
        assertEquals(Durations.PERMANENT, Durations.parseMillis("Навсегда"));
    }

    @Test
    void reasonWordsAreNotDurations() {
        // the first word of a reason must not be swallowed as a time
        assertEquals(Durations.NOT_A_DURATION, Durations.parseMillis("мат"));
        assertEquals(Durations.NOT_A_DURATION, Durations.parseMillis("10"));
        assertEquals(Durations.NOT_A_DURATION, Durations.parseMillis("10x"));
        assertEquals(Durations.NOT_A_DURATION, Durations.parseMillis("m10"));
        assertEquals(Durations.NOT_A_DURATION, Durations.parseMillis("0m"));
        assertEquals(Durations.NOT_A_DURATION, Durations.parseMillis(""));
    }

    @Test
    void formatsTwoLargestUnits() {
        assertEquals("2 ч 10 мин", Durations.format(7_800_000L));
        assertEquals("3 д 4 ч", Durations.format(3 * 86_400_000L + 4 * 3_600_000L + 59_000L));
        assertEquals("1 д", Durations.format(86_400_000L));
        assertEquals("45 сек", Durations.format(44_001L));
        assertEquals("1 сек", Durations.format(1L));
    }
}
