from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from src.config import get_settings
from src.middleware.tenant import TenantContextMiddleware
from src.api import tenants, documents, rag, auth, departments, chat
import src.api.rag_settings as rag_settings
import src.api.admin as admin_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: auto-seed super admin and dashboard tenants
    from src.db.seed import run_seed
    try:
        await run_seed()
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Auto-seed failed")
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ProAiRag - Hybrid Multi-Tenant RAG",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(TenantContextMiddleware)

    # Routers
    app.include_router(auth.router)
    app.include_router(departments.router)
    app.include_router(tenants.router)
    app.include_router(documents.router)
    app.include_router(rag.router)
    app.include_router(chat.router)
    app.include_router(rag_settings.router)
    app.include_router(admin_api.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    # Serve frontend static files
    # Check both dev path (frontend/dist/) and Docker path (src/static/)
    static_dir = Path(__file__).parent.parent / "frontend" / "dist"
    if not static_dir.exists():
        static_dir = Path(__file__).parent / "static"
    assets_dir = static_dir / "assets"

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    def _serve_index():
        """Serve the SPA index.html"""
        index_file = static_dir / "index.html"
        if index_file.exists():
            return HTMLResponse(index_file.read_text())
        return HTMLResponse("<h1>Frontend not built. Run: cd frontend && npm run build</h1>", status_code=503)

    # SPA routes - each one serves index.html
    for path in ["/", "/login", "/services", "/documents", "/chat", "/settings"]:
        app.get(path)(_serve_index)

    return app


app = create_app()
