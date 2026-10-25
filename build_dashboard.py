#!/usr/bin/env python3
"""Build the KAI task dashboard from the markdown task files.

Reads:
    tasks/personal-tasks.md
    tasks/cytron-tasks.md
Writes:
    index.html   (repo root — self-contained single file, no network)

Statuses can be changed IN THE PAGE (Edit mode). Changes live in
localStorage; "Simpan ke Markdown" prints the updated .md so they can be
committed back to the source files.

Run:  python3 build_dashboard.py
"""
import json
import re
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
TASKS_DIR = REPO_ROOT / "tasks"
OUT_DIR = REPO_ROOT
OUT = REPO_ROOT / "index.html"

FILES = ["personal-tasks.md", "cytron-tasks.md"]
BUCKET_OF = {"personal-tasks.md": "Personal", "cytron-tasks.md": "Cytron"}

STATUS_LABEL = {
    "⏳": "Pending",
    "🔄": "In Progress",
    "✅": "Done",
    "⏸️": "On Hold",
    "🔜": "Upcoming",
}
STATUS_CLASS = {
    "⏳": "pending",
    "🔄": "progress",
    "✅": "done",
    "⏸️": "hold",
    "🔜": "upcoming",
}


def parse_tables(md_text: str):
    """Return [(section_title, kind, [ [cells...], ... ]), ...]."""
    sections = []
    current_title = None
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^#{2,3} ", line):
            current_title = re.sub(r"^#{2,3} ", "", line).strip()
        elif line.strip().startswith("|") and current_title:
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            rows = []
            for row in block:
                if re.match(r"^\|[\s:\-|]+\|$", row):  # separator
                    continue
                cells = [c.strip() for c in row.strip("|").split("|")]
                rows.append(cells)
            if rows:
                sections.append((current_title, "table", rows))
            continue
        elif line.startswith("> ") and current_title and not sections:
            sections.append((current_title, "note", line[2:].strip()))
        i += 1
    return sections


def status_of(cells):
    joined = " ".join(cells)
    for k in STATUS_LABEL:
        if k in joined:
            return k
    low = joined.lower()
    if "in progress" in low or "ongoing" in low or "dah start" in low:
        return "🔄"
    if "done" in low or "settled" in low:
        return "✅"
    return ""


def build_data():
    sources = {}
    groups = []
    for name in FILES:
        text = (TASKS_DIR / name).read_text(encoding="utf-8")
        sources[name] = text
        groups.append((BUCKET_OF[name], name, text))

    sections = []
    counters = {"pending": 0, "progress": 0, "done": 0, "hold": 0, "upcoming": 0, "total": 0}

    for bucket, path, text in groups:
        for title, kind, payload in parse_tables(text):
            if kind == "note":
                continue
            header = payload[0]
            rows = []
            for cells in payload[1:]:
                if not any(cells):
                    continue
                st = status_of(cells)
                if not st:
                    # section title carries the status (e.g. "## ✅ Done")
                    st = status_of([title])
                cls = STATUS_CLASS.get(st, "")
                if cls:
                    counters[cls] += 1
                    counters["total"] += 1
                rows.append({"cells": cells, "status": cls, "status_label": STATUS_LABEL.get(st, "")})
            if not rows:
                continue
            sections.append(
                {
                    "bucket": bucket,
                    "file": path,
                    "title": title,
                    "header": header,
                    "rows": rows,
                    "default": STATUS_CLASS.get(status_of([title]), ""),
                }
            )

    return {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "counters": counters,
        "sections": sections,
        "_sources": sources,
    }

TEMPLATE = r"""<!DOCTYPE html>
<html lang="ms">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KAI — Task Dashboard</title>
<style>
  :root{
    --bg:#0b0e14; --panel:#141a24; --panel2:#1b2331; --line:#263145;
    --txt:#e6edf7; --dim:#8b9bb4; --accent:#4ade80; --accent2:#38bdf8;
    --pend:#f59e0b; --prog:#38bdf8; --done:#4ade80; --hold:#f472b6;
    --radius:14px;
  }
  *{box-sizing:border-box}
  body{
    margin:0; background:var(--bg); color:var(--txt);
    font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    padding:28px 20px 60px;
  }
  .wrap{max-width:1180px; margin:0 auto}
  header{display:flex; flex-wrap:wrap; align-items:baseline; gap:12px; margin-bottom:18px}
  h1{font-size:26px; margin:0; letter-spacing:-.4px}
  h1 span{color:var(--accent)}
  .stamp{color:var(--dim); font-size:12.5px}
  .controls{display:flex; gap:8px; margin:16px 0 26px; flex-wrap:wrap}
  .btn{
    background:var(--panel); border:1px solid var(--line); color:var(--dim);
    padding:7px 13px; border-radius:999px; cursor:pointer; font-size:13px;
  }
  .btn:hover{color:var(--txt); border-color:var(--accent2)}
  .btn.on{background:var(--accent2); border-color:var(--accent2); color:#04121c; font-weight:600}
  .btn.act{border-color:var(--accent); color:var(--accent); background:var(--panel2); font-weight:600}
  .btn[disabled]{opacity:.45; cursor:not-allowed}
  .stats{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin-bottom:26px}
  .stat{background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); padding:14px 16px}
  .stat .n{font-size:28px; font-weight:700; letter-spacing:-1px}
  .stat .l{color:var(--dim); font-size:12.5px; margin-top:2px}
  .stat.pending .n{color:var(--pend)} .stat.progress .n{color:var(--prog)}
  .stat.done .n{color:var(--done)} .stat.hold .n{color:var(--hold)}
  .stat.upcoming .n{color:#c4b5fd}
  h2{font-size:13px; text-transform:uppercase; letter-spacing:1.2px; color:var(--dim);
     margin:26px 0 10px; display:flex; align-items:center; gap:9px}
  h2 .tag{background:var(--panel2); border:1px solid var(--line); border-radius:6px;
           padding:2px 8px; font-size:11.5px; letter-spacing:0; text-transform:none; color:var(--accent2)}
  .card{background:var(--panel); border:1px solid var(--line); border-radius:var(--radius);
        overflow:hidden; margin-bottom:14px}
  .card .head{padding:13px 16px; background:var(--panel2); border-bottom:1px solid var(--line);
              display:flex; justify-content:space-between; gap:10px; align-items:center; flex-wrap:wrap}
  .card .head .t{font-weight:600; font-size:14.5px}
  .card .head .c{color:var(--dim); font-size:12.5px}
  .bar{height:3px; background:var(--line)}
  .bar i{display:block; height:100%; background:var(--accent2); width:0; transition:width .5s}
  table{width:100%; border-collapse:collapse}
  th,td{padding:10px 16px; text-align:left; font-size:13.5px; vertical-align:top}
  th{color:var(--dim); font-size:11.5px; text-transform:uppercase; letter-spacing:.8px; font-weight:600}
  tbody tr{border-top:1px solid var(--line)}
  tbody tr:hover{background:#18202e}
  td.num{color:var(--dim); width:44px; font-variant-numeric:tabular-nums}
  td.notes{color:var(--dim)}
  .pill{display:inline-block; padding:2px 9px; border-radius:999px; font-size:11.5px; font-weight:600; white-space:nowrap}
  .pill.pending{background:#3a2c10; color:var(--pend)}
  .pill.progress{background:#0f2a3d; color:var(--prog)}
  .pill.done{background:#12351f; color:var(--done)}
  .pill.hold{background:#371626; color:var(--hold)}
  .pill.upcoming{background:#2b1e44; color:#c4b5fd}
  .pill.none{background:var(--panel2); color:var(--dim); font-weight:500}
  /* --- editor --- */
  .editmode .statuscell{cursor:pointer; outline:1px dashed var(--line); outline-offset:-1px}
  .editmode .statuscell:hover{outline-color:var(--accent2); background:#14202f}
  .editmode .statuscell:focus-visible{outline:2px solid var(--accent2); outline-offset:-2px}
  .picker{background:var(--panel2); border:1px solid var(--line); border-radius:10px;
          padding:8px; display:inline-flex; gap:6px; flex-wrap:wrap; max-width:430px}
  .pick{background:var(--panel); border:1px solid var(--line); color:var(--dim);
        padding:5px 11px; border-radius:999px; cursor:pointer; font-size:12.5px; font-weight:600}
  .pick:hover{color:var(--txt); border-color:var(--accent2)}
  .pick.on{color:#04121c; font-weight:700}
  .pick.on.pending{background:var(--pend); border-color:var(--pend)}
  .pick.on.progress{background:var(--prog); border-color:var(--prog)}
  .pick.on.done{background:var(--done); border-color:var(--done)}
  .pick.on.hold{background:var(--hold); border-color:var(--hold)}
  .pick.on.upcoming{background:#c4b5fd; border-color:#c4b5fd}
  .editbar{display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin:0 0 18px}
  .note{color:var(--dim); font-size:12.5px}
  #toast{position:fixed; left:50%; bottom:26px; transform:translateX(-50%) translateY(14px);
          background:var(--panel2); border:1px solid var(--line); color:var(--txt);
          padding:10px 16px; border-radius:10px; font-size:13px; opacity:0;
          transition:opacity .2s, transform .2s; pointer-events:none; max-width:90vw}
  #toast.show{opacity:1; transform:translateX(-50%) translateY(0)}
  #diffbar{display:none; background:#0a0f18; border:1px solid var(--line);
           border-radius:10px; padding:12px 14px; margin:0 0 26px; font-size:12px;
           font-family:ui-monospace,SFMono-Regular,Menlo,monospace; white-space:pre-wrap;
           max-height:240px; overflow:auto; color:var(--dim)}
  #diffbar.show{display:block}
  #diffbar .fh{color:var(--accent2); font-weight:700}
  footer{color:var(--dim); font-size:12.5px; margin-top:30px; text-align:center}
  @media (max-width:640px){
    body{padding:18px 12px 40px}
    th,td{padding:9px 10px; font-size:12.5px}
    .card .head .t{font-size:13.5px}
  }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>KAI <span>//</span> Task Dashboard</h1>
    <span class="stamp" id="stamp"></span>
  </header>

  <div class="editbar">
    <button class="btn" id="editToggle" type="button">✏️ Edit Status</button>
    <button class="btn act" id="saveMd" type="button" disabled>💾 Simpan ke Markdown</button>
    <span class="note" id="editNote">Klik “Edit Status”, kemudian klik mana-mana sel status untuk tukar.</span>
  </div>

  <div id="diffbar"></div>
  <div class="stats" id="stats"></div>

  <div class="controls" id="controls">
    <button class="btn on" data-f="all">Semua</button>
    <button class="btn" data-f="pending">⏳ Pending</button>
    <button class="btn" data-f="progress">🔄 In Progress</button>
    <button class="btn" data-f="hold">⏸️ On Hold</button>
    <button class="btn" data-f="done">✅ Done</button>
  </div>

  <main id="sections"></main>

  <footer>
    Sumber: <code>personal-tasks.md</code> &amp; <code>cytron-tasks.md</code> ·
    Tukar status terus dalam dashboard (tersimpan dalam localStorage), atau edit fail .md
    dan jalan semula <code>build_dashboard.py</code>.
  </footer>
</div>

<div id="toast"></div>

<script>
const DATA = __DATA__;

document.getElementById('stamp').textContent = 'Dikemaskini: ' + DATA.generated;

const STORE_KEY = 'kai-task-status-v1';
const STATUS_KEYS = ['pending', 'progress', 'done', 'hold', 'upcoming'];
const STATUS_ICON = {pending:'⏳', progress:'🔄', done:'✅', hold:'⏸️', upcoming:'🔜'};
const STATUS_LABEL = {pending:'Pending', progress:'In Progress', done:'Done', hold:'On Hold', upcoming:'Upcoming'};
const STATUS_MD = {pending:'⏳', progress:'🔄', done:'✅', hold:'⏸️', upcoming:'🔜', none:'—'};
const ICON_TO_KEY = {'⏳':'pending','🔄':'progress','✅':'done','⏸️':'hold','🔜':'upcoming'};

// ---------- change log (localStorage) ----------
const loadLog = () => { try { return JSON.parse(localStorage.getItem(STORE_KEY) || '{}'); } catch(e){ return {}; } };
const saveLog = o => { try { localStorage.setItem(STORE_KEY, JSON.stringify(o)); } catch(e){} };
let changeLog = loadLog();

function hashCode(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) { h = (h * 31 + s.charCodeAt(i)) | 0; }
  return Math.abs(h);
}

const SECTION_INDEX = {};
DATA.sections.forEach(s => { SECTION_INDEX[s.bucket + '||' + s.title] = s; });

function statusCol(sec) {
  return sec.header.findIndex(h => /status/i.test(h));
}

function keyOf(bucket, title, idx) { return bucket + '||' + title + '||' + idx; }

function origStatus(bucket, title, idx) {
  const sec = SECTION_INDEX[bucket + '||' + title];
  if (!sec || !sec.rows[idx]) return null;
  const cells = sec.rows[idx].cells;
  const stIdx = statusCol(sec);
  let fromCell = null;
  if (stIdx >= 0) {
    fromCell = normStatus(cells[stIdx]);
  }
  if (!fromCell) {
    // No Status column (or an empty one): scan every cell, like the Python build
    // does — e.g. "🔄 In Progress" written inside the Nota column.
    for (const c of cells) {
      fromCell = normStatus(c);
      if (fromCell) break;
    }
  }
  // Rows whose cell is empty inherit the section's status (e.g. "## ✅ Done").
  return fromCell || sec.default || null;
}

function resolveStatus(bucket, title, idx) {
  const k = keyOf(bucket, title, idx);
  if (changeLog[k]) return changeLog[k];
  return origStatus(bucket, title, idx);
}

function normStatus(v) {
  if (v == null) return null;
  const s = String(v).trim();
  if (s === '' || s === '—' || s === '-' || s === 'none') return null;
  if (STATUS_KEYS.includes(s)) return s;
  const m = s.match(/^(⏳|🔄|✅|⏸️|🔜)/);
  if (m) return ICON_TO_KEY[m[1]];
  const low = s.toLowerCase();
  for (const k of STATUS_KEYS) if (low.includes(STATUS_LABEL[k].toLowerCase())) return k;
  return null;
}

function hasChanges() { return Object.keys(changeLog).length > 0; }

// ---------- edit mode ----------
let editMode = false;
let openPicker = null;

const editToggle = document.getElementById('editToggle');
const saveBtn = document.getElementById('saveMd');
const editNote = document.getElementById('editNote');
const toastEl = document.getElementById('toast');
const diffbar = document.getElementById('diffbar');

function toast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  clearTimeout(toastEl._t);
  toastEl._t = setTimeout(() => toastEl.classList.remove('show'), 2400);
}

function closePicker() {
  if (!openPicker) return;
  const td = document.getElementById('sc-' + openPicker.cellId);
  if (td) td.innerHTML = pillHtml(openPicker.status);
  openPicker = null;
}

function openPickerFor(td) {
  if (!editMode) return;
  closePicker();
  const bucket = td.dataset.bucket, title = td.dataset.title, idx = +td.dataset.idx;
  const cur = resolveStatus(bucket, title, idx);
  td.innerHTML = '<span class="picker" role="group" aria-label="Pilih status">' +
    STATUS_KEYS.map(k =>
      `<button type="button" class="pick ${k}${k === cur ? ' on' : ''}" data-k="${k}">${STATUS_ICON[k]} ${STATUS_LABEL[k]}</button>`
    ).join('') +
    '<button type="button" class="pick" data-k="none">— Tiada</button></span>';
  openPicker = {bucket, title, idx, cellId: td.dataset.cellId, status: cur};
  td.querySelector('.picker').addEventListener('click', e => {
    const b = e.target.closest('.pick'); if (!b) return;
    applyStatus(b.dataset.k === 'none' ? null : b.dataset.k);
  });
}

function applyStatus(status) {
  const p = openPicker;
  if (!p) return;
  const k = keyOf(p.bucket, p.title, p.idx);
  const before = resolveStatus(p.bucket, p.title, p.idx);
  if (status === before) { closePicker(); return; }
  if (status) changeLog[k] = status; else delete changeLog[k];
  saveLog(changeLog);
  openPicker = null;
  renderAll();
  saveBtn.disabled = !hasChanges();
  toast(status ? ('Ditukar kepada ' + STATUS_ICON[status] + ' ' + STATUS_LABEL[status])
               : 'Status dibuang');
}

editToggle.addEventListener('click', () => {
  editMode = !editMode;
  document.body.classList.toggle('editmode', editMode);
  editToggle.classList.toggle('on', editMode);
  editToggle.textContent = editMode ? '✏️ Edit: ON' : '✏️ Edit Status';
  editNote.textContent = editMode
    ? 'Klik mana-mana sel status untuk tukar. Tekan butang yang sama untuk tamat.'
    : 'Klik “Edit Status”, kemudian klik mana-mana sel status untuk tukar.';
  closePicker();
  renderAll();
});

document.addEventListener('click', e => {
  if (openPicker && !e.target.closest('.statuscell') && !e.target.closest('.picker')) closePicker();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') closePicker(); });

// ---------- rendering ----------
function computeCounters() {
  const c = {pending:0, progress:0, done:0, hold:0, upcoming:0, total:0};
  DATA.sections.forEach(sec => {
    sec.rows.forEach((r, idx) => {
      const st = resolveStatus(sec.bucket, sec.title, idx);
      if (st) { c[st]++; c.total++; }
    });
  });
  return c;
}

function renderStats() {
  const c = computeCounters();
  const cards = [
    {k:'pending', n:c.pending, l:'Pending', cls:'pending'},
    {k:'progress', n:c.progress, l:'In Progress', cls:'progress'},
    {k:'done', n:c.done, l:'Done', cls:'done'},
    {k:'hold', n:c.hold, l:'On Hold', cls:'hold'},
    {k:'upcoming', n:c.upcoming, l:'Upcoming', cls:'upcoming'},
    {k:'total', n:c.total, l:'Jumlah', cls:''},
  ];
  document.getElementById('stats').innerHTML = cards.map(x =>
    `<div class="stat ${x.cls}"><div class="n">${x.n}</div><div class="l">${x.l}</div></div>`
  ).join('');
}

function pillHtml(st) {
  if (!st) return '<span class="pill none">—</span>';
  return `<span class="pill ${st}">${STATUS_ICON[st]} ${STATUS_LABEL[st]}</span>`;
}

function escAttr(s) {
  return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;')
                  .replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function renderSections(filter) {
  const host = document.getElementById('sections');
  let lastBucket = null;
  let html = '';
  DATA.sections.forEach(sec => {
    const shown = [];
    sec.rows.forEach((r, idx) => {
      const st = resolveStatus(sec.bucket, sec.title, idx);
      if (filter !== 'all' && st !== filter) return;
      shown.push({idx, cells: r.cells, status: st});
    });
    if (!shown.length) return;
    if (sec.bucket !== lastBucket) {
      html += `<h2>${sec.bucket === 'Cytron' ? '🛠' : '🏠'} ${sec.bucket}<span class="tag">${sec.bucket === 'Cytron' ? 'Cytron Technologies' : 'Peribadi'}</span></h2>`;
      lastBucket = sec.bucket;
    }
    const done = shown.filter(r => r.status === 'done').length;
    const pct = Math.round(done / shown.length * 100);
    const hasNotes = sec.header.some(h => /nota|evidence/i.test(h));
    const stIdx = statusCol(sec);
    const header = stIdx >= 0 ? sec.header : [...sec.header, 'Status'];
    html += `
      <div class="card">
        <div class="head">
          <span class="t">${escAttr(sec.title)}</span>
          <span class="c">${shown.length} item · ${done} done (${pct}%)</span>
        </div>
        <div class="bar"><i style="width:${pct}%"></i></div>
        <table>
          <thead><tr>${header.map((h, i) => `<th class="${i === 0 ? 'num' : ''}">${h}</th>`).join('')}</tr></thead>
          <tbody>
            ${shown.map(r => {
              const cellId = r.idx + '-' + hashCode(sec.bucket + '|' + sec.title);
              return `<tr>${
                header.map((h, i) => {
                  if (i === stIdx || (stIdx < 0 && i === header.length - 1)) {
                    return `<td class="statuscell"${editMode ? ` tabindex="0" role="button" data-bucket="${escAttr(sec.bucket)}" data-title="${escAttr(sec.title)}" data-idx="${r.idx}" data-cell-id="${cellId}" id="sc-${cellId}"` : ''}>${pillHtml(r.status)}</td>`;
                  }
                  const cls = (i === 0 && /^\d+$/.test(r.cells[i] || '')) ? 'num'
                            : (hasNotes && i === sec.header.length - 1 && stIdx < 0 ? 'notes' : '');
                  return `<td class="${cls}">${r.cells[i] ?? ''}</td>`;
                }).join('')
              }</tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>`;
  });
  host.innerHTML = html || '<p class="stamp">Tiada item dalam filter ini.</p>';
  if (editMode) {
    host.querySelectorAll('td.statuscell').forEach(td => {
      td.addEventListener('click', () => openPickerFor(td));
      td.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPickerFor(td); }
      });
    });
  }
}

function renderAll() {
  renderStats();
  const active = document.querySelector('#controls .btn.on');
  renderSections(active ? active.dataset.f : 'all');
}

document.getElementById('controls').addEventListener('click', e => {
  const b = e.target.closest('.btn'); if (!b) return;
  document.querySelectorAll('#controls .btn').forEach(x => x.classList.remove('on'));
  b.classList.add('on');
  renderSections(b.dataset.f);
});

// ---------- rebuild markdown ----------
function renderMarkdown() {
  const out = [];
  ['personal-tasks.md', 'cytron-tasks.md'].forEach(file => {
    const src = DATA._sources[file];
    if (!src) return;
    const bucket = DATA.sections.find(s => s.file === file).bucket;
    const lines = src.split('\n');
    let section = null;
    let rowIdx = -1;
    let changed = 0;
    let fixSepNext = false;   // header gained a Status column -> extend its separator too
    for (let li = 0; li < lines.length; li++) {
      const line = lines[li];
      const hm = line.match(/^#{2,3}\s+(.*)$/);
      if (hm) { section = hm[1].trim(); rowIdx = -1; fixSepNext = false; continue; }
      const trimmed = line.trim();
      if (!trimmed.startsWith('|')) continue;
      if (/^\|[\s:\-|]+\|$/.test(trimmed)) {
        if (fixSepNext) { lines[li] = trimmed.replace(/\|$/, '') + '|------|'; fixSepNext = false; }
        continue;
      }
      const cells = trimmed.replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
      if (!cells.length) continue;
      if (/^(#|task|idea|minggu|kandidat)$/i.test(cells[0])) {
        // Section has no Status column yet: add one rather than overwriting the
        // last column (which may hold a real note, e.g. Cytron's "Nota").
        if (!/status/i.test(cells.join('|'))) {
          lines[li] = trimmed.replace(/\s*\|$/, '') + ' | Status |';
          fixSepNext = true;
        }
        continue;
      }
      rowIdx++;
      const st = resolveStatus(bucket, section, rowIdx);
      const before = origStatus(bucket, section, rowIdx);
      if (st === before) continue;
      const sec = SECTION_INDEX[bucket + '||' + section];
      const stIdx = sec ? statusCol(sec) : -1;
      const newCells = cells.slice();
      if (stIdx >= 0) {
        while (newCells.length <= stIdx) newCells.push('');
        newCells[stIdx] = st ? STATUS_MD[st] : STATUS_MD.none;
      } else {
        // No Status column: append one so existing columns are left intact.
        newCells.push(st ? STATUS_MD[st] : STATUS_MD.none);
      }
      lines[li] = '| ' + newCells.join(' | ') + ' |';
      changed++;
    }
    if (!changed) return;
    out.push('### ' + file + '  (' + changed + ' baris diubah)\n\n```markdown\n'
             + lines.join('\n') + '\n```');
  });
  return out.join('\n\n');
}

saveBtn.addEventListener('click', () => {
  const md = renderMarkdown();
  if (!md) { toast('Tiada perubahan untuk disimpan.'); return; }
  diffbar.innerHTML = '<span class="fh">— Perubahan belum masuk ke fail .md —</span>\n'
                    + 'Salin kandungan di bawah ke fail berkenaan, kemudian commit &amp; push.\n\n'
                    + md.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  diffbar.classList.add('show');
  toast('Perubahan dipaparkan di bawah.');
});

saveBtn.disabled = !hasChanges();
renderAll();
</script>
</body>
</html>
"""


def main():
    data = build_data()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False)
    page = TEMPLATE.replace("__DATA__", payload)
    OUT.write_text(page, encoding="utf-8")
    print(f"OK -> {OUT}")
    print(f"sections: {len(data['sections'])}  counters: {data['counters']}")
    for s in data["sections"]:
        print(f"  [{s['bucket']}] {s['title']} -> {len(s['rows'])} rows")


if __name__ == "__main__":
    main()
