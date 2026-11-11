/* Calculadoras de investimento e crédito — consomem /api/market/simulate/* (dados reais do BCB). */
import { api, esc, format, toast, dateBR } from './kit.js';

const field = (id, label, value, attrs = '') => `<label>${esc(label)}<input data-f="${id}" value="${esc(value)}" ${attrs} inputmode="decimal" autocomplete="off"></label>`;
const num = (v) => Number(String(v).replace(/\./g, '').replace(',', '.')) || Number(String(v).replace(',', '.'));
const readNum = (root, id) => { const v = root.querySelector(`[data-f="${id}"]`).value.trim(); return Number(v.includes(',') ? v.replace(/\./g, '').replace(',', '.') : v); };

export function mountCalculator(host, kind) {
  if (kind === 'investment') return investment(host);
  if (kind === 'loan') return loan(host);
  host.innerHTML = '<div class="dk-error">Calculadora desconhecida.</div>';
}

function marketLine(mi) {
  if (!mi) return '';
  const parts = [`CDI ${format('num2', mi.cdi_aa)}% a.a.`, `Selic meta ${format('num2', mi.selic_meta)}% a.a.`];
  if (mi.ipca_12m != null) parts.push(`IPCA 12m ${format('num2', mi.ipca_12m)}%`);
  return `<div class="calc-market"><span class="status-tag ${mi.overridden ? 'warning' : 'real'}">${mi.overridden ? 'taxas informadas' : 'dados reais · BCB'}</span> ${parts.join(' · ')} <small>(ref. ${esc(dateBR(mi.as_of))})</small></div>`;
}

function investment(host) {
  host.innerHTML = `<form class="calc-form form-grid" novalidate>${field('amount', 'Valor aplicado (R$)', '10000')}${field('months', 'Prazo (meses)', '12')}${field('pct_cdb', 'CDB — % do CDI', '100')}${field('pct_lci', 'LCI/LCA — % do CDI', '90')}<div class="span2"><button class="btn btn-primary" type="submit">Simular</button></div></form><div class="calc-out" aria-live="polite"></div>`;
  const out = host.querySelector('.calc-out'); const form = host.querySelector('form');
  const run = async (e) => {
    e?.preventDefault(); out.innerHTML = '<div class="dk-empty">Calculando…</div>';
    try {
      const r = await api('/api/market/simulate/investment', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ amount: readNum(form, 'amount'), months: Math.round(readNum(form, 'months')), pct_cdb: readNum(form, 'pct_cdb'), pct_lci: readNum(form, 'pct_lci') }) });
      const best = r.products[0].net_final; const base = r.inputs.amount;
      const rows = r.products.map((p, i) => `<tr><td><strong>${esc(p.label)}</strong><br><small>${esc(p.note)}</small></td><td>${format('money2', p.net_final)}${i === 0 ? ' <span class="status-tag winner">maior</span>' : ''}<div class="bar-track calc-bar"><div class="bar-fill" style="width:${Math.max(4, ((p.net_final - base) / Math.max(best - base, 1)) * 100).toFixed(1)}%"></div></div></td><td>${format('money2', p.net_gain)}</td><td>${format('pct', p.net_annual_pct)}</td><td>${p.ir ? `${format('money2', p.ir)} (${p.ir_rate_pct}%)` : 'isento'}</td><td>${p.real_return_pct == null ? '—' : format('pct', p.real_return_pct)}</td></tr>`).join('');
      out.innerHTML = `${marketLine(r.market_inputs)}<div class="table-scroll"><table class="data-table"><thead><tr><th>Produto</th><th>Valor líquido</th><th>Ganho líquido</th><th>% a.a. líquido</th><th>IR</th><th>Retorno real*</th></tr></thead><tbody>${rows}</tbody></table></div><ul class="calc-assume">${r.assumptions.map((a) => `<li>${esc(a)}</li>`).join('')}</ul><p class="footnote">* acima do IPCA acumulado em 12 meses, assumido constante.</p>`;
    } catch (err) { out.innerHTML = `<div class="dk-error">${esc(err.message)}</div>`; if (e) toast(err.message, true); }
  };
  form.addEventListener('submit', run); run();
}

function loan(host) {
  host.innerHTML = `<form class="calc-form form-grid" novalidate>${field('principal', 'Valor financiado (R$)', '10000')}${field('months', 'Prazo (meses)', '24')}${field('rate', 'Taxa de juros (% ao mês)', '2,5')}<label>Sistema<select data-f="system"><option value="price">Price (parcelas fixas)</option><option value="sac">SAC (parcelas decrescentes)</option></select></label>${field('fee', 'Tarifa inicial (R$)', '0')}<div class="span2"><button class="btn btn-primary" type="submit">Simular</button></div></form><div class="calc-out" aria-live="polite"></div>`;
  const out = host.querySelector('.calc-out'); const form = host.querySelector('form');
  const run = async (e) => {
    e?.preventDefault(); out.innerHTML = '<div class="dk-empty">Calculando…</div>';
    try {
      const r = await api('/api/market/simulate/loan', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ principal: readNum(form, 'principal'), months: Math.round(readNum(form, 'months')), rate_monthly_pct: readNum(form, 'rate'), system: form.querySelector('[data-f="system"]').value, upfront_fee: readNum(form, 'fee') || 0 }) });
      const s = r.summary; const ctx = r.market_context;
      const kp = [['Primeira parcela', format('money2', s.first_payment)], ['Total pago', format('money2', s.total_paid)], ['Juros totais', format('money2', s.total_interest)], ['CET (a.a.)', format('pct', s.cet_annual_pct)]].map(([l, v]) => `<div class="kpi-card kpi-compact"><div class="kpi-top"><span>${l}</span></div><div class="kpi-number">${v}</div></div>`).join('');
      const sched = r.schedule.map((x) => `<tr><td>${x.n}</td><td>${format('money2', x.payment)}</td><td>${format('money2', x.interest)}</td><td>${format('money2', x.amortization)}</td><td>${format('money2', x.balance)}</td></tr>`).join('');
      out.innerHTML = `<div class="kpi-grid calc-kpis">${kp}</div>${ctx ? `<div class="calc-market"><span class="status-tag real">dados reais · BCB</span> Selic meta ${format('num2', ctx.selic_meta_aa)}% a.a. ≈ ${format('num2', ctx.selic_meta_monthly_pct)}% a.m. · sua taxa está ${format('num2', Math.abs(ctx.spread_vs_selic_monthly_pp))} p.p. ${ctx.spread_vs_selic_monthly_pp >= 0 ? 'acima' : 'abaixo'} da Selic mensal<br><small>${esc(ctx.note)}</small></div>` : ''}<details class="calc-details"><summary>Ver cronograma de ${r.schedule.length} parcelas</summary><div class="table-scroll"><table class="data-table"><thead><tr><th>#</th><th>Parcela</th><th>Juros</th><th>Amortização</th><th>Saldo</th></tr></thead><tbody>${sched}</tbody></table></div></details><ul class="calc-assume">${r.assumptions.map((a) => `<li>${esc(a)}</li>`).join('')}</ul>`;
    } catch (err) { out.innerHTML = `<div class="dk-error">${esc(err.message)}</div>`; if (e) toast(err.message, true); }
  };
  form.addEventListener('submit', run); run();
}
