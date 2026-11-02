"""Repo-owned preview synthesizer.

This is a simple synth, not a General MIDI soundfont and not a mix engine.
It renders an excerpt of the canonical arrangement notes. Sample positions
are absolute from the excerpt start:

    sample = floor(seconds * sample_rate + 0.5)

seconds = tick / 960 * encoded_microseconds_per_quarter / 1_000_000.
Intervals are not accumulated. Sample peak is not a loudness measurement.
"""

from __future__ import annotations

import math
import wave
from array import array
from pathlib import Path

SR = 44100
RENDERER_VERSION = "simple-synth-1.0.0"


def tick_to_sample(tick: int, tempo_us: int, sample_rate: int = SR) -> int:
    seconds = (tick / 960) * (tempo_us / 1_000_000)
    return int(math.floor(seconds * sample_rate + 0.5))


def container_seconds(container_ticks: int, tempo_us: int) -> float:
    return (container_ticks / 960) * (tempo_us / 1_000_000)


def _midi_freq(pitch: int) -> float:
    return 440.0 * (2.0 ** ((pitch - 69) / 12.0))


def _env(index: int, start: int, end: int, attack: float, release: float) -> float:
    t = (index - start) / SR
    remain = (end - index) / SR
    level = 1.0
    if attack > 0 and t < attack:
        level *= t / attack
    if release > 0 and remain < release:
        level *= max(0.0, remain / release)
    return level


def render_preview(parts: list[dict], tempo_us: int, container_ticks: int, wav_path: Path) -> dict:
    total = tick_to_sample(container_ticks, tempo_us)
    mix = array("i", [0]) * total

    def add_tone(note: dict, wave_kind: str, amp_scale: float, attack: float, release: float, decay: float) -> None:
        start = tick_to_sample(note["performed_start"], tempo_us)
        end = tick_to_sample(note["performed_start"] + note["duration"], tempo_us)
        end = min(total, max(end, start + 1))
        freq = _midi_freq(note["pitch"])
        inc = freq / SR
        phase = 0.0
        amp = (note["velocity"] / 127.0) * amp_scale
        for index in range(start, end):
            phase += inc
            if phase >= 1.0:
                phase -= 1.0
            if wave_kind == "sine":
                sample = math.sin(2.0 * math.pi * phase)
            else:
                sample = 1.0 - 4.0 * abs(phase - 0.5)
            t = (index - start) / SR
            level = _env(index, start, end, attack, release)
            if decay > 0:
                level *= math.exp(-decay * t)
            mix[index] += int(sample * level * amp)

    def add_noise(note: dict, amp_scale: float, color: float, decay: float) -> None:
        start = tick_to_sample(note["performed_start"], tempo_us)
        end = tick_to_sample(note["performed_start"] + note["duration"], tempo_us)
        end = min(total, max(end, start + 1))
        state = 1 + note["pitch"] * 131 + note["performed_start"]
        amp = (note["velocity"] / 127.0) * amp_scale
        low = 0.0
        for index in range(start, end):
            state = (1103515245 * state + 12345) & 0x7FFFFFFF
            noise = (state / 0x7FFFFFFF) * 2.0 - 1.0
            low += color * (noise - low)
            t = (index - start) / SR
            level = math.exp(-decay * t) * _env(index, start, end, 0.001, 0.01)
            mix[index] += int(low * level * amp)

    def add_drums(note: dict) -> None:
        pitch = note["pitch"]
        if pitch == 36:
            start = tick_to_sample(note["performed_start"], tempo_us)
            end = tick_to_sample(note["performed_start"] + note["duration"], tempo_us)
            end = min(total, max(end, start + 1))
            phase = 0.0
            amp = (note["velocity"] / 127.0) * 14000.0
            for index in range(start, end):
                t = (index - start) / SR
                freq = 48.0 + 90.0 * math.exp(-t * 28.0)
                phase += freq / SR
                mix[index] += int(math.sin(2.0 * math.pi * phase) * math.exp(-t * 18.0) * amp)
        elif pitch == 38:
            add_noise(note, 9000.0, 0.35, 28.0)
        elif pitch == 42:
            add_noise(note, 3500.0, 0.8, 60.0)
        elif pitch == 46:
            add_noise(note, 4200.0, 0.72, 12.0)
        elif pitch == 49:
            add_noise(note, 5000.0, 0.55, 6.0)
        else:
            add_noise(note, 3000.0, 0.6, 20.0)

    def add_percussion(note: dict) -> None:
        pitch = note["pitch"]
        if pitch == 75:
            add_tone(note, "sine", 5000.0, 0.001, 0.02, 24.0)
        elif pitch == 76:
            add_tone(note, "triangle", 4200.0, 0.001, 0.02, 18.0)
        elif pitch in (63, 64):
            add_tone(note, "sine", 4600.0, 0.004, 0.03, 8.0)
        elif pitch == 54:
            add_noise(note, 2800.0, 0.7, 16.0)
        else:
            add_noise(note, 2400.0, 0.85, 30.0)

    roles = {
        "drums": add_drums,
        "percussion": add_percussion,
        "bass": lambda note: add_tone(note, "sine", 9000.0, 0.008, 0.03, 1.2),
        "motif": lambda note: add_tone(note, "triangle", 5200.0, 0.012, 0.04, 0.6),
        "harmonic-field": lambda note: add_tone(note, "sine", 2800.0, 0.03, 0.06, 0.15),
        "atmosphere": lambda note: add_tone(note, "sine", 1800.0, 0.08, 0.1, 0.05),
    }
    rendered = []
    for part in parts:
        voice = roles[part["role"]]
        for note in part["notes"]:
            voice(note)
        rendered.append({"id": part["id"], "role": part["role"], "notes": len(part["notes"])})

    peak = 0
    for sample in mix:
        magnitude = sample if sample >= 0 else -sample
        if magnitude > peak:
            peak = magnitude
    if peak == 0:
        raise RuntimeError("preview mix is silent")
    scale = 1.0 if peak <= 28000 else 28000.0 / peak
    pcm = array("h")
    for sample in mix:
        value = int(sample * scale)
        if value > 32767:
            value = 32767
        elif value < -32768:
            value = -32768
        pcm.append(value)
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(wav_path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(pcm.tobytes())
    sample_peak = int(peak * scale)
    return {
        "renderer": RENDERER_VERSION,
        "sample_rate": SR,
        "channels": 1,
        "sample_format": "signed 16-bit little-endian PCM",
        "samples": total,
        "seconds": container_seconds(container_ticks, tempo_us),
        "rounding": "sample = floor(seconds * sample_rate + 0.5), computed from tick 0 of the excerpt; intervals are not summed",
        "sample_peak": sample_peak,
        "sample_peak_dbfs": 20.0 * math.log10(sample_peak / 32768.0),
        "sample_peak_note": "This is a sample peak of the integer mix after scaling. It is not a loudness measurement.",
        "voices": rendered,
        "mapping": {
            "drums": "Bass drum is a short falling sine. Snare, hats, and crash are short noise bursts with different decays. The MIDI pitch selects the burst. No controller is read.",
            "percussion": "Clave and woodblock are short sines. Congas are lower sines. Tambourine and maracas are short noise. The MIDI pitch selects the voice.",
            "bass": "Sine at the written pitch, short attack, held for the written duration.",
            "motif": "Triangle at the written pitch, short attack, held for the written duration.",
            "harmonic-field": "Quiet sine at the written pitch, held for the written duration.",
            "atmosphere": "Quieter sine with a slow attack at the written pitch. The attack is this synth envelope. The MIDI note is only pitch, start, duration, and velocity.",
        },
        "mapping_note": "These voices are preview mappings. They are not encoded in the MIDI file.",
    }
