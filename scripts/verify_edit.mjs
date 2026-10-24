// Exercise the dashboard's edit-mode logic against a DOM stub.
// The <script> from index.html is run through new Function so its internals
// (renderMarkdown, changeLog, counters) can be inspected from the test.
import { readFileSync } from 'node:fs';

const html = readFileSync('index.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

const store = {};
const els = {};

const mkEl = (id) => ({
  id,
  _text: '',
  _html: '',
  disabled: false,
  dataset: {},
  classList: {
    _s: new Set(),
    add(c) { this._s.add(c); },
    remove(c) { this._s.delete(c); },
    toggle(c, on) { on ? this._s.add(c) : this._s.delete(c); },
    contains(c) { return this._s.has(c); },
  },
  set textContent(v) { this._text = String(v); },
  get textContent() { return this._text; },
  set innerHTML(v) { this._html = String(v); },
  get innerHTML() { return this._html; },
  addEventListener(type, fn) { (this._h ??= {})[type] = fn; },
  querySelector() {
    return { addEventListener(t, fn) { this._fn = fn; } };
  },
  querySelectorAll() { return []; },
});

const body = mkEl('body');
globalThis.document = {
  getElementById: (id) => (els[id] ??= mkEl(id)),
  querySelector: () => null,
  querySelectorAll: () => [],
  addEventListener() {},
  body,
};
globalThis.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { delete store[k]; },
};

const api = new Function(script + `
;return {
  renderMarkdown,
  renderAll,
  resolveStatus,
  changeLog: () => changeLog,
  hasChanges,
};`)();

const out = [];
const count = (s, re) => (s.match(re) || []).length;

out.push('=== initial render ===');
out.push('stamp: ' + els.stamp._text);
out.push('editToggle label: ' + els.editToggle.textContent);
out.push('saveBtn disabled at boot: ' + els.saveMd.disabled);
out.push('status cells rendered: ' + count(els.sections._html, /class="statuscell"/g));
out.push('pills rendered: ' + count(els.sections._html, /class="pill /g));
out.push('unresolved ${: ' + (els.sections._html.includes('${') || els.sections._html.includes('undefined') || els.sections._html.includes('NaN')));
out.push('stats cards: ' + count(els.stats._html, /class="stat /g));
out.push('leaked secrets: ' + /Puan Hana|Maybank|Padang Lumat|Makmal E23|Kelisa Emas/.test(els.sections._html));

out.push('');
out.push('=== edit mode ON ===');
els.editToggle._h.click();
out.push('body has editmode: ' + body.classList.contains('editmode'));
out.push('editToggle label: ' + els.editToggle.textContent);
out.push('editable cells (tabindex): ' + count(els.sections._html, /class="statuscell" tabindex="0"/g));

out.push('');
out.push('=== after simulating a change (BizTrack -> done) ===');
store['kai-task-status-v1'] = JSON.stringify({ 'Personal||💼 Projek Peribadi (Personal Projects)||0': 'done' });
const api2 = new Function(script + `
;return { renderMarkdown, renderAll, resolveStatus, changeLog: () => changeLog, hasChanges };`)();
out.push('changeLog size: ' + api2.changeLog().length);
out.push('hasChanges: ' + api2.hasChanges());
out.push('saveBtn enabled: ' + !els.saveMd.disabled);
out.push('resolveStatus now: ' + api2.resolveStatus('Personal', '💼 Projek Peribadi (Personal Projects)', 0));
out.push('stats done count: ' + api2.renderMarkdown && (els.stats._html.match(/class="n">(\d+)<\/div><div class="l">Done/g) || [])[1]);

const md = api2.renderMarkdown();
out.push('');
out.push('=== renderMarkdown ===');
out.push('mentions personal-tasks.md: ' + md.includes('personal-tasks.md'));
out.push('mentions cytron-tasks.md: ' + md.includes('cytron-tasks.md'));
out.push('BizTrack row now ✅: ' + /\| 1 \| BizTrack \(Pelanggan A\) \| ✅ \|/.test(md));
out.push('no secret leaked: ' + !/Puan Hana|Maybank|Padang Lumat|invoice 52/.test(md));
out.push('--- first 400 chars ---');
out.push(md.slice(0, 400));

console.log(out.join('\n'));
