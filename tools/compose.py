"""Original psybient construction kits.

Container lengths were chosen before any notes: every core part is 8 bars,
every arrangement is 32 bars, meter 4/4. Tempos are integer quarter-note BPM
values inside the project range 75-110. Offsets are 0. Nothing is random.
"""

from __future__ import annotations

from tools.midi_io import BAR_TICKS_4_4, PPQ, bpm_to_us, effective_bpm

GENERATOR_VERSION = "psybient-1.0.0"
PACK_ID = "psybient"
PACK_NAME = "Psybient"
BAR = BAR_TICKS_4_4

DRUM_MAP = {
    36: "Bass Drum 1",
    38: "Acoustic Snare",
    42: "Closed Hi-Hat",
    46: "Open Hi-Hat",
    49: "Crash Cymbal 1",
}
PERC_MAP = {
    54: "Tambourine",
    63: "Open Hi Conga",
    64: "Low Conga",
    70: "Maracas",
    75: "Claves",
    76: "Hi Wood Block",
}
ROLE_NAME = {
    "drums": "Drums",
    "percussion": "Percussion",
    "bass": "Bass",
    "motif": "Motif",
    "harmonic-field": "Harmonic Field",
    "atmosphere": "Atmosphere",
}
ROLE_ORDER = (
    "drums",
    "percussion",
    "bass",
    "motif",
    "harmonic-field",
    "atmosphere",
)


class Part:
    def __init__(self, kit, role, variation, channel, slug, mono, poly, lo, hi):
        self.kit = kit
        self.part_id = f"{kit['id']}.{role}.{variation}"
        self.role = role
        self.variation = variation
        self.core = True
        self.channel = channel
        self.file_slug = slug
        self.monophonic = mono
        self.max_poly = poly
        self.lo = lo
        self.hi = hi
        self.container_ticks = kit["part_bars"] * BAR
        self.notes = []

    def add(self, start, duration, pitch, velocity, departure=False):
        end = start + duration
        if start < 0 or duration <= 0 or end > self.container_ticks:
            raise ValueError(f"{self.part_id} boundary {start}+{duration}")
        if not self.lo <= pitch <= self.hi:
            raise ValueError(f"{self.part_id} pitch {pitch}")
        if self.role == "drums" and pitch not in DRUM_MAP:
            raise ValueError(f"{self.part_id} drum pitch {pitch} is outside the map")
        if self.role == "percussion" and pitch not in PERC_MAP:
            raise ValueError(f"{self.part_id} percussion pitch {pitch} is outside the map")
        if not 1 <= velocity <= 127:
            raise ValueError(f"{self.part_id} velocity {velocity}")
        active = 1
        for other in self.notes:
            o0 = other["performed_start"]
            o1 = o0 + other["duration"]
            if start < o1 and o0 < end:
                if other["pitch"] == pitch or self.monophonic:
                    raise ValueError(f"{self.part_id} overlap {pitch}@{start} with {other['pitch']}@{o0}")
                active += 1
        if active > self.max_poly:
            raise ValueError(f"{self.part_id} poly {active}")
        self.notes.append({
            "nominal_start": start,
            "offset": 0,
            "performed_start": start,
            "duration": duration,
            "pitch": pitch,
            "velocity": velocity,
            "channel": self.channel,
            "departure": departure,
        })

    def finish(self):
        ordered = sorted(self.notes, key=lambda note: (note["performed_start"], note["pitch"]))
        minimum = 2 if self.role == "atmosphere" else 4
        if len(ordered) < minimum:
            raise ValueError(f"{self.part_id} too few notes")
        for index, note in enumerate(ordered, 1):
            note["id"] = f"{self.part_id}.n{index:04d}"
        return {
            "id": self.part_id,
            "kit_id": self.kit["id"],
            "slug": self.kit["slug"],
            "role": self.role,
            "variation": self.variation,
            "core": True,
            "channel": self.channel,
            "file_slug": self.file_slug,
            "path": f"midi/{self.kit['slug']}/{self.file_slug}.mid",
            "monophonic": self.monophonic,
            "max_poly": self.max_poly,
            "container_ticks": self.container_ticks,
            "container_bars": self.kit["part_bars"],
            "bpm": self.kit["bpm"],
            "tempo_us": self.kit["tempo_us"],
            "notes": ordered,
        }


def add_events(part, events):
    for event in events:
        bar, tick, dur, pitch, vel = event[:5]
        departure = bool(event[5]) if len(event) > 5 else False
        part.add(bar * BAR + tick, dur, pitch, vel, departure=departure)


def make(kit, role, variation):
    spec = {
        "drums": (9, f"drums-{variation}", False, 4, 36, 51),
        "percussion": (9, f"percussion-{variation}", False, 4, 54, 76),
        "bass": (0, f"bass-{variation}", True, 1, 28, 55),
        "motif": (1, f"motif-{variation}", True, 1, 60, 84),
        "harmonic-field": (2, f"harmonic-{variation}", False, 4, 48, 76),
        "atmosphere": (3, f"atmosphere-{variation}", False, 3, 52, 88),
    }
    channel, slug, mono, poly, lo, hi = spec[role]
    return Part(kit, role, variation, channel, slug, mono, poly, lo, hi)


def kit_record(kit_id, slug, title, bpm, tonic, collection, pitch_classes, seed, identity, limitations, rhythm, phrases, arrangement_phrases, changes, change_bars, departures, spell, placements):
    tempo_us = bpm_to_us(bpm)
    return {
        "id": kit_id,
        "slug": slug,
        "title": title,
        "bpm": bpm,
        "tempo_us": tempo_us,
        "effective_bpm": effective_bpm(tempo_us),
        "part_bars": 8,
        "arrangement_bars": 32,
        "bars": 8,
        "meter": "4/4",
        "bar_ticks": BAR,
        "tonic": tonic,
        "tonal_reference": tonic,
        "collection_name": collection,
        "pitch_classes": pitch_classes,
        "departures": departures,
        "seed": seed,
        "identity": identity,
        "limitations": limitations,
        "harmonic_rhythm": rhythm,
        "phrases": phrases,
        "arrangement_phrases": arrangement_phrases,
        "changes": changes,
        "change_bars": change_bars,
        "spell": spell,
        "placements": placements,
        "stochastic_draws": 0,
    }


def kits():
    common_limit = (
        "Variation A and variation B are alternatives. Do not stack them. "
        "Do not mix parts from different kits: the tempos and collections differ. "
        "The 32-bar arrangement uses variation A only. "
        "Closed and open hats never overlap, and no hat-choke controller is written."
    )
    return [
        kit_record(
            "k01", "k01-low-water", "Low Water", 82, "D", "D dorian",
            [0, 2, 4, 5, 7, 9, 11], 8201,
            "Half-time pocket: kick on beat 1, snare on beat 3, hats only on the and of 2 and the last 16th. "
            "The bass leaps D to A, then settles. The motif rises D F A B and leaves bar 3 empty. "
            "Harmony holds Dm11, then G9, then a C major color, then a thinner Dm. "
            "Atmosphere is a few long high notes with silence in the last bar.",
            common_limit,
            "Dm11 for two bars, G9 for two, Cmaj7 for two, then a delayed Dm for two.",
            [
                {"name": "Open", "start_bar": 0, "bars": 2},
                {"name": "Answer", "start_bar": 2, "bars": 2},
                {"name": "Hold", "start_bar": 4, "bars": 2},
                {"name": "Cadence", "start_bar": 6, "bars": 2},
            ],
            [
                {"name": "Air", "start_bar": 0, "bars": 8},
                {"name": "All six", "start_bar": 8, "bars": 8},
                {"name": "Pulse", "start_bar": 16, "bars": 8},
                {"name": "Return", "start_bar": 24, "bars": 8},
            ],
            ["Dm11", "G9", "Cmaj7", "Dm"],
            [2, 2, 2, 2],
            [],
            ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"],
            {
                "drums": [8, 16, 24],
                "percussion": [8, 24],
                "bass": [8, 16, 24],
                "motif": [8, 24],
                "harmonic-field": [8, 16],
                "atmosphere": [0, 8, 24],
            },
        ),
        kit_record(
            "k02", "k02-glass-orbit", "Glass Orbit", 96, "A", "A aeolian",
            [0, 2, 4, 5, 7, 9, 11], 9602,
            "The kick pushes the and of 2 as well as beat 1. Claves sit on beats 2 and 4. "
            "Bass is a three-note pedal that changes root each bar and cadences on B. "
            "The motif descends in five short notes for four bars, then answers with fewer longer notes. "
            "Harmony staggers root, fifth, third, and seventh, one chord a bar. "
            "Atmosphere enters late in every other bar.",
            common_limit,
            "One chord per bar: Am, F, Cmaj7, Em7, Am, F, Dm, Am. Each tone enters a beat later than the last.",
            [
                {"name": "Descent", "start_bar": 0, "bars": 4},
                {"name": "Answer", "start_bar": 4, "bars": 4},
            ],
            [
                {"name": "Pads", "start_bar": 0, "bars": 8},
                {"name": "Bass entry", "start_bar": 8, "bars": 8},
                {"name": "Motif", "start_bar": 16, "bars": 8},
                {"name": "Full", "start_bar": 24, "bars": 8},
            ],
            ["Am", "F", "Cmaj7", "Em7", "Am", "F", "Dm", "Am"],
            [1, 1, 1, 1, 1, 1, 1, 1],
            [],
            ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"],
            {
                "drums": [8, 16, 24],
                "percussion": [16, 24],
                "bass": [8, 16, 24],
                "motif": [16, 24],
                "harmonic-field": [0, 8, 24],
                "atmosphere": [0, 16],
            },
        ),
        kit_record(
            "k03", "k03-dust-choir", "Dust Choir", 76, "F", "F mixolydian",
            [0, 2, 3, 5, 7, 9, 10], 7603,
            "Most of the bar is silent. Kick only on odd bars, hat on the even bars, snare on beat 4 of bars 4 and 8. "
            "Congas group attacks as 3+3+2 sixteenths twice in the bar. That grouping does not change the 4/4 meter. "
            "Bass is one long note per bar. The motif is eight calls spread over eight bars. "
            "Harmony is two held chords, F then Bb. Atmosphere is one note every four bars.",
            common_limit + " Variation B of the motif uses E4 once, flagged as a departure, then returns to F.",
            "Fadd9 for four bars, then Bb for four bars.",
            [
                {"name": "Call", "start_bar": 0, "bars": 4},
                {"name": "Second call", "start_bar": 4, "bars": 4},
            ],
            [
                {"name": "Air only", "start_bar": 0, "bars": 8},
                {"name": "Harmony", "start_bar": 8, "bars": 8},
                {"name": "Melody", "start_bar": 16, "bars": 8},
                {"name": "Drums", "start_bar": 24, "bars": 8},
            ],
            ["Fadd9", "Bb"],
            [4, 4],
            ["Motif B bar 6 uses E4 (64) for one short note, then steps back to F4."],
            ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"],
            {
                "drums": [24],
                "percussion": [24],
                "bass": [16, 24],
                "motif": [16, 24],
                "harmonic-field": [8, 16, 24],
                "atmosphere": [0, 8],
            },
        ),
        kit_record(
            "k04", "k04-night-ferry", "Night Ferry", 104, "E", "E minor pentatonic plus 9",
            [2, 4, 6, 7, 9, 11], 10404,
            "Faster tempo, still half-time in the kick: beats 1 and 3, with an 8th-note hat and an open hat on beat 4. "
            "Woodblocks answer just after each beat. Bass is four short syncopations, including the 9th F#. "
            "The motif is a downbeat arrival plus a pickup into the next bar. "
            "Harmony lands on beat 2 every two bars: Em9, G, D, Em. "
            "Atmosphere pulses a fifth once per bar.",
            common_limit + " Variation B of the bass uses C2 once, flagged as a departure, between E and D.",
            "Em9, G, Dsus, Em. Each chord starts on beat 2 and lasts two bars.",
            [
                {"name": "Arrival", "start_bar": 0, "bars": 4},
                {"name": "Pickup", "start_bar": 4, "bars": 4},
            ],
            [
                {"name": "Hats", "start_bar": 0, "bars": 8},
                {"name": "Bass and harmony", "start_bar": 8, "bars": 8},
                {"name": "All six", "start_bar": 16, "bars": 8},
                {"name": "Motif and air", "start_bar": 24, "bars": 8},
            ],
            ["Em9", "G6", "Dsus", "Em"],
            [2, 2, 2, 2],
            ["Bass B bar 7 uses C2 (36) for a short passing note, then moves to D2."],
            ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"],
            {
                "drums": [0, 8, 16],
                "percussion": [0, 16],
                "bass": [8, 16, 24],
                "motif": [16, 24],
                "harmonic-field": [8, 16],
                "atmosphere": [16, 24],
            },
        ),
    ]


def events_k01(variation):
    if variation == "a":
        drums = []
        for bar in range(7):
            drums += [
                (bar, 0, 300, 36, 96),
                (bar, 1440, 120, 42, 58),
                (bar, 1920, 240, 38, 84),
                (bar, 3360, 120, 42, 48),
            ]
        drums += [
            (7, 0, 300, 36, 104),
            (7, 1440, 120, 42, 64),
            (7, 1920, 240, 38, 96),
            (7, 2880, 200, 36, 88),
            (7, 3360, 400, 46, 70),
        ]
        perc = []
        for bar in range(8):
            perc += [
                (bar, 480, 140, 70, 52),
                (bar, 1440, 140, 70, 48),
                (bar, 2400, 140, 70, 52),
                (bar, 3360, 140, 70, 44),
            ]
            if bar in (3, 7):
                perc.append((bar, 0, 200, 75, 78))
        bass = [
            (0, 0, 1440, 38, 90), (0, 1920, 1440, 45, 84),
            (1, 0, 960, 41, 86), (1, 960, 960, 43, 88), (1, 1920, 1440, 45, 82),
            (2, 480, 1440, 38, 90), (2, 2400, 960, 36, 80),
            (3, 0, 3000, 38, 92),
            (4, 0, 1440, 38, 86), (4, 1920, 1200, 47, 84),
            (5, 0, 720, 45, 88), (5, 960, 960, 43, 86), (5, 2400, 960, 41, 80),
            (6, 0, 960, 47, 90), (6, 1440, 960, 45, 88), (6, 2880, 720, 43, 84),
            (7, 0, 3360, 38, 96),
        ]
        motif = [
            (0, 0, 1800, 62, 78), (0, 1920, 1440, 65, 82),
            (1, 480, 1440, 69, 86), (1, 2400, 1200, 71, 84),
            (3, 0, 960, 69, 80), (3, 1440, 960, 67, 78), (3, 2880, 720, 65, 76),
            (4, 0, 2880, 62, 74),
            (5, 960, 960, 64, 80), (5, 2400, 1200, 65, 82),
            (6, 0, 480, 69, 88), (6, 720, 480, 71, 90), (6, 1440, 1440, 69, 84),
            (7, 0, 3000, 62, 86),
        ]
        harmonic = []
        for pitch, vel in ((50, 70), (57, 66), (60, 64), (65, 68)):
            harmonic.append((0, 0, 7680, pitch, vel))
        for pitch, vel in ((55, 72), (59, 66), (62, 64), (69, 70)):
            harmonic.append((2, 0, 7680, pitch, vel))
        for pitch, vel in ((60, 68), (64, 64), (67, 66), (71, 62)):
            harmonic.append((4, 0, 6720, pitch, vel))
        for pitch, vel in ((50, 74), (57, 68), (65, 70)):
            harmonic.append((6, 480, 6240, pitch, vel))
        atmosphere = [
            (0, 960, 4800, 74, 56),
            (2, 1920, 4320, 81, 52),
            (4, 0, 2880, 77, 54),
            (5, 1440, 1680, 72, 50),
            (6, 0, 1920, 74, 58),
            (6, 2400, 960, 81, 48),
        ]
    else:
        drums = []
        for bar in range(8):
            drums += [
                (bar, 0, 280, 36, 90),
                (bar, 480, 100, 42, 50),
                (bar, 960, 220, 38, 80),
                (bar, 2400, 100, 42, 54),
                (bar, 2880, 260, 36, 86),
            ]
        drums.append((7, 1680, 140, 38, 70))
        perc = []
        for bar in range(8):
            perc += [
                (bar, 0, 200, 64, 74),
                (bar, 960, 200, 63, 70),
                (bar, 1920, 180, 64, 68),
                (bar, 2880, 220, 63, 72),
            ]
        perc.append((7, 3360, 160, 76, 80))
        bass = [
            (0, 0, 480, 45, 88), (0, 720, 480, 43, 84), (0, 1440, 720, 41, 86), (0, 2400, 960, 38, 90),
            (1, 0, 1920, 36, 82), (1, 2400, 1200, 38, 88),
            (2, 0, 960, 40, 86), (2, 1440, 480, 41, 84), (2, 2400, 960, 43, 82),
            (3, 480, 2400, 38, 90),
            (4, 0, 720, 47, 88), (4, 960, 720, 45, 86), (4, 1920, 1440, 43, 84),
            (5, 0, 1440, 41, 86), (5, 1920, 1440, 40, 82),
            (6, 240, 960, 45, 88), (6, 1440, 1920, 38, 92),
            (7, 0, 480, 36, 80), (7, 960, 1920, 38, 94),
        ]
        motif = [
            (0, 0, 480, 71, 90), (0, 480, 480, 69, 88), (0, 960, 480, 67, 86),
            (0, 1440, 480, 65, 84), (0, 1920, 720, 64, 82), (0, 2880, 720, 62, 80),
            (2, 0, 1440, 65, 84), (2, 1920, 1440, 69, 88),
            (3, 480, 1680, 72, 86), (3, 2880, 720, 71, 82),
            (4, 0, 960, 69, 84), (4, 1440, 1920, 65, 80),
            (5, 0, 480, 67, 86), (5, 720, 1200, 69, 88), (5, 2400, 960, 71, 84),
            (7, 960, 1920, 62, 82),
        ]
        harmonic = [
            (0, 0, 2880, 50, 72), (0, 480, 2400, 65, 66), (0, 960, 1920, 57, 64),
            (1, 0, 1440, 60, 70), (1, 480, 1440, 64, 66), (1, 1440, 1440, 67, 64), (1, 2400, 960, 71, 68),
            (2, 0, 3360, 55, 72), (2, 960, 1920, 62, 66), (2, 1920, 1440, 59, 64),
            (3, 0, 1920, 53, 70), (3, 480, 1440, 57, 66), (3, 1440, 1920, 60, 68),
            (4, 0, 960, 57, 70), (4, 960, 960, 60, 68), (4, 1920, 960, 64, 66), (4, 2880, 720, 67, 64),
            (5, 0, 1920, 50, 72), (5, 480, 1440, 57, 66), (5, 960, 1920, 65, 68),
            (6, 0, 1440, 59, 74), (6, 480, 1440, 62, 68), (6, 960, 960, 65, 66), (6, 1440, 1440, 69, 70),
            (7, 0, 2880, 50, 76), (7, 960, 1920, 57, 68),
        ]
        atmosphere = [
            (0, 0, 1200, 60, 48), (0, 1920, 1200, 67, 46),
            (1, 480, 1440, 62, 50), (1, 2400, 960, 69, 44),
            (2, 0, 1200, 60, 48), (2, 1920, 1200, 67, 46),
            (3, 480, 1440, 62, 50), (3, 2400, 960, 69, 44),
            (4, 0, 1440, 65, 52), (4, 1920, 1440, 69, 48),
            (5, 0, 960, 64, 50), (5, 1440, 1920, 60, 46),
            (6, 480, 1200, 67, 48), (6, 2160, 1200, 62, 50),
            (7, 960, 1920, 65, 54),
        ]
    return {
        "drums": drums,
        "percussion": perc,
        "bass": bass,
        "motif": motif,
        "harmonic-field": harmonic,
        "atmosphere": atmosphere,
    }


def events_k02(variation):
    if variation == "a":
        drums = []
        for bar in range(8):
            drums += [
                (bar, 0, 240, 36, 100),
                (bar, 480, 100, 42, 54),
                (bar, 1440, 200, 36, 90),
                (bar, 1920, 220, 38, 86),
                (bar, 2400, 100, 42, 50),
            ]
            if bar == 7:
                drums += [(bar, 0, 600, 49, 78), (bar, 3360, 360, 46, 64)]
            else:
                drums.append((bar, 3360, 100, 42, 46))
        perc = []
        for bar in range(8):
            perc += [(bar, 960, 150, 75, 72), (bar, 2880, 150, 75, 68)]
            if bar in (3, 7):
                perc.append((bar, 0, 200, 54, 70))
        roots = [45, 48, 52, 50, 53, 52, 55, 45]
        bass = []
        for bar, pitch in enumerate(roots):
            bass += [(bar, 0, 1200, pitch, 90), (bar, 1440, 900, pitch, 84)]
            if bar == 7:
                bass.append((bar, 2880, 600, 47, 88))
            else:
                bass.append((bar, 2880, 700, pitch, 82))
        motif = []
        descents = [
            (76, 74, 72, 71, 69, 67),
            (74, 72, 71, 69, 67, 65),
            (72, 71, 69, 67, 65, 64),
            (71, 69, 67, 65, 64, 62),
        ]
        slots = ((0, 200), (240, 400), (720, 600), (1440, 800), (2400, 1200))
        for bar, row in enumerate(descents):
            for (tick, dur), pitch in zip(slots, row):
                motif.append((bar, tick, dur, pitch, 80))
        rises = [
            (69, 71, 72, 74),
            (67, 69, 71, 72),
            (65, 67, 69, 71),
        ]
        late = ((480, 400), (960, 400), (1440, 900), (2880, 720))
        for index, row in enumerate(rises):
            bar = 4 + index
            for (tick, dur), pitch in zip(late, row):
                motif.append((bar, tick, dur, pitch, 84))
        motif += [(7, 480, 720, 69, 82), (7, 1440, 720, 67, 80), (7, 2400, 1200, 64, 78)]
        chords = [
            (57, 64, 60, 67),
            (53, 60, 57, 64),
            (48, 55, 52, 59),
            (52, 59, 55, 62),
            (57, 64, 60, 67),
            (53, 60, 57, 64),
            (50, 57, 53, 60),
            (57, 64, 60, 67),
        ]
        harmonic = []
        for bar, chord in enumerate(chords):
            for pitch, tick, dur, vel in zip(chord, (0, 480, 960, 1440), (2880, 2400, 1920, 1440), (70, 66, 64, 62)):
                harmonic.append((bar, tick, dur, pitch, vel))
        atmosphere = [
            (0, 1920, 2880, 76, 50),
            (1, 0, 1440, 67, 46),
            (2, 1920, 2880, 72, 52),
            (3, 0, 1440, 65, 44),
            (4, 1920, 2880, 69, 50),
            (5, 0, 1440, 62, 46),
            (6, 1920, 2880, 71, 54),
        ]
    else:
        drums = []
        for bar in range(8):
            drums += [
                (bar, 240, 80, 42, 48),
                (bar, 720, 80, 42, 46),
                (bar, 1200, 80, 42, 50),
                (bar, 1680, 80, 42, 46),
                (bar, 1920, 240, 38, 84),
                (bar, 2880, 240, 36, 92),
            ]
            if bar == 7:
                drums.append((bar, 0, 200, 36, 100))
        perc = []
        for bar in range(8):
            perc += [
                (bar, 0, 160, 76, 70),
                (bar, 720, 160, 76, 66),
                (bar, 1440, 160, 76, 68),
                (bar, 1920, 240, 64, 74),
            ]
            if bar == 7:
                perc.append((bar, 2880, 400, 63, 78))
        pairs = [(45, 48), (52, 50), (48, 45), (47, 45), (50, 48), (52, 53), (55, 52), (48, 45)]
        bass = []
        for bar, (first, second) in enumerate(pairs):
            bass += [(bar, 0, 1680, first, 88), (bar, 1920, 1440, second, 84)]
        motif = []
        rows = [
            (64, 69, 67),
            (65, 71, 69),
            (67, 72, 71),
            (69, 74, 72),
            (71, 76, 74),
            (69, 74, 72),
            (67, 72, 69),
            (64, 69, 65),
        ]
        for bar, (low, leap, fall) in enumerate(rows):
            motif += [
                (bar, 960, 240, low, 78),
                (bar, 1440, 960, leap, 86),
                (bar, 2880, 480, fall, 80),
            ]
        harmonic = []
        blocks = [
            (0, 7200, (53, 57, 60, 64)),
            (2, 7200, (52, 55, 59, 62)),
            (4, 6000, (57, 60, 64, 59)),
        ]
        for bar, dur, chord in blocks:
            for pitch, vel in zip(chord, (72, 66, 64, 60)):
                harmonic.append((bar, 0, dur, pitch, vel))
        for pitch, vel in zip((55, 60, 62, 57), (74, 68, 66, 64)):
            harmonic.append((6, 960, 6000, pitch, vel))
        atmosphere = []
        for bar in range(4):
            atmosphere += [(bar, 0, 720, 74, 52), (bar, 1440, 1440, 69, 48)]
        for bar in range(4, 7):
            atmosphere += [(bar, 0, 720, 76, 54), (bar, 1440, 1440, 71, 50)]
        atmosphere.append((7, 0, 2400, 76, 56))
    return {
        "drums": drums,
        "percussion": perc,
        "bass": bass,
        "motif": motif,
        "harmonic-field": harmonic,
        "atmosphere": atmosphere,
    }


def events_k03(variation):
    if variation == "a":
        drums = []
        for bar in (0, 2, 4, 6):
            drums.append((bar, 0, 360, 36, 80))
        for bar in (1, 3, 5, 7):
            drums.append((bar, 960, 160, 42, 48))
        for bar in (3, 7):
            drums.append((bar, 2880, 240, 38, 76))
        drums.append((7, 1920, 200, 36, 84))
        perc = []
        for bar in range(8):
            for tick in (0, 720, 1440):
                perc.append((bar, tick, 180, 64, 70))
            for tick in (1920, 2640, 3360):
                perc.append((bar, tick, 180, 63, 66))
        pitches = [41, 36, 46, 41, 43, 38, 36, 41]
        bass = []
        for bar, pitch in enumerate(pitches):
            if bar % 2 == 0:
                bass.append((bar, 0, 2700, pitch, 88))
            else:
                bass.append((bar, 960, 1920, pitch, 82))
        motif = [
            (0, 1920, 1440, 69, 78),
            (2, 0, 960, 67, 76),
            (3, 2880, 720, 65, 74),
            (4, 960, 1440, 70, 80),
            (5, 480, 960, 72, 82),
            (6, 2400, 960, 69, 78),
            (7, 0, 720, 67, 76),
            (7, 1920, 1440, 65, 80),
        ]
        harmonic = []
        for pitch, vel in ((53, 68), (57, 64), (60, 62), (67, 66)):
            harmonic.append((0, 0, 14400, pitch, vel))
        for pitch, vel in ((58, 70), (62, 66), (65, 64), (60, 62)):
            harmonic.append((4, 0, 14000, pitch, vel))
        atmosphere = [
            (0, 0, 14000, 77, 44),
            (4, 0, 12000, 72, 42),
        ]
    else:
        drums = []
        for bar in range(8):
            drums.append((bar, 1440, 240, 36, 86))
            if bar % 2 == 0:
                drums.append((bar, 0, 140, 42, 50))
        drums += [(7, 2880, 400, 46, 68), (7, 3360, 200, 38, 80)]
        perc = []
        for bar in range(0, 8, 2):
            perc += [(bar, 960, 160, 75, 74), (bar, 3600, 160, 54, 60)]
        for bar in range(4, 8):
            perc.append((bar, 1920, 180, 76, 72))
        pairs = [(41, 48), (46, 43), (45, 41), (43, 36), (38, 41), (39, 36), (46, 43), (41, 41)]
        bass = []
        for bar, (first, second) in enumerate(pairs):
            bass += [(bar, 480, 900, first, 86), (bar, 1920, 1200, second, 82)]
        motif = [
            (0, 0, 720, 65, 80), (0, 960, 720, 67, 82), (0, 1920, 960, 69, 84),
            (1, 0, 1440, 70, 82), (1, 1920, 1440, 72, 86),
            (2, 480, 960, 74, 84), (2, 1920, 1440, 70, 80),
            (3, 0, 2880, 65, 78),
            (4, 960, 480, 69, 82), (4, 1920, 960, 67, 80),
            (5, 0, 720, 65, 84), (5, 1440, 480, 64, 90, True), (5, 2160, 1200, 65, 82),
            (6, 0, 1920, 70, 80),
            (7, 480, 2400, 65, 78),
        ]
        harmonic = [
            (0, 0, 7000, 53, 70), (0, 960, 6000, 60, 64), (0, 1920, 4800, 57, 62),
            (2, 0, 6000, 58, 72), (2, 480, 5000, 62, 66), (2, 1440, 4000, 65, 64),
            (4, 0, 5000, 60, 70), (4, 480, 4500, 63, 66), (4, 960, 4000, 67, 64), (4, 1440, 3600, 58, 62),
            (6, 480, 6000, 53, 74), (6, 960, 5000, 57, 66), (6, 1920, 4000, 60, 64),
        ]
        atmosphere = [
            (0, 960, 2400, 65, 48),
            (2, 0, 1920, 70, 50),
            (3, 1440, 1920, 72, 46),
            (4, 480, 2880, 69, 52),
            (6, 0, 1440, 67, 48),
            (6, 1920, 1440, 65, 50),
            (7, 960, 1920, 74, 54),
        ]
    return {
        "drums": drums,
        "percussion": perc,
        "bass": bass,
        "motif": motif,
        "harmonic-field": harmonic,
        "atmosphere": atmosphere,
    }


def events_k04(variation):
    if variation == "a":
        drums = []
        hat_ticks = (0, 480, 960, 1440, 1920, 2400, 3360)
        for bar in range(8):
            drums += [
                (bar, 0, 200, 36, 102),
                (bar, 1920, 200, 36, 96),
                (bar, 1920, 220, 38, 86),
                (bar, 2880, 300, 46, 64),
            ]
            for tick in hat_ticks:
                drums.append((bar, tick, 80, 42, 52))
        drums.append((7, 0, 480, 49, 76))
        perc = []
        for bar in range(8):
            for tick in (240, 1200, 2160, 3120):
                perc.append((bar, tick, 120, 76, 68))
            if bar % 2 == 1:
                perc.append((bar, 0, 140, 75, 74))
        rows = [
            [40, 47, 40, 43],
            [45, 40, 47, 40],
            [38, 40, 43, 47],
            [40, 45, 40, 52],
            [47, 43, 40, 38],
            [40, 42, 45, 47],
            [43, 47, 52, 47],
            [40, 40, 38, 40],
        ]
        bass = []
        for bar, row in enumerate(rows):
            for tick, pitch in zip((240, 1200, 2160, 3120), row):
                dur = 360 if tick == 3120 else 400
                bass.append((bar, tick, dur, pitch, 90))
        motif_pairs = [
            (64, 67), (69, 71), (74, 71), (69, 66),
            (67, 64), (62, 64), (66, 69), (71, 64),
        ]
        motif = []
        for bar, (arrival, pickup) in enumerate(motif_pairs):
            motif += [(bar, 0, 1200, arrival, 84), (bar, 3120, 200, pickup, 78)]
        harmonic = []
        chords = [
            (52, 55, 59, 66),
            (55, 59, 62, 64),
            (50, 57, 64, 66),
            (52, 59, 67),
        ]
        for index, chord in enumerate(chords):
            for pitch, vel in zip(chord, (70, 66, 64, 62)):
                harmonic.append((index * 2, 960, 6000, pitch, vel))
        atmosphere = []
        for bar in range(6):
            if bar % 2 == 0:
                atmosphere += [(bar, 0, 720, 71, 52), (bar, 1920, 720, 64, 48)]
            else:
                atmosphere += [(bar, 0, 720, 66, 50), (bar, 1920, 720, 62, 46)]
        atmosphere += [
            (6, 0, 720, 69, 54), (6, 1920, 720, 64, 48),
            (7, 0, 720, 64, 56), (7, 1920, 1200, 71, 50),
        ]
    else:
        drums = []
        for bar in range(8):
            drums += [
                (bar, 0, 400, 36, 94),
                (bar, 1440, 100, 42, 50),
                (bar, 2880, 240, 38, 82),
            ]
            if bar in (3, 7):
                drums += [(bar, 1920, 200, 36, 88), (bar, 3360, 360, 46, 66)]
        perc = []
        for bar in range(8):
            for tick in (0, 960, 1920, 2880):
                perc.append((bar, tick, 160, 54, 64))
            if bar >= 4:
                perc += [(bar, 480, 200, 64, 72), (bar, 1440, 240, 63, 70)]
        bass = [
            (0, 0, 1440, 40, 90), (0, 1920, 1440, 47, 86),
            (1, 0, 1440, 45, 88), (1, 1920, 1440, 43, 84),
            (2, 0, 1440, 38, 86), (2, 1920, 1440, 40, 88),
            (3, 0, 1440, 42, 86), (3, 1920, 1440, 45, 84),
            (4, 0, 1440, 47, 90), (4, 1920, 1440, 52, 86),
            (5, 0, 1440, 43, 84), (5, 1920, 1440, 42, 82),
            (6, 0, 960, 40, 88), (6, 1440, 480, 36, 92, True), (6, 2160, 1200, 38, 86),
            (7, 0, 2880, 40, 94),
        ]
        scale = [64, 66, 67, 69, 71, 74, 76, 74, 71, 69, 67, 66, 64, 62, 64, 67]
        motif = []
        index = 0
        for bar in range(8):
            for tick in (0, 960):
                motif.append((bar, tick, 700, scale[index], 82))
                index += 1
        harmonic = []
        chords = [
            (52, 59, 64),
            (55, 62, 67),
            (50, 57, 66),
            (52, 55, 71),
            (57, 64, 59),
            (50, 55, 62),
            (59, 66, 62),
            (52, 59, 67),
        ]
        for bar, chord in enumerate(chords):
            for pitch, vel in zip(chord, (72, 66, 64)):
                harmonic.append((bar, 0, 3000, pitch, vel))
        atmosphere = [
            (0, 0, 7000, 76, 48),
            (2, 480, 6000, 71, 50),
            (4, 0, 5000, 69, 46),
            (5, 1920, 3000, 66, 48),
            (6, 0, 2880, 64, 52),
            (7, 960, 1920, 62, 50),
        ]
    return {
        "drums": drums,
        "percussion": perc,
        "bass": bass,
        "motif": motif,
        "harmonic-field": harmonic,
        "atmosphere": atmosphere,
    }


BUILDERS = {
    "k01": events_k01,
    "k02": events_k02,
    "k03": events_k03,
    "k04": events_k04,
}


def _sig(notes):
    return tuple((note["performed_start"], note["pitch"], note["duration"]) for note in notes)


def _attacks(notes):
    return tuple(note["performed_start"] for note in notes)


def _is_transpose(left, right):
    if len(left) != len(right):
        return False
    paired = list(zip(left, right))
    if any(a["performed_start"] != b["performed_start"] or a["duration"] != b["duration"] for a, b in paired):
        return False
    deltas = {b["pitch"] - a["pitch"] for a, b in paired}
    return len(deltas) == 1


def assert_collections(kit_rows, parts):
    allowed = {kit["id"]: set(kit["pitch_classes"]) for kit in kit_rows}
    for part in parts:
        if part["role"] in ("drums", "percussion"):
            continue
        pool = allowed[part["kit_id"]]
        for note in part["notes"]:
            inside = (note["pitch"] % 12) in pool
            if note["departure"] and inside:
                raise ValueError(f"{part['id']} departure {note['pitch']} is inside the collection")
            if not note["departure"] and not inside:
                raise ValueError(f"{part['id']} note {note['pitch']} left the collection")


def assert_identities(parts):
    by_role = {}
    for part in parts:
        by_role.setdefault(part["role"], {}).setdefault(part["kit_id"], {})[part["variation"]] = part
    report = []
    for role, kits_map in by_role.items():
        seen = {}
        for kit_id, versions in kits_map.items():
            left = versions["a"]["notes"]
            right = versions["b"]["notes"]
            if _sig(left) == _sig(right):
                raise ValueError(f"{kit_id} {role} variations match")
            if _is_transpose(left, right):
                raise ValueError(f"{kit_id} {role} variation B is only a transpose of A")
            attacks = _attacks(left)
            if attacks in seen:
                raise ValueError(f"{role} variation A attack tuple repeats {seen[attacks]} and {kit_id}")
            seen[attacks] = kit_id
            report.append({
                "kit_id": kit_id,
                "role": role,
                "a_notes": len(left),
                "b_notes": len(right),
                "a_attacks": len(set(attacks)),
            })
    return {
        "rows": report,
        "method": (
            "For each core role, variation A and variation B differ in pitch and rhythm, "
            "not only in velocity, and B is not a uniform transpose of A. "
            "Variation A attack-time tuples are unique across the four kits."
        ),
    }


def _shift_notes(source, bar_offset):
    shift = bar_offset * BAR
    shifted = []
    for note in source["notes"]:
        start = note["performed_start"] + shift
        shifted.append({
            "nominal_start": start,
            "offset": 0,
            "performed_start": start,
            "duration": note["duration"],
            "pitch": note["pitch"],
            "velocity": note["velocity"],
            "channel": note["channel"],
            "departure": note["departure"],
        })
    return shifted


def build_arrangement(kit, by_id):
    container = kit["arrangement_bars"] * BAR
    tracks = [{"name": "Conductor", "source_part": None, "channel": None, "placements": [], "notes": []}]
    for role in ROLE_ORDER:
        source = by_id[f"{kit['id']}.{role}.a"]
        notes = []
        for offset in kit["placements"][role]:
            notes.extend(_shift_notes(source, offset))
        notes.sort(key=lambda note: (note["performed_start"], note["pitch"]))
        for note in notes:
            end = note["performed_start"] + note["duration"]
            if end > container:
                raise ValueError(f"{kit['id']} {role} arrangement boundary")
        tracks.append({
            "name": ROLE_NAME[role],
            "source_part": source["id"],
            "channel": source["channel"],
            "placements": list(kit["placements"][role]),
            "notes": notes,
        })
    path = "midi/arrangement.mid" if kit["id"] == "k01" else f"midi/{kit['slug']}/arrangement.mid"
    return {
        "id": f"{kit['id']}-arrangement-a",
        "kit_id": kit["id"],
        "path": path,
        "format": 1,
        "container_ticks": container,
        "container_bars": 32,
        "bpm": kit["bpm"],
        "tempo_us": kit["tempo_us"],
        "meter": "4/4",
        "description": (
            f"{kit['title']} variation A arranged over 32 bars. "
            "Each musical track is one or more copies of the 8-bar part, placed at the listed bar offsets."
        ),
        "tracks": tracks,
    }


def compose():
    kit_rows = kits()
    if len(kit_rows) != 4:
        raise ValueError("expected four kits")
    parts = []
    for kit in kit_rows:
        builder = BUILDERS[kit["id"]]
        for variation in ("a", "b"):
            events = builder(variation)
            if set(events) != set(ROLE_ORDER):
                raise ValueError(kit["id"])
            for role in ROLE_ORDER:
                part = make(kit, role, variation)
                add_events(part, events[role])
                parts.append(part.finish())
    assert_collections(kit_rows, parts)
    identity = assert_identities(parts)
    by_id = {part["id"]: part for part in parts}
    arrangements = [build_arrangement(kit, by_id) for kit in kit_rows]
    preview = arrangements[0]
    if preview["kit_id"] != "k01" or 8 not in preview["tracks"][1]["placements"]:
        raise ValueError("preview arrangement is not Low Water")
    core = [part for part in parts if part["core"]]
    refs = [part for part in parts if not part["core"]]
    if len(core) != 48 or refs:
        raise ValueError((len(core), len(refs)))
    catalog_kits = []
    for kit in kit_rows:
        catalog_kits.append({key: kit[key] for key in (
            "id", "slug", "title", "bpm", "tempo_us", "effective_bpm", "part_bars", "arrangement_bars",
            "bars", "meter", "bar_ticks", "tonic", "tonal_reference", "collection_name", "pitch_classes",
            "departures", "seed", "identity", "limitations", "harmonic_rhythm", "phrases",
            "arrangement_phrases", "changes", "change_bars", "spell", "placements", "stochastic_draws",
        )})
    catalog = {
        "pack_id": PACK_ID,
        "pack_name": PACK_NAME,
        "catalog_version": GENERATOR_VERSION,
        "generator_version": GENERATOR_VERSION,
        "ppq": PPQ,
        "c4": 60,
        "meter": {"numerator": 4, "denominator": 4, "bar_ticks": BAR},
        "container_plan": "Core parts are 8 bars. Arrangements are 32 bars. Lengths were fixed before the notes.",
        "creative_direction": (
            "Patient downtempo development, evolving pitch fields, layered detail, and spacious interplay. "
            "The BPM range is a project choice, not a claim that these files are authentic genre productions."
        ),
        "note_policy": "Note-only MIDI. No program changes, controllers, pitch bend, or samples are encoded.",
        "microtiming": "offset is 0; performed_start = nominal_start",
        "stochastic_draws": 0,
        "seed_meaning": "Seeds identify kits. Nothing is random.",
        "core_part_count": 48,
        "reference_part_count": 0,
        "reference_note": "There is no reference-only part. All six roles are core. The arrangements reuse those files.",
        "drum_map": {str(pitch): name for pitch, name in DRUM_MAP.items()},
        "percussion_map": {str(pitch): name for pitch, name in PERC_MAP.items()},
        "drum_channel": 10,
        "range_statement": (
            "Drums and percussion use channel 10 and the maps in this catalog. "
            "Bass is monophonic, MIDI 28 to 55. Motif is monophonic, MIDI 60 to 84. "
            "Harmonic field is MIDI 48 to 76, at most four notes. "
            "Atmosphere is MIDI 52 to 88, at most three notes, written as notes. C4 is 60."
        ),
        "kits": catalog_kits,
        "parts": [{
            "id": part["id"],
            "kit_id": part["kit_id"],
            "role": part["role"],
            "variation": part["variation"],
            "core": part["core"],
            "channel": part["channel"],
            "path": part["path"],
            "notes": len(part["notes"]),
            "container_bars": part["container_bars"],
            "bpm": part["bpm"],
            "monophonic": part["monophonic"],
        } for part in parts],
        "arrangements": [{
            "id": item["id"],
            "kit_id": item["kit_id"],
            "path": item["path"],
            "bpm": item["bpm"],
            "container_bars": item["container_bars"],
            "description": item["description"],
            "placements": {track["source_part"]: track["placements"] for track in item["tracks"] if track["source_part"]},
        } for item in arrangements],
        "arrangement": {
            "id": preview["id"],
            "path": preview["path"],
            "kit_id": "k01",
            "container_bars": 32,
            "description": preview["description"],
        },
        "preview": {
            "kit_id": "k01",
            "title": "Low Water",
            "bpm": 82,
            "musical_bars": "9-16",
            "start_bar_index": 8,
            "end_bar_index": 16,
            "start_tick": 8 * BAR,
            "end_tick": 16 * BAR,
            "variation": "a",
            "arrangement_path": preview["path"],
            "statement": "Bars 9-16 of the Low Water arrangement. Eight bars at 82 BPM.",
        },
        "preview_part_ids": [f"k01.{role}.a" for role in ROLE_ORDER],
        "stack_warning": (
            "Use either the combined arrangement or the separate parts. "
            "Do not stack the part files on top of the combined file."
        ),
    }
    score = {
        "pack_id": PACK_ID,
        "generator_version": GENERATOR_VERSION,
        "ppq": PPQ,
        "parts": parts,
        "arrangements": arrangements,
        "arrangement": preview,
        "identity_check": identity,
    }
    return {"catalog": catalog, "score": score}
