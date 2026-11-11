from pathlib import Path

from ...registry import Dataset, Module
from .router import router
from .seed import seed


def _datasets(con):
    n = con.execute("SELECT COUNT(*) FROM content_items").fetchone()[0]
    return [Dataset("experience.content", "experience", "Componentes editoriais e revisões", "synthetic",
                    "Texto institucional fictício escrito para a demonstração", None, None, n,
                    "Tokens {{selic_meta}} etc. são resolvidos na entrega com dados reais do módulo market.")]


MODULE = Module(
    name="experience",
    title="Experience / Content Studio",
    version="2.0.0",
    description="Workflow editorial com papéis, versionamento, diff, compliance YAML, tokens de mercado e entrega headless.",
    router=router,
    schema=Path(__file__).with_name("schema.sql"),
    tables=("content_items", "content_revisions"),
    seed=seed,
    datasets=_datasets,
    requires=("platform",),
    optional=("market",),
)
