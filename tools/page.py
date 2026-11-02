"""Catalog page. Kit lanes are measured from the fetched MIDI files."""

from __future__ import annotations

import json
from pathlib import Path

from tools.article import TAG_LINE, TITLE
from tools.screening import pack_frames, render_media
from tools.statements import AUDITION, ON_PICTURE, PREVIEW_LINE, PROGRAM, PUBLICATION, WARNING


def write_page(path: Path, catalog: dict, report: dict, preview: dict, film: dict) -> None:
    path.write_text(render_page(catalog, report, preview, film), encoding="utf-8")
    root = path.parent
    path.with_name("media.html").write_text(render_media({
        "pack_name": catalog["pack_name"],
        "subject": (
            "The still is a set of horizontal lanes on a deep teal field. "
            "Long bars are pad notes. Short ticks are drums. A sand bar is the motif."
        ),
        "colors": {
            "bg": "#071614",
            "paper": "#e7f4f0",
            "ink": "#10221f",
            "accent": "#8fd9cc",
            "muted": "#b7ccc6",
        },
        "frames": pack_frames(root),
        "preview_seconds": preview["seconds_encoded"],
        "film_seconds": film["duration_seconds"],
    }), encoding="utf-8")


def render_page(catalog: dict, report: dict, preview: dict, film: dict) -> str:
    part_rows = []
    for part in catalog["parts"]:
        part_rows.append(
            "<tr>"
            f"<td><a href=\"{part['path']}\">{part['id']}</a></td>"
            f"<td>{part['role']}</td>"
            f"<td>{part['variation']}</td>"
            f"<td>core</td>"
            f"<td>{part['bpm']}</td>"
            f"<td>{part['container_bars']}</td>"
            f"<td>{part['notes']}</td>"
            "</tr>"
        )
    arrangement_rows = []
    for item in catalog["arrangements"]:
        arrangement_rows.append(
            "<tr>"
            f"<td><a href=\"{item['path']}\">{item['kit_id']}</a></td>"
            f"<td>{item['bpm']}</td>"
            f"<td>{item['container_bars']}</td>"
            f"<td>{item['description']}</td>"
            "</tr>"
        )
    kit_items = []
    for kit in catalog["kits"]:
        kit_items.append(
            f"<li><strong>{kit['id']} {kit['title']}</strong>, {kit['bpm']} BPM, {kit['collection_name']}, "
            f"tonic {kit['tonal_reference']}. Parts are {kit['part_bars']} bars. "
            f"The arrangement is {kit['arrangement_bars']} bars. {kit['identity']} "
            f"Limitations: {kit['limitations']}</li>"
        )
    payload = {
        "kits": [
            {
                "id": kit["id"],
                "title": kit["title"],
                "bpm": kit["bpm"],
                "bars": kit["part_bars"],
                "arrangement_bars": kit["arrangement_bars"],
                "collection": kit["collection_name"],
                "tonic": kit["tonal_reference"],
                "identity": kit["identity"],
                "limitations": kit["limitations"],
                "harmonic_rhythm": kit["harmonic_rhythm"],
                "phrases": kit["phrases"],
                "arrangement_phrases": kit["arrangement_phrases"],
                "changes": kit["changes"],
                "change_bars": kit["change_bars"],
                "tempo_us": kit["tempo_us"],
                "spell": kit["spell"],
                "departures": kit["departures"],
            }
            for kit in catalog["kits"]
        ],
        "parts": [
            {
                "id": part["id"],
                "kit_id": part["kit_id"],
                "role": part["role"],
                "variation": part["variation"],
                "path": part["path"],
            }
            for part in catalog["parts"]
        ],
        "arrangements": [
            {
                "kit_id": item["kit_id"],
                "path": item["path"],
                "bpm": item["bpm"],
                "bars": item["container_bars"],
            }
            for item in catalog["arrangements"]
        ],
        "roles": [
            {"id": "atmosphere", "label": "Atmosphere"},
            {"id": "harmonic-field", "label": "Harmonic field"},
            {"id": "motif", "label": "Motif"},
            {"id": "bass", "label": "Bass"},
            {"id": "percussion", "label": "Percussion"},
            {"id": "drums", "label": "Drums"},
        ],
    }
    data = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    seconds = f"{preview['seconds_encoded']:.2f}"
    film_seconds = f"{film['duration_seconds']:.2f}"
    html = TEMPLATE
    replacements = {
        "__DATA__": data,
        "__WARNING__": WARNING,
        "__AUDITION__": AUDITION,
        "__PROGRAM__": PROGRAM,
        "__PREVIEW_LINE__": PREVIEW_LINE,
        "__ON_PICTURE__": ON_PICTURE,
        "__PUBLICATION__": PUBLICATION,
        "__TAG_LINE__": TAG_LINE,
        "__ARTICLE_TITLE__": TITLE,
        "__RANGE__": catalog["range_statement"],
        "__DIRECTION__": catalog["creative_direction"],
        "__RESULT__": report["result"],
        "__CORE__": str(catalog["core_part_count"]),
        "__REFS__": str(catalog["reference_part_count"]),
        "__PART_ROWS__": "".join(part_rows),
        "__ARR_ROWS__": "".join(arrangement_rows),
        "__KIT_ITEMS__": "".join(kit_items),
        "__PREVIEW_SECONDS__": seconds,
        "__FILM_SECONDS__": film_seconds,
        "__PREVIEW_STATEMENT__": catalog["preview"]["statement"],
        "__REF_NOTE__": catalog["reference_note"],
    }
    for key, value in replacements.items():
        html = html.replace(key, value)
    return html


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Psybient</title>
  <style>
    :root {
      --bg: #071614;
      --paper: #e7f4f0;
      --ink: #10221f;
      --teal: #1f8a78;
      --teal-2: #8fd9cc;
      --sand: #c4a574;
      --muted: #b7ccc6;
      --line: rgba(231, 244, 240, .16);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; background: var(--bg); color: var(--paper);
      font-family: Georgia, "Iowan Old Style", Palatino, serif;
      line-height: 1.45;
    }
    a { color: var(--teal-2); }
    button, .meta, .note, .transport, .lane-label, .legend { font-family: ui-monospace, Menlo, Consolas, monospace; }
    .top {
      display: flex; justify-content: space-between; gap: 12px; align-items: center;
      padding: 12px 20px; background: #071614; border-bottom: 1px solid var(--line);
    }
    .brand { letter-spacing: .14em; text-transform: uppercase; font-size: .72rem; color: var(--paper); text-decoration: none; }
    .top nav { display: flex; gap: 14px; flex-wrap: wrap; font-size: .78rem; }
    main { width: min(1180px, calc(100% - 2rem)); margin: 0 auto; }
    .stage {
      display: grid; grid-template-columns: minmax(0, .82fr) minmax(0, 1.18fr);
      gap: 28px; align-items: start; padding: 26px 0 8px;
    }
    .stage > div { min-width: 0; }
    h1 { font-weight: 500; font-size: clamp(2.2rem, 5vw, 4.2rem); line-height: .92; margin: 8px 0 10px; }
    h2 { font-weight: 500; margin: 28px 0 8px; }
    .kicker { letter-spacing: .16em; text-transform: uppercase; color: var(--teal-2); font-size: .74rem; margin: 0; }
    .meta, .note { color: var(--muted); font-size: .82rem; }
    .hero img, audio, video, .stage img { display: block; width: 100%; height: auto; }
    .hero img { border-radius: 12px; }
    .rail, .phrases, .switch { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0; }
    button {
      border: 1px solid var(--line); background: transparent; color: var(--paper);
      border-radius: 999px; padding: 7px 11px; cursor: pointer;
    }
    button[aria-pressed="true"] { background: var(--teal); color: white; border-color: var(--teal); }
    .transport {
      display: flex; gap: 10px; flex-wrap: wrap; align-items: center;
      margin: 8px 0 12px;
    }
    .scroller { overflow-x: auto; max-width: 100%; background: transparent; color: var(--ink); }
    .roll-wrap {
      display: grid; grid-template-columns: 8.6rem minmax(0, 1fr); align-items: start;
      background: var(--paper); color: var(--ink); border-radius: 16px; padding: 8px 0 12px;
    }
    .label-col { display: flex; flex-direction: column; }
    .ruler { position: relative; height: 28px; }
    .ruler-gap { height: 28px; }
    .change {
      position: absolute; top: 4px; height: 20px; border-left: 2px solid var(--teal);
      padding-left: 5px; font-size: 11px; white-space: nowrap; overflow: hidden;
    }
    .lane-label {
      height: 78px;
      font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: #3d5c56;
      padding: 8px 8px 0 0;
    }
    .lane-notes { position: relative; height: 78px; border-top: 1px solid rgba(16, 34, 31, .12); }
    .block { position: absolute; border-radius: 3px; min-width: 3px; }
    .block.atmosphere { background: #d7ece6; }
    .block.harmonic-field { background: #1f8a78; }
    .block.motif { background: #c4a574; }
    .block.bass { background: #10221f; }
    .block.percussion { background: #4e9c8c; }
    .block.drums { background: #0c3f38; }
    .legend { display: flex; gap: 12px; flex-wrap: wrap; font-size: .75rem; color: var(--muted); }
    .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 4px; }
    .table-scroll { overflow-x: auto; max-width: 100%; }
    table { width: 100%; border-collapse: collapse; font-size: .8rem; }
    th, td { text-align: left; padding: 7px 6px; border-bottom: 1px solid var(--line); vertical-align: top; }
    .flow { display: flex; flex-wrap: wrap; gap: 8px; }
    .flow span { border: 1px solid var(--line); border-radius: 999px; padding: 4px 8px; font-size: .78rem; }
    .map { padding-left: 1.1rem; }
    .map li { margin: 0 0 10px; }
    @media (max-width: 860px) {
      .stage { grid-template-columns: 1fr; }
      .top { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <header class="top">
    <a class="brand" href="index.html">Psybient</a>
    <nav>
      <a href="#roll">Kits</a>
      <a href="#map">Map</a>
      <a href="#files">Files</a>
      <a href="#reading">Preview</a>
      <a href="media.html">Stills</a>
      <a href="midi/arrangement.mid">Arrangement</a>
    </nav>
  </header>
  <main>
    <section class="stage">
      <div>
        <p class="kicker">Four kits · two variations · 32-bar arrangements</p>
        <h1 id="title">Low Water</h1>
        <p id="identity"></p>
        <p class="meta" id="facts"></p>
        <p id="rhythm"></p>
        <p class="note" id="limits"></p>
        <p class="note" id="departures"></p>
        <p>__DIRECTION__</p>
      </div>
      <div id="roll">
        <figure class="hero">
          <img src="art/hero.jpg" width="1280" height="720" alt="Illustration of horizontal lanes on a deep teal field, with long pad bars and short drum ticks. Not a photograph of a studio or of performers.">
          <figcaption class="note">Illustration of lanes. Not a photograph of a session or of performers.</figcaption>
        </figure>
        <div class="rail" id="rail" role="tablist" aria-label="Kits"></div>
        <div class="switch">
          <button type="button" id="var-a" aria-pressed="true">Variation A</button>
          <button type="button" id="var-b" aria-pressed="false">Variation B</button>
          <button type="button" id="view-kit" aria-pressed="true">8-bar kit</button>
          <button type="button" id="view-arr" aria-pressed="false">32-bar arrangement</button>
        </div>
        <div class="phrases" id="phrases"></div>
        <div class="transport">
          <button type="button" id="play">Play lanes</button>
          <span id="transport-label">Space plays. J and K change kit.</span>
        </div>
        <div class="roll-wrap">
          <div class="label-col" id="label-col"></div>
          <div class="scroller" id="scroller">
            <div class="ruler" id="ruler"></div>
            <div id="lanes"></div>
          </div>
        </div>
        <p class="legend">
          <span><i class="swatch" style="background:#d7ece6"></i>atmosphere</span>
          <span><i class="swatch" style="background:#1f8a78"></i>harmonic field</span>
          <span><i class="swatch" style="background:#c4a574"></i>motif</span>
          <span><i class="swatch" style="background:#10221f"></i>bass</span>
          <span><i class="swatch" style="background:#4e9c8c"></i>percussion</span>
          <span><i class="swatch" style="background:#0c3f38"></i>drums</span>
        </p>
        <p class="note" id="status">Reading the MIDI.</p>
      </div>
    </section>
    <p>__RANGE__</p>
    <h2 id="map">Kit map</h2>
    <ul class="map">__KIT_ITEMS__</ul>
    <p>__REF_NOTE__ Variation A of each role has its own attack pattern. The four kits are not transpositions of one phrase.</p>
    <div class="flow" aria-label="File contract">
      <span>Score</span><span>MIDI</span><span>Reopened validation</span><span>MP3</span><span>Film</span><span>Stills</span><span>Drafts</span><span>Catalog</span>
    </div>
    <p class="note"><a href="articles/medium-draft-Cursor.md">Article draft</a> · <a href="articles/medium-paste-Cursor.txt">plain text</a></p>
    <h2>Article draft</h2>
    <p>DRAFT. __ARTICLE_TITLE__</p>
    <p>__TAG_LINE__</p>
    <p>__WARNING__</p>
    <h2 id="files">Files</h2>
    <p class="meta">Validation __RESULT__. Core __CORE__. Reference __REFS__. <a href="midi/validation-Cursor.json">validation report</a> · <a href="catalog/catalog-Cursor.json">catalog</a> · <a href="score/canonical-score-Cursor.json">canonical score</a></p>
    <div class="table-scroll">
      <table>
        <thead><tr><th>Part</th><th>Role</th><th>Var</th><th>Count</th><th>BPM</th><th>Bars</th><th>Notes</th></tr></thead>
        <tbody>__PART_ROWS__</tbody>
      </table>
    </div>
    <h2>Arrangements</h2>
    <div class="table-scroll">
      <table>
        <thead><tr><th>Kit</th><th>BPM</th><th>Bars</th><th>What the file contains</th></tr></thead>
        <tbody>__ARR_ROWS__</tbody>
      </table>
    </div>
    <section id="reading">
      <p class="kicker">Recorded reading</p>
      <p>__PREVIEW_STATEMENT__ The encoded MP3 is __PREVIEW_SECONDS__ seconds. __PREVIEW_LINE__. The film is __FILM_SECONDS__ seconds and shows __ON_PICTURE__.</p>
      <audio controls preload="metadata" src="preview/preview.mp3"></audio>
      <p><a href="preview/preview.mp3">preview/preview.mp3</a> · <a href="preview/preview-manifest-Cursor.txt">preview manifest</a></p>
      <video controls preload="metadata" poster="film/poster.jpg" width="1280" height="720">
        <source src="film/preview.mp4" type="video/mp4">
        <track kind="captions" src="film/preview.vtt" srclang="en" label="English" default>
      </video>
      <p><a href="film/preview.mp4">film/preview.mp4</a> · <a href="film/preview.vtt">film/preview.vtt</a> · <a href="media.html">stills</a></p>
    </section>
    <p>__PROGRAM__</p>
    <p>__AUDITION__</p>
    <p>__PUBLICATION__</p>
  </main>
  <script id="pack" type="application/json">__DATA__</script>
  <script>
    const pack = JSON.parse(document.getElementById("pack").textContent);
    const rail = document.getElementById("rail");
    const phrases = document.getElementById("phrases");
    const scroller = document.getElementById("scroller");
    const ruler = document.getElementById("ruler");
    const lanes = document.getElementById("lanes");
    const labelCol = document.getElementById("label-col");
    const status = document.getElementById("status");
    let kitId = "k01";
    let variation = "a";
    let view = "kit";
    let laneNotes = {};
    let audio = null;
    let playing = false;
    let followId = 0;
    let rollWidth = 1120;

    function kit() {
      return pack.kits.find((item) => item.id === kitId);
    }
    function pitchName(pitch) {
      return kit().spell[pitch % 12] + String(Math.floor(pitch / 12) - 1);
    }
    function readVlq(viewBytes, offset) {
      let value = 0;
      let byte = 0;
      do {
        byte = viewBytes.getUint8(offset);
        offset += 1;
        value = (value << 7) | (byte & 0x7f);
      } while (byte & 0x80);
      return [value, offset];
    }
    function parseMidi(buffer) {
      const viewBytes = new DataView(buffer);
      const head = String.fromCharCode(viewBytes.getUint8(0), viewBytes.getUint8(1), viewBytes.getUint8(2), viewBytes.getUint8(3));
      if (head !== "MThd" || viewBytes.getUint16(12) !== 960) throw new Error("unexpected MIDI header");
      const tracks = viewBytes.getUint16(10);
      let offset = 14;
      const parsed = [];
      for (let trackIndex = 0; trackIndex < tracks; trackIndex += 1) {
        const mark = String.fromCharCode(viewBytes.getUint8(offset), viewBytes.getUint8(offset + 1), viewBytes.getUint8(offset + 2), viewBytes.getUint8(offset + 3));
        if (mark !== "MTrk") throw new Error("missing track");
        const length = viewBytes.getUint32(offset + 4);
        offset += 8;
        const end = offset + length;
        let tick = 0;
        let running = 0;
        let name = "";
        const open = new Map();
        const notes = [];
        while (offset < end) {
          let delta;
          [delta, offset] = readVlq(viewBytes, offset);
          tick += delta;
          let byte = viewBytes.getUint8(offset);
          if (byte >= 0x80) {
            running = byte;
            offset += 1;
          }
          if (running === 0xff) {
            const metaType = viewBytes.getUint8(offset);
            offset += 1;
            let metaLen;
            [metaLen, offset] = readVlq(viewBytes, offset);
            if (metaType === 0x03) {
              name = "";
              for (let index = 0; index < metaLen; index += 1) name += String.fromCharCode(viewBytes.getUint8(offset + index));
            }
            offset += metaLen;
            continue;
          }
          const kind = running & 0xf0;
          const data1 = byte < 0x80 ? byte : viewBytes.getUint8(offset);
          if (byte >= 0x80) offset += 1;
          let data2 = 0;
          if (kind !== 0xc0 && kind !== 0xd0) {
            data2 = viewBytes.getUint8(offset);
            offset += 1;
          }
          const key = (running & 0x0f) + ":" + data1;
          if (kind === 0x90 && data2 > 0) open.set(key, { tick: tick, velocity: data2 });
          else if (kind === 0x80 || (kind === 0x90 && data2 === 0)) {
            const started = open.get(key);
            if (started) {
              notes.push({ pitch: data1, start: started.tick, duration: tick - started.tick, velocity: started.velocity });
              open.delete(key);
            }
          }
        }
        notes.sort((a, b) => a.start - b.start || a.pitch - b.pitch);
        parsed.push({ name: name, notes: notes });
      }
      return parsed;
    }
    function partPath(role) {
      const found = pack.parts.find((part) => part.kit_id === kitId && part.role === role && part.variation === variation);
      if (!found) throw new Error("missing " + role);
      return found.path;
    }
    function arrangementPath() {
      const found = pack.arrangements.find((item) => item.kit_id === kitId);
      if (!found) throw new Error("missing arrangement");
      return found.path;
    }
    function renderCopy() {
      const item = kit();
      document.getElementById("title").textContent = item.title;
      document.getElementById("identity").textContent = item.identity;
      const bars = view === "arrangement" ? item.arrangement_bars : item.bars;
      document.getElementById("facts").textContent = item.id + " · " + item.bpm + " BPM · " + bars + " bars on screen · " + item.collection + " · tonic " + item.tonic;
      document.getElementById("rhythm").textContent = item.harmonic_rhythm;
      document.getElementById("limits").textContent = item.limitations;
      document.getElementById("departures").textContent = item.departures.length ? item.departures.join(" ") : "No pitched note in this kit is flagged as a departure.";
      const mode = view === "arrangement" ? "arrangement A" : "variation " + variation.toUpperCase();
      document.getElementById("transport-label").textContent = item.title + " " + mode + " · Space plays · J and K change kit";
      for (const button of rail.querySelectorAll("button")) button.setAttribute("aria-pressed", button.dataset.id === kitId ? "true" : "false");
      document.getElementById("var-a").setAttribute("aria-pressed", view === "kit" && variation === "a" ? "true" : "false");
      document.getElementById("var-b").setAttribute("aria-pressed", view === "kit" && variation === "b" ? "true" : "false");
      document.getElementById("view-kit").setAttribute("aria-pressed", view === "kit" ? "true" : "false");
      document.getElementById("view-arr").setAttribute("aria-pressed", view === "arrangement" ? "true" : "false");
      phrases.innerHTML = "";
      const phraseList = view === "arrangement" ? item.arrangement_phrases : item.phrases;
      phraseList.forEach((phrase) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = phrase.name;
        button.addEventListener("click", () => {
          const x = (phrase.start_bar / bars) * rollWidth;
          scroller.scrollTo({ left: Math.max(0, x - 12), behavior: "smooth" });
        });
        phrases.appendChild(button);
      });
    }
    function drawLane(host, notes, role, bars) {
      host.querySelectorAll(".block").forEach((node) => node.remove());
      const container = bars * 4 * 960;
      if (!notes.length) {
        const empty = document.createElement("div");
        empty.className = "block";
        empty.textContent = "";
        return;
      }
      const low = Math.min(...notes.map((note) => note.pitch));
      const high = Math.max(...notes.map((note) => note.pitch));
      const span = Math.max(1, high - low);
      notes.forEach((note) => {
        const block = document.createElement("div");
        block.className = "block " + role;
        block.title = pitchName(note.pitch) + " · velocity " + note.velocity;
        const y = 16 + (1 - (note.pitch - low) / span) * 46;
        block.style.left = (note.start / container) * rollWidth + "px";
        block.style.width = Math.max(3, (note.duration / container) * rollWidth - 1) + "px";
        block.style.top = y + "px";
        block.style.height = (6 + (note.velocity / 127) * 14) + "px";
        host.appendChild(block);
      });
    }
    function draw() {
      const item = kit();
      const bars = view === "arrangement" ? item.arrangement_bars : item.bars;
      rollWidth = Math.max(960, bars * 150);
      ruler.style.width = rollWidth + "px";
      ruler.innerHTML = "";
      let bar = 0;
      item.changes.forEach((name, index) => {
        const span = item.change_bars[index];
        if (view === "arrangement") {
          for (let copy = 0; copy < item.arrangement_bars; copy += item.bars) {
            const mark = document.createElement("div");
            mark.className = "change";
            mark.textContent = name;
            mark.style.left = ((copy + bar) / bars) * rollWidth + "px";
            mark.style.width = (span / bars) * rollWidth + "px";
            ruler.appendChild(mark);
          }
        } else {
          const mark = document.createElement("div");
          mark.className = "change";
          mark.textContent = name;
          mark.style.left = (bar / item.bars) * rollWidth + "px";
          mark.style.width = (span / item.bars) * rollWidth + "px";
          ruler.appendChild(mark);
        }
        bar += span;
      });
      lanes.innerHTML = "";
      labelCol.innerHTML = "";
      const gap = document.createElement("div");
      gap.className = "ruler-gap";
      labelCol.appendChild(gap);
      let total = 0;
      pack.roles.forEach((role) => {
        const label = document.createElement("div");
        label.className = "lane-label";
        label.textContent = role.label;
        labelCol.appendChild(label);
        const notesHost = document.createElement("div");
        notesHost.className = "lane-notes";
        notesHost.style.width = rollWidth + "px";
        const notes = laneNotes[role.id] || [];
        total += notes.length;
        drawLane(notesHost, notes, role.id, bars);
        lanes.appendChild(notesHost);
      });
      const source = view === "arrangement" ? "arrangement file" : "part files";
      status.textContent = total + " notes across " + pack.roles.length + " lanes, read from the " + source + ".";
    }
    async function loadKit() {
      stopPlayback();
      renderCopy();
      status.textContent = "Reading the MIDI.";
      laneNotes = {};
      try {
        if (view === "kit") {
          for (const role of pack.roles) {
            const response = await fetch(partPath(role.id));
            if (!response.ok) throw new Error(role.id + " request failed");
            const tracks = parseMidi(await response.arrayBuffer());
            laneNotes[role.id] = tracks[0].notes;
          }
        } else {
          const response = await fetch(arrangementPath());
          if (!response.ok) throw new Error("arrangement request failed");
          const tracks = parseMidi(await response.arrayBuffer());
          const byName = {};
          tracks.forEach((track) => { byName[track.name] = track.notes; });
          pack.roles.forEach((role) => {
            const name = role.label === "Harmonic field" ? "Harmonic Field" : role.label;
            laneNotes[role.id] = byName[name] || [];
          });
        }
        draw();
      } catch (error) {
        laneNotes = {};
        lanes.innerHTML = "";
        status.textContent = "The MIDI did not load. " + error.message;
      }
    }
    function freq(pitch) {
      return 440 * Math.pow(2, (pitch - 69) / 12);
    }
    function scheduleTone(ctx, note, origin, secondsOf, type, amount, attack) {
      const when = origin + secondsOf(note.start);
      const duration = Math.max(0.05, secondsOf(note.duration));
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type;
      osc.frequency.value = freq(note.pitch);
      const level = amount * (note.velocity / 110);
      gain.gain.setValueAtTime(0.0001, when);
      gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, level), when + Math.min(attack, duration * 0.4));
      gain.gain.exponentialRampToValueAtTime(0.0001, when + duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(when);
      osc.stop(when + duration + 0.02);
    }
    function scheduleNoise(ctx, note, origin, secondsOf, amount, decay) {
      const when = origin + secondsOf(note.start);
      const duration = Math.max(0.03, Math.min(0.4, secondsOf(note.duration)));
      const count = Math.max(1, Math.floor(ctx.sampleRate * duration));
      const buffer = ctx.createBuffer(1, count, ctx.sampleRate);
      const data = buffer.getChannelData(0);
      let state = note.pitch * 17 + note.start;
      for (let index = 0; index < count; index += 1) {
        state = (1103515245 * state + 12345) & 0x7fffffff;
        const noise = state / 0x7fffffff * 2 - 1;
        data[index] = noise * Math.exp(-decay * index / ctx.sampleRate);
      }
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      const gain = ctx.createGain();
      gain.gain.value = amount * (note.velocity / 110);
      source.connect(gain);
      gain.connect(ctx.destination);
      source.start(when);
    }
    function schedule(ctx, note, origin, secondsOf, role) {
      if (role === "drums") {
        if (note.pitch === 36) scheduleTone(ctx, note, origin, secondsOf, "sine", 0.12, 0.005);
        else scheduleNoise(ctx, note, origin, secondsOf, 0.05, note.pitch === 46 ? 8 : 30);
        return;
      }
      if (role === "percussion") {
        if (note.pitch === 75 || note.pitch === 76 || note.pitch === 63 || note.pitch === 64) {
          scheduleTone(ctx, note, origin, secondsOf, "triangle", 0.05, 0.004);
        } else scheduleNoise(ctx, note, origin, secondsOf, 0.04, 24);
        return;
      }
      if (role === "bass") scheduleTone(ctx, note, origin, secondsOf, "sine", 0.09, 0.01);
      else if (role === "motif") scheduleTone(ctx, note, origin, secondsOf, "triangle", 0.05, 0.012);
      else if (role === "harmonic-field") scheduleTone(ctx, note, origin, secondsOf, "sine", 0.03, 0.03);
      else scheduleTone(ctx, note, origin, secondsOf, "sine", 0.02, 0.08);
    }
    function stopPlayback() {
      playing = false;
      cancelAnimationFrame(followId);
      if (audio) audio.close();
      audio = null;
      document.getElementById("play").textContent = "Play lanes";
    }
    function playLanes() {
      const notes = pack.roles.flatMap((role) => (laneNotes[role.id] || []).map((note) => ({ note: note, role: role.id })));
      if (!notes.length) return;
      stopPlayback();
      const ctx = new AudioContext();
      audio = ctx;
      playing = true;
      document.getElementById("play").textContent = "Stop";
      const item = kit();
      const secondsOf = (tick) => tick / 960 * item.tempo_us / 1000000;
      const origin = ctx.currentTime + 0.05;
      notes.forEach((itemNote) => schedule(ctx, itemNote.note, origin, secondsOf, itemNote.role));
      const bars = view === "arrangement" ? item.arrangement_bars : item.bars;
      const container = bars * 4 * item.tempo_us / 1000000;
      const follow = () => {
        if (!playing || !audio) return;
        if (audio.currentTime - origin < container) followId = requestAnimationFrame(follow);
        else stopPlayback();
      };
      follow();
    }
    function stepKit(direction) {
      const index = pack.kits.findIndex((item) => item.id === kitId);
      kitId = pack.kits[(index + direction + pack.kits.length) % pack.kits.length].id;
      loadKit();
    }
    pack.kits.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.id = item.id;
      button.textContent = item.id + " " + item.title;
      button.addEventListener("click", () => { kitId = item.id; loadKit(); });
      rail.appendChild(button);
    });
    document.getElementById("var-a").addEventListener("click", () => { variation = "a"; if (view === "arrangement") view = "kit"; loadKit(); });
    document.getElementById("var-b").addEventListener("click", () => { variation = "b"; if (view === "arrangement") view = "kit"; loadKit(); });
    document.getElementById("view-kit").addEventListener("click", () => { view = "kit"; loadKit(); });
    document.getElementById("view-arr").addEventListener("click", () => { view = "arrangement"; loadKit(); });
    document.getElementById("play").addEventListener("click", () => { if (playing) stopPlayback(); else playLanes(); });
    window.addEventListener("keydown", (event) => {
      const tag = document.activeElement && document.activeElement.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (event.target && event.target.closest && event.target.closest("video, audio")) return;
      if (event.code === "Space") {
        event.preventDefault();
        if (playing) stopPlayback(); else playLanes();
      } else if (event.key === "j" || event.key === "J") stepKit(-1);
      else if (event.key === "k" || event.key === "K") stepKit(1);
    });
    loadKit();
  </script>
</body>
</html>
"""
