import { api, esc } from '../dashkit/kit.js';

export async function mountArchitecture(root) {
  let mods = [];
  try { mods = await api('/api/platform/modules'); } catch { /* página funciona sem a API */ }
  root.innerHTML = `
  <div class="page-heading"><div><div class="eyebrow">ENGINEERING SYSTEM DESIGN <span class="eyebrow-line"></span></div><h1>Arquitetura <span class="heading-muted">/ Modular</span></h1><p>Um núcleo pequeno, módulos plugáveis e um kit de dashboards declarativo.</p></div><a class="btn btn-outline" href="/docs" target="_blank" rel="noopener">OpenAPI ↗</a></div>
  <article class="panel arch-panel"><div class="panel-kicker">FLUXO AUTHOR → PUBLISH</div>
    <div class="architecture-diagram"><div class="arch-node arch-editor"><small>AUTHOR</small><strong>Content Studio</strong><span>Workflow · compliance YAML · diff</span></div><div class="arch-arrow">→</div><div class="arch-node arch-aem"><small>PUBLISH API (LOCAL)</small><strong>/delivery · .model.json</strong><span>ETag · Cache-Control · tokens</span></div><div class="arch-arrow">←</div><div class="arch-node arch-market"><small>DADOS REAIS</small><strong>Banco Central</strong><span>SGS · Focus · snapshots</span></div></div>
    <div class="arch-sub"><span>Local e funcional: FastAPI + SQLite + JS sem bundler</span><span>Mapeamento para AEM em docs/ROADMAP_AEM.md — AEM SDK não executado</span></div></article>
  <div class="arch-grid">
    <article class="panel"><div class="panel-kicker">NÚCLEO</div><h2>Registry de módulos</h2><p>Cada módulo declara rotas, schema, seed, proveniência e dashboards. Habilite um subconjunto com <code>FINSERVE_MODULES</code> ou crie um com <code>finserve new-module</code>.</p><code>registry.Module(...)</code><code>/api/platform/modules</code></article>
    <article class="panel"><div class="panel-kicker">DASHKIT</div><h2>Dashboards como dados</h2><p>Um dashboard é um JSON: filtros, fontes e widgets (KPI, linha, barras, funil, tabela…). O mesmo renderizador serve qualquer módulo.</p><code>web/assets/dashkit/kit.js</code><code>/api/platform/dashboards/{id}</code></article>
    <article class="panel"><div class="panel-kicker">PROVENIÊNCIA</div><h2>Real × sintético</h2><p>Todo dataset é rotulado como real, sintético ou derivado, com fonte e data de coleta. Pontos futuros do SGS são descartados.</p><code>/api/platform/provenance</code><code>docs/DATA_CARD.md</code></article>
  </div>
  <article class="panel" style="margin-top:17px"><div class="panel-kicker">MÓDULOS ATIVOS</div><h2>${mods.length} carregado(s)</h2><div class="table-scroll"><table class="data-table"><thead><tr><th>Módulo</th><th>Versão</th><th>Tabelas</th><th>Dashboards</th><th>Depende de</th></tr></thead><tbody>${mods.map((m) => `<tr><td><strong>${esc(m.name)}</strong><br><small>${esc(m.description)}</small></td><td>${esc(m.version)}</td><td>${esc(m.tables.join(', ') || '—')}</td><td>${esc(m.dashboards.join(', ') || '—')}</td><td>${esc(m.requires.join(', ') || '—')}</td></tr>`).join('')}</tbody></table></div></article>`;
}
