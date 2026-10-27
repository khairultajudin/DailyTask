#!/usr/bin/env python3
"""Build the KAI task dashboard from the markdown task files.

Reads:
    tasks/personal-tasks.md
    tasks/cytron-tasks.md
Writes:
    index.html   (repo root — self-contained single file, no network)

Statuses can be changed IN THE PAGE (Edit mode). Changes live in
localStorage; "Simpan" prints the updated .md so they can be
committed back to the source files.

Run:  python3 build_dashboard.py
"""
import json
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
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
    "❌": "Cancel",
}
STATUS_CLASS = {
    "⏳": "pending",
    "🔄": "progress",
    "✅": "done",
    "⏸️": "hold",
    "🔜": "upcoming",
    "❌": "cancel",
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
    if "cancel" in low or "batal" in low:
        return "❌"
    return ""


EXCLUDED_SECTIONS = [
    "Weekly Focus (12–16 Oct)",
    "Slot Kosong — kandidat untuk diisi kemudian",
]


def is_excluded_section(title: str) -> bool:
    norm = re.sub(r"\s+", " ", title.replace("–", "-").replace("—", "-")).strip().lower()
    for ex in EXCLUDED_SECTIONS:
        ex_norm = re.sub(r"\s+", " ", ex.replace("–", "-").replace("—", "-")).strip().lower()
        if norm == ex_norm or ex.lower() in title.lower() or ex_norm in norm:
            return True
    return False


def build_data():
    sources = {}
    groups = []
    for name in FILES:
        text = (TASKS_DIR / name).read_text(encoding="utf-8")
        sources[name] = text
        groups.append((BUCKET_OF[name], name, text))

    sections = []
    counters = {"pending": 0, "progress": 0, "done": 0, "hold": 0, "upcoming": 0, "cancel": 0, "total": 0}

    for bucket, path, text in groups:
        for title, kind, payload in parse_tables(text):
            if kind == "note":
                continue
            if is_excluded_section(title):
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
  .pill.cancel{background:#3b1414; color:#f87171}
  .stat.cancel .n{color:#f87171}
  .pick.on.cancel{background:#ef4444; border-color:#ef4444; color:#fff}
  .controls .btn[data-f="cancel"].on{background:#dc2626; border-color:#ef4444; color:#fff}
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

/* Floating save popup */
.save-popup {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%) translateY(120px);
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(16, 185, 129, 0.45);
  box-shadow: 0 12px 32px -4px rgba(0, 0, 0, 0.6), 0 0 20px rgba(16, 185, 129, 0.25);
  border-radius: 9999px;
  padding: 8px 14px 8px 18px;
  display: flex;
  align-items: center;
  gap: 16px;
  z-index: 1000;
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.3s ease;
  opacity: 0;
  pointer-events: none;
}
.save-popup.show {
  transform: translateX(-50%) translateY(0);
  opacity: 1;
  pointer-events: auto;
}
.save-popup-content {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #e2e8f0;
}
.save-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
  animation: pulse-dot 1.8s infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.45; transform: scale(0.8); }
}
.save-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.save-actions .btn {
  padding: 6px 14px;
  font-size: 13px;
  border-radius: 9999px;
}
/* Editable notes */
td.notes {
  cursor: text;
  min-width: 140px;
  outline: none;
  border-radius: 4px;
  padding: 6px 10px;
  transition: background 0.15s, border-color 0.15s;
}
td.notes:hover {
  background: rgba(255, 255, 255, 0.05);
}
td.notes:focus {
  background: rgba(255, 255, 255, 0.09);
  box-shadow: 0 0 0 1px #10b981;
}
td.notes:empty:before {
  content: attr(data-placeholder);
  color: var(--muted);
  opacity: 0.55;
  font-style: italic;
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
    <button class="btn act" id="saveMd" type="button" disabled>💾 Simpan</button>
    <span class="note" id="editNote">Klik mana-mana status atau ruangan nota untuk edit terus di sini.</span>
  </div>

  <div id="diffbar"></div>
  <div class="stats" id="stats"></div>

  <div class="controls" id="controls">
    <button class="btn on" data-f="all">Semua</button>
    <button class="btn" data-f="pending">⏳ Pending</button>
    <button class="btn" data-f="progress">🔄 In Progress</button>
    <button class="btn" data-f="hold">⏸️ On Hold</button>
    <button class="btn" data-f="done">✅ Done</button>
    <button class="btn" data-f="cancel">❌ Cancel</button>
  </div>

  <main id="sections"></main>

  <footer>
    Sumber: <code>personal-tasks.md</code> &amp; <code>cytron-tasks.md</code> ·
    Tukar status terus dalam dashboard (tersimpan dalam localStorage), atau edit fail .md
    dan jalan semula <code>build_dashboard.py</code>.
  </footer>
</div>

  <div id="savePopup" class="save-popup" role="alert">
    <div class="save-popup-content">
      <span class="save-dot"></span>
      <span class="save-msg">Ada <strong id="changeCount">1</strong> perubahan belum disimpan</span>
    </div>
    <div class="save-actions">
      <button class="btn act" id="savePopupBtn" type="button">💾 Simpan</button>
      <button class="btn" id="discardPopupBtn" type="button">Batal</button>
    </div>
  </div>
<div id="toast"></div>

<script>
const DATA = __DATA__;

const BASELINE_KEY = 'kai-task-baseline-v2';
try {
  const savedBase = JSON.parse(localStorage.getItem(BASELINE_KEY) || 'null');
  if (savedBase && savedBase.sections) {
    savedBase.sections.forEach(savedSec => {
      const liveSec = DATA.sections.find(s => s.bucket === savedSec.bucket && s.title === savedSec.title);
      if (liveSec && savedSec.rows) {
        savedSec.rows.forEach((r, idx) => {
          if (liveSec.rows[idx]) {
            if (r.cells) liveSec.rows[idx].cells = r.cells;
            if (r.status !== undefined) liveSec.rows[idx].status = r.status;
          }
        });
      }
    });
    if (savedBase.counters) DATA.counters = savedBase.counters;
    if (savedBase.sources) DATA._sources = savedBase.sources;
  }
} catch(e){}

document.getElementById('stamp').textContent = 'Dikemaskini: ' + DATA.generated;

const STORE_KEY = 'kai-task-status-v1';
const NOTE_STORE_KEY = 'kai-task-notes-v1';
const STATUS_KEYS = ['pending', 'progress', 'done', 'hold', 'upcoming', 'cancel'];
const STATUS_ICON = {pending:'⏳', progress:'🔄', done:'✅', hold:'⏸️', upcoming:'🔜', cancel:'❌'};
const STATUS_LABEL = {pending:'Pending', progress:'In Progress', done:'Done', hold:'On Hold', upcoming:'Upcoming', cancel:'Cancel'};
const STATUS_MD = {pending:'⏳', progress:'🔄', done:'✅', hold:'⏸️', upcoming:'🔜', cancel:'❌', none:'—'};
const ICON_TO_KEY = {'⏳':'pending','🔄':'progress','✅':'done','⏸️':'hold','🔜':'upcoming','❌':'cancel'};

// ---------- change log (localStorage) ----------
const loadLog = () => { try { return JSON.parse(localStorage.getItem(STORE_KEY) || '{}'); } catch(e){ return {}; } };
const saveLog = o => { try { localStorage.setItem(STORE_KEY, JSON.stringify(o)); } catch(e){} };
let changeLog = loadLog();

const loadNoteLog = () => { try { return JSON.parse(localStorage.getItem(NOTE_STORE_KEY) || '{}'); } catch(e){ return {}; } };
const saveNoteLog = o => { try { localStorage.setItem(NOTE_STORE_KEY, JSON.stringify(o)); } catch(e){} };
let noteLog = loadNoteLog();

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

function noteCol(sec) {
  return sec.header.findIndex(h => /nota|note|evidence|kenapa sesuai|catatan/i.test(h));
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
    for (const c of cells) {
      fromCell = normStatus(c);
      if (fromCell) break;
    }
  }
  return fromCell || sec.default || null;
}

function resolveStatus(bucket, title, idx) {
  const k = keyOf(bucket, title, idx);
  if (changeLog[k]) return changeLog[k];
  return origStatus(bucket, title, idx);
}

function origNote(bucket, title, idx) {
  const sec = SECTION_INDEX[bucket + '||' + title];
  if (!sec || !sec.rows[idx]) return '';
  const nIdx = noteCol(sec);
  if (nIdx >= 0 && sec.rows[idx].cells.length > nIdx) {
    return sec.rows[idx].cells[nIdx] || '';
  }
  return '';
}

function resolveNote(bucket, title, idx) {
  const k = keyOf(bucket, title, idx);
  if (k in noteLog) return noteLog[k];
  return origNote(bucket, title, idx);
}

function applyNote(bucket, title, idx, text) {
  const k = keyOf(bucket, title, idx);
  const before = origNote(bucket, title, idx);
  const clean = (text || '').trim();
  if (clean === (before || '').trim()) {
    delete noteLog[k];
  } else {
    noteLog[k] = clean;
  }
  saveNoteLog(noteLog);
  updateSaveUI();
}

function normStatus(v) {
  if (v == null) return null;
  const s = String(v).trim();
  if (s === '' || s === '—' || s === '-' || s === 'none') return null;
  if (STATUS_KEYS.includes(s)) return s;
  const m = s.match(/^(⏳|🔄|✅|⏸️|🔜|❌)/);
  if (m) return ICON_TO_KEY[m[1]];
  const low = s.toLowerCase();
  for (const k of STATUS_KEYS) if (low.includes(STATUS_LABEL[k].toLowerCase())) return k;
  return null;
}

function hasChanges() {
  return Object.keys(changeLog).length > 0 || Object.keys(noteLog).length > 0;
}

// ---------- live direct edit (always enabled) ----------
let editMode = true;
let openPicker = null;

const editToggle = document.getElementById('editToggle');
const saveBtn = document.getElementById('saveMd');
const editNote = document.getElementById('editNote');
const toastEl = document.getElementById('toast');
const diffbar = document.getElementById('diffbar');
const savePopup = document.getElementById('savePopup');
const changeCountEl = document.getElementById('changeCount');

function updateSaveUI() {
  const total = (Object.keys(changeLog).length) + (Object.keys(noteLog).length);
  if (saveBtn) saveBtn.disabled = (total === 0);
  if (savePopup) {
    if (total > 0) {
      if (changeCountEl) changeCountEl.textContent = total;
      savePopup.classList.add('show');
    } else {
      savePopup.classList.remove('show');
    }
  }
}

function toast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  clearTimeout(toastEl._t);
  toastEl._t = setTimeout(() => toastEl.classList.remove('show'), 2400);
}

function closePicker() {
  if (!openPicker) return;
  const el = document.getElementById('sc-' + openPicker.cellId);
  if (el) el.innerHTML = pillHtml(openPicker.status);
  openPicker = null;
}

function openPickerFor(td) {
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
  const before = origStatus(p.bucket, p.title, p.idx);
  if (status === before) {
    delete changeLog[k];
  } else if (status) {
    changeLog[k] = status;
  } else {
    changeLog[k] = 'none';
  }
  saveLog(changeLog);
  openPicker = null;
  renderAll();
  updateSaveUI();
  toast(status ? ('Ditukar kepada ' + STATUS_ICON[status] + ' ' + STATUS_LABEL[status])
               : 'Status dibuang');
}

if (editToggle) {
  editToggle.textContent = '✏️ Edit: ON';
  editToggle.classList.add('on');
  editToggle.addEventListener('click', () => {
    editMode = !editMode;
    document.body.classList.toggle('editmode', editMode);
    editToggle.classList.toggle('on', editMode);
    editToggle.textContent = editMode ? '✏️ Edit: ON' : '✏️ Edit Status';
    closePicker();
    renderAll();
  });
}
document.body.classList.add('editmode');

// ---------- counters & renderers ----------
function computeCounters() {
  const c = {pending:0, progress:0, done:0, hold:0, upcoming:0, cancel:0, total:0};
  DATA.sections.forEach(sec => {
    sec.rows.forEach((r, idx) => {
      c.total++;
      const st = resolveStatus(sec.bucket, sec.title, idx);
      if (st && c[st] !== undefined) c[st]++;
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
    {k:'cancel', n:c.cancel, l:'Cancel', cls:'cancel'},
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
  const isDoneSec = s => /^✅/.test(s.title);
  const isDoneOrCancel = st => (st === 'done' || st === 'cancel');
  const buckets = ['Personal', 'Cytron'];
  let html = '';

  const allDoneRows = [];

  buckets.forEach(bucket => {
    const bSections = DATA.sections.filter(s => s.bucket === bucket);
    if (!bSections.length) return;

    const activeSecs = bSections.filter(s => !isDoneSec(s));
    const doneSec = bSections.find(s => isDoneSec(s));
    let bHtml = '';

    // Render active sections for this bucket
    activeSecs.forEach(sec => {
      const shown = [];
      const stIdx = statusCol(sec);
      const nIdx = noteCol(sec);
      const header = stIdx >= 0 ? sec.header : [...sec.header, 'Status'];

      let secDoneCount = 0;
      sec.rows.forEach((r, idx) => {
        const st = resolveStatus(sec.bucket, sec.title, idx);
        const curNoteVal = resolveNote(sec.bucket, sec.title, idx);
        if (isDoneOrCancel(st)) {
          secDoneCount++;
          const taskName = r.cells[1] || r.cells[0] || '';
          allDoneRows.push({
            origBucket: sec.bucket,
            origTitle: sec.title,
            origIdx: idx,
            taskName: taskName,
            secTag: sec.title.replace(/^[^a-zA-Z0-9\s]+/, '').split('(')[0].trim(),
            date: st === 'cancel' ? 'Batal' : 'Selesai',
            note: curNoteVal,
            status: st
          });
        } else {
          if (filter === 'all' || st === filter) {
            shown.push({ idx, cells: r.cells, status: st });
          }
        }
      });

      const totalInSec = sec.rows.length;
      const pct = totalInSec ? Math.round((secDoneCount / totalInSec) * 100) : 0;

      if (!shown.length && filter !== 'all') return;

      bHtml += `
      <div class="card">
        <div class="head">
          <span class="t">${escAttr(sec.title)}</span>
          <span class="c">${shown.length} item · ${secDoneCount} done (${pct}%)</span>
        </div>
        <div class="bar"><i style="width:${pct}%"></i></div>
        <table>
          <thead><tr>${header.map((h, i) => `<th class="${i === 0 ? 'num' : ''}">${h}</th>`).join('')}</tr></thead>
          <tbody>
            ${shown.length ? shown.map(r => {
              const cellId = r.idx + '-' + hashCode(sec.bucket + '|' + sec.title);
              return `<tr>${
                header.map((h, i) => {
                  if (i === stIdx || (stIdx < 0 && i === header.length - 1)) {
                    return `<td class="statuscell" tabindex="0" role="button" data-bucket="${escAttr(sec.bucket)}" data-title="${escAttr(sec.title)}" data-idx="${r.idx}" data-cell-id="${cellId}" id="sc-${cellId}">${pillHtml(r.status)}</td>`;
                  }
                  if (i === nIdx) {
                    const noteText = resolveNote(sec.bucket, sec.title, r.idx);
                    return `<td class="notes" contenteditable="true" data-bucket="${escAttr(sec.bucket)}" data-title="${escAttr(sec.title)}" data-idx="${r.idx}" data-placeholder="Tambah nota...">${escAttr(noteText || '')}</td>`;
                  }
                  const cls = (i === 0 && /^\d+$/.test(r.cells[i] || '')) ? 'num' : '';
                  return `<td class="${cls}">${r.cells[i] ?? ''}</td>`;
                }).join('')
              }</tr>`;
            }).join('') : `<tr><td colspan="${header.length}" style="text-align:center;color:var(--muted);padding:14px;font-size:13px;">Semua task aktif dalam seksyen ini telah selesai! 🎉</td></tr>`}
          </tbody>
        </table>
      </div>`;
    });

    // Also collect original Done section tasks for this bucket
    if (doneSec) {
      const taskColIdx = doneSec.header.findIndex(h => /task|perkara|projek/i.test(h)) >= 0
        ? doneSec.header.findIndex(h => /task|perkara|projek/i.test(h)) : 1;
      const dateColIdx = doneSec.header.findIndex(h => /tarikh|date/i.test(h));
      const nIdx = noteCol(doneSec);

      doneSec.rows.forEach((r, idx) => {
        const st = resolveStatus(doneSec.bucket, doneSec.title, idx) || 'done';
        if (isDoneOrCancel(st)) {
          const curNoteVal = resolveNote(doneSec.bucket, doneSec.title, idx);
          allDoneRows.push({
            origBucket: doneSec.bucket,
            origTitle: doneSec.title,
            origIdx: idx,
            taskName: r.cells[taskColIdx] || r.cells[1] || r.cells[0] || '',
            secTag: '',
            date: dateColIdx >= 0 ? (r.cells[dateColIdx] || '—') : '—',
            note: curNoteVal || (nIdx >= 0 ? r.cells[nIdx] : ''),
            status: st
          });
        }
      });
    }

    if (bHtml) {
      html += `<h2>${bucket === 'Cytron' ? '🛠' : '🏠'} ${bucket}<span class="tag">${bucket === 'Cytron' ? 'Cytron Technologies' : 'Peribadi'}</span></h2>` + bHtml;
    }
  });

  // Filter rows for the Done/Cancel table
  const doneTableRows = allDoneRows.filter(r => {
    if (filter === 'all') return true;
    if (filter === 'done') return r.status === 'done';
    if (filter === 'cancel') return r.status === 'cancel';
    return false;
  });

  // Render ONE unified Done & Cancel section at the very bottom
  if (doneTableRows.length && (filter === 'all' || filter === 'done' || filter === 'cancel')) {
    const doneCount = doneTableRows.filter(r => r.status === 'done').length;
    const cancelCount = doneTableRows.filter(r => r.status === 'cancel').length;
    const totalDoneCard = doneTableRows.length;
    const pct = totalDoneCard ? Math.round((doneCount / totalDoneCard) * 100) : 0;

    html += `
    <h2>✅ Selesai &amp; ❌ Dibatalkan <span class="tag">Personal &amp; Cytron</span></h2>
    <div class="card">
      <div class="head">
        <span class="t">✅ Selesai &amp; ❌ Dibatalkan</span>
        <span class="c">${totalDoneCard} item · ${doneCount} selesai · ${cancelCount} batal</span>
      </div>
      <div class="bar"><i style="width:${pct}%"></i></div>
      <table>
        <thead>
          <tr>
            <th class="num">#</th>
            <th>Kategori</th>
            <th>Task</th>
            <th>Tarikh / Dari</th>
            <th>Nota</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${doneTableRows.map((r, i) => {
            const cellId = r.origIdx + '-' + hashCode(r.origBucket + '|' + r.origTitle);
            const categoryBadge = r.origBucket === 'Cytron'
              ? '<span class="tag" style="background:#0284c7;color:#fff;border-color:#38bdf8;font-weight:600;">🛠 Cytron</span>'
              : '<span class="tag" style="background:#059669;color:#fff;border-color:#34d399;font-weight:600;">🏠 Personal</span>';

            const originTag = r.secTag ? `<span class="tag" style="margin-right:6px;font-size:11px;opacity:0.85;">${escAttr(r.secTag)}</span>` : '';

            return `<tr>
              <td class="num">${i + 1}</td>
              <td style="white-space:nowrap;">${categoryBadge}</td>
              <td>${originTag}${escAttr(r.taskName)}</td>
              <td style="white-space:nowrap;color:var(--muted);">${escAttr(r.date)}</td>
              <td class="notes" contenteditable="true" data-bucket="${escAttr(r.origBucket)}" data-title="${escAttr(r.origTitle)}" data-idx="${r.origIdx}" data-placeholder="Tambah nota...">${escAttr(r.note || '')}</td>
              <td class="statuscell" tabindex="0" role="button" data-bucket="${escAttr(r.origBucket)}" data-title="${escAttr(r.origTitle)}" data-idx="${r.origIdx}" data-cell-id="${cellId}" id="sc-${cellId}">${pillHtml(r.status)}</td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>`;
  }

  host.innerHTML = html || '<p class="stamp">Tiada item dalam filter ini.</p>';

  // Attach interactive listeners for status and notes
  if (host && typeof host.querySelectorAll === 'function') {
    host.querySelectorAll('td.statuscell').forEach(td => {
      td.addEventListener('click', () => openPickerFor(td));
      td.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPickerFor(td); }
      });
    });

    host.querySelectorAll('td.notes[contenteditable="true"]').forEach(td => {
      td.addEventListener('input', () => {
        const b = td.dataset.bucket, t = td.dataset.title, idx = +td.dataset.idx;
        applyNote(b, t, idx, td.innerText);
      });
      td.addEventListener('blur', () => {
        const b = td.dataset.bucket, t = td.dataset.title, idx = +td.dataset.idx;
        applyNote(b, t, idx, td.innerText);
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

// ---------- rebuild markdown & auto-save ----------
const DASHBOARD_KEY = "__DASHBOARD_KEY__";
const SAVE_ENDPOINT = (typeof location !== 'undefined' && location.hostname === 'dashboard.khaispace.com')
  ? '/save'
  : 'https://dashboard.khaispace.com/save';

function getModifiedFiles() {
  const result = {};
  ['personal-tasks.md', 'cytron-tasks.md'].forEach(file => {
    const src = DATA._sources[file];
    if (!src) return;
    const secObj = DATA.sections.find(s => s.file === file);
    if (!secObj) return;
    const bucket = secObj.bucket;
    const lines = src.split('\n');
    let section = null;
    let rowIdx = -1;
    let changed = 0;
    let fixSepNext = false;
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
        if (!/status/i.test(cells.join('|'))) {
          lines[li] = trimmed.replace(/\s*\|$/, '') + ' | Status |';
          fixSepNext = true;
        }
        continue;
      }
      rowIdx++;
      const st = resolveStatus(bucket, section, rowIdx);
      const before = origStatus(bucket, section, rowIdx);
      const curN = resolveNote(bucket, section, rowIdx);
      const origN = origNote(bucket, section, rowIdx);

      const stChanged = (st !== before);
      const noteChanged = (curN !== origN);

      if (!stChanged && !noteChanged) continue;

      const sec = SECTION_INDEX[bucket + '||' + section];
      const stIdx = sec ? statusCol(sec) : -1;
      const nIdx = sec ? noteCol(sec) : -1;
      const newCells = cells.slice();

      if (stChanged) {
        if (stIdx >= 0) {
          while (newCells.length <= stIdx) newCells.push('');
          newCells[stIdx] = st ? STATUS_MD[st] : STATUS_MD.none;
        } else {
          newCells.push(st ? STATUS_MD[st] : STATUS_MD.none);
        }
      }

      if (noteChanged) {
        if (nIdx >= 0) {
          while (newCells.length <= nIdx) newCells.push('');
          newCells[nIdx] = curN;
        } else {
          newCells.push(curN);
        }
      }

      lines[li] = '| ' + newCells.join(' | ') + ' |';
      changed++;
    }
    if (changed > 0) {
      result[file] = { content: lines.join('\n'), changed };
    }
  });
  return result;
}

function renderMarkdown() {
  const mod = getModifiedFiles();
  const out = [];
  for (const [file, item] of Object.entries(mod)) {
    out.push('### ' + file + '  (' + item.changed + ' baris diubah)\\n\\n```markdown\\n'
             + item.content + '\\n```');
  }
  return out.join('\\n\\n');
}

saveBtn.addEventListener('click', async () => {
  const modFiles = getModifiedFiles();
  const fileNames = Object.keys(modFiles);
  if (!fileNames.length) {
    toast('Tiada perubahan untuk disimpan.');
    return;
  }

  saveBtn.disabled = true;
  saveBtn.textContent = '⏳ Menyimpan...';
  const popupSaveBtn = document.getElementById('savePopupBtn');
  if (popupSaveBtn) { popupSaveBtn.disabled = true; popupSaveBtn.textContent = '⏳ Menyimpan...'; }
  toast('Menyimpan ke GitHub...');

  try {
    // 1. Commit statuses into in-memory DATA
    for (const [k, newSt] of Object.entries(changeLog)) {
      const parts = k.split('||');
      const b = parts[0], t = parts[1], i = +parts[2];
      const sec = SECTION_INDEX[b + '||' + t];
      if (sec && sec.rows[i]) {
        const oldSt = origStatus(b, t, i);
        sec.rows[i].status = newSt;
        const stCol = statusCol(sec);
        if (stCol >= 0) {
          while (sec.rows[i].cells.length <= stCol) sec.rows[i].cells.push('');
          sec.rows[i].cells[stCol] = newSt ? STATUS_ICON[newSt] : '';
        } else {
          sec.rows[i].cells.push(newSt ? STATUS_ICON[newSt] : '');
        }
        if (oldSt && DATA.counters[oldSt] !== undefined) DATA.counters[oldSt]--;
        if (newSt && DATA.counters[newSt] !== undefined) DATA.counters[newSt]++;
      }
    }

    // 2. Commit notes into in-memory DATA
    for (const [k, newNote] of Object.entries(noteLog)) {
      const parts = k.split('||');
      const b = parts[0], t = parts[1], i = +parts[2];
      const sec = SECTION_INDEX[b + '||' + t];
      if (sec && sec.rows[i]) {
        const nIdx = noteCol(sec);
        if (nIdx >= 0) {
          while (sec.rows[i].cells.length <= nIdx) sec.rows[i].cells.push('');
          sec.rows[i].cells[nIdx] = newNote;
        }
      }
    }

    for (const file of fileNames) {
      DATA._sources[file] = modFiles[file].content;
    }

    // Build indexHtml payload to update GitHub's index.html simultaneously
    let indexHtml = null;
    try {
      if (typeof document !== 'undefined' && document.documentElement) {
        closePicker();
        const curHtml = '<!DOCTYPE html>\\n<html lang="ms">\\n' + document.documentElement.innerHTML + '\\n</html>';
        indexHtml = curHtml.replace(/const DATA = \{.*?\};\n/s, 'const DATA = ' + JSON.stringify(DATA) + ';\\n');
      }
    } catch(e){}

    for (const file of fileNames) {
      const resp = await fetch(SAVE_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-dashboard-key': DASHBOARD_KEY,
        },
        body: JSON.stringify({
          file: file,
          content: modFiles[file].content,
          indexHtml: indexHtml,
        }),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok || !data.ok) {
        throw new Error(data.error || ('Gagal menyimpan ' + file));
      }
    }

    // 3. Persist updated baseline in localStorage
    try {
      localStorage.setItem(BASELINE_KEY, JSON.stringify({
        sections: DATA.sections,
        counters: DATA.counters,
        sources: DATA._sources,
        timestamp: Date.now()
      }));
      localStorage.removeItem(STORE_KEY);
      localStorage.removeItem(NOTE_STORE_KEY);
    } catch(e){}

    changeLog = {};
    noteLog = {};
    saveBtn.disabled = true;
    saveBtn.textContent = '💾 Simpan';
    if (popupSaveBtn) { popupSaveBtn.disabled = true; popupSaveBtn.textContent = '💾 Simpan'; }
    updateSaveUI();
    diffbar.classList.remove('show');
    toast('✅ Berjaya disimpan! Dashboard telah dikemas kini.');
    renderAll();
  } catch (err) {
    console.error(err);
    saveBtn.disabled = false;
    saveBtn.textContent = '💾 Simpan Semula';
    if (popupSaveBtn) { popupSaveBtn.disabled = false; popupSaveBtn.textContent = '💾 Simpan Semula'; }
    toast('❌ Ralat: ' + (err.message || err));

    const md = renderMarkdown();
    diffbar.innerHTML = '<span class="fh">— Auto-save gagal (' + (err.message || err) + ') —</span>\\n'
                      + 'Salin kandungan di bawah secara manual:\\n\\n'
                      + md.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    diffbar.classList.add('show');
  }
});

// Floating popup actions
document.getElementById('savePopupBtn')?.addEventListener('click', () => saveBtn.click());
document.getElementById('discardPopupBtn')?.addEventListener('click', () => {
  if (confirm('Batalkan semua perubahan yang belum disimpan?')) {
    changeLog = {};
    noteLog = {};
    try {
      localStorage.removeItem(STORE_KEY);
      localStorage.removeItem(NOTE_STORE_KEY);
    } catch(e){}
    updateSaveUI();
    renderAll();
    toast('Perubahan dibatalkan.');
  }
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
    key = "321295cb186bdc7a6f81155d6f72165b0cab5361d62693b2"
    page = TEMPLATE.replace("__DATA__", payload).replace("__DASHBOARD_KEY__", key)
    OUT.write_text(page, encoding="utf-8")
    print(f"OK -> {OUT}")
    print(f"sections: {len(data['sections'])}  counters: {data['counters']}")
    for s in data["sections"]:
        print(f"  [{s['bucket']}] {s['title']} -> {len(s['rows'])} rows")


if __name__ == "__main__":
    main()
