# dashkit — dashboards como dados

O `dashkit` separa **o que mostrar** (uma spec JSON entregue pela API) de **como desenhar** (`web/assets/dashkit/kit.js`, vanilla JS, sem bundler, sem dependências). Qualquer módulo ganha uma página de dashboard declarando uma spec; nenhum JavaScript novo é necessário.

## Spec

```json
{
  "id": "market", "title": "Mercado", "eyebrow": "DADOS OFICIAIS", "subtitle": "...",
  "nav": {"label": "Mercado", "icon": "◐", "order": 2},
  "filters": [{"id": "days", "label": "Janela", "type": "int", "default": 365,
               "options": [{"value": 365, "label": "12 meses"}]}],
  "sources": {
    "main":  {"url": "/api/market/overview"},
    "selic": {"url": "/api/market/series/selic_meta", "params": ["days"]}
  },
  "widgets": [
    {"type": "kpis", "items": [{"label": "Meta Selic", "path": "cards.selic_meta.value", "format": "num2",
                                "suffix": "% a.a.", "delta_path": "cards.selic_meta.change", "delta_unit": "p.p."}]},
    {"type": "line", "source": "selic", "title": "Meta Selic", "path": "points", "x": "date",
     "series": [{"key": "value", "label": "Meta Selic"}], "span": 2}
  ]
}
```

- **sources**: endpoints GET; `params` lista os filtros enviados como query string. `main` é obrigatório; cada widget pode escolher outra via `"source"`.
- **path**: caminho com pontos dentro do JSON da fonte (`""` = raiz).
- **span**: largura na grade de 3 colunas (1–3). Em telas pequenas tudo empilha.
- Falha de uma fonte não derruba o dashboard: só os widgets daquela fonte mostram o erro.

## Widgets

| Tipo | Campos obrigatórios | Notas |
|---|---|---|
| `kpis` | `items` | `delta_path`, `delta_good` (`up`/`down`/`none`), `foot`/`foot_path`, `compact` |
| `line` | `path`, `x`, `series` | `normalize` (séries em unidades diferentes), `format`; tooltip nativo por ponto |
| `bars` | `path`, `label`, `value` | aceita negativos (cor distinta); `label_format: "month"` |
| `donut` | `path`, `label`, `value` | `center_label` |
| `funnel` | `path`, `stages` | mostra % do topo e % da etapa anterior |
| `vitals` | `path` | espera itens `{id,name,p75,unit,good,poor,status,samples}` |
| `table` | `path`, `columns` | ordenação por clique; chaves com ponto (`control.rate_pct`); `export` (link de CSV) |
| `list` | `path`, `primary` | `secondary`/`primary` são templates `{campo}`; `badge`, `limit`, `empty` |
| `notes` | `items` | lista simples |
| `calculator` | `calc` | `investment` ou `loan` (usam `/api/market/simulate/*`) |

**Formatos** (`format`): `int compact pct pct1 money money2 num2 num4 ms date month bool badge text` — pt-BR.

## Validação
`finserve check` roda `finserve.dashkit.validate_spec` em todas as specs: tipo de widget, campos obrigatórios, fontes inexistentes, parâmetros sem filtro, formatos e calculadoras desconhecidos. Os testes (`tests/test_platform.py`) cobrem cada regra.

## Segurança
Todo texto vindo da API passa por `esc()` antes de entrar no DOM; formatos que devolvem HTML (`badge`) escapam o conteúdo internamente.

## Reaproveitar fora da plataforma
`kit.js` + `kit.css` + `theme.css` não dependem do backend FastAPI: basta servir os arquivos e expor endpoints JSON compatíveis com as specs.
