"""Fixtures for integration tests - uses real Docker database."""

import asyncio
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from src.db.session import async_session, engine
from src.main import create_app


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
async def db_session():
    """Real database session for integration tests."""
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def setup_test_db(db_session):
    """Clean up and prepare test database."""
    # Clean up in reverse order of dependencies
    await db_session.execute(text("DELETE FROM user_departments"))
    await db_session.execute(text("DELETE FROM users"))
    await db_session.execute(text("DELETE FROM departments"))
    await db_session.execute(text("DELETE FROM chunks"))
    await db_session.execute(text("DELETE FROM documents"))
    await db_session.execute(text("DELETE FROM tenants"))
    await db_session.commit()
    yield db_session
    # Clean up after test
    await db_session.execute(text("DELETE FROM user_departments"))
    await db_session.execute(text("DELETE FROM users"))
    await db_session.execute(text("DELETE FROM departments"))
    await db_session.execute(text("DELETE FROM chunks"))
    await db_session.execute(text("DELETE FROM documents"))
    await db_session.execute(text("DELETE FROM tenants"))
    await db_session.commit()


@pytest.fixture
async def tenant_a(setup_test_db):
    """Create a test tenant A."""
    from src.models.tenant import Tenant
    from src.models.department import Department
    from src.models.user import User
    from src.services.auth_service import pwd_context

    tenant = Tenant(
        name="Tenant A",
        api_key=f"test-key-a-{uuid.uuid4()}",
    )
    setup_test_db.add(tenant)
    await setup_test_db.flush()

    # Create default departments
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
    setup_test_db.add(dept_hr)
    setup_test_db.add(dept_compta)

    # Create users
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
    setup_test_db.add(user_hr)
    setup_test_db.add(user_compta)

    # Create user-department assignments
    from src.models.user_department import UserDepartment

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
    setup_test_db.add(ud_hr)
    setup_test_db.add(ud_compta)

    await setup_test_db.commit()
    await setup_test_db.refresh(tenant)
    await setup_test_db.refresh(dept_hr)
    await setup_test_db.refresh(dept_compta)
    await setup_test_db.refresh(user_hr)
    await setup_test_db.refresh(user_compta)

    # Return a dict with all fixtures
    return {
        "tenant": tenant,
        "dept_hr": dept_hr,
        "dept_compta": dept_compta,
        "user_hr": user_hr,
        "user_compta": user_compta,
    }


@pytest.fixture
def tenant_a_data(setup_test_db):
    """Simpler fixture that returns just tenant data."""
    return None  # Will be set by tenant_a


@pytest.fixture
async def tenant_b(setup_test_db):
    """Create a test tenant B (isolated from tenant A)."""
    from src.models.tenant import Tenant

    tenant = Tenant(
        name="Tenant B",
        api_key=f"test-key-b-{uuid.uuid4()}",
    )
    setup_test_db.add(tenant)
    await setup_test_db.commit()
    await setup_test_db.refresh(tenant)
    return tenant


@pytest.fixture
async def hr_token(tenant_a):
    """JWT token for HR user."""
    from src.services.auth_service import AuthService

    user = tenant_a["user_hr"]
    return AuthService.create_access_token(
        user.id, user.tenant_id, user.is_tenant_admin
    )


@pytest.fixture
async def compta_token(tenant_a):
    """JWT token for Compta user."""
    from src.services.auth_service import AuthService

    user = tenant_a["user_compta"]
    return AuthService.create_access_token(
        user.id, user.tenant_id, user.is_tenant_admin
    )
