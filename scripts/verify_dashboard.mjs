// Headless verification of the dashboard's client-side render logic.
// Runs the exact <script> from index.html against a minimal DOM stub.
import { readFileSync } from 'node:fs';

const html = readFileSync('index.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

const els = {};
const mkEl = (id) => ({
  id,
  _text: '',
  _html: '',
  set textContent(v) { this._text = v; },
  get textContent() { return this._text; },
  set innerHTML(v) { this._html = v; },
  get innerHTML() { return this._html; },
  addEventListener() {},
  dataset: {},
  classList: { add() {}, remove() {}, contains: () => false },
});

globalThis.document = {
  getElementById: (id) => (els[id] ??= mkEl(id)),
  querySelectorAll: () => [],
};

eval(script);

const stats = els.stats._html;
const sections = els.sections._html;

const cards = [...sections.matchAll(/class="t">([^<]+)<\/span>/g)].map(m => m[1]);
const counts = [...sections.matchAll(/(\d+) item · (\d+) done \((\d+)%\)/g)]
  .map(m => `${m[1]} item / ${m[2]} done / ${m[3]}%`);
const rows = (sections.match(/<tr>/g) || []).length;
const pills = [...sections.matchAll(/class="pill ([a-z]+)">([^<]+)</g)].map(m => `${m[1]}:${m[2].trim()}`);
const pillsByKind = pills.reduce((a, p) => ((a[p.split(':')[0]] = (a[p.split(':')[0]] || 0) + 1), a), {});

console.log('stamp:', els.stamp._text);
console.log('stat cards:', [...stats.matchAll(/<div class="n">(\d+)<\/div><div class="l">([^<]+)<\/div>/g)]
  .map(m => `${m[2]}=${m[1]}`).join(' | '));
console.log('cards rendered:', cards.length);
cards.forEach((c, i) => console.log(`  ${i + 1}. ${c} -> ${counts[i]}`));
console.log('total <tr> rows:', rows);
console.log('status pills by kind:', JSON.stringify(pillsByKind));
console.log('unresolved template syntax:', sections.includes('${') || sections.includes('undefined') || sections.includes('NaN'));
console.log('headings:', [...sections.matchAll(/<h2>([^<]+)/g)].map(m => m[1].trim()).join(' / '));
