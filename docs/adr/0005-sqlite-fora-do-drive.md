# ADR 0005 — SQLite local, banco fora da pasta sincronizada

**Status:** aceito · **Contexto:** o projeto vive em pasta sincronizada pelo Google Drive; arquivos de banco abertos e reescritos nesse tipo de pasta podem gerar conflito ou corrupção. A execução precisa de zero credenciais.

**Decisão:** SQLite sem WAL, caminho configurável por `FINSERVE_DB` (os testes usam `tmp_path`); `data/*.sqlite3` é ignorado pelo git; o seed recria tudo de forma determinística (`FINSERVE_TODAY` fixa a data de referência). Ao rodar a partir de uma pasta sincronizada, aponte `FINSERVE_DB` para um disco local.

**Consequências:** (+) reprodutível e portátil; (−) sem concorrência de escrita real — PostgreSQL é caminho de evolução, não recurso atual.
