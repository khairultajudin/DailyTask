#!/usr/bin/env python3
"""Build the KAI task dashboard from the markdown task files.

Reads:
    tasks/personal-tasks.md
    tasks/cytron-tasks.md
Writes:
    index.html   (repo root — self-contained single file, no network)

Run:  python3 build_dashboard.py
"""
import html
import json
import re
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
TASKS_DIR = REPO_ROOT / "tasks"
OUT_DIR = REPO_ROOT
OUT = REPO_ROOT / "index.html"

STATUS_ORDER = {"⏳": 1, "🔄": 2, "✅": 3, "⏸️": 4, "🔜": 5, "": 9}
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
    personal = (TASKS_DIR / "personal-tasks.md").read_text(encoding="utf-8")
    cytron = (TASKS_DIR / "cytron-tasks.md").read_text(encoding="utf-8")

    groups = [
        ("Personal", TASKS_DIR / "personal-tasks.md", personal),
        ("Cytron", TASKS_DIR / "cytron-tasks.md", cytron),
    ]

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
                {"bucket": bucket, "title": title, "header": header, "rows": rows}
            )

    return {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "counters": counters,
        "sections": sections,
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
  header{display:flex; flex-wrap:wrap; align-items:baseline; gap:12px; margin-bottom:22px}
  h1{font-size:26px; margin:0; letter-spacing:-.4px}
  h1 span{color:var(--accent)}
  .stamp{color:var(--dim); font-size:12.5px}
  .controls{display:flex; gap:8px; margin:18px 0 26px; flex-wrap:wrap}
  .btn{
    background:var(--panel); border:1px solid var(--line); color:var(--dim);
    padding:7px 13px; border-radius:999px; cursor:pointer; font-size:13px;
  }
  .btn:hover{color:var(--txt); border-color:var(--accent2)}
  .btn.on{background:var(--accent2); border-color:var(--accent2); color:#04121c; font-weight:600}
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
  .ev{color:var(--dim); font-size:12.5px}
  footer{color:var(--dim); font-size:12.5px; margin-top:30px; text-align:center}
  .hidden{display:none}
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
    Tukar task dalam fail .md, jalan semula <code>build_dashboard.py</code> untuk refresh.
  </footer>
</div>

<script>
const DATA = __DATA__;

document.getElementById('stamp').textContent = 'Dikemaskini: ' + DATA.generated;

const c = DATA.counters;
const cards = [
  {k:'pending', n:c.pending, l:'Pending', cls:'pending'},
  {k:'progress', n:c.progress, l:'In Progress', cls:'progress'},
  {k:'done', n:c.done, l:'Done', cls:'done'},
  {k:'hold', n:c.hold, l:'On Hold', cls:'hold'},
  {k:'upcoming', n:c.upcoming||0, l:'Upcoming', cls:'upcoming'},
  {k:'total', n:c.total, l:'Jumlah', cls:''},
];
document.getElementById('stats').innerHTML = cards.map(x =>
  `<div class="stat ${x.cls}"><div class="n">${x.n}</div><div class="l">${x.l}</div></div>`
).join('');

function pill(row){
  if(!row.status) return '<span class="pill none">—</span>';
  const icon = {pending:'⏳',progress:'🔄',done:'✅',hold:'⏸️',upcoming:'🔜'}[row.status];
  return `<span class="pill ${row.status}">${icon} ${row.status_label}</span>`;
}

function render(filter){
  const host = document.getElementById('sections');
  let lastBucket = null;
  let html = '';
  DATA.sections.forEach(sec=>{
    const rows = sec.rows.filter(r => filter==='all' || r.status===filter);
    if(!rows.length) return;
    if(sec.bucket !== lastBucket){
      html += `<h2>${sec.bucket === 'Cytron' ? '🛠' : '🏠'} ${sec.bucket}<span class="tag">${sec.bucket === 'Cytron' ? 'Cytron Technologies' : 'Peribadi'}</span></h2>`;
      lastBucket = sec.bucket;
    }
    const done = rows.filter(r=>r.status==='done').length;
    const pct = Math.round(done/rows.length*100);
    const hasNotes = sec.header.some(h=>/nota|evidence/i.test(h));
    const stIdx = sec.header.findIndex(h=>/status/i.test(h));
    const header = stIdx >= 0 ? sec.header : [...sec.header, 'Status'];
    const cellFor = (row, i) => {
      if(i === stIdx && row.status) return pill(row);
      if(stIdx < 0 && i === header.length-1) return row.status ? pill(row) : '<span class="pill none">—</span>';
      return row.cells[i] ?? '';
    };
    html += `
      <div class="card">
        <div class="head">
          <span class="t">${sec.title}</span>
          <span class="c">${rows.length} item · ${done} done (${pct}%)</span>
        </div>
        <div class="bar"><i style="width:${pct}%"></i></div>
        <table>
          <thead><tr>${header.map((h,i)=>`<th class="${i===0?'num':''}">${h}</th>`).join('')}</tr></thead>
          <tbody>
            ${rows.map(r=>`<tr>${
              header.map((h,i)=>{
                const cls = (i===0 && /^\d+$/.test(r.cells[i]||'')) ? 'num'
                          : (hasNotes && i===sec.header.length-1 && stIdx<0 ? 'notes' : '');
                return `<td class="${cls}">${cellFor(r,i)}</td>`;
              }).join('')
            }</tr>`).join('')}
          </tbody>
        </table>
      </div>`;
  });
  host.innerHTML = html || '<p class="stamp">Tiada item dalam filter ini.</p>';
}

document.getElementById('controls').addEventListener('click', e=>{
  const b = e.target.closest('.btn'); if(!b) return;
  document.querySelectorAll('#controls .btn').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');
  render(b.dataset.f);
});

render('all');
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
