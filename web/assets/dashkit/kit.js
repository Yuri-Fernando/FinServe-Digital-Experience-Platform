/* dashkit — renderizador declarativo de dashboards (vanilla JS, sem bundler).
 * Uso: renderDashboard(elemento, spec). A spec vem de /api/platform/dashboards/{id}; veja docs/DASHKIT.md.
 * Segurança: todo texto dinâmico passa por esc() antes de virar HTML. */
import { mountCalculator } from './calculators.js';

export const $ = (sel, root = document) => root.querySelector(sel);
export const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (s) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[s]));

/* ---------- formatação (pt-BR) ---------- */
const nf = (min, max) => new Intl.NumberFormat('pt-BR', { minimumFractionDigits: min, maximumFractionDigits: max });
const NF = { 0: nf(0, 0), 1: nf(1, 1), 2: nf(2, 2), 4: nf(4, 4) };
const MONEY0 = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
const MONEY2 = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const isNum = (v) => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v));
const compact = (v) => { const x = Number(v); return x >= 1e6 ? NF[2].format(x / 1e6) + ' mi' : x >= 1e3 ? NF[1].format(x / 1e3) + ' mil' : NF[0].format(x); };
const MONTHS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
export const dateBR = (iso) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso)); return m ? `${m[3]}/${m[2]}/${m[1]}` : String(iso ?? ''); };
export const monthBR = (iso) => { const m = /^(\d{4})-(\d{2})/.exec(String(iso)); return m ? `${MONTHS[+m[2] - 1]}/${m[1].slice(2)}` : String(iso ?? ''); };
const BADGE_LABEL = { on_track: 'no ritmo', over: 'acima', under: 'abaixo', paused: 'pausada', winner: 'vencedor', loser: 'perdedor', inconclusive: 'inconclusivo', real: 'real', synthetic: 'sintético', derived: 'derivado', critical: 'crítico', warning: 'atenção', active: 'ativa' };

export function format(kind, v) {
  if (v === null || v === undefined || v === '') return '—';
  switch (kind) {
    case 'int': return isNum(v) ? NF[0].format(v) : esc(v);
    case 'compact': return isNum(v) ? compact(v) : esc(v);
    case 'pct': return isNum(v) ? NF[2].format(v) + '%' : esc(v);
    case 'pct1': return isNum(v) ? NF[1].format(v) + '%' : esc(v);
    case 'money': return isNum(v) ? MONEY0.format(v) : esc(v);
    case 'money2': return isNum(v) ? MONEY2.format(v) : esc(v);
    case 'num2': return isNum(v) ? NF[2].format(v) : esc(v);
    case 'num4': return isNum(v) ? NF[4].format(v) : esc(v);
    case 'ms': return isNum(v) ? NF[0].format(v) + ' ms' : esc(v);
    case 'date': return esc(dateBR(v));
    case 'month': return esc(monthBR(v));
    case 'bool': return v ? 'sim' : 'não';
    case 'badge': return `<span class="status-tag ${esc(v)}">${esc(BADGE_LABEL[v] ?? String(v).replace('_', ' '))}</span>`;
    default: return esc(v);
  }
}
// formatos que já devolvem HTML seguro (não devem ser escapados de novo)
const HTML_FORMATS = new Set(['badge']);

export const get = (obj, path) => (path === '' || path == null ? obj : String(path).split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj));
const tpl = (t, item) => String(t).replace(/\{([\w.]+)\}/g, (_, k) => esc(get(item, k) ?? '—'));

/* ---------- rede e toasts ---------- */
let toastTimer;
export function toast(msg, bad = false) {
  const el = document.getElementById('toast'); if (!el) return;
  el.textContent = msg; el.className = 'toast show' + (bad ? ' error' : '');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => (el.className = 'toast'), 5200);
}
export async function api(url, opts = {}) {
  let r; try { r = await fetch(url, opts); } catch { throw new Error('Não foi possível conectar à API. Execute: python run.py'); }
  if (r.status === 304) return null;
  let data = null; try { data = await r.json(); } catch { if (!r.ok) throw new Error('Resposta inválida da API'); }
  if (!r.ok) {
    const d = data?.detail;
    // 422 de validação do FastAPI vem como lista [{loc, msg}]; mostra "campo: mensagem" em vez do JSON cru
    const text = typeof d === 'string' ? d : Array.isArray(d) ? d.map((x) => `${(x.loc || []).slice(1).join('.') || 'campo'}: ${x.msg}`).join('; ') : d?.message ?? JSON.stringify(d);
    const e = new Error(text); e.detail = d; e.status = r.status; throw e;
  }
  return data;
}

/* ---------- gráficos SVG ---------- */
const PALETTE = ['#6c62e8', '#32bbbd', '#efaa6a', '#86b2ef', '#e07a8f'];
export const palette = PALETTE;
const niceTicks = (min, max, n = 4) => Array.from({ length: n + 1 }, (_, i) => min + ((max - min) * i) / n);

function lineChart(w, data, width) {
  const pts = get(data, w.path) || [];
  if (!pts.length) return '<div class="dk-empty">Sem dados no período.</div>';
  const series = w.series; const W = Math.max(320, width || 700), H = 260, L = w.normalize ? 14 : 52, R = 14, T = 16, B = 30;
  const pw = W - L - R, ph = H - T - B; const n = pts.length;
  const xAt = (i) => L + (n === 1 ? pw / 2 : (i * pw) / (n - 1));
  const vals = (k) => pts.map((p) => Number(p[k]));
  let lo = Infinity, hi = -Infinity;
  if (!w.normalize) series.forEach((s) => vals(s.key).forEach((v) => { if (v < lo) lo = v; if (v > hi) hi = v; }));
  if (!w.normalize) { const pad = (hi - lo || Math.abs(hi) || 1) * 0.08; lo -= pad; hi += pad; }
  const yScale = (k) => { if (w.normalize) { const mx = Math.max(1, ...vals(k)); return (v) => T + ph - (v / mx) * (ph - 12); } return (v) => T + ph - ((v - lo) / (hi - lo || 1)) * ph; };
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(w.title)}" class="dk-svg">`;
  const grid = niceTicks(0, 1, 4);
  grid.forEach((g) => { const y = T + ph - g * ph; svg += `<line x1="${L}" x2="${W - R}" y1="${y}" y2="${y}" stroke="#edf0f7" stroke-dasharray="4 5"/>`; if (!w.normalize) svg += `<text x="${L - 8}" y="${y + 3}" text-anchor="end" class="dk-tick">${format(w.format || 'num2', lo + (hi - lo) * g).replace(/<[^>]+>/g, '')}</text>`; });
  series.forEach((s, si) => {
    const color = PALETTE[si % PALETTE.length]; const ys = yScale(s.key); const v = vals(s.key);
    const d = v.map((val, i) => `${i ? 'L' : 'M'}${xAt(i).toFixed(1)},${ys(val).toFixed(1)}`).join(' ');
    if (series.length === 1) svg += `<path d="${d} L${xAt(n - 1).toFixed(1)},${T + ph} L${xAt(0).toFixed(1)},${T + ph} Z" fill="${color}" opacity=".08"/>`;
    svg += `<path d="${d}" fill="none" stroke="${color}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>`;
    svg += `<circle cx="${xAt(n - 1).toFixed(1)}" cy="${ys(v[n - 1]).toFixed(1)}" r="4" fill="#fff" stroke="${color}" stroke-width="2.4"/>`;
  });
  for (let i = 0; i < 6; i++) { const j = Math.min(n - 1, Math.round((i * (n - 1)) / 5)); svg += `<text x="${xAt(j)}" y="${H - 8}" text-anchor="middle" class="dk-tick">${esc(monthOrDay(pts[j][w.x], pts))}</text>`; }
  const bw = Math.max(4, pw / n);
  pts.forEach((p, i) => { const tip = `${dateBR(p[w.x])} — ` + series.map((s) => `${s.label}: ${format(w.format || 'int', p[s.key]).replace(/<[^>]+>/g, '')}`).join(' · '); svg += `<rect x="${(xAt(i) - bw / 2).toFixed(1)}" y="${T}" width="${bw.toFixed(1)}" height="${ph}" fill="transparent"><title>${esc(tip)}</title></rect>`; });
  svg += '</svg>';
  const legend = series.length > 1 ? `<div class="dk-legend">${series.map((s, i) => `<span><i class="dot" style="background:${PALETTE[i % PALETTE.length]}"></i>${esc(s.label)}</span>`).join('')}</div>` : '';
  const note = w.normalize ? '<div class="vital-note">Séries normalizadas individualmente para comparar tendências; valores absolutos estão nos KPIs.</div>' : '';
  return legend + svg + note;
}
function monthOrDay(iso, pts) {
  const span = pts.length > 1 ? (new Date(pts[pts.length - 1].date || iso) - new Date(pts[0].date || iso)) / 864e5 : 0;
  const d = new Date(String(iso).slice(0, 10) + 'T12:00:00'); if (isNaN(d)) return String(iso);
  return span > 200 ? `${MONTHS[d.getMonth()]}/${String(d.getFullYear()).slice(2)}` : `${String(d.getDate()).padStart(2, '0')} ${MONTHS[d.getMonth()]}`;
}

function barsChart(w, data, width) {
  const pts = get(data, w.path) || [];
  if (!pts.length) return '<div class="dk-empty">Sem dados no período.</div>';
  const vals = pts.map((p) => Number(p[w.value])); const W = Math.max(320, width || 700), H = 240, L = 40, R = 10, T = 18, B = 30;
  const lo = Math.min(0, ...vals), hi = Math.max(0, ...vals), span = hi - lo || 1; const pw = W - L - R, ph = H - T - B;
  const y = (v) => T + ph - ((v - lo) / span) * ph; const bw = pw / pts.length; const zero = y(0);
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(w.title)}" class="dk-svg"><line x1="${L}" x2="${W - R}" y1="${zero}" y2="${zero}" stroke="#cfd6e4"/>`;
  [hi, lo].forEach((v) => { svg += `<text x="${L - 6}" y="${y(v) + 3}" text-anchor="end" class="dk-tick">${format(w.format || 'num2', v).replace(/<[^>]+>/g, '')}</text>`; });
  const every = Math.ceil(pts.length / 12);
  pts.forEach((p, i) => {
    const v = vals[i]; const x = L + i * bw + bw * 0.15; const top = Math.min(y(v), zero); const h = Math.abs(y(v) - zero);
    svg += `<rect x="${x.toFixed(1)}" y="${top.toFixed(1)}" width="${(bw * 0.7).toFixed(1)}" height="${Math.max(h, 1).toFixed(1)}" rx="3" fill="${v < 0 ? '#e07a8f' : '#6c62e8'}" opacity=".9"><title>${esc(format(w.label_format || 'text', p[w.label]).replace(/<[^>]+>/g, ''))}: ${esc(format(w.format || 'num2', v))}</title></rect>`;
    if (i % every === 0) svg += `<text x="${(x + bw * 0.35).toFixed(1)}" y="${H - 9}" text-anchor="middle" class="dk-tick">${esc(format(w.label_format || 'text', p[w.label]).replace(/<[^>]+>/g, ''))}</text>`;
  });
  return svg + '</svg>';
}

function donut(w, data) {
  const items = get(data, w.path) || []; const sum = items.reduce((a, x) => a + Number(x[w.value] || 0), 0) || 1;
  if (!items.length) return '<div class="dk-empty">Sem dados.</div>';
  let start = 0; const slices = items.map((d, i) => { const v = (Number(d[w.value]) / sum) * 100; const s = start; start += v; return `${PALETTE[i % PALETTE.length]} ${s.toFixed(2)}% ${start.toFixed(2)}%`; }).join(',');
  const legend = items.map((d, i) => `<div class="donut-row"><span><i class="dot" style="background:${PALETTE[i % PALETTE.length]}"></i>${esc(d[w.label])}</span><strong>${NF[1].format((Number(d[w.value]) / sum) * 100)}%</strong></div>`).join('');
  return `<div class="donut-layout"><div class="donut" role="img" aria-label="${esc(w.title)}" style="border-radius:50%;background:conic-gradient(${slices});position:relative"><div class="donut-hole"><span>${esc(w.center_label || '')}</span><strong>${compact(sum)}</strong></div></div><div class="donut-legend">${legend}</div></div>`;
}

function funnel(w, data) {
  const o = get(data, w.path) || {}; const top = Math.max(Number(o[w.stages[0].key]) || 0, 1);
  const rows = w.stages.map((s, i) => { const v = Number(o[s.key]) || 0; const prev = i ? Number(o[w.stages[i - 1].key]) || 0 : null; const step = prev ? ` · ${NF[1].format((v / prev) * 100)}% da etapa anterior` : '';
    return `<div class="funnel-row"><div class="funnel-label"><span>${esc(s.label)}</span><strong>${NF[0].format(v)}</strong></div><div class="bar-track"><div class="bar-fill" style="width:${v > 0 ? Math.max(1.5, (100 * v) / top).toFixed(3) : 0}%"></div></div><div class="vital-note">${NF[1].format((v / top) * 100)}% do topo${step}</div></div>`; }).join('');
  return rows;
}

function vitals(w, data) {
  const items = get(data, w.path) || []; if (!items.length) return '<div class="dk-empty">Sem dados.</div>';
  const label = { good: 'bom', 'needs-improvement': 'precisa melhorar', poor: 'ruim' };
  return items.map((v) => { const max = v.poor * 1.4; const pos = Math.min(100, (v.p75 / max) * 100); const gs = (v.good / max) * 100, ps = (v.poor / max) * 100;
    const val = v.id === 'cls' ? NF[2].format(v.p75) : NF[0].format(v.p75) + ' ' + v.unit;
    const goal = v.id === 'cls' ? NF[2].format(v.good) : NF[0].format(v.good) + ' ' + v.unit;
    return `<div class="vital-row"><div class="vital-header"><span>${esc(v.name)}</span><strong>${val} <span class="status-tag ${esc(v.status)}">${label[v.status]}</span></strong></div><div class="vital-track" style="background:linear-gradient(90deg,#8ddebf 0 ${gs}%,#f8d286 ${gs}% ${ps}%,#f2a1a7 ${ps}% 100%)"><span class="vital-pin" style="left:${pos}%"></span></div><div class="vital-note">p75 de ${v.samples} medições · meta ≤ ${goal}</div></div>`; }).join('') + '<div class="vital-note">Valores simulados, não coletados por RUM.</div>';
}

function sortRows(rows, key, dir) { return [...rows].sort((a, b) => { const x = get(a, key), y = get(b, key); const nx = isNum(x) && isNum(y); const c = nx ? Number(x) - Number(y) : String(x ?? '').localeCompare(String(y ?? ''), 'pt-BR'); return dir === 'asc' ? c : -c; }); }
function tableHtml(w, rows, sort) {
  if (!rows.length) return '<div class="dk-empty">Sem dados.</div>';
  const data = sort.key ? sortRows(rows, sort.key, sort.dir) : rows;
  const head = w.columns.map((c) => `<th><button class="dk-sort" data-key="${esc(c.key)}" aria-label="Ordenar por ${esc(c.label)}">${esc(c.label)}${sort.key === c.key ? (sort.dir === 'asc' ? ' ▲' : ' ▼') : ''}</button></th>`).join('');
  const body = data.map((r) => `<tr>${w.columns.map((c) => { const v = get(r, c.key); return `<td>${HTML_FORMATS.has(c.format) ? format(c.format, v) : format(c.format || 'text', v)}</td>`; }).join('')}</tr>`).join('');
  return `<div class="table-scroll"><table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>${w.footnote ? `<p class="footnote">${esc(w.footnote)}</p>` : ''}`;
}

function listHtml(w, data) {
  let items = get(data, w.path) || []; if (w.limit) items = items.slice(0, w.limit);
  if (!items.length) return `<div class="dk-empty">${esc(w.empty || 'Sem itens.')}</div>`;
  return items.map((it) => `<div class="audit-row"><span><strong>${tpl(w.primary, it)}</strong>${w.secondary ? `<br><small>${tpl(w.secondary, it)}</small>` : ''}</span>${w.badge && it[w.badge] ? `<span class="status-tag ${esc(it[w.badge])}">${esc(BADGE_LABEL[it[w.badge]] ?? it[w.badge])}</span>` : ''}</div>`).join('');
}

function kpis(w, data) {
  const cards = w.items.map((it, idx) => {
    const raw = get(data, it.path); const val = raw == null ? '—' : (it.prefix ?? '') + format(it.format || 'text', raw) + (it.suffix ?? '');
    let delta = ''; const d = it.delta_path ? get(data, it.delta_path) : null;
    if (isNum(d)) { const good = it.delta_good ?? 'up'; const up = Number(d) > 0; const cls = Number(d) === 0 || good === 'none' ? 'neutral' : (up === (good === 'up') ? 'pos' : 'neg'); const unit = it.delta_unit ?? '%'; delta = `<span class="kpi-delta ${cls}" title="vs. período anterior">${up ? '▲' : Number(d) < 0 ? '▼' : '•'} ${NF[unit === 'p.p.' ? 2 : 1].format(Math.abs(Number(d)))} ${esc(unit)}</span>`; }
    let foot = it.foot ? esc(it.foot) : '';
    if (it.foot_path) { const fv = get(data, it.foot_path); if (fv != null) foot = esc(it.foot_prefix ?? '') + (it.foot_format === 'month' ? esc(monthBR(fv)) : format(it.foot_format || (/date|as_of/.test(it.foot_path) ? 'date' : 'text'), fv)) + esc(it.foot_suffix ?? ''); }
    return `<div class="kpi-card ${w.compact ? 'kpi-compact' : ''}"><div class="kpi-top"><span>${esc(it.label)}</span>${it.icon && !w.compact ? `<span class="kpi-icon">${esc(it.icon)}</span>` : ''}</div><div class="kpi-number">${val}</div><div class="kpi-foot">${delta}${foot ? `<span>${foot}</span>` : ''}</div></div>`; });
  return `<div class="kpi-grid">${cards.join('')}</div>`;
}

function notes(w) { return `<ul class="checks">${w.items.map((i) => `<li>${esc(i)}</li>`).join('')}</ul>`; }

/* ---------- renderização do dashboard ---------- */
const BODY = { line: lineChart, bars: barsChart, donut, funnel, vitals, list: listHtml, notes };

export async function renderDashboard(root, spec) {
  const state = {}; (spec.filters || []).forEach((f) => (state[f.id] = f.default));
  const filters = (spec.filters || []).map((f) => `<label class="select-wrap">${esc(f.label)} <select data-filter="${esc(f.id)}">${f.options.map((o) => `<option value="${esc(o.value)}"${String(o.value) === String(f.default) ? ' selected' : ''}>${esc(o.label)}</option>`).join('')}</select></label>`).join('');
  root.innerHTML = `<div class="page-heading"><div><div class="eyebrow">${esc(spec.eyebrow || '')} <span class="eyebrow-line"></span></div><h1>${esc(spec.title)}</h1><p>${esc(spec.subtitle || '')}</p></div><div class="heading-actions">${filters}</div></div>${spec.notice ? `<div class="demo-alert dk-notice"><span class="alert-icon">ⓘ</span><span>${esc(spec.notice)}</span></div>` : ''}<div class="dk-grid" aria-live="polite">${spec.widgets.map((w, i) => widgetShell(w, i)).join('')}</div>`;
  const sortState = {}; let cache = {};
  const sourceUrl = (name) => { const s = spec.sources[name]; const qs = new URLSearchParams(); (s.params || []).forEach((p) => qs.set(p, state[p])); const q = qs.toString(); return s.url + (q ? (s.url.includes('?') ? '&' : '?') + q : ''); };
  const paint = () => spec.widgets.forEach((w, i) => paintWidget(root, spec, w, i, cache, sortState, sourceUrl, state));
  async function load() {
    root.querySelector('.dk-grid').classList.add('loading');
    const names = Object.keys(spec.sources);
    const results = await Promise.allSettled(names.map((n) => api(sourceUrl(n))));
    cache = {}; names.forEach((n, i) => (cache[n] = results[i].status === 'fulfilled' ? { data: results[i].value } : { error: results[i].reason.message }));
    root.querySelector('.dk-grid').classList.remove('loading'); paint();
  }
  root.querySelectorAll('[data-filter]').forEach((el) => el.addEventListener('change', () => { state[el.dataset.filter] = el.value; load(); }));
  await load();
}

function widgetShell(w, i) {
  const span = w.span ? ` dk-span-${w.span}` : (w.type === 'kpis' ? ' dk-span-3' : '');
  if (w.type === 'kpis') return `<div class="dk-w${span}" id="dkw-${i}"></div>`;
  const head = `<div class="panel-head"><div>${w.kicker ? `<div class="panel-kicker">${esc(w.kicker)}</div>` : ''}${w.title ? `<h2>${esc(w.title)}</h2>` : ''}${w.subtitle ? `<p>${esc(w.subtitle)}</p>` : ''}</div>${w.export ? `<a class="btn btn-outline" id="dkx-${i}" href="#" download>${esc(w.export.label || 'Exportar')}</a>` : ''}</div>`;
  return `<article class="panel dk-w${span}" id="dkw-${i}">${head}<div class="dk-body"></div></article>`;
}

function paintWidget(root, spec, w, i, cache, sortState, sourceUrl, state) {
  const host = root.querySelector(`#dkw-${i}`); if (!host) return;
  const src = cache[w.source || 'main'] || {};
  const body = w.type === 'kpis' ? host : host.querySelector('.dk-body');
  if (src.error) { body.innerHTML = `<div class="dk-error">Não foi possível carregar: ${esc(src.error)}</div>`; return; }
  if (w.type === 'calculator') { mountCalculator(body, w.calc); return; }
  if (w.type === 'kpis') { host.innerHTML = kpis(w, src.data); return; }
  if (w.type === 'table') {
    const rows = get(src.data, w.path) || []; const st = sortState[i] || (sortState[i] = {});
    const draw = () => { body.innerHTML = tableHtml(w, rows, st); body.querySelectorAll('.dk-sort').forEach((b) => b.addEventListener('click', () => { st.dir = st.key === b.dataset.key && st.dir === 'asc' ? 'desc' : 'asc'; st.key = b.dataset.key; draw(); })); };
    draw();
    if (w.export) { const a = root.querySelector(`#dkx-${i}`); const qs = new URLSearchParams(); (w.export.params || []).forEach((p) => qs.set(p, state[p])); if (a) a.href = w.export.url + '?' + qs; }
    return;
  }
  body.innerHTML = (BODY[w.type] || (() => `<div class="dk-error">Widget desconhecido: ${esc(w.type)}</div>`))(w, src.data, Math.round(body.clientWidth));
}
