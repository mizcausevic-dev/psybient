"""Reopen delivered MIDI bytes and compare them with the canonical score.

The report records hashes of the files it checked. It does not hash itself.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from tools.compose import DRUM_MAP, PERC_MAP, ROLE_NAME
from tools.midi_io import (
    BAR_TICKS_4_4,
    PPQ,
    bpm_to_us,
    effective_bpm,
    notes_to_events,
    pair_notes,
    parse_midi,
    preamble,
    write_midi,
)

VALIDATOR_VERSION = "psybient-1.0.0"
ROLE_LIMITS = {
    "drums": {"lo": 36, "hi": 51, "poly": 4},
    "percussion": {"lo": 54, "hi": 76, "poly": 4},
    "bass": {"lo": 28, "hi": 55, "poly": 1},
    "motif": {"lo": 60, "hi": 84, "poly": 1},
    "harmonic-field": {"lo": 48, "hi": 76, "poly": 5},
    "atmosphere": {"lo": 52, "hi": 88, "poly": 3},
}
PERCUSSION_ROLES = {"drums", "percussion"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def dump_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_midi_files(root: Path, score: dict) -> None:
    for part in score["parts"]:
        events = preamble(ROLE_NAME[part["role"]], part["tempo_us"], part["container_ticks"])
        events += notes_to_events(part["notes"])
        write_midi(root / part["path"], 0, [(events, part["container_ticks"])])
    for arrangement in score["arrangements"]:
        container = arrangement["container_ticks"]
        tracks = [(preamble("Conductor", arrangement["tempo_us"], container), container)]
        for track in arrangement["tracks"]:
            if track["source_part"] is None:
                continue
            events = [{"type": "track_name", "tick": 0, "name": track["name"]}]
            events += notes_to_events(track["notes"])
            tracks.append((events, container))
        write_midi(root / arrangement["path"], 1, tracks)


def _meta(track: dict, meta_type: int) -> list[dict]:
    return [event for event in track["events"] if event["type"] == "meta" and event["meta_type"] == meta_type]


def _tempo_us(track: dict) -> int | None:
    found = _meta(track, 0x51)
    if len(found) != 1:
        return None
    data = found[0]["data"]
    if len(data) != 3 or found[0]["tick"] != 0:
        return None
    return (data[0] << 16) | (data[1] << 8) | data[2]


def _meter(track: dict) -> tuple[int, int] | None:
    found = _meta(track, 0x58)
    if len(found) != 1 or found[0]["tick"] != 0 or len(found[0]["data"]) != 4:
        return None
    numerator = found[0]["data"][0]
    denominator = 1 << found[0]["data"][1]
    return numerator, denominator


def _note_key(note: dict) -> tuple:
    return (note["channel"], note["pitch"], note["start"], note["duration"], note["velocity"])


def _overlaps(notes: list[dict], monophonic: bool) -> str | None:
    ordered = sorted(notes, key=lambda note: (note["start"], note["pitch"]))
    for index, left in enumerate(ordered):
        left_end = left["start"] + left["duration"]
        for right in ordered[index + 1:]:
            if right["start"] >= left_end:
                break
            same_channel = left.get("channel", right.get("channel")) == right.get("channel", left.get("channel"))
            if not same_channel:
                continue
            if monophonic or left["pitch"] == right["pitch"]:
                return f"{left['pitch']}@{left['start']} overlaps {right['pitch']}@{right['start']}"
    return None


def _max_poly(notes: list[dict]) -> int:
    points = []
    for note in notes:
        points.append((note["start"], 1))
        points.append((note["start"] + note["duration"], -1))
    points.sort(key=lambda item: (item[0], item[1]))
    active = 0
    peak = 0
    for _, delta in points:
        active += delta
        peak = max(peak, active)
    return peak


def _same_tick_order(track: dict) -> str | None:
    by_tick: dict[int, list[str]] = {}
    for event in track["events"]:
        if event["type"] in ("note_on", "note_off"):
            by_tick.setdefault(event["tick"], []).append(event["type"])
    for tick, kinds in by_tick.items():
        seen_on = False
        for kind in kinds:
            if kind == "note_on":
                seen_on = True
            elif kind == "note_off" and seen_on:
                return f"note-off follows note-on at tick {tick}"
    return None


def _check_part_file(path: Path, part: dict, pitch_classes: set[int]) -> tuple[dict, list[str], list[dict]]:
    errors = []
    data = path.read_bytes()
    record = {
        "path": part["path"],
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "role": part["role"],
        "core": part["core"],
        "checks": {},
    }
    try:
        parsed = parse_midi(data)
    except Exception as exc:  # noqa: BLE001
        record["checks"]["parse"] = f"FAIL {exc}"
        errors.append(f"{part['path']} parse: {exc}")
        return record, errors, []
    record["format"] = parsed["format"]
    record["ppq"] = parsed["ppq"]
    record["tracks"] = len(parsed["tracks"])
    if parsed["format"] != 0:
        errors.append(f"{part['path']} format {parsed['format']}")
    if parsed["ppq"] != PPQ:
        errors.append(f"{part['path']} ppq {parsed['ppq']}")
    if len(parsed["tracks"]) != 1:
        errors.append(f"{part['path']} track count")
        return record, errors, []
    track = parsed["tracks"][0]
    if track["eot_tick"] != part["container_ticks"]:
        errors.append(f"{part['path']} eot {track['eot_tick']} != {part['container_ticks']}")
    tempo = _tempo_us(track)
    meter = _meter(track)
    record["tempo_us"] = tempo
    record["requested_bpm"] = part["bpm"]
    record["effective_bpm"] = None if tempo is None else effective_bpm(tempo)
    record["meter"] = None if meter is None else f"{meter[0]}/{meter[1]}"
    if tempo != part["tempo_us"]:
        errors.append(f"{part['path']} tempo {tempo} != {part['tempo_us']}")
    if meter != (4, 4):
        errors.append(f"{part['path']} meter {meter}")
    unexpected = [
        event for event in track["events"]
        if event["type"] in ("sysex", "channel") or (event["type"] == "meta" and event["meta_type"] not in (0x03, 0x51, 0x58, 0x2F))
    ]
    if unexpected:
        errors.append(f"{part['path']} unexpected messages {[event['type'] for event in unexpected]}")
    order_error = _same_tick_order(track)
    if order_error:
        errors.append(f"{part['path']} {order_error}")
    try:
        notes = pair_notes(track)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{part['path']} pairing: {exc}")
        return record, errors, []
    record["notes"] = len(notes)
    record["channels"] = sorted({note["channel"] for note in notes})
    for note in notes:
        end = note["start"] + note["duration"]
        if note["start"] < 0 or note["duration"] <= 0 or note["start"] >= part["container_ticks"] or end > part["container_ticks"]:
            errors.append(f"{part['path']} boundary {note}")
            break
        if not 1 <= note["velocity"] <= 127:
            errors.append(f"{part['path']} velocity {note['velocity']}")
            break
    if part["role"] in PERCUSSION_ROLES:
        allowed = DRUM_MAP if part["role"] == "drums" else PERC_MAP
        if any(note["channel"] != 9 or note["pitch"] not in allowed for note in notes):
            errors.append(f"{part['path']} percussion map")
    else:
        if any(note["channel"] != part["channel"] for note in notes):
            errors.append(f"{part['path']} channel")
        limits = ROLE_LIMITS[part["role"]]
        if any(not limits["lo"] <= note["pitch"] <= limits["hi"] for note in notes):
            errors.append(f"{part['path']} range")
        outside = 0
        for note in notes:
            if (note["pitch"] % 12) not in pitch_classes:
                outside += 1
        if outside:
            record["outside_collection"] = outside
    overlap = _overlaps(notes, monophonic=part["monophonic"])
    if overlap:
        errors.append(f"{part['path']} {overlap}")
    limits = ROLE_LIMITS[part["role"]]
    if _max_poly(notes) > limits["poly"]:
        errors.append(f"{part['path']} polyphony {_max_poly(notes)} > {limits['poly']}")
    record["max_polyphony"] = _max_poly(notes)
    record["checks"] = {
        "parse": "PASS",
        "ppq": parsed["ppq"],
        "tempo": tempo,
        "meter": record["meter"],
        "eot": track["eot_tick"],
        "notes": len(notes),
        "overlap": "PASS" if overlap is None else overlap,
    }
    return record, errors, notes


def _expand_source(source_notes: list[dict], placements: list[int]) -> list[dict]:
    expanded = []
    for offset in placements:
        shift = offset * BAR_TICKS_4_4
        for note in source_notes:
            expanded.append({
                "channel": note["channel"],
                "pitch": note["pitch"],
                "start": note["start"] + shift,
                "duration": note["duration"],
                "velocity": note["velocity"],
            })
    return expanded


def _check_arrangement(root: Path, arrangement: dict, reopened: dict) -> tuple[dict, list[str]]:
    errors = []
    path = root / arrangement["path"]
    record = {"path": arrangement["path"], "kit_id": arrangement["kit_id"]}
    if not path.is_file():
        errors.append(f"missing {arrangement['path']}")
        return record, errors
    data = path.read_bytes()
    record.update({"bytes": len(data), "sha256": sha256_bytes(data)})
    parsed = parse_midi(data)
    record["format"] = parsed["format"]
    record["ppq"] = parsed["ppq"]
    record["tracks"] = len(parsed["tracks"])
    musical = [track for track in arrangement["tracks"] if track["source_part"]]
    if parsed["format"] != 1 or parsed["ppq"] != PPQ or len(parsed["tracks"]) != len(arrangement["tracks"]):
        errors.append(f"{arrangement['path']} header")
    if len(parsed["tracks"]) != len(musical) + 1:
        errors.append(f"{arrangement['path']} track count {len(parsed['tracks'])}")
    conductor = parsed["tracks"][0]
    if _tempo_us(conductor) != arrangement["tempo_us"] or _meter(conductor) != (4, 4):
        errors.append(f"{arrangement['path']} conductor tempo or meter")
    if pair_notes(conductor):
        errors.append(f"{arrangement['path']} conductor has notes")
    if conductor["eot_tick"] != arrangement["container_ticks"]:
        errors.append(f"{arrangement['path']} conductor boundary")
    channel_ten = []
    for index, track_spec in enumerate(musical, start=1):
        track = parsed["tracks"][index]
        if _meta(track, 0x51) or _meta(track, 0x58):
            errors.append(f"{arrangement['path']} tempo or meter leaked onto {track_spec['name']}")
        if track["eot_tick"] != arrangement["container_ticks"]:
            errors.append(f"{arrangement['path']} {track_spec['name']} boundary")
        if _same_tick_order(track):
            errors.append(f"{arrangement['path']} {track_spec['name']} note order")
        notes = pair_notes(track)
        source = reopened.get(track_spec["source_part"], [])
        expected = _expand_source(source, track_spec["placements"])
        if Counter(_note_key(note) for note in notes) != Counter(_note_key(note) for note in expected):
            errors.append(f"{arrangement['path']} {track_spec['name']} disagrees with {track_spec['source_part']}")
        canonical = [{
            "channel": note["channel"],
            "pitch": note["pitch"],
            "start": note["performed_start"],
            "duration": note["duration"],
            "velocity": note["velocity"],
        } for note in track_spec["notes"]]
        if Counter(_note_key(note) for note in notes) != Counter(_note_key(note) for note in canonical):
            errors.append(f"{arrangement['path']} {track_spec['name']} disagrees with the score")
        overlap = _overlaps(notes, monophonic=False)
        if overlap:
            errors.append(f"{arrangement['path']} {track_spec['name']} {overlap}")
        for note in notes:
            if note["channel"] == 9:
                channel_ten.append(note)
    cross = _overlaps(channel_ten, monophonic=False)
    if cross:
        errors.append(f"{arrangement['path']} channel 10 {cross}")
    record["agreement"] = "PASS" if not any(item.startswith(arrangement["path"]) for item in errors) else "FAIL"
    return record, errors


def _negative_tests() -> dict:
    results = {}
    bad_notes = [
        {"channel": 0, "pitch": 40, "performed_start": 0, "duration": 480, "velocity": 80},
        {"channel": 0, "pitch": 42, "performed_start": 240, "duration": 240, "velocity": 80},
    ]
    events = preamble("Bass", bpm_to_us(82), BAR_TICKS_4_4) + notes_to_events(bad_notes)
    path = Path("/tmp/psybient-negative-overlap.mid")
    write_midi(path, 0, [(events, BAR_TICKS_4_4)])
    parsed = parse_midi(path.read_bytes())
    notes = pair_notes(parsed["tracks"][0])
    overlap = _overlaps(notes, monophonic=True)
    results["monophonic_overlap_detected"] = "PASS" if overlap else "FAIL"
    try:
        write_midi(path, 0, [(events, 100)])
        results["boundary_rejected_at_write"] = "FAIL"
    except ValueError:
        results["boundary_rejected_at_write"] = "PASS"
    path.unlink(missing_ok=True)
    return results


def _recompute_identity(parts: list[dict]) -> dict:
    by_role: dict[str, dict[str, dict[str, dict]]] = {}
    for part in parts:
        by_role.setdefault(part["role"], {}).setdefault(part["kit_id"], {})[part["variation"]] = part
    errors = []
    seen_by_role = {}
    for role, kits_map in by_role.items():
        seen = {}
        for kit_id, versions in kits_map.items():
            left = versions["a"]["notes"]
            right = versions["b"]["notes"]
            sig_a = tuple((note["performed_start"], note["pitch"], note["duration"]) for note in left)
            sig_b = tuple((note["performed_start"], note["pitch"], note["duration"]) for note in right)
            if sig_a == sig_b:
                errors.append(f"{kit_id} {role} variations match")
            attacks = tuple(note["performed_start"] for note in left)
            if attacks in seen:
                errors.append(f"{role} variation A attacks repeat {seen[attacks]} and {kit_id}")
            seen[attacks] = kit_id
        seen_by_role[role] = len(seen)
    return {"pass": not errors, "errors": errors, "roles": seen_by_role}


def validate_tree(root: Path) -> dict:
    catalog = load_json(root / "catalog" / "catalog-Cursor.json")
    score = load_json(root / "score" / "canonical-score-Cursor.json")
    errors = []
    if catalog["pack_id"] != score["pack_id"]:
        errors.append("pack id mismatch")
    pitch_sets = {kit["id"]: set(kit["pitch_classes"]) for kit in catalog["kits"]}
    file_records = []
    reopened = {}
    for part in score["parts"]:
        path = root / part["path"]
        if not path.is_file():
            errors.append(f"missing {part['path']}")
            continue
        record, part_errors, notes = _check_part_file(path, part, pitch_sets[part["kit_id"]])
        errors.extend(part_errors)
        expected = Counter(_note_key({
            "channel": note["channel"],
            "pitch": note["pitch"],
            "start": note["performed_start"],
            "duration": note["duration"],
            "velocity": note["velocity"],
        }) for note in part["notes"])
        actual = Counter(_note_key(note) for note in notes)
        if expected != actual:
            errors.append(f"{part['path']} does not match the canonical score")
            record["score_agreement"] = "FAIL"
        else:
            record["score_agreement"] = "PASS"
        if part["role"] not in PERCUSSION_ROLES:
            departures = [note for note in part["notes"] if note["departure"]]
            for note in departures:
                if (note["pitch"] % 12) in pitch_sets[part["kit_id"]]:
                    errors.append(f"{part['id']} departure {note['pitch']} is inside the collection")
            for note in part["notes"]:
                if not note["departure"] and (note["pitch"] % 12) not in pitch_sets[part["kit_id"]]:
                    errors.append(f"{part['id']} note {note['pitch']} left the collection without a departure flag")
            record["departures"] = len(departures)
        else:
            record["departures"] = 0
        file_records.append(record)
        reopened[part["id"]] = notes

    arrangement_records = []
    for arrangement in score["arrangements"]:
        record, arrangement_errors = _check_arrangement(root, arrangement, reopened)
        errors.extend(arrangement_errors)
        arrangement_records.append(record)
    primary = next(record for record in arrangement_records if record["path"] == score["arrangement"]["path"])

    identity = _recompute_identity(score["parts"])
    if not identity["pass"]:
        errors.extend(identity["errors"])
    negative = _negative_tests()
    if any(value != "PASS" for value in negative.values()):
        errors.append(f"negative tests {negative}")
    report = {
        "validator_version": VALIDATOR_VERSION,
        "generator_version": score["generator_version"],
        "pack_id": score["pack_id"],
        "catalog_path": "catalog/catalog-Cursor.json",
        "catalog_sha256": sha256_file(root / "catalog" / "catalog-Cursor.json"),
        "score_path": "score/canonical-score-Cursor.json",
        "score_sha256": sha256_file(root / "score" / "canonical-score-Cursor.json"),
        "result": "FAIL" if errors else "PASS",
        "errors": errors,
        "files": file_records,
        "arrangement": primary,
        "arrangements": arrangement_records,
        "identity_check": {
            "method": score["identity_check"]["method"],
            "recomputed": identity,
        },
        "negative_tests": negative,
        "percussion_map": {
            "channel": 10,
            "drums": {str(pitch): name for pitch, name in DRUM_MAP.items()},
            "percussion": {str(pitch): name for pitch, name in PERC_MAP.items()},
        },
        "repairs": [],
        "repair_note": "No repairs were applied. This report is the first validation pass of the delivered bytes.",
        "listening": "No human listening audition was performed for this build.",
        "rules": [
            "file exists and parses",
            "PPQ 960",
            "encoded tempo and 4/4 meter",
            "one end-of-track at the declared container",
            "explicit note pairing",
            "boundaries, velocity, range, monophonic bass, role polyphony caps",
            "channel 10 drums and percussion limited to the declared maps",
            "same-pitch overlap is illegal, including across channel 10 arrangement tracks",
            "note-offs precede note-ons that share a tick",
            "no program changes or other channel messages",
            "reopened notes match the canonical score",
            "each arrangement track is the source part placed at the declared bar offsets",
            "variation A attack times are unique per role across kits",
            "variation B is a different phrase from variation A",
        ],
    }
    return report
