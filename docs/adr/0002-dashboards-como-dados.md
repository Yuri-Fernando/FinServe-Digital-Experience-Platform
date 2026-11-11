# ADR 0002 — Dashboards como dados (dashkit) sem bundler

**Status:** aceito · **Contexto:** a v1 tinha um `app.js` de 14 KB com um desenho por gráfico; cada novo painel exigia JavaScript novo. O projeto precisa rodar offline e ser reaproveitado em outros repositórios.

**Decisão:** o servidor entrega uma *spec* JSON (filtros, fontes, widgets) e um renderizador único em vanilla JS a interpreta. O vocabulário de widgets é validado no servidor (`finserve check`). Gráficos são SVG gerado em string, com todo texto escapado.

**Consequências:** (+) um módulo novo ganha uma página sem escrever JS; (+) sem `npm`, sem build, funciona em pasta sincronizada (Drive) sem `node_modules`; (+) specs validadas por teste. (−) menos flexível que uma biblioteca de gráficos madura; interações avançadas (zoom, seleção de intervalo) não existem — registrado como limitação.

**Alternativas descartadas:** Chart.js/ECharts (dependência e build); React (fora do escopo e em conflito com a regra de não instalar `node_modules` dentro de pasta sincronizada).
