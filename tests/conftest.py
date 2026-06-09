import pytest
import asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from src.main import create_app
from src.db.session import engine, Base, async_session
from src.models.tenant import Tenant


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def app():
    application = create_app()
    yield application


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def tenant_a(db_session):
    tenant = Tenant(
        name="Tenant A",
        api_key=f"test-key-a-{uuid.uuid4()}",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def tenant_b(db_session):
    tenant = Tenant(
        name="Tenant B",
        api_key=f"test-key-b-{uuid.uuid4()}",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def db_session():
    async with async_session() as session:
        yield session
        await session.rollback()
