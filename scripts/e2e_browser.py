"""E2E de navegador (opcional, não roda no CI): percorre o workflow editorial, o portal, o mercado e o mobile.

Requisitos: `pip install playwright && playwright install chromium`.
Uso (com o servidor rodando em banco LIMPO, pois o fluxo publica conteúdo):
    FINSERVE_DB=/tmp/e2e.sqlite3 python run.py --port 8767
    python scripts/e2e_browser.py http://127.0.0.1:8767
"""
import sys, time
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8767"
errors, checks = [], []
def ok(name, cond):
    checks.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name.encode("ascii", "replace").decode())

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_context(viewport={"width": 1450, "height": 900}).new_page()
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "status of 4" not in m.text else None)

    def act(selector, expect, timeout=10000):
        """Clica e espera o toast com o texto esperado (toast limpo antes) + rede ociosa."""
        page.evaluate("document.getElementById('toast').textContent=''")
        page.click(selector)
        page.wait_for_function("t=>document.getElementById('toast').textContent.toLowerCase().includes(t)", arg=expect.lower(), timeout=timeout)
        page.wait_for_load_state("networkidle"); page.wait_for_function("()=>![...document.querySelectorAll('[data-act]')].some(b=>b.disabled)", timeout=timeout)

    page.goto(f"{BASE}/#studio"); page.wait_for_selector("#sItems .content-item")
    page.click("text=Benefícios que combinam com sua rotina"); page.wait_for_function("()=>document.getElementById('fKey').value==='banner-cartao'")
    page.fill("#fBody", "Retorno garantido de 20% ao ano, sem risco!")
    page.wait_for_function("()=>document.getElementById('cmpOut').innerText.includes('bloqueado')", timeout=8000)
    ok("compliance ao vivo mostra bloqueado + CMP001", "CMP001" in page.inner_text("#cmpOut"))
    act("[data-act=save]", "versão salva")
    act("[data-act=submit]", "compliance")
    ok("status segue DRAFT após bloqueio", "DRAFT" in page.inner_text("#sStatus"))
    page.fill("#fBody", "Ajuste benefícios de acordo com suas prioridades.")
    act("[data-act=save]", "versão salva")
    act("[data-act=submit]", "ação submit")
    ok("enviado para revisão", "IN_REVIEW" in page.inner_text("#sStatus"))
    page.select_option("#fRole", "author"); act("[data-act=approve]", "insuficiente")
    page.select_option("#fRole", "reviewer"); act("[data-act=approve]", "ação approve")
    page.select_option("#fRole", "publisher"); act("[data-act=publish]", "ação publish")
    ok("publicado", "PUBLISHED" in page.inner_text("#sStatus"))
    ok("histórico com 3 versões", page.locator("#sRevs .rev-row").count() == 3)
    page.click("#sRevs button:has-text('comparar')"); page.wait_for_selector("#sDiff .diff-row, #sDiff .dk-empty", timeout=8000)
    ok("diff exibido", page.locator("#sDiff .diff-row").count() >= 1)

    # clique duplo rápido não pode gerar 409 (trava de concorrência)
    page.click("text=Benefícios que combinam");
    page.goto(f"{BASE}/#studio"); page.wait_for_selector("#sItems .content-item")
    page.click("text=Uma estratégia para cada objetivo"); page.wait_for_function("()=>document.getElementById('fKey').value==='banner-invest'")
    page.select_option("#fRole", "publisher")
    page.evaluate("document.getElementById('toast').textContent=''")
    page.dblclick("[data-act=publish]")
    page.wait_for_function("()=>document.getElementById('toast').textContent.length>0", timeout=8000)
    page.wait_for_function("()=>![...document.querySelectorAll('[data-act]')].some(b=>b.disabled)", timeout=8000)
    ok("duplo clique em Publicar não gera conflito", "conflito" not in page.inner_text("#toast").lower() and "inválida" not in page.inner_text("#toast").lower())

    page.goto(f"{BASE}/#portal"); page.wait_for_selector("#pContent .hero-portal")
    page.select_option("#pSeg", "jovem"); page.wait_for_function("()=>document.getElementById('pContent').innerText.includes('Benefícios que combinam')", timeout=8000)
    ok("banner publicado aparece no portal (jovem)", True)
    page.click("#pRevalidate"); page.wait_for_function("()=>document.getElementById('pHdrs').innerText.includes('304')", timeout=8000)
    ok("revalidação If-None-Match retorna 304", True)
    page.click("[data-shape=model]"); page.wait_for_function("()=>document.getElementById('pJson').textContent.includes(':itemsOrder')", timeout=8000)
    ok("model.json exibido", True)
    page.click("[data-tab=loan]"); page.wait_for_function("()=>document.getElementById('pCalc').innerText.includes('CET')", timeout=8000)
    ok("calculadora de crédito no portal", True)

    page.goto(f"{BASE}/#market"); page.wait_for_selector(".kpi-card .kpi-number")
    vb = page.evaluate("[...document.querySelectorAll('.dk-w svg')].map(s=>s.getAttribute('viewBox').split(' ')[2]|0)")
    ok(f"gráficos usam largura real (viewBoxes={vb})", len(set(vb)) > 1)
    page.select_option("[data-filter=days]", "1825"); page.wait_for_load_state("networkidle")
    ok("filtro de janela re-renderiza sem erro", page.locator(".dk-error").count() == 0)
    page.fill("[data-f=amount]", "-5"); page.click("text=Simular >> nth=0"); page.wait_for_selector(".calc-out .dk-error", timeout=8000)
    msg = page.inner_text(".calc-out .dk-error")
    ok("validação mostra mensagem legível (não JSON cru)", "amount" in msg and "{" not in msg)

    page.goto(f"{BASE}/#analytics-overview"); page.wait_for_selector(".data-table")
    page.click(".dk-sort[data-key=leads] >> nth=0"); page.click(".dk-sort[data-key=leads] >> nth=0")
    ok("tabela ordenável", "▼" in page.inner_text(".data-table thead") or "▲" in page.inner_text(".data-table thead"))
    page.select_option("[data-filter=segment]", "credito"); page.wait_for_load_state("networkidle")
    ok("filtro de audiência", page.locator(".data-table tbody tr").count() >= 4)

    m = b.new_context(viewport={"width": 390, "height": 800}).new_page()
    m.goto(f"{BASE}/#market"); m.wait_for_selector(".kpi-card .kpi-number"); m.wait_for_load_state("networkidle")
    ov = m.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    ok(f"mobile sem scroll horizontal (overflow={ov}px)", ov <= 2)
    b.close()
print("erros JS inesperados:", errors or "nenhum")
print(f"{sum(checks)}/{len(checks)} checks")
