"""Fixtures for integration tests - uses real Docker database."""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from src.db.session import async_session
from src.main import create_app
from passlib.context import CryptContext
from src.models.tenant import Tenant
from src.models.department import Department
from src.models.user import User
from src.models.user_department import UserDepartment

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture(scope="session")
async def app():
    """Create the FastAPI app once for the session."""
    application = create_app()
    yield application


@pytest.fixture(scope="session")
async def client(app):
    """Create the HTTP client once for the session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session():
    """Database session for tests."""
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
async def cleanup_before_test():
    """Clean up before each test to ensure isolation."""
    async with async_session() as session:
        try:
            await session.execute(text("DELETE FROM user_departments"))
            await session.execute(text("DELETE FROM users"))
            await session.execute(text("DELETE FROM departments"))
            await session.execute(text("DELETE FROM chunks"))
            await session.execute(text("DELETE FROM documents"))
            await session.execute(text("DELETE FROM tenants"))
            await session.commit()
        except Exception:
            # Ignore cleanup errors
            pass


async def create_test_data():
    """Create tenant with departments and users for testing."""
    async with async_session() as session:
        tenant = Tenant(
            name=f"TestTenant-{uuid.uuid4().hex[:8]}",
            api_key=f"test-key-a-{uuid.uuid4()}",
        )
        session.add(tenant)
        await session.flush()

        dept_hr = Department(
            tenant_id=tenant.id,
            name="RH",
            description="Ressources Humaines",
        )
        dept_compta = Department(
            tenant_id=tenant.id,
            name="Comptabilite",
            description="Finance",
        )
        session.add(dept_hr)
        session.add(dept_compta)
        await session.flush()

        user_hr = User(
            tenant_id=tenant.id,
            email="hr@company.com",
            password_hash=pwd_context.hash("password123"),
            full_name="HR User",
        )
        user_compta = User(
            tenant_id=tenant.id,
            email="compta@company.com",
            password_hash=pwd_context.hash("password123"),
            full_name="Compta User",
        )
        session.add(user_hr)
        session.add(user_compta)
        await session.flush()

        ud_hr = UserDepartment(
            user_id=user_hr.id,
            department_id=dept_hr.id,
            role="member",
        )
        ud_compta = UserDepartment(
            user_id=user_compta.id,
            department_id=dept_compta.id,
            role="member",
        )
        session.add(ud_hr)
        session.add(ud_compta)
        await session.commit()

        return {
            "tenant": tenant,
            "dept_hr": dept_hr,
            "dept_compta": dept_compta,
            "user_hr": user_hr,
            "user_compta": user_compta,
        }


@pytest.fixture
async def tenant_data(client):
    """Create test tenant with departments and users."""
    data = await create_test_data()
    yield {"client": client, **data}


@pytest.fixture
async def tenant_a(client):
    """Create test tenant A with departments and users."""
    data = await create_test_data()
    yield data


@pytest.fixture
async def tenant_b(client):
    """Create test tenant B."""
    async with async_session() as session:
        tenant = Tenant(
            name=f"TenantB-{uuid.uuid4().hex[:8]}",
            api_key=f"test-key-b-{uuid.uuid4()}",
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        yield tenant


@pytest.fixture
async def hr_token(client, tenant_a):
    """JWT token for HR user."""
    from src.services.auth_service import AuthService

    user = tenant_a["user_hr"]
    return AuthService.create_access_token(
        user.id, user.tenant_id, user.is_tenant_admin
    )


@pytest.fixture
async def compta_token(client, tenant_a):
    """JWT token for Compta user."""
    from src.services.auth_service import AuthService

    user = tenant_a["user_compta"]
    return AuthService.create_access_token(
        user.id, user.tenant_id, user.is_tenant_admin
    )
