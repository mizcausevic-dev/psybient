"""Procedural raster artwork and ffmpeg media steps.

The painter is original and deterministic. It draws horizontal lanes on a deep
teal field: long bars for pads, short ticks for drums, one sand bar for the
motif. It is an illustration, not a photograph of a session or of performers.

DejaVu Sans Bold is used only to rasterize the disclosure into the film and the
poster. The font file is not shipped.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
ON_PICTURE = "preview, not master"


def _clamp(value: int) -> int:
    return 0 if value < 0 else 255 if value > 255 else value


def paint(width: int, height: int, framing: str) -> bytes:
    """Deep teal lanes. Square and wide are different framings, not scales."""
    pixels = bytearray(width * height * 3)
    for y in range(height):
        shade = y / max(1, height - 1)
        row = y * width * 3
        base_r = int(6 + 8 * shade)
        base_g = int(28 + 26 * shade)
        base_b = int(26 + 18 * shade)
        for x in range(width):
            pixels[row + x * 3] = base_r
            pixels[row + x * 3 + 1] = base_g
            pixels[row + x * 3 + 2] = base_b
    margin_x = int(width * (0.08 if framing == "wide" else 0.12))
    margin_y = int(height * (0.14 if framing == "wide" else 0.1))
    lane_count = 6
    lane_gap = (height - margin_y * 2) / lane_count
    for lane in range(lane_count):
        y = int(margin_y + lane * lane_gap + lane_gap * 0.72)
        if not 0 <= y < height:
            continue
        row = y * width * 3
        for x in range(margin_x, width - margin_x):
            pixels[row + x * 3] = 18
            pixels[row + x * 3 + 1] = 64
            pixels[row + x * 3 + 2] = 58
    if framing == "wide":
        bars = (
            (0, 0.08, 0.42, 196, 214, 188),
            (0, 0.48, 0.28, 120, 176, 160),
            (1, 0.18, 0.55, 92, 158, 146),
            (2, 0.30, 0.22, 196, 174, 120),
            (3, 0.06, 0.12, 150, 210, 196),
            (3, 0.28, 0.10, 150, 210, 196),
            (3, 0.52, 0.08, 150, 210, 196),
            (4, 0.10, 0.06, 214, 228, 220),
            (4, 0.40, 0.05, 214, 228, 220),
            (4, 0.70, 0.05, 214, 228, 220),
            (5, 0.04, 0.04, 232, 236, 228),
            (5, 0.22, 0.03, 232, 236, 228),
            (5, 0.46, 0.04, 232, 236, 228),
            (5, 0.78, 0.03, 232, 236, 228),
        )
    else:
        bars = (
            (0, 0.16, 0.62, 120, 176, 160),
            (1, 0.10, 0.34, 196, 214, 188),
            (1, 0.52, 0.30, 92, 158, 146),
            (2, 0.22, 0.18, 196, 174, 120),
            (2, 0.58, 0.16, 196, 174, 120),
            (3, 0.08, 0.14, 150, 210, 196),
            (4, 0.20, 0.08, 214, 228, 220),
            (4, 0.48, 0.07, 214, 228, 220),
            (5, 0.12, 0.05, 232, 236, 228),
            (5, 0.36, 0.04, 232, 236, 228),
            (5, 0.64, 0.05, 232, 236, 228),
        )
    usable = width - margin_x * 2
    for lane, start, length, red, green, blue in bars:
        y0 = int(margin_y + lane * lane_gap + lane_gap * 0.18)
        y1 = int(margin_y + lane * lane_gap + lane_gap * 0.62)
        x0 = margin_x + int(start * usable)
        x1 = x0 + max(4, int(length * usable))
        for y in range(max(0, y0), min(height, y1)):
            row = y * width * 3
            for x in range(max(0, x0), min(width, x1)):
                pixels[row + x * 3] = red
                pixels[row + x * 3 + 1] = green
                pixels[row + x * 3 + 2] = blue
    return bytes(pixels)

def write_ppm(path: Path, width: int, height: int, rgb: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    path.write_bytes(header + rgb)


def run(command: list[str]) -> None:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "command failed\n"
            + " ".join(command)
            + "\n"
            + completed.stderr[-2000:]
        )


def ppm_to_jpeg(ppm: Path, jpeg: Path, quality: int = 3) -> None:
    jpeg.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-i", str(ppm), "-frames:v", "1", "-q:v", str(quality), str(jpeg)])


def draw_disclosure(source: Path, dest: Path, textfile: Path) -> list[str]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    textfile.write_text(ON_PICTURE + "\n", encoding="utf-8")
    command = [
        "ffmpeg", "-y", "-i", str(source),
        "-vf",
        (
            f"drawtext=textfile={textfile}:fontfile={FONT}:fontsize=48:"
            "fontcolor=white:x=(w-text_w)/2:y=h-100:box=1:boxcolor=black@0.68:boxborderw=22"
        ),
        "-frames:v", "1",
        "-q:v", "3",
        str(dest),
    ]
    run(command)
    return command


def encode_mp3(wav: Path, mp3: Path) -> list[str]:
    mp3.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y", "-i", str(wav),
        "-codec:a", "libmp3lame", "-b:a", "192k",
        str(mp3),
    ]
    run(command)
    return command


def encode_film(plate: Path, mp3: Path, mp4: Path, textfile: Path, duration: str) -> list[str]:
    mp4.parent.mkdir(parents=True, exist_ok=True)
    textfile.write_text(ON_PICTURE + "\n", encoding="utf-8")
    command = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "24", "-i", str(plate),
        "-i", str(mp3),
        "-t", duration,
        "-vf",
        (
            "scale=1280:720,"
            f"drawtext=textfile={textfile}:fontfile={FONT}:fontsize=48:"
            "fontcolor=white:x=(w-text_w)/2:y=h-100:box=1:boxcolor=black@0.68:boxborderw=22"
        ),
        "-r", "24",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        "-shortest",
        "-movflags", "+faststart",
        str(mp4),
    ]
    run(command)
    return command


def derive_social(hero: Path, square: Path, portrait: Path, card: Path) -> dict[str, list[str]]:
    portrait.parent.mkdir(parents=True, exist_ok=True)
    card.parent.mkdir(parents=True, exist_ok=True)
    portrait_cmd = [
        "ffmpeg", "-y", "-i", str(square),
        "-vf", "crop=864:1080:108:0,scale=1080:1350",
        "-q:v", "3",
        str(portrait),
    ]
    card_cmd = [
        "ffmpeg", "-y", "-i", str(hero),
        "-vf", "scale=1600:900",
        "-q:v", "3",
        str(card),
    ]
    run(portrait_cmd)
    run(card_cmd)
    return {"portrait": portrait_cmd, "card": card_cmd}
