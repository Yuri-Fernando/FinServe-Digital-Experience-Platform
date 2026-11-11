/* Content Studio: workflow editorial com compliance ao vivo, prévia com tokens reais, diff de versões e auditoria. */
import { api, esc, format, toast } from '../dashkit/kit.js';

const FIELDS = { key: 'fKey', component: 'fComponent', eyebrow: 'fEyebrow', title: 'fTitle', body: 'fBody', cta_label: 'fCtaLabel', cta_url: 'fCtaUrl', segment: 'fSegment' };
const TOKENS = ['selic_meta', 'cdi_anual', 'ipca_12m', 'usd_brl'];

export async function mountStudio(root) {
  const st = { items: [], selected: null, creating: false, tokens: {}, timer: null };
  root.innerHTML = `
  <div class="page-heading"><div><div class="eyebrow">CONTENT OPERATIONS <span class="eyebrow-line"></span></div><h1>Content Studio <span class="heading-muted">/ Authoring</span></h1><p>Crie, revise, aprove e publique conteúdo com compliance automático e trilha de auditoria.</p></div><button class="btn btn-primary" id="sNew">+ Novo componente</button></div>
  <div class="studio-stats" id="sStats"></div>
  <div class="content-layout">
    <article class="panel content-list-panel"><div class="panel-head"><div><div class="panel-kicker">COMPONENT LIBRARY</div><h2>Itens editoriais</h2></div><span class="muted-chip" id="sCount">—</span></div><div class="content-items" id="sItems"></div></article>
    <article class="panel editor-panel"><div class="panel-head"><div><div class="panel-kicker">EDITOR</div><h2>Editor de conteúdo</h2></div><span id="sStatus" class="status-tag DRAFT">DRAFT</span></div>
      <div class="form-grid">
        <label>Identificador técnico<input id="fKey" placeholder="banner-exemplo" autocomplete="off"></label>
        <label>Componente<select id="fComponent"><option value="campaignhero">Campaign Hero</option><option value="promobanner">Promo Banner</option><option value="ratecard">Rate Card (dados de mercado)</option></select></label>
        <label class="span2">Eyebrow<input id="fEyebrow" placeholder="Ex: Novidade"></label>
        <label class="span2">Título<input id="fTitle" placeholder="Título principal"></label>
        <label class="span2">Descrição<textarea id="fBody" rows="3" placeholder="Texto do componente"></textarea>
          <div class="tok-row" id="sTokens" aria-label="Inserir token de mercado"></div></label>
        <label>Texto do botão<input id="fCtaLabel" placeholder="Saiba mais"></label>
        <label>URL interna da CTA<input id="fCtaUrl" placeholder="/solucoes"></label>
        <label>Segmento<select id="fSegment"><option value="all">Todos</option><option value="investidor">Investidor</option><option value="credito">Crédito</option><option value="jovem">Jovem</option></select></label>
        <label>Persona demo<select id="fRole"><option value="author">Autor</option><option value="reviewer">Revisor</option><option value="publisher">Publicador</option></select></label>
      </div>
      <div class="editor-actions"><button class="btn btn-primary" data-act="save">Salvar versão</button><button class="btn btn-outline" data-act="submit">Enviar revisão</button><button class="btn btn-outline" data-act="approve">Aprovar</button><button class="btn btn-outline" data-act="reject">Rejeitar</button><button class="btn btn-dark" data-act="publish">Publicar</button><button class="btn btn-outline" data-act="archive">Arquivar</button></div>
      <div class="editor-hint">Fluxo: Autor → Revisor → Publicador. O compliance roda ao digitar e bloqueia “Enviar revisão” e “Publicar”. Papéis são simulação, não autenticação.</div>
    </article>
  </div>
  <div class="studio-side">
    <article class="panel"><div class="panel-head"><div><div class="panel-kicker">COMPLIANCE EDITORIAL</div><h2>Revisão automática</h2><p id="cmpMeta">Regras YAML versionadas · heurísticas educacionais, não parecer jurídico.</p></div></div><div id="cmpOut"></div></article>
    <article class="panel"><div class="panel-head"><div><div class="panel-kicker">PRÉVIA (PUBLISH)</div><h2>Como o cliente verá</h2><p>Tokens resolvidos com dados reais do Banco Central.</p></div></div><div id="sPreview"></div></article>
  </div>
  <div class="studio-side">
    <article class="panel"><div class="panel-head"><div><div class="panel-kicker">VERSÕES</div><h2>Histórico e diff</h2></div></div><div id="sRevs"></div><div id="sDiff"></div></article>
    <article class="panel audit-panel"><div class="panel-head"><div><div class="panel-kicker">AUDIT TRAIL</div><h2>Últimas atividades</h2></div></div><div id="sAudit"></div></article>
  </div>`;
  const $ = (id) => root.querySelector('#' + id);
  const role = () => $('fRole').value;
  const hdr = () => ({ 'Content-Type': 'application/json', 'X-Demo-Role': role() });

  $('sTokens').innerHTML = '<small style="width:100%;color:#97a2b5">Inserir dado de mercado:</small>' + TOKENS.map((t) => `<button type="button" class="tok" data-tok="${t}">{{${t}}}</button>`).join('');
  $('sTokens').addEventListener('click', (e) => { const t = e.target.dataset?.tok; if (!t) return; const ta = $('fBody'); const s = ta.selectionStart ?? ta.value.length; ta.value = ta.value.slice(0, s) + `{{${t}}}` + ta.value.slice(ta.selectionEnd ?? s); ta.focus(); onInput(); });

  const read = () => Object.fromEntries(Object.entries(FIELDS).map(([k, id]) => [k, $(id).value.trim()]));
  const resolve = (t) => String(t ?? '').replace(/\{\{\s*([a-z0-9_]+)\s*\}\}/g, (_, k) => st.tokens[k] ?? '—');

  function renderPreview() {
    const v = read();
    $('sPreview').innerHTML = `<div class="preview-card"><span class="hero-brow">${esc(resolve(v.eyebrow) || 'Eyebrow')}</span><h3>${esc(resolve(v.title) || 'Título')}</h3><p>${esc(resolve(v.body) || 'Descrição do componente.')}</p><span class="hero-cta">${esc(resolve(v.cta_label) || 'CTA')} ↗</span></div>`;
  }
  function renderCompliance(r) {
    if (!r) { $('cmpOut').innerHTML = '<div class="dk-empty">Digite para avaliar.</div>'; return; }
    const head = `<div class="cmp-summary"><span class="status-tag ${r.passed ? 'good' : 'block'}">${r.passed ? 'sem bloqueios' : 'bloqueado'}</span><span>${r.blocking} bloqueio(s) · ${r.warnings} aviso(s) · regras v${esc(r.rules_version)}</span></div>`;
    const list = r.issues.map((i) => `<div class="cmp-issue ${esc(i.severity)}"><strong>${esc(i.rule_id)} · ${esc(i.name)}</strong> <span class="status-tag ${i.severity === 'block' ? 'block' : 'warn'}">${i.severity === 'block' ? 'bloqueia' : 'aviso'}</span><br>${esc(i.message)}<small>Campo: ${esc(i.field)} · trecho: “${esc(i.match)}” · ${esc(i.reason_code)}</small>${i.suggestion ? `<small>Sugestão: ${esc(i.suggestion)}</small>` : ''}</div>`).join('');
    $('cmpOut').innerHTML = head + (list || '<div class="dk-empty">Nenhuma ocorrência.</div>');
  }
  async function check() { try { renderCompliance(await api('/api/experience/compliance/check', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(read()) })); } catch (e) { $('cmpOut').innerHTML = `<div class="dk-error">${esc(e.message)}</div>`; } }
  function onInput() { renderPreview(); clearTimeout(st.timer); st.timer = setTimeout(check, 350); }
  Object.values(FIELDS).forEach((id) => $(id).addEventListener('input', onInput));

  function renderItems() {
    $('sCount').textContent = st.items.length + ' ITENS';
    $('sItems').innerHTML = st.items.map((x) => `<button class="content-item ${st.selected?.id === x.id ? 'selected' : ''}" data-id="${x.id}"><span><strong>${esc(x.title)}</strong><small>${esc(x.key)} · v${x.version} · ${esc(x.segment)} · ${esc(x.component)}</small></span><span class="status-tag ${esc(x.status)}">${esc(x.status)}</span></button>`).join('');
    $('sItems').querySelectorAll('[data-id]').forEach((b) => (b.onclick = () => select(+b.dataset.id)));
  }
  function fill(item) {
    Object.entries(FIELDS).forEach(([k, id]) => ($(id).value = item?.[k] ?? ''));
    if (!item) { $('fComponent').value = 'promobanner'; $('fSegment').value = 'all'; }
    $('fKey').disabled = $('fComponent').disabled = !!item; renderPreview(); check();
  }
  async function select(id) {
    st.selected = st.items.find((x) => x.id === id) || null; st.creating = false; if (!st.selected) return;
    fill(st.selected); $('sStatus').textContent = `${st.selected.status} · v${st.selected.version}`; $('sStatus').className = 'status-tag ' + st.selected.status; renderItems();
    try {
      const d = await api('/api/experience/content/' + id); renderCompliance(d.compliance);
      $('sRevs').innerHTML = d.revisions.map((r) => `<div class="rev-row"><span><strong>v${r.version}</strong> · ${esc(r.actor)} · ${esc(r.reason)}<br><small>${esc(format('date', r.created_at))} ${esc(r.created_at.slice(11, 16))}</small></span>${r.version !== d.content.version ? `<button class="btn btn-outline" data-v="${r.version}">comparar com v${d.content.version}</button>` : '<span class="muted-chip">ATUAL</span>'}</div>`).join('');
      $('sDiff').innerHTML = '';
      $('sRevs').querySelectorAll('[data-v]').forEach((b) => (b.onclick = async () => { try { const df = await api(`/api/experience/content/${id}/diff?from_version=${b.dataset.v}&to_version=${d.content.version}`); $('sDiff').innerHTML = df.changes.length ? df.changes.map((c) => `<div class="diff-row"><strong>${esc(c.field)}</strong><br><del>${esc(c.from)}</del><br><ins>${esc(c.to)}</ins></div>`).join('') : '<div class="dk-empty">Sem diferenças entre as versões.</div>'; } catch (e) { toast(e.message, true); } }));
    } catch (e) { toast(e.message, true); }
  }
  function blank() { st.selected = null; st.creating = true; fill(null); $('sStatus').textContent = 'NEW DRAFT'; $('sStatus').className = 'status-tag DRAFT'; $('sRevs').innerHTML = '<div class="dk-empty">Salve o rascunho para criar a v1.</div>'; $('sDiff').innerHTML = ''; renderItems(); }

  async function load(keepId) {
    const [items, stats, audit] = await Promise.all([api('/api/experience/content'), api('/api/experience/stats'), api('/api/platform/audit?module=experience&limit=10')]);
    st.items = items;
    $('sStats').innerHTML = [['Componentes', stats.total], ['Em revisão', stats.by_status.IN_REVIEW], ['Aprovados', stats.by_status.APPROVED], ['Publicados', stats.by_status.PUBLISHED]].map(([l, v]) => `<div class="kpi-card kpi-compact"><div class="kpi-top"><span>${l}</span></div><div class="kpi-number">${v}</div></div>`).join('');
    $('sAudit').innerHTML = audit.map((a) => `<div class="audit-row"><span><strong>${esc(a.actor)}</strong> · ${esc(a.action)} ${a.entity_id ? '· #' + a.entity_id : ''}${a.notes && a.notes !== 'Dados de demonstração' ? `<br><small>${esc(a.notes)}</small>` : ''}</span><small>${esc(a.occurred_at.replace('T', ' ').slice(0, 16))}</small></div>`).join('');
    if (st.creating) blank(); else await select(items.some((x) => x.id === keepId) ? keepId : items[0]?.id);
  }

  async function save() {
    try {
      const data = read(); let r;
      if (st.creating) r = await api('/api/experience/content', { method: 'POST', headers: hdr(), body: JSON.stringify(data) });
      else { if (!st.selected) throw new Error('Selecione um item'); const { key, component, ...rest } = data; r = await api('/api/experience/content/' + st.selected.id, { method: 'PUT', headers: hdr(), body: JSON.stringify({ ...rest, version: st.selected.version }) }); }
      st.creating = false; toast(`Versão salva: ${r.key} · v${r.version}`); await load(r.id);
    } catch (e) { toast(e.message, true); }
  }
  async function act(action) {
    if (!st.selected) return toast('Selecione um conteúdo', true);
    try { const it = await api(`/api/experience/content/${st.selected.id}/transition`, { method: 'POST', headers: hdr(), body: JSON.stringify({ action, notes: 'Ação no laboratório de demonstração' }) }); toast(`Ação ${action}: ${it.status}`); await load(it.id); }
    catch (e) { if (e.detail?.compliance) renderCompliance(e.detail.compliance); toast(e.message, true); }
  }
  // Trava de concorrência na UI: enquanto uma ação não termina (e a lista recarrega), as demais ficam desabilitadas.
  // Sem isso, um segundo clique rápido usaria `version` desatualizada e tomaria 409 (o servidor protege, mas a UX é ruim).
  let busy = false;
  const setBusy = (v) => { busy = v; root.querySelectorAll('[data-act]').forEach((b) => (b.disabled = v)); };
  const guarded = (fn) => async () => { if (busy) return; setBusy(true); try { await fn(); } finally { setBusy(false); } };
  root.querySelectorAll('[data-act]').forEach((b) => (b.onclick = guarded(() => (b.dataset.act === 'save' ? save() : act(b.dataset.act)))));
  $('sNew').onclick = blank;
  try { st.tokens = (await api('/api/market/tokens')).values; } catch { st.tokens = {}; }
  await load();
}
