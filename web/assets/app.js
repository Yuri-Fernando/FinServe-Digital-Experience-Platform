/* Shell da aplicação: monta a navegação a partir do registry de módulos e roteia por hash. */
import { api, esc, renderDashboard, toast } from './dashkit/kit.js';
import { mountStudio } from './pages/studio.js';
import { mountPortal } from './pages/portal.js';
import { mountArchitecture } from './pages/architecture.js';

const pages = [];
let current = null;

async function init() {
  let mods, dashes, health;
  try { [mods, dashes, health] = await Promise.all([api('/api/platform/modules'), api('/api/platform/dashboards'), api('/api/platform/health')]); }
  catch (e) { document.getElementById('pages').innerHTML = `<div class="dk-error" style="margin:30px">${esc(e.message)}</div>`; return; }
  const names = new Set(mods.map((m) => m.name));
  dashes.forEach((d) => pages.push({ id: d.id, label: d.nav.label || d.title, icon: d.nav.icon || '◆', order: d.nav.order ?? 50, group: d.nav.group || (d.nav.order >= 10 ? 'ENGENHARIA' : 'WORKSPACE'), kind: 'dash' }));
  if (names.has('experience')) {
    pages.push({ id: 'studio', label: 'Content Studio', icon: '▤', order: 3, group: 'WORKSPACE', kind: 'studio', dot: true });
    pages.push({ id: 'portal', label: 'Portal do cliente', icon: '▣', order: 4, group: 'WORKSPACE', kind: 'portal' });
  }
  pages.push({ id: 'architecture', label: 'Arquitetura', icon: '⌘', order: 11, group: 'ENGENHARIA', kind: 'architecture' });
  pages.sort((a, b) => a.order - b.order);
  const groups = [...new Set(pages.map((p) => p.group))];
  document.getElementById('nav').innerHTML = groups.map((g) => `<div class="nav-group-title">${esc(g)}</div><nav aria-label="${esc(g)}">${pages.filter((p) => p.group === g).map((p, i) => `<button class="nav-link" data-page="${esc(p.id)}"><span class="nav-ico">${esc(p.icon)}</span> ${esc(p.label)} ${p.dot ? '<span class="nav-dot"></span>' : `<span class="nav-shortcut">${String(p.order).padStart(2, '0')}</span>`}</button>`).join('')}</nav>`).join('');
  document.querySelectorAll('[data-page]').forEach((b) => b.addEventListener('click', () => go(b.dataset.page)));
  document.getElementById('apiStatus').innerHTML = `<strong>API online · v${esc(health.version)}</strong><small>${mods.length} módulos · AEM SDK não conectado</small>`;
  document.getElementById('toggleSidebar').onclick = () => document.getElementById('sidebar').classList.toggle('open');
  window.addEventListener('hashchange', () => go(location.hash.slice(1), false));
  go(pages.some((p) => p.id === location.hash.slice(1)) ? location.hash.slice(1) : pages[0].id);
}

async function go(id, push = true) {
  const page = pages.find((p) => p.id === id) || pages[0];
  if (!page) return;
  current = page.id;
  document.querySelectorAll('.nav-link').forEach((b) => b.classList.toggle('active', b.dataset.page === page.id));
  document.getElementById('breadcrumb').textContent = page.label;
  document.getElementById('sidebar').classList.remove('open');
  if (push) history.replaceState(null, '', '#' + page.id);
  const host = document.getElementById('pages');
  // O container precisa estar no DOM ANTES de renderizar: os gráficos medem a largura real (clientWidth).
  const root = document.createElement('section'); root.className = 'page active';
  root.innerHTML = '<div class="dk-empty" style="padding:40px">Carregando…</div>';
  host.replaceChildren(root);
  try {
    if (page.kind === 'dash') { const spec = await api('/api/platform/dashboards/' + page.id); await renderDashboard(root, spec); }
    else if (page.kind === 'studio') await mountStudio(root);
    else if (page.kind === 'portal') await mountPortal(root, { hasMarket: pages.some((p) => p.id === 'market') });
    else await mountArchitecture(root);
  } catch (e) { root.innerHTML = `<div class="dk-error" style="margin:20px 0">${esc(e.message)}</div>`; toast(e.message, true); }
}

init();
