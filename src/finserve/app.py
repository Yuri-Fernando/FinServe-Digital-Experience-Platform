"""Application factory: monta somente os módulos habilitados."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, config, registry
from .db import apply_schema, connect


def bootstrap(modules: list[registry.Module]) -> None:
    """Aplica schemas e roda seeds idempotentes. Seguro de chamar a cada start."""
    with connect() as con:
        for m in modules:
            if m.schema:
                apply_schema(con, m.schema)
        for m in modules:
            if m.seed:
                m.seed(con)


def create_app(modules: list[str] | None = None) -> FastAPI:
    mods = registry.load(modules)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        bootstrap(mods)
        yield

    app = FastAPI(
        title="FinServe Platform API",
        version=__version__,
        lifespan=lifespan,
        description=(
            "Plataforma modular de experiência digital financeira. Cada módulo declara a proveniência dos seus "
            "dados (real × sintético) em /api/platform/provenance. Não é backend bancário nem Adobe AEM."
        ),
    )
    app.state.modules = mods
    for m in mods:
        if m.router is not None:
            app.include_router(m.router, prefix=f"/api/{m.name}", tags=[m.name])

    web = config.web_dir()
    if (web / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=str(web / "assets")), name="assets")

        @app.get("/", include_in_schema=False)
        def index():
            return FileResponse(web / "index.html")

    return app


app = create_app()
