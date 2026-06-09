from fastapi import FastAPI
from src.config import get_settings
from src.middleware.tenant import TenantContextMiddleware
from src.api import tenants, documents, rag


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ProAirAg - Hybrid Multi-Tenant RAG",
        version="0.1.0",
    )

    # Middleware
    app.add_middleware(TenantContextMiddleware)

    # Routers
    app.include_router(tenants.router)
    app.include_router(documents.router)
    app.include_router(rag.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()