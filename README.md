# DailyTask — KAI Task Dashboard

Dashboard task peribadi + kerja, dibina automatik daripada fail Markdown.
Satu fail HTML, tiada *framework*, tiada *build step* masa penggunaan — double-click dan dah.

**Live:** <https://khairultajudin.github.io/DailyTask/>

---

## Apa dalam dashboard

- **6 kad statistik** — Pending · In Progress · Done · On Hold · Upcoming · Jumlah
- **9 seksyen** — Rumah, Projek Peribadi, Next Ideas, Done (personal) + Pending Cytron,
  Tutorial Plan Q4, Slot Kosong, Weekly Focus, Done (Cytron)
- **Butang filter** ikut status — Semua / Pending / In Progress / On Hold / Done
- **Progress bar + peratusan** untuk setiap seksyen
- **Responsive** — jadi kecil bila skrin kecil
- **Tiada dependency luar** — berfungsi walaupun offline

Statistik terkini (25 Okt 2026, 00:42):

```
Pending 35 · In Progress 2 · Done 18 · On Hold 0 · Upcoming 1 · Jumlah 56
```

---

## Cara guna

1. Buka `index.html` dalam browser (Chrome / Edge / Firefox).
2. Klik butang filter atas untuk tapis ikut status.

Tidak perlu server, tidak perlu internet.

---

## Cara kemaskini task

Edit fail dalam folder [`tasks/`](tasks/) — ikut format sedia ada:

| # | Task | Status | Nota |
|---|------|--------|------|
| 1 | Contoh task | ⏳ | Nota bebas |

### Legend status

| Simbol | Maksud |
|--------|--------|
| ⏳ | Pending |
| 🔄 | In Progress |
| ✅ | Done |
| ⏸️ | On Hold |
| 🔜 | Upcoming |

### Tambah seksyen baharu

Tambah header `##` baharu dalam fail `.md` — seksyen itu akan keluar sendiri dalam dashboard
selagi ia diikuti dengan jadual Markdown. Tajuk seksyen yang ada ikon status
(contoh `## ✅ Done`) akan dipakai sebagai status asal bila baris tiada status sendiri.

---

## Struktur repo

```
DailyTask/
├── index.html            # dashboard siap (yang awak buka)
├── build_dashboard.py    # penjana — baca tasks/, tulis index.html
├── tasks/
│   ├── personal-tasks.md # task peribadi
│   └── cytron-tasks.md   # task Cytron
├── scripts/
│   └── verify_dashboard.mjs  # ujian render tanpa browser (Node)
└── README.md
```

---

## Regenerate dashboard

Setiap kali task berubah:

```bash
python3 build_dashboard.py
```

Output: `OK -> /path/ke/DailyTask/index.html`

Fail lama `index.html` akan ditulis ganti dengan data terkini. Stamp
`Dikemaskini: <tarikh masa>` pada dashboard dikemas kini mengikut masajalan skrip.

### Semakan render (pilihan, perlukan Node)

```bash
node scripts/verify_dashboard.mjs
```

Mengesan: kad statistik, seksyen, bilangan baris, *pill* status, dan sebarang
`${...}` / `undefined` / `NaN` yang tak terselesaikan.

### Deploy ke GitHub Pages

```bash
git add -A && git commit -m "update: task terkini"
git push
```

Dengan GitHub Pages **Deploy from a branch → `main` / root**, `index.html` di root repo
akan dihoskan terus di <https://khairultajudin.github.io/DailyTask/> — tiada workflow perlu ditambah.

---

## Nota privasi

Repo ini **public**, jadi nama pelanggan, institusi, dan butiran peribadi telah
diredaksi kepada label generik (contoh: "Pelanggan A").

---

## Lesen

MIT
