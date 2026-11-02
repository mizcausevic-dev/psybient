"""Build the Psybient construction kit in the required order."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.article import TITLE, markdown, plain_text  # noqa: E402
from tools.audit import run_audit  # noqa: E402
from tools.compose import GENERATOR_VERSION, compose  # noqa: E402
from tools.midi_io import BAR_TICKS_4_4  # noqa: E402
from tools.page import write_page  # noqa: E402
from tools.render_audio import RENDERER_VERSION, render_preview  # noqa: E402
from tools.render_visual import (  # noqa: E402
    derive_social,
    draw_disclosure,
    encode_film,
    encode_mp3,
    paint,
    ppm_to_jpeg,
    write_ppm,
)
from tools.statements import (  # noqa: E402
    AUDITION,
    ON_PICTURE,
    PREVIEW_LINE,
    PROGRAM,
    PUBLICATION,
    WARNING,
)
from tools.validate import dump_json, validate_tree, write_midi_files  # noqa: E402

X_BODY = (
    "Psybient: Low Water 82, Glass Orbit 96, Dust Choir 76, Night Ferry 104. "
    "Preview is Low Water bars 9-16 at 82 BPM, 23.458 seconds, not the 32-bar MIDI. "
    "preview, not a master. The film shows preview, not master. "
    "No human listening audition was performed for this build."
)
EXCERPT_START = 8 * BAR_TICKS_4_4
EXCERPT_END = 16 * BAR_TICKS_4_4


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path: Path) -> dict:
    completed = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,sample_rate,channels",
            "-of", "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    streams = payload.get("streams", [])
    return {
        "duration": float(payload["format"]["duration"]),
        "video": any(stream.get("codec_type") == "video" for stream in streams),
        "audio": any(stream.get("codec_type") == "audio" for stream in streams),
        "streams": streams,
    }


def vtt_time(seconds: float) -> str:
    millis = int(math.floor(seconds * 1000 + 1e-9))
    if millis / 1000 > seconds:
        millis -= 1
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def excerpt_parts(score: dict) -> list[dict]:
    arrangement = score["arrangement"]
    by_id = {part["id"]: part for part in score["parts"]}
    pieces = []
    for track in arrangement["tracks"]:
        if track["source_part"] is None:
            continue
        source = by_id[track["source_part"]]
        if 8 not in track["placements"]:
            raise RuntimeError(f"{track['source_part']} is not in the preview window")
        notes = []
        for note in track["notes"]:
            start = note["performed_start"]
            end = start + note["duration"]
            if end <= EXCERPT_START or start >= EXCERPT_END:
                continue
            if start < EXCERPT_START or end > EXCERPT_END:
                raise RuntimeError(f"note crosses the excerpt boundary: {note['pitch']}@{start}")
            copied = dict(note)
            copied["nominal_start"] = start - EXCERPT_START
            copied["performed_start"] = start - EXCERPT_START
            notes.append(copied)
        expected = sorted(
            (note["performed_start"] + EXCERPT_START, note["pitch"], note["duration"], note["velocity"])
            for note in source["notes"]
        )
        actual = sorted(
            (note["performed_start"] + EXCERPT_START, note["pitch"], note["duration"], note["velocity"])
            for note in notes
        )
        if expected != actual:
            raise RuntimeError(f"excerpt notes do not match {source['id']}")
        pieces.append({
            "id": source["id"],
            "role": source["role"],
            "path": source["path"],
            "notes": notes,
        })
    return pieces


def write_readme(catalog: dict, preview: dict, film: dict) -> None:
    kit_lines = "\n".join(
        f"- {kit['id']} {kit['title']}: {kit['bpm']} BPM, parts {kit['part_bars']} bars, arrangement {kit['arrangement_bars']} bars, {kit['collection_name']}, tonic {kit['tonal_reference']}."
        for kit in catalog["kits"]
    )
    text = f"""# Psybient

Original note-only MIDI construction kits. Four kits, six core roles, two variations of each role. The roles are drums, percussion, bass, motif, harmonic field, and atmosphere. Each part is 8 bars. Each kit has one 32-bar arrangement built from variation A. There are no reference-only parts.

This is a creative direction: patient downtempo writing, moving pitch fields, and space between the parts. It is not a claim that the files are authentic genre productions. {PUBLICATION}

## What you can open

- `index.html` is the file catalog. The kit chooser draws lanes from the MIDI bytes.
- `media.html` is the stills page. The film sits under the pictures.
- `midi/arrangement.mid` is the Format 1 arrangement of Low Water, variation A, 32 bars.
- The other three arrangements live next to their part files under `midi/`.
- Individual Format 0 parts live under `midi/`.
- `midi/validation-Cursor.json` is the report from reopening those exact bytes.
- `preview/preview.mp3` is the primary music preview. It is {preview['seconds_encoded']:.3f} seconds in the encoded file. {PREVIEW_LINE}.
- `film/preview.mp4` and `film/preview.vtt` are the film. On-picture and caption text is `{ON_PICTURE}`.
- `art/hero.jpg` is a 1280x720 illustration. `art/square.jpg` is 1080x1080. Neither is a photograph.

{WARNING}

## Kits

{kit_lines}

Core files: {catalog['core_part_count']}. Reference files: {catalog['reference_part_count']}. {catalog['reference_note']}

{catalog['range_statement']} C4 is 60. PPQ is 960. Meter is 4/4. Offsets are 0. Seeds identify kits and are not random draws. Generator {GENERATOR_VERSION}.

Drums and percussion use channel 10. The drum map is kick 36, snare 38, closed hat 42, open hat 46, crash 49. The percussion map is tambourine 54, open conga 63, low conga 64, maracas 70, claves 75, woodblock 76. Closed and open hats do not overlap, and no choke controller is written.

## Preview path

The preview renders bars 9-16 of `midi/arrangement.mid` (ticks {EXCERPT_START} through {EXCERPT_END}) with `{RENDERER_VERSION}`. Those notes are variation A of all six Low Water parts, each shifted by 8 bars. The 32-bar arrangement stays in the MIDI. It is not the MP3. Tempo authority is the encoded microsecond value in the MIDI, {catalog['kits'][0]['tempo_us']} us per quarter note. Sample positions use `floor(seconds * 44100 + 0.5)` from the excerpt start. Intervals are not summed. Sample-exact repeating loops at an arbitrary BPM are not promised.

The synth mapping is documented in the preview manifest. Bass is a sine. The motif is a triangle. Harmony and atmosphere are quiet sines. The atmosphere attack is the synth envelope, not a message in the MIDI. Drum and percussion pitches select short sines or noise bursts. {PROGRAM} The mapping is not encoded in the MIDI.

Encoded MP3 settings: libmp3lame, 192 kbps. Film audio is AAC at 160 kbps re-encoded from that MP3, so the decoded film audio is not byte-identical to the MP3. Film duration probe: {film['duration_seconds']:.3f} seconds. {film['duration_relation']} The picture is a still illustration with rasterized disclosure text. DejaVu Sans Bold from the build machine supplies the glyphs. The font file is not in this pack.

{AUDITION} A sample peak is recorded in the preview manifest. It is not a loudness measurement.

## Build

From the repository root, with Python 3.11+ and ffmpeg (libmp3lame, aac, libx264):

```bash
python3 tools/build_pack.py
python3 -m http.server 43211
```

The page is static. It is served with Python's HTTP server so the MIDI and media keep working relative paths. There is no application server and no package install. Standard library only.

`build/` holds the intermediate WAV, the procedural PPM, and the film plate. Those files are gitignored. The delivered audio is the MP3.

## Checks the validator actually runs

File existence, parse, PPQ, tempo, 4/4, end-of-track boundary, note pairing, ranges, monophonic bass, role polyphony caps, channel 10 map, same-pitch overlap, note-off before note-on at a shared tick, absence of program changes and other channel messages, departure flags against the declared pitch-class set, agreement with the canonical score, and agreement between each arrangement and the placed source parts. Variation A attack times must differ across kits for each role. A negative overlap fixture is written outside the pack and must be rejected.

## Drafts and publication

Social captions, the X post, and the Medium article are drafts. They are not access controls. If this repository is public, the drafts are public. Do not treat them as posted to Instagram, X, or Medium.

Prepared repository description: Original note-only MIDI construction kits for psybient, with matched validation and a simple-synth preview.

Prepared topics: midi, psybient, music-production, composition, ambient.

No release tag was created. `index.html` keeps its name because players and links depend on it. This page is the file catalog the pack requires. GitHub Pages serves the gh-pages branch.

## Limitations

Variation A and variation B of a kit are alternatives. The arrangement already contains variation A, so stacking the part files on top of it doubles those notes. Parts from different kits do not share a tempo or a collection. Dust Choir's conga grouping is 3+3+2 sixteenths inside 4/4. It does not change the meter. These parts are original.
"""
    (ROOT / "README.md").write_text(text, encoding="utf-8")


def write_identity(catalog: dict) -> None:
    lines = [
        "# Kit identity",
        "",
        "Container lengths were fixed before note generation. Every core part is 8 bars. Every arrangement is 32 bars. Meter is 4/4. No stochastic draws.",
        "",
        catalog["creative_direction"],
        "",
        "Core versus reference: " + catalog["reference_note"],
        "",
    ]
    for kit in catalog["kits"]:
        lines.append(f"## {kit['id']} {kit['title']}")
        lines.append("")
        lines.append(kit["identity"])
        lines.append("")
        lines.append(f"Harmonic rhythm: {kit['harmonic_rhythm']}")
        lines.append("")
        lines.append(
            "Arrangement placements, in bars from 0: "
            + ", ".join(f"{role} {offsets}" for role, offsets in kit["placements"].items())
            + "."
        )
        lines.append("")
        lines.append(f"Limitations: {kit['limitations']}")
        lines.append("")
    (ROOT / "score" / "identity-Cursor.md").write_text("\n".join(lines), encoding="utf-8")


def write_social() -> None:
    ig = ROOT / "social" / "instagram-Cursor"
    xdir = ROOT / "social" / "x-Cursor"
    ig.mkdir(parents=True, exist_ok=True)
    xdir.mkdir(parents=True, exist_ok=True)
    caption = """DRAFT
This file is a draft. It has not been posted.

Caption

Psybient. Four kits: Low Water 82, Glass Orbit 96, Dust Choir 76, Night Ferry 104. Drums, percussion, bass, motif, harmonic field, and atmosphere, two variations each, one 32-bar arrangement. Atmosphere is notes plus a documented sine mapping, not a hidden effect. The audio preview is bars 9-16 of Low Water at 82 BPM, 23.458 seconds, not the 32-bar arrangement. preview, not a master. The film shows preview, not master. No human listening audition was performed for this build.

Hashtags

#midi #psybient #musicproduction #composition #ambient

Alt text, 1080x1080

Illustration of horizontal lanes on a deep teal field. Long bars are pads, short ticks are drums, and a sand bar is the motif. Not a photograph of a studio or of performers.

Alt text, 1080x1350

The same teal lane illustration, cropped from the square still and reframed as a vertical 1080 by 1350 image. The crop keeps a centered 864-pixel-wide slice of the square, then scales it. Not a photograph of a studio or of performers.
"""
    (ig / "captions-Cursor.md").write_text(caption, encoding="utf-8")
    post = f"DRAFT\nThis label is not the post body.\n\nPOST BODY\n{X_BODY}\n"
    if len(X_BODY) > 280 or "DRAFT" in X_BODY:
        raise RuntimeError(f"X body is {len(X_BODY)} characters")
    (xdir / "post-Cursor.txt").write_text(post, encoding="utf-8")
    (xdir / "alt-text-Cursor.txt").write_text(
        "Illustration of teal lanes, long pad bars, and short drum ticks, resized from the 1280 by 720 still. Not a photograph of a studio or of performers.\n",
        encoding="utf-8",
    )


def write_publication_plan(preview: dict) -> None:
    text = f"""# Publication plan

Status: prepared for GitHub Pages on the gh-pages branch. Treat the address as live only after it responds.

{PUBLICATION}

## What is local

The MIDI, matched validation report, MP3 ({preview['seconds_encoded']:.3f} s), MP4, VTT, raster stills, drafts, page, and README are produced by `python3 tools/build_pack.py`. Draft labels do not hide files. A public remote makes the drafts public.

## What this build does not do

No release tag is created. Nothing is posted to Medium, Instagram, or X. The catalog address is the GitHub Pages URL in the publication line.

## Prepared metadata

Description: Original note-only MIDI construction kits for psybient, with matched validation and a simple-synth preview.

Topics: midi, psybient, music-production, composition, ambient.

`index.html` is the Pages entry. `media.html` is the stills page. Pages should serve the gh-pages branch at the repository root.

## Security note for a later deploy

The page is static. It has no form, no account system, and no secret. It links to MIDI and media in the same tree. A later deploy should not add a checkout or a lead form without a separate privacy review.
"""
    path = ROOT / "docs" / "publication-plan-Cursor.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    if len(X_BODY) > 280:
        raise SystemExit(f"X body {len(X_BODY)}")
    data = compose()
    dump_json(ROOT / "catalog" / "catalog-Cursor.json", data["catalog"])
    dump_json(ROOT / "score" / "canonical-score-Cursor.json", data["score"])
    write_midi_files(ROOT, data["score"])
    report = validate_tree(ROOT)
    if report["result"] != "PASS":
        dump_json(ROOT / "midi" / "validation-Cursor.json", report)
        raise SystemExit("MIDI validation failed:\n" + "\n".join(report["errors"]))
    dump_json(ROOT / "midi" / "validation-Cursor.json", report)

    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    pieces = excerpt_parts(data["score"])
    arrangement = data["score"]["arrangement"]
    wav_path = build / "preview.wav"
    audio_info = render_preview(pieces, arrangement["tempo_us"], EXCERPT_END - EXCERPT_START, wav_path)
    mp3_path = ROOT / "preview" / "preview.mp3"
    mp3_cmd = encode_mp3(wav_path, mp3_path)
    mp3_probe = probe(mp3_path)
    if not 10 <= mp3_probe["duration"] <= 40:
        raise SystemExit(f"preview duration {mp3_probe['duration']} is outside 10-40 seconds")

    by_path = {record["path"]: record for record in report["files"]}
    source_files = []
    for part in pieces:
        record = by_path[part["path"]]
        source_files.append({"path": part["path"], "sha256": record["sha256"], "id": part["id"]})
    manifest = {
        "pack_id": data["catalog"]["pack_id"],
        "renderer": RENDERER_VERSION,
        "renderer_note": audio_info["mapping_note"],
        "mapping": audio_info["mapping"],
        "source_parts": source_files,
        "arrangement_path": arrangement["path"],
        "arrangement_sha256": report["arrangement"]["sha256"],
        "score_sha256": report["score_sha256"],
        "excerpt": {
            "kit": "k01",
            "title": "Low Water",
            "bars": "9-16",
            "start_tick": EXCERPT_START,
            "end_tick": EXCERPT_END,
            "bar_count": 8,
            "bpm": 82,
            "transposition": "none",
            "sequencing": "variation A of drums, percussion, bass, motif, harmonic field, and atmosphere",
            "correspondence": "Each preview note equals the 8-bar kit note with performed_start increased by 30720, which is bar 9 of the 32-bar arrangement.",
        },
        "tempo_us": arrangement["tempo_us"],
        "tempo_authority": "encoded MIDI tempo",
        "score_seconds": audio_info["seconds"],
        "rounding": audio_info["rounding"],
        "sample_peak": audio_info["sample_peak"],
        "sample_peak_dbfs": audio_info["sample_peak_dbfs"],
        "sample_peak_note": audio_info["sample_peak_note"],
        "intermediate_wav": "build/preview.wav",
        "intermediate_wav_sha256": sha256_file(wav_path),
        "intermediate_wav_note": "The WAV is gitignored build storage. The delivered preview is the MP3.",
        "mp3_path": "preview/preview.mp3",
        "mp3_sha256": sha256_file(mp3_path),
        "mp3_encode_command": mp3_cmd,
        "seconds_encoded": mp3_probe["duration"],
        "encode": "libmp3lame CBR 192 kbps, mono source",
        "program_changes": PROGRAM,
        "listening": AUDITION,
        "label": PREVIEW_LINE,
    }
    manifest_path = ROOT / "preview" / "preview-manifest-Cursor.txt"
    manifest_path.write_text(PREVIEW_LINE + "\n" + json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    wide = paint(1280, 720, "wide")
    plate_ppm = build / "plate.ppm"
    write_ppm(plate_ppm, 1280, 720, wide)
    plate_jpg = build / "plate.jpg"
    ppm_to_jpeg(plate_ppm, plate_jpg)
    textfile = build / "onpicture.txt"
    film_cmd = encode_film(plate_jpg, mp3_path, ROOT / "film" / "preview.mp4", textfile, f"{mp3_probe['duration']:.6f}")
    mp4_probe = probe(ROOT / "film" / "preview.mp4")
    vtt_end = vtt_time(mp4_probe["duration"])
    vtt = f"WEBVTT\n\n00:00:00.000 --> {vtt_end}\n{ON_PICTURE}\n"
    (ROOT / "film" / "preview.vtt").write_text(vtt, encoding="utf-8")

    ppm_to_jpeg(plate_ppm, ROOT / "art" / "hero.jpg")
    square_rgb = paint(1080, 1080, "square")
    square_ppm = build / "square.ppm"
    write_ppm(square_ppm, 1080, 1080, square_rgb)
    ppm_to_jpeg(square_ppm, ROOT / "art" / "square.jpg")
    poster_cmd = draw_disclosure(ROOT / "art" / "hero.jpg", ROOT / "film" / "poster.jpg", textfile)

    ig_square = ROOT / "social" / "instagram-Cursor" / "square.jpg"
    ig_portrait = ROOT / "social" / "instagram-Cursor" / "portrait.jpg"
    card = ROOT / "social" / "x-Cursor" / "card.jpg"
    ig_square.parent.mkdir(parents=True, exist_ok=True)
    card.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "art" / "square.jpg", ig_square)
    social_cmds = derive_social(ROOT / "art" / "hero.jpg", ROOT / "art" / "square.jpg", ig_portrait, card)
    lineage = {
        "painter": "tools/render_visual.py paint()",
        "hero": "JPEG of the 1280x720 wide framing. The film plate is a JPEG of the same PPM, made before this final hero file was written.",
        "square": "JPEG of the 1080x1080 square framing of the same painter. Not a scale of the hero.",
        "instagram_square": "Byte copy of art/square.jpg.",
        "instagram_square_sha256": sha256_file(ig_square),
        "square_sha256": sha256_file(ROOT / "art" / "square.jpg"),
        "instagram_portrait": "crop=864:1080:108:0 of the square still, then scale to 1080x1350.",
        "x_card": "scale the 1280x720 hero to 1600x900.",
        "commands": social_cmds,
        "poster_command": poster_cmd,
    }
    if lineage["instagram_square_sha256"] != lineage["square_sha256"]:
        raise SystemExit("Instagram square is not a byte copy of the square still")
    dump_json(ROOT / "social" / "lineage-Cursor.json", lineage)

    film_manifest = {
        "audio_source": "preview/preview.mp3",
        "audio_source_sha256": manifest["mp3_sha256"],
        "picture_source": "build/plate.jpg from the wide procedural paint. Disclosure text is drawn on top.",
        "on_picture": ON_PICTURE,
        "textfile_contents": textfile.read_text(encoding="utf-8").strip(),
        "encode_command": film_cmd,
        "video_codec": "libx264",
        "audio_codec": "aac",
        "audio_bitrate": "160k",
        "reencode_note": "Film audio is decoded from the MP3 and encoded as AAC. It is not byte-identical to the preview.",
        "duration_seconds": mp4_probe["duration"],
        "mp3_duration_seconds": mp3_probe["duration"],
        "streams": mp4_probe["streams"],
        "vtt": "film/preview.vtt",
        "font": "DejaVu Sans Bold, build machine only, not redistributed",
        "listening": AUDITION,
        "duration_relation": (
            f"MP3 container probe {mp3_probe['duration']:.3f} seconds. "
            f"MP4 probe {mp4_probe['duration']:.3f} seconds. "
            "The film ends on a video frame, so it is slightly shorter than the MP3 container. "
            "The music is the same preview, not a different excerpt."
        ),
    }
    if film_manifest["textfile_contents"] != ON_PICTURE:
        raise SystemExit("on-picture textfile drifted")
    dump_json(ROOT / "film" / "film-manifest-Cursor.json", film_manifest)

    articles = ROOT / "articles"
    articles.mkdir(exist_ok=True)
    (articles / "medium-draft-Cursor.md").write_text(markdown(), encoding="utf-8")
    (articles / "medium-paste-Cursor.txt").write_text(plain_text(), encoding="utf-8")
    write_social()
    write_identity(data["catalog"])
    write_page(ROOT / "index.html", data["catalog"], report, manifest, film_manifest)
    write_readme(data["catalog"], manifest, film_manifest)
    write_publication_plan(manifest)
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")

    frame = build / "film-frame.png"
    subprocess.run(
        ["ffmpeg", "-y", "-ss", "1", "-i", str(ROOT / "film" / "preview.mp4"), "-frames:v", "1", str(frame)],
        check=True,
        capture_output=True,
    )
    probes = {"mp3": mp3_probe, "mp4": mp4_probe}
    checklist = run_audit(ROOT, probes)
    dump_json(ROOT / "checks" / "artifact-checklist-Cursor.json", checklist)
    print(checklist["result"])
    for item in checklist["items"]:
        print(f"{item['status']:7} {item['name']} :: {item['evidence']}")
    if checklist["result"] != "PASS":
        raise SystemExit(1)
    print("TITLE", TITLE)
    print("X_BODY_CHARS", len(X_BODY))
    print("PREVIEW_SECONDS", f"{mp3_probe['duration']:.3f}")


if __name__ == "__main__":
    main()
