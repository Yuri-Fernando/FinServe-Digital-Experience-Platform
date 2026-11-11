/* Portal do cliente (camada Publish): consome apenas /api/experience/delivery e mostra a resposta headless. */
import { api, esc, toast } from '../dashkit/kit.js';
import { mountCalculator } from '../dashkit/calculators.js';

const SEGMENTS = [['all', 'Público geral'], ['investidor', 'Investidor'], ['credito', 'Crédito'], ['jovem', 'Jovem']];

export async function mountPortal(root, { hasMarket }) {
  root.innerHTML = `
  <div class="page-heading"><div><div class="eyebrow">PUBLISH EXPERIENCE <span class="eyebrow-line"></span></div><h1>Portal do cliente <span class="heading-muted">/ Preview</span></h1><p>Canal Publish consumindo somente conteúdo publicado, com taxas reais do Banco Central resolvidas na entrega.</p></div>
    <label class="select-wrap">Persona <select id="pSeg">${SEGMENTS.map(([v, l]) => `<option value="${v}">${l}</option>`).join('')}</select></label></div>
  <div class="portal-frame"><div class="portal-bar"><div class="portal-brand"><span class="portal-logo">f.</span><strong>finserve</strong></div><div>Para você　　Soluções　　Investimentos　　Educação</div><span class="portal-login">Acessar conta <span>↗</span></span></div>
    <div id="pContent"></div>
    ${hasMarket ? `<div class="portal-section"><h3>Simule com taxas de hoje</h3><p>Cálculos educacionais baseados em CDI, Selic e IPCA reais publicados pelo Banco Central.</p><div class="portal-tabs"><button class="on" data-tab="investment">Investimentos</button><button data-tab="loan">Crédito</button></div><div id="pCalc"></div></div>` : ''}
    <div class="portal-footer"><span>FinServe — Experiência fictícia de portfólio</span><span>Somente demonstração • Sem produtos financeiros reais</span></div></div>
  <article class="panel dev-panel" style="margin-top:18px"><div class="panel-head"><div><div class="panel-kicker">CAMADA PUBLISH · HEADLESS</div><h2>Resposta da API de entrega</h2><p>O mesmo conteúdo em dois formatos: JSON simples e <code class="inline">.model.json</code> no estilo do Sling Model Exporter do AEM.</p></div></div>
    <div class="portal-tabs"><button class="on" data-shape="plain">/delivery</button><button data-shape="model">/model/{persona}.model.json</button><button class="btn-outline" id="pRevalidate">Revalidar (If-None-Match)</button></div>
    <div class="hdrs" id="pHdrs"></div><pre id="pJson" tabindex="0"></pre></article>`;
  const $ = (id) => root.querySelector('#' + id);
  let shape = 'plain', etag = null;

  async function fetchRaw(url, headers = {}) { const r = await fetch(url, { headers }); return { status: r.status, etag: r.headers.get('etag'), cache: r.headers.get('cache-control'), body: r.status === 200 ? await r.json() : null }; }
  const urlFor = (seg) => (shape === 'plain' ? `/api/experience/delivery?segment=${seg}` : `/api/experience/model/${seg}.model.json`);

  async function loadPortal() {
    const seg = $('pSeg').value;
    try {
      const plain = await fetchRaw(`/api/experience/delivery?segment=${seg}`);
      const items = plain.body.content;
      const hero = items.find((i) => i.component === 'campaignhero') || items[0];
      const cards = items.filter((i) => i.component !== 'campaignhero').map((i) => `<div class="portal-editorial-banner ${i.component === 'ratecard' ? 'portal-banner-ratecard' : ''}"><span>${esc(i.eyebrow)}</span><strong>${esc(i.title)}</strong><p>${esc(i.body)}</p></div>`).join('');
      $('pContent').innerHTML = `<div class="hero-portal"><div class="hero-copy"><span class="hero-brow">${esc(hero?.eyebrow || 'FINANCE EXPERIENCE')}</span><h2>${esc(hero?.title || 'Seu dinheiro, novas possibilidades')}</h2><p>${esc(hero?.body || '')}</p><a class="hero-cta" href="#portal" onclick="event.preventDefault()">${esc(hero?.cta_label || 'Explorar')} ↗</a></div><div class="hero-visual"><div class="orb"></div><div class="credit-card"><small>FINSERVE · DIGITAL</small><strong>finserve.</strong><div class="card-number">••••　••••　••••　2046</div></div></div></div>${cards ? `<div class="portal-banners">${cards}</div>` : ''}<div class="portal-features"><div class="portal-feature"><span>◈</span><h3>Investimentos</h3><p>Simulações claras para decisões mais conscientes.</p></div><div class="portal-feature"><span>◎</span><h3>Crédito responsável</h3><p>Conheça alternativas e simule antes de contratar.</p></div><div class="portal-feature"><span>▤</span><h3>Conta digital</h3><p>Uma experiência descomplicada no seu dia a dia.</p></div></div>`;
      await showPayload();
    } catch (e) { toast(e.message, true); }
  }
  async function showPayload() {
    const seg = $('pSeg').value; const r = await fetchRaw(urlFor(seg)); etag = r.etag;
    $('pHdrs').innerHTML = `<code class="inline">GET ${esc(urlFor(seg))}</code><br>Status <strong>${r.status}</strong> · ETag <code class="inline">${esc(r.etag || '—')}</code> · Cache-Control <code class="inline">${esc(r.cache || '—')}</code>`;
    $('pJson').textContent = JSON.stringify(r.body, null, 2);
  }
  $('pSeg').onchange = loadPortal;
  root.querySelectorAll('[data-shape]').forEach((b) => (b.onclick = async () => { shape = b.dataset.shape; root.querySelectorAll('[data-shape]').forEach((x) => x.classList.toggle('on', x === b)); await showPayload(); }));
  $('pRevalidate').onclick = async () => { const seg = $('pSeg').value; const r = await fetchRaw(urlFor(seg), etag ? { 'If-None-Match': etag } : {}); $('pHdrs').innerHTML += `<br>↻ Revalidação com <code class="inline">If-None-Match</code> → status <strong>${r.status}</strong> ${r.status === 304 ? '(Not Modified: o cache do edge seria reaproveitado)' : '(conteúdo mudou)'}`; };
  if (hasMarket) {
    const mount = (tab) => { root.querySelectorAll('[data-tab]').forEach((x) => x.classList.toggle('on', x.dataset.tab === tab)); mountCalculator($('pCalc'), tab); };
    root.querySelectorAll('[data-tab]').forEach((b) => (b.onclick = () => mount(b.dataset.tab)));
    mount('investment');
  }
  await loadPortal();
}
